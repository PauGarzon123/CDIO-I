from pystac_client import Client  #per connectar-nos al catàleg STAC i fer cerques
import geopandas as gpd  #per llegir el polygon.geojson
import json  #per llegir el config.json
from tqdm import tqdm  #barra de progrés als bucles
import pprint  #imprimir llistes i diccionaris ben formatats
from collections import Counter  #diccionari que compta coses sol
from pathlib import Path  #per treballar amb rutes de fitxers
from datetime import date  #per restar dates (dies del període)
import time  #cronòmetre per mesurar el temps
import psutil  #per llegir els bytes rebuts per la targeta de xarxa
import rasterio  #per llegir i escriure imatges geogràfiques (GeoTIFF)
from rasterio.mask import mask  #per retallar una imatge amb el polígon
from rasterio.windows import from_bounds  #per passar coordenades en metres a files/columnes
import matplotlib.pyplot as plt  #per fer les figures RGB


#__file__ es la ruta del propi tasca2.py , parent es la carpeta major
#BASE_DIR es desde la carpeta tasca2 --> busca `polygon o config`
BASE_DIR = Path(__file__).resolve().parent
POLYGON_FILE = BASE_DIR / "polygon.geojson"
CONFIG_FILE = BASE_DIR / "config.json"
OUTPUT_DIR = BASE_DIR / "imatges"  #aqui es desen els GeoTIFF green i nir
RGB_DIR = BASE_DIR / "rgb"  #aqui es desen els PNG en color real

#impressora "bonica" amb sagnat de 4 espais, s'usa amb pp.pprint(...)
pp = pprint.PrettyPrinter(indent=4)


def search_catalog(catalog, max_cloud=None):
    """Busca les imatges Sentinel-2 L2A que toquen el polígon dins del període del config.
    Si max_cloud té valor, només retorna les que tenen menys d'aquest % de núvols."""

    #escollim la URL segons el catàleg que ens passen
    if catalog == "element84":
        catalog_url = "https://earth-search.aws.element84.com/v1"
    elif catalog == "copernicus":
        catalog_url = "https://stac.dataspace.copernicus.eu/v1"
    else:
        #si no és cap dels dos, parem el programa amb un error
        raise ValueError("Invalid catalog name. Choose 'copernicus' or 'element84'.")

    #llegim el polígon i agafem la primera forma en format GeoJSON (el que entén el catàleg)
    gdf = gpd.read_file(POLYGON_FILE)
    aoi = gdf.geometry[0].__geo_interface__
    #llegim les dates del config, el with tanca el fitxer sol
    with open(CONFIG_FILE) as f:
        config = json.load(f)

    #filtre de núvols: només el posem si ens passen max_cloud
    #"lt" vol dir "less than" (menor que), sobre la propietat eo:cloud_cover de cada imatge
    query = None
    if max_cloud is not None:
        query = {"eo:cloud_cover": {"lt": max_cloud}}

    #ens connectem al servidor i preparem la cerca amb els filtres
    client = Client.open(catalog_url)
    search = client.search(
        collections=["sentinel-2-l2a"],  #només Sentinel-2 amb correcció atmosfèrica
        intersects=aoi,  #imatges que toquen el polígon
        datetime=f"{config['START_DATE']}/{config['END_DATE']}",  #"inici/final"
        query=query,  #filtre de núvols (None = sense filtre)
    )
    #search.items() va demanant resultats al servidor, list() els porta tots
    items = list(search.items())

    # 1) Nombre d'imatges per satèl·lit
    platform_counter = Counter()
    #uutilitzem llibreria Counter per comptar
    for it in items:
        props = it.properties or {}
        #Mirem si tenen per request de platform o satellite:id , un dels dos
        platform = props.get("platform") or props.get("satellite:id") or "unknown"
        # +1 a platform (sentinel A/B/C)
        platform_counter[platform] += 1

    #títol diferent segons si hem filtrat o no
    if max_cloud is None:
        print("Imatges per plataforma (sense filtre de núvols):")
    else:
        print(f"Imatges per plataforma (núvols < {max_cloud} %):")
    pp.pprint(dict(platform_counter))
    #len(items) = quants elements té la llista = total d'imatges
    print(f"Total d'imatges: {len(items)}")

    return items, platform_counter


