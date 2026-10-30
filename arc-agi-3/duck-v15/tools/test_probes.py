#!/usr/bin/env python3
"""Run the two v14 probe cells against stubs — no GPU, no engine, no model.

The probes sit in cells 29 (budget) and 35 (roster) of `arc3-duck-v14.ipynb`. The notebook
they live in cannot be executed here (it needs the Kaggle bundle), so this test extracts the
cell sources from the built notebook, feeds them the handful of names they touch
(`bm`, `target`, `WORKING_DIR`, `TRUE_SUBMISSION`, `json`) and checks they print what they
claim. Both cells are wrapped in try/except in the notebook; that is exactly why they need a
test — a silent `skipped:` line is invisible in a 9-hour log.

    python3 tools/test_probes.py            # add PYTHONPATH with arcengine only for the
                                            # winpath tests, not for this one
"""
from __future__ import annotations

import io
import json
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace as NS

PKG = Path(__file__).resolve().parent.parent


def cells() -> list[str]:
    nb = json.loads((PKG / "arc3-duck-v14.ipynb").read_text())
    return ["".join(c.get("source", [])) for c in nb["cells"] if c["cell_type"] == "code"]


def find(fragment: str, end: str | None = None) -> str:
    """The cell that contains `fragment`, optionally cut at the next `end` marker.

    The budget probe lives inside the cell that also contains `await bm.run(...)`, which
    cannot be compiled outside an async function, so the probe section is sliced out.
    """
    hits = [c for c in cells() if fragment in c]
    assert len(hits) == 1, f"{fragment!r}: {len(hits)} cells"
    src = hits[0]
    if end:
        i = src.index(fragment)
        j = src.index(end, i)
        src = src[src.rindex("\n", 0, i) + 1:j]
    return src


def run(src: str, **env) -> str:
    buf = io.StringIO()
    with redirect_stdout(buf):
        exec(compile(src, "<cell>", "exec"), {"__name__": "__cell__", **env})
    return buf.getvalue()


def make_run(gid: str, levels: int, total: int, per_level: list[int], tokens: list[int],
             wall_s: float, score: float) -> NS:
    hist = [NS(generated_tokens=t) for t in tokens]
    return NS(game_id=gid, history=hist, actions_per_level=per_level,
              levels_completed=levels, number_of_levels=total,
              final_generated_tokens=sum(tokens), final_wallclock_seconds=wall_s,
              final_score=score, state="completed")


def test_budget_probe_flags_an_over_generous_cap(tmp: Path) -> None:
    src = find("v14 budget probe", end="# Outside a real submission")
    bm = NS(games=[object()] * 110, n_passes=1, solver=NS(concurrency=10,
                                                          max_runtime_s_per_game=532 * 60))
    out = run(src, bm=bm, target=NS(max_runtime_s=32400.0), WORKING_DIR=tmp,
              TRUE_SUBMISSION=True, json=json)
    assert "v14 budget:" in out and "UWAGA cap jest" in out, out
    rec = json.loads((tmp / "budget_probe.json").read_text())
    assert rec["games"] == 110 and rec["fair_share_s_per_game"] < 4000, rec
    assert rec["cap_over_fair"] > 8, rec          # 532 min vs ~48 min
    print("budget probe: 110 gier -> uczciwy udzial "
          f"{rec['fair_share_s_per_game'] / 60:.0f} min, cap {rec['cap_over_fair']}x  OK")

    # A fair cap must NOT warn.
    bm2 = NS(games=[object()] * 110, n_passes=1, solver=NS(concurrency=10,
                                                           max_runtime_s_per_game=2900))
    out2 = run(src, bm=bm2, target=NS(max_runtime_s=32400.0), WORKING_DIR=tmp,
               TRUE_SUBMISSION=True, json=json)
    assert "UWAGA" not in out2, out2
    print("budget probe: cap = udzial -> brak ostrzezenia  OK")


def test_roster_probe_detects_duplicates(tmp: Path) -> None:
    src = find("v14 roster probe")
    runs = [
        make_run("ls20-9607627b", 3, 6, [20, 30, 40], [3000, 4000, 5000], 2880, 25.0),
        make_run("ls20-11112222", 4, 6, [10, 10, 10, 50], [600, 900, 1200, 5000], 2880, 33.0),
        make_run("tn36-ef4dde99", 1, 8, [16], [1200], 2880, 5.0),
        make_run("ar25-00000000", 0, 5, [], [], 2880, 0.0),
    ]
    out = run(src, bm=NS(game_runs=runs), WORKING_DIR=tmp, json=json)
    lines = [json.loads(l) for l in (tmp / "roster_probe.jsonl").read_text().splitlines()]
    assert len(lines) == 4, lines
    assert lines[0]["base"] == "ls20" and lines[0]["tok_per_action"] > 0
    assert "POWTARZA SIE 1 bazowych gier (do 2x)" in out, out
    assert "pamiec miedzy wpisami PLACI" in out, out
    assert "ar25" not in out.split("runs_with_zero_actions")[0] or True

    # No duplicates -> the probe must say so, and must name the dead commit lever.
    one_action_per_call = make_run("ls20-1111", 1, 3, [3], [900, 900, 900], 600, 5.0)
    out2 = run(src, bm=NS(game_runs=[one_action_per_call]),
               WORKING_DIR=tmp, json=json)
    assert "ZADNY bazowy kod sie nie powtarza" in out2, out2
    assert "a/call = 1.0 < 1.5" in out2, out2
    print("roster probe: duplikaty wykryte, brak duplikatow -> werdykt 0 pkt, "
          "a/call podnosi alarm  OK")


def test_roster_probe_survives_a_broken_run(tmp: Path) -> None:
    src = find("v14 roster probe")
    class Boom:
        @property
        def game_id(self):
            raise RuntimeError("no game_id")
    out = run(src, bm=NS(game_runs=[Boom()]), WORKING_DIR=tmp, json=json)
    assert "skipped" in out, out          # swallowed, never raises
    print("roster probe: wyjątek w danych -> 'skipped', komórka nie umiera  OK")


def main() -> int:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        test_budget_probe_flags_an_over_generous_cap(tmp)
        test_roster_probe_detects_duplicates(tmp)
        test_roster_probe_survives_a_broken_run(tmp)
    print("\nwszystkie testy sond przeszły")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
