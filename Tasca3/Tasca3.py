import glob
import os
import rasterio
import numpy as np

archivos = glob.glob("../Tasca2/ndwi/*.tif")

matrices_binarias = []

for archivo in archivos:
    with rasterio.open(archivo) as src:
        ndwi = src.read(1)

        # Guardamos el perfil geoespacial del original
        perfil = src.profile.copy()

    # Negativos = 0, positivos = 1
    matriz_binaria = (ndwi > 0).astype(np.uint8)

    matrices_binarias.append(matriz_binaria)

    # Nombre del fichero de salida
    nombre = os.path.basename(archivo)
    nombre_salida = os.path.splitext(nombre)[0] + "_binary.tif"

    # Directorio de salida
    directorio_salida = "../Tasca3/ndwi_binary"
    os.makedirs(directorio_salida, exist_ok=True)

    ruta_salida = os.path.join(directorio_salida, nombre_salida)

    # Actualizamos el perfil para la matriz binaria
    perfil.update(
        dtype=rasterio.uint8,
        count=1,
        nodata=0
    )

    # Guardamos el GeoTIFF
    with rasterio.open(ruta_salida, "w", **perfil) as dst:
        dst.write(matriz_binaria, 1)

    print(f"Guardado: {ruta_salida}")




"""for i, matriz in enumerate(matrices_binarias):

    plt.figure(figsize=(8, 6))
    plt.imshow(matriz, cmap="gray")
    plt.colorbar(label="0 = negativo / 1 = positivo")
    plt.title(f"NDWI binario - TIFF {i}")
    plt.show()"""