def download_band(item, band):
    """Descarrega només el tros de la banda que cau dins del polígon i el desa com a GeoTIFF."""
    #URL del fitxer de la banda (ex: .../B03.tif per green)
    href = item.assets[band].href
    OUTPUT_DIR.mkdir(exist_ok=True) #Crea carpeta de imatges i si ja existeix no dona error
    #nom del fitxer de sortida: id de la imatge + banda
    out_path = OUTPUT_DIR / f"{item.id}_{band}.tif"

    # Si ja el tenim d'una execució anterior, no el tornem a baixar
    if out_path.exists():
        return out_path

    gdf = gpd.read_file(POLYGON_FILE)

    # rasterio llegeix el COG per internet: només baixa els blocs que toquen el polígon
    with rasterio.open(href) as src:
        # El polígon està en graus (EPSG:4326) i la imatge en metres (UTM): cal convertir-lo
        aoi = gdf.to_crs(src.crs).geometry
        #rasterio nomes demana les imatges dintre del aoi
        #crop=True retalla al rectangle del polígon, transform diu on és al mapa
        data, transform = mask(src, aoi, crop=True)
        #fitxa tècnica del GeoTIFF que crearem
        profile = {
            "driver": "GTiff",  #format GeoTIFF
            "dtype": data.dtype,  #uint16, igual que l'original
            "count": data.shape[0],  #nombre de bandes (1)
            "height": data.shape[1],  #files
            "width": data.shape[2],  #columnes
            "crs": src.crs,  #sistema de coordenades (UTM 31N)
            "transform": transform,  #posició al mapa
            "nodata": src.nodata,  #valor que vol dir "sense dada" (0)
        }

    #obrim el fitxer en mode escriptura ("w") i hi escrivim la matriu
    #**profile desempaqueta el diccionari com si escrivíssim driver=..., dtype=..., etc
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(data)

    return out_path


def save_rgb(item, marge_m=2000):
    """Desa com a PNG la imatge en color real (asset 'visual') de la zona del polígon, amb un marge al voltant."""
    RGB_DIR.mkdir(exist_ok=True)
    out_path = RGB_DIR / f"{item.id}_rgb.png"

    gdf = gpd.read_file(POLYGON_FILE)

    #"visual" és la TCI: red+green+blue ja muntades per l'ESA, en 8 bits (0-255)
    with rasterio.open(item.assets["visual"].href) as src:
        aoi = gdf.to_crs(src.crs)
        # Rectangle que envolta el polígon, ampliat marge_m metres per cada costat
        minx, miny, maxx, maxy = aoi.total_bounds
        #passem el rectangle en metres a una finestra de files/columnes de la imatge
        finestra = from_bounds(minx - marge_m, miny - marge_m, maxx + marge_m, maxy + marge_m, src.transform)
        rgb = src.read(window=finestra)  # forma (3, files, columnes), valors 0-255
        #coordenades reals de les vores, perquè els eixos surtin en metres
        left, bottom, right, top = src.window_bounds(finestra)

    fig, ax = plt.subplots(figsize=(10, 6))
    # matplotlib vol (files, columnes, 3): movem l'eix de les bandes al final
    ax.imshow(rgb.transpose(1, 2, 0), extent=(left, right, bottom, top))
    #dibuixem només el contorn del polígon en vermell
    aoi.boundary.plot(ax=ax, color="red", linewidth=1)
    #al títol posem el % de núvols de la imatge
    ax.set_title(f"{item.id} | núvols: {item.properties['eo:cloud_cover']:.1f} %")
    ax.set_xlabel("x (m, UTM 31N)")
    ax.set_ylabel("y (m, UTM 31N)")
    #desem com a PNG, bbox_inches="tight" treu el marge blanc que sobra
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    #tanquem la figura per alliberar memòria
    plt.close(fig)

    return out_path


