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


#valors que falten: NaN, None o infinit a qualsevol de les dues bandes -> el píxel queda NaN
@pytest.mark.parametrize(
    "green, nir",
    [
        (np.nan, 0.10),  #falta green
        (0.10, np.nan),  #falta nir
        (np.nan, np.nan),  #falten les dues
        (None, 0.10),  #None (ex: una llista de Python amb forats) -> numpy el passa a NaN
        (np.inf, 0.10),  #infinit a green: inf / inf no té valor
        (0.10, -np.inf),  #infinit negatiu a nir
        (np.inf, np.inf),  #inf - inf tampoc té valor
    ],
)
def test_valors_que_falten_donen_nan(green, nir):
    result = calculate_ndwi([green], [nir])
    assert np.isnan(result[0])


#totes les maneres d'arribar a un denominador 0 (o negatiu)
@pytest.mark.parametrize(
    "green, nir",
    [
        (0.0, 0.0),  #0/0 amb decimals
        (np.uint16(0), np.uint16(0)),  #0/0 amb enters, com el nodata dels GeoTIFF
        (-0.01, 0.0),  #el negatiu es posa a 0 -> torna a ser 0/0
        (-0.01, -0.02),  #tots dos negatius -> 0/0
    ],
)
def test_denominador_zero_dona_nan(green, nir):
    result = calculate_ndwi(np.array([green]), np.array([nir]))
    assert np.isnan(result[0])


def test_un_forat_no_espatlla_els_veins():
    #un píxel sense dada al mig de la imatge no ha d'afectar els del costat
    green = np.array([[0.08, np.nan, 0.10]])
    nir = np.array([[0.02, 0.40, 0.0]])
    result = calculate_ndwi(green, nir)
    assert np.isnan(result[0, 1])
    assert result[0, 0] == pytest.approx(0.6)
    assert result[0, 2] == pytest.approx(1.0)


def test_matriu_buida():
    #un retall buit (polígon fora de la imatge) ha de donar una matriu buida, no un error
    result = calculate_ndwi(np.array([]), np.array([]))
    assert result.shape == (0,)


# --- Tests de regressió: el resultat no pot canviar amb el temps ---
#si algú modifica calculate_ndwi i el resultat canvia, aquests tests ho detecten

#valors "congelats": entrada uint16 com la dels GeoTIFF i el resultat que ha de sortir sempre
@pytest.mark.parametrize(
    "green, nir, expected",
    [
        (766, 54, 712 / 820),  #(766 - 54) / (766 + 54): mar de la imatge del 30-06-2025
        (2758, 3348, -590 / 6106),  #(2758 - 3348) / (2758 + 3348): sorra de la mateixa imatge
        (1000, 3000, -0.5),  #nir > green: la resta seria negativa en uint16
        (65535, 0, 1.0),  #valor màxim de uint16
        (0, 0, np.nan),  #nodata
    ],
)
def test_regressio_valors_fixos(green, nir, expected):
    result = calculate_ndwi(np.array([green], dtype=np.uint16), np.array([nir], dtype=np.uint16))
    #equal_nan=True: NaN == NaN compta com a igual (normalment NaN no és igual a res)
    np.testing.assert_allclose(result, [expected], rtol=1e-12, equal_nan=True)


def test_regressio_imatge_real():
    #green i nir reals (retall del 30-06-2025, 19 x 476 píxels) i el NDWI que donava la funció
    #quan es va crear el fitxer; el resultat d'avui ha de ser el mateix
    dades = np.load(REFERENCIA)
    result = calculate_ndwi(dades["green"], dades["nir"])
    assert result.shape == dades["ndwi"].shape
    #mateixos NaN als mateixos llocs i mateixos valors a la resta
    np.testing.assert_allclose(result, dades["ndwi"], rtol=1e-12, equal_nan=True)


def test_no_modifica_les_entrades():
    #la funció no ha de canviar les bandes que li passem (les podríem fer servir després)
    green = np.array([-0.01, 0.08, np.nan])
    nir = np.array([0.02, 0.02, 0.10])
    copia_green, copia_nir = green.copy(), nir.copy()
    calculate_ndwi(green, nir)
    np.testing.assert_array_equal(green, copia_green)
    np.testing.assert_array_equal(nir, copia_nir)
