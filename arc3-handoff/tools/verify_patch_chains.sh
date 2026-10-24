#!/usr/bin/env bash
# Odtwarza DOWÓD run-killera i weryfikuje nasze patche na prawdziwym drzewie harnessa.
#
# Co robi: buduje pristine drzewo ARC3-Inference (42 pliki z bundle r033 = stan PRE-patch),
# a potem nakłada patche DOKŁADNIE komendami z cell 9 ich notebooka:
#     git apply --include=ARC3-Inference/* <patch>     (cwd = <bundle>/src, check=True)
# i raportuje cztery łańcuchy:
#   A   franzen -> 0001 -> 0002 -> 0003b -> 0004            (nasz pełny zestaw)   => MUSI być OK
#   B   franzen -> 0001 -> 0002 -> 0004                     (0004 bez 0003b)       => MUSI być FAIL
#   B'  franzen -> 0001 -> 0002 -> 0004-standalone          (zalecane wpięcie)     => MUSI być OK
#   C   franzen -> 0001 -> 0002 -> ich stary 0003           (dowód run-killera)    => MUSI być FAIL
#
# Na końcu py_compile całego solver.py + testy jednostkowe (16, offline, bez GPU).
#
# Użycie:  ./verify_patch_chains.sh [katalog_z_pristine_bundle] [katalog_z_patchami]
#          domyślnie: ../bundle/src  i  ../patches  (względem tego skryptu)
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRISTINE="${1:-$HERE/../../bundle/src}"     # drzewo ARC3-Inference PRE-patch (tools/fetch_repo_artifacts.sh)
PATCHES="${2:-$HERE/../patches}"
WORK="${WORK:-/tmp/arc3-verify}"

[ -d "$PRISTINE/ARC3-Inference" ] || { echo "BRAK pristine drzewa: $PRISTINE/ARC3-Inference"; echo "  -> uruchom tools/fetch_repo_artifacts.sh"; exit 2; }
[ -d "$PATCHES" ] || { echo "BRAK patchy: $PATCHES"; exit 2; }

# łańcuch C potrzebuje ich ORYGINALNEGO 0003; jeśli go nie ma, wyciągnij z notebooka
if [ ! -f "$PATCHES/duck-extra-02.patch" ] && [ -f "$PRISTINE/../../bundle/duck-v7.ipynb" ]; then
  echo "[i] brak duck-extra-02.patch - wydobywam z notebooka"
  python3 "$HERE/extract_notebook_patches.py" "$PRISTINE/../../bundle/duck-v7.ipynb" "$PATCHES" >/dev/null
fi

fresh() {  # $1 = katalog roboczy
  rm -rf "$1"; mkdir -p "$1"
  cp -a "$PRISTINE/ARC3-Inference" "$1/"
  cd "$1"
}

chain() {  # $1 = etykieta, reszta = patche
  local label="$1"; shift
  local ok=1 p
  echo
  echo "=== $label ==="
  for p in "$@"; do
    if git apply --include='ARC3-Inference/*' "$PATCHES/$p.patch" 2>/tmp/arc3_apply_err.txt; then
      echo "  OK   $p"
    else
      echo "  FAIL $p"
      sed 's/^/       /' /tmp/arc3_apply_err.txt | head -3
      ok=0
    fi
  done
  if [ $ok -eq 1 ]; then
    python3 -m py_compile ARC3-Inference/inference/framework/solver.py 2>/dev/null \
      && echo "  py_compile solver.py OK"
    grep -c "arc3_level_budget" ARC3-Inference/inference/framework/solver.py 2>/dev/null \
      | sed 's/^/  hooki 0004 w solver.py: /'
  fi
  return $((1 - ok))
}

echo "pristine: $(find "$PRISTINE/ARC3-Inference" -type f | wc -l) plików"
echo "solver.py md5 (PRE): $(md5sum "$PRISTINE/ARC3-Inference/inference/framework/solver.py" | cut -c1-12)"

rm -rf "$WORK"; mkdir -p "$WORK"

# --- ŁAŃCUCH A: pełny zestaw ---
fresh "$WORK/A"
chain "A: franzen -> 0001 -> 0002 -> 0003b -> 0004  (OCZEKIWANE: OK)" \
  0000-franzen-harness-changes duck-extra-00 duck-extra-01 \
  0003b-early-abandon-rebased 0004-level-token-cap
A=$?
mkdir -p "$WORK/A/tests" && cp "$HERE/../tests/test_arc3_level_budget.py" "$WORK/A/tests/" 2>/dev/null
if [ $A -eq 0 ]; then
  (cd "$WORK/A" && python3 tests/test_arc3_level_budget.py 2>&1 | tail -3 | sed 's/^/  [testy A] /')
fi

# --- ŁAŃCUCH B: 0004 bez 0003b (kotwica importu) ---
fresh "$WORK/B"
chain "B: franzen -> 0001 -> 0002 -> 0004  (OCZEKIWANE: FAIL na solver.py:47)" \
  0000-franzen-harness-changes duck-extra-00 duck-extra-01 0004-level-token-cap
B=$?

# --- ŁAŃCUCH B': wariant zalecany ---
fresh "$WORK/Bp"
chain "B': franzen -> 0001 -> 0002 -> 0004-standalone  (OCZEKIWANE: OK)" \
  0000-franzen-harness-changes duck-extra-00 duck-extra-01 0004-standalone-level-token-cap
Bp=$?
mkdir -p "$WORK/Bp/tests" && cp "$HERE/../tests/test_arc3_level_budget.py" "$WORK/Bp/tests/" 2>/dev/null
if [ $Bp -eq 0 ]; then
  (cd "$WORK/Bp" && python3 tests/test_arc3_level_budget.py 2>&1 | tail -3 | sed 's/^/  [testy B'"'"'] /')
fi

# --- ŁAŃCUCH C: dowód run-killera ---
fresh "$WORK/C"
chain "C: franzen -> 0001 -> 0002 -> ich stary 0003  (OCZEKIWANE: FAIL => run umiera w cell 9)" \
  0000-franzen-harness-changes duck-extra-00 duck-extra-01 duck-extra-02
C=$?

echo
echo "==================== WERDYKT ===================="
printf "  A  (0003b + 0004)          : %s   [oczekiwane OK]\n"   "$([ $A  -eq 0 ] && echo 'OK   ' || echo 'FAIL ')"
printf "  B  (0004 bez 0003b)        : %s   [oczekiwane FAIL]\n" "$([ $B  -ne 0 ] && echo 'FAIL ' || echo 'OK   ')"
printf "  B' (0004-standalone)       : %s   [oczekiwane OK]\n"   "$([ $Bp -eq 0 ] && echo 'OK   ' || echo 'FAIL ')"
printf "  C  (ich stary 0003)        : %s   [oczekiwane FAIL = run-killer]\n" "$([ $C -ne 0 ] && echo 'FAIL ' || echo 'OK   ')"
echo
if [ $A -eq 0 ] && [ $B -ne 0 ] && [ $Bp -eq 0 ] && [ $C -ne 0 ]; then
  echo "WSZYSTKIE CZTERY ŁAŃCUCHY ZGODNE Z OCZEKIWANIEM."
  echo "Wniosek: cell 9 z duck-extra-02 w patch_files => CalledProcessError => run umiera"
  echo "         przed pobraniem wag. Lekarstwo: 0004-standalone (albo 0003b + 0004)."
else
  echo "ROZJAZD - sprawdź, czy pristine drzewo to na pewno stan PRE-patch (blob 0b69d62)."
fi
