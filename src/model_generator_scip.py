"""Sama líkan og model_generator.py (Gurobi), en leyst með SCIP (frjáls og
ókeypis, engs leyfis þörf) í gegnum pyscipopt. `main.py --solver scip` velur
þessa útgáfu. Sama s/c/v/d vísanakerfi og í model_generator.py.

Uppbygging líkansins hér er höfð eins nálægt model_generator.py og hægt er,
línu fyrir línu, svo auðvelt sé að bera þær tvær saman. Munurinn er eingöngu
tæknilegur: pyscipopt hefur ekki `addVars`/`addConstrs` (margar breytur/skorður
í einu, eins og gurobipy), svo þær eru byggðar upp með handvirkum lykkjum í
staðinn, og lausnargildi eru lesin með `model.getVal(var)` í stað `.X` -
ScipVar hér að neðan brúar þann mun svo solution_check.py og utkoma.py þurfi
ekki að vita hvorn leysinn var notaður."""
from pyscipopt import Model, quicksum
from postur import Postur
from vikur import Vikur

class ScipVar:
  """Lætur SCIP breytu haga sér eins og gurobipy breytu (`.X`) fyrir kóðann
  sem les lausnina. `.X` er reiknað þegar á það er kallað (ekki við smíði),
  svo þetta virkar óháð því hvenær `likan.optimize()` er keyrt af kallanda."""
  __slots__ = ('_model', '_var')

  def __init__(self, model, var):
    self._model = model
    self._var = var

  @property
  def X(self):
    return self._model.getVal(self._var)

def is_optimal(likan):
  """True ef SCIP fann sannaða bestu lausn."""
  return likan.getStatus() == 'optimal'

