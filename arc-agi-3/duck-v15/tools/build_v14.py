#!/usr/bin/env python3
"""Build `arc3-duck-v14.ipynb` from the shipped v13.2 package.

v14 = v13.2 (`6b10853`) with **four** changes, every one of them either measured or a
crash-hardening. It deliberately does **not** touch the patch chain (0001/0002/0004/0005/0006
stay byte-identical, so their `verify_v13.py` result 6/6 still applies), does **not** touch
`src/base-v11.ipynb`, and does **not** touch `playbook.json` (14 levels / 9 games on real
game code, worth 2.90 mean over the 25 public games).

1. `ESCALATE_ACTIONS` 10 -> 20  (measured, see README). At 10 the directive fires 154 times
   over the 32 levels of r085, i.e. 15.3% of a game's token pool in directive text alone, and
   on 31 of those 32 levels it tells the model to stop probing while it is at or better than
   the human baseline the score is measured against. At 20 it fires 60 times.

2. Roster probe hardened. The c45 hook in the v11/v13 chain does
   `_orig_play = _S._HarnessGameSession.play` outside any try/except, in the cell that also
   sets `bm.solver.*`. If that attribute is missing (different bundle revision), the cell
   raises and the whole run dies before it starts. v14 wraps it, and adds a *second* probe
   that reads `bm.game_runs` after the run and cannot fail.

3. New post-run roster probe. Answers the one question that decides whether patch 0006's
   cross-entry memory is worth 0 or +5..15 mean: does the roster repeat base game codes?

4. New pre-run budget probe. All three saved runs (r085 48 min, r110 48 min, r118 90 min)
   end with `max(final_wallclock_seconds) == min(...) == cap`, so a game never stops early:
   the per-game time cap *is* the action allotment (actions = cap / seconds-per-action).
   In a real rerun the cap is 532 min while the fair share is ~(32400 s x concurrency / games);
   if that ratio is > 1 the tail of the roster never plays. v14 only measures and logs it.

Usage:
  python3 tools/build_v14.py --src ../duck-v13-2 --out arc3-duck-v14.ipynb
  (--src may be omitted when the package sits next to its own tools/, which is the default)
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent


def cell_source(cell: dict) -> str:
    return "".join(cell.get("source", []))


def set_source(cell: dict, text: str) -> None:
    cell["source"] = text.splitlines(keepends=True)


def replace_once(text: str, old: str, new: str, what: str) -> str:
    n = text.count(old)
    assert n == 1, f"{what}: expected exactly 1 occurrence, found {n}"
    return text.replace(old, new, 1)


SWITCH_HEADER = """# === v14 switch (was: v13.2 switch) ======================================
# v14 = v13.2 with a *measured* escalation threshold, not a guessed one.
#   ESCALATE_ACTIONS = 20  (v13.1: 60, v13.2: 10)
#   measured on r085's 32 completed levels:
#     @60 ->  12 injections,  1.2% of the game's token pool
#     @20 ->  60 injections,  6.0% of the pool
#     @10 -> 154 injections, 15.3% of the pool, and on 31/32 levels it fires
#            while the agent is at or better than the human baseline
#   The directive costs ~146 tokens, but each one invites a multi-thousand-token
#   modelling turn, so the count matters more than the text.
#   Better still (needs a scaffold patch, not shipped here): fire only when
#   on_level > max(20, 1.2 x game_run.base_actions_per_level[level]) -> 8x on r085.
# PLAN_COMMIT = "1"  -> commit(plan) with per-step expect checks. This is the only
#                       lever with a ceiling above 50 (up to 40 actions per model
#                       turn, ~0.3 s each instead of ~12.9 s), which is why it stays.
# TRUE_CONCURRENCY   -> solver concurrency in the TRUE_SUBMISSION pass (10 = slots).
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(PKG), help="package dir with src/base-v11.ipynb")
    ap.add_argument("--out", default=str(PKG / "arc3-duck-v14.ipynb"))
    args = ap.parse_args()
    src = Path(args.src)

    # 1. Reproduce v13.2 exactly with its own builder (byte-identical, checked in tests).
    tmp = Path(args.out).with_suffix(".v132-build.ipynb")
    subprocess.run(
        [sys.executable, str(src / "tools" / "build_v13.py"),
         "--base", str(src / "src" / "base-v11.ipynb"),
         "--patch", str(src / "patches" / "0006-winpath-replay.patch"),
         "--playbook", str(src / "playbook.json"),
         "--out", str(tmp)],
        check=True, cwd=str(src),
    )
    nb = json.loads(tmp.read_text())
    tmp.unlink()
    cells = nb["cells"]

    # 2. Switch cell: measured threshold + v14 header.
    switch_idx = next(i for i, c in enumerate(cells) if "v13 switch" in cell_source(c))
    s = cell_source(cells[switch_idx])
    s = replace_once(s, s.split("\n", 1)[0], SWITCH_HEADER.rstrip("\n"), "switch header")
    s = replace_once(s, "ESCALATE_ACTIONS = 10", "ESCALATE_ACTIONS = 20", "escalate value")
    s = replace_once(s, 'print(f"v13.2 profile=', 'print(f"v14 profile=', "profile print")
    s = replace_once(s, "# v13 additions (variant env): ARC3_WINPATH=1",
                     "# v13 additions (variant env), unchanged in v14: ARC3_WINPATH=1",
                     "variant comment")
    set_source(cells[switch_idx], s)

    # 3. Harden the c45 roster-probe hook installed in the config cell.
    cfg_idx = next(i for i, c in enumerate(cells)
                   if "_install_roster_probe" in cell_source(c) and "bm.solver" in cell_source(c))
    s = cell_source(cells[cfg_idx])
    s = replace_once(
        s,
        "    _orig_play = _S._HarnessGameSession.play\n",
        "    try:\n"
        "        _orig_play = _S._HarnessGameSession.play\n"
        "    except AttributeError as exc:  # inny revision bundla -> nie zabijaj notebooka\n"
        "        return f\"probe: POMINIETA (brak _HarnessGameSession.play: {exc!r})\"\n",
        "probe attribute guard",
    )
    s = replace_once(
        s,
        "print(_install_roster_probe(), flush=True)\n",
        "try:  # v14: ten hook stoi w komorce, ktora ustawia bm.solver.* - nie moze rzucic\n"
        "    print(_install_roster_probe(), flush=True)\n"
        "except Exception as _probe_exc:\n"
        "    print(f\"probe: BLAD {_probe_exc!r}\", flush=True)\n",
        "probe call guard",
    )
    set_source(cells[cfg_idx], s)

    # 4. Budget probe, right after the game list is known and before the run.
    run_idx = next(i for i, c in enumerate(cells) if "bm.games = _offline_games(" in cell_source(c))
    s = cell_source(cells[run_idx])
    anchor = "# Outside a real submission, stop ~10 min before the wall-clock budget for a graceful exit."
    s = replace_once(s, anchor, BUDGET_PROBE + "\n" + anchor, "budget probe anchor")
    set_source(cells[run_idx], s)

    # 5. Post-run roster probe, after the metering cell.
    meter_idx = max(i for i, c in enumerate(cells) if "v11 metering" in cell_source(c))
    cells.insert(meter_idx + 1, {
        "cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
        "source": ROSTER_PROBE.splitlines(keepends=True),
    })

    out = Path(args.out)
    out.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n")
    print(f"built {out} ({len(cells)} cells, {out.stat().st_size} bytes)")


