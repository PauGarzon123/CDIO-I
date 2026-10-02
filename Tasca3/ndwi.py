import numpy as np  #per operar amb matrius senceres


def calculate_ndwi(green, nir):
    """Calcula el NDWI = (green - nir) / (green + nir) per a cada píxel.
    Els píxels on no es pot calcular (green + nir = 0) queden com a NaN."""

    green = np.asarray(green, dtype=np.float64)
    nir = np.asarray(nir, dtype=np.float64)

    if green.shape != nir.shape:
        raise ValueError(f"green {green.shape} i nir {nir.shape} han de tenir la mateixa forma")
    green = np.where(np.isfinite(green), green, np.nan)
    nir = np.where(np.isfinite(nir), nir, np.nan)
    green = np.maximum(green, 0)
    nir = np.maximum(nir, 0)

    numerador = green - nir
    denominador = green + nir
    ndwi = np.full(green.shape, np.nan)
    np.divide(numerador, denominador, out=ndwi, where=denominador > 0)

    return ndwi
