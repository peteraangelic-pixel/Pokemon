#!/usr/bin/env python3
"""Build `arc3-duck-v11.ipynb` from the Kaggle-proven duck-c45 notebook.

Base: src/base-c45.ipynb (byte copy of Smak `kaggle/duck-c45/arc3-duck-c45.ipynb`,
the notebook that ran on Kaggle: smoke COMPLETE, log "harness patch applied
successfully"). v11 changes exactly four things, all greppable:

1. adds ONE extra patch, `duck-extra-03.patch` (patches/0005-plan-commit.patch):
   `commit(plan)` with per-step expectation checks + escalation, ported from
   the e499c604 v10 package as a minimal diff (4 files) instead of v10's
   rebuilt 660 KB patch (which does not apply to the bundle tree: Makefile:40,
   README.md:1). The feature is env-gated (`ARC3_PLAN_COMMIT`); off = c45.
2. adds a V11 switch cell: PLAN_COMMIT (default "0" = control), ESCALATE_ACTIONS,
   TRUE_CONCURRENCY (default 10).
3. fixes the rerun killer: cell 21 `bm.solver.concurrency = 120` replaced by
   `int(os.environ.get("ARC3_TRUE_CONCURRENCY", "10"))`. c45's scoring rerun
   (ref 57629847) scored 0.00 with 120 game threads against a MAXREQ=10 server
   while its 10-game smoke (concurrency 10) completed 32 levels.
4. appends the read-only metering cell (tools/metering_cell.py.txt).

Everything else (498 KB harness patch cell, extra patches 00-02, model paths,
TRUE_SUBMISSION logic, ONLY_RESET_LEVELS pin) stays byte-identical to c45.

Usage: python3 tools/build_v11.py [--base src/base-c45.ipynb] [--out arc3-duck-v11.ipynb]
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
MARK_BASE_CELLS = 30  # c45 has exactly 30 cells; a different base is a different notebook

SWITCH_CELL = '''# === v11 switch: ONE lever per run ========================================
# PLAN_COMMIT = "0"  -> control: behaviour identical to duck-c45 (commit()
#                       hidden, no prompt addendum, no escalation). This is
#                       the first v11 run if the concurrency fix needs a
#                       clean control measurement.
# PLAN_COMMIT = "1"  -> commit(plan) with per-step expect checks, plus an
#                       escalation directive every ESCALATE_ACTIONS actions
#                       on an unfinished level (retrodiction -> model_state/
#                       model_step -> check_model() -> plan() -> commit()).
# TRUE_CONCURRENCY   -> solver concurrency in the TRUE_SUBMISSION pass.
#                       c45 shipped 120 against a MAXREQ=10 server and its
#                       rerun (ref 57629847) scored 0.00; 10 matches slots.
import os as _v11_os

PLAN_COMMIT = "0"          # "0" | "1"  <- flip ONLY this between slots
ESCALATE_ACTIONS = 60
TRUE_CONCURRENCY = 10

_v11_os.environ["ARC3_TRUE_CONCURRENCY"] = str(TRUE_CONCURRENCY)
if PLAN_COMMIT == "1":
    _v11_os.environ["ARC3_PLAN_COMMIT"] = "1"
    _v11_os.environ["ARC3_ESCALATE_ACTIONS"] = str(ESCALATE_ACTIONS)
V11_PROFILE = "plan" if PLAN_COMMIT == "1" else "c45fix"
print(f"v11 profile={V11_PROFILE} plan_commit={PLAN_COMMIT} "
      f"escalate={ESCALATE_ACTIONS} true_concurrency={TRUE_CONCURRENCY}",
      flush=True)
'''


def cell_source(cell: dict) -> str:
    return "".join(cell.get("source", []))


def set_source(cell: dict, text: str) -> None:
    cell["source"] = text.splitlines(keepends=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=str(PKG / "src" / "base-c45.ipynb"))
    ap.add_argument("--patch", default=str(PKG / "patches" / "0005-plan-commit.patch"))
    ap.add_argument("--metering", default=str(HERE / "metering_cell.py.txt"))
    ap.add_argument("--out", default=str(PKG / "arc3-duck-v11.ipynb"))
    args = ap.parse_args()

    nb = json.loads(Path(args.base).read_text())
    cells = nb["cells"]
    assert len(cells) == MARK_BASE_CELLS, f"base has {len(cells)} cells, expected {MARK_BASE_CELLS}"

    patch_text = Path(args.patch).read_text()
    if not patch_text.endswith("\n"):
        patch_text += "\n"

    # 1. ARC3_VARIANT (cell 1): register duck-extra-03 / 0005-plan-commit.
    variant_idx = next(i for i, c in enumerate(cells) if "ARC3_VARIANT" in cell_source(c))
    src = cell_source(cells[variant_idx])
    src, n = re.subn(r'("/kaggle/duck-extra-02\.patch")(\s*\])', r'\1, "/kaggle/duck-extra-03.patch"\2', src, count=1)
    assert n == 1, "patch_files anchor not found"
    src, n = re.subn(r'("0004-level-token-cap\.patch")(\s*\])', r'\1, "0005-plan-commit.patch"\2', src, count=1)
    assert n == 1, "patches anchor not found"
    set_source(cells[variant_idx], src)

    # 2. V11 switch cell right after the variant/preflight cell.
    cells.insert(variant_idx + 1, {
        "cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
        "source": SWITCH_CELL.splitlines(keepends=True),
    })

    # 3. duck-extra-03 writer cell after the last existing patch-writer cell.
    write_idx = max(i for i, c in enumerate(cells)
                    if ".patch" in cell_source(c) and "write_text" in cell_source(c))
    writer = (
        "# ARC3 Duck v11: patch 0005-plan-commit — commit(plan) with per-step\n"
        "# expectation checks + escalation (from the e499c604 v10 package, as a\n"
        "# minimal 4-file diff on top of the proven c45 chain). Env-gated:\n"
        "# with ARC3_PLAN_COMMIT unset the patched code is inert.\n"
        "from pathlib import Path as _P\n"
        f'_P("/kaggle/duck-extra-03.patch").write_text({patch_text!r})\n'
    )
    cells.insert(write_idx + 1, {
        "cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
        "source": writer.splitlines(keepends=True),
    })

    # 4. Concurrency fix in the solver-config cell.
    fixed = False
    for c in cells:
        s = cell_source(c)
        if "bm.solver.concurrency = 120" in s:
            s = s.replace(
                "bm.solver.concurrency = 120  # game count should be 110",
                'bm.solver.concurrency = int(os.environ.get("ARC3_TRUE_CONCURRENCY", "10"))'
                "  # v11 fix: was 120 vs MAXREQ=10 server -> rerun 0.00 (ref 57629847)",
            )
            set_source(c, s)
            fixed = True
    assert fixed, "concurrency anchor not found"

    # 5. Metering cell at the end.
    meter = Path(args.metering).read_text()
    cells.append({
        "cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
        "source": meter.splitlines(keepends=True),
    })

    out = Path(args.out)
    out.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n")
    print(f"built {out} ({len(cells)} cells, {out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
