# gen8: tempo-aware config evolution — WYNIK (plateau)

2026-10-11. Celem było przebicie v11 (agent z ich v15) szukaniem w 26 wagach
PTCG_* z fitness tempowym: `0.65*wwr + 0.20*t9 + 0.15*early_first_prize`,
pool = 8 decków z przegranych v14 (w3) + 6 meta (w2) + 11 weak (w1).

## Urządzenia

- `tools/evolve_gen8.py` — szybka ścieżka (sandbox), FFI do libcg.so, agent
  in-process, 26 wag z env, tempo (t9, first-prize turn) mierzone per gra.
- `rust/src/bin/evolve_tempo.rs` + `rust/worker_eval.py` — trwały port
  **Rust+Rayon** (orkestracja natywna, eval przez worker subprocess z
  realnym Python agentem + engine). Build na Actions (`rust-build.yml` +
  `evolve_gen8.yml`, pop 150 × 5 gens × 30g, 2 vCPU).

## Wynik sandbox (4 gens × 80, 30g/matchup)

- Top gen0: f≈0.72, wwr≈0.79–0.82, t9 1.31–1.36, fp 8.2–8.5.
- **Ale**: niezmieniona baza v11 (d={}) też w top5 (f=0.697, wwr 0.814).
  Przy 30g/matchup szum ≈ ±2% wwr — selekcja na tym sampelu szumowa.

## Werdyfikacja 100 gier/matchup (decydująca)

| Kandydat | wr (10 matchupów) | t9 | fp |
|---|---|---|---|
| **base v11 (bez zmian)** | **0.711** | 1.11 | 8.6 |
| gen8_best (gen0 #1) | 0.685 | 1.18 | 8.4 |
| gen8_tempo | 0.704 | 1.12 | 8.7 |

**Wynik: konfig waga-v11 jest w optimum (plateau) tej rodziny heurystyk.**
160+ kandydatów, żaden nie przebił bazy na 100g. Druga niezależna ewolucja
(gen0–gen7 na drugiej gałęzi) też zbiegła do v11/v11f — dwa niezależne
wyszukiwania, ten sam punkt.

## Wniosek operacyjny

1. **Do submitu: ich `v15_30_boss4_v11` (v11 + 30W)** — potwierdzony
   najlepszy combo same-policy (loss-pool 0.679 vs v14 0.588; 100g core 0.711).
   Moje gen8 nic lepszego nie dało.
2. Dalszy zysk w tej architekturze = zmiany **strukturalne** (nowe reguły
   decyzyjne), nie tune'owanie 26 wag. To już nie jest "gen8 config search" —
   to nowy heurystyk (kandydat do połączenia z pracą drugiej gałęzi).
3. Duży run Rust na Actions (pop 150 × 5 gens) działa jako potwierdzenie
   plateau z 10× mocą obliczeniową; wynik wróci commitem do tej gałęzi.

## Słabe punkty v11+30W (100g)

- 35W/35E mirrory: 0.42–0.59 (najgorsze matchupy — ściana mid-tieru)
- (ノ◡ <) Lucario 14E: 0.75, tanzaku Ogerpon: 0.81, F.A.Nina Lucario 13E: 0.85