def generate_model(M):
  postur = Postur()
  V = Vikur()
  sym_vikur = V.sym

  likan = Model('likan')

  raw_x = {}
  x = {}
  i = 0
  for s in M.nemendur:
    for c in M.klinik:
      for v in M.klinik[c]:
        for d in M.klinik[c][v]:
          var = likan.addVar(vtype='B', name=f'x{i}')
          raw_x[s, c, v, d] = var
          x[s, c, v, d] = ScipVar(likan, var)
          i += 1

  raw_mx = {}
  mx = {}
  for i, c in enumerate(M.klinik):
    var = likan.addVar(vtype='C', name=f'mx{i}')
    raw_mx[c] = var
    mx[c] = ScipVar(likan, var)

  raw_deild_min = {}
  deild_min = {}
  raw_deild_max = {}
  deild_max = {}
  i = 0
  for c in M.klinik:
    for v in M.klinik[c]:
      var_min = likan.addVar(vtype='C', name=f'dmin{i}')
      var_max = likan.addVar(vtype='C', name=f'dmax{i}')
      raw_deild_min[c, v] = var_min
      deild_min[c, v] = ScipVar(likan, var_min)
      raw_deild_max[c, v] = var_max
      deild_max[c, v] = ScipVar(likan, var_max)
      i += 1

  vigt_rada_jafnt = 10**2
  vigt_postnumer = 10
  vigt_klara_snemma = 10**6
  vigt_klara_snemma_serstakt = 10**6
  vigt_serstakur_stadur = 10**4
  vigt_auka_vikur = 10**7
  vigt_serstakar_deildir = 10**5
  vigt_fri_osk = 10**3

  likan.setObjective(
    # Raða nemendum á deildir sem eru nálægt heimilum þeirra
    quicksum(
      raw_x[s, c, v, d] * postur.fjar(M.nemendur[s].postnumer, M.klinik[c][v][d].postnumer)
      for s in M.nemendur
      for c in M.klinik
      for v in M.klinik[c]
      for d in M.klinik[c][v]
    ) * vigt_postnumer

    # Leyfa ákveðnum nemendum að klára klíník snemma, t.d. vegna barnseigna eða snemmrar útskriftar
    + quicksum(
      raw_x[s, c, v, d] for s in M.klara_snemma
      for c in M.klinik
      for v in set(M.klinik[c]).difference(M.auka_vikur)
      if sym_vikur[v] >= sym_vikur[M.klara_snemma[s]] for d in M.klinik[c][v]
    ) * vigt_klara_snemma

    # Leyfa ákveðnum nemendum að klára sérstök námskeið snemma
    + quicksum(
      raw_x[s, c, v, d] for s in M.klara_snemma_serstakt
      for c in M.klara_snemma_serstakt[s]
      for v in set(M.klinik[c]).difference(M.auka_vikur)
      if sym_vikur[v] >= sym_vikur[M.klara_snemma_serstakt[s][c]] for d in M.klinik[c][v]
    ) * vigt_klara_snemma_serstakt

    # Setja nemendur í klíník á ákveðna staði (landsbyggðaskráning t.d.)
    - quicksum(
      raw_x[s, c, v, d] for s in M.nemendur
      for c in M.klinik
      for v in M.klinik[c]
      for d in {d for d in M.klinik[c][v] if M.klinik[c][v][d].stadur in M.sami_stadur[s][c]}
    ) * vigt_serstakur_stadur

    # Ekki setja nemendur á stað sem þeir báðu um að fara ekki á
    + quicksum(
      raw_x[s, c, v, d] for s in M.nemendur
      for c in M.klinik
      for v in M.klinik[c]
      for d in {d for d in M.klinik[c][v] if M.klinik[c][v][d].stadur in M.ekki_sami_stadur[s][c]}
    ) * vigt_serstakur_stadur

    # Ekki setja nemendur á stað sem þeir báðu ekki um að fara á
    + quicksum(
      raw_x[s, c, v, d] for s in M.nemendur
      for c in M.klinik
      for v in M.klinik[c]
      for d in {d for d in M.klinik[c][v] if M.klinik[c][v][d].stadur in M.stadir[c].difference(M.sami_stadur[s][c])}
    ) * vigt_serstakur_stadur

    # Ekki setja nemendur í auka plássin sem eru búin til svo að módelið geti samt keyrt
    + quicksum(
      raw_x[s, c, v, 'Vantar pláss'] for s in M.nemendur
      for c in M.klinik
      for v in M.auka_vikur & set(M.klinik[c])
    ) * vigt_auka_vikur

    # Setja nemendur í ákveðnar deildir
    - quicksum(
      raw_x[s, c, v, d] for s in M.sama_deild
      for c in M.sama_deild[s]
      for d in M.sama_deild[s][c]
      for v in M.vikur if d in M.klinik[c][v]
    ) * vigt_serstakar_deildir

    # Setja nemendur ekki í ákveðnar deildir
    + quicksum(
      raw_x[s, c, v, d] for s in M.ekki_sama_deild
      for c in M.ekki_sama_deild[s]
      for d in M.ekki_sama_deild[s][c]
      for v in M.vikur if d in M.klinik[c][v]
    ) * vigt_serstakar_deildir

    # Gefa nemendum frí í umbeðnum vikum
    + quicksum(
      raw_x[s, c, v, d] for s in M.fri_osk
      for c in M.klinik
      for v in M.klinik[c] if v > 0
      for d in M.klinik[c][v]
      # .get() en ekki bein vísun: MRS/Deildir gögnin (M.klinik) geta haft viku
      # sem klinik_vikur (byggt úr stundatöflu) þekkir ekki - sjá model_generator.py
      if len(set(M.fri_osk[s]) & M.klinik_vikur.get(c, {}).get(v, set())) > 0
    ) * vigt_fri_osk
    , sense='minimize'
  )

  # 1. Allir nemendur fá klíník sem þau eru skráð í
  # (nákvæmlega einu sinni per klíník)
  for s in M.nemendur:
    for c in M.klinik:
      likan.addCons(
        quicksum(raw_x[s, c, v, d] for v in M.klinik[c] for d in M.klinik[c][v]) == M.nemendaskraning[s][c]
      )

  # 2. Fjöldi nemenda í klíník er ekki meiri en pláss
  for c in M.klinik:
    for v in M.klinik[c]:
      for d in M.klinik[c][v]:
        likan.addCons(
          quicksum(raw_x[s, c, v, d] for s in M.nemendur) <= M.klinik[c][v][d].plass
        )

  # 3. Engin skörun á milli klínískra námskeiða
  for s in M.nemendur:
    for c1 in M.klinik_vikur:
      if M.nemendaskraning[s][c1] != 1:
        continue
      for c2 in M.klinik_vikur:
        if M.nemendaskraning[s][c2] != 1:
          continue
        if c1 == c2:
          continue
        for v1 in M.klinik_vikur[c1]:
          if v1 <= 0:
            continue
          for v2 in M.klinik_vikur[c2]:
            if v2 <= 0:
              continue
            if len(M.klinik_vikur[c1][v1] & M.klinik_vikur[c2][v2]) == 0:
              continue
            likan.addCons(
              quicksum(raw_x[s, c1, v1, d1] for d1 in M.klinik[c1][v1])
              <= 1 - quicksum(raw_x[s, c2, v2, d2] for d2 in M.klinik[c2][v2])
            )

  # 4. Engin skörun á milli klínískra námskeiða og valnámskeiða
  for s in M.nemendur:
    for c in M.klinik_vikur:
      if M.nemendaskraning[s][c] != 1:
        continue
      for v in M.klinik_vikur[c]:
        if len(set(M.klinik_vikur[c][v]) & M.nemendur_val_vikur[s]) == 0:
          continue
        likan.addCons(
          quicksum(raw_x[s, c, v, d] for d in M.klinik[c][v]) == 0
        )

  # 5. Skilyrt frí
  likan.addCons(
    quicksum(
      raw_x[s, c, v, d] for s in M.fri_skilyrt if s in M.nemendur
      for c in M.klinik
      for v in M.klinik[c] if v > 0
      for d in M.klinik[c][v]
      if len(set(M.fri_skilyrt[s]) & M.klinik_vikur.get(c, {}).get(v, set())) > 0
    ) == 0
  )

  # 6. Fyrirfram ákveðnar skráningar
  for s in M.akvedin_rodun:
    for c in M.akvedin_rodun[s]:
      if len(M.akvedin_rodun[s][c]['deildir']) == 0:  # ef engar sérstakar deildir voru tilgreindar, förum við bara eftir gefnum vikum
        likan.addCons(
          quicksum(
            raw_x[s, c, v, d] for v in M.akvedin_rodun[s][c]['vikur'] for d in M.klinik[c][v]
          ) == M.nemendaskraning[s][c]
        )
      else:
        likan.addCons(
          quicksum(
            raw_x[s, c, v, d] for v in M.akvedin_rodun[s][c]['vikur'] for d in M.akvedin_rodun[s][c]['deildir'] if d in M.klinik[c][v]
          ) == M.nemendaskraning[s][c]
        )

  return likan, x, mx, deild_min, deild_max
