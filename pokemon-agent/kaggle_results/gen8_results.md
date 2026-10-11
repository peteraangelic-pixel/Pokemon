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

---

## Cross-validation @100g — REJECT (2026-10-11, merge 6e0d5fd)

The other branch's Rust search produced a new best config (`gen8_rust.json`,
run 38149708032: best wwr 0.8126/570g @30g, 26 keys changed vs v11).
Baked verbatim into `agents/main_heuristic_gen8r.py` and verified:

| agent | loss8+meta @100g | mirror | tanzaku | YumeNeko |
|---|---|---|---|---|
| **v11** | **0.711** | 0.51–0.59 | 0.81 | 0.81 |
| v11f | 0.700 | 0.50–0.55 | 0.80 | 0.80 |
| **gen8r (Rust best)** | **0.654** | 0.42–0.54 | 0.75 | 0.70 |
| gen8_tempo (theirs) | 0.584 | — | — | — |
| v13 LOW_E_AGGRO | 0.557 | — | — | — |

**REJECT gen8r** — 3rd independent confirmation that 30g/matchup evolution
fitness (even Rayon-parallel Rust) does not transfer to 100g winrate.

## Mirror rule attempts — REJECT

Mirror (4/10 core matchups, 0.42–0.59 for every variant) is the only
structural weakness. Tested Kyogre-lead vs Snover-lead rules in
`_fighter_score` when opp active ∈ {721,722,723}:
- M1 (Kyogre +120, Snover −60): mirrors 0.487
- M2 (Kyogre +60, Snover −30): mirrors 0.468
- v11 control: mirrors 0.505 (per-matchup 0.47–0.55)

All statistically identical (engine is non-deterministic: identical 50g setup
replays as 45-50 vs 42-50). **Mirror is a robust coin flip** — symmetric
equilibrium vs the same deck; needs mill-race timing changes to break, not
lead-order tweaks. Note: 121975039 (newest replay) is exactly this —
our two live v14 submissions auto-mirroring, 3-by-T9 vs 2-by-T9.

**Decision: v11 (0.711) remains the refined version** — already in the
submitted v15 bundles. Nothing from either branch's gen8/v12/v13/
deck-search work survived 100g validation.
