"""
Greinir hvers vegna líkan er óstuðlanlegt (infeasible) með Gurobi's
computeIIS() - finnur minnsta mengi skorða sem eru saman óstuðlanlegar
(Irreducible Inconsistent Subsystem). Notar alltaf Gurobi óháð því hvaða
leysir er sjálfgefinn í main.py - hvorki SCIP né HiGHS bjóða upp á
sambærilega greiningu, og þarfnast því ekki --solver val hér.

Skorður eru nefndar skýrt í model_generator.py (t.d. "c5_fri_skilyrt_...")
einmitt svo úttakið hér sé læsilegt, ekki bara sjálfvirk Gurobi-nöfn eins og
"R1523".

Keyra: python3 iis_greining.py <input.json> [utskjal.ilp]
"""
import sys
import gurobipy as gp
from innlestur import lesa_gogn
from model_generator import generate_model, is_optimal

# Verða að passa nákvæmlega við nafnaforskeytin sem eru notuð í model_generator.py
THEKKT_FORSKEYTI = [
  'c1_skraning_', 'c2_plass_', 'c3_skorun_', 'c4_val_skorun_',
  'c5_fri_skilyrt_', 'c6_akvedin_rodun_',
]


def flokkur_fyrir(nafn):
  for forskeyti in THEKKT_FORSKEYTI:
    if nafn.startswith(forskeyti):
      return forskeyti.rstrip('_')
  return 'óþekkt'


def main():
  if len(sys.argv) < 2:
    print('Notkun: python3 iis_greining.py <input.json> [utskjal.ilp]')
    sys.exit(1)

  input_json = sys.argv[1]
  ilp_utskjal = sys.argv[2] if len(sys.argv) > 2 else 'iis.ilp'

  M, warnings = lesa_gogn(input_json)
  likan, x, mx, deild_min, deild_max = generate_model(M)
  likan.optimize()

  if is_optimal(likan):
    print('Líkanið er stuðlanlegt (fann bestu lausn) - engin IIS greining nauðsynleg.')
    return

  if likan.Status not in (gp.GRB.INFEASIBLE, gp.GRB.INF_OR_UNBD):
    print(f'Líkanið er hvorki stuðlanlegt né staðfest óstuðlanlegt (staða {likan.Status}) - IIS greining ekki möguleg.')
    return

  print('Líkanið er óstuðlanlegt - reikna IIS (minnsta mengi skorða sem stangast á)...')
  likan.computeIIS()
  likan.write(ilp_utskjal)
  print(f'Full IIS skrifað í {ilp_utskjal} (Gurobi LP-snið).\n')

  flokkar = {}
  for c in likan.getConstrs():
    if c.IISConstr:
      flokkar.setdefault(flokkur_fyrir(c.ConstrName), []).append(c.ConstrName)

  if not flokkar:
    print('Engar nafngreindar skorður fundust í IIS (óvænt - athugaðu ilp skjalið handvirkt).')
  else:
    print(f'Skorður í IIS ({sum(len(v) for v in flokkar.values())} samtals), flokkaðar eftir tegund:')
    for flokkur, nofn in sorted(flokkar.items()):
      print(f'\n{flokkur} ({len(nofn)} skorður):')
      for n in nofn:
        print(f'  - {n}')

  mork_i_iis = [v.VarName for v in likan.getVars() if v.IISLB or v.IISUB]
  if mork_i_iis:
    print(f'\nBreytu-mörk í IIS ({len(mork_i_iis)}):')
    for n in mork_i_iis:
      print(f'  - {n}')


if __name__ == '__main__':
  main()
