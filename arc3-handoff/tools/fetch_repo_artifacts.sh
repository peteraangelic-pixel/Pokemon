#!/usr/bin/env bash
# Ściąga artefakty z gałęzi konkursowej ARC-AGI-3 (Smak-Domu-Konkurs) do katalogu roboczego.
#
# Dlaczego tak, a nie `git clone` / raw.githubusercontent.com:
#   - w piaskownicy agenta dozwolone są TYLKO github.com i api.github.com;
#     raw.githubusercontent.com i codeload.github.com kończą się SSL_ERROR_SYSCALL/timeoutem,
#   - `gh api .../contents/<path>` zwraca PUSTO dla plików >1 MB (serve.log ma 1.13 MB)
#     -> trzeba wziąć SHA z `git/trees?recursive=1` i pobrać `git/blobs/<sha>`,
#   - pełny clone waży >200 MB (kernel outputy r019/r050), a potrzebne są ~4 MB.
#
# Użycie:  ./fetch_repo_artifacts.sh [katalog_wyjsciowy]
set -euo pipefail

REPO="peteraangelic-pixel/Smak-Domu-Konkurs"
REF="arena/5ed750ef-smak-domu-konkurs"
REF_ENC="arena%2F5ed750ef-smak-domu-konkurs"
OUT="${1:-$PWD/arc3-fetch}"

mkdir -p "$OUT/games" "$OUT/meta" "$OUT/bundle"
cd "$OUT"

echo "[1/5] lista blobów (SHA + rozmiar + ścieżka) -> their_tree_snapshot.tsv"
gh api "repos/$REPO/git/trees/$REF_ENC?recursive=1" \
  --jq '.tree[] | select(.type=="blob") | "\(.sha)\t\(.size)\t\(.path)"' > their_tree_snapshot.tsv
echo "      $(wc -l < their_tree_snapshot.tsv) blobów"

# helper: pobierz blob po SHA (działa też dla plików >1 MB)
get_blob() {  # $1=sha $2=plik_wyjsciowy
  gh api "repos/$REPO/git/blobs/$1" -H "Accept: application/vnd.github.raw+json" > "$2"
}

echo "[2/5] 25 oficjalnych gier (environment_files/<g>/<g>/<g>.py) -> games/"
grep -E "environment_files/[^/]+/[^/]+/[^/]+\.py$" their_tree_snapshot.tsv | cut -f1,3 |
  xargs -P 6 -I{} bash -c 'sha=$(echo "{}" | cut -f1); p=$(echo "{}" | cut -f2);
    g=$(echo "$p" | sed -E "s|.*/environment_files/([^/]+)/[^/]+/[^/]+\.py|\1|");
    gh api "repos/'"$REPO"'/git/blobs/$sha" -H "Accept: application/vnd.github.raw+json" > games/$g.py'

echo "[3/5] metadata.json 25 gier (baseline_actions!) -> meta/"
grep -E "environment_files/[^/]+/[^/]+/metadata.json$" their_tree_snapshot.tsv | cut -f1,3 |
  while IFS=$'\t' read -r sha path; do
    g=$(echo "$path" | sed -E "s|.*/environment_files/([^/]+)/.*|\1|")
    get_blob "$sha" "meta/$g.json"
  done

echo "[4/5] bundle ARC3-Inference (r033, stan PRE-patch) -> bundle/src/"
grep "r033-recon-bundle/bundle/src/ARC3-Inference/" their_tree_snapshot.tsv | cut -f1,3 |
  while IFS=$'\t' read -r sha path; do
    rel="${path#*bundle/src/}"
    mkdir -p "bundle/src/$(dirname "$rel")"
    get_blob "$sha" "bundle/src/$rel"
  done

echo "[5/5] notebooki + kernel outputy (duże pliki przez blobs)"
for spec in \
  "arc-agi-3/kaggle/duck-v7/arc3-duck.ipynb:duck-v7.ipynb" \
  "arc-agi-3/kaggle/duck-v7/variant.json:duck-v7-variant.json" \
  "arc-agi-3/kaggle/duck-original/tufa-labs-duck-harness-june-30-milestone-winner.ipynb:duck-original.ipynb" \
  "arc-agi-3/kaggle/ops/request.json:ops-request.json"
do
  path="${spec%%:*}"; out="${spec##*:}"
  sha=$(awk -F'\t' -v p="$path" '$3==p {print $1}' their_tree_snapshot.tsv | head -1)
  [ -n "$sha" ] && get_blob "$sha" "bundle/$out" && echo "      $out ($(stat -c%s "bundle/$out") B)"
done

# serve.log (1.13 MB) i benchmark.json (520 KB) z r019 - tylko na żądanie, bo duże:
#   sha=$(awk -F'\t' '$3 ~ /r019-kernel-output\/output\/serve.log/ {print $1}' their_tree_snapshot.tsv)
#   get_blob "$sha" bundle/r019-serve.log

cat <<EOF

GOTOWE w $OUT:
  their_tree_snapshot.tsv   $(wc -l < their_tree_snapshot.tsv) blobów (SHA/rozmiar/ścieżka) - migawka gałęzi
  games/                    $(ls games | wc -l) gier (.py, $(du -sh games | cut -f1))
  meta/                     $(ls meta | wc -l) × metadata.json (baseline_actions per poziom)
  bundle/src/               $(find bundle/src -type f | wc -l) plików ARC3-Inference (pre-patch)
  bundle/*.ipynb            notebooki duck-v7 (patche w komórkach 4-7) i duck-original (V8)

Następny krok: tools/extract_notebook_patches.py  -> patche, potem tools/verify_patch_chains.sh
EOF
