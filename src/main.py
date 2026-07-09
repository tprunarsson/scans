"""
Aðalforritið: les input.json, leysir röðunarlíkanið (Gurobi eða SCIP,
sjá --solver), og skrifar output.json.

Notkun:
  python3 main.py input.json [output.json] [--solver gurobi|scip]

input.json kemur úr Google Sheet vinnuskjalinu ("Sækja gögn", sjá
gas/Export.gs). output.json er lesið aftur inn í sama vinnuskjal ("Hlaða upp
niðurstöðum") sem býr til/yfirskrifar eitt blað per lykil í output.json
(stundatafla, skraningar, mrs_radad_<námskeið> - eitt per námskeið).
"""
import argparse
import json
import importlib
from innlestur import lesa_gogn
from solution_check import check_solution
from utkoma import generate_output

SOLVER_MODULES = {
  'highs': 'model_generator_highs',                    # Sjálfgefið - frjálst, ókeypis, og nálægt Gurobi í hraða (sjá benchmark.py)
  'highs-parallel': 'model_generator_highs_parallel',    # Sama og 'highs' en þvingar samhliða MIP-leit ('parallel'='on')
  'gurobi': 'model_generator',                            # Hraðast, en þarfnast Gurobi-leyfis (sjá gurobi.env)
  'scip': 'model_generator_scip',                          # Frjálst og ókeypis, en mun hægara en hin tvö
}

def build_date_lookup(input_path):
  """Les Lotur beint úr input.json (óháð ModelData) og skilar
  {(námskeið, vika): dagsetning} - notað af utkoma.py til að setja réttar
  dagsetningar í úttakið án þess að reikna þær út frá viku+ártali."""
  with open(input_path, encoding='utf-8') as f:
    data = json.load(f)
  uppfletting = {}
  for row in data.get('Lotur', []):
    namskeid = row.get('namskeid')
    vika = row.get('vika')
    if namskeid is not None and vika is not None:
      uppfletting[(namskeid, vika)] = row.get('dagsetning', '')
  return uppfletting

def json_default(o):
  """Sum gildi frá pandas (t.d. numpy.int64) rata inn í output.json ef upprunadálkur
  hefur enga tóma reiti - þá ályktar pandas hreinan numpy-tölutaga í stað 'object'
  dálks af native Python gildum, sem hið almenna json einingin ræður ekki við beint."""
  if hasattr(o, 'item'):
    return o.item()
  raise TypeError(f'Object of type {o.__class__.__name__} is not JSON serializable')

def write_result(output_path, result):
  with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2, default=json_default)

def parse_args():
  parser = argparse.ArgumentParser(description='Keyrir stundatöflulíkanið út frá input.json og skrifar output.json.')
  parser.add_argument('input_json', help='Slóð á input.json (flutt út úr Google Sheet vinnuskjalinu).')
  parser.add_argument('output_json', nargs='?', default='output.json', help='Slóð fyrir úttaksskjalið (sjálfgefið: output.json).')
  parser.add_argument('--solver', choices=sorted(SOLVER_MODULES), default='highs', help='Hvaða MIP-leysi á að nota (sjálfgefið: highs - frjálst og ókeypis, sjá benchmark.py).')
  return parser.parse_args()

def main():
  args = parse_args()
  input_path = args.input_json
  output_path = args.output_json
  model_module = importlib.import_module(SOLVER_MODULES[args.solver])
  messages = []

  try:
    M, warnings = lesa_gogn(input_path)
    messages += [{'level': 'warning', 'text': w} for w in warnings]
  except Exception as e:
    write_result(output_path, {'status': 'error', 'messages': [{'level': 'error', 'text': str(e)}]})
    print(f'Villa við innlestur - sjá {output_path}.')
    raise SystemExit(1)

  likan, x, mx, deild_min, deild_max = model_module.generate_model(M)
  likan.optimize()

  if not model_module.is_optimal(likan):
    write_result(output_path, {
      'status': 'error',
      'messages': messages + [{'level': 'error', 'text': f'{args.solver} fann ekki bestu lausn.'}],
    })
    print(f'Líkanið fann ekki lausn - sjá {output_path}.')
    raise SystemExit(1)

  date_lookup = build_date_lookup(input_path)
  result = generate_output(M, x, date_lookup)

  solution_warnings = check_solution(x, M)
  messages += [{'level': 'warning', 'text': w} for w in solution_warnings]

  result['status'] = 'success' if not solution_warnings and not warnings else 'warning'
  result['messages'] = messages

  write_result(output_path, result)
  print(f'Skrifaði {output_path}.')

if __name__ == '__main__':
  main()
