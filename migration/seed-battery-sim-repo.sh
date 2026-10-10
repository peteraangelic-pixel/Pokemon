#!/bin/bash
# Wypełnia PUSTE repo zawartością projektu battery-sim (czysty main, bez historii Pokemon).
#
# Użycie (wymaga zalogowanego gh jako użytkownik, NIE tokena aplikacji Arena):
#   1) załóż puste repo:   gh repo create battery-sim --public
#                         (lub przez WWW: New repository -> nazwa: battery-sim, publiczne, bez README)
#   2) uruchom:            bash migration/seed-battery-sim-repo.sh [owner/repo]
#                         (domyślnie: peteraangelic-pixel/battery-sim)
#
# Po zakończeniu: projekt jest na main, a CI (lint + test + sweep-full) odpala się
# automatycznie przy pushu i ręcznie przez przycisk "Run workflow".
set -euo pipefail
REPO=${1:-peteraangelic-pixel/battery-sim}
ROOT="$(cd "$(dirname "$0")/.." && pwd)" # katalog główny tego repozytorium
cd "$ROOT"
[ -d battery-sim ] || { echo "Brak battery-sim/ w $ROOT"; exit 1; }
[ -f .github/workflows/ci.yml ] || { echo "Brak .github/workflows/ci.yml"; exit 1; }
[ -f migration/newrepo-README.md ] || { echo "Brak migration/newrepo-README.md"; exit 1; }

tree_json='[]'
add_file() {
  local src="$1" path="$2" b64 sha
  b64=$(base64 -w0 "$src")
  sha=$(jq -n --arg c "$b64" '{content:$c, encoding:"base64"}' \
    | gh api "repos/$REPO/git/blobs" --method POST --input - | jq -r .sha)
  tree_json=$(jq -c --arg p "$path" --arg s "$sha" \
    '. + [{mode:"100644",type:"blob",sha:$s,path:$p}]' <<<"$tree_json")
  echo "  blob: $path"
}

echo "== tworzę bloby w $REPO =="
while IFS= read -r f; do add_file "$f" "$f"; done < <(find battery-sim .github -type f -not -path '*/target/*' | sort)
add_file migration/newrepo-README.md README.md

echo "== tree + commit + ref refs/heads/main =="
tree_sha=$(jq -n --argjson t "$tree_json" '{tree:$t}' \
  | gh api "repos/$REPO/git/trees" --method POST --input - | jq -r .sha)
msg="battery-sim: symulator projektowania baterii (Rust + rayon) + CI

Kryteria 'nowej baterii': energia >= Li-ion (baseline 236.9 Wh/kg),
>=500 cykli przy szybkim ladowaniu (2C-3C), brak eksplozji w tescie
abuse (piec 150C + overcharge 1C przez 3 h).

CLI: demo | cell | sweep | list | baseline | benchmark | report.
Sweep po siatce kombinacji (katoda x elektrolit x anoda x loading x N/P
x C-rate x temperatura), rownolegle przez rayon. Metryki rynkowe:
Wh/kg pakietowe, Wh/L, koszt materialowy \$/kWh. Wyniki CSV.

Najlepszy kandydat: NMC811 + Si-C + GEL @ load=30 mg/cm2
-> 278.8 Wh/kg (200.7 pakiet), 994 Wh/L, ~670 cykli @2C, PASS
wszystkich kryteriow (w tym abuse 150C).

CI (GitHub Actions): lint (fmt + clippy), test (build + demo + quick
sweep + benchmark + raporty PL/EN), sweep-full (siatka chemiczna -> CSV)."
commit_sha=$(jq -n --arg m "$msg" --arg t "$tree_sha" '{message:$m, tree:$t}' \
  | gh api "repos/$REPO/git/commits" --method POST --input - | jq -r .sha)
gh api "repos/$REPO/git/refs" --method POST -f ref=refs/heads/main -f sha="$commit_sha"
gh api -X PATCH "repos/$REPO" -f default_branch=main
gh repo edit "$REPO" --add-topic battery,simulator,rust,rayon,energy-storage >/dev/null 2>&1 || true

echo "== gotowe =="
echo "Repo:  https://github.com/$REPO"
echo "CI:    https://github.com/$REPO/actions"
echo "Push na main odpala lint + test + sweep-full; ręczny bieg: przycisk 'Run workflow'."
