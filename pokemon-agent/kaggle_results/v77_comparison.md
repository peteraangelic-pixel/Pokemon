# Porownanie: nasza v76 vs c87 v77_rl (2026-10-19)

Ich v77: BC2000 (match 0.891) + soft lethal +200 + gated margin>=250,
talia Judge, champion.py jako osobny plik w paczce (2.0M). Wyslana
przez c87 (e7f5d27). Deklaracja: H2H 0.600 vs v67 (12-8 = 20 gier).

## Clean-room (jak Kaggle), prizetest 600g
| test | ich v77 | nasza v76 |
|---|---|---|
| vs v67 | 0.483 | **0.517** |
| vs champion | 0.508 | **0.552** |
| H2H bezposrednie | 0.477 | **0.523** |

Ich paczka tym razem NIE crashuje (poprawili import championa po
ERRORze v75_rl_lethal). Mimo to nasza v76 (BC 6000g + PPO, lethal-win
override) wygrywa kazdy test przyczynowy. Deklarowane 0.600 to 20 gier.
Zywy wynik v77: poll c87 w toku.
