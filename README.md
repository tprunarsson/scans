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
python3 src/main.py input.json [output.json] [--solver highs|gurobi|scip|highs-parallel]
```

Uppsetning:
```
python3 -m venv venv && source venv/bin/activate
pip install -r src/requirements.txt
```

Fjórir leysar eru studdir - allir skila sömu bestu lausn (staðfest með
`benchmark.py`, sjá að neðan), aðeins hraði og leyfiskröfur eru ólíkar:

| `--solver` | Pakki | Leyfi | Hraði á dæminu (109 nemendur, 4 námskeið) |
|---|---|---|---|
| `highs` (sjálfgefið) | highspy | Frjálst og ókeypis | Nálægt Gurobi (~1-3s lausn) |
| `highs-parallel` | highspy | Frjálst og ókeypis | Sama og `highs` - engin mælanlegur munur á þessu líkani, sjá að neðan |
| `gurobi` | gurobipy | Þarfnast leyfis (`src/gurobi.env`) | Hraðast - lausn á broti úr sekúndu |
| `scip` | pyscipopt | Frjálst og ókeypis | Hægast (~20-50s lausn á sama gagnasafni) |

`highs` er sjálfgefið því það þarfnast ekki leyfis en er samt nálægt Gurobi í
hraða (sjá `benchmark.py` niðurstöður að ofan) - `scip` er til taks en mun
hægara á stærri gagnasöfnum.

Skráaryfirlit:
| Skrá | Hlutverk |
|---|---|
| `main.py` | Skipanalínuforritið - les, leysir, skrifar |
| `benchmark.py` | Ber saman uppbyggingar-/lausnartíma og hlutlægisgildi allra tiltækra leysa á sama input.json |
| `innlestur.py` | Les input.json, sannreynir gögn, byggir upp `ModelData` |
| `model_generator.py` / `model_generator_scip.py` / `model_generator_highs.py` | Sjálft MIP-líkanið, sama uppbygging í öllum, ólíkir leysar |
| `model_generator_highs_parallel.py` | Sama og `model_generator_highs.py`, en þvingar HiGHS til að nota samhliða leit (sjá "Að bera saman leysa" að neðan) |
| `solution_check.py` | Mannlæsilegar aðvaranir um mjúkar skorður sem ekki tókst að uppfylla |
| `utkoma.py` | Býr til output.json úr leystu líkani |
| `iis_greining.py` | Greinir hvers vegna líkan er óstuðlanlegt (infeasible) með Gurobi's computeIIS() - sjá athugasemd í skránni sjálfri |
| `model_data.py`, `deild.py`, `nemandi.py`, `vikur.py`, `postur.py` | Gagnaform og hjálparföll (sjá útskýringar í hverri skrá) |

Vísanakerfið sem er notað út um allan kóðann (`s`/`c`/`v`/`d` fyrir
nemanda/námskeið/viku/deild) er útskýrt í `model_data.py`.

### Að bera saman leysa

```
python3 benchmark.py ../data/example_input.json
```

Keyrir líkanið með öllum leysum í sömu Python-lotu (sanngjarnari samanburður
en að keyra hvern fyrir sig - forðast endurtekinn túlk-ræsingarkostnað),
mælir uppbyggingar- og lausnartíma sitt í hvoru lagi, og athugar að öll skili
sama hlutlægisgildi - það er sjálfstæð staðfesting þess að
model_generator*.py þýðingarnar séu í raun samhljóða, óháð hraðamun þeirra.
Hægt að velja undirmengi leysa: `--solvers gurobi,highs`.

`highs-parallel` er sama líkan og `highs` en þvingar HiGHS til að nota
samhliða MIP-leit (`parallel`='on') í stað þess að láta HiGHS ákveða sjálft
(`'choose'`, sjálfgefið). Á þessu líkani gerir það engan mælanlegan mun -
forúrvinnslan (presolve) leysir vandamálið nánast alveg áður en
greinun-og-mörkun þarf yfirhöfuð að byrja, svo það er ekkert tré eftir sem
er þess virði að leita í samhliða. HiGHS-eigin sjálfvirka val ("choose") var
sem sagt réttmætt hér - staðfest með eigin log-skilaboðum HiGHS:

```
# --solver highs (sjálfgefið, 'parallel'='choose'):
Thread count 7 (of 14 threads). Using 1 max workers. Parallel search off

