# v0.6 – Forecasting (Deliverable 2, parts 2 i 3)

Models paramètrics, dinàmica de l'erosió i predicció de la línia de costa de Castelldefels per a gener–juny 2025.

## Com s'executa
1. Descomprimir `time_series/shoreline_distances_csv.zip` dins de `time_series/`.
2. `cd time_series && python holahola.py` → crea la sèrie neta i `selected_transects.csv`.
3. `python forecasting/models_prediccio.py` → models, prediccions i figures a `forecasting/figures/`.

La LSTM fa servir `keras` amb `jax` de motor (tensorflow no funciona amb Python 3.14).

## Què fa `models_prediccio.py`
- **Part 2:** tres models (a) lineal + FFT, (b) lineal + esglaó (Gloria) + FFT, (c) lineal + sigmoide + FFT; comparació, residus, velocitat i acceleració.
- **Part 3:** model A (el millor paramètric) amb interval de confiança del 95 % i PICP; model B (LSTM, finestra de 12 mesos, predicció recursiva i a un pas); validació amb les dades reals de 2025 i taula de mètriques.
