"""Package-level invariants for v14: the things that must NOT drift from v13.2.

Cheap, offline, and they catch the only real risk of this build: that a change meant for one
cell leaked into the patch chain or the playbook.
"""
import hashlib
import json
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent


def test_patch_chain_is_byte_identical_to_v13_2():
    # 0001/0002/0004/0005 live inside src/base-v11.ipynb; 0006 is its own file.
    base = PKG / "src" / "base-v11.ipynb"
    assert hashlib.md5(base.read_bytes()).hexdigest() == "fdaa8b84d04a742d1692c5c5193536f2", \
        "base-v11.ipynb must stay byte-identical to v13.2"


def test_playbook_unchanged():
    pb = json.loads((PKG / "playbook.json").read_text())
    assert hashlib.md5((PKG / "playbook.json").read_bytes()).hexdigest() == \
        "e2d86b1e07fe35d2412065268d142175"
    assert sum(len(g["levels"]) for g in pb["games"].values()) == 14
    assert len(pb["games"]) == 9


def test_notebook_carries_the_measured_threshold():
    nb = json.loads((PKG / "arc3-duck-v14.ipynb").read_text())
    cells = ["".join(c.get("source", [])) for c in nb["cells"]]
    assert len(cells) == 36
    switch = next(c for c in cells if "v14 switch" in c)
    assert "ESCALATE_ACTIONS = 20" in switch
    assert "ESCALATE_ACTIONS = 10" not in switch
    assert any("v14 budget probe" in c for c in cells)
    assert any("v14 roster probe" in c for c in cells)
    # the c45 hook must no longer touch the attribute outside a try
    cfg = next(c for c in cells if "_install_roster_probe" in c and "bm.solver" in c)
    i = cfg.index("_orig_play = _S._HarnessGameSession.play")
    assert "try:" in cfg[max(0, i - 200):i], "probe attribute lookup must be guarded"
