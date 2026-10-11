# Rust+Rayon gauntlet — status and porting plan

## TL;DR

- `tools/gauntlet_ffi.py` is the **working fast tool** (2026-10-11): direct FFI into
  `libcg.so`, real Python policy on both seats, process-pool parallelism.
  ~8 ms/game single-core (≈20x faster than the kaggle_environments wrapper),
  near-linear with `--workers`.
- This sandbox has **no Rust toolchain** and the network allowlist
  (github.com, pypi.org, npmjs, …) blocks rustup/dist.rust-lang.org, so a new
  Rust binary **cannot be built or verified here**. Everything below is for a
  machine with `cargo`.
- The existing crate (this directory) is 90% of the way to a native gauntlet:
  the engine FFI works; the heuristic is the missing piece.

## What exists

| file | what it is | status |
|---|---|---|
| `src/engine.rs` | FFI contract for `libcg.so` (BattleStart/GetBattleData/Select/BattleFinish, same structs the Python wrapper uses) | **works** — verified driving real games from Rust in prior session |
| `src/heuristic.rs` | rough native heuristic: "first option" for non-main selects, damage-only attack scoring | **incomplete** — not the real policy; it is what makes `rust_full` play badly |
| `src/main.rs` (`rust_gauntlet`) | rayon fan-out over deck pairs, each game runs the **Python agent in a subprocess** (JSON-lines protocol) | works, but per-decision pipe IPC (~0.1–0.5 ms) eats the per-core gain → ≈ same throughput as `gauntlet_ffi.py --workers N` |
| `src/bin/full.rs` (`rust_full`) | native engine + native (rough) heuristic, no Python at all | **crashes**: `abort: Rust cannot catch foreign exceptions` on ENERGY selects, `buffer full. capacity:7` |

## The `rust_full` crash — analysis

- Trigger: ENERGY selects (`stype=4`, context 30, Swirling-Waves energy discard /
  attach) after the rough heuristic has attached a pile of energy. Reproduced
  consistently with the rough policy; **never** with the real Python policy
  (200+ FFI games, 138 ENERGY selects, clean).
- The panic is a C++ exception thrown *inside* `libcg.so` during `Select` and
  unwinding across the FFI boundary. `buffer full. capacity:7` reads like a
  fixed 7-slot engine buffer overflowing.
