"""
Les input.json (flutt út úr Google Sheet vinnuskjalinu með "Sækja gögn",
sjá gas/Export.gs) og skilar (ModelData, listi af aðvörunum) sem
model_generator*.py getur leyst.

input.json inniheldur eitt fylki (lista af hlutum, einn hlutur = ein röð í
blaðinu) fyrir hvert blað í vinnuskjalinu: Nemendur, Skraningar, Lotur,
Deildir, fri_skilyrt, klara_snemma, klara_snemma_serstakt, akvedin_rodun,
sami_stadur, ekki_sami_stadur, sama_deild, ekki_sama_deild, fri_osk.

Skráin er í tveimur lögum:
  1. Þýðingarlag (_df, _build_*_dfs): endurgerir sömu pandas DataFrame-form,
     með sömu upprunalegu íslensku dálkaheitunum, sem restin af skránni
     vinnur með. Þetta einangrar JSON-sniðið frá restinni af lestrinum.
  2. Sannreyning og smíði (lesa_namskeid, build_model_data): les þessi
     DataFrame og byggir upp ModelData, með ítarlegri villuleit - m.a.
     athugun á að vikunúmer og dagsetningar í stundatöflunni stemmi saman
     (sjá kaflann um ISO-vikutal hér að neðan).

Sameiginlegt vísanakerfi (s/c/v/d) sem er notað hér og út um allan kóðann er
útskýrt í model_data.py.
"""
import json
import pandas as pd
from model_data import ModelData
from deild import Deild
from nemandi import Nemandi

def clean_split(s, delim=';'):
  """Skiptir upp streng eins og "8;12" í ['8', '12)], hunsar tóm/auð gildi.
  Notað fyrir öll svæði í input.json sem geyma lista sem semikommu-aðgreindan
  streng (t.d. "vikur", "deild", "staður")."""
  s = str(s).replace('\xa0', ' ').strip()
  return [x.strip() for x in s.split(delim) if x.strip() != '']

# ---------------------------------------------------------------------------
# 1. Þýðingarlag: input.json -> pandas DataFrames með upprunalegu íslensku
#    dálkaheitunum sem build_model_data vinnur með.
# ---------------------------------------------------------------------------

AUKA_SHEETS = [
  'fri_skilyrt', 'klara_snemma', 'klara_snemma_serstakt', 'akvedin_rodun',
  'sami_stadur', 'ekki_sami_stadur', 'sama_deild', 'ekki_sama_deild', 'fri_osk',
]

def _df(records, rename=None, date_col=None, columns=None):
  df = pd.DataFrame(records)
  if rename:
    df = df.rename(columns=rename)
  if columns:
    # Tryggir að dálkar séu til staðar (t.d. þegar blað er alveg tómt í input.json -
    # DataFrame með engar línur hefur þá enga dálka nema þeir séu settir handvirkt).
    for c in columns:
      if c not in df.columns:
        df[c] = pd.Series(dtype=object)
  if date_col and date_col in df.columns:
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    # Halda "" fyrir línur án dagsetningar (sama regla og restin af lestrinum notar),
    # en halda alvöru Timestamp gildum fyrir hinar - því þarf að fara framhjá
    # hinu almenna fillna('') fyrir þennan dálk eingöngu.
    mask = df[date_col].isna()
    df[date_col] = df[date_col].astype(object)
    df.loc[mask, date_col] = ''
  df = df.fillna('')
  return df.reset_index(drop=True)

NEMENDUR_COLUMNS = ['notandanafn', 'nafn', 'kennitala', 'póstnúmer', 'farsími']
LOTUR_COLUMNS = ['námskeið', 'vika', 'dagsetning', 'fjöldi vikna', 'klíník byrjar í viku']
DEILDIR_COLUMNS = [
  'námskeið', 'vika', 'dagsetning', 'deild', 'staður', 'viðfang', 'pláss',
  'póstnúmer', 'deildarstjóri', 'netfang', 'símanúmer',
]

