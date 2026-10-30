#!/usr/bin/env python3
"""Build `arc3-duck-v15.ipynb` from the Gemma-session duck-v14 notebook.

Base: arc3-duck-v14.ipynb (byte-identical patch chain 0001-0006 and
playbook as v13.2, plus the measured ESCALATE_ACTIONS=20, the guarded
roster hook, and the budget/roster probes). v15 changes exactly two
things:

1. registers patch 0007 (duck-extra-05, patches/0007-escalate-relative
   .patch): baseline-relative escalation trigger + per-level directive
   cap (PROPOZYCJA-0007 from the v14 package, implemented and verified
   here because this session has the r033 bundle Gemma lacked).
2. renames the switch banner to v15.

Everything else stays byte-identical to v14. Usage:
  python3 tools/build_v15.py [--base arc3-duck-v14.ipynb] [--out arc3-duck-v15.ipynb]
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
MARK_BASE_CELLS = 36  # v14 has exactly 36 cells


def cell_source(cell: dict) -> str:
    return "".join(cell.get("source", []))


def set_source(cell: dict, text: str) -> None:
    cell["source"] = text.splitlines(keepends=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=str(PKG / "arc3-duck-v14.ipynb"))
    ap.add_argument("--patch", default=str(PKG / "patches" / "0007-escalate-relative.patch"))
    ap.add_argument("--out", default=str(PKG / "arc3-duck-v15.ipynb"))
    args = ap.parse_args()

    nb = json.loads(Path(args.base).read_text())
    cells = nb["cells"]
    assert len(cells) == MARK_BASE_CELLS, f"base has {len(cells)} cells, expected {MARK_BASE_CELLS}"

    patch_text = Path(args.patch).read_text()
    if not patch_text.endswith("\n"):
        patch_text += "\n"

    # 1. ARC3_VARIANT cell: register duck-extra-05 / 0007.
    variant_idx = next(i for i, c in enumerate(cells) if "ARC3_VARIANT" in cell_source(c))
    src = cell_source(cells[variant_idx])
    src, n = re.subn(r'("/kaggle/duck-extra-04\.patch")(\s*\])', r'\1, "/kaggle/duck-extra-05.patch"\2', src, count=1)
    assert n == 1, "patch_files anchor not found"
    src, n = re.subn(r'("0006-winpath-replay\.patch")(\s*\])', r'\1, "0007-escalate-relative.patch"\2', src, count=1)
    assert n == 1, "patches anchor not found"
    set_source(cells[variant_idx], src)

    # 2. Switch banner: v15 (threshold stays the measured 20 from v14).
    switch_idx = next(i for i, c in enumerate(cells) if "ESCALATE_ACTIONS = 20" in cell_source(c))
    src = cell_source(cells[switch_idx])
    src, n = re.subn(r'v14 profile', 'v15 profile', src, count=1)
    assert n == 1, "switch banner anchor not found"
    src, n = re.subn(r'# === v14 switch', '# === v15 switch', src, count=1)
    assert n == 1, "switch header anchor not found"
    set_source(cells[switch_idx], src)

    # 3. duck-extra-05 writer cell after the extra-04 writer cell.
    write_idx = max(i for i, c in enumerate(cells)
                    if "duck-extra-04.patch" in cell_source(c) and "write_text" in cell_source(c))
    writer = (
        "# ARC3 Duck v15: patch 0007-escalate-relative - baseline-relative\n"
        "# escalation trigger + per-level directive cap (PROPOZYCJA-0007\n"
        "# from duck-v14, implemented against r033). Env-gated via\n"
        "# ARC3_ESCALATE_RATE / ARC3_ESCALATE_MAX_PER_LEVEL; without human\n"
        "# baselines (submission mode) it degrades to the absolute\n"
        "# threshold from ARC3_ESCALATE_ACTIONS plus the cap.\n"
        "from pathlib import Path as _P\n"
        f'_P("/kaggle/duck-extra-05.patch").write_text({patch_text!r})\n'
    )
    cells.insert(write_idx + 1, {
        "cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
        "source": writer.splitlines(keepends=True),
    })

    out = Path(args.out)
    out.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n")
    print(f"built {out} ({len(cells)} cells, {out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
