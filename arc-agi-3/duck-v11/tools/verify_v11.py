#!/usr/bin/env python3
"""Offline verification for the v11 package (no GPU, no Kaggle).

  python3 tools/verify_v11.py [--bundle <r033 bundle dir>] [--tests]

Without --bundle: notebook/metadata/switch checks only.
With --bundle: also extracts all five patches from the notebook itself,
applies them in notebook order to a pristine bundle copy, compiles the tree.
With --tests: also runs tests/test_plan_commit.py on the patched tree
(needs requests/pillow/pydantic in the interpreter).

Patch extraction mirrors Kaggle runtime faithfully: the %%writefile cell
body is written with a trailing newline (measured IPython behaviour: the
full run_cell pipeline appends it; the c45 kernel log on Kaggle confirms
"harness patch applied successfully").
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
NB = PKG / "arc3-duck-v11.ipynb"
META = PKG / "kernel-metadata.json"

FAIL: list[str] = []


def check(name: str, ok: bool, detail: object = "") -> None:
    print(("OK   " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"))
    if not ok:
        FAIL.append(name)


def cells_of(nb: dict) -> list[str]:
    return ["".join(c.get("source", [])) for c in nb.get("cells", [])]


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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", default="")
    ap.add_argument("--tests", action="store_true")
    args = ap.parse_args()

    nb = json.loads(NB.read_text())
    cells = cells_of(nb)
    check("notebook parses (33 cells)", len(cells) == 33, len(cells))

    bad = []
    compiled = 0
    for i, (c, s) in enumerate(zip(nb["cells"], cells)):
        if c.get("cell_type") != "code" or s.lstrip().startswith("%%"):
            continue
        s2 = "\n".join("pass" if ln.lstrip().startswith("!") else ln for ln in s.splitlines())
        try:
            compile(s2, f"<cell {i}>", "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
            compiled += 1
        except SyntaxError as exc:
            bad.append(f"{i}: {exc}")
    check(f"code cells compile ({compiled})", not bad, "; ".join(bad))

    joined = "\n".join(cells)
    check("concurrency fix present", 'ARC3_TRUE_CONCURRENCY", "10"' in joined)
    check("concurrency 120 gone", "concurrency = 120" not in joined)
    check("extra-03 registered", '"/kaggle/duck-extra-03.patch"' in joined and "0005-plan-commit" in joined)
    check("metering cell present", "v11 metering" in joined and "v11_metrics.json" in joined)
    check("ONLY_RESET_LEVELS pinned", 'os.environ["ONLY_RESET_LEVELS"] = "true"' in joined)

    switch = next(s for s in cells if "v11 switch" in s)
    for plan, expect in [("0", False), ("1", True)]:
        ns: dict = {}
        src = re.sub(r'^PLAN_COMMIT = "0"', f'PLAN_COMMIT = "{plan}"', switch, count=1, flags=re.M)
        import io
        buf, real = io.StringIO(), sys.stdout
        sys.stdout = buf
        try:
            exec(compile(src, "<switch>", "exec"), ns)
        finally:
            sys.stdout = real
        env = ns["_v11_os"].environ
        check(f"switch PLAN_COMMIT={plan}",
              env.get("ARC3_TRUE_CONCURRENCY") == "10"
              and (("ARC3_PLAN_COMMIT" in env) == expect)
              and ns.get("V11_PROFILE") == ("plan" if expect else "c45fix"),
              {k: env.get(k) for k in ("ARC3_PLAN_COMMIT", "ARC3_TRUE_CONCURRENCY")})

    meta = json.loads(META.read_text())
    check("metadata id/title/code_file",
          meta["id"].endswith("/arc3-duck-v11") and meta["title"] == "arc3-duck-v11"
          and meta["code_file"] == NB.name)
    declared = {d.lower() for d in meta.get("dataset_sources", [])}
    declared |= {m.lower().split("/transformers")[0] for m in meta.get("model_sources", [])}
    declared |= {c.lower() for c in meta.get("competition_sources", [])}
    missing = []
    for m in re.finditer(r"/kaggle/input/(?:datasets|models|competitions)/([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)", joined):
        ref = m.group(1).lower()
        if not any(ref == d or ref.startswith(d + "/") for d in declared):
            missing.append(ref)
    check("all /kaggle/input paths declared", not missing, sorted(set(missing)))

    patches = extract_patches(cells)
    order = ["harness-changes.patch", "duck-extra-00.patch", "duck-extra-01.patch",
             "duck-extra-02.patch", "duck-extra-03.patch"]
    check("all five patches extracted", all(p in patches for p in order),
          [p for p in order if p not in patches])

    if args.bundle:
        bundle = Path(args.bundle)
        tmp = Path(tempfile.mkdtemp(prefix="v11-verify-"))
        try:
            work = tmp / "src"
            shutil.copytree(bundle / "src", work)
            subprocess.run(["git", "init", "-q"], cwd=work, check=True)
            subprocess.run(["git", "add", "-A", "-f"], cwd=work, check=True, capture_output=True)
            subprocess.run(["git", "-c", "user.email=v@v", "-c", "user.name=v", "commit", "-qm", "base"],
                           cwd=work, check=True, capture_output=True)
            for name in order:
                body = patches[name]
                # Kaggle's %%writefile pipeline delivers the trailing newline.
                (tmp / name).write_text(body if body.endswith("\n") else body + "\n")
                proc = subprocess.run(["git", "apply", "--include=ARC3-Inference/*", str(tmp / name)],
                                      cwd=work, capture_output=True, text=True)
                check(f"applies: {name}", proc.returncode == 0,
                      proc.stderr.strip().splitlines()[-1] if proc.stderr else "")
                if proc.returncode != 0:
                    break
            else:
                proc = subprocess.run([sys.executable, "-m", "compileall", "-q", "ARC3-Inference/inference"],
                                      cwd=work, capture_output=True, text=True)
                check("patched tree compiles", proc.returncode == 0, proc.stderr[-300:])
                if args.tests:
                    tdir = work / "ARC3-Inference" / "tests"
                    tdir.mkdir(exist_ok=True)
                    shutil.copyfile(PKG / "tests" / "test_plan_commit.py", tdir / "test_plan_commit.py")
                    import os as _os
                    env = dict(_os.environ)
                    env["ARC3_PLAN_COMMIT"] = "1"
                    proc = subprocess.run([sys.executable, "-m", "unittest", "tests.test_plan_commit"],
                                          cwd=work / "ARC3-Inference", capture_output=True,
                                          text=True, env=env)
                    check("12 plan-commit tests pass", proc.returncode == 0,
                          (proc.stderr or proc.stdout)[-300:])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    else:
        print("SKIP patch-chain checks (pass --bundle <r033 bundle dir>)")

    print()
    if FAIL:
        print(f"{len(FAIL)} FAILURES: {FAIL}")
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
