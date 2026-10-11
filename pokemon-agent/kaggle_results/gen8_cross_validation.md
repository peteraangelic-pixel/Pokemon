# Cross-validation: ich gen8 (55277c2) vs mój v11 — 100g/matchup

2026-10-11. Druga gałąź commit `55277c2`: "gen8: tempo fitness evolution …
first prize T4.5 prize_T9 4.0 better than leaders T6-7/2.2, v16 gen8 1.000
vs Lucario/Ogerpon".

## Czerwone flagi w ich danych (zanim cokolwiek uruchomiłem)

- `kaggle_results/tempo_latest.json` (62W-20L): `first_prize_turn: 15.7`,
  `prize_by_T9: 1.82` — **nie** T4.5/4.0 jak w commit message.
- "4.5/4.0" = błąd metryki: średnia per-deck przy **2 grach na matchup**
  + sentinel 99 dla "nigdy" (per-deck w best.json: alakazam first=99,
  charizard first=5.5 prize_T9=4.0 przy 2 grach…).
- Pool ewolucji = archetypy-szablony (bronzong_lock, charizard_mega,
  sylveon_safeguard, crustle_wall, …), nie decki top30; "1.000 vs Lucario/
  Ogerpon" ≈ 2–4 gry na matchup.

## Moja walidacja (ten sam protokół co v11: 100 gier/matchup, 10 matchupów)

| Matchup (100g) | v11+30W | ich gen8+30W |
|---|---|---|
| tanzaku Ogerpon 14E | 0.81 | **0.55** |
| meta:YumeNeko Ogerpon 14E | 0.74 | **0.49** |
| meta:OceanMix Lucario 13E | 0.89 | 0.64 |
| F.A.Nina Lucario 13E | 0.85 | 0.70 |
| (ノ◡ <) Lucario 14E | 0.75 | 0.72 |
| Kevin Hulin Dragapult 10E | 0.92 | 0.77 |
| vrmichalski 35E ×2 | 0.50 / 0.59 | 0.46 / 0.51 |
| Tom Curry 35W | 0.55 | 0.49 |
| auto-mirror 29W | 0.51 | 0.51 |
| **Σ 1000 gier** | **0.711** | **0.584** |

Tempo: v11 t9=1.11 fp=8.6 vs gen8 t9=1.27 fp=8.8 (porównywalne, nie lepsze).

H2H gen8 vs v11 (ten sam deck, 200g, seats na przemian): 0.515 — szum.

## Werdykt

**Ich gen8 to pułapka: overfit na 2-grywowy pool archetypów.** Na realnych
deckach traci −12.7 pkt vs v11 (1000 gier), z załamaniem Ogerpon 0.81→0.55.
- **Nie submitować `phase1_tuned_v16_gen8_tempo`.**
- **Submit pozostaje: `v15_30_boss4_v11`** (v11 + 30W) — potwierdzony
  najlepszy combo (0.711 core 100g, 0.679 loss-pool 30g).
- Ich `gauntlet_tempo.py`/`search_gen8.py` warto przejąć do mojej
  infrastruktury, ale fitness musi weryfikować finalistów na ≥100g/matchup
  na realnych deckach (dwustopniowo: screen 20g → verify 100g).
