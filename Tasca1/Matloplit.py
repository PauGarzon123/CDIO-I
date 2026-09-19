import matplotlib.pyplot as plt
import rasterio

imatge = '/home/archpc/CDIO-I/Tasca1/Imatges/S2C_31TDF_20250630_0_L2A_nir.tif'
imatge_green = '/home/archpc/CDIO-I/Tasca1/Imatges/S2C_31TDF_20250630_0_L2A_green.tif'

#Imatge tiff comprimida,necessitem rasterio per descomprimir-ho a la mateixa resolucio per fer els calculs
print(type(imatge))


with rasterio.open(imatge) as src:
    nir = src.read(1, out_shape=(1098, 1098))

with rasterio.open(imatge_green) as src:
    green = src.read(1, out_shape=(1098, 1098))

#Imatge descompresa
print(type(green))   

#plt.imshow(imatge_f)
#plt.show()

# Calculem NDWI amb : (Verd - NIR) / (Verd + NIR ), float a green pels valors negatius
# astype(float) per cambiar a float tota la matriu
ndwi = (green.astype(float) - nir) / (green + nir )
plt.imshow(ndwi)
plt.show()

