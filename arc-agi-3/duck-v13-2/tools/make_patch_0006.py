#!/usr/bin/env python3
"""Generate patches/0006-winpath-replay.patch.

Rebuilds the exact Kaggle patch chain on a pristine r033 bundle copy
(harness-changes + duck-extra-00..03, extracted from the v11 notebook the
same way tools/verify_v11.py does), then adds the v13 changes:

  * new file  ARC3-Inference/inference/framework/arc3_winpath.py
  * 4 small hooks in ARC3-Inference/inference/framework/solver.py
    (begin_session / maybe_replay+dead_skip at the play-loop top /
     record_action at the end of _execute_action / end_session in finally)

and emits the result as a git diff. Every solver.py anchor is asserted to
occur exactly once; any drift in the base tree fails the build loudly.

Usage: python3 tools/make_patch_0006.py --bundle <r033 bundle dir>
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
         "duck-extra-02.patch", "duck-extra-03.patch"]

HOOKS = [
    # H1: begin win-path session at play() start (patched play() wraps
    # _play_inner in a priority gate; body indent is 12).
    (
        "            self.seed_initial_history()\n"
        "            self.write_runtime_state()\n"
        "            self._append_initial_viewer_event()\n",
        "            self.seed_initial_history()\n"
        "            self.write_runtime_state()\n"
        "            try:\n"
        "                from inference.framework import arc3_winpath as _arc3_wp_mod\n"
        "                _arc3_wp_mod.begin_session(self)\n"
        "                self._arc3_wp_mod = _arc3_wp_mod\n"
        "            except Exception:\n"
        "                self._arc3_wp_mod = None\n"
        "            self._append_initial_viewer_event()\n",
    ),
    # H2: replay / dead-skip at the top of the _play_inner loop (indent 16).
    (
        "            while not self.should_stop():\n"
        "                if (\n",
        "            while not self.should_stop():\n"
        "                _arc3_wp_mod = getattr(self, \"_arc3_wp_mod\", None)\n"
        "                if _arc3_wp_mod is not None:\n"
        "                    try:\n"
        "                        if _arc3_wp_mod.maybe_replay(self):\n"
        "                            continue\n"
        "                        if _arc3_wp_mod.dead_skip(self):\n"
        "                            break\n"
        "                    except Exception:\n"
        "                        pass\n"
        "                if (\n",
    ),
    # H3: record every executed action.
    (
        "        self._append_action_viewer_event(payload, current_frame)\n"
        "        if flush_viewer_payload:\n"
        "            self.write_viewer_payload()\n"
        "        return payload\n",
        "        self._append_action_viewer_event(payload, current_frame)\n"
        "        if flush_viewer_payload:\n"
        "            self.write_viewer_payload()\n"
        "        try:\n"
        "            from inference.framework import arc3_winpath as _arc3_wp_rec\n"
        "            _arc3_wp_rec.record_action(\n"
        "                self,\n"
        "                action_name=action.id.name,\n"
        "                action_data=dict(action.data),\n"
        "                previous_completed=previous_completed,\n"
        "                previous_grid=previous_grid,\n"
        "                new_state=new_state,\n"
        "                payload=payload,\n"
        "            )\n"
        "        except Exception:\n"
        "            pass\n"
        "        return payload\n",
    ),
    # H4: persist session metadata in play()'s finally (before gate release).
    (
        "        finally:\n"
        "            if gate is not None:\n"
        "                gate.release()\n",
        "        finally:\n"
        "            _arc3_wp_mod = getattr(self, \"_arc3_wp_mod\", None)\n"
        "            if _arc3_wp_mod is not None:\n"
        "                try:\n"
        "                    _arc3_wp_mod.end_session(self)\n"
        "                except Exception:\n"
        "                    pass\n"
        "            if gate is not None:\n"
        "                gate.release()\n",
    ),
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
    ap.add_argument("--module", default=str(PKG / "src" / "arc3_winpath.py"))
    ap.add_argument("--out", default=str(PKG / "patches" / "0006-winpath-replay.patch"))
    args = ap.parse_args()

    nb = json.loads(Path(args.base).read_text())
    cells = ["".join(c.get("source", [])) for c in nb["cells"]]
    patches = extract_patches(cells)
    missing = [p for p in ORDER if p not in patches]
    if missing:
        raise SystemExit(f"base notebook is missing patches: {missing}")

    tmp = Path(tempfile.mkdtemp(prefix="v13-patch-"))
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
             "commit", "-qm", "c45+v11 chain"], work)

        solver = work / "ARC3-Inference/inference/framework/solver.py"
        text = solver.read_text()
        for i, (old, new) in enumerate(HOOKS, 1):
            count = text.count(old)
            if count != 1:
                raise SystemExit(f"hook H{i}: anchor found {count}x (expected 1)")
            text = text.replace(old, new)
        solver.write_text(text)

        module_dst = work / "ARC3-Inference/inference/framework/arc3_winpath.py"
        shutil.copyfile(args.module, module_dst)

        run([sys.executable, "-m", "compileall", "-q",
             "ARC3-Inference/inference/framework/solver.py",
             "ARC3-Inference/inference/framework/arc3_winpath.py"], work)
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
