#!/usr/bin/env python3
"""Single entry point for every Kaggle operation of the ARC-AGI-3 project.

Runs inside GitHub Actions (the agent sandbox has no route to kaggle.com).
The workflow `.github/workflows/arc3-ops.yml` executes:

    python arc-agi-3/duck/ops/kaggle_ops.py arc-agi-3/duck/ops/request.json

`request.json` looks like {"id": "r003", "op": "<op>", "args": {...}}.

Every op writes its artefacts to ``arc-agi-3/duck/ops/results/<id>-<op>/`` and a
short ``SUMMARY.md`` there. The workflow commits that directory back to the
branch and prints the summary as an Actions annotation (readable via
``gh run view``), because Actions logs are not reachable from the sandbox.

Ops
---
recon        leaderboard, best public notebooks, our submissions + error
             reasons, limits, GPU quota, and ``kernels pull -m`` of chosen refs.
pull         ``kernels pull -m`` for args.refs (code + metadata).
push         build-free push of args.dir (must hold kernel-metadata.json),
             optional args.accelerator, then poll until done (args.wait_min).
status       status + downloaded log (as text) of args.kernel.
submit       guarded submission of args.kernel. Refuses unless the save run is
             COMPLETE *and* its log contains the smoke marker (args.marker,
             default ARC3_SMOKE_OK) *and* a submission is left today.
submissions  our submissions, per-ref details, limits.
topics       list competition discussion topics (args.query optional).

Design rules: never print the token; never submit implicitly; every op is
idempotent and only reads unless it is ``push`` or ``submit``.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

COMP = "arc-prize-2026-arc-agi-3"
ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
SMOKE_MARKER = "ARC3_SMOKE_OK"


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
class Ctx:
    def __init__(self, req_id: str, op: str) -> None:
        self.out = RESULTS / f"{req_id}-{op}"
        if self.out.exists():
            shutil.rmtree(self.out)
        self.out.mkdir(parents=True)
        self.summary: list[str] = [f"# {req_id} · {op}", "",
                                   f"UTC {datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S}", ""]
        self.ok = True

    def say(self, line: str = "") -> None:
        print(line, flush=True)
        self.summary.append(line)

    def block(self, title: str, text: str, limit: int = 60) -> None:
        lines = text.rstrip().splitlines()
        if len(lines) > limit:
            lines = lines[:limit] + [f"... ({len(lines) - limit} more lines in files)"]
        self.say(f"## {title}")
        self.say("```")
        for ln in lines:
            self.say(ln[:300])
        self.say("```")

    def save(self, name: str, text: str) -> Path:
        p = self.out / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        return p

    def finish(self) -> None:
        self.save("SUMMARY.md", "\n".join(self.summary) + "\n")


def kg(*args: str, timeout: int = 600) -> tuple[int, str]:
    """Run the kaggle CLI, return (code, combined output). Never raises."""
    try:
        proc = subprocess.run(["kaggle", *args], capture_output=True, text=True, timeout=timeout)
        return proc.returncode, (proc.stdout + proc.stderr).strip()
    except subprocess.TimeoutExpired:
        return 124, f"(timeout after {timeout}s: kaggle {' '.join(args)})"
    except FileNotFoundError:
        return 127, "kaggle CLI not installed"


def log_to_text(raw: str) -> str:
    """Kaggle kernel logs are a JSON list of {stream_name,time,data}."""
    raw = raw.strip()
    try:
        items = json.loads(raw)
    except json.JSONDecodeError:
        # Sometimes the array is truncated; salvage line by line.
        items = []
        for line in raw.splitlines():
            line = line.lstrip("[,").rstrip("]")
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    out = []
    for it in items:
        if not isinstance(it, dict):
            continue
        t = float(it.get("time", 0.0))
        stream = "E" if it.get("stream_name") == "stderr" else " "
        for ln in str(it.get("data", "")).rstrip("\n").splitlines() or [""]:
            out.append(f"[{t:8.1f}s]{stream} {ln}")
    return "\n".join(out)


NOISE = re.compile(r"Debugger warning|frozen modules|Xfrozen_modules|PYDEVD_DISABLE|"
                   r"Requirement already satisfied|NbConvertApp|SyntaxWarning|re\.sub\(|"
                   r"MissingIDFieldWarning|_validate\(nbdict")


def interesting(text: str) -> str:
    return "\n".join(ln for ln in text.splitlines() if not NOISE.search(ln))


def kernel_status(kernel: str) -> str:
    _, out = kg("kernels", "status", kernel)
    m = re.search(r'status "?([A-Za-z_.]+)"?', out)
    return (m.group(1) if m else out).replace("KernelWorkerStatus.", "")


def download_output(ctx: Ctx, kernel: str, sub: str = "output", pattern: str | None = None,
                    keep: str = r"(benchmark\.json|summary\.txt|BUILD_INFO\.json)$",
                    max_bytes: int = 2_000_000) -> str:
    """Download a kernel's output (optionally only files matching ``pattern``)
    and return the notebook log as text. Small artefacts and files matching
    ``keep`` are committed; everything else large is dropped."""
    dest = ctx.out / sub
    dest.mkdir(parents=True, exist_ok=True)
    cmd = ["kernels", "output", kernel, "-p", str(dest), "-o"]
    if pattern:
        cmd += ["--file-pattern", pattern]
    code, out = kg(*cmd, timeout=1800)
    ctx.save(f"{sub}/_download.txt", "\n".join(out.splitlines()[-200:]))
    text = ""
    m = re.search(r"Kernel log downloaded to (\S+)", out)
    log_path = Path(m.group(1)) if m else None
    if log_path is None or not log_path.exists():
        cands = [p for p in dest.glob("*.log") if p.name != "serve.log"]
        log_path = cands[0] if cands else None
    if log_path is not None and log_path.exists():
        text = log_to_text(log_path.read_text(errors="replace"))
        ctx.save(f"{sub}/log.txt", text)
        log_path.unlink()
    keep_re = re.compile(keep)
    for f in dest.rglob("*"):
        if not f.is_file():
            continue
        limit = 25_000_000 if keep_re.search(f.name) else max_bytes
        if f.stat().st_size > limit or f.suffix in {".mp4", ".pkl"}:
            f.unlink()
    return text


def bench_table(path: Path) -> str:
    """Per-run table from a TAAF benchmark.json."""
    try:
        b = json.loads(path.read_text())
    except Exception as e:  # noqa: BLE001
        return f"(cannot read {path}: {e})"
    rows = []
    for r in b.get("game_runs", []):
        rows.append(f"{r['game_id']:<16} {r['state']:<10} lv={r['levels_completed']}/{r['number_of_levels']} "
                    f"acts={len(r.get('history', []))} score={r.get('final_score') or 0:.2f} "
                    f"apl={r.get('actions_per_level')} base={r.get('base_actions_per_level')}")
    return "\n".join(rows)


def op_output(ctx: Ctx, args: dict) -> None:
    """Download outputs of args.kernels (refs, optionally ref/version)."""
    pattern = args.get("pattern", r"(benchmark\.json|summary\.txt)$")
    for ref in args.get("kernels", []):
        sub = "out_" + ref.replace("/", "__")
        text = download_output(ctx, ref, sub=sub, pattern=pattern)
        ctx.say(f"## {ref}")
        summ = ctx.out / sub / "summary.txt"
        if summ.exists():
            ctx.block("summary.txt", summ.read_text(), 60)
        bj = ctx.out / sub / "benchmark.json"
        if bj.exists():
            ctx.save(f"{sub}/table.txt", bench_table(bj))
            ctx.say(f"benchmark.json: {bj.stat().st_size} bytes, table in {sub}/table.txt")
        else:
            ctx.say("no benchmark.json")
        ctx.say(f"log lines: {len(text.splitlines())} SMOKE_MARKER_PRESENT={SMOKE_MARKER in text}")
        arc3 = [ln for ln in text.splitlines() if "ARC3" in ln or "Traceback" in ln]
        if arc3:
            ctx.block("ARC3 lines", "\n".join(arc3[-40:]), 40)
def limits_text() -> str:
    return kg("competitions", "submission-limits", COMP)[1]


def remaining_today(text: str) -> int | None:
    m = re.search(r"Remaining today:\s*(\d+)", text)
    return int(m.group(1)) if m else None


# --------------------------------------------------------------------------
# ops
# --------------------------------------------------------------------------
def op_recon(ctx: Ctx, args: dict) -> None:
    code, lb = kg("competitions", "leaderboard", COMP, "--show", "--csv")
    ctx.save("leaderboard.csv", lb)
    ctx.block("Leaderboard (top 25)", "\n".join(lb.splitlines()[:26]), 30)

    for sort in ("scoreDescending", "voteCount", "dateRun"):
        _, ks = kg("kernels", "list", "--competition", COMP, "--sort-by", sort,
                   "--page-size", str(args.get("page_size", 60)), "--csv")
        ctx.save(f"kernels_{sort}.csv", ks)
        if sort == "scoreDescending":
            ctx.block("Public notebooks by score", "\n".join(ks.splitlines()[:30]), 32)

    op_submissions(ctx, args)

    _, quota = kg("quota")
    ctx.save("quota.txt", quota)
    ctx.block("GPU quota", quota, 20)

    if args.get("pull"):
        op_pull(ctx, {"refs": args["pull"]})

    if args.get("topics") is not None:
        op_topics(ctx, {"query": args.get("topics_query", ""), "show": args.get("topics", [])})


def op_pull(ctx: Ctx, args: dict) -> None:
    rows = []
    for ref in args.get("refs", []):
        dest = ctx.out / "pulled" / ref.replace("/", "__")
        dest.mkdir(parents=True, exist_ok=True)
        code, out = kg("kernels", "pull", ref, "-p", str(dest), "-m", timeout=300)
        meta_p = dest / "kernel-metadata.json"
        meta = {}
        if meta_p.exists():
            try:
                meta = json.loads(meta_p.read_text())
            except json.JSONDecodeError:
                pass
        rows.append(f"- {ref}: code={code} machine_shape={meta.get('machine_shape')!r} "
                    f"datasets={meta.get('dataset_sources')} models={meta.get('model_sources')} "
                    f"kernels={meta.get('kernel_sources')}")
        if code != 0:
            rows.append(f"    {out[:300]}")
    ctx.say("## Pulled notebooks")
    for r in rows:
        ctx.say(r)


def op_push(ctx: Ctx, args: dict) -> None:
    kdir = Path(args["dir"])
    meta = json.loads((kdir / "kernel-metadata.json").read_text())
    kernel = meta["id"]
    cmd = ["kernels", "push", "-p", str(kdir)]
    if args.get("accelerator"):
        cmd += ["--accelerator", args["accelerator"]]
    if args.get("timeout_s"):
        cmd += ["-t", str(args["timeout_s"])]
    code, out = kg(*cmd, timeout=900)
    ctx.save("push.txt", out)
    ctx.block("Push", out, 20)
    if code != 0:
        ctx.ok = False
        return
    m = re.search(r"version\s+(\d+)", out, re.I)
    if m:
        ctx.say(f"VERSION={m.group(1)}")
    wait_s = int(args.get("wait_min", 45)) * 60
    t0 = time.time()
    status = "unknown"
    while time.time() - t0 < wait_s:
        time.sleep(30)
        status = kernel_status(kernel)
        print(f"[{int(time.time() - t0):5d}s] {status}", flush=True)
        if status.upper() in {"COMPLETE", "ERROR", "CANCEL_ACKNOWLEDGED", "CANCELLED"}:
            break
    ctx.say(f"STATUS={status} after {int(time.time() - t0)}s")
    if status.upper() in {"COMPLETE", "ERROR"}:
        report_log(ctx, kernel, args)


def report_log(ctx: Ctx, kernel: str, args: dict) -> None:
    text = download_output(ctx, kernel)
    marker = args.get("marker", SMOKE_MARKER)
    ctx.say(f"SMOKE_MARKER_PRESENT={marker in text}")
    arc3 = [ln for ln in text.splitlines() if "ARC3" in ln or "Traceback" in ln or "Error" in ln]
    ctx.block("ARC3 / error lines", "\n".join(arc3[-60:]), 60)
    key = interesting(text)
    ctx.block("Log (filtered, last 80 lines)", "\n".join(key.splitlines()[-80:]), 80)


def op_status(ctx: Ctx, args: dict) -> None:
    kernel = args["kernel"]
    status = kernel_status(kernel)
    ctx.say(f"STATUS={status}")
    report_log(ctx, kernel, args)


def op_submit(ctx: Ctx, args: dict) -> None:
    kernel = args["kernel"]
    marker = args.get("marker", SMOKE_MARKER)
    status = kernel_status(kernel)
    ctx.say(f"STATUS={status}")
    if status.upper() != "COMPLETE":
        ctx.say("REFUSED: latest save run is not COMPLETE.")
        ctx.ok = False
        return
    text = download_output(ctx, kernel)
    if marker not in text:
        ctx.say(f"REFUSED: smoke marker {marker!r} missing from the save-run log.")
        ctx.block("Log tail", "\n".join(interesting(text).splitlines()[-60:]), 60)
        ctx.ok = False
        return
    lim = limits_text()
    ctx.block("Limits before", lim, 10)
    left = remaining_today(lim)
    if left is not None and left < 1:
        ctx.say("REFUSED: no submissions left today.")
        ctx.ok = False
        return
    version = str(args.get("version", "")).strip()
    if not version:
        _, out = kg("kernels", "list", "--mine", "--search", kernel.split("/")[1], "--csv")
        ctx.save("mine.csv", out)
        ctx.say("REFUSED: pass an explicit args.version (the COMPLETE save run's version).")
        ctx.ok = False
        return
    msg = args.get("message", f"{kernel} v{version}")[:200]
    code, out = kg("competitions", "submit", COMP, "-k", kernel, "-v", version,
                   "-f", args.get("file", "submission.parquet"), "-m", msg)
    ctx.block("Submit", out, 20)
    ctx.ok = code == 0
    op_submissions(ctx, {})


def op_submissions(ctx: Ctx, args: dict) -> None:
    _, subs = kg("competitions", "submissions", COMP, "--csv")
    ctx.save("submissions.csv", subs)
    ctx.block("Our submissions", subs, 20)
    lim = limits_text()
    ctx.save("limits.txt", lim)
    ctx.block("Limits", lim, 10)


def op_topics(ctx: Ctx, args: dict) -> None:
    _, out = kg("competitions", "topics", "list", COMP, "--sort-by", args.get("sort", "top"),
                "--page-size", "60", "--csv")
    ctx.save("topics.csv", out)
    ctx.block("Discussion topics", "\n".join(out.splitlines()[:40]), 42)
    for tid in args.get("show", []):
        _, body = kg("competitions", "topics", "show", f"{COMP}/{tid}")
        ctx.save(f"topic_{tid}.md", body)


OPS = {
    "recon": op_recon, "pull": op_pull, "push": op_push, "status": op_status,
    "submit": op_submit, "submissions": op_submissions, "topics": op_topics,
    "output": op_output,
}


def main() -> int:
    req = json.loads(Path(sys.argv[1]).read_text())
    op = req["op"]
    ctx = Ctx(str(req.get("id", "r")), op)
    if op not in OPS:
        ctx.say(f"unknown op {op!r}; known: {sorted(OPS)}")
        ctx.finish()
        return 2
    if not os.environ.get("KAGGLE_API_TOKEN") and not os.environ.get("KAGGLE_KEY"):
        ctx.say("missing KAGGLE_API_TOKEN")
        ctx.finish()
        return 2
    try:
        OPS[op](ctx, req.get("args", {}))
    except Exception as exc:  # report, never hide
        ctx.ok = False
        ctx.say(f"EXCEPTION: {type(exc).__name__}: {exc}")
    ctx.say("")
    ctx.say(f"RESULT={'OK' if ctx.ok else 'FAILED'}")
    ctx.finish()
    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a") as fh:
            fh.write(f"outdir={ctx.out}\n")
    return 0 if ctx.ok else 1


if __name__ == "__main__":
    sys.exit(main())
