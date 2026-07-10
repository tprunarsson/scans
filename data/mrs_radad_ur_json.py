"""
Les output.json (frá src/main.py) og endurskapar upprunalegu
mrs_radad_<námskeið>.xlsx skjölin - sama dálkasnið og gamla Excel-byggða
kerfið (lib/excel_generator.py) skilaði, með einni "Vika N" fyrirsagnarlínu
per viku og einum dálki per nemanda/deildarupplýsingu. Sniðið er staðfest
gegn raunverulegum dæmum í docs/<ár>/radad/.

Aðeins dálkarnir sem núverandi kerfi fyllir út eru settir inn (Fullt nafn
nema, Kennitala, Netfang, Farsími, Deild (viðfang), Frá, Til, Deild,
Deildarstjóri, Netfang (deild), Símanúmer) - hinir eru hafðir auðir eins og
í upprunalega sniðinu (þeir eru fylltir út handvirkt af starfsfólki eftir á).

Keyra: python3 mrs_radad_ur_json.py <output.json> <útmappa>
"""
import sys
import json
import datetime
import pandas as pd

INNSKJAL = sys.argv[1] if len(sys.argv) > 1 else 'output.json'
UTMAPPA = sys.argv[2] if len(sys.argv) > 2 else '.'

DALKAR = [
  'Fullt nafn nema', 'Kennitala', 'Kyn', 'Netfang', 'Farsími',
  'Þjóðerni (ISO kóði)', 'Starfsheiti (kóði)', 'Kennitala leiðbeinanda',
  'Deild (viðfang)', 'Frá', 'Til', 'Dagar/viku', 'Athugasemd',
  'Námstig (GYMNASIUM, GRADUATE, POSTGRADUATE', 'Skóli (kóði/nafn)',
  'Námsgráða (ef postgrad) (ss. CP, Diploma, MD, MPH, EDS',
  'Aðalnámsgrein (kóði/nafn)', 'Sérnámsgrein (kóði/nafn)',
  'Land erlends skóla (ISO kóði)', 'Samtök (kóði/nafn)', 'Áætluð útskrift',
  'Nemandi hefur undirritað þagnarheiti',
  'Nemandi hefur undirritað reglur um notkun sjúkraskrárupplýsinga',
  'Auðkenniskort hefur verið afgreitt', 'Nemandi þarf tölvuaðgang',
  'Nemandi hefur farið í heilbrigðisviðtal', 'Nemandi þarf mynd í auðkenniskort',
  'Nemandi þarf auðkenniskort', 'Nemandi sækir auðkenniskort til skrifstofu',
  'Nemandi sækir auðkenniskort til umsjónarmanns', 'Ónotað',
  'Deild', 'Deildarstjóri', 'Netfang (deild)', 'Símanúmer',
]


def dags_eda_ekkert(iso_strengur):
  if not iso_strengur:
    return None
  return datetime.date.fromisoformat(iso_strengur)


def bua_til_dataframe(radir):
  """Hópar línur eftir (vika, dagsetning), raðar hópunum í dagatalsröð (ekki
  tölulegri vikuröð - vika 52 kemur á undan viku 1 ef dagsetningin segir svo),
  og setur inn "Vika N" fyrirsagnarlínu á undan hverjum hópi - nákvæmlega eins
  og upprunalega sniðið."""
  hopar = {}
  for r in radir:
    lykill = (r['vika'], r['dagsetning'])
    hopar.setdefault(lykill, []).append(r)

  # Röðun eftir dagsetningu (ISO-strengir raðast rétt í tölustafaröð) tryggir
  # rétta dagatalsröð óháð því hvort vikan er í upphafi eða lok skólaársins.
  ordudir_lyklar = sorted(hopar.keys(), key=lambda k: k[1] or '')

  linur = []
  for vika, _dags in ordudir_lyklar:
    linur.append({'Fullt nafn nema': f'Vika {vika}'})
    for r in hopar[(vika, _dags)]:
      linur.append({
        'Fullt nafn nema': r['nafn'] or None,
        'Kennitala': r['kennitala'] or None,
        'Netfang': r['notandanafn'] or None,
        'Farsími': r['farsimi'] or None,
        'Deild (viðfang)': r['vidfang'] or None,
        'Frá': dags_eda_ekkert(r['fra']),
        'Til': dags_eda_ekkert(r['til']),
        'Deild': r['deild'] or None,
        'Deildarstjóri': r['deildarstjori'] or None,
        'Netfang (deild)': r['netfang_deildar'] or None,
        'Símanúmer': r['simanumer'] or None,
      })
  df = pd.DataFrame(linur, columns=DALKAR)
  df.index = range(1, len(df) + 1)
  return df


def main():
  with open(INNSKJAL, encoding='utf-8') as f:
    data = json.load(f)

  namskeidslyklar = [k for k in data if k.startswith('mrs_radad_')]
  if not namskeidslyklar:
    print(f'Engin mrs_radad_* blöð fundust í {INNSKJAL}.')
    return

  for lykill in namskeidslyklar:
    df = bua_til_dataframe(data[lykill])
    slod = f'{UTMAPPA}/{lykill}.xlsx'
    df.to_excel(slod)
    print(f'Skrifaði {slod} ({len(df)} línur).')


if __name__ == '__main__':
  main()
