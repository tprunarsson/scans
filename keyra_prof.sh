#!/usr/bin/env bash
# Prófunarskript: keyrir alla leiðina - 3 hrá xlsx skjöl -> input.json ->
# leyst output.json -> endursköpuð mrs_radad_*.xlsx - fyrir hvert ár í
# docs/1year, docs/2year, docs/3year, docs/4year.
#
# Keyra frá rót scans/ (eða hvaðan sem er - skriftan finnur sjálf sína
# eigin staðsetningu):
#   ./keyra_prof.sh [--solver highs|gurobi|scip|highs-parallel]
#
# docs/<ár>/ er algjörlega gitignored (raunveruleg persónugögn nemenda) -
# sjá .gitignore. Úttak hvers árs endar í sömu möppu: sameinad.xlsx,
# input.json, output.json, og radad_nytt/mrs_radad_*.xlsx.

set -uo pipefail

SKRIFTUMAPPA="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA="$SKRIFTUMAPPA/data"
SRC="$SKRIFTUMAPPA/src"
DOCS="$SKRIFTUMAPPA/docs"

if [ -x "$SKRIFTUMAPPA/venv/bin/python3" ]; then
  PY="$SKRIFTUMAPPA/venv/bin/python3"
elif [ -x "$SKRIFTUMAPPA/.venv/bin/python3" ]; then
  PY="$SKRIFTUMAPPA/.venv/bin/python3"
elif [ -x "$SKRIFTUMAPPA/../hvsenv/bin/python3" ]; then
  PY="$SKRIFTUMAPPA/../hvsenv/bin/python3"
else
  PY="python3"
fi

SOLVER="highs"
if [ "${1:-}" = "--solver" ] && [ -n "${2:-}" ]; then
  SOLVER="$2"
fi

AR_LISTI=(1year 2year 3year 4year)
TOKST=()
MISTOKST=()

for AR in "${AR_LISTI[@]}"; do
  MAPPA="$DOCS/$AR"
  echo "================================================================"
  echo "=== $AR ==="
  echo "================================================================"

  if [ ! -f "$MAPPA/skraningar.xlsx" ]; then
    echo "[$AR] SLEPPT - engin gögn fundust í $MAPPA"
    MISTOKST+=("$AR: engin gögn")
    continue
  fi

  echo "--- [$AR] 1/4 Sameina xlsx skjöl ---"
  "$PY" "$DATA/sameina_gogn.py" "$MAPPA" "$MAPPA/sameinad.xlsx" || {
    echo "[$AR] MISTÓKST við að sameina xlsx skjöl"
    MISTOKST+=("$AR: sameina_gogn.py")
    continue
  }

  echo "--- [$AR] 2/4 Breyta í input.json ---"
  "$PY" "$DATA/xlsx_til_json.py" "$MAPPA/sameinad.xlsx" "$MAPPA/input.json" || {
    echo "[$AR] MISTÓKST við að búa til input.json"
    MISTOKST+=("$AR: xlsx_til_json.py")
    continue
  }

  echo "--- [$AR] 3/4 Leysa líkanið (--solver $SOLVER) ---"
  (cd "$SRC" && PYTHONPATH=. "$PY" main.py "$MAPPA/input.json" "$MAPPA/output.json" --solver "$SOLVER")
  if [ $? -ne 0 ]; then
    echo "[$AR] MISTÓKST - líkanið fann ekki lausn (sjá $MAPPA/output.json fyrir villuskilaboð)"
    MISTOKST+=("$AR: main.py (engin lausn)")
    continue
  fi

  echo "--- [$AR] 4/4 Endurskapa mrs_radad_*.xlsx ---"
  mkdir -p "$MAPPA/radad_nytt"
  "$PY" "$DATA/mrs_radad_ur_json.py" "$MAPPA/output.json" "$MAPPA/radad_nytt" || {
    echo "[$AR] MISTÓKST við að endurskapa mrs_radad skjöl"
    MISTOKST+=("$AR: mrs_radad_ur_json.py")
    continue
  }

  echo "[$AR] LOKIÐ - sjá $MAPPA/output.json og $MAPPA/radad_nytt/"
  TOKST+=("$AR")
done

echo
echo "================================================================"
echo "=== Samantekt ==="
echo "================================================================"
echo "Tókst (${#TOKST[@]}): ${TOKST[*]:-(ekkert)}"
echo "Mistókst (${#MISTOKST[@]}):"
for m in "${MISTOKST[@]:-}"; do
  [ -n "$m" ] && echo "  - $m"
done

[ ${#MISTOKST[@]} -eq 0 ]
