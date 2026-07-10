"""Sama líkan og model_generator.py (Gurobi), en leyst með HiGHS (frjáls og
ókeypis, ekkert leyfi þarf) í gegnum highspy. `main.py --solver highs` velur
þessa útgáfu. Sama s/c/v/d vísanakerfi og í model_generator.py.

Uppbygging líkansins hér er höfð eins nálægt model_generator.py og hægt er,
línu fyrir línu, svo auðvelt sé að bera þær saman. Munurinn er tæknilegur:
highspy hefur `addVariables` (fleirtala, tekur lista af lyklum og skilar
dict - svipað og gurobipy's `addVars`), en engan `addConstrs` sem ræður við
eins flóknar, margfalt-síaðar nestaðar summur og skorða 3 hér að neðan er,
svo skorður eru byggðar upp með handvirkum lykkjum eins og í
model_generator_scip.py. Lausnargildi eru lesin með `model.val(var)` í stað
`.X` - HighsVar hér að neðan brúar þann mun svo solution_check.py og
utkoma.py þurfi ekki að vita hvaða leysir var notaður."""
import highspy
from postur import Postur
from vikur import Vikur

class HighsVar:
  """Lætur HiGHS breytu haga sér eins og gurobipy breytu (`.X`) fyrir kóðann
  sem les lausnina. `.X` er reiknað þegar á það er kallað (ekki við smíði),
  svo þetta virkar óháð því hvenær `likan.optimize()` er keyrt af kallanda."""
  __slots__ = ('_model', '_var')

  def __init__(self, model, var):
    self._model = model
    self._var = var

  @property
  def X(self):
    return self._model.val(self._var)

def is_optimal(likan):
  """True ef HiGHS fann sannaða bestu lausn."""
  return likan.getModelStatus() == highspy.HighsModelStatus.kOptimal

