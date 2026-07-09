# SCANS — Scheduling Clinical Assignments for Nursing Students

Raðar hjúkrunarfræðinemum á klínísk pláss og valnámskeið eins hagkvæmt og
mögulegt er, með MIP-líkani (HiGHS, Gurobi, eða SCIP - sjá `src/benchmark.py`).
Þessi mappa er hrein, sjálfstæð útgáfa af verkefninu - eingöngu JSON-byggða leiðin, engin
Excel-skjöl í innlestri eða úttaki.

## Yfirlit yfir gagnaflæðið

```
Google Sheet vinnuskjal
   │  "Sækja gögn" (gas/Export.gs)
   ▼
input.json  ──────────►  src/main.py  ──────────►  output.json
                          (Gurobi eða SCIP)
                                                        │  "Hlaða upp niðurstöðum"
                                                        ▼
                                                Google Sheet vinnuskjal
                                       (ný blöð: stundatafla, skraningar,
                                        mrs_radad_<námskeið> per námskeið)
```

Vinnuskjalið sjálft (Google Sheet með gas/-skriftunum uppsettum) er ekki
hluti af þessari möppu - það er staðsett í Google Drive notandans. `gas/`
inniheldur skriftukóðann sem keyrir *í* því skjali.

## `src/` - líkanið sjálft

```
python3 src/main.py input.json [output.json] [--solver gurobi|scip]
```

Uppsetning:
```
python3 -m venv venv && source venv/bin/activate
pip install -r src/requirements.txt
```

Þrír leysar eru studdir - allir skila sömu bestu lausn (staðfest með
`benchmark.py`, sjá að neðan), aðeins hraði og leyfiskröfur eru ólíkar:

| `--solver` | Pakki | Leyfi | Hraði á t0 (109 nemendur, 4 námskeið) |
|---|---|---|---|
| `highs` (sjálfgefið) | highspy | Frjálst og ókeypis | Nálægt Gurobi (~1s lausn) |
| `gurobi` | gurobipy | Þarfnast leyfis (`src/gurobi.env`) | Hraðast - lausn á broti úr sekúndu |
| `scip` | pyscipopt | Frjálst og ókeypis | Hægast (~50s lausn á sama gagnasafni) |

`highs` er sjálfgefið því það þarfnast ekki leyfis en er samt nálægt Gurobi í
hraða (sjá `benchmark.py` niðurstöður að ofan) - `scip` er til taks en mun
hægara á stærri gagnasöfnum.

Skráaryfirlit:
| Skrá | Hlutverk |
|---|---|
| `main.py` | Skipanalínuforritið - les, leysir, skrifar |
| `benchmark.py` | Ber saman uppbyggingar-/lausnartíma og hlutlægisgildi allra tiltækra leysa á sama input.json |
| `innlestur.py` | Les input.json, sannreynir gögn, byggir upp `ModelData` |
| `model_generator.py` / `model_generator_scip.py` / `model_generator_highs.py` | Sjálft MIP-líkanið, sama uppbygging í öllum þremur, ólíkir leysar |
| `solution_check.py` | Mannlæsilegar aðvaranir um mjúkar skorður sem ekki tókst að uppfylla |
| `utkoma.py` | Býr til output.json úr leystu líkani |
| `model_data.py`, `deild.py`, `nemandi.py`, `vikur.py`, `postur.py` | Gagnaform og hjálparföll (sjá útskýringar í hverri skrá) |

Vísanakerfið sem er notað út um allan kóðann (`s`/`c`/`v`/`d` fyrir
nemanda/námskeið/viku/deild) er útskýrt í `model_data.py`.

### Að bera saman leysa

```
python3 benchmark.py ../data/t0/input.json
```

Keyrir líkanið með öllum þremur leysum í sömu Python-lotu (sanngjarnari
samanburður en að keyra hvern fyrir sig - forðast endurtekinn
túlk-ræsingarkostnað), mælir uppbyggingar- og lausnartíma sitt í hvoru lagi,
og athugar að öll skili sama hlutlægisgildi - það er sjálfstæð staðfesting
þess að model_generator*.py þýðingarnar þrjár séu í raun samhljóða, óháð
hraðamun þeirra. Hægt að velja undirmengi leysa: `--solvers gurobi,highs`.