# --solver highs-parallel ('parallel' þvingað á 'on'):
Thread count 7 (of 14 threads). Using 12 max workers. Parallel search on
```

Munurinn í stillingunni er raunverulegur (1 á móti 12 verkþráðum), en skilar
sér ekki í mælanlegum hraðamun (2.96s á móti 2.94s í töflunni að neðan) -
HiGHS ákvað réttilega sjálft að samhliða leit borgaði sig ekki hér.

Dæmi um niðurstöðu á `data/example_input.json` (109 nemendur, 4 námskeið,
Apple M4 Max) - tímar eru vélarháðir og eiga eftir að hækka á stærri
gagnasöfnum, en innbyrðis munur leysa ætti að haldast svipaður:

```
==================================================================================
Leysir             Uppbygging      Lausn    Samtals     Hlutlægisgildi
----------------------------------------------------------------------------------
gurobi                  0.28s      0.12s      0.41s        -1274695.00
highs                   0.27s      2.69s      2.96s        -1274695.00
highs-parallel          0.26s      2.67s      2.94s        -1274695.00
scip                    0.30s     18.98s     19.28s        -1274695.00
==================================================================================
Allir leysar fundu sama hlutlægisgildi - líkönin eru samhljóða.
```

### Fleiri en eitt gagnasafn - hvernig leysar skala

`benchmark.py` tekur við mörgum input.json slóðum í einu og prentar að lokum
eina sameiginlega samantekt þvert á þau öll - gagnlegt til að sjá hvort
hraðamunur leysa haldist eins þegar líkön stækka, ekki bara á einu prófunar-
gagnasafni:

```
python3 benchmark.py ../docs/1year/input.json ../docs/2year/input.json \
  ../docs/3year/input.json ../docs/4year/input.json \
  --solvers gurobi,highs,highs-parallel,scip --time-limit 180
