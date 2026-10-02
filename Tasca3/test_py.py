import numpy as np  #per crear matrius de prova
import pytest  #llibreria de tests: s'executa amb "pytest Tasca2"
from pathlib import Path  #per trobar el fitxer de referència
from ndwi import calculate_ndwi  #la funció que volem comprovar

#qualsevol avís (RuntimeWarning de numpy, per exemple) fa fallar el test
#així ens assegurem que els casos límit es gestionen, no que "surten bé per casualitat"
pytestmark = pytest.mark.filterwarnings("error")

#fitxer amb una imatge real (green, nir) i el NDWI que dona avui la funció
REFERENCIA = Path(__file__).resolve().parent / "dades_test" / "ndwi_referencia.npz"


#parametrize: el mateix test s'executa una vegada per cada fila de la llista
#cada fila és (green, nir, resultat esperat)
@pytest.mark.parametrize(
    "green, nir, expected",
    [
        (0.08, 0.02, 0.6),          # aigua
        (0.05, 0.40, -0.7777778),   # vegetació
        (0.10, 0.10, 0.0),          # iguals
        (0.10, 0.0, 1.0),           # nir = 0
        (0.0, 0.10, -1.0),          # green = 0
        (0.0, 0.0, np.nan),         # 0/0 -> NaN
    ],
)
def test_detect_waterbody(green, nir, expected):
    result = calculate_ndwi(green, nir)

    if np.isnan(expected):
        assert np.isnan(result)
    else:
        assert result == pytest.approx(expected)

