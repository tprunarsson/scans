"""
Ber saman þá MIP-leysa sem eru tiltækir (Gurobi/SCIP/HiGHS) á sama input.json:
tíma sem fer í að byggja upp líkanið í Python (uppbygging), tíma sem leysirinn
sjálfur notar (lausn), og hvort báðir/allir leysar finni sömu bestu lausn
(hlutlægisgildi) - það er sjálfstæð staðfesting þess að þýðingin á milli
leysanna í model_generator*.py sé rétt, óháð hraðamun þeirra.

Notkun:
  python3 benchmark.py [input.json] [--solvers gurobi,scip,highs]

Sjálfgefið: input.json = ../data/t0/input.json, allir leysar sem finnast.
"""
import sys
import time
import argparse
import importlib
from innlestur import lesa_gogn
from main import SOLVER_MODULES

def parse_args():
  parser = argparse.ArgumentParser(description='Ber saman leysa (Gurobi/SCIP/HiGHS) á sama input.json.')
  parser.add_argument('input_json', nargs='?', default='../data/t0/input.json', help='Slóð á input.json (sjálfgefið: ../data/t0/input.json).')
  parser.add_argument('--solvers', default=','.join(sorted(SOLVER_MODULES)), help='Kommulisti leysa til að keyra (sjálfgefið: allir í main.SOLVER_MODULES).')
  return parser.parse_args()

def keyra_leysi(nafn, einingarnafn, M):
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

  try:
    likan.optimize()
  except Exception as e:
    return {'leysir': nafn, 'villa': f'villa við lausn: {e}'}
  t2 = time.perf_counter()

  optimal = eining.is_optimal(likan)
  hlutlaegi = None
  if optimal:
    # x[hvaða sem er].X er sama tala óháð leysi (sjá ScipVar/HighsVar í hverri einingu)
    einhver_lykill = next(iter(x))
    hlutlaegi = objective_value(likan, einingarnafn)

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
  á ólíkum stað (Gurobi: likan.ObjVal, SCIP: getObjVal(), HiGHS: úr info)."""
  if einingarnafn == 'model_generator':
    return likan.ObjVal
  if einingarnafn == 'model_generator_scip':
    return likan.getObjVal()
  if einingarnafn == 'model_generator_highs':
    return likan.getObjectiveValue()
  return None

def main():
  args = parse_args()
  solver_nofn = [s.strip() for s in args.solvers.split(',') if s.strip()]

  print(f'Les {args.input_json}...')
  M, warnings = lesa_gogn(args.input_json)
  print(f'{len(M.nemendur)} nemendur, {len(M.klinik)} námskeið, {len(warnings)} aðvaranir við innlestur.\n')

  nidurstodur = []
  for nafn in solver_nofn:
    if nafn not in SOLVER_MODULES:
      print(f'Óþekktur leysir: {nafn} (þekktir: {", ".join(sorted(SOLVER_MODULES))})')
      continue
    print(f'--- {nafn} ---')
    r = keyra_leysi(nafn, SOLVER_MODULES[nafn], M)
    nidurstodur.append(r)
    if 'villa' in r:
      print(f'  {r["villa"]}\n')
    else:
      print(f'  uppbygging: {r["uppbygging_s"]:.2f}s, lausn: {r["lausn_s"]:.2f}s, samtals: {r["samtals_s"]:.2f}s')
      print(f'  besta lausn fundin: {r["bestalausn"]}, hlutlægisgildi: {r["hlutlaegisgildi"]}\n')

  prenta_samantekt(nidurstodur)

def prenta_samantekt(nidurstodur):
  print('=' * 78)
  print(f'{"Leysir":<10} {"Uppbygging":>12} {"Lausn":>10} {"Samtals":>10} {"Hlutlægisgildi":>18}')
  print('-' * 78)
  for r in nidurstodur:
    if 'villa' in r:
      print(f'{r["leysir"]:<10} {r["villa"]}')
      continue
    print(f'{r["leysir"]:<10} {r["uppbygging_s"]:>11.2f}s {r["lausn_s"]:>9.2f}s {r["samtals_s"]:>9.2f}s {r["hlutlaegisgildi"]:>18.2f}')
  print('=' * 78)

  gild = [r for r in nidurstodur if 'villa' not in r and r['bestalausn']]
  if len(gild) > 1:
    gildi = {round(r['hlutlaegisgildi'], 2) for r in gild}
    if len(gildi) == 1:
      print('Allir leysar fundu sama hlutlægisgildi - líkönin eru samhljóða.')
    else:
      print(f'VIÐVÖRUN: leysar skiluðu ólíkum hlutlægisgildum: {gildi}')

if __name__ == '__main__':
  main()
