import glob
import rasterio

archivos = glob.glob("../Tasca2/ndwi/*.tif")

print("Imágenes encontradas:", len(archivos))

for n in range(0, 24):
    with rasterio.open(archivos[n]) as src:
        ndwi = src.read(1)

    print(f"\n--- TIFF {n}: {archivos[n]} ---")
    print(ndwi)