def _build_skraningar_dfs(data):
  nemendur_df = _df(data.get('Nemendur', []), rename={
    'postnumer': 'póstnúmer', 'farsimi': 'farsími',
  }, columns=NEMENDUR_COLUMNS)

  # Skraningar er langt form (ein lína per (nemandi, námskeið)) - breytt hér
  # í breitt form (einn dálkur per námskeið, "x" ef skráð/ur) því restin af
  # lestrinum (og upprunalega Excel-sniðið sem það er byggt á) vinnur þannig.
  skraningar_records = data.get('Skraningar', [])
  if skraningar_records:
    skraningar_df = pd.DataFrame(skraningar_records)
    breitt = (
      skraningar_df.assign(_merki='x')
      .pivot_table(index='notandanafn', columns='namskeid', values='_merki', aggfunc='first', fill_value='')
    )
    breitt.columns = [str(c).lower() for c in breitt.columns]
    nemendur_df = nemendur_df.merge(breitt, how='left', left_on='notandanafn', right_index=True)
    nemendur_df = nemendur_df.fillna('')

  stundatafla_df = _df(data.get('Lotur', []), rename={
    'namskeid': 'námskeið', 'fjoldi_vikna': 'fjöldi vikna',
    'klinik_byrjar_i_viku': 'klíník byrjar í viku',
  }, date_col='dagsetning', columns=LOTUR_COLUMNS)

  return {'nemendur': nemendur_df, 'stundatafla': stundatafla_df}

def _build_mrs_dfs(data):
  deildir_df = _df(data.get('Deildir', []), rename={
    'namskeid': 'námskeið', 'stadur': 'staður', 'vidfang': 'viðfang', 'plass': 'pláss',
    'postnumer': 'póstnúmer', 'deildarstjori': 'deildarstjóri', 'netfang_deildar': 'netfang',
    'simanumer': 'símanúmer',
  }, date_col='dagsetning', columns=DEILDIR_COLUMNS)

  # Höfuðborgarsvæði er ekki lengur safnað (ónotað af líkaninu, sjá Deild í
  # deild.py), en lesa_namskeid() vænti dálksins - fyllum inn tómu gildi svo
  # sá kóði þurfi ekki að breytast.
  if 'höfuðborgarsvæði' not in deildir_df.columns:
    deildir_df['höfuðborgarsvæði'] = ''

  # Eitt DataFrame per námskeið, eins og upprunalega mrs_stadlad.xlsx hafði
  # eitt blað per námskeið.
  mrs_dfs = {}
  for namskeid, hopur in deildir_df.groupby('námskeið', sort=False):
    mrs_dfs[namskeid] = hopur.reset_index(drop=True)
  return mrs_dfs

AUKA_COLUMNS = {
  'fri_skilyrt': ['netfang', 'vikur'],
  'klara_snemma': ['netfang', 'vika'],
  'klara_snemma_serstakt': ['netfang', 'námskeið', 'vika'],
  'akvedin_rodun': ['netfang', 'námskeið', 'vika', 'deild'],
  'sami_stadur': ['netfang', 'námskeið', 'staður'],
  'ekki_sami_stadur': ['netfang', 'námskeið', 'staður'],
  'sama_deild': ['netfang', 'námskeið', 'deild'],
  'ekki_sama_deild': ['netfang', 'námskeið', 'deild'],
  'fri_osk': ['netfang', 'vikur'],
}

def _build_auka_dfs(data):
  rename = {'notandanafn': 'netfang', 'namskeid': 'námskeið', 'stadur': 'staður'}
  return {
    name: _df(data.get(name, []), rename=rename, columns=AUKA_COLUMNS[name])
    for name in AUKA_SHEETS
  }

# ---------------------------------------------------------------------------
# 2. lesa_namskeid: eitt "námskeið" úr Deildir - ein Deild fyrir hverja
#    (viku, deild) samsetningu sem það á.
# ---------------------------------------------------------------------------

