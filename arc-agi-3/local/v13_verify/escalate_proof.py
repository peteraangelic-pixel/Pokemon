#!/usr/bin/env python3
"""Verify the claims about ESCALATE_ACTIONS in V13-AUDIT-30OCT.md section 1A.1.

Three separate claims, each checked against a different artefact:

  A. The notebook really exports the threshold to the environment
     (`ARC3_ESCALATE_ACTIONS`), so changing `ESCALATE_ACTIONS` changes behaviour.
     Read from the notebook's switch cell as source text, not from the README.

  B. Patch 0005 really reads that variable and really *appends text to the prompt*
     — i.e. escalation is a directive, NOT a hard gate. This is the distinction
     the audit turns on: v13.2 raises pressure 12x but does not enforce batching.

  C. The escalation counts quoted in the audit (16 at N=60, 189 at N=10) follow
     from the real per-level action counts in r018.

Usage
-----
    git fetch origin arena/a450b00f-pokemon:refs/remotes/origin/arena/a450b00f-pokemon --force
    git archive 6b10853 arc-agi-3/duck-v13-2 | tar -x -C /tmp/v132

    python3 local/v13_verify/escalate_proof.py \
        --notebook /tmp/v132/arc-agi-3/duck-v13-2/arc3-duck-v13.ipynb \
        --benchmark local/benchmarks/r018.json

Exit code 0 when all three claims hold.
"""
from __future__ import annotations

import argparse
import json
import re
import sys

import pathlib

PATCH_CELL_MARKER = "duck-extra-03.patch"  # cell 10 holds patch 0005 as a literal


def cell_sources(nb_path: str) -> list[str]:
    nb = json.loads(pathlib.Path(nb_path).read_text())
    return ["".join(c.get("source", [])) for c in nb["cells"] if c.get("cell_type") == "code"]


def check_notebook_exports(notebook: str) -> tuple[bool, str]:
    """Claim A: ESCALATE_ACTIONS is written into os.environ."""
    src = "\n".join(cell_sources(notebook))
    m = re.search(r"^ESCALATE_ACTIONS\s*=\s*(\d+)", src, re.M)
    if not m:
        return False, "nie znalazłem przypisania ESCALATE_ACTIONS w notebooku"
    value = int(m.group(1))
    exported = re.search(
        r'os\.environ\[\s*"ARC3_ESCALATE_ACTIONS"\s*\]\s*=\s*str\(\s*ESCALATE_ACTIONS\s*\)', src
    )
    if not exported:
        return False, f"ESCALATE_ACTIONS={value}, ale NIE jest eksportowane do env"
    return True, f"ESCALATE_ACTIONS={value} i jest eksportowane jako ARC3_ESCALATE_ACTIONS"


def extract_patch_0005(notebook: str) -> str:
    """Pull the patch 0005 text out of the cell that writes it."""
    for src in cell_sources(notebook):
        if PATCH_CELL_MARKER not in src:
            continue
        m = re.search(r"write_text\(\s*(['\"])(.*?)\1\s*\)", src, re.S)
        if m:
            return m.group(2)
    return ""


def check_patch_reads_env(patch: str) -> tuple[bool, str]:
    """Claim B: patch 0005 reads ARC3_ESCALATE_ACTIONS and only appends prompt text."""
    if not patch:
        return False, "nie wyciągnąłem patcha 0005 z notebooka"
    reads_env = "ARC3_ESCALATE_ACTIONS" in patch
    has_reader = re.search(r"def _escalate_actions\(\)", patch) is not None
    appends = re.search(r"lines\.append\(\s*plan_escalation_prompt", patch) is not None
    # A hard gate would look like "return" / "raise" / "continue" next to the threshold.
    hard_gate = re.search(
        r"escalate_every[^\n]{0,80}\n[^\n]{0,40}(return|raise|continue|break)", patch
    ) is not None
    bits = [
        f"czyta ARC3_ESCALATE_ACTIONS: {reads_env}",
        f"ma _escalate_actions(): {has_reader}",
        f"dopisuje tekst do promptu (lines.append): {appends}",
        f"twarda bramka (return/raise/continue): {hard_gate}",
    ]
    ok = reads_env and has_reader and appends and not hard_gate
    return ok, " | ".join(bits)


def count_escalations(benchmark: str, threshold: int) -> int:
    """Claim C: escalations = sum over levels of floor(actions_on_level / threshold)."""
    data = json.loads(pathlib.Path(benchmark).read_text())
    total = 0
    for game in data["game_runs"]:
        for actions in game.get("actions_per_level", []):
            if actions:
                total += actions // threshold
    return total


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--notebook", required=True)
    ap.add_argument("--benchmark", default="local/benchmarks/r018.json")
    ap.add_argument("--expect-60", type=int, default=16)
    ap.add_argument("--expect-10", type=int, default=189)
    args = ap.parse_args()

    print("A) notebook eksportuje prog do env")
    ok_a, msg_a = check_notebook_exports(args.notebook)
    print(f"   {'OK  ' if ok_a else 'FAIL'} {msg_a}")

    print("\nB) patch 0005 czyta env i TYLKO dopisuje prompt (nie wymusza)")
    patch = extract_patch_0005(args.notebook)
    ok_b, msg_b = check_patch_reads_env(patch)
    print(f"   {'OK  ' if ok_b else 'FAIL'} {msg_b}")

    print(f"\nC) liczba eskalacji z realnych akcji ({args.benchmark})")
    n60 = count_escalations(args.benchmark, 60)
    n10 = count_escalations(args.benchmark, 10)
    ok_c = n60 == args.expect_60 and n10 == args.expect_10
    print(f"   {'OK  ' if ok_c else 'FAIL'} N=60 -> {n60} (oczekiwane {args.expect_60}), "
          f"N=10 -> {n10} (oczekiwane {args.expect_10})")

    print()
    if ok_a and ok_b and ok_c:
        print("WYNIK: wszystkie trzy twierdzenia potwierdzone.")
        print("       v13.2 podnosi presje 12x, ale nadal NIE wymusza batchowania.")
        return 0
    print("WYNIK: NIEZGODNE — zaktualizuj V13-AUDIT-30OCT.md §1A.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
