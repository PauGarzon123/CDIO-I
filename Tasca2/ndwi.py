import numpy as np  #per operar amb matrius senceres


def calculate_ndwi(green, nir):
    """Calcula el NDWI = (green - nir) / (green + nir) per a cada píxel.
    Els píxels on no es pot calcular (green + nir = 0) queden com a NaN."""

    #1) passem a float: amb uint16 les restes negatives "donen la volta" (1000 - 3000 = 63536)
    #np.asarray també accepta llistes normals de Python
    green = np.asarray(green, dtype=np.float64)
    nir = np.asarray(nir, dtype=np.float64)

    #comprovem que siguin la mateixa imatge: si no, numpy podria "estirar" una matriu
    #per encaixar-la amb l'altra (broadcasting) i donaria un resultat sense sentit
    if green.shape != nir.shape:
        raise ValueError(f"green {green.shape} i nir {nir.shape} han de tenir la mateixa forma")

    #2) les reflectàncies negatives no tenen sentit físic (només poden venir de soroll), les posem a 0
    #np.maximum compara element a element i es queda el més gran
    green = np.maximum(green, 0)
    nir = np.maximum(nir, 0)

    numerador = green - nir
    denominador = green + nir

    #3) matriu del resultat plena de NaN, i només dividim on el denominador no és 0
    #els píxels amb 0/0 (sense dades) es queden com a NaN, sense avisos
    ndwi = np.full(green.shape, np.nan)
    np.divide(numerador, denominador, out=ndwi, where=denominador > 0)

    return ndwi
