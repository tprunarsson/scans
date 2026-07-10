"""
Ber saman þá MIP-leysa sem eru tiltækir (Gurobi/SCIP/HiGHS) á einu eða fleiri
input.json gagnasöfnum: tíma sem fer í að byggja upp líkanið í Python
(uppbygging), tíma sem leysirinn sjálfur notar (lausn), og hvort allir leysar
finni sömu bestu lausn (hlutlægisgildi) - það er sjálfstæð staðfesting þess
að þýðingin á milli leysanna í model_generator*.py sé rétt, óháð hraðamun
þeirra.

Notkun:
  python3 benchmark.py [input.json ...] [--solvers gurobi,scip,highs] [--time-limit SEK]

Sjálfgefið: input.json = ../data/example_input.json, allir leysar sem finnast,
engin tímamörk. Með fleiri en einu input.json er keyrt í gegnum hvert
gagnasafn fyrir sig og að lokum prentuð ein samantektartafla þvert á öll
gagnasöfnin, til að bera saman hvernig leysar skala eftir því sem líkönin
stækka.

Ábending: SCIP er umtalsvert hægari en HiGHS/Gurobi (sjá README.md), og á
stórum gagnasöfnum getur það lent í "numerical troubles" og hangið án þess
að skila neinu (staðfest á docs/3year - keyrsla var drepin eftir >30mín án
framfara). --time-limit 180 (t.d.) kemur í veg fyrir þetta - leysir sem nær
ekki að sanna bestu lausn fyrir tímamörk skilar samt bestu lausn sem fannst
(merkt "ekki staðfest") í stað þess að hanga endalaust.
"""
import os
import time
import math
import argparse
import importlib
from innlestur import lesa_gogn
from main import SOLVER_MODULES

def parse_args():
  parser = argparse.ArgumentParser(description='Ber saman leysa (Gurobi/SCIP/HiGHS) á einu eða fleiri input.json gagnasöfnum.')
  parser.add_argument('input_json', nargs='*', default=['../data/example_input.json'], help='Slóð(ir) á input.json (sjálfgefið: ../data/example_input.json).')
  parser.add_argument('--solvers', default=','.join(sorted(SOLVER_MODULES)), help='Kommulisti leysa til að keyra (sjálfgefið: allir í main.SOLVER_MODULES).')
  parser.add_argument('--time-limit', type=float, default=None, help='Hámarks lausnartími í sekúndum per leysi (sjálfgefið: engin tímamörk).')
  return parser.parse_args()

def setja_timamork(likan, einingarnafn, sekundur):
  """Setur tímamörk á leysinn áður en likan.optimize() er kallað - hver leysir
  hefur sína eigin færibreytu fyrir þetta."""
  if sekundur is None:
    return
  if einingarnafn == 'model_generator':
    likan.setParam('TimeLimit', sekundur)
  elif einingarnafn == 'model_generator_scip':
    likan.setParam('limits/time', sekundur)
  elif einingarnafn.startswith('model_generator_highs'):
    likan.setOptionValue('time_limit', sekundur)

def gagnasafn_heiti(slod):
  """Læsilegt heiti fyrir gagnasafn í töflum - notar nafn möppunnar sem
  input.json liggur í (t.d. "1year" fyrir docs/1year/input.json), eða slóðina
  sjálfa ef mappan gefur ekkert til kynna."""
  mappa = os.path.basename(os.path.dirname(os.path.abspath(slod)))
  return mappa or slod

def keyra_leysi(nafn, einingarnafn, M, timamork=None):
  """Byggir upp og leysir líkanið með einum leysi. Skilar dict með tímum og
  niðurstöðu, eða dict með 'villa' ef leysirinn er ekki uppsettur/mistekst."""
  try:
    eining = importlib.import_module(einingarnafn)
  except ImportError as e:
    return {'leysir': nafn, 'villa': f'ekki uppsettur ({e})'}

  t0 = time.perf_counter()
  try:
    likan, x, mx, deild_min, deild_max = eining.generate_model(M)
  except Exception as e:
    return {'leysir': nafn, 'villa': f'villa við uppbyggingu líkans: {e}'}
  t1 = time.perf_counter()

  setja_timamork(likan, einingarnafn, timamork)

  try:
    likan.optimize()
  except Exception as e:
    return {'leysir': nafn, 'villa': f'villa við lausn: {e}'}
  t2 = time.perf_counter()

  optimal = eining.is_optimal(likan)
  try:
    # Ef tímamörk náðust áður en leysirinn kláraði, er oft samt til besta lausn
    # sem fannst - reynum að ná í hana þó hún sé ekki staðfest best, í stað
    # þess að skila engu.
    hlutlaegi = objective_value(likan, einingarnafn)
  except Exception:
    hlutlaegi = None

  return {
    'leysir': nafn,
    'uppbygging_s': t1 - t0,
    'lausn_s': t2 - t1,
    'samtals_s': t2 - t0,
    'bestalausn': optimal,
    'hlutlaegisgildi': hlutlaegi,
  }

