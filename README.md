# CDIO-I,
Grup de l'assignatura CDIO I format per : Pau Garzon, Alex Tong, Guillem Ribas,Sebastian Simo.

## Tasques

- [Tasca 2 — Descàrrega eficient d'imatges Sentinel-2](Tasca2/README.md)


##
git config --global user.email "you@example.com"
git config --global user.name "Your Name"
git merge origin/Tasca-1-branca

## Entorn virtual: 
python3 -m venv .venv
source .venv/bin/activate
Descarregar libs: pip install -r requirements.txt

## Estimate the coastline:
cd bdse-cdio1/coastline_estimator
python coastline_estimator/extract_shorelines.py -p /home/cbltic/Documents/CDIO-I/Tasca3

## Estimate erosion:
cd bdse-cdio1/coastline_estimator
python coastline_estimator/calculate_erosion.py -p /home/cbltic/Documents/CDIO-I/Tasca3
python coastline_estimator/analyze.py -p /home/cbltic/Documents/CDIO-I/Tasca3

