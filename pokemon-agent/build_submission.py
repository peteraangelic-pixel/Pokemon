"""Package an agent into the .tar.gz bundle Kaggle expects.

The competition requires a gzipped tarball whose **top level** contains
``main.py`` and ``deck.csv`` (no wrapping directory), built essentially like
``tar -czvf submission.tar.gz *``.  At runtime the archive is unpacked into
``/kaggle_simulations/agent/`` and the harness imports ``main.py``.

Usage
-----
    # build the Phase 1 heuristic bundle
    python build_submission.py --agent agents/main_heuristic.py

    # build the Phase 0 random bundle
    python build_submission.py --agent agents/main_random.py --name phase0_random

    # build AND rehearse the validation episode locally (unpack + BO3 self-play)
    python build_submission.py --agent agents/main_heuristic.py --smoke
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
MAX_BYTES = 197 * 1024 * 1024  # Kaggle limit is 197.7 MiB


def _read_deck(path: str) -> list[int]:
    with open(path, encoding="utf-8") as fh:
        return [int(t) for line in fh for t in line.replace(",", " ").split() if t.strip()]


def build(agent_path: str, name: str, outdir: str) -> str:
    agent_path = os.path.abspath(agent_path)
    deck_path = os.path.join(ROOT, "deck.csv")
    index_path = os.path.join(ROOT, "assets", "card_index.json")

    deck = _read_deck(deck_path)
    if len(deck) != 60:
        raise SystemExit(f"deck.csv must hold exactly 60 cards, found {len(deck)}")
    if not os.path.exists(agent_path):
        raise SystemExit(f"agent not found: {agent_path}")
    if not os.path.exists(index_path):
        raise SystemExit(
            "assets/card_index.json missing -- run tools/build_card_index.py first"
        )

    os.makedirs(outdir, exist_ok=True)
    tar_path = os.path.join(outdir, f"{name}.tar.gz")

    with tempfile.TemporaryDirectory() as staging:
        # main.py must be at the archive root.
        shutil.copyfile(agent_path, os.path.join(staging, "main.py"))
        shutil.copyfile(deck_path, os.path.join(staging, "deck.csv"))
        shutil.copyfile(index_path, os.path.join(staging, "card_index.json"))

        with tarfile.open(tar_path, "w:gz") as tar:
            for fname in ("main.py", "deck.csv", "card_index.json"):
                tar.add(os.path.join(staging, fname), arcname=fname)

    verify(tar_path, deck)
    size = os.path.getsize(tar_path)
    print(f"built {tar_path}  ({size/1024:.1f} KiB)")
    if size > MAX_BYTES:
        raise SystemExit("bundle exceeds the 197.7 MiB submission limit")
    return tar_path


def verify(tar_path: str, deck: list[int]) -> None:
    """Assert the archive matches Kaggle's documented requirements."""
    with tarfile.open(tar_path, "r:gz") as tar:
        names = tar.getnames()
        assert "main.py" in names, f"main.py missing from archive root: {names}"
        assert "deck.csv" in names, f"deck.csv missing from archive root: {names}"
        assert not any(n.startswith(".//") or "/" in n for n in names), (
            f"archive must be flat, got {names}"
        )
        member = tar.extractfile("main.py")
        src = member.read().decode("utf-8")
        assert "def agent(" in src, "main.py does not define agent(obs)"
    print(f"verify ok: flat archive {names}, agent() present, deck {len(deck)} cards")


def smoke(tar_path: str, bo: int) -> None:
    """Rehearse the Kaggle validation episode: unpack + BO3 self-play."""
    from kaggle_environments import make

    with tempfile.TemporaryDirectory() as work:
        with tarfile.open(tar_path, "r:gz") as tar:
            tar.extractall(work)  # noqa: S202 - our own archive
        sys.path.insert(0, work)
        import importlib.util

        spec = importlib.util.spec_from_file_location("main", os.path.join(work, "main.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        agent = mod.agent
        print(f"imported main.py from {work}; deck len = {len(mod.DECK)}")

        for label, cfg in (("BO1", 1), ("BO3", bo)):
            env = make("cabt", configuration={"bo": cfg}, debug=False)
            env.run([agent, agent])  # agent vs copies of itself == validation
            final = env.steps[-1]
            statuses = [s.get("status") for s in final]
            print(f"  self-play {label}: status={statuses} bo_result={env.result}")
            assert all(s == "DONE" for s in statuses), f"{label} self-play did not finish cleanly"
    print("smoke ok: validation-style self-play finished with no errors")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", default=os.path.join(ROOT, "agents", "main_heuristic.py"))
    ap.add_argument("--name", default=None, help="output basename (default: agent filename)")
    ap.add_argument("--outdir", default=os.path.join(ROOT, "bundles"))
    ap.add_argument("--smoke", action="store_true", help="rehearse a validation episode")
    ap.add_argument("--bo", type=int, default=3)
    args = ap.parse_args()

    name = args.name or os.path.splitext(os.path.basename(args.agent))[0]
    tar_path = build(args.agent, name, args.outdir)

    print("\nto inspect manually:")
    print(f"  tar -tzvf {tar_path}")
    print("upload at: https://www.kaggle.com/competitions/"
          "the-pokemon-company-ptcg-ai-battle-challenge-playground/submissions")
    print("(or: kaggle competitions submit -c the-pokemon-company-ptcg-ai-battle-challenge-playground"
          f" -f {tar_path} -m \"<message>\")")

    if args.smoke:
        print()
        smoke(tar_path, args.bo)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