BUDGET_PROBE = r'''# === v14 budget probe: co naprawde ogranicza wynik - cap czy tokeny? ========
# Fakty z trzech zapisanych runow (r085, r110, r118): KAZDY run konczy sie
# dokladnie na capie (max(final_wallclock_seconds) == min == 48/48/90 min).
# Gra nie konczy sie wczesniej, wiec cap JEST przydzialem akcji:
#     akcje = cap / (sekundy na akcje),  a sekundy na akcje ~ tokeny na akcje.
# W prawdziwym rerunie cap = 532 min, a uczciwy udzial to
#     (budzet_notebooka - rezerwa) * concurrency / liczba_gier.
# Jesli cap / udzial > 1, ogon rosteru nie zagra wcale i liczy sie jako 0.
# Ten blok NICZEGO nie zmienia - liczy i loguje. Decyzje po pierwszym przebiegu.
try:
    _n_games = len(bm.games)
    _conc = max(1, int(bm.solver.concurrency))
    _total = float(getattr(target, "max_runtime_s", 0.0) or 0.0) or 32400.0
    _reserve = 600.0
    _fair = max(60.0, (_total - _reserve) * _conc / max(1, _n_games))
    _cap = float(getattr(bm.solver, "max_runtime_s_per_game", 0.0) or 0.0)
    _budget = {
        "games": _n_games,
        "passes": getattr(bm, "n_passes", None),
        "concurrency": _conc,
        "notebook_budget_s": _total,
        "fair_share_s_per_game": round(_fair, 1),
        "configured_cap_s": _cap,
        "cap_over_fair": round(_cap / _fair, 2) if _fair else None,
        "true_submission": TRUE_SUBMISSION,
    }
    (WORKING_DIR / "budget_probe.json").write_text(json.dumps(_budget, indent=2))
    print(f"v14 budget: {_n_games} gier x {_budget['passes']} pass(es), concurrency {_conc}, "
          f"uczciwy udzial {_fair / 60:.0f} min/gra, cap {_cap / 60:.0f} min "
          f"-> {_budget['cap_over_fair']}x", flush=True)
    if _cap and _fair and _cap / _fair > 1.3:
        print(f"v14 budget: UWAGA cap jest {_cap / _fair:.1f}x powyzej udzialu - jesli gra nie konczy "
              f"sie wczesniej, ogon rosteru ({_n_games} gier) nie zagra", flush=True)
except Exception as _budget_exc:
    print(f"v14 budget probe skipped: {_budget_exc!r}", flush=True)
'''

