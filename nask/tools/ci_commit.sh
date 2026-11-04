#!/usr/bin/env bash
# Commit + push raportow z runnera GitHub Actions — z ponowieniami.
#
# Dlaczego osobny skrypt: sandbox sesji Arena NIE czyta logow Actions (host blobow
# `productionresultssa*.blob.core.windows.net` -> EOF), wiec jedynym kanalem zwrotnym
# jest commit do repo. Run 6 stracil komplet raportow (129 prob + mining 10,9 MB JS),
# bo krok commitujacy wykonal sie na koncu i padl — stad: (1) commitujemy KAZDY artefakt
# od razu po jego powstaniu, (2) push z 5 probami, (3) porzadek po nieudanym rebase.
#
# Uzycie:  bash ci_commit.sh "<komunikat>" <sciezka> [<sciezka> ...]
set -u

BRANCH="${NASK_CI_BRANCH:-arena/c87f7a48-pokemon}"
MSG="${1:-raport z przebiegu}"
shift || true
if [ "$#" -eq 0 ]; then echo "brak sciezek do commitu"; exit 2; fi

echo "== ci_commit: $# sciezek, komunikat: $MSG"
EXISTING=()
for p in "$@"; do
  if [ -e "$p" ]; then
    echo "   + $p ($(du -sh "$p" 2>/dev/null | cut -f1))"
    EXISTING+=("$p")
  else
    echo "   - $p (NIE ISTNIEJE — pomijam)"
  fi
done
if [ "${#EXISTING[@]}" -eq 0 ]; then echo "brak istniejacych sciezek do commitu"; exit 0; fi

git config user.name  "arena-nask-bot"
git config user.email "arena-nask-bot@users.noreply.github.com"

git add -- "${EXISTING[@]}"
if git diff --cached --quiet; then
  echo "brak zmian do commitu"
  exit 0
fi

# zabezpieczenie: nigdy nic poza nask/reports
BAD=$(git diff --cached --name-only | grep -vE '^nask/reports/' || true)
if [ -n "$BAD" ]; then
  echo "Odmowa: proba commitu czegos poza nask/reports:"
  echo "$BAD"
  exit 3
fi

git commit -m "$MSG" || { echo "commit nieudany"; exit 4; }

for i in 1 2 3 4 5; do
  if ! git pull --rebase origin "$BRANCH"; then
    echo "pull --rebase rc=$? (proba $i) — porzadkuje stan i próbuje dalej"
    git rebase --abort 2>/dev/null || true
  fi
  if git push origin "HEAD:$BRANCH"; then
    echo "push OK (proba $i)"
    exit 0
  fi
  echo "push nieudany (proba $i), czekam 10 s"
  sleep 10
done

echo "push NIE udal sie po 5 probach — raport jest w lokalnym commicie runnera"
exit 1
