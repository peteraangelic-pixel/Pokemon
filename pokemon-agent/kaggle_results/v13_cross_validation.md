# Cross-validation: v12b/v13 LOW_E_AGGRO rule — REJECT (100g)

2026-10-11. Druga gałąź (582deeb, 9a5bf9b): "structural opening fix" —
LOW_E_AGGRO_IDS (16 ID) → w _fighter_score: Kyogre(721) −150, Snover(722) +80
gdy aktywny rywala z listy. Klaimy 20-30g: v14 pool 0.686, top30 0.835,
broad 0.622, tempo fitness 0.751.

## 100 gier/matchup (mój protokół, 10 matchupów, 30W deck)

| Matchup | v11 | v11f | **v13 (v11f+reguła)** |
|---|---|---|---|
| tanzaku Ogerpon 14E | 0.81 | 0.74 | **0.61** |
| meta:YumeNeko Ogerpon 14E | 0.74 | 0.81 | **0.51** |
| meta:OceanMix Lucario 13E | 0.89 | 0.88 | **0.61** |
| F.A.Nina Lucario 13E | 0.85 | 0.81 | **0.63** |
| (ノ◡ <) Lucario 14E | 0.75 | 0.83 | **0.67** |
| Kevin Hulin Dragapult 10E | 0.92 | 0.92 | **0.69** |
| vrmichalski 35E ×2 | 0.50/0.59 | 0.52/0.45 | 0.42/0.49 |
| Tom Curry 35W | 0.55 | 0.53 | 0.42 |
| auto-mirror 29W | 0.51 | 0.51 | 0.52 |
| **Σ 1000 gier** | **0.711** | **0.700** | **0.557** |

Reguła: −14.3 pkt vs baza v11f (1000 gier), z załamaniem aggro:
Ogerpon −20..−30, Lucario −17..−27, Dragapult −23. Tempo (t9): 1.12→1.23
lekko lepiej, ale za 14 pkt winrate — proxy metryka wygrywa kosztem wygrań.

## Werdykt

- **v12b/v13 (LOW_E_AGGRO): REJECT** — klaimy 20-30g to szum (±15%/matchup).
- **v15_30_boss4_v11 (v11+30W) = 0.711** — nadal najlepszy combo; v11f (0.700)
  statystycznie równoważne.
- Hard rule dla obu gałęzi: **każda zmiana strukturalna weryfikowana ≥100g na
  realnych deckach PRZED submitem** (screen 20-30g → verify 100g). To samo
  dotyczy wag (gen8 plateau) i reguł (v12b) — 2 gałęzie, 3 nieudane "best"
  (gen8 temp, v13) wszystkie upadły na 100g.
