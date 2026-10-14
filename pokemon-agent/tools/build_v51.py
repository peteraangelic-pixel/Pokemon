#!/usr/bin/env python3
"""Build v51 = v42.2 agent (per-arch state-value modulator) whose models are
LEAGUE-trained (kaggle_results/league_models.json) + CEM2-best knobs baked
(same setdefaults as v48). Run after tools/train_league.py.
"""
from __future__ import annotations

import base64
import json
import re
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def pack(model) -> str:
    W1 = np.array(model["W1"], dtype=np.float32)
    h1, h2 = W1.shape[1], np.array(model["W2"]).shape[1]
    dims = np.array([W1.shape[0], h1, h2, 1], dtype=np.float32)
    parts = [dims]
    for k in ("W1", "b1", "W2", "b2", "W3", "b3", "mean", "std"):
        parts.append(np.array(model[k], dtype=np.float32).ravel())
    return base64.b64encode(np.concatenate(parts).tobytes()).decode()


def main() -> int:
    models = json.loads((ROOT / "kaggle_results/league_models.json").read_text())
    blobs = {a: pack(m) for a, m in models.items()}
    glob_b64 = blobs["GLOBAL"]

    src = (ROOT / "agents/main_heuristic_v42_2.py").read_text()
    head = ("# v51 LEAGUE (a450, 2026-10-14): v42.2 modulator with LEAGUE-trained\n"
            "# per-arch state-value models (24k games, 5 pilots x pool decks, 454k\n"
            "# states, split po grach) + CEM2-best knobs (jak v48). Zrodlo modeli:\n"
            "# tools/gen_league_data.py + train_league.py -> league_models.json\n")
    src = head + src

    # swap model blobs: replace each arch entry; fall back to GLOBAL for missing
    def sub_arch(match):
        arch = match.group(1)
        return f'"{arch}": "{blobs.get(arch, glob_b64)}"'
    src, n = re.subn(r'"(GLOBAL|SPREAD|GRASS|FIGHTING|WALL|DEFAULT)": "[A-Za-z0-9+/=]+"', sub_arch, src)
    print("blobs swapped:", n)
    assert n >= 5, n

    best = json.loads((ROOT / "kaggle_results/es_tune2/best.json").read_text())["knobs"]
    cnt = 0
    for k, v in best.items():
        pat = re.compile(r'(os\.environ\.setdefault\("' + k + r'", ")[^"]+("\))')
        src, c = pat.subn(lambda mm: mm.group(1) + str(v) + mm.group(2), src)
        cnt += c
    print("knobs baked:", cnt)
    assert cnt == 26, cnt

    (ROOT / "agents/main_heuristic_v51.py").write_text(src)
    print("wrote agents/main_heuristic_v51.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
