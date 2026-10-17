# v67 = v63 champion + Kyogre wrapper + R1/R2 (v66) + no-imitation-in-MIRROR (c87 v85)

Wspolny kandydat obu galezi: kazdy mechanizm testowany pojedynczo na artefakcie
Python (tools/prizetest.py, mirror trolley34w vs champion), potem zlozony.

| wariant | mirror n | WR | famine | siatka |
|---|---|---|---|---|
| baza v63 (live 57290311) | 1800 | 0.472 | 54% | 0.709 |
| v66 (R1+R2) | 1800 | 0.503 | 52% | 0.708 |
| v85 sam (talia c87, test u nas) | 2400 pooled | ~0.506 vs baza 0.500 | 55-58% vs 59-60% | - |
| **v67 (stack)** | **2400** | **0.527** | **53%** | **0.714** |

Uwaga: champion c87_v44 jest bajt-identyczny w obu galeziach (2702 linie) —
roznice wynikow A/B pochodzily z harnessu, nie z wersji championa.
Harness c87 (gauntlet_ffi mirror) daje 0% zero-prize i nie odtwarza live;
prizetest odtwarza (live mirror famine ~52-57%).
