"""
Býr til data/example_input.json úr data/t0/input.json með öllum persónu-
auðkennanlegum gögnum skipt út fyrir tilbúin (random) gildi: nöfn, kennitölur,
símanúmer nemenda OG deildarstjóra, og netföng deilda sett á dummy@dummy.dum.

`notandanafn` er sérstakt - það er lykillinn sem tengir saman nemanda þvert á
öll blöðin (Skraningar, fri_skilyrt, sami_stadur o.s.frv.), svo því er skipt
út fyrir samræmt en einkvæmt tilbúið notandanafn (t.d. nemandi001@example.com)
í stað þess að vera fjarlægt eða allt sett á sama gildi - annars myndu allir
nemendur "renna saman" í eitt í úttakinu og gögnin hætta að vera nothæf sem
raunhæft dæmi.

Keyra: python3 anonymize_example.py [t0] [example_input.json]
"""
import sys
import json
import random

MAPPA = sys.argv[1] if len(sys.argv) > 1 else 't0'
UTSKJAL = sys.argv[2] if len(sys.argv) > 2 else 'example_input.json'

FORNOFN = [
  'Anna', 'Björg', 'Guðrún', 'Sigríður', 'Kristín', 'Margrét', 'Helga', 'Ólöf',
  'Jón', 'Sigurður', 'Guðmundur', 'Ólafur', 'Einar', 'Kristján', 'Björn', 'Þór',
]
EFTIRNOFN = [
  'Jónsdóttir', 'Guðmundsdóttir', 'Sigurðardóttir', 'Ólafsdóttir', 'Björnsdóttir',
  'Jónsson', 'Guðmundsson', 'Sigurðsson', 'Ólafsson', 'Björnsson',
]

NOTANDANAFN_LYKLAR = [
  'Skraningar', 'fri_skilyrt', 'klara_snemma', 'klara_snemma_serstakt',
  'akvedin_rodun', 'sami_stadur', 'ekki_sami_stadur', 'sama_deild',
  'ekki_sama_deild', 'fri_osk',
]


def tilbuid_nafn():
  return f'{random.choice(FORNOFN)} {random.choice(EFTIRNOFN)}'


def tilbuin_kennitala():
  return random.randint(1000000000, 9999999999)


def tilbuid_simanumer():
  return random.randint(6000000, 8999999)


def main():
  random.seed(0)  # samræmi milli keyrslna

  with open(f'{MAPPA}/input.json', encoding='utf-8') as f:
    data = json.load(f)

  # ---- Notandanafn: samræmd en einkvæm tilbúin gildi, notuð sem lykill ----
  notandanafn_kort = {
    row['notandanafn']: f'nemandi{i + 1:03d}@example.com'
    for i, row in enumerate(data['Nemendur'])
  }

  for row in data['Nemendur']:
    gamalt = row['notandanafn']
    row['notandanafn'] = notandanafn_kort[gamalt]
    row['nafn'] = tilbuid_nafn()
    row['kennitala'] = tilbuin_kennitala()
    row['farsimi'] = tilbuid_simanumer()

  # Sum blöð vísa í notandanafn sem er ekki (eða ekki lengur) skráð í Nemendur
  # (þekkt gagnavilla - sjá integrity.md) - þau gildi eru samt sem áður alvöru
  # netföng og verða að vera fjarlægð, svo þeim er úthlutað nýju tilbúnu
  # gildi rétt eins og hinum í staðinn fyrir að sleppa þeim.
  for lykill in NOTANDANAFN_LYKLAR:
    for row in data.get(lykill, []):
      gamalt = row.get('notandanafn')
      if not gamalt:
        continue
      if gamalt not in notandanafn_kort:
        notandanafn_kort[gamalt] = f'ovoentanotandi{len(notandanafn_kort) + 1:03d}@example.com'
      row['notandanafn'] = notandanafn_kort[gamalt]

  # ---- Deildarstjórar: tilbúin nöfn/símanúmer, netföng á dummy@dummy.dum ----
  for row in data.get('Deildir', []):
    if row.get('deildarstjori'):
      row['deildarstjori'] = tilbuid_nafn()
    if row.get('simanumer'):
      row['simanumer'] = tilbuid_simanumer()
    if row.get('netfang_deildar'):
      row['netfang_deildar'] = 'dummy@dummy.dum'

  with open(UTSKJAL, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

  print(f'Skrifaði {UTSKJAL}: {len(data["Nemendur"])} nemendur með tilbúin nöfn/kennitölur/símanúmer.')


if __name__ == '__main__':
  main()
