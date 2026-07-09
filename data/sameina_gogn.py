"""
Býr til eitt sameinað .xlsx skjal úr þremur upprunalegum inntaksskjölum
(skraningar.xlsx, mrs_stadlad.xlsx, auka_upplysingar.xlsx) í einni möppu hér
undir data/ (t.d. t0/), umskrifað í sama normalíseraða form og Google Sheet
vinnuskjalið notar (Nemendur/Skraningar/Lotur/Deildir/... blöð, með
dropdown-staðfestingu tilbúinni).

Notað til að "sá" (seed) Google Sheet vinnuskjalið með sögulegum gögnum, ef
þörf er á - t.d. þegar byrjað er á nýju skólaári og gamalt Excel-byggt gagnasafn
er til, en ekkert Google Sheet ennþá.

Keyra: python3 sameina_gogn.py <mappa> <utskjal>
Sjálfgefið: mappa=t0, utskjal=t0/sameinad.xlsx
"""
import sys
import pandas as pd
from openpyxl.worksheet.datavalidation import DataValidation

MAPPA = sys.argv[1] if len(sys.argv) > 1 else 't0'
UTSKJAL = sys.argv[2] if len(sys.argv) > 2 else f'{MAPPA}/sameinad.xlsx'

NEMENDUR_META_DALKAR = ['Notandanafn', 'Nafn', 'Kennitala', 'Póstnúmer', 'Farsími']


def hreinsa_auka(df):
  df = df.rename(columns={
    'Netfang': 'notandanafn', 'Námskeið': 'namskeid', 'Vika': 'vika',
    'Vikur': 'vikur', 'Deild': 'deild', 'Staður': 'stadur',
  })
  return df.drop(columns=['Nafn'], errors='ignore')


def leidretta_hastafi(df, vaentir_dalkar):
  """Sum eldri skjöl (t.d. t3/skraningar.xlsx) hafa "notandanafn" með litlum
  staf í stað "Notandanafn" - passar dálkaheiti óháð há-/lágstöfum svo
  sömu vænta nöfnin (NEMENDUR_META_DALKAR o.fl.) virki óháð þessu."""
  vidsnuid = {c.lower(): c for c in df.columns}
  endurnefna = {}
  for vaentur in vaentir_dalkar:
    fundinn = vidsnuid.get(vaentur.lower())
    if fundinn and fundinn != vaentur:
      endurnefna[fundinn] = vaentur
  return df.rename(columns=endurnefna) if endurnefna else df