- Working hypothesis: the rough "first option" policy reaches a board state
  (e.g. an energy attach the real policy would never pick — an 8th energy on a
  line the engine's internal buffer was sized for 7) that trips a real engine
  edge case. The C library then throws instead of rejecting the select.
- Next steps on a dev machine (needs toolchain + gdb):
  1. `gdb` the abort, print the C++ exception type/message — it will name the buffer.
  2. Add a C++ shim (`extern "C" int safe_select(...)`) around `Select` that
     `try/catches` and returns an error code, so one bad select can never abort the process.
  3. Re-derive the ENERGY-select logic from `best_from_search.py::_score_option`
     (it is a *scoring* problem, not "first option").

## Why the speedup here is NOT the 200x from Kaggriculture

In Kaggriculture the whole engine was pure Python, so a Rust engine = 100-200x.
Here the **engine itself is a closed-source C library** (`libcg.so`): the per-step
cost is (a) the C battle simulation, (b) a ~30–60 KB JSON battle snapshot we must
parse, (c) our heuristic decision. Per-core, Rust can only save (b) and (c)
(≈2–4x vs Python `json.loads` + heuristic). The parallel win — which is what
matters for gauntlets — is **N cores × that**, and Python already achieves it:
each `gauntlet_ffi.py` worker is an independent process with its own GIL
(measured: 1 worker 10 s → 2 workers 6 s for 400 games on this 2-core box;
expect ~linear on an 8-core machine).

So the honest model, 8-core machine, 10k games:

| tool | throughput |
|---|---|
| kaggle_environments wrapper (`tools/gauntlet.py`) | ~125 games/s single-core → ~2 min |
| `tools/gauntlet_ffi.py --workers 8` | ~1000 games/s → **~10 s** |
| native Rust+rayon (heuristic ported) | ~2–4x the FFI per-core → ~3–6 s |

The native Rust port is a 3x constant-factor on an already-fast tool. It is
worth doing if we expect to run *millions* of games (evolutionary search over
policy parameters); it is **not** the blocker for top30 gauntlet evaluation,
which the FFI tool handles in seconds.

## Porting plan (machine with cargo)

Goal: replace `src/heuristic.rs` with a faithful port of
`agents/best_from_search.py` (1484 lines, 60 functions) and have `rust_full`
play the real policy.

### 1. Data layer (mechanical)

- `data/cards.json` + `data/attacks.json` → `src/db.rs`:
  `serde_json::from_str::<Vec<Card>>` at startup; `Card`/`Attack` structs mirror
  the JSON keys (`id, n, ct, b, hp, atk[], skills[], energyType, gu, ex, mex, …`).
  Build `by_name: HashMap<String, Vec<u32>>` exactly like
  `best_from_search.py::_load_card_index`.
- The tuning env knobs (`_env_int`, lines 231–280) → `Tuning` struct read once
  from env at startup (same names: `T_*`).

### 2. Observation layer (mechanical, highest bug-risk)

- Define Rust structs for the JSON `obs`: `Current { your_index, turn, players: [Player;2], active, bench, prize, stadium, … }`,
  `Select { context, type, min_count, max_count, options: Vec<Option> }`,
  `Option { type, area, player_index, index, card_id, count, energy_index, … }`.
- **Derive `Deserialize`**, do NOT hand-map fields. The Python code reads
  dict keys with `.get()` everywhere — a missing-key panic in Rust is the
  classic port bug. For every `.get()` in the Python, use
  `opt.get("x").cloned().unwrap_or(default)` in Rust.
- Port the accessor helpers first, verbatim: `_sel_card_id`, `_hand_id`,
  `_board_card_id`, `_pokemon_at`, `_active`, `_bench` (lines 502–596).

### 3. Domain scoring (the real work — port function by function, same order)

Port in this dependency order, keeping function names so the diff stays reviewable:

1. card predicates: `card`, `cname`, `ctype`, `is_pokemon`, `is_basic_pokemon`,
   `attack_data`, `prize_value` (374–411)
2. plan: `_build_plan`, `is_primary_line`, `plan_power` (417–495)
3. energy/deck math: `_energy_id_of`, `_deck_energy_remaining`,
   `_deck_energy_rate`, `_count_for_each` (598–690)
4. damage model: `_estimate_damage_raw`, `damage_prevented`,
   `_wall_gust_bonus`, `estimate_attack_damage` (691–842) — this is the heart;
   keep the integer arithmetic identical (Python ints are arbitrary precision,
   but all values here fit `i32`; still use `i64` to be safe)
5. attack readiness: `_mill_would_deck_us_out`, `_best_attack_damage`,
   `_cheapest_attack_cost`, `_energies_needed`, `_attack_ready`,
   `_fighter_score` (843–953)
6. card valuation + option scoring: `card_value`, `_copies_in_hand`,
   `_discard_rank`, … through the main `_score_option` dispatcher (~955–1484)

For each function: translate, then **unit-test it** with 2–3 hand-picked obs
snapshots (save real JSON snapshots from `tools/gauntlet_ffi.py` runs — dump
`obs` on a few interesting steps — and assert Rust output == Python output).

### 4. Driver

- `rust_full` main loop = the Python `gauntlet_ffi.py::_run_pair` logic:
  `BattleStart → loop { GetBattleData → decide → Select } → BattleFinish`,
  alternating seats, per-deck-pair result aggregation.
- `rayon::parallel_iter` over `(our_deck, opp_deck)` pairs; `--games`,
  `--workers` (rayon pool size), `--only` filter — same CLI as `gauntlet_ffi.py`
  so results are directly comparable.
- **Do not use `rust_gauntlet`'s subprocess protocol** — the whole point is
  zero Python.

### 5. Acceptance gate (before trusting any native number)

1. `rust_full` mirror (our deck vs itself, 200 games, both seats) must be
   0.45–0.55 and within ±0.03 of `gauntlet_ffi.py` on the same 200 seeds.
2. `rust_full` vs all 20 top30 decks must be within ±0.03 of the FFI tool
   per deck (80 games each).
3. Zero `Select` errors across 5000 games (the ENERGY-select crash must be gone).

## Immediate local command (no build needed, for reference)

```bash
cd pokemon-agent
.venv/bin/python tools/gauntlet_ffi.py \
  --agent agents/best_from_search.py \
  --our-deck decks/v10_34_sig4.csv \
  --opp-dir decks/top30_live \
  --games 8 --workers $(nproc)
```
