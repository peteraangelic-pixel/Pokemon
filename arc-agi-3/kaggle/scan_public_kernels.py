"""Summarise public ARC-AGI-3 notebooks without importing their code.

We want to know WHAT the top of the leaderboard does -- which models, which
libraries, which techniques -- so we can build our own version. This script
deliberately extracts only metadata, imports and prose. It never copies
solution code into our agent.

Usage:
    python3 scan_public_kernels.py <kernel-dir> <output.md>
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

MODEL_HINTS = (
    "qwen", "gemma", "llama", "mistral", "phi-", "deepseek", "gpt",
    "claude", "gemini", "internvl", "glm", "nemotron", "smollm",
)
ENGINE_HINTS = (
    "vllm", "transformers", "torch", "onnx", "llama.cpp", "llama_cpp",
    "ctransformers", "tensorflow", "jax",
)
TECHNIQUE_HINTS = (
    "bfs", "a-star", "astar", "dijkstra", "beam", "mcts", "monte",
    "replay", "cache", "precompute", "pre-compute", "precompute", "offline",
    "memory", "summary", "summarize", "context", "truncate", "prune",
    "few-shot", "fewshot", "cot", "chain-of-thought", "reflection",
    "self-consistency", "json", "structured", "retry", "backtrack",
    "segmentation", "connected", "component", "object", "diff", "delta",
)


def _text_cells(nb: dict) -> str:
    out = []
    for cell in nb.get("cells", []):
        if cell.get("cell_type") == "markdown":
            out.append("".join(cell.get("source", [])))
    return "\n".join(out)


def _code(nb: dict) -> str:
    out = []
    for cell in nb.get("cells", []):
        if cell.get("cell_type") == "code":
            out.append("".join(cell.get("source", [])))
    return "\n".join(out)


def _imports(code: str) -> set[str]:
    found: set[str] = set()
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return found
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                found.add(node.module.split(".")[0])
    return found


def _hits(text: str, hints: tuple[str, ...]) -> list[str]:
    low = text.lower()
    return [h for h in hints if h in low]


def describe(path: Path) -> dict:
    try:
        nb = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {"file": path.name, "error": str(exc)}

    code = _code(nb)
    prose = _text_cells(nb)
    imports = sorted(_imports(code))
    return {
        "file": path.name,
        "cells": len(nb.get("cells", [])),
        "bytes": path.stat().st_size,
        "imports": imports,
        "models": _hits(code + prose, MODEL_HINTS),
        "engines": _hits(code + prose, ENGINE_HINTS),
        "techniques": _hits(code + prose, TECHNIQUE_HINTS),
        "prose_head": " ".join(prose.split())[:1200],
    }


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: scan_public_kernels.py <dir> <out.md>", file=sys.stderr)
        return 2

    root = Path(sys.argv[1])
    out = Path(sys.argv[2])
    files = sorted(root.rglob("*.ipynb"))
    if not files:
        out.write_text("Brak pobranych notebooków.\n")
        return 0

    lines = ["# Czego używa czołówka — skan publicznych notebooków", ""]
    lines.append(
        "> Celowo **nie kopiujemy ich kodu**. Wyciągamy tylko: jaki model,"
    )
    lines.append("> jaki silnik wnioskowania, jakie techniki. Resztę piszemy sami.")
    lines.append("")

    for f in files:
        d = describe(f)
        lines.append(f"## `{d['file']}`")
        lines.append("")
        if "error" in d:
            lines.append(f"  błąd: {d['error']}")
            lines.append("")
            continue
        lines.append(f"- komórek: {d['cells']}, rozmiar: {d['bytes']:,} B")
        if d["models"]:
            lines.append(f"- **modele**: {', '.join(d['models'])}")
        if d["engines"]:
            lines.append(f"- **silniki**: {', '.join(d['engines'])}")
        if d["techniques"]:
            lines.append(f"- **techniki**: {', '.join(d['techniques'])}")
        if d["imports"]:
            lines.append(f"- importy: {', '.join(d['imports'][:30])}")
        if d["prose_head"]:
            lines.append("")
            lines.append("Opis autora (fragment):")
            lines.append("")
            lines.append("> " + d["prose_head"][:900])
        lines.append("")

    out.write_text("\n".join(lines) + "\n")
    print(out.read_text()[:4000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
