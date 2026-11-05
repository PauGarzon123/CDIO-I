# =====================================================================
# models paramètrics, dinàmica de l'erosió i predicció gener–juny 2025
# =====================================================================
# s'executa DESPRÉS de time_series/holahola.py
# (holahola.py crea la sèrie neta i la llista de transectes vàlids a time_series/)

import os
import importlib.util
from pathlib import Path

# tensorflow no funciona amb python 3.14 → si hi ha jax, keras fa servir jax de motor
if importlib.util.find_spec("jax"):
    os.environ.setdefault("KERAS_BACKEND", "jax")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import keras
from scipy.fft import fft, fftfreq
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import MinMaxScaler

# carpeta d'aquest script (forecasting/)
AQUI = Path(__file__).parent
# carpeta amb les dades i els csv que genera holahola.py
DADES = AQUI.parent / "time_series"
# carpeta on es guarden les figures per a l'informe
FIGS = AQUI / "figures"
FIGS.mkdir(exist_ok=True)


def mostra(nom):
    # ajusta marges, guarda la figura en png i la mostra
    plt.tight_layout()
    plt.savefig(FIGS / f"{nom}.png", dpi=150)
    plt.show()


def metriques(real, pred):
    # mae, rmse i r² entre valors reals i predits (en metres)
    return {"MAE": mean_absolute_error(real, pred),
            "RMSE": np.sqrt(mean_squared_error(real, pred)),
            "R2": r2_score(real, pred)}


# ========== PART 2: TRES MODELS PARAMÈTRICS (tendència + FFT) ==========

# sèrie mensual neta 2017–2024 que genera holahola.py
ts = pd.read_csv(DADES / "shoreline_distances_2017_2024_clean.csv", index_col=0, parse_dates=True).iloc[:, 0]
# valors de distància (m)
y = ts.values
# nombre de mesos (96)
n = len(y)
# temps en mesos: 0, 1, ..., n-1
t = np.arange(n)
# temps dels 6 mesos a predir (gener–juny 2025)
t_fut = np.arange(n, n + 6)
# dates dels 6 mesos a predir
dates_fut = pd.date_range("2025-01-01", periods=6, freq="MS")
# mes del temporal gloria (gener 2020) → primer mes després: febrer 2020
t_gloria = ts.index.get_loc(pd.Timestamp("2020-02-01"))
# nombre de freqüències de la fft que conservem
N_FREQ = 5


def sigmoide(tt, k):
    # funció logística: val 0 abans del gloria i 1 després
    # k = velocitat de la transició (k petit → lenta, k gran → com un esglaó)
    return 1 / (1 + np.exp(-k * (tt - t_gloria)))


def base(tt, tipus, k=None):
    # matriu X de la regressió segons el tipus de tendència
    if tipus == "lineal":
        # només el temps: y = a·t + b
        return tt.reshape(-1, 1)
    if tipus == "esglao":
        # temps + esglaó de heaviside: 0 abans del gloria, 1 després
        return np.column_stack([tt, tt >= t_gloria])
    # temps + sigmoide: y = a·t + β·sigmoide(t) + b
    return np.column_stack([tt, sigmoide(tt, k)])


def ajusta(tipus, k=None):
    # 1) tendència amb regressió lineal
    reg = LinearRegression().fit(base(t, tipus, k), y)
    # tendència als mesos coneguts i als 6 futurs
    tend = reg.predict(base(t, tipus, k))
    tend_fut = reg.predict(base(t_fut, tipus, k))
    # 2) fft de la sèrie sense tendència
    F = fft(y - tend)
    # freqüències en cicles/mes
    f = fftfreq(n)
    # magnitud de cada freqüència
    mag = np.abs(F)
    # llindar = magnitud de la N-èsima freqüència positiva més forta
    llindar = np.sort(mag[f > 0])[-N_FREQ]
    # índexs de les freqüències fortes (positives i negatives), sense la freqüència 0
    sel = np.where((mag >= llindar) & (f != 0))[0]

    def cicles(tt):
        # suma de cosinus (amplitud i fase de la fft): val per al passat i per al futur
        return sum(mag[i] / n * np.cos(2 * np.pi * f[i] * tt + np.angle(F[i])) for i in sel)

    # períodes trobats en mesos (només freqüències positives)
    periodes = 1 / f[sel][f[sel] > 0]
    # retornem: ajust, predicció 2025, tendència, períodes i regressió
    return tend + cicles(t), tend_fut + cicles(t_fut), tend, periodes, reg


