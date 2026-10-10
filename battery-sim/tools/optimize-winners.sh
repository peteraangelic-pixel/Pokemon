#!/bin/bash
# Zadanie dla PC: optymalizacja zwycięskich architektur (z ANALIZA_GRID.md).
#
# Użycie (po pobraniu repo i pierwszym `cargo build --release`):
#   bash tools/optimize-winners.sh
# Na Windows: Git Bash (instaluje się razem z git) albo wklej komendy
# pojedynczo w PowerShell (patrz README).
#
# Co robi:
#   1. drobna siatka 2880 kombinacji wokół zwycięzców:
#      NMC811/LFP/DRX x LIFREE/SIC/GRAPHITE x LP57/GEL/IONIC/SOLID
#      x load 20/25/30/35 x N/P 1.02/1.05/1.1/1.2 x T -10/0/10/25/45 °C
#      -> optim_winners.csv
#   2. drabiny testowe dla top 12 PASS (komenda `ladder`):
#      - C-rate 1/2/3/4/6C (ile cykli przy każdym tempie ładowania)
#      - abuse 130/150/170/200/250 °C (margines bezpieczeństwa)
#      - moc: rozładowanie 1/2/3/5C przy 25 °C
set -euo pipefail
cd "$(dirname "$0")/.." # katalog battery-sim
BIN=target/release/battery-sim
[ -f "$BIN.exe" ] && BIN="$BIN.exe"
[ -f "$BIN" ] || cargo build --release

echo "== 1/2: drobna siatka 2880 kombinacji (wokol zwyciezcow) =="
"$BIN" sweep --cathodes NMC811,LFP,DRX --anodes LIFREE,SIC,GRAPHITE \
  --electrolytes LP57,GEL,IONIC,SOLID --loadings 20,25,30,35 \
  --nps 1.02,1.05,1.1,1.2 --temps -10,0,10,25,45 --c-rates 2,3 \
  --csv optim_winners.csv --top 25

echo ""
echo "== 2/2: drabiny testowe (C-rate / abuse / moc) dla top 12 PASS =="
"$BIN" ladder --csv optim_winners.csv --top 12

echo ""
echo "Gotowe. Wyniki: optim_winners.csv + tabele powyzej."
echo "Zeby zobaczyc tylko najlepsze PASS:  grep ',true,' optim_winners.csv | head -25"