```

`--time-limit SEK` setur hámarks lausnartíma per leysi (allir þrír styðja
þetta - Gurobi `TimeLimit`, SCIP `limits/time`, HiGHS `time_limit`).
Nauðsynlegt fyrir SCIP á stærri gagnasöfnum - án tímamarka lenti það í
"numerical troubles" á `docs/3year` og hékk án framfara í >30mín þar til
keyrslan var drepin handvirkt. Ef tímamörk nást áður en besta lausn er
staðfest er besta lausn sem fannst samt birt, merkt `(?)`.

Niðurstöður á öllum fjórum sögulegu gagnasöfnunum (`docs/1year`–`4year`,
Apple M4 Max, `--time-limit 180`):

```
Gagnasafn    Leysir             Uppbygging      Lausn    Samtals     Hlutlægisgildi
----------------------------------------------------------------------------------------------
1year        gurobi                  0.04s      0.02s      0.05s            7708.00
1year        highs                   0.04s      0.06s      0.09s            7708.00
1year        highs-parallel          0.03s      0.05s      0.09s            7708.00
1year        scip                    0.05s      0.16s      0.22s            7708.00
2year        gurobi                  0.03s      0.02s      0.05s            8096.00
2year        highs                   0.03s      0.05s      0.08s            8096.00
2year        highs-parallel          0.03s      0.05s      0.08s            8096.00
2year        scip                    0.03s      0.20s      0.23s            8096.00
3year        gurobi                  0.81s      1.32s      2.14s         -133535.00
3year        highs                   0.77s     84.20s     84.97s         -133535.00
3year        highs-parallel          0.76s     84.78s     85.54s         -133535.00
3year        scip                    0.92s    180.03s    180.95s    701873884.83 (?)
4year        gurobi                  0.27s      0.14s      0.41s        -1274695.00
4year        highs                   0.29s      0.60s      0.89s        -1274695.00
4year        highs-parallel          0.27s      0.59s      0.86s        -1274695.00
4year        scip                    0.30s     44.23s     44.53s        -1274695.00
```

Athugasemdir:
- Á litlu gagnasöfnunum (1year, 2year) er nánast enginn munur - allir leysar
  klára á broti úr sekúndu og finna sama hlutlægisgildi.
- Á `3year` (stærst, ~88þ. breytur - einnig gagnasafnið sem olli
  "numerical troubles" hjá SCIP) vinnur Gurobi afgerandi (2.14s). HiGHS og
  HiGHS-parallel eru bæði ~85s (staðfestir aftur að samhliða leit hjálpar
  ekki hér). **SCIP nær ekki bestu lausn innan 3ja mínútna** - besta gildi
  sem það fann (701873884.83, ekki staðfest) er víðsfjarri réttu svari
  (-133535).
- Á `4year` er Gurobi hraðast (0.41s), HiGHS rétt á eftir (~0.89s), og SCIP
  er hægt en finnur þó rétt svar (-1274695) á 44.5s.
- Niðurstaðan: forskot Gurobi á HiGHS vex verulega með stærð líkansins - það
  sem leit út eins og lítill munur á litlu prófunargagnasafni verður að
  tugum sekúndna mun á stærsta raunverulega gagnasafninu. Þetta er vert að
  hafa í huga ef Gurobi-leyfi er til staðar og hraði skiptir máli á stórum
  árgöngum.

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
sögulegt gagnasafn. `example_input.json` (rót `data/`) er eina skjalið hér
sem er í git - staðgengill fyrir alvöru `input.json` með nöfnum/kennitölum/
símanúmerum nemenda og deildarstjóra skipt út fyrir tilbúin gildi (sjá
`anonymize_example.py`), notað í `benchmark.py`/prófunum án þess að alvöru
persónugögn þurfi að vera í boði.

Flutningsskriftur (allar taka `--help`-laust inn/út slóðir sem rök):
- `sameina_gogn.py <mappa> <útskjal.xlsx>` - les þrjú upprunaleg Excel-skjöl
  úr einni möppu og býr til eitt sameinað, normalíserað `.xlsx` skjal (sama
  snið og Google Sheet vinnuskjalið notar, með dropdown-staðfestingu
  tilbúinni) - nota til að "sá" (seed) vinnuskjalið með sögulegum gögnum.
- `xlsx_til_json.py <sameinad.xlsx> <input.json>` - breytir sameinaða
  skjalinu í input.json, sama snið og "Sækja gögn" í Google Sheet skilar -
  til að prófa `src/main.py` án þess að fara í gegnum Sheets.
- `mrs_radad_ur_json.py <output.json> <útmappa>` - endurskapar upprunalegu
  `mrs_radad_<námskeið>.xlsx` skjölin úr output.json (sjá `docs/` að neðan).
- `anonymize_example.py <mappa> <example.json>` - skiptir út
  nöfnum/kennitölum/símanúmerum fyrir tilbúin gildi, notað til að útbúa
  `example_input.json`.

## `docs/` - raunveruleg söguleg gögn (aldrei í git)

`docs/1year`–`4year` innihalda raunveruleg (ekki nafnlaus) inntaksskjöl fyrir
fjögur skólaár - `.gitignore`d í heild sinni (sjá athugasemd þar) þar sem
engin nafnlaus útgáfa er til fyrir þessi gögn, ólíkt `data/`.

`keyra_prof.sh` (rót `scans/`) keyrir alla leiðina fyrir hvert ár í `docs/`:
sameinar xlsx skjölin, breytir í input.json, leysir (sjálfgefið `--solver
highs`), og endurskapar `mrs_radad_*.xlsx` í `radad_nytt/` - gagnlegt til að
staðfesta að breytingar á `src/` virki enn á raunverulegum, sögulegum gögnum,
ekki bara `data/example_input.json`:

```
./keyra_prof.sh [--solver highs|gurobi|scip|highs-parallel]
```

## Hvers vegna JSON, ekki Excel

Upprunalega útgáfa þessa verkefnis las/skrifaði Excel-skjöl beint. Það gerði
tvöfalda villuleit erfiða: dagsetningar og vikunúmer voru handslegin inn á
mörgum stöðum með enga leið til að staðfesta að þau stemmdu saman fyrr en
eftir á. Núverandi hönnun færir alla gagnastaðfestingu inn í Google Sheet
sjálft (dropdown-listar sem koma í veg fyrir ógildar tilvísanir, sjálfvirk
athugun á viku-á-móti-dagsetningu), þannig að `src/` þarf aldrei að takast á
við óstaðfest gögn - það les eingöngu already-staðfest input.json.
