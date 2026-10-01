import glob
import rasterio
import matplotlib.pyplot as plt

archivos = glob.glob("../Tasca2/ndwi/*.tif")

print("Imágenes encontradas:", len(archivos))
print(archivos[0])

for n in range(0,24):
    with rasterio.open(archivos[n]) as src:
        ndwi = src.read(1)

plt.figure(figsize=(10, 8))
plt.imshow(ndwi, cmap="RdYlBu")
plt.colorbar(label="NDWI")
plt.title("NDWI")
plt.show()
