from pystac_client import Client
import geopandas as gpd
import json
from tqdm import tqdm
import pprint
from collections import Counter

pp = pprint.PrettyPrinter(indent=4)

def search_catalog(catalog):
    if catalog == "element84":
        catalog_url = "https://earth-search.aws.element84.com/v1"
    elif catalog == "copernicus":
        catalog_url = "https://stac.dataspace.copernicus.eu/v1"
    else:
        raise ValueError("Invalid catalog name. Choose 'copernicus' or 'element84'.")

    gdf = gpd.read_file("polygon.geojson")
    aoi = gdf.geometry[0].__geo_interface__
    config = json.load(open("config.json"))

    catalog = Client.open(catalog_url)
    search = catalog.search(
        collections=["sentinel-2-l2a"],
        intersects=aoi,
        datetime=f"{config['START_DATE']}/{config['END_DATE']}",
    )
    items = list(search.items())

    # 1) Nombre d'imatges per satèl·lit
    platform_counter = Counter()
    for it in items:
        props = it.properties or {}
        platform = props.get("platform") or props.get("satellite:id") or "unknown"
        platform_counter[platform] += 1

    print("Imatges per plataforma:")
    pp.pprint(dict(platform_counter))

    # 2) Llistar assets de la primera imatge (com ja feies)
    if items:
        pp.pprint(list(items[0].to_dict()['assets'].keys()))

    return items

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="STAC Catalog Demo")
    parser.add_argument("--catalog", type=str, default="element84", choices=["copernicus", "element84"])
    args = parser.parse_args()
    search_catalog(args.catalog)