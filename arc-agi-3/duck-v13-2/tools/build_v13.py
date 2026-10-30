#!/usr/bin/env python3
"""Build `arc3-duck-v13.ipynb` from the twice-verified duck-v11 notebook.

Base: src/base-v11.ipynb (the v11 package: c45 byte-identical base + patch
0005 commit(plan) + concurrency fix, verified 5/5 patches on a pristine
r033 bundle by two independent sessions). v13 changes exactly five things:

1. PLAN_COMMIT = "1" in the switch cell (v11 slot B configuration: commit
   (plan) with per-step expect checks + escalation every 60 actions).
2. ARC3_LEVEL_TOKEN_CAP "45000" -> "0" in the variant env. Cross-build
   smoke measurement (same 10 games): c45-with-cap 26.78 < r019-no-cap
   27.21 < v3-no-cap 29.02; the cap also gates the free RESET/ABANDON of
   patch 0004 off with it, which the same data says is net-negative.
3. Patch 0006 (duck-extra-04): win-path memory + deterministic replay +
   dead-game pass skip (new file arc3_winpath.py, 4 small solver hooks).
4. A playbook cell that seeds /kaggle/working/arc3_winpath/playbook.json
   with offline BFS/beam solutions (14 levels / 9 games, every sequence
   re-validated on the real game code by tools/build_playbook.py).
5. Variant env gains ARC3_WINPATH=1 and ARC3_DEAD_SKIP=1.

Everything else stays byte-identical to v11. Usage:
  python3 tools/build_v13.py [--base src/base-v11.ipynb] [--out arc3-duck-v13.ipynb]
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
MARK_BASE_CELLS = 33  # v11 has exactly 33 cells

SWITCH_CELL = '''# === v13 switch (was: v11 switch) =========================================
# PLAN_COMMIT = "1"  -> commit(plan) with per-step expect checks, plus an
#                       escalation directive every ESCALATE_ACTIONS actions
#                       on an unfinished level (retrodiction -> model_state/
#                       model_step -> check_model() -> plan() -> commit()).
#                       Set to "0" ONLY to re-run the v11 control (c45fix).
# TRUE_CONCURRENCY   -> solver concurrency in the TRUE_SUBMISSION pass.
#                       c45 shipped 120 against a MAXREQ=10 server and its
#                       rerun (ref 57629847) scored 0.00; 10 matches slots.
# v13 additions (variant env): ARC3_WINPATH=1 (win-path memory + replay,
# patch 0006), ARC3_DEAD_SKIP=1 (late passes of never-progressing games
# exit early), ARC3_LEVEL_TOKEN_CAP="0" (measured -0.4..-2.2 pts at 45k).
import os as _v11_os

PLAN_COMMIT = "1"          # "0" | "1"  <- flip ONLY this between slots
ESCALATE_ACTIONS = 10
TRUE_CONCURRENCY = 10

_v11_os.environ["ARC3_TRUE_CONCURRENCY"] = str(TRUE_CONCURRENCY)
if PLAN_COMMIT == "1":
    _v11_os.environ["ARC3_PLAN_COMMIT"] = "1"
    _v11_os.environ["ARC3_ESCALATE_ACTIONS"] = str(ESCALATE_ACTIONS)
else:
    _v11_os.environ.pop("ARC3_PLAN_COMMIT", None)
V11_PROFILE = "plan" if PLAN_COMMIT == "1" else "c45fix"
print(f"v13.2 profile={V11_PROFILE} plan_commit={PLAN_COMMIT} "
      f"escalate={ESCALATE_ACTIONS} true_concurrency={TRUE_CONCURRENCY}",
      flush=True)
'''


def cell_source(cell: dict) -> str:
    return "".join(cell.get("source", []))


def set_source(cell: dict, text: str) -> None:
    cell["source"] = text.splitlines(keepends=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=str(PKG / "src" / "base-v11.ipynb"))
    ap.add_argument("--patch", default=str(PKG / "patches" / "0006-winpath-replay.patch"))
    ap.add_argument("--playbook", default=str(PKG / "playbook.json"))
    ap.add_argument("--out", default=str(PKG / "arc3-duck-v13.ipynb"))
    args = ap.parse_args()

    nb = json.loads(Path(args.base).read_text())
    cells = nb["cells"]
    assert len(cells) == MARK_BASE_CELLS, f"base has {len(cells)} cells, expected {MARK_BASE_CELLS}"

    patch_text = Path(args.patch).read_text()
    if not patch_text.endswith("\n"):
        patch_text += "\n"
    playbook = json.loads(Path(args.playbook).read_text())
    n_levels = sum(len(g["levels"]) for g in playbook["games"].values())

    # 1. ARC3_VARIANT cell: register extra-04 / 0006, cap off, winpath on.
    variant_idx = next(i for i, c in enumerate(cells) if "ARC3_VARIANT" in cell_source(c))
    src = cell_source(cells[variant_idx])
    src, n = re.subn(r'("/kaggle/duck-extra-03\.patch")(\s*\])', r'\1, "/kaggle/duck-extra-04.patch"\2', src, count=1)
    assert n == 1, "patch_files anchor not found"
    src, n = re.subn(r'("0005-plan-commit\.patch")(\s*\])', r'\1, "0006-winpath-replay.patch"\2', src, count=1)
    assert n == 1, "patches anchor not found"
    src, n = re.subn(r'"ARC3_LEVEL_TOKEN_CAP": "45000"',
                     '"ARC3_LEVEL_TOKEN_CAP": "0", "ARC3_WINPATH": "1", "ARC3_DEAD_SKIP": "1"',
                     src, count=1)
    assert n == 1, "level-token-cap anchor not found"
    set_source(cells[variant_idx], src)

    # 2. Switch cell: v13 text with PLAN_COMMIT = "1".
    switch_idx = next(i for i, c in enumerate(cells) if "v11 switch" in cell_source(c))
    set_source(cells[switch_idx], SWITCH_CELL)

    # 3. Playbook cell right after the switch cell.
    playbook_cell = (
        "# ARC3 Duck v13: offline playbook for patch 0006 (win-path replay).\n"
        "# Sequences were solved by BFS/beam search on the public games and\n"
        "# re-validated action-by-action on the real game code; the runtime\n"
        "# still verifies every replayed frame against the recorded hashes\n"
        "# and falls back to the LLM on the first mismatch.\n"
        "import json as _pb_json\n"
        "from pathlib import Path as _PBPath\n\n"
        f"_PB = _pb_json.loads(r'''{json.dumps(playbook)}''')\n"
        "_pb_dir = _PBPath('/kaggle/working/arc3_winpath')\n"
        "try:\n"
        "    _pb_dir.mkdir(parents=True, exist_ok=True)\n"
        "    (_pb_dir / 'playbook.json').write_text(_pb_json.dumps(_PB))\n"
        "    _pb_n = sum(len(g['levels']) for g in _PB['games'].values())\n"
        "    print(f'v13 playbook: {len(_PB[\"games\"])} gier, {_pb_n} poziomów -> {_pb_dir}', flush=True)\n"
        "except Exception as _pb_exc:\n"
        "    print(f'v13 playbook NIE zapisany: {_pb_exc!r}', flush=True)\n"
    )
    cells.insert(switch_idx + 1, {
        "cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
        "source": playbook_cell.splitlines(keepends=True),
    })

    # 4. duck-extra-04 writer cell after the extra-03 writer cell.
    write_idx = max(i for i, c in enumerate(cells)
                    if "duck-extra-03.patch" in cell_source(c) and "write_text" in cell_source(c))
    writer = (
        "# ARC3 Duck v13: patch 0006-winpath-replay — win-path memory with\n"
        "# frame-verified deterministic replay + dead-game pass skip.\n"
        "# Env-gated: with ARC3_WINPATH unset the patched code is inert.\n"
        "from pathlib import Path as _P\n"
        f'_P("/kaggle/duck-extra-04.patch").write_text({patch_text!r})\n'
    )
    cells.insert(write_idx + 1, {
        "cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
        "source": writer.splitlines(keepends=True),
    })

    out = Path(args.out)
    out.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n")
    print(f"built {out} ({len(cells)} cells, {out.stat().st_size} bytes, "
          f"playbook {len(playbook['games'])} gier/{n_levels} poziomów)")


if __name__ == "__main__":
    main()