Dæmi um niðurstöðu á `data/t0` (109 nemendur, 4 námskeið, Apple M4 Max) -
tímar eru vélarháðir og eiga eftir að hækka á stærri gagnasöfnum, en
innbyrðis munur leysa ætti að haldast svipaður:

```
==============================================================================
Leysir       Uppbygging      Lausn    Samtals     Hlutlægisgildi
------------------------------------------------------------------------------
gurobi            0.27s      0.12s      0.39s        -1274695.00
highs             0.26s      0.79s      1.05s        -1274695.00
scip              0.29s     52.84s     53.13s        -1274695.00
==============================================================================
Allir leysar fundu sama hlutlægisgildi - líkönin eru samhljóða.
```

### Af hverju vika/dagsetning skiptir máli

`innlestur.py` athugar að vikunúmer og dagsetning í `Lotur` blaðinu passi
saman samkvæmt ISO-vikutali (vika 1 = vikan með fyrsta fimmtudegi ársins).
Þetta er söguleg ástæða: eldra kerfi taldi vikur frá fyrsta mánudegi í
staðinn, sem stemmir við ISO-vikutalið flest ár en skekkist um heila viku
þau ár sem 1. janúar lendir á ákveðnum vikudögum. `gas/Validation.gs` grípur
og lagar þetta sjálfkrafa fyrir lítið misræmi (±2 vikur), og stingur upp á
lagfæringu (sem þarf samþykki) fyrir stærra misræmi sem bendir frekar til
rangrar dagsetningar (t.d. dagur/mánuður víxlað við innslátt) en rangrar
vikutalningar.

## `gas/` - Google Apps Script (clasp-stýrt)

Tvær skriftur bundnar við Google Sheet vinnuskjalið:
- `Validation.gs` - valmyndin "Stundatafla": "Staðfesta gögn" (athugar
  tilvísanir og vikur/dagsetningar, lagar sjálfkrafa það sem óhætt er) og
  "Beita samþykktum lagfæringum".
- `Export.gs` (+ `SaekjaGognDialog.html`, `HladaUppDialog.html`) - "Sækja
  gögn" (niðurhalar input.json beint í Downloads-möppuna) og "Hlaða upp
  niðurstöðum" (les output.json af tölvunni og býr til/yfirskrifar blöð).

### Að setja upp/uppfæra með clasp

```
cd gas
cp .clasp.json.example .clasp.json
# Settu inn þitt raunverulega Script ID í .clasp.json - finnst í
# Apps Script ritlinum: Extensions > Apps Script > Project Settings > Script ID
clasp push
```

`clasp push` skrifar yfir skriftukóðann í lifandi vinnuskjalinu - farðu
varlega og skoðaðu breytingarnar áður en þú keyrir það á skjali sem er í
notkun.

## `data/` - söguleg gögn og flutningur

Hver `tX/` mappa inniheldur upprunalegu þrjú Excel-skjölin
(`skraningar.xlsx`, `mrs_stadlad.xlsx`, `auka_upplysingar.xlsx`) fyrir eitt
sögulegt gagnasafn, og ef keyrsla hefur verið framkvæmd fyrir það gagnasafn,
líka `input.json`/`output.json` parið sem varð til.

`sameina_gogn.py` les þessi þrjú Excel-skjöl úr einni möppu og býr til eitt
sameinað, normalíserað `.xlsx` skjal (sama snið og Google Sheet
vinnuskjalið notar, með dropdown-staðfestingu tilbúinni) - nota til að "sá"
(seed) vinnuskjalið með sögulegum gögnum ef þörf er á:

```
python3 sameina_gogn.py t0 t0/sameinad.xlsx
```

## Hvers vegna JSON, ekki Excel

Upprunalega útgáfa þessa verkefnis las/skrifaði Excel-skjöl beint. Það gerði
tvöfalda villuleit erfiða: dagsetningar og vikunúmer voru handslegin inn á
mörgum stöðum með enga leið til að staðfesta að þau stemmdu saman fyrr en
eftir á. Núverandi hönnun færir alla gagnastaðfestingu inn í Google Sheet
sjálft (dropdown-listar sem koma í veg fyrir ógildar tilvísanir, sjálfvirk
athugun á viku-á-móti-dagsetningu), þannig að `src/` þarf aldrei að takast á
við óstaðfest gögn - það les eingöngu already-staðfest input.json.