def lesa_namskeid(df, namskeid=None):
  """Les eitt DataFrame (allar Deildir-línur fyrir eitt námskeið) og skilar
  {námskeiðsheiti: {vika: {deildarheiti: Deild}}}."""
  vikur = dict()
  for row in df.iterrows():
    row = row[1]
    try:
      if row['vika'] not in vikur:
        vikur[row['vika']] = dict()

      postnumer = [101]
      if not row['póstnúmer'] == '':
        postnumer = [int(float(i)) for i in clean_split(row['póstnúmer'], ';')]

      hofudborgarsvaedi = True
      if row['höfuðborgarsvæði'] == 0 or row['höfuðborgarsvæði'] == '':
        hofudborgarsvaedi = False

      # Getur verið tómur strengur. Strippum bæði deild og staður hér - allar
      # tilvísanir í þau annars staðar (akvedin_rodun, sama_deild, sami_stadur
      # o.fl.) fara í gegnum clean_split(), sem strippar - án þessa geta tvær
      # eins deildir/staðir sem eingöngu greinast á bili í lok strengs (t.d.
      # "Heilsugæslan Ísafirði " á móti "Heilsugæslan Ísafirði") aldrei parað
      # saman, sem gerir annars gilda "ákveðin röðun" óstuðlanlega.
      deild_nafn = str(row['deild']).strip()
      stadsetning = str(row['staður']).strip()

      vidfang = row['viðfang']
      if row['viðfang'] == '':
        vidfang = '00000'
      else:
        vidfang = str(int(vidfang)).rjust(5, '0')

      plass = row['pláss']
      try:
        plass = int(plass)
      except ValueError:
        raise Exception(f'Pláss verður að vera heiltala, fann {plass} í mrs skjali.')
      vikur[row['vika']][deild_nafn] = Deild(deild_nafn, vidfang, plass, stadsetning, hofudborgarsvaedi, postnumer, row['deildarstjóri'], row['netfang'], row['símanúmer'])
    except KeyError as kerr:
      if namskeid is not None:
        raise Exception(f'Vantar dálkinn {kerr} í mrs skjali undir {namskeid}.')
      raise Exception(f'Vantar dálkinn {kerr} í mrs skjali.')
  return { df['námskeið'][0]: vikur }

# ---------------------------------------------------------------------------
# 3. build_model_data: sannreyning gagna og smíði ModelData
# ---------------------------------------------------------------------------

