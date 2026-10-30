#!/usr/bin/env python3
"""Generate patches/0007-escalate-relative.patch (implements PROPOZYCJA-0007).

Rebuilds the full Kaggle patch chain on a pristine r033 bundle copy
(harness + duck-extra-00..04, extracted from src/base-v11.ipynb + the
shipped 0006), then adds patch 0007:

  * inference/utils/plan_commit.py: pure pc_escalate_at() threshold logic
    (absolute floor, baseline-relative trigger, per-level directive cap).
  * inference/agent/tool_agent.py: import it, env readers
    (ARC3_ESCALATE_RATE / ARC3_ESCALATE_MAX_PER_LEVEL), a
    base_actions_per_level constructor argument, and the escalation
    block rewritten to use the relative trigger.
  * inference/framework/solver.py: _make_analyzer hands the game's
    base_actions_per_level to ToolAgent (None in submission mode, where
    the engine hides baselines -> behaviour degrades to v14's absolute
    threshold + the per-level cap).

Every anchor is asserted to occur exactly once. Usage:
  python3 tools/make_patch_0007.py --bundle <r033 bundle dir>
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
ORDER = ["harness-changes.patch", "duck-extra-00.patch", "duck-extra-01.patch",
         "duck-extra-02.patch", "duck-extra-03.patch", "duck-extra-04.patch"]

EDITS = [
    # E1: pure threshold logic in plan_commit.py (appended at EOF anchor).
    ("ARC3-Inference/inference/utils/plan_commit.py",
     """    if terminal is not None:
        report["terminal"] = terminal
    return report
""",
     """    if terminal is not None:
        report["terminal"] = terminal
    return report


def pc_escalate_at(escalate_every, base_actions, level, fired, rate=1.2,
                   max_per_level=2):
    \"\"\"Next on-level action count that earns an escalation directive.

    Pure threshold logic for patch 0007 (relative escalation). Returns 0
    for silence: feature off, or the per-level directive cap reached.
    Without a human baseline for the level the absolute threshold rules;
    with one, the directive waits until the agent is `rate`x past the
    human action count - the point where the run actually loses points.
    Measured motivation (r085, 32 completed levels): an absolute trigger
    at 10 fires 154x, mostly on levels already at or better than the
    human baseline; the relative trigger fires 8x, all on losing levels.
    \"\"\"
    every = int(escalate_every or 0)
    if every <= 0:
        return 0
    cap = int(max_per_level or 0)
    if cap and int(fired or 0) >= cap:
        return 0
    at = every
    if base_actions:
        idx = int(level or 1) - 1
        if 0 <= idx < len(base_actions) and base_actions[idx]:
            at = max(at, int(float(base_actions[idx]) * float(rate)))
    return at * (int(fired or 0) + 1)
"""),
    # E2: import the helper in tool_agent.py.
    ("ARC3-Inference/inference/agent/tool_agent.py",
     "from inference.utils.retained_functions import function_signature\n",
     "from inference.utils.retained_functions import function_signature\n"
     "from inference.utils.plan_commit import pc_escalate_at\n"),
    # E3: env readers next to _escalate_actions.
    ("ARC3-Inference/inference/agent/tool_agent.py",
     '''def _escalate_actions() -> int:
    """ARC3_ESCALATE_ACTIONS: actions on one level before the escalation directive."""
    return max(0, _get_env_int("ARC3_ESCALATE_ACTIONS", 0))
''',
     '''def _escalate_actions() -> int:
    """ARC3_ESCALATE_ACTIONS: actions on one level before the escalation directive."""
    return max(0, _get_env_int("ARC3_ESCALATE_ACTIONS", 0))


def _escalate_rate() -> float:
    """ARC3_ESCALATE_RATE: baseline multiple for the relative trigger."""
    raw = os.environ.get("ARC3_ESCALATE_RATE", "").strip()
    try:
        return float(raw) if raw else 1.2
    except ValueError:
        return 1.2


def _escalate_max_per_level() -> int:
    """ARC3_ESCALATE_MAX_PER_LEVEL: directive cap per level (0 = unlimited)."""
    return max(0, _get_env_int("ARC3_ESCALATE_MAX_PER_LEVEL", 2))
'''),
    # E4: constructor argument.
    ("ARC3-Inference/inference/agent/tool_agent.py",
     """        provider: str | None = None,
    ) -> None:
""",
     """        provider: str | None = None,
        base_actions_per_level: list[int] | None = None,
    ) -> None:
