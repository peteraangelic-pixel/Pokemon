# v66 wall tempo — walidacja (protokol: jedna regula naraz, replikacje, regresja)

Pomysl z c87 v83 (ochrona Snovera + priorytet energii na lawkowego Snovera),
przetestowany poprawnie: na championie v63, artefakt Python, tools/prizetest.py.

## Mirror Abomasnow (trolley34w vs c87_v44), prizetest
| wariant | n | WR | porazki 0-nagrod | sr. nagrod w porazkach |
|---|---|---|---|---|
| baza v63 | 1800 | 0.472 | 54.2% | 1.30 (pooled) |
| R1 energia na lawke | 1800 | 0.504 | 52.4% | ~1.3 |
| R2 ucieczka Snovera | 1800 | 0.502 | 51.8% | ~1.3 |
| R1+R2 | 1800 | 0.503 | ~52% | ~1.3 |

Efekt prawdziwy, ale skromny: +3pp mirror, -2pp famine. Glod <30% nieosiagniety —
to w duzej mierze wariancja wyscigu ewolucji, nie sama kolejnosc decyzji.

## Regresje
- siatka zywa 200/deck: 0.708 (baza 0.709) — brak regresji
- sciana Crustle 600g: 0.215 (baza 0.237) — w szumie

## Artefakt
agents/v66_wall_tempo.py + bundles/ptcg_v66_wall_tempo_a450.tar.gz
(deck.csv == trolley34w, loader Kaggle ok). Dla porownania c87 v83 (artefakt Python):
0.125-0.135 WR i 81-83% famine w tym samym prizetest — ich liczby byly z benchmarku Rust.