#part del programa que nomes executa si sexecuta tasca2.py, + per posar el argument descollir sentinel o element84
#esta posat element84 per defecte, sino python tasca.py--catalog copernicus
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="STAC Catalog Demo")
    parser.add_argument("--catalog", type=str, default="element84", choices=["copernicus", "element84"])
    args = parser.parse_args()

    #cronòmetre de tot el programa
    t_programa = time.perf_counter()

    with open(CONFIG_FILE) as f:
        config = json.load(f)
    max_cloud = config["MAX_CLOUD_COVER_PERCENTAGE"]

    # 2) Filtre de núvols
    #cerca sense filtre, només per poder comparar (la cerca és ràpida, no baixa imatges)
    items_tots, comptador_tots = search_catalog(args.catalog)
    #cerca amb filtre: el servidor ja només ens retorna les imatges amb pocs núvols
    items, comptador_filtrat = search_catalog(args.catalog, max_cloud)

    #validació: per cada satèl·lit, amb filtre n'hi ha d'haver menys o igual que sense
    print("Validació del filtre:")
    for plataforma in sorted(comptador_tots):
        abans = comptador_tots[plataforma]
        despres = comptador_filtrat[plataforma]  #Counter dona 0 si no hi és
        estat = "OK" if despres <= abans else "ERROR"
        print(f"  {plataforma}: {abans} -> {despres} ({estat})")

    if items:
        # Descarregar green i nir de totes les imatges, sumant el que ocupen
        total_bytes = 0
        # Bytes rebuts per la targeta de xarxa i hora abans de començar
        net_inici = psutil.net_io_counters().bytes_recv
        t_inici = time.perf_counter()
        #dos bucles: per cada imatge, per cada banda
        for item in tqdm(items, desc="Descarregant"):
            for band in ["green", "nir"]:
                path = download_band(item, band)
                #sumem el que ocupa el fitxer al disc
                total_bytes += path.stat().st_size
        #temps de descàrrega = ara - inici
        t_descarrega = time.perf_counter() - t_inici
        #MB que han entrat per la xarxa durant la descàrrega
        net_mb = (psutil.net_io_counters().bytes_recv - net_inici) / 1024**2

        # Extrapolació: quant ocuparia per a N mesos
        #restant dues dates surt un interval, .days el dona en dies
        days = (date.fromisoformat(config["END_DATE"]) - date.fromisoformat(config["START_DATE"])).days
        #30.44 = dies que té un mes de mitjana (365.25 / 12)
        months = days / 30.44
        #dividim per 1024**2 per transformar-ho a MB
        total_mb = total_bytes / 1024**2

        print(f"Fitxers: {2 * len(items)} | Total: {total_mb:.2f} MB | Per imatge (green+nir): {total_mb / len(items) * 1024:.1f} KB")
        print(f"Període: {months:.1f} mesos -> {total_mb / months:.2f} MB/mes")
        #regla de tres: MB/mes * N
        for n in [1, 6, 12, 24]:
            print(f"  {n:>2} mesos ≈ {total_mb / months * n:.2f} MB")

        # Temps i amplada de banda
        print(f"Temps de descàrrega: {t_descarrega:.1f} s ({t_descarrega / len(items):.2f} s per imatge)")
        print(f"Baixat per la xarxa: {net_mb:.2f} MB (a disc: {total_mb:.2f} MB)")
        #amplada de banda = MB / segons, *8 per passar de bytes a bits (Mbit/s)
        print(f"Amplada de banda: {net_mb / t_descarrega:.3f} MB/s = {net_mb * 8 / t_descarrega:.2f} Mbit/s")
        #mateixa regla de tres amb el temps, /60 per passar a minuts
        print(f"Temps per mes: {t_descarrega / months / 60:.1f} min")
        for n in [1, 6, 12, 24]:
            print(f"  {n:>2} mesos ≈ {t_descarrega / months * n / 60:.1f} min")
        print(f"Temps total del programa: {time.perf_counter() - t_programa:.1f} s")

    # Visualització RGB: la imatge amb menys núvols i la que en té més, per comprovar el filtre
    #només mirem imatges on el tile té dades gairebé sencer (algunes passades només en cobreixen un 7%)
    completes = [it for it in items_tots if it.properties["s2:nodata_pixel_percentage"] < 50]
    #min/max amb key: compara les imatges pel seu % de núvols
    mes_neta = min(completes, key=lambda it: it.properties["eo:cloud_cover"])
    mes_nuvolosa = max(completes, key=lambda it: it.properties["eo:cloud_cover"])
    for item in [mes_neta, mes_nuvolosa]:
        rgb_path = save_rgb(item)
        print(f"RGB desat: {rgb_path.name}")