ROSTER_PROBE = r'''# === v14 roster probe: czy roster powtarza gry? (0 kosztu GPU) ==============
# Jedyne pytanie, od ktorego zalezy, czy pamiec win-path (patch 0006) jest warta
# 0 czy +5..15 punktow sredniej. v13.x zaklada "tak" i nie mierzy tego wcale.
# Ten blok czyta bm.game_runs PO biegu - nie dotyka solvera, nie moze wywalic runu.
import json as _v14_json
from collections import Counter as _V14Counter

_v14_out = WORKING_DIR / "roster_probe.jsonl"
try:
    _v14_runs = list(getattr(bm, "game_runs", None) or [])
    _v14_recs = []
    for _i, _r in enumerate(_v14_runs):
        _gid = str(getattr(_r, "game_id", "?") or "?")
        _hist = list(getattr(_r, "history", []) or [])
        _tok = sum(int(getattr(_h, "generated_tokens", 0) or 0) for _h in _hist)
        _calls = sum(1 for _h in _hist if int(getattr(_h, "generated_tokens", 0) or 0) > 0)
        _acts = sum(int(_x or 0) for _x in (getattr(_r, "actions_per_level", []) or []))
        _v14_recs.append({
            "index": _i,
            "game_id": _gid,
            "base": _gid.split("-")[0],
            "levels": int(getattr(_r, "levels_completed", 0) or 0),
            "total_levels": int(getattr(_r, "number_of_levels", 0) or 0),
            "actions": _acts,
            "tokens": _tok,
            "calls": _calls,
            "actions_per_call": round(_acts / _calls, 2) if _calls else 0.0,
            "tok_per_action": round(_tok / _acts, 1) if _acts else 0.0,
            "wall_min": round(float(getattr(_r, "final_wallclock_seconds", 0.0) or 0.0) / 60.0, 1),
            "score": round(float(getattr(_r, "final_score", 0.0) or 0.0), 2),
            "state": str(getattr(_r, "state", "?")),
        })
    with _v14_out.open("w", encoding="utf-8") as _fh:
        for _rec in _v14_recs:
            _fh.write(_v14_json.dumps(_rec, sort_keys=True) + "\n")

    if _v14_recs:
        _bases = _V14Counter(_r["base"] for _r in _v14_recs)
        _dups = {k: v for k, v in _bases.items() if v > 1}
        _zero = [(_r["game_id"], _r["state"]) for _r in _v14_recs if _r["actions"] == 0]
        _acpc = [_r["actions_per_call"] for _r in _v14_recs if _r["calls"]]
        _summary = {
            "runs": len(_v14_recs),
            "unique_bases": len(_bases),
            "duplicate_bases": len(_dups),
            "max_repeats": max(_bases.values()),
            "repeats": dict(sorted(_dups.items(), key=lambda kv: -kv[1])),
            "runs_with_zero_actions": _zero[:20],
            "mean_actions_per_call": round(sum(_acpc) / len(_acpc), 2) if _acpc else 0.0,
            "mean_wall_min": round(sum(_r["wall_min"] for _r in _v14_recs) / len(_v14_recs), 1),
        }
        print("v14 roster: " + _v14_json.dumps(_summary, sort_keys=True), flush=True)
        if _dups:
            print(f"v14 roster: POWTARZA SIE {len(_dups)} bazowych gier (do {_summary['max_repeats']}x) "
                  f"-> pamiec miedzy wpisami PLACI", flush=True)
        else:
            print("v14 roster: ZADNY bazowy kod sie nie powtarza -> pamiec win-path = 0 pkt "
                  "(dokladnie tak, jak twierdzi OCENA-V9 c45)", flush=True)
        print(f"v14 roster: zapisane do {_v14_out}", flush=True)
        if _acpc and _summary["mean_actions_per_call"] < 1.5:
            print(f"v14 roster: a/call = {_summary['mean_actions_per_call']} < 1.5 -> commit(plan) "
                  f"praktycznie nie odpala; dzwignia 50+ lezy odlogiem", flush=True)
except Exception as _v14_exc:
    print(f"v14 roster probe skipped: {_v14_exc!r}", flush=True)
'''


if __name__ == "__main__":
    main()
