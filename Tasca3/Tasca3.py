import glob
import rasterio
import numpy as np

archivos = glob.glob("../Tasca2/ndwi/*.tif")

matrices_binarias = []

for archivo in archivos:
    with rasterio.open(archivo) as src:
        ndwi = src.read(1)

    # Negativos = 0, positivos = 1
    matriz_binaria = (ndwi > 0).astype(np.uint8)

    matrices_binarias.append(matriz_binaria)

    print(f"\n--- {archivo} ---")
    print(matriz_binaria)

import matplotlib.pyplot as plt

for i, matriz in enumerate(matrices_binarias):

    plt.figure(figsize=(8, 6))
    plt.imshow(matriz, cmap="gray")
    plt.colorbar(label="0 = negativo / 1 = positivo")
    plt.title(f"NDWI binario - TIFF {i}")
    plt.show()
