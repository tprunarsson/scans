"""Sama líkan og model_generator_highs.py, en þvingar HiGHS til að nota
samhliða (parallel) MIP-leit ('parallel' stillt á 'on') í stað þess að láta
HiGHS ákveða sjálft ('choose', sjálfgefið gildi - sem á þessu líkani velur
oftast EKKI samhliða leit, því forúrvinnslan leysir vandamálið nánast alveg
áður en greinun-og-mörkun (branch-and-bound) þarf að byrja, sjá athugasemd í
src/benchmark.py). Notað til að bera saman í benchmark.py hvort þvinguð
samhliða leit skili raunverulegum ávinningi á þessu líkani eða ekki.

Engin tvítekning á sjálfri líkanasmíðinni - endurnýtir generate_model úr
model_generator_highs.py óbreytt og stillir bara valkostinn áður en líkanið
er skilað til kallanda (sem kallar sjálfur á likan.optimize() á eftir)."""
from model_generator_highs import generate_model as _generate_model, is_optimal  # noqa: F401 (endurflutt fyrir main.py)

def generate_model(M):
  likan, x, mx, deild_min, deild_max = _generate_model(M)
  likan.setOptionValue('parallel', 'on')
  return likan, x, mx, deild_min, deild_max