def main():
  # ---- Lesa upprunagögn ------------------------------------------------
  skraningar_xl = pd.ExcelFile(f'{MAPPA}/skraningar.xlsx')
  nemendur_hra = leidretta_hastafi(skraningar_xl.parse('nemendur'), NEMENDUR_META_DALKAR)
  STUNDATAFLA_DALKAR = ['Vika', 'Dagsetning', 'Námskeið', 'Fjöldi vikna', 'Klíník byrjar í viku']
  stundatafla_hra = leidretta_hastafi(skraningar_xl.parse('stundatafla'), STUNDATAFLA_DALKAR)

  mrs_xl = pd.ExcelFile(f'{MAPPA}/mrs_stadlad.xlsx')
  deildir_hra = pd.concat([mrs_xl.parse(s) for s in mrs_xl.sheet_names], ignore_index=True)

  auka_xl = pd.ExcelFile(f'{MAPPA}/auka_upplysingar.xlsx')
  auka = {s: auka_xl.parse(s) for s in auka_xl.sheet_names}

  # ---- Nemendur (frá skráningarkerfi / API) -----------------------------
  nemendur = nemendur_hra[NEMENDUR_META_DALKAR].copy()
  nemendur.columns = ['notandanafn', 'nafn', 'kennitala', 'postnumer', 'farsimi']

  # ---- Skraningar: langt form í stað einn dálkur per námskeið -----------
  namskeids_dalkar = [c for c in nemendur_hra.columns if c not in NEMENDUR_META_DALKAR]
  linur = []
  for _, row in nemendur_hra.iterrows():
    for c in namskeids_dalkar:
      gildi = row[c]
      if pd.notna(gildi) and str(gildi).strip() != '':
        linur.append({'notandanafn': row['Notandanafn'], 'namskeid': c})
  skraningar = pd.DataFrame(linur, columns=['notandanafn', 'namskeid'])

  # ---- Lotur: lota hvers námskeiðs (klínísk og valnámskeið) --------------
  lotur = stundatafla_hra.rename(columns={
    'Vika': 'vika', 'Dagsetning': 'dagsetning', 'Námskeið': 'namskeid',
    'Fjöldi vikna': 'fjoldi_vikna', 'Klíník byrjar í viku': 'klinik_byrjar_i_viku',
  })[['namskeid', 'vika', 'dagsetning', 'fjoldi_vikna', 'klinik_byrjar_i_viku']]

  # ---- Deildir: öll klínísk pláss, eitt blað í stað eins per námskeið ----
  # Höfuðborgarsvæði dálkurinn er sleppt hér - hann er lesinn í kerfinu en
  # ekki notaður af neinni virkri skorðu/marki líkansins (sjá src/deild.py).
  deildir = deildir_hra.rename(columns={
    'Vika': 'vika', 'Dagsetning': 'dagsetning', 'Námskeið': 'namskeid',
    'Deild': 'deild', 'Staður': 'stadur', 'Viðfang': 'vidfang', 'Pláss': 'plass',
    'Póstnúmer': 'postnumer', 'Deildarstjóri': 'deildarstjori',
    'Netfang': 'netfang_deildar', 'Símanúmer': 'simanumer',
  })[['namskeid', 'vika', 'dagsetning', 'deild', 'stadur', 'plass', 'vidfang',
      'postnumer', 'deildarstjori', 'netfang_deildar', 'simanumer']]

  # ---- Undanþágur (starfsfólk) og óskir (nemendakönnun) ------------------
  fri_skilyrt = hreinsa_auka(auka['fri_skilyrt'])
  klara_snemma = hreinsa_auka(auka['klara_snemma'])
  klara_snemma_serstakt = hreinsa_auka(auka['klara_snemma_serstakt'])
  akvedin_rodun = hreinsa_auka(auka['akvedin_rodun'])
  sami_stadur = hreinsa_auka(auka['sami_stadur'])
  ekki_sami_stadur = hreinsa_auka(auka['ekki_sami_stadur'])
  sama_deild = hreinsa_auka(auka['sama_deild'])
  ekki_sama_deild = hreinsa_auka(auka['ekki_sama_deild'])
  fri_osk = hreinsa_auka(auka['fri_osk'])

  # ---- Viðmið: einstakar tilvísanalistar fyrir dropdown-staðfestingu -----
  vidmid = pd.DataFrame({
    'namskeid': pd.Series(sorted(set(lotur['namskeid'].dropna()))),
  })
  vidmid_deild = pd.DataFrame({'deild': pd.Series(sorted(set(deildir['deild'].dropna())))})
  vidmid_stadur = pd.DataFrame({'stadur': pd.Series(sorted(set(deildir['stadur'].dropna()) - {''}))})
  vidmid = pd.concat([vidmid, vidmid_deild, vidmid_stadur], axis=1)

  # ---- Yfirlit: hvað er hvað, og hvaðan kemur það -------------------------
  yfirlit = pd.DataFrame([
    ('Nemendur', 'API (skráningarkerfi)', 'Nemendaskrá: kennitala, netfang, sími, póstnúmer.'),
    ('Skraningar', 'API (skráningarkerfi)', 'Hvaða nemandi er skráður í hvaða námskeið (langt form).'),
    ('Lotur', 'Starfsfólk (stjórnun)', 'Upphafsvika/dagsetning og lengd hverrar lotu, klínísk og val.'),
    ('Deildir', 'Starfsfólk (pláss/klínik)', 'Öll klínísk pláss: deild, staður, pláss, vika.'),
    ('fri_skilyrt', 'Starfsfólk (samþykkt undanþága)', 'Skilyrt (hörð) frívika - verður að uppfylla.'),
    ('klara_snemma', 'Starfsfólk (samþykkt undanþága)', 'Nemandi verður að klára alla klíník fyrir gefna viku.'),
    ('klara_snemma_serstakt', 'Starfsfólk (samþykkt undanþága)', 'Sama og ofan en fyrir eitt tiltekið námskeið.'),
    ('akvedin_rodun', 'Starfsfólk (samþykkt undanþága)', 'Fyrirfram ákveðin röðun nemanda á námskeið/viku/deild.'),
    ('sami_stadur', 'Nemendakönnun (Form)', 'Óskastaðir nemanda fyrir tiltekið námskeið (mjúk ósk).'),
    ('ekki_sami_stadur', 'Nemendakönnun (Form)', 'Staðir sem nemandi vill ekki fara á (mjúk ósk).'),
    ('sama_deild', 'Nemendakönnun (Form)', 'Óskadeildir nemanda fyrir tiltekið námskeið (mjúk ósk).'),
    ('ekki_sama_deild', 'Nemendakönnun (Form)', 'Deildir sem nemandi vill ekki fara á (mjúk ósk).'),
    ('fri_osk', 'Nemendakönnun (Form)', 'Óskir um frí í tilteknum vikum (mjúk ósk).'),
    ('Vidmid', 'Reiknað (formúlur)', 'Tilvísanalistar fyrir dropdown-staðfestingu í hinum blöðunum.'),
  ], columns=['Blað', 'Uppruni', 'Lýsing'])

  # ---- Skrifa allt í eitt .xlsx skjal ------------------------------------
  blod = {
    'Yfirlit': yfirlit,
    'Nemendur': nemendur,
    'Skraningar': skraningar,
    'Lotur': lotur,
    'Deildir': deildir,
    'fri_skilyrt': fri_skilyrt,
    'klara_snemma': klara_snemma,
    'klara_snemma_serstakt': klara_snemma_serstakt,
    'akvedin_rodun': akvedin_rodun,
    'sami_stadur': sami_stadur,
    'ekki_sami_stadur': ekki_sami_stadur,
    'sama_deild': sama_deild,
    'ekki_sama_deild': ekki_sama_deild,
    'fri_osk': fri_osk,
    'Vidmid': vidmid,
  }

  with pd.ExcelWriter(UTSKJAL, engine='openpyxl') as writer:
    for nafn, df in blod.items():
      df.to_excel(writer, sheet_name=nafn, index=False)

    wb = writer.book

    def dalkstafur(df, dalknafn):
      idx = list(df.columns).index(dalknafn)
      return chr(ord('A') + idx)

    def baeta_vid_stadfestingu(bladnafn, dalknafn, df, tilvisunarformula, max_rows=500):
      ws = wb[bladnafn]
      stafur = dalkstafur(df, dalknafn)
      dv = DataValidation(type='list', formula1=tilvisunarformula, allow_blank=True, showErrorMessage=True)
      dv.error = f'Gildi verður að vera í tilvísanalistanum ({tilvisunarformula}).'
      ws.add_data_validation(dv)
      dv.add(f'{stafur}2:{stafur}{max_rows}')

    nem_tilvisun = f"Nemendur!$A$2:$A${len(nemendur) + 200}"
    ns_tilvisun = f"Vidmid!$A$2:$A${len(vidmid) + 200}"
    deild_tilvisun = f"Vidmid!$B$2:$B${len(vidmid) + 200}"
    stadur_tilvisun = f"Vidmid!$C$2:$C${len(vidmid) + 200}"

    baeta_vid_stadfestingu('Skraningar', 'notandanafn', skraningar, nem_tilvisun)
    baeta_vid_stadfestingu('Skraningar', 'namskeid', skraningar, ns_tilvisun)
    baeta_vid_stadfestingu('Lotur', 'namskeid', lotur, ns_tilvisun)
    baeta_vid_stadfestingu('Deildir', 'namskeid', deildir, ns_tilvisun)

    for bladnafn, df in [
      ('fri_skilyrt', fri_skilyrt), ('klara_snemma', klara_snemma),
      ('klara_snemma_serstakt', klara_snemma_serstakt), ('akvedin_rodun', akvedin_rodun),
      ('sami_stadur', sami_stadur), ('ekki_sami_stadur', ekki_sami_stadur),
      ('sama_deild', sama_deild), ('ekki_sama_deild', ekki_sama_deild), ('fri_osk', fri_osk),
    ]:
      baeta_vid_stadfestingu(bladnafn, 'notandanafn', df, nem_tilvisun)
      if 'namskeid' in df.columns:
        baeta_vid_stadfestingu(bladnafn, 'namskeid', df, ns_tilvisun)
      if 'deild' in df.columns:
        baeta_vid_stadfestingu(bladnafn, 'deild', df, deild_tilvisun)
      if 'stadur' in df.columns:
        baeta_vid_stadfestingu(bladnafn, 'stadur', df, stadur_tilvisun)

  print(f'Skrifaði {UTSKJAL} með {len(blod)} blöðum.')


if __name__ == '__main__':
  main()