# provem diverses k per a la sigmoide i ens quedem la de rmse més petit
ks = [0.05, 0.1, 0.2, 0.3, 0.5, 1, 2, 5]
k_millor = min(ks, key=lambda k: metriques(y, ajusta("sigmoide", k)[0])["RMSE"])
print(f"\nMillor k de la sigmoide: {k_millor}")

# ajustem els tres models (a, b, c)
models = {"a) lineal + FFT": ajusta("lineal"),
          "b) lineal + esglaó + FFT": ajusta("esglao"),
          "c) lineal + sigmoide + FFT": ajusta("sigmoide", k_millor)}

# taula de mètriques i figura amb els tres ajustos
taula = {}
fig, eixos = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
for eix, (nom, (recon, _, tend, periodes, reg)) in zip(eixos, models.items()):
    # mètriques de l'ajust
    taula[nom] = metriques(y, recon)
    # residus = real − model
    res = y - recon
    # resum dels residus (mitjana ~0 i desviació petita = bon model)
    print(f"\n{nom}")
    print(f"  pendent: {reg.coef_[0]:.4f} m/mes ({reg.coef_[0] * 12:.2f} m/any)")
    # si el model té gloria, el segon coeficient és la mida del salt (m)
    if len(reg.coef_) > 1:
        print(f"  salt del gloria: {reg.coef_[1]:.2f} m")
    print(f"  períodes (mesos): {np.round(periodes, 1)}")
    print(f"  residus → mitjana {res.mean():.3f}, std {res.std():.3f}, mín {res.min():.2f}, màx {res.max():.2f} m")
    # dibuix: dades, tendència i reconstrucció
    eix.plot(ts.index, y, lw=0.8, alpha=0.6, label="original")
    eix.plot(ts.index, tend, c="C3", label="tendència")
    eix.plot(ts.index, recon, c="C1", label="tendència + FFT")
    eix.axvline(pd.Timestamp("2020-02-01"), c="k", ls="--", lw=0.8)
    eix.set_title(f"{nom}  (R²={taula[nom]['R2']:.3f})")
    eix.set_ylabel("Distància (m)")
    eix.legend(loc="upper left")
    eix.grid(alpha=0.3)
mostra("models_parametrics")

# taula comparativa dels tres models
taula = pd.DataFrame(taula).T
print("\nComparació dels models paramètrics (ajust 2017–2024):")
print(taula.round(3))
# el millor = rmse més petit
millor = taula["RMSE"].idxmin()
print(f"Model escollit: {millor}")

# histograma dels residus del millor model (comprovem si són ~normals per a l'interval de confiança)
recon_m, pred_A, tend_m, _, _ = models[millor]
residus = y - recon_m
plt.figure(figsize=(8, 4))
plt.hist(residus, bins=20)
plt.title(f"Residus del model {millor}")
plt.xlabel("Residu (m)")
plt.ylabel("Freqüència")
mostra("residus_histograma")


# ========== DINÀMICA DE L'EROSIÓ: VELOCITAT I ACCELERACIÓ ==========
# el gloria va fer retrocedir la costa i el salt surt positiu
# → distància que creix = erosió (retrocés), distància que baixa = acreció

# velocitat = 1a derivada (m/mes) → ×12 = m/any
vel = np.gradient(recon_m) * 12
# acceleració = 2a derivada (m/mes²) → ×144 = m/any²
acc = np.gradient(np.gradient(recon_m)) * 144

fig, eixos = plt.subplots(3, 1, figsize=(12, 9), sharex=True)
# distància i model
eixos[0].plot(ts.index, y, lw=0.8, alpha=0.6, label="original")
eixos[0].plot(ts.index, recon_m, c="C1", label=millor)
eixos[0].set_ylabel("Distància (m)")
eixos[0].legend()
# velocitat: pintem en vermell erosió (v>0) i en blau acreció (v<0)
eixos[1].plot(ts.index, vel, c="k", lw=1)
eixos[1].fill_between(ts.index, vel, 0, where=vel > 0, color="C3", alpha=0.4, label="erosió")
eixos[1].fill_between(ts.index, vel, 0, where=vel < 0, color="C0", alpha=0.4, label="acreció")
eixos[1].set_ylabel("Velocitat (m/any)")
eixos[1].legend()
# acceleració: >0 la distància creix cada cop més de pressa
eixos[2].plot(ts.index, acc, c="C2")
eixos[2].axhline(0, c="k", lw=0.8)
eixos[2].set_ylabel("Acceleració (m/any²)")
for eix in eixos:
    eix.grid(alpha=0.3)
eixos[0].set_title("Dinàmica de la línia de costa")
mostra("velocitat_acceleracio")

