#!/usr/bin/env python3
"""Generate the Kaggle notebook for one variant of the ARC3 Duck submission.

Base: Daniel Franzen's public Milestone-2 notebook (Apache-2.0), vendored
verbatim in ``base/franzen-m2.ipynb`` (sha256 pinned below). We never
hand-edit it. Every change is an *anchored* string edit that aborts the build
if its anchor is missing or not unique, so drift in the base fails loudly.

What a variant can change (``variants/<name>.json``)
----------------------------------------------------
- ``env``: extra environment variables, applied after Franzen's ``setup_env``
  in BOTH modes (save run and competition rerun). Used for config toggles.
- ``patches``: our own harness patches (``patches/*.patch``) applied with
  ``git apply`` on top of Franzen's patch, in both modes.
- ``smoke``: what the *save run* plays. The competition rerun branch
  (``TRUE_SUBMISSION``) keeps Franzen's settings unchanged.

What every variant gets
-----------------------
1. Preflight cell: fails in seconds (not after a 10-minute model load) when
   the GPU is not the RTX PRO 6000 or an input mount is missing.
2. Save-run smoke test: plays ``smoke.games`` for ``smoke.minutes`` through the
   exact solver/agent code path the rerun uses, then prints a per-game table
   and ``ARC3_SMOKE_OK`` only if the model really acted (tokens > 0 and
   non-reset actions > 0, no crashed game). ``kaggle_ops.py submit`` refuses
   to submit a version whose log lacks that marker.
3. Variant banner in the log (name + git sha + env) so every LB score can be
   traced back to exact code.

Usage::

    python build.py --variant v1                  # writes out/
    python build.py --request ../ops/request.json # variant from args.variant
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE_NB = HERE / "base" / "franzen-m2.ipynb"
BASE_SHA256 = "88a379f17c3a4ba8c98715fc23155346ccd6eb289bdafebadfc61a3178f9d9bd"
OUT = HERE / "out"
KERNEL_ID = "petersharps/arc3-duck"
KERNEL_TITLE = "ARC3 Duck"
NB_NAME = "arc3-duck.ipynb"

METADATA = {
    "id": KERNEL_ID,
    "title": KERNEL_TITLE,
    "code_file": NB_NAME,
    "language": "python",
    "kernel_type": "notebook",
    "is_private": True,
    "enable_gpu": True,
    "enable_tpu": False,
    "enable_internet": False,
    "keywords": ["gpu"],
    "dataset_sources": [
        "dfranzen/pennyroyal-v253",
        "dfranzen/taaf-kaggle-source-bundle-copy",
    ],
    "kernel_sources": [],
    "competition_sources": ["arc-prize-2026-arc-agi-3"],
    "model_sources": [
        "dfranzen/albucino-qwen3-8-flash-next-drafter/Transformers/default/1",
        "dfranzen/intel-qwen3.8-flash-next-w4a16-autoround/Transformers/default/1",
    ],
    # Same image Franzen's scored run used: the wheelhouse is built for it.
    "docker_image": "gcr.io/kaggle-private-byod/python@sha256:"
                    "57e612b484cf3df5026ee4dcc3cb176974b22b2bc0937fb1e16132a8be4cb13c",
    "machine_shape": "NvidiaRtxPro6000",
}


# --------------------------------------------------------------------------
# notebook helpers
# --------------------------------------------------------------------------
def src(cell: dict) -> str:
    s = cell["source"]
    return "".join(s) if isinstance(s, list) else s


def set_src(cell: dict, text: str) -> None:
    lines = text.splitlines(keepends=True)
    cell["source"] = lines


def code_cell(text: str) -> dict:
    c = {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": []}
    set_src(c, text)
    return c


def md_cell(text: str) -> dict:
    c = {"cell_type": "markdown", "metadata": {}, "source": []}
    set_src(c, text)
    return c


def find_cell(cells: list[dict], needle: str) -> int:
    hits = [i for i, c in enumerate(cells) if needle in src(c)]
    if len(hits) != 1:
        raise SystemExit(f"build: anchor {needle!r} matched cells {hits}, expected exactly one")
    return hits[0]


def replace_once(text: str, old: str, new: str) -> str:
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"build: anchor {old[:70]!r} occurs {n} times, expected 1")
    return text.replace(old, new)


def git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short=12", "HEAD"], cwd=HERE,
                                       text=True).strip()
    except Exception:
        return "unknown"


# --------------------------------------------------------------------------
# injected code
# --------------------------------------------------------------------------
PREFLIGHT = r'''# ARC3 Duck preflight: fail in seconds instead of after the model load.
import json as _pf_json, os as _pf_os, subprocess as _pf_sp
from pathlib import Path as _PfPath

ARC3_VARIANT = __VARIANT_JSON__
print("ARC3_VARIANT", _pf_json.dumps(ARC3_VARIANT, sort_keys=True), flush=True)

_pf_errors = []
try:
    _gpu = _pf_sp.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                      capture_output=True, text=True, timeout=60).stdout.strip()
except Exception as _e:  # noqa: BLE001
    _gpu = f"nvidia-smi failed: {_e!r}"
print("ARC3_PREFLIGHT gpu:", _gpu, flush=True)
if "RTX PRO 6000" not in _gpu.upper().replace("PRO6000", "PRO 6000"):
    _pf_errors.append(f"expected an RTX PRO 6000 GPU, got {_gpu!r}")
for _p in [
    "/kaggle/input/datasets/dfranzen/pennyroyal-v253",
    "/kaggle/input/datasets/dfranzen/taaf-kaggle-source-bundle-copy",
    "/kaggle/input/models/dfranzen/intel-qwen3.8-flash-next-w4a16-autoround/transformers/default/1",
    "/kaggle/input/models/dfranzen/albucino-qwen3-8-flash-next-drafter/transformers/default/1",
    "/kaggle/input/competitions/arc-prize-2026-arc-agi-3/arc_agi_3_wheels",
]:
    if not _PfPath(_p).exists():
        _pf_errors.append(f"missing input {_p}")
_pf_rerun = _pf_os.environ.get("KAGGLE_IS_COMPETITION_RERUN", "").strip().lower() in {"1", "true"}
print("ARC3_PREFLIGHT rerun:", _pf_rerun, flush=True)
if _pf_errors and not _pf_rerun:
    # Save run only: never let a naming quirk kill a real competition rerun.
    raise RuntimeError("ARC3_PREFLIGHT_FAILED: " + "; ".join(_pf_errors))
print("ARC3_PREFLIGHT_OK" if not _pf_errors else f"ARC3_PREFLIGHT_WARN {_pf_errors}", flush=True)
'''

EXTRA_PATCH_APPLY = r'''
# ARC3 Duck: our own harness patches, applied on top of Franzen's patch.
for _extra_patch in ARC3_VARIANT.get("patch_files", []):
    subprocess.run(["git", "apply", "--include=ARC3-Inference/*", "-v", _extra_patch],
                   cwd=f"{BUNDLE_DIR}/src", check=True)
    print(f"ARC3 extra patch applied: {_extra_patch}", flush=True)
'''

ENV_OVERRIDE = r'''
# ARC3 Duck: variant env overrides (both modes).
_variant_env = {k: str(v) for k, v in ARC3_VARIANT.get("env", {}).items()}
os.environ.update(_variant_env)
print("ARC3 variant env:", _variant_env, flush=True)
'''

SMOKE_CONFIG_OLD = """else:
    if USE_PRIORITY_SCHEDULING:
        bm.solver.concurrency = (25 - len(demo_excluded_games)) * bm.n_passes
        bm.solver.max_runtime_s_per_game = 532*60 * bm.solver.concurrency // 110
