import numpy as np  #per crear matrius de prova
import pytest  #llibreria de tests: s'executa amb "pytest Tasca2"
from ndwi import calculate_ndwi  #la funció que volem comprovar


#parametrize: el mateix test s'executa una vegada per cada fila de la llista
#cada fila és (green, nir, resultat esperat)
@pytest.mark.parametrize(
    "green, nir, expected",
    [
        (0.08, 0.02, 0.6),  #aigua: reflecteix verd i absorbeix l'infraroig -> positiu
        (0.05, 0.40, -0.7777778),  #vegetació: reflecteix molt infraroig -> negatiu
        (0.10, 0.10, 0.0),  #iguals -> 0
        (0.10, 0.0, 1.0),  #nir = 0 -> màxim possible
        (0.0, 0.10, -1.0),  #green = 0 -> mínim possible
    ],
)
def test_valors_basics(green, nir, expected):
    #np.array([...]) perquè la funció treballa amb matrius, com les imatges
    result = calculate_ndwi(np.array([green]), np.array([nir]))
    #pytest.approx: accepta petits errors de decimals (0.1 + 0.2 no és exactament 0.3)
    assert result[0] == pytest.approx(expected)


def test_matriu_2d_mante_la_forma():
    #una imatge és una matriu de files x columnes: el resultat ha de tenir la mateixa forma
    green = np.array([[0.08, 0.05], [0.10, 0.10]])
    nir = np.array([[0.02, 0.40], [0.10, 0.0]])
    result = calculate_ndwi(green, nir)
    assert result.shape == (2, 2)
    #cada píxel es calcula pel seu compte
    assert result == pytest.approx(np.array([[0.6, -0.7777778], [0.0, 1.0]]))


def test_divisio_per_zero_dona_nan():
    #píxels sense dades: green = 0 i nir = 0 -> 0/0
    #no volem un error ni un número inventat, volem NaN ("not a number" = sense dada)
    result = calculate_ndwi(np.array([0.0, 0.08]), np.array([0.0, 0.02]))
    assert np.isnan(result[0])
    #la resta de píxels s'han de calcular bé igualment
    assert result[1] == pytest.approx(0.6)


def test_entrada_uint16():
    #els GeoTIFF que baixem són uint16 (enters sense signe de 0 a 65535)
    #en uint16, 1000 - 3000 no dona -2000: "dona la volta" i surt 63536
    green = np.array([1000], dtype=np.uint16)
    nir = np.array([3000], dtype=np.uint16)
    result = calculate_ndwi(green, nir)
    #(1000 - 3000) / (1000 + 3000) = -0.5
    assert result[0] == pytest.approx(-0.5)


def test_resultat_entre_menys_u_i_u():
    #amb reflectàncies negatives (no haurien d'existir, però una entrada amb soroll les podria tenir)
    #el resultat podria sortir de [-1, 1], cosa que no té sentit físic
    result = calculate_ndwi(np.array([0.02, 0.05]), np.array([-0.01, 0.40]))
    assert np.all(result >= -1)
    assert np.all(result <= 1)


@pytest.mark.parametrize(
    "forma_green, forma_nir",
    [
        ((2, 2), (3, 3)),  #mides que numpy no pot combinar
        ((2, 2), (1, 2)),  #mides que numpy sí que "estira" (broadcasting) sense avisar
    ],
)
def test_formes_diferents_dona_error(forma_green, forma_nir):
    #si green i nir no tenen la mateixa mida no són la mateixa imatge: ha d'avisar
    with pytest.raises(ValueError):
        calculate_ndwi(np.ones(forma_green), np.ones(forma_nir))
