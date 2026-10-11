# v15 testy: nasze najlepsze agenty vs dokładne decki z przegranych v14

2026-10-11. FFI gauntlet (libcg.so), 30 gier/matchup, ten sam agent po obu stronach
(limitacja: nie da się symulować policy rywala).

## Decki oponentów wyciągnięte 1:1 z 8 replayów v14 → `decks/v14_losses/`

| Oponent (rank) | Archetyp | v14 live | v14 combo (v11f+29W) | ich v15#1 (v11+30W) |
|---|---|---|---|---|
| F.A.Nina (198) | Lucario 13E | L | 0.800 | **0.900** |
| Kevin Hulin (226) | Dragapult 10E | W | 0.900 | 0.867 |
| tanzaku (214) | Ogerpon 14E | L | 0.700 | **0.800** |
| (ノ◡ <) (157) | Lucario 14E | L | 0.833 | 0.667 |
| auto-mirror (222) | 29W | L | 0.300 | **0.667** |
| vrmichalski (155) | 35E | W | 0.267 | **0.633** |
| Tom Curry11 (246) | 35W | L | 0.367 | 0.467 |
| vrmichalski (155) | 35E | L | 0.533 | 0.433 |
| **Σ 240 gier** | | 2W-6L | **0.588** | **0.679** |

Fix mirror jest duży (0.27–0.30 → 0.63–0.67). Słabe punkty v15#1: Lucario 14E (0.667),
mirror 35W (0.43–0.47).

## Combo na 3 poolach (FII, pełny sampel)

| Combo | broad 39 (30g) | top30 23 (20g) | loss8 (30g) |
|---|---|---|---|
| A: v11 + v12_30_boss4 (ich v15#1) | 0.611 | 0.807 | **0.679** |
| B: v11f + v12_30_boss4 (ich v15#2) | **0.626** | — | 0.658 |
| C: v11f + v10_34_sig4 (mój plan) | **0.632** | 0.807 | 0.642 |
| D: v11f + v13_29_top30 (wysłany v14) | 0.580 | 0.74–0.78 | 0.588 |

- Ich zgłoszone liczby (broad 0.692 / top30 0.87–0.89) to sampel 2–8 gier/deck →
  na pełnym sampelu: 0.611–0.626 / 0.807. Kierunek (30W > 29W) potwierdzony.
- Agent v11 vs v11f: identyczny wynik na loss8 (158-82) — H1/gust-tweaki nie
  zadziałają na tym poolu (są pod walls Sylveon/Crustle i endgame mill).
- v15#1 = najlepszy na loss8 (co teraz najbardziej liczy się), v10_34 (C) = najlepszy
  na weak/broad.

## Werdykt

Submit: `phase1_tuned_v15_30_boss4_v11` (#1) + ewentualnie `v15_34_sig4_v11f` (#2 backup).
Następna dźwignia (gen8, tempo-aware evolution) powinna jechać na decku 30W.
