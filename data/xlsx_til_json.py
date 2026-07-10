"""
Les sameinað .xlsx skjal (t.d. búið til af sameina_gogn.py) og skrifar
input.json með nákvæmlega sama sniði og Google Sheet vinnuskjalið skilar með
"Sækja gögn" (sjá gas/Export.gs). Notað til að prófa src/main.py á vélinni
án þess að fara í gegnum Google Sheets - t.d. fyrir söguleg gagnasöfn í
docs/<ár>/ (sjá keyra_prof.sh).

Keyra: python3 xlsx_til_json.py <inn.xlsx> <input.json>
"""
import sys
import json
import pandas as pd

INNSKJAL = sys.argv[1] if len(sys.argv) > 1 else 'sameinad.xlsx'
UTSKJAL = sys.argv[2] if len(sys.argv) > 2 else 'input.json'

GAGNABLOD = [
  'Nemendur', 'Skraningar', 'Lotur', 'Deildir',
  'fri_skilyrt', 'klara_snemma', 'klara_snemma_serstakt', 'akvedin_rodun',
  'sami_stadur', 'ekki_sami_stadur', 'sama_deild', 'ekki_sama_deild', 'fri_osk',
]


def blad_i_faerslur(df):
  df = df.where(pd.notna(df), None)
  faerslur = []
  for row in df.to_dict(orient='records'):
    faersla = {}
    for k, v in row.items():
      if isinstance(v, pd.Timestamp):
        v = v.strftime('%Y-%m-%d')
      faersla[k] = v
    faerslur.append(faersla)
  return faerslur


def main():
  xl = pd.ExcelFile(INNSKJAL)
  data = {}
  for blad in GAGNABLOD:
    if blad in xl.sheet_names:
      data[blad] = blad_i_faerslur(xl.parse(blad))
  with open(UTSKJAL, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
  print(f'Skrifaði {UTSKJAL} með {sum(len(v) for v in data.values())} færslum úr {len(data)} blöðum.')


if __name__ == '__main__':
  main()