def generate_model(M):
  postur = Postur()
  V = Vikur()
  sym_vikur = V.sym

  likan = highspy.Highs()

  x_lyklar = [(s, c, v, d) for s in M.nemendur for c in M.klinik for v in M.klinik[c] for d in M.klinik[c][v]]
  raw_x = likan.addVariables(x_lyklar, type=highspy.HighsVarType.kInteger, lb=0, ub=1)
  x = {k: HighsVar(likan, raw_x[k]) for k in x_lyklar}

  mx_lyklar = list(M.klinik)
  raw_mx = likan.addVariables(mx_lyklar, type=highspy.HighsVarType.kContinuous)
  mx = {k: HighsVar(likan, raw_mx[k]) for k in mx_lyklar}

  deild_mm_lyklar = [(c, v) for c in M.klinik for v in M.klinik[c]]
  raw_deild_min = likan.addVariables(deild_mm_lyklar, type=highspy.HighsVarType.kContinuous)
  deild_min = {k: HighsVar(likan, raw_deild_min[k]) for k in deild_mm_lyklar}
  raw_deild_max = likan.addVariables(deild_mm_lyklar, type=highspy.HighsVarType.kContinuous)
  deild_max = {k: HighsVar(likan, raw_deild_max[k]) for k in deild_mm_lyklar}

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
    likan.qsum(
      raw_x[s, c, v, d] * postur.fjar(M.nemendur[s].postnumer, M.klinik[c][v][d].postnumer)
      for s in M.nemendur
      for c in M.klinik
      for v in M.klinik[c]
      for d in M.klinik[c][v]
    ) * vigt_postnumer

    # Leyfa ákveðnum nemendum að klára klíník snemma, t.d. vegna barnseigna eða snemmrar útskriftar
    + likan.qsum(
      raw_x[s, c, v, d] for s in M.klara_snemma
      for c in M.klinik
      for v in set(M.klinik[c]).difference(M.auka_vikur)
      if sym_vikur[v] >= sym_vikur[M.klara_snemma[s]] for d in M.klinik[c][v]
    ) * vigt_klara_snemma

    # Leyfa ákveðnum nemendum að klára sérstök námskeið snemma
    + likan.qsum(
      raw_x[s, c, v, d] for s in M.klara_snemma_serstakt
      for c in M.klara_snemma_serstakt[s]
      for v in set(M.klinik[c]).difference(M.auka_vikur)
      if sym_vikur[v] >= sym_vikur[M.klara_snemma_serstakt[s][c]] for d in M.klinik[c][v]
    ) * vigt_klara_snemma_serstakt

    # Setja nemendur í klíník á ákveðna staði (landsbyggðaskráning t.d.)
    - likan.qsum(
      raw_x[s, c, v, d] for s in M.nemendur
      for c in M.klinik
      for v in M.klinik[c]
      for d in {d for d in M.klinik[c][v] if M.klinik[c][v][d].stadur in M.sami_stadur[s][c]}
    ) * vigt_serstakur_stadur

    # Ekki setja nemendur á stað sem þeir báðu um að fara ekki á
    + likan.qsum(
      raw_x[s, c, v, d] for s in M.nemendur
      for c in M.klinik
      for v in M.klinik[c]
      for d in {d for d in M.klinik[c][v] if M.klinik[c][v][d].stadur in M.ekki_sami_stadur[s][c]}
    ) * vigt_serstakur_stadur

    # Ekki setja nemendur á stað sem þeir báðu ekki um að fara á
    + likan.qsum(
      raw_x[s, c, v, d] for s in M.nemendur
      for c in M.klinik
      for v in M.klinik[c]
      for d in {d for d in M.klinik[c][v] if M.klinik[c][v][d].stadur in M.stadir[c].difference(M.sami_stadur[s][c])}
    ) * vigt_serstakur_stadur

    # Ekki setja nemendur í auka plássin sem eru búin til svo að módelið geti samt keyrt
    + likan.qsum(
      raw_x[s, c, v, 'Vantar pláss'] for s in M.nemendur
      for c in M.klinik
      for v in M.auka_vikur & set(M.klinik[c])
    ) * vigt_auka_vikur

    # Setja nemendur í ákveðnar deildir
    - likan.qsum(
      raw_x[s, c, v, d] for s in M.sama_deild
      for c in M.sama_deild[s]
      for d in M.sama_deild[s][c]
      for v in M.vikur if d in M.klinik[c][v]
    ) * vigt_serstakar_deildir

    # Setja nemendur ekki í ákveðnar deildir
    + likan.qsum(
      raw_x[s, c, v, d] for s in M.ekki_sama_deild
      for c in M.ekki_sama_deild[s]
      for d in M.ekki_sama_deild[s][c]
      for v in M.vikur if d in M.klinik[c][v]
    ) * vigt_serstakar_deildir

    # Gefa nemendum frí í umbeðnum vikum
    + likan.qsum(
      raw_x[s, c, v, d] for s in M.fri_osk
      for c in M.klinik
      for v in M.klinik[c] if v > 0
      for d in M.klinik[c][v]
      # .get() en ekki bein vísun: MRS/Deildir gögnin (M.klinik) geta haft viku
      # sem klinik_vikur (byggt úr stundatöflu) þekkir ekki - sjá model_generator.py
      if len(set(M.fri_osk[s]) & M.klinik_vikur.get(c, {}).get(v, set())) > 0
    ) * vigt_fri_osk
    , sense=highspy.ObjSense.kMinimize
  )

  # 1. Allir nemendur fá klíník sem þau eru skráð í
  # (nákvæmlega einu sinni per klíník)
  for s in M.nemendur:
    for c in M.klinik:
      likan.addConstr(
        likan.qsum(raw_x[s, c, v, d] for v in M.klinik[c] for d in M.klinik[c][v]) == M.nemendaskraning[s][c]
      )

  # 2. Fjöldi nemenda í klíník er ekki meiri en pláss
  for c in M.klinik:
    for v in M.klinik[c]:
      for d in M.klinik[c][v]:
        likan.addConstr(
          likan.qsum(raw_x[s, c, v, d] for s in M.nemendur) <= M.klinik[c][v][d].plass
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
            likan.addConstr(
              likan.qsum(raw_x[s, c1, v1, d1] for d1 in M.klinik[c1][v1])
              <= 1 - likan.qsum(raw_x[s, c2, v2, d2] for d2 in M.klinik[c2][v2])
            )

  # 4. Engin skörun á milli klínískra námskeiða og valnámskeiða
  for s in M.nemendur:
    for c in M.klinik_vikur:
      if M.nemendaskraning[s][c] != 1:
        continue
      for v in M.klinik_vikur[c]:
        if len(set(M.klinik_vikur[c][v]) & M.nemendur_val_vikur[s]) == 0:
          continue
        likan.addConstr(
          likan.qsum(raw_x[s, c, v, d] for d in M.klinik[c][v]) == 0
        )

  # 5. Skilyrt frí
  likan.addConstr(
    likan.qsum(
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
        likan.addConstr(
          likan.qsum(
            raw_x[s, c, v, d] for v in M.akvedin_rodun[s][c]['vikur'] for d in M.klinik[c][v]
          ) == M.nemendaskraning[s][c]
        )
      else:
        likan.addConstr(
          likan.qsum(
            raw_x[s, c, v, d] for v in M.akvedin_rodun[s][c]['vikur'] for d in M.akvedin_rodun[s][c]['deildir'] if d in M.klinik[c][v]
          ) == M.nemendaskraning[s][c]
        )

  return likan, x, mx, deild_min, deild_max