def objective_value(likan, einingarnafn):
  """Hlutlægisgildi lesið á sama hátt óháð leysi - hver leysir geymir það
  á ólíkum stað (Gurobi: likan.ObjVal, SCIP: getObjVal(), HiGHS: úr info).
  Skilar None ef engin lausn er til (t.d. tímamörk náðust áður en fyrsta
  gild lausn fannst) - HiGHS skilar +-inf frekar en að kasta villu í því
  tilviki, svo það er sérstaklega athugað hér."""
  if einingarnafn == 'model_generator':
    gildi = likan.ObjVal
  elif einingarnafn == 'model_generator_scip':
    gildi = likan.getObjVal()
  elif einingarnafn.startswith('model_generator_highs'):  # nær bæði 'highs' og 'highs_parallel'
    gildi = likan.getObjectiveValue()
  else:
    return None
  return None if math.isinf(gildi) else gildi

def keyra_gagnasafn(slod, solver_nofn, timamork=None):
  print(f'\n################################################################')
  print(f'### {gagnasafn_heiti(slod)}  ({slod})')
  print(f'################################################################')
  print(f'Les {slod}...')
  M, warnings = lesa_gogn(slod)
  print(f'{len(M.nemendur)} nemendur, {len(M.klinik)} námskeið, {len(warnings)} aðvaranir við innlestur.\n')

  nidurstodur = []
  for nafn in solver_nofn:
    if nafn not in SOLVER_MODULES:
      print(f'Óþekktur leysir: {nafn} (þekktir: {", ".join(sorted(SOLVER_MODULES))})')
      continue
    print(f'--- {nafn} ---')
    r = keyra_leysi(nafn, SOLVER_MODULES[nafn], M, timamork)
    r['gagnasafn'] = gagnasafn_heiti(slod)
    nidurstodur.append(r)
    if 'villa' in r:
      print(f'  {r["villa"]}\n')
    else:
      stada = 'staðfest best' if r['bestalausn'] else 'EKKI staðfest best (líklega tímamörk náð)'
      print(f'  uppbygging: {r["uppbygging_s"]:.2f}s, lausn: {r["lausn_s"]:.2f}s, samtals: {r["samtals_s"]:.2f}s')
      print(f'  {stada}, hlutlægisgildi: {r["hlutlaegisgildi"]}\n')

  prenta_samantekt(nidurstodur, f'Samantekt - {gagnasafn_heiti(slod)}')
  return nidurstodur

def main():
  args = parse_args()
  solver_nofn = [s.strip() for s in args.solvers.split(',') if s.strip()]
  if args.time_limit:
    print(f'Tímamörk: {args.time_limit}s per leysi.\n')

  allar_nidurstodur = []
  for slod in args.input_json:
    allar_nidurstodur += keyra_gagnasafn(slod, solver_nofn, args.time_limit)

  if len(args.input_json) > 1:
    prenta_samantekt(allar_nidurstodur, 'Samantekt - öll gagnasöfn', med_gagnasafn=True)

def prenta_samantekt(nidurstodur, titill, med_gagnasafn=False):
  breidd_leysir = max(16, max((len(r['leysir']) for r in nidurstodur), default=0) + 1)
  breidd_gagnasafn = max(12, max((len(r['gagnasafn']) for r in nidurstodur), default=0) + 1) if med_gagnasafn else 0
  linubreidd = breidd_leysir + breidd_gagnasafn + 66

  print(f'\n{titill}')
  print('=' * linubreidd)
  haus = f'{"Gagnasafn":<{breidd_gagnasafn}} ' if med_gagnasafn else ''
  print(f'{haus}{"Leysir":<{breidd_leysir}} {"Uppbygging":>12} {"Lausn":>10} {"Samtals":>10} {"Hlutlægisgildi":>18}')
  print('-' * linubreidd)
  for r in nidurstodur:
    forskeyti = f'{r["gagnasafn"]:<{breidd_gagnasafn}} ' if med_gagnasafn else ''
    if 'villa' in r:
      print(f'{forskeyti}{r["leysir"]:<{breidd_leysir}} {r["villa"]}')
      continue
    if r['hlutlaegisgildi'] is None:
      hlutlaegi = f'{"(óleysanlegt)":>18}'
    elif r['bestalausn']:
      hlutlaegi = f'{r["hlutlaegisgildi"]:>18.2f}'
    else:
      hlutlaegi = f'{r["hlutlaegisgildi"]:>15.2f} (?)'  # ekki staðfest best - t.d. tímamörk náð
    print(f'{forskeyti}{r["leysir"]:<{breidd_leysir}} {r["uppbygging_s"]:>11.2f}s {r["lausn_s"]:>9.2f}s {r["samtals_s"]:>9.2f}s {hlutlaegi}')
  print('=' * linubreidd)

  if med_gagnasafn:
    return  # hlutlægisgildi ólíkra gagnasafna eru ekki samanburðarhæf

  gild = [r for r in nidurstodur if 'villa' not in r and r['bestalausn']]
  if len(gild) > 1:
    gildi = {round(r['hlutlaegisgildi'], 2) for r in gild}
    if len(gildi) == 1:
      print('Allir leysar fundu sama hlutlægisgildi - líkönin eru samhljóða.')
    else:
      print(f'VIÐVÖRUN: leysar skiluðu ólíkum hlutlægisgildum: {gildi}')

if __name__ == '__main__':
  main()
