#!/usr/bin/env python3
"""Prove the shipped bundle survives the way Kaggle actually loads it.

WHY THIS EXISTS
---------------
Our first two uploads both failed with:

    File "/kaggle_simulations/agent/main.py", line 240, in _candidate_dirs
        here = os.path.dirname(os.path.abspath(__file__))
    NameError: name '__file__' is not defined

Kaggle does not import our module. It compiles the source and `exec`s it:

    kaggle_environments/agent.py -> get_last_callable -> exec(code_object, env)

In that namespace `__file__` does not exist. Any import-time code that touches
it raises, the submission is marked Error, and the only feedback is a downloadable
log. Nothing in our local test suite could see it, because importing the file
normally (or running it as a script) always defines `__file__`.

WHAT THIS TEST DOES
-------------------
Unpacks the real .tar.gz we are about to upload, then loads `main.py` by
exec'ing its source into a bare namespace **with no `__file__`** and with the
working directory set to the unpacked folder -- reproducing Kaggle's
environment as closely as we can from here.

Then it checks the things that actually matter:
  1. the module executes at all (this is the bug we shipped)
  2. `agent({"select": None})` returns 60 card ids
  3. it returns the deck from deck.csv, not the hardcoded fallback
  4. the card index loaded (otherwise the agent is blind)
  5. optionally, it plays real games on the cabt engine

Usage
-----
    .venv/bin/python tools/test_kaggle_import.py                 # both bundles
    .venv/bin/python tools/test_kaggle_import.py --games 20      # + real games
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tarfile
import tempfile
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUNDLES = os.path.join(ROOT, "bundles")


def load_like_kaggle(main_path: str, cwd: str) -> dict:
    """Exec an agent's source the way kaggle_environments does.

    Note what is *not* in the namespace: __file__. That is the entire point.
    """
    with open(main_path, encoding="utf-8") as fh:
        src = fh.read()
    code = compile(src, "/kaggle_simulations/agent/main.py", "exec")
    env = {"__name__": "__main__", "__builtins__": __builtins__}
    old_cwd = os.getcwd()
    try:
        os.chdir(cwd)
        exec(code, env)  # noqa: S102 - this is the thing under test
    finally:
        os.chdir(old_cwd)
    return env


def check_bundle(path: str, games: int) -> bool:
    name = os.path.basename(path)
    tmp = tempfile.mkdtemp(prefix="kaggle_sim_")
    try:
        with tarfile.open(path, "r:gz") as tar:
            tar.extractall(tmp)

        main_py = os.path.join(tmp, "main.py")
        src = open(main_py, encoding="utf-8").read()
        ok = True
        if not os.path.exists(main_py):
            print(f"  {name}: FAIL - no main.py at the top level of the archive")
            return False

        # --- 1. does it even execute? -------------------------------------
        try:
            env = load_like_kaggle(main_py, tmp)
        except Exception:  # noqa: BLE001
            print(f"  {name}: FAIL - crashed while loading (this is the __file__ bug)")
            traceback.print_exc()
            return False

        if "agent" not in env:
            print(f"  {name}: FAIL - no agent() defined")
            return False
        print(f"  {name}: loaded without __file__                      ok")

        # --- 1b. is `agent` what Kaggle will actually pick? ---------------
        # get_last_callable() ends with
        #     return [v for v in env.values() if callable(v)][-1]
        # so it takes the LAST callable in the file, whatever it is named.
        # Helpers defined below `agent` silently become "the agent" -- which is
        # exactly how the heuristic submission died with
        #     TypeError: _score_yes_no() missing 3 required positional arguments
        try:
            from kaggle_environments.agent import get_last_callable
        except Exception:  # noqa: BLE001
            print(f"  {name}: WARN - kaggle_environments missing, "
                  f"cannot check entry-point resolution")
            get_last_callable = None
        if get_last_callable is not None:
            import inspect as _inspect

            picked = get_last_callable(src, path="/kaggle_simulations/agent/main.py")
            pname = getattr(picked, "__name__", repr(picked))
            try:
                nparams = len(_inspect.signature(picked).parameters)
            except (TypeError, ValueError):
                nparams = -1
            if pname != "agent":
                print(f"  {name}: FAIL - Kaggle would pick `{pname}` as the agent "
                      f"(helpers are defined after `agent`)")
                return False
            if nparams != 1:
                print(f"  {name}: FAIL - agent takes {nparams} parameters, "
                      f"expected exactly 1 (2 would make Kaggle call it the "
                      f"legacy way with (observation, configuration))")
                return False
            print(f"  {name}: get_last_callable() resolves to `agent`/1  ok")

        # --- 2. does it return a deck? ------------------------------------
        agent = env["agent"]
        try:
            deck = agent({"select": None})
        except Exception:  # noqa: BLE001
            print(f"  {name}: FAIL - agent({{'select': None}}) raised")
            traceback.print_exc()
            return False
        if not isinstance(deck, list) or len(deck) != 60:
            print(f"  {name}: FAIL - deck has {len(deck) if isinstance(deck, list) else type(deck)} entries, expected 60")
            return False
        print(f"  {name}: agent() returned 60 card ids                ok")

        # --- 3. from deck.csv, not the hardcoded fallback? ----------------
        csv_path = os.path.join(tmp, "deck.csv")
        if os.path.exists(csv_path):
            with open(csv_path) as fh:
                want = [int(t) for t in fh.read().replace(",", " ").split() if t.strip()]
            if want and list(deck) != want:
                print(f"  {name}: WARN - deck does not match deck.csv "
                      f"(the agent fell back to its hardcoded list)")
                ok = False
            elif want:
                print(f"  {name}: deck matches deck.csv                     ok")

        # --- 4. did the card index load? ----------------------------------
        # Only meaningful for agents that actually use one: main_random.py is
        # deliberately index-free, so an empty CARDS there is not a problem.
        needs_index = ("card_index" in src) or ("CARDS" in src and "card(" in src)
        cards = env.get("CARDS") or {}
        if not needs_index:
            print(f"  {name}: card index not used by this agent          skip")
        elif isinstance(cards, dict) and len(cards) < 100:
            print(f"  {name}: WARN - card index looks empty ({len(cards)} cards); "
                  f"the agent would be playing blind")
            ok = False
        else:
            print(f"  {name}: card index loaded ({len(cards)} cards)          ok")

        # --- 5. real games on the engine ----------------------------------
        if games:
            from kaggle_environments import make

            def wrap(obs):
                return agent(obs)

            env1 = make("cabt", configuration={"bo": 1}, debug=False)
            env1.run([wrap, wrap])
            st = [env1.steps[-1][i].get("status") for i in (0, 1)]
            if all(s == "DONE" for s in st):
                print(f"  {name}: self-play finished {st}            ok")
            else:
                print(f"  {name}: FAIL - self-play ended {st}")
                ok = False

        return ok
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=1,
                    help="also play N self-play games per bundle (0 skips)")
    ap.add_argument("--bundle", default=None, help="test one bundle instead of all")
    args = ap.parse_args()

    if args.bundle:
        paths = [args.bundle]
    else:
        paths = sorted(
            os.path.join(BUNDLES, f)
            for f in os.listdir(BUNDLES) if f.endswith(".tar.gz")
        )
    if not paths:
        print(f"no bundles in {BUNDLES} -- run build_submission.py first")
        return 1

    print(f"Kaggle-style load test ({len(paths)} bundle(s))")
    print("-" * 62)
    results = []
    for p in paths:
        print(f"{os.path.basename(p)}:")
        results.append(check_bundle(p, args.games))
        print()
    print("-" * 62)
    if all(results):
        print("ALL BUNDLES OK - safe to upload")
        return 0
    print("FAILURES PRESENT - do not upload")
    return 1


if __name__ == "__main__":
    sys.exit(main())
