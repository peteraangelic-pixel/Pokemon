# Analiza live 2026-10-17 (submisje nocne, fetch c87)

## Bilans
- NASZA v63 super fix (57290311): 31W-44L = 0.413 (75 gier), rating 611.8 -> 399.7 (kalibracja)
- ICH v70g Alakazam (57290256): 34W-33L = 0.507 (67 gier), rating 220.5 -> 358.5

## Taksonomia 77 porazek (wszystkie z replayami)
v63 (44): ABOMASNOW mirror 15 (wipe 9, sr. 1.0 nagr.), OTHER 7, DRAGAPULT 5, ALAKAZAM 4,
HYDRAPPLE 5, CRUSTLE+KANGA 4, FROSLASS 3, LUCARIO 1.
Klasy v63: famine 0 nagrod = 23/44 (52%), 1-2 nagr. = 12, wyscig >=3 = 8, wipe przy prowadzeniu = 6.
v70g (33): famine 15/33 (45%), mirror 10.

## Testy lokalne (mirror, prizetest.py)
- baza v63: WR 0.512, porazki z 0 nagrod = 56%, sr. nagrod w porazkach 1.17 (live: 52% / 1.0) — famine odtwarza sie lokalnie
- wariant tempo (-2E +2 Mega Signal): WR 0.507, famine 54% — brak poprawy
- wczesniej odrzucone: bench-guard pilot, +Night Stretcher, +2 Poffin (famine/empty-bench bez zmian)

## Wniosek
Dominujacy wyciek to mirror Abomasnowa i wyscig o pierwszego Abomasnowa (przegrany bierze ~0 nagrod),
nie klasyczne czyszczenie lawki przy prowadzeniu (6/44). Kierunek: pilot pod mirror (ochrona Snovera,
wczesny Kyogre do snajpienia Snovera), nie kolejne zamiany kart.
