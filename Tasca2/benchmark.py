import argparse  #per llegir les opcions de la terminal (--fils)
import json  #per llegir el config.json
import shutil  #per esborrar la carpeta temporal amb tot el que té dins
import time  #cronòmetre
import psutil  #bytes rebuts per la targeta de xarxa
import tasca2  #reutilitzem les funcions del programa principal


#cada execució fa UNA sola mesura: així no hi ha res a la memòria cau d'una mesura anterior
#ús: python Tasca2/benchmark.py descarrega --fils 1
#    python Tasca2/benchmark.py descarrega --fils 4
#    python Tasca2/benchmark.py ndwi --procs 1
#    python Tasca2/benchmark.py ndwi --procs 4
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Comparació de temps amb diferents fils")
    parser.add_argument("prova", choices=["descarrega", "ndwi"])
    parser.add_argument("--fils", type=int, default=1)  #per a la prova descarrega
    parser.add_argument("--procs", type=int, default=1)  #per a la prova ndwi
    args = parser.parse_args()

    with open(tasca2.CONFIG_FILE) as f:
        config = json.load(f)
    #mateixes imatges que el programa principal: 1r semestre 2025, núvols < 10 %
    items, _ = tasca2.search_catalog("element84", config["MAX_CLOUD_COVER_PERCENTAGE"])

    if args.prova == "descarrega":
        #carpeta temporal buida, perquè no es salti cap fitxer que ja existeixi
        carpeta = tasca2.BASE_DIR / f"benchmark_{args.fils}_fils"
        shutil.rmtree(carpeta, ignore_errors=True)

        net_inici = psutil.net_io_counters().bytes_recv
        t_inici = time.perf_counter()
        paths = tasca2.download_all(items, n_fils=args.fils, out_dir=carpeta)
        temps = time.perf_counter() - t_inici
        net_mb = (psutil.net_io_counters().bytes_recv - net_inici) / 1024**2

        print(f"Fils: {args.fils} | Fitxers: {len(paths)} | Temps: {temps:.1f} s "
              f"({temps / len(paths):.2f} s per fitxer) | Xarxa: {net_mb:.1f} MB "
              f"| Amplada de banda: {net_mb * 8 / temps:.2f} Mbit/s")

        #esborrem la carpeta temporal
        shutil.rmtree(carpeta)

    if args.prova == "ndwi":
        #abans del cronòmetre ens assegurem que les bandes ja són a imatges/
        #així només mesurem el càlcul del NDWI, no la descàrrega
        tasca2.download_all(items)

        t_inici = time.perf_counter()
        resultats = tasca2.ndwi_all(items, n_processos=args.procs)
        temps = time.perf_counter() - t_inici

        print(f"Processos: {args.procs} | Imatges: {len(resultats)} | Temps: {temps:.2f} s "
              f"({temps / len(resultats) * 1000:.0f} ms per imatge)")