def build_model_data(skraningar_dfs, mrs_dfs, auka_upplysingar_dfs, skraningar='Nemendur/Skraningar/Lotur', mrs='Deildir', auka_upplysingar='input.json'):
  """Byggir upp ModelData úr þremur dict-of-DataFrame hópum (sjá _build_*_dfs
  hér að ofan) og skilar (M, warnings). `skraningar`/`mrs`/`auka_upplysingar`
  eru eingöngu notuð til að gera villuskilaboð læsileg - þau vísa á hvaða
  blað/blöð í input.json gögnin komu úr."""
  M = ModelData()
  warnings = []

  try:
    nemendur_df = skraningar_dfs['nemendur']
    stundatafla_df = skraningar_dfs['stundatafla']
  except KeyError as kerr:
    raise Exception(f'Vantar blað {kerr} í {skraningar} gögnunum.')

  try:
    sami_stadur_df = auka_upplysingar_dfs['sami_stadur']
    ekki_sami_stadur_df = auka_upplysingar_dfs['ekki_sami_stadur']
    klara_snemma_df = auka_upplysingar_dfs['klara_snemma']
    klara_snemma_serstakt_df = auka_upplysingar_dfs['klara_snemma_serstakt']
    sama_deild_df = auka_upplysingar_dfs['sama_deild']
    ekki_sama_deild_df = auka_upplysingar_dfs['ekki_sama_deild']
    fri_osk_df = auka_upplysingar_dfs['fri_osk']
    fri_skilyrt_df = auka_upplysingar_dfs['fri_skilyrt']
    akvedin_rodun_df = auka_upplysingar_dfs['akvedin_rodun']
  except KeyError as kerr:
    raise Exception(f'Vantar blað {kerr} í {auka_upplysingar} gögnunum.')

  vikur = set()
  for vika in stundatafla_df['vika']:
    vikur.add(vika)
  M.vikur = vikur

  #----------------------------------------------------------------------------
  # Athuga að vikunúmer í stundatöflu passi við dagsetningu (ISO-vikutal:
  # vika 1 er sú vika sem inniheldur fyrsta fimmtudag ársins). Þetta grípur
  # bæði stök innsláttarmistök og kerfisbundið misræmi milli vikutalningar-
  # aðferða (t.d. ef "vika 1" er miðuð við fyrsta mánudag ársins í staðinn).

  for i in stundatafla_df.index:
    dags = stundatafla_df.loc[i, 'dagsetning']
    vika = stundatafla_df.loc[i, 'vika']
    if isinstance(dags, str):
      continue # engin dagsetning skráð, ekkert til að bera saman við

    iso_vika = dags.isocalendar()[1]
    if int(vika) != iso_vika:
      namskeid_row = stundatafla_df.loc[i, 'námskeið']
      warnings.append(
        f'Í stundatöflu er skráð að námskeiðið {namskeid_row} sé í viku {vika} þann {dags.strftime("%d/%m/%Y")}, '
        f'en samkvæmt ISO-vikutali er sú dagsetning í viku {iso_vika}. Athugaðu hvort vikunúmerið eða dagsetningin sé rétt.'
      )
  #----------------------------------------------------------------------------

  #----------------------------------------------------------------------------
  # Deildir (áður: MRS skjöl)

  namskeid = dict()

  if isinstance(mrs_dfs, dict):
    for x in mrs_dfs:
      namskeid.update(lesa_namskeid(mrs_dfs[x], x))
  else:
    namskeid.update(lesa_namskeid(mrs_dfs))

  if len(namskeid) == 0:
    raise Exception(f'Engin námskeið lesin úr Deildir gögnunum')

  for c in namskeid:
    for vika in vikur:
      if vika not in namskeid[c]:
        namskeid[c][vika] = dict()

  M.klinik = namskeid

  # Deildir í hverju námskeiði - notað til að passa að gögn séu rétt
  klinik_deildir = dict()
  for c in namskeid:
    klinik_deildir[c] = set()
    for vika in namskeid[c]:
      for deild in namskeid[c][vika]:
        klinik_deildir[c].add(deild)

  # Staðir fyrir hvert námskeið - notað til að passa að gögn séu rétt
  klinik_stadir = dict()
  for c in namskeid:
    klinik_stadir[c] = set()
    for vika in namskeid[c]:
      for deild in namskeid[c][vika]:
        klinik_stadir[c].add(namskeid[c][vika][deild].stadur)
  #----------------------------------------------------------------------------

  #----------------------------------------------------------------------------
  # Nemendur

  nemendur = dict()
  try:
    for i, nemandi in enumerate(nemendur_df['notandanafn']):
      nemendur[nemandi] = Nemandi(nemendur_df['nafn'][i], str(nemendur_df['kennitala'][i]).rjust(10, '0'), nemendur_df['notandanafn'][i], nemendur_df['farsími'][i], nemendur_df['póstnúmer'][i], 0)
      if nemendur[nemandi].postnumer == '':
        nemendur[nemandi].postnumer = 101

  except KeyError as kerr:
    raise Exception(f'Vantar dálkinn {kerr} í nemenda hlutann í {skraningar} gögnunum')

  M.nemendur = nemendur
  #----------------------------------------------------------------------------

  #----------------------------------------------------------------------------
  # Skráning nemenda í námskeið

  nemendaskraning = dict()
  try:
    for i, nemandi in enumerate(nemendur_df['notandanafn']):
      nemendaskraning[nemandi] = dict()
      failed_namskeid = set()
      for nam in namskeid:
        if nam not in failed_namskeid:
          try:
            if len(str(nemendur_df[nam.lower()][i])) > 0:
              nemendaskraning[nemandi][nam] = 1
            else:
              nemendaskraning[nemandi][nam] = 0
          except KeyError as kerr:
            warnings.append(f'Vantar dálkinn {kerr} í nemenda hlutann í {skraningar} gögnunum. Allir nemendur skráðir í námskeiðið.')
            failed_namskeid.add(nam)

    for nemandi in nemendur:
      for nam in failed_namskeid:
        nemendaskraning[nemandi][nam] = 1

  except KeyError as kerr:
    raise Exception(f'Vantar dálkinn {kerr} í nemenda hlutann í {skraningar} gögnunum')

  M.nemendaskraning = nemendaskraning

  # og í valnámskeið
  val_vikur = dict()
  val_listi = set()
  try:
    # dict fyrir vikur valnámskeiða
    val_listi = set(stundatafla_df[stundatafla_df['klíník byrjar í viku'] == '']['námskeið'])

    for val in val_listi:
      val_vikur.update({
        val: stundatafla_df[stundatafla_df['námskeið'] == val]['vika'].tolist()
      })

  except KeyError as kerr:
    raise Exception(f'Vantar dálkinn {kerr} í stundatöflu hlutann í {skraningar} gögnunum')

  M.val_listi = val_listi
  M.val_vikur = val_vikur

  val_nemenda = dict()
  try:
    for i, nemandi in enumerate(nemendur_df['notandanafn']):
      val_nemenda[nemandi] = dict()
      for val in val_vikur:
        if len(str(nemendur_df[val.lower()][i])) > 0:
          val_nemenda[nemandi][val] = 1
        else:
          val_nemenda[nemandi][val] = 0

  except KeyError as kerr:
    raise Exception(f'Vantar dálkinn {kerr} í nemanda hlutann í {skraningar} gögnunum')

  M.val_nemenda = val_nemenda
  #----------------------------------------------------------------------------

  #----------------------------------------------------------------------------
  # Skrá nemendur á sama stað

  sami_stadur = dict()
  try:
    failed_stadir = { c: set() for c in namskeid }

    for s in M.nemendur:
      sami_stadur[s] = { c: set() for c in namskeid }
    for i, netfang in enumerate(sami_stadur_df['netfang']):

      nams = set(clean_split(sami_stadur_df['námskeið'][i], ';'))

      if netfang not in M.nemendur:
        raise Exception(f'Nemandinn {netfang} í sami_stadur í {auka_upplysingar} fannst ekki í nemendaskráningu í {skraningar} gögnunum.')
      for c in nams:
        if c not in M.klinik:
          raise Exception(f'Námskeiðið {c} úr sami_stadur í {auka_upplysingar} fannst ekki í {mrs} gögnunum.')

      if len(nams) == 0:
        nams = namskeid

      stadir = set(clean_split(sami_stadur_df['staður'][i], ';'))
      for c in nams:
        for st in stadir:
          if st not in klinik_stadir[c]:
            failed_stadir[c].add(st)
            warnings.append(f'Staðurinn {st} í sami_stadur í {auka_upplysingar} fannst ekki í {mrs} gögnunum fyrir námskeiðið {c}.')
        sami_stadur[netfang][c] = stadir

  except KeyError as kerr:
    raise Exception(f'Rangt netfang/námskeið gefið í {auka_upplysingar}/sami_stadur: {kerr}')

  M.sami_stadur = sami_stadur
  #----------------------------------------------------------------------------

  #----------------------------------------------------------------------------
  # Skrá nemendur á annan stað

  ekki_sami_stadur = dict()
  try:
    failed_stadir = { c: set() for c in namskeid }

    for s in M.nemendur:
      ekki_sami_stadur[s] = { c: set() for c in namskeid }
    for i, netfang in enumerate(ekki_sami_stadur_df['netfang']):
      nams = set(clean_split(ekki_sami_stadur_df['námskeið'][i], ';'))

      if netfang not in M.nemendur:
        raise Exception(f'Nemandinn {netfang} í ekki_sami_stadur í {auka_upplysingar} fannst ekki í nemendaskráningu í {skraningar} gögnunum.')
      for c in nams:
        if c not in M.klinik:
          raise Exception(f'Námskeiðið {c} úr ekki_sami_stadur í {auka_upplysingar} fannst ekki í {mrs} gögnunum.')

      if len(nams) == 0:
        nams = namskeid

      stadir = set(clean_split(ekki_sami_stadur_df['staður'][i], ';'))
      for c in nams:
        for st in stadir:
          if st not in klinik_stadir[c] and st not in failed_stadir[c]:
            failed_stadir[c].add(st)
            warnings.append(f'Staðurinn {st} í ekki_sami_stadur í {auka_upplysingar} fannst ekki í {mrs} gögnunum fyrir námskeiðið {c}.')
        ekki_sami_stadur[netfang][c] = stadir

  except KeyError as kerr:
    raise Exception(f'Rangt netfang/námskeið gefið í {auka_upplysingar}/ekki_sami_stadur: {kerr}')

  M.ekki_sami_stadur = ekki_sami_stadur
  #----------------------------------------------------------------------------

  #----------------------------------------------------------------------------
  # Vikur per hólf

  stundatafla_klinik = stundatafla_df[stundatafla_df['klíník byrjar í viku'] != '']
  try:
    stundatafla_klinik = stundatafla_klinik.astype({ 'klíník byrjar í viku': int })
  except ValueError as err:
    raise Exception(f'Gildi í "klíník byrjar í viku" dálki í {skraningar} gögnunum ekki heiltala: {err}')

  klinik_vikur = dict()
  for c in set(stundatafla_klinik['námskeið']):
    temp = dict()
    for i in stundatafla_klinik[stundatafla_klinik['námskeið'] == c].index:
      v = stundatafla_klinik.loc[i, 'vika']
      q = stundatafla_klinik.loc[i, 'klíník byrjar í viku']
      n = stundatafla_klinik.loc[i, 'fjöldi vikna']
      temp.update({ v + q - 1: set(range(v, v + n)) })
    klinik_vikur.update({ c: temp })

  # Athuga að allar vikur í Deildir séu í klinik_vikur
  for c in namskeid:
    for v in M.klinik[c]:
      if len(M.klinik[c][v]) > 0:
        if v not in klinik_vikur[c]:
          warnings.append(f'Námskeiðið {c} er með skráða klíník í viku {v} í {mrs} gögnunum en ekki í {skraningar} gögnunum.')

  # Athuga að allar vikur í klinik_vikur séu í Deildir
  for c in klinik_vikur:
    if c not in M.klinik:
      continue
    for v in klinik_vikur[c]:
      if v not in M.klinik[c]:
        warnings.append(f'Námskeiðið {c} er með skráða klíník í viku {v} í {skraningar} gögnunum en ekki í {mrs} gögnunum.')

  M.klinik_vikur = klinik_vikur
  #----------------------------------------------------------------------------

  #----------------------------------------------------------------------------
  # Nemendur sem þurfa að klára alla klíník snemma

  klara_snemma = dict()
  try:
    for i, netfang in enumerate(klara_snemma_df['netfang']):
      if netfang not in M.nemendur:
        raise Exception(f'Nemandinn {netfang} í klara_snemma í {auka_upplysingar} fannst ekki í nemendaskráningu í {skraningar} gögnunum.')

      klara_snemma[netfang] = klara_snemma_df['vika'][i]
  except KeyError as kerr:
    raise Exception(f'Vantar dálkinn {kerr} í klara_snemma í {auka_upplysingar} gögnunum.')

  M.klara_snemma = klara_snemma
  #----------------------------------------------------------------------------

  #----------------------------------------------------------------------------
  # Nemendur sem þurfa að klára tiltekna klíník snemma

  klara_snemma_serstakt = dict()
  try:
    for i, netfang in enumerate(klara_snemma_serstakt_df['netfang']):
      nam = klara_snemma_serstakt_df['námskeið'][i]

      if netfang not in M.nemendur:
        raise Exception(f'Nemandinn {netfang} í klara_snemma_serstakt í {auka_upplysingar} fannst ekki í nemendaskráningu í {skraningar} gögnunum.')
      if nam not in M.klinik:
        raise Exception(f'Námskeiðið {nam} í klara_snemma_serstakt í {auka_upplysingar} fannst ekki í {mrs} gögnunum.')

      if netfang not in klara_snemma_serstakt:
        klara_snemma_serstakt[netfang] = dict()
      if nam in klara_snemma_serstakt[netfang]:
        raise Exception(f'Nemandinn {netfang} er tvískráður í klara_snemma_serstakt í {auka_upplysingar} með námskeiðið {nam}.')
      klara_snemma_serstakt[netfang][nam] = klara_snemma_serstakt_df['vika'][i]

  except KeyError as kerr:
    raise Exception(f'Vantar dálkinn {kerr} í klara_snemma_serstakt í {auka_upplysingar} gögnunum.')

  M.klara_snemma_serstakt = klara_snemma_serstakt
  #----------------------------------------------------------------------------

  #----------------------------------------------------------------------------
  # Skrá nemendur á sömu deild

  sama_deild = dict()
  try:
    for s in M.nemendur:
      sama_deild[s] = { c: set() for c in namskeid }
    for i, netfang in enumerate(sama_deild_df['netfang']):
      nam = sama_deild_df['námskeið'][i]

      if netfang not in M.nemendur:
        raise Exception(f'Nemandinn {netfang} í sama_deild í {auka_upplysingar} fannst ekki í nemendaskráningu í {skraningar} gögnunum.')
      if nam not in M.klinik:
        raise Exception(f'Námskeiðið {nam} í sama_deild í {auka_upplysingar} fannst ekki í {mrs} gögnunum.')

      for deild in clean_split(sama_deild_df['deild'][i], ';'):
        if deild not in klinik_deildir[nam]:
          warnings.append(f'Deildin {deild} í sama_deild í {auka_upplysingar} fannst ekki í {mrs} gögnunum fyrir námskeiðið {nam}.')

        sama_deild[netfang][nam].add(deild)

  except KeyError as kerr:
    raise Exception(f'Vantar dálkinn {kerr} í sama_deild í {auka_upplysingar} gögnunum.')

  M.sama_deild = sama_deild
  #----------------------------------------------------------------------------

  #----------------------------------------------------------------------------
  # Skrá nemendur á aðra deild

  ekki_sama_deild = dict()
  try:
    for s in M.nemendur:
      ekki_sama_deild[s] = { c: set() for c in namskeid }
    for i, netfang in enumerate(ekki_sama_deild_df['netfang']):
      nam = ekki_sama_deild_df['námskeið'][i]

      if netfang not in M.nemendur:
        raise Exception(f'Nemandinn {netfang} í ekki_sama_deild í {auka_upplysingar} fannst ekki í nemendaskráningu í {skraningar} gögnunum.')
      if nam not in M.klinik:
        raise Exception(f'Námskeiðið {nam} úr ekki_sama_deild í {auka_upplysingar} fannst ekki í {mrs} gögnunum.')

      for deild in clean_split(ekki_sama_deild_df['deild'][i], ';'):
        if deild not in klinik_deildir[nam]:
          warnings.append(f'Deildin {deild} í ekki_sama_deild í {auka_upplysingar} fannst ekki í {mrs} gögnunum fyrir námskeiðið {nam}.')

        ekki_sama_deild[netfang][nam].add(deild)

  except KeyError as kerr:
    raise Exception(f'Vantar dálkinn {kerr} í ekki_sama_deild í {auka_upplysingar} gögnunum.')

  M.ekki_sama_deild = ekki_sama_deild
  #----------------------------------------------------------------------------

  #----------------------------------------------------------------------------
  # Óskir um frívikur

  fri_osk = dict()
  try:
    for i, netfang in enumerate(fri_osk_df['netfang']):
      if netfang not in M.nemendur:
        warnings.append(f'Nemandinn {netfang} í fri_osk í {auka_upplysingar} fannst ekki í nemendaskráningu í {skraningar} gögnunum.')

      try:
        if netfang in fri_osk:
          fri_osk[netfang] |= set([int(i) for i in clean_split(fri_osk_df['vikur'][i], ';')])
        else:
          fri_osk[netfang] = set([int(i) for i in clean_split(fri_osk_df['vikur'][i], ';')])
      except:
        warnings.append(f'Tókst ekki að lesa vikur fyrir {netfang} í fri_osk í {auka_upplysingar}.')

  except:
    warnings.append(f'Tókst ekki að lesa fríóskir úr {auka_upplysingar} gögnunum.')

  M.fri_osk = fri_osk
  #----------------------------------------------------------------------------

  #----------------------------------------------------------------------------
  # Skilyrtar frívikur

  fri_skilyrt = dict()
  try:
    for i, netfang in enumerate(fri_skilyrt_df['netfang']):
      if netfang not in M.nemendur:
        warnings.append(f'Nemandinn {netfang} í fri_skilyrt í {auka_upplysingar} fannst ekki í nemendaskráningu í {skraningar} gögnunum.')

      try:
        if netfang in fri_skilyrt:
          fri_skilyrt[netfang] |= set([int(i) for i in clean_split(fri_skilyrt_df['vikur'][i], ';')])
        else:
          fri_skilyrt[netfang] = set([int(i) for i in clean_split(fri_skilyrt_df['vikur'][i], ';')])
      except:
        warnings.append(f'Tókst ekki að lesa vikur fyrir {netfang} í fri_skilyrt í {auka_upplysingar}.')

  except:
    warnings.append(f'Tókst ekki að lesa skilyrtar fríóskir úr {auka_upplysingar} gögnunum.')

  M.fri_skilyrt = fri_skilyrt
  #----------------------------------------------------------------------------

  #----------------------------------------------------------------------------
  # vikur sem nemendur eru í valnámskeiðum

  nemendur_val_vikur = dict()

  for s in M.val_nemenda:
    tmp = set()
    for c in M.val_nemenda[s]:
      if M.val_nemenda[s][c] > 0:
        tmp.update(set(M.val_vikur[c]))
    nemendur_val_vikur.update({ s: tmp })

  M.nemendur_val_vikur = nemendur_val_vikur
  #----------------------------------------------------------------------------

  #----------------------------------------------------------------------------
  # Röðun sem er ákveðin fyrirfram

  akvedin_rodun = dict()

  for i, netfang in enumerate(akvedin_rodun_df['netfang']):
    if netfang not in M.nemendur:
      raise Exception(f'Nemandinn {netfang} í akvedin_rodun í {auka_upplysingar} fannst ekki í nemendaskráningu í {skraningar} gögnunum.')

    namskeid = akvedin_rodun_df.loc[i, 'námskeið']

    if akvedin_rodun_df.loc[i,'vika'] == '':
      vikur = set(klinik_vikur[namskeid]) # ef engar vikur eru tilgreindar má skráningin vera í hvaða viku námskeiðsins sem tiltekin deild er möguleg

      if akvedin_rodun_df.loc[i, 'deild'] == '':
        continue # ef bæði mengin eru tóm, þá þarf ekki að bæta við auka skorðu

    else:
      vikur = {int(n) for n in clean_split(akvedin_rodun_df.loc[i,'vika'], ';')}

    deildir = set(clean_split(akvedin_rodun_df.loc[i,'deild'], ';'))
    for d in deildir:
      if d not in klinik_deildir[namskeid]:
        warnings.append(f'Deild {d} í akvedin_rodun í {auka_upplysingar} fannst ekki í {mrs} gögnunum fyrir námskeiðið {namskeid}.')

    if netfang not in akvedin_rodun:
      akvedin_rodun.update({ netfang: dict() })
    akvedin_rodun[netfang].update({ namskeid: { 'deildir': deildir, 'vikur': vikur } })

  M.akvedin_rodun = akvedin_rodun

  M.generate_extra_data()
  M.generate_extra_weeks()

  warnings = list(set(warnings))

  return M, warnings

# ---------------------------------------------------------------------------
# 4. lesa_gogn: opinbera fallið sem main.py kallar á
# ---------------------------------------------------------------------------

def lesa_gogn(json_slod):
  """Les input.json af `json_slod` og skilar (ModelData, listi af aðvörunum).
  Kastar Exception ef gögnin eru svo gölluð að ekki er hægt að byggja upp
  líkan úr þeim (t.d. vantar nauðsynlegan dálk, eða tilvísun í nemanda/
  námskeið sem er ekki til) - allt annað (t.d. villa í einni línu sem hægt
  er að hunsa) verður að aðvörun í skilaða listanum í staðinn."""
  with open(json_slod, encoding='utf-8') as f:
    data = json.load(f)

  skraningar_dfs = _build_skraningar_dfs(data)
  mrs_dfs = _build_mrs_dfs(data)
  auka_upplysingar_dfs = _build_auka_dfs(data)

  return build_model_data(skraningar_dfs, mrs_dfs, auka_upplysingar_dfs)