# mitjana anual de velocitat i acceleració (per veure si l'erosió s'accelera o frena)
dinamica = pd.DataFrame({"velocitat (m/any)": vel, "acceleració (m/any²)": acc}, index=ts.index)
print("\nMitjana anual de la dinàmica:")
print(dinamica.groupby(dinamica.index.year).mean().round(2))
# velocitat mitjana de la tendència abans i després del gloria
print(f"Velocitat mitjana abans del gloria: {vel[:t_gloria].mean():.2f} m/any")
print(f"Velocitat mitjana després del gloria: {vel[t_gloria + 1:].mean():.2f} m/any")


# ========== PART 3: DADES REALS GENER–JUNY 2025 ==========
# les netegem igual que 2017–2024: mateixos transectes, iqr i filtre de dates

# transectes vàlids guardats per holahola.py
transectes = pd.read_csv(DADES / "selected_transects.csv")["transect_id"]
# dades de 2025
d25 = pd.read_csv(DADES / "shoreline_distances_h1_2025.csv", parse_dates=["date"])
# taula data × transecte, només amb els transectes vàlids
p25 = d25.pivot_table(index="date", columns="transect_id", values="distance_m")[transectes]
# quartils de cada transecte
q1, q3 = p25.quantile(0.25), p25.quantile(0.75)
# outliers fora de [q1 − 1.5·iqr, q3 + 1.5·iqr] → nan
p25 = p25.where((p25 >= q1 - 1.5 * (q3 - q1)) & (p25 <= q3 + 1.5 * (q3 - q1)))
# traiem dates amb més d'un 40 % de nan (com a holahola.py)
p25 = p25[p25.isna().mean(axis=1) <= 0.40]
# mitjana entre transectes → mitjana mensual → interpolem si falta algun mes
obs = p25.mean(axis=1).resample("MS").mean().interpolate().values
print("\nObservat gener–juny 2025 (m):", np.round(obs, 2))


# ========== MODEL A: PARAMÈTRIC + INTERVAL DE CONFIANÇA 95 % ==========

# desviació dels residus del model
sigma = residus.std()
# horitzó de predicció: 1, 2, ..., 6 mesos
h = np.arange(1, 7)
# marge de l'interval: creix amb l'horitzó (ŷ ± 1.96·σ·√(1 + h/n))
marge = 1.96 * sigma * np.sqrt(1 + h / n)
# picp = fracció de valors reals que cauen dins l'interval
picp = np.mean((obs >= pred_A - marge) & (obs <= pred_A + marge))
print(f"\nModel A ({millor})")
print(f"  σ residus: {sigma:.3f} m, PICP: {picp * 100:.0f} %")
for d, p, m, o in zip(dates_fut, pred_A, marge, obs):
    print(f"  {d:%Y-%m}: predit {p:6.2f} m [{p - m:6.2f}, {p + m:6.2f}]  observat {o:6.2f} m")


# ========== MODEL B: LSTM ==========

# llavor fixa → resultats reproduïbles
keras.utils.set_random_seed(42)
# finestra: el model mira 12 mesos enrere per predir el següent
FINESTRA = 12
# normalitzem a [0, 1] amb l'escalador ajustat NOMÉS amb l'entrenament (2017–2024)
esc = MinMaxScaler()
y_esc = esc.fit_transform(y.reshape(-1, 1))


def finestres(dades):
    # finestra lliscant: x = 12 mesos seguits, y = el mes següent
    X = np.array([dades[i:i + FINESTRA] for i in range(len(dades) - FINESTRA)])
    Y = np.array([dades[i + FINESTRA] for i in range(len(dades) - FINESTRA)])
    return X, Y


# parelles d'entrenament (84 finestres)
X_tr, Y_tr = finestres(y_esc)
# xarxa: entrada (12, 1) → lstm de 64 unitats → 1 neurona de sortida
model = keras.Sequential([keras.Input((FINESTRA, 1)),
                          keras.layers.LSTM(64),
                          keras.layers.Dense(1)])
# optimitzador adam i error quadràtic mitjà
model.compile(optimizer="adam", loss="mse")
# entrenem 300 èpoques; el 20 % final (2023–2024) només es fa servir per vigilar la validació
# (amb earlystopping la xarxa es parava massa aviat i quedava infraajustada: r² ≈ 0.4)
hist = model.fit(X_tr, Y_tr, epochs=300, batch_size=8, validation_split=0.2, verbose=0)
print(f"\nLSTM entrenada durant {len(hist.history['loss'])} èpoques")