"""
SMOKE_CONFIG_NEW = """else:
    # ARC3 Duck: the save run is a smoke test of the real solver/agent code path.
    _smoke = ARC3_VARIANT["smoke"]
    bm.n_passes = 1
    bm.solver.concurrency = max(1, len(_smoke["games"]))
    bm.solver.max_runtime_s_per_game = int(_smoke["minutes"] * 60)
    print(f"ARC3 smoke: games={_smoke['games']} minutes={_smoke['minutes']}", flush=True)
"""

SMOKE_FILTER_OLD = ("    game_ids = [game_id for game_id in game_ids if not any(game_id.startswith(g) "
                    "for g in demo_excluded_games)]\n")
SMOKE_FILTER_NEW = SMOKE_FILTER_OLD + (
    "    _smoke_games = ARC3_VARIANT.get('smoke', {}).get('games') or []\n"
    "    if _smoke_games:\n"
    "        game_ids = [g for g in game_ids if any(g.startswith(s) for s in _smoke_games)]\n"
    "    print('ARC3 offline games:', game_ids, flush=True)\n"
)

SMOKE_VERDICT = r'''# ARC3 Duck smoke verdict (save run only). The submit op requires ARC3_SMOKE_OK.
if not TRUE_SUBMISSION:
    _rows, _tok, _acts, _bad = [], 0, 0, []
    for _r in bm.game_runs:
        _gen = int(getattr(_r, "final_generated_tokens", 0) or 0) or sum(
            int(getattr(h, "generated_tokens", 0) or 0) for h in _r.history)
        _non_reset = sum(1 for h in _r.history if getattr(h.action.id, "name", "") != "RESET")
        _score = _r.final_score if _r.final_score is not None else _r._compute_final_score()
        _rows.append(f"  {_r.game_id:<24} state={_r.state:<10} levels={_r.levels_completed}/"
                     f"{_r.number_of_levels} actions={len(_r.history)} non_reset={_non_reset} "
                     f"gen_tokens={_gen} score={_score:.2f}")
        _tok += _gen
        _acts += _non_reset
        if _r.state == "crashed":
            _bad.append(_r.game_id)
    print("ARC3 smoke results:\n" + "\n".join(_rows), flush=True)
    _ok = bool(bm.game_runs) and _tok > 0 and _acts > 0 and not _bad
    print(f"ARC3 smoke: games={len(bm.game_runs)} gen_tokens={_tok} non_reset_actions={_acts} "
          f"crashed={_bad}", flush=True)
    print("ARC3_SMOKE_OK" if _ok else "ARC3_SMOKE_FAILED", flush=True)
    if not _ok:
        raise RuntimeError("ARC3 smoke test failed - do not submit this version")
'''


def intro_md(variant: dict, sha: str) -> str:
    env = "\n".join(f"- `{k}={v}`" for k, v in variant.get("env", {}).items()) or "- none"
    patches = "\n".join(f"- `{p}`" for p in variant.get("patches", [])) or "- none"
    return f"""# ARC3 Duck — variant `{variant['name']}`