"""),
    # E5: store the baselines (context unique to __init__).
    ("ARC3-Inference/inference/agent/tool_agent.py",
     "        self._actions_at_level_start = 0\n"
     "        self._arc3_escalations_on_level = 0\n"
     "        self._tokens_at_level_start = 0\n",
     "        self._actions_at_level_start = 0\n"
     "        self._arc3_escalations_on_level = 0\n"
     "        self._arc3_base_actions = [int(x) for x in (base_actions_per_level or [])]\n"
     "        self._tokens_at_level_start = 0\n"),
    # E6: relative-trigger escalation block.
    ("ARC3-Inference/inference/agent/tool_agent.py",
     """        escalate_every = _escalate_actions()
        if escalate_every and _plan_commit_enabled():
            on_level = max(0, int(action_num or 0) - int(self._actions_at_level_start or 0))
            if on_level >= escalate_every * (self._arc3_escalations_on_level + 1):
                self._arc3_escalations_on_level = on_level // escalate_every
                lines.append(plan_escalation_prompt(int(current_level or 1), on_level))
""",
     """        escalate_every = _escalate_actions()
        if escalate_every and _plan_commit_enabled():
            on_level = max(0, int(action_num or 0) - int(self._actions_at_level_start or 0))
            _arc3_at = pc_escalate_at(
                escalate_every,
                getattr(self, "_arc3_base_actions", None),
                current_level,
                self._arc3_escalations_on_level,
                rate=_escalate_rate(),
                max_per_level=_escalate_max_per_level(),
            )
            if _arc3_at and on_level >= _arc3_at:
                self._arc3_escalations_on_level += 1
                lines.append(plan_escalation_prompt(int(current_level or 1), on_level))
"""),
    # E7: solver hands the game's baselines to the analyzer.
    ("ARC3-Inference/inference/framework/solver.py",
     "            dispatch_index=index,\n",
     "            dispatch_index=index,\n"
     "            base_actions_per_level=getattr(game, \"base_actions_per_level\", None),\n"),
]


def extract_patches(cells: list[str]) -> dict[str, str]:
    patches: dict[str, str] = {}
    for src in cells:
        if src.startswith("%%writefile"):
            head, _, body = src.partition("\n")
            patches[Path(head.split(maxsplit=1)[1].strip()).name] = body
            continue
        if ".write_text(" not in src or ".patch" not in src:
            continue
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "write_text" and node.args):
                try:
                    body = ast.literal_eval(node.args[0])
                except Exception:
                    continue
                m = re.search(r"""['"]([^'"]+\.patch)['"]""", src)
                if m and isinstance(body, str):
                    patches[Path(m.group(1)).name] = body
    return patches


def run(cmd: list[str], cwd: Path) -> None:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"FAILED {cmd}:\n{proc.stdout}\n{proc.stderr}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", required=True)
    ap.add_argument("--base", default=str(PKG / "src" / "base-v11.ipynb"))
    ap.add_argument("--patch6", default=str(PKG / "patches" / "0006-winpath-replay.patch"))
    ap.add_argument("--out", default=str(PKG / "patches" / "0007-escalate-relative.patch"))
    args = ap.parse_args()

    nb = json.loads(Path(args.base).read_text())
    cells = ["".join(c.get("source", [])) for c in nb["cells"]]
    patches = extract_patches(cells)
    missing = [p for p in ORDER[:-1] if p not in patches]
    if missing:
        raise SystemExit(f"base notebook is missing patches: {missing}")
    patches["duck-extra-04.patch"] = Path(args.patch6).read_text()

    tmp = Path(tempfile.mkdtemp(prefix="v15-patch-"))
    try:
        work = tmp / "src"
        shutil.copytree(Path(args.bundle) / "src", work)
        run(["git", "init", "-q"], work)
        run(["git", "add", "-A", "-f"], work)
        run(["git", "-c", "user.email=v@v", "-c", "user.name=v",
             "commit", "-qm", "bundle"], work)
        for name in ORDER:
            body = patches[name]
            pfile = tmp / name
            pfile.write_text(body if body.endswith("\n") else body + "\n")
            run(["git", "apply", "--include=ARC3-Inference/*", str(pfile)], work)
        run(["git", "add", "-A", "-f"], work)
        run(["git", "-c", "user.email=v@v", "-c", "user.name=v",
             "commit", "-qm", "chain 0001-0006"], work)

        for rel, old, new in EDITS:
            target = work / rel
            text = target.read_text()
            count = text.count(old)
            if count != 1:
                raise SystemExit(f"{rel}: anchor found {count}x (expected 1): {old[:70]!r}")
            target.write_text(text.replace(old, new))

        run([sys.executable, "-m", "compileall", "-q",
             "ARC3-Inference/inference/utils/plan_commit.py",
             "ARC3-Inference/inference/agent/tool_agent.py",
             "ARC3-Inference/inference/framework/solver.py"], work)
        for cache in work.rglob("__pycache__"):
            shutil.rmtree(cache, ignore_errors=True)
        run(["git", "add", "-A", "-f"], work)
        proc = subprocess.run(["git", "diff", "--cached"], cwd=work,
                              capture_output=True, text=True, check=True)
        out = Path(args.out)
        out.write_text(proc.stdout)
        print(f"wrote {out} ({len(proc.stdout)} chars)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
