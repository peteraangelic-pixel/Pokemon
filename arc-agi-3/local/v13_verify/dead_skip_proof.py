#!/usr/bin/env python3
"""Reproduce the central finding of V13-AUDIT-30OCT.md section 3.

Claim
-----
In v13 (`duck-v13-mega`, commit 3782f8c) the dead-game skip NEVER fires, for two
independent reasons that mask each other:

  1. `dead_skip()` required `pass_index >= ARC3_DEAD_MIN_PASS (default 4)`, but the
     scoring rerun sets `bm.n_passes = 1`, so `pass_index` is always 0.
  2. `_Store` keyed its JSON file by `_sanitize(game_id)` — the FULL id including the
     hash suffix (`dead00-abcdef12.json`). Entries of the same game therefore never
     shared a store, so `passes_completed` always read back as 0.

v13.1 (`duck-v13-1`, commit cbefdd4) removes the `pass_index` gate and keys the store
by `base_key()` (`dead00`), so both fail.

Why reason 2 matters even at `pass_index=4`
-------------------------------------------
If only the gate were wrong, `pass_index=4` would still fire. It does not — which is
what proves the second, independent bug.

Usage
-----
    git fetch origin arena/a450b00f-pokemon
    git archive 3782f8c arc-agi-3/duck-v13-mega | tar -x -C /tmp/v13a
    git archive cbefdd4 arc-agi-3/duck-v13-1   | tar -x -C /tmp/v13

    python3 local/v13_verify/dead_skip_proof.py \
        --v13    /tmp/v13a/arc-agi-3/duck-v13-mega/src/arc3_winpath.py \
        --v13-1  /tmp/v13/arc-agi-3/duck-v13-1/src/arc3_winpath.py

Exit code 0 when the observed behaviour matches the claim.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import sys
import tempfile


class FakeGameRun:
    def __init__(self, game_id: str) -> None:
        self.game_id = game_id


class FakeGame:
    def __init__(self, game_id: str) -> None:
        self.game_run = FakeGameRun(game_id)


class FakeSession:
    """The minimum `dead_skip` touches: game id and pass_index."""

    def __init__(self, game_id: str, pass_index: int) -> None:
        self.game = FakeGame(game_id)
        self.game_index = 0
        self.pass_index = pass_index


def load(module_name: str, path: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"nie mogę załadować {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def probe(mod, game_id: str, pass_index: int, seed_store: str | None = None) -> bool:
    """Seed a store with 10 dead entries, then ask dead_skip for one session."""
    if seed_store:
        store = mod._Store(seed_store)
        store.data["best_levels"] = 0
        store.data["passes_completed"] = 10
        store.save()
    session = FakeSession(game_id=game_id, pass_index=pass_index)
    mod.begin_session(session)
    try:
        return bool(mod.dead_skip(session))
    finally:
        mod.end_session(session)


def run(label: str, path: str, expected: dict[int, bool]) -> bool:
    print(f"\n=== {label} ===")
    print(f"    {path}")
    ok = True
    for pass_index, want in expected.items():
        # Fresh store dir per case so runs cannot contaminate each other.
        os.environ["ARC3_WINPATH"] = "1"
        os.environ["ARC3_WINPATH_DIR"] = tempfile.mkdtemp(prefix="wp-proof-")
        os.environ["ARC3_DEAD_SKIP"] = "1"
        mod = load(f"wp_{label.replace('.', '_')}_{pass_index}", path)
        got = probe(mod, "dead00-abcdef12", pass_index, seed_store="dead00")
        mark = "OK " if got == want else "FAIL"
        if got != want:
            ok = False
        print(f"    pass_index={pass_index}: dead_skip={got!s:<5} (oczekiwane {want!s:<5}) {mark}")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--v13", required=True, help="ścieżka do v13 src/arc3_winpath.py")
    ap.add_argument("--v13-1", dest="v13_1", required=True,
                    help="ścieżka do v13.1 src/arc3_winpath.py")
    args = ap.parse_args()

    print("Teza: w v13 dead_skip nie zadziała NIGDY (także przy pass_index=4),")
    print("bo bramka pass_index i kluczowanie magazynu to dwa niezależne błędy.")

    a = run("v13", args.v13, {0: False, 1: False, 4: False})
    b = run("v13.1", args.v13_1, {0: True, 1: True, 4: True})

    print()
    if a and b:
        print("WYNIK: zgodne z tezą — v13 martwe (nawet przy 4), v13.1 działa.")
        return 0
    print("WYNIK: NIEZGODNE z tezą — kod się zmienił, zaktualizuj V13-AUDIT-30OCT.md §3.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