{variant.get('description', '').strip()}

**Base:** [Daniel Franzen's ARC-AGI-3 Milestone 2 solution](https://www.kaggle.com/code/dfranzen/arc-agi-3-milestone-2-solution)
([GitHub](https://github.com/da-fr/arc-agi-3-solution), Apache-2.0), built on Tufa Labs' Duck harness
and TAAF. Model: Qwen3.8-Flash-Next (Intel AutoRound W4A16) + Albucino MTP drafter on SGLang
Pennyroyal v2.5.3. Third-party code and weights keep their own licenses.

Generated by `arc-agi-3/duck/notebook/build.py` from commit `{sha}`; do not edit by hand.

**Changes on top of the base**

Environment overrides (both modes):
{env}

Harness patches (both modes):
{patches}

Save run: smoke test only (`{', '.join(variant['smoke']['games'])}` for {variant['smoke']['minutes']} min);
it must print `ARC3_SMOKE_OK`. The competition rerun keeps Franzen's run settings
(1 pass, all games, priority scheduler, 532 min budget).

---
"""


# --------------------------------------------------------------------------
# build
# --------------------------------------------------------------------------
def build(variant_name: str) -> Path:
    raw = BASE_NB.read_bytes()
    got = hashlib.sha256(raw).hexdigest()
    if got != BASE_SHA256:
        raise SystemExit(f"build: base notebook sha256 {got} != pinned {BASE_SHA256}")
    variant = json.loads((HERE / "variants" / f"{variant_name}.json").read_text())
    variant.setdefault("name", variant_name)
    variant.setdefault("env", {})
    variant.setdefault("patches", [])
    smoke = variant.setdefault("smoke", {})
    smoke.setdefault("games", ["ft09", "ls20"])
    smoke.setdefault("minutes", 8)
    sha = git_sha()

    nb = json.loads(raw)
    cells: list[dict] = nb["cells"]
    for c in cells:
        if c["cell_type"] == "code":
            c["outputs"] = []
            c["execution_count"] = None

    # -- our patches: one %%writefile cell each, inserted after Franzen's patch cell
    patch_cells = []
    patch_files = []
    for i, rel in enumerate(variant["patches"]):
        body = (HERE / "patches" / rel).read_text()
        if not body.endswith("\n"):
            body += "\n"
        target = f"/kaggle/duck-extra-{i:02d}.patch"
        patch_files.append(target)
        # Written via a JSON string literal (exact bytes, no %%writefile newline quirks).
        patch_cells.append(code_cell(
            f"# ARC3 Duck harness patch: patches/{rel}\n"
            f"from pathlib import Path as _P\n"
            f"_P({target!r}).write_text({json.dumps(body)})\n"
            f"print('wrote {target}', len(_P({target!r}).read_text()), 'chars')\n"))

    banner = {"name": variant["name"], "git": sha, "env": variant["env"],
              "patches": variant["patches"], "patch_files": patch_files, "smoke": smoke}

    # -- env/setup cell: extra patches after Franzen's, env overrides after setup_env
    i_env = find_cell(cells, "os.environ.update({k: str(v) for k,v in setup_env.items()})")
    t = src(cells[i_env])
    t = replace_once(t, "print('harness patch applied successfully')\n",
                     "print('harness patch applied successfully')\n" + EXTRA_PATCH_APPLY)
    t = replace_once(t, "os.environ.update({k: str(v) for k,v in setup_env.items()})",
                     "os.environ.update({k: str(v) for k,v in setup_env.items()})\n" + ENV_OVERRIDE)
    set_src(cells[i_env], t)

    # -- config hook: TRUE_SUBMISSION branch untouched, save run -> smoke
    i_cfg = find_cell(cells, "if TRUE_SUBMISSION:  # overrides for contest run")
    t = src(cells[i_cfg])
    t = replace_once(t, SMOKE_CONFIG_OLD, SMOKE_CONFIG_NEW)
    set_src(cells[i_cfg], t)

    # -- offline game list: restrict to smoke games (save run only path)
    i_run = find_cell(cells, "def _offline_games(env_dir: str):")
    t = src(cells[i_run])
    t = replace_once(t, SMOKE_FILTER_OLD, SMOKE_FILTER_NEW)
    set_src(cells[i_run], t)

    # -- assemble
    i_patch = find_cell(cells, "%%writefile /kaggle/harness-changes.patch")
    preflight = code_cell(PREFLIGHT.replace("__VARIANT_JSON__", json.dumps(banner, sort_keys=True)))
    new_cells = [md_cell(intro_md(variant, sha)), preflight]
    new_cells += cells[: i_patch + 1] + patch_cells + cells[i_patch + 1:]
    new_cells.append(md_cell("## ARC3 Duck smoke verdict\n\nSave run only."))
    new_cells.append(code_cell(SMOKE_VERDICT))
    nb["cells"] = new_cells
    nb.setdefault("metadata", {}).pop("papermill", None)

    if OUT.exists():
        for p in OUT.iterdir():
            p.unlink()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / NB_NAME).write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n")
    meta = copy.deepcopy(METADATA)
    (OUT / "kernel-metadata.json").write_text(json.dumps(meta, indent=2) + "\n")
    (OUT / "BUILD_INFO.json").write_text(json.dumps(banner, indent=2, sort_keys=True) + "\n")
    print(f"build: variant={variant['name']} git={sha} -> {OUT / NB_NAME} "
          f"({(OUT / NB_NAME).stat().st_size} bytes, {len(new_cells)} cells)")
    return OUT


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant")
    ap.add_argument("--request")
    a = ap.parse_args()
    name = a.variant
    if a.request:
        req = json.loads(Path(a.request).read_text())
        name = name or req.get("args", {}).get("variant")
    if not name:
        sys.exit("build: pass --variant or a request with args.variant")
    build(name)


if __name__ == "__main__":
    main()