# corba d'aprenentatge: si val_loss puja mentre loss baixa → sobreajust
plt.figure(figsize=(8, 4))
plt.plot(hist.history["loss"], label="entrenament")
plt.plot(hist.history["val_loss"], label="validació")
plt.title("Corba d'aprenentatge de la LSTM")
plt.xlabel("Època")
plt.ylabel("MSE (normalitzat)")
plt.legend()
plt.grid(alpha=0.3)
mostra("lstm_aprenentatge")

# ajust de la lstm a l'entrenament (desnormalitzat a metres)
ajust_B = esc.inverse_transform(model.predict(X_tr, verbose=0)).ravel()

# predicció recursiva: cada mes predit entra a la finestra per predir el següent
# (no veu cap dada de 2025 → comparació justa amb el model A)
fin = y_esc[-FINESTRA:].ravel()
pred = []
for _ in range(6):
    # predim el mes següent
    seg = model.predict(fin.reshape(1, FINESTRA, 1), verbose=0)[0, 0]
    pred.append(seg)
    # desplacem la finestra: traiem el mes més antic i afegim el predit
    fin = np.append(fin[1:], seg)
# tornem a metres
pred_B = esc.inverse_transform(np.array(pred).reshape(-1, 1)).ravel()

# predicció a un pas: cada mes es prediu amb els 12 mesos REALS anteriors (inclou 2025)
dades = np.concatenate([y_esc, esc.transform(obs.reshape(-1, 1))])
X_te, _ = finestres(dades[-(FINESTRA + 6):])
pred_B1 = esc.inverse_transform(model.predict(X_te, verbose=0)).ravel()


# ========== AVALUACIÓ I COMPARACIÓ ==========

# figura final: històric + predicció + observat 2025
plt.figure(figsize=(13, 5))
plt.plot(ts.index, y, c="C0", lw=0.8, label="històric 2017–2024")
plt.plot(dates_fut, obs, "ko-", label="observat gen–jun 2025")
plt.plot(dates_fut, pred_A, "s-", c="C1", label=f"model A: {millor}")
plt.fill_between(dates_fut, pred_A - marge, pred_A + marge, color="C1", alpha=0.2, label="IC 95 % model A")
plt.plot(dates_fut, pred_B, "^-", c="C2", label="model B: LSTM recursiva")
plt.plot(dates_fut, pred_B1, "v--", c="C2", alpha=0.6, label="model B: LSTM a un pas")
plt.title("Predicció de la línia de costa de Castelldefels (gener–juny 2025)")
plt.ylabel("Distància (m)")
plt.legend(loc="upper left", fontsize=8)
plt.grid(alpha=0.3)
mostra("prediccio_2025")

# detall dels dos últims anys + 2025
plt.figure(figsize=(10, 5))
plt.plot(ts.index[-24:], y[-24:], c="C0", lw=1, label="històric")
plt.plot(dates_fut, obs, "ko-", label="observat 2025")
plt.plot(dates_fut, pred_A, "s-", c="C1", label="model A")
plt.fill_between(dates_fut, pred_A - marge, pred_A + marge, color="C1", alpha=0.2, label="IC 95 %")
plt.plot(dates_fut, pred_B, "^-", c="C2", label="LSTM recursiva")
plt.plot(dates_fut, pred_B1, "v--", c="C2", alpha=0.6, label="LSTM a un pas")
plt.title("Detall 2023–2025")
plt.ylabel("Distància (m)")
plt.legend(fontsize=8)
plt.grid(alpha=0.3)
mostra("prediccio_2025_detall")

# taula final: mètriques d'entrenament (optimistes) i de test 2025 (realistes)
final = pd.DataFrame({
    "A entrenament": metriques(y, recon_m),
    "A test 2025": metriques(obs, pred_A),
    "LSTM entrenament": metriques(y[FINESTRA:], ajust_B),
    "LSTM test recursiva": metriques(obs, pred_B),
    "LSTM test a un pas": metriques(obs, pred_B1),
}).T
print("\nMètriques finals (m):")
print(final.round(3))
# es guarda per copiar-la a l'informe
final.round(3).to_csv(FIGS / "metriques_finals.csv")

# comprovació de sobreajust: si r² entrenament − r² test > 0.1 → possible sobreajust
# ull: el 2025 només té 6 mesos i varia poc (10–14 m) → el r² de test surt negatiu
# encara que l'error sigui petit; per al test cal mirar sobretot mae i rmse
for nom, tr, te in [("A", "A entrenament", "A test 2025"), ("LSTM", "LSTM entrenament", "LSTM test recursiva")]:
    dif = final.loc[tr, "R2"] - final.loc[te, "R2"]
    print(f"{nom}: R² entrenament − R² test = {dif:.3f} → {'possible sobreajust' if dif > 0.1 else 'sense sobreajust clar'}")
