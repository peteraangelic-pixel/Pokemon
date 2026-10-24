#!/usr/bin/env python3
"""Naprawia ich notebook `arc3-duck.ipynb` (duck-v7): run-killer + nasz patch 0004.

CO JEST ZEPSUTE (dowód, nie hipoteza)
-------------------------------------
Komórka 7 zapisuje `/kaggle/duck-extra-02.patch` = ich `0003-early-abandon.patch`, którego
hunk `@@ -35,6 +35,7 @@` w `solver.py` NIE nakłada się na drzewo po patchu Franzena
(`harness-changes.patch`, komórka 4). Komórka 10 aplikuje patche z `check=True`:

    subprocess.run(["git", "apply", "--include=ARC3-Inference/*", "-v",
                    "/kaggle/harness-changes.patch"], cwd=f"{BUNDLE_DIR}/src", check=True)
    for _extra_patch in ARC3_VARIANT.get("patch_files", []):
        subprocess.run([...], cwd=f"{BUNDLE_DIR}/src", check=True)

czyli `CalledProcessError` na trzecim patchu -> **notebook umiera przed jakimkolwiek
użyciem GPU**. Zweryfikowane `git apply` na prawdziwym drzewie ich repo
(`results/verification_output.txt`, łańcuch C = FAIL solver.py:35).

Do tego ich 0003 jest merytorycznie podwójnie nieskuteczny (FAKTY §9.2): warunek
`levels_completed > min_levels()` przy `ARC3_ABANDON_MIN_LEVELS=0` chroni przed abandonem
dokładnie te gry, które wyciekają, a licznik jest liczony od `token_baseline` zamiast
`game_token_baseline`, więc cap 60 000 jest nieosiągalny.

CO TEN SKRYPT ROBI (i tylko to)
-------------------------------
  1. podmienia TREŚĆ komórki 7: `/kaggle/duck-extra-02.patch` <- nasz
     `0004-standalone-level-token-cap.patch`. Nie dodajemy nowej komórki ani nowego pliku,
     więc `patch_files` w `ARC3_VARIANT` zostaje bez zmian i kolejność jest zachowana.
  2. aktualizuje `ARC3_VARIANT` w komórce 1: nazwa patcha 0003 -> 0004, env 0004 dodane,
     a osierocone `ARC3_ABANDON_*` wyzerowane (modułu `arc3_abandon` już nie ma w drzewie,
     więc zostawienie "60000" sugerowałoby innej gałęzi, że abandon działa).

Nie rusza: modelu, konfiguracji SGLang, budżetów, smoke'a, `ONLY_RESET_LEVELS`, preflightu.

DLACZEGO 0004 W SLOCIE 02, A NIE JAKO CZWARTY PATCH
----------------------------------------------------
Sprawdzone empirycznie: `0004-standalone` NIE nakłada się po `0003b` (oba ruszają
`solver.py` w tym samym rejonie) - `error: patch failed: solver.py:46`. Natomiast łańcuch
`franzen -> 0001 -> 0002 -> 0004-standalone` nakłada się czysto. Ponieważ 0004 i tak
zastępuje 0003 (ma własną logikę ABANDON), poprawna konfiguracja to ZAMIENIĆ, nie DODAĆ.

WERYFIKACJA TEJ DOKŁADNEJ KONFIGURACJI (wykonana, nie zadeklarowana)
---------------------------------------------------------------------
Patches wydobyte z wygenerowanego notebooka, nałożone komendami z komórki 10 na pristine
drzewo ARC3-Inference (bundle r033):
    OK harness-changes.patch (498 780 B, bit-w-bit zgodny z oryginałem)
    OK duck-extra-00.patch   (0001 level notes)
    OK duck-extra-01.patch   (0002 world model)
    OK duck-extra-02.patch   (nasz 0004-standalone)
    OK py_compile solver.py / tool_agent.py / arc3_level_budget.py
    OK 8 referencji `arc3_level_budget` w solver.py, 0 referencji `arc3_abandon`
    OK testy jednostkowe 16/16 (2 skipped - brak arc3_abandon w wariancie standalone)

PUŁAPKA PRZY WYDOBYWANIU PATCHY Z NOTEBOOKA (kosztowała mnie jedną fałszywą porażkę)
------------------------------------------------------------------------------------
Komórka 4 to `%%writefile /kaggle/harness-changes.patch` i jej treść MUSI zostać zapisana
Z KOŃCOWYM NEWLINE. Bez niego `git apply` zgłasza `corrupt patch at line 10086` na zupełnie
sprawnym patchu (różnica 1 bajt: 498 779 vs 498 780). Komórki 5-8 trzymają treść jako
literal łańcucha w `_P(...).write_text(...)` i ścieżka bywa w APOSTROFACH - regex musi
przyjmować oba rodzaje cudzysłowów, inaczej cicho pominie duck-extra-00/01.

Użycie:
  python3 make_notebook_patch.py <in.ipynb> <out.ipynb> [--dry-run]

Kill-switch: `ARC3_LEVEL_TOKEN_CAP=0` wyłącza całą funkcjonalność 0004 i przywraca
zachowanie stockowe (przetestowane w testach jednostkowych).
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PATCH_DIR = HERE.parent / "patches"

# slot w notebooku -> nasz patch, który go ZASTĘPUJE
REPLACEMENTS = {
    "/kaggle/duck-extra-02.patch": "0004-standalone-level-token-cap.patch",
}
# nazwy w ARC3_VARIANT["patches"]: stare -> nowe
RENAME_PATCH_NAMES = {
    "0003-early-abandon.patch": "0004-level-token-cap.patch",
}
# env, które dokłada 0004; wartości z pomiaru ich własnego smoke r019 (FAKTY §2 i §4)
NEW_ENV = {
    # 35% tokenów i akcji w r019 poszło na poziom, który nigdy nie został ukończony
    # (tn36 86%, ls20 91%); 45k odcina wyciek, zostawiając zapas na poziom naprawdę trudny
    "ARC3_LEVEL_TOKEN_CAP": "45000",
    # jeden darmowy RESET poziomu (ONLY_RESET_LEVELS=true zachowuje poziom), potem ABANDON
    "ARC3_LEVEL_RESETS_MAX": "1",
    # 0 = żadna gra nie jest chroniona przed abandonem (ich 0003 z min_levels=0 chronił
    # dokładnie te gry, które wyciekały)
    "ARC3_LEVEL_MIN_DONE": "0",
}
# osierocone po usunięciu 0003 - modułu arc3_abandon nie ma już w drzewie
ORPHANED_ENV_ZERO = ["ARC3_ABANDON_TOKENS", "ARC3_ABANDON_MIN_LEVELS"]

# literal łańcucha w apostrofach LUB cudzysłowach (komórki 5-8 używają apostrofów w ścieżce)
_WRITER_RE = re.compile(
    r"""_P\(\s*('(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*")\s*\)"""
    r"""\.write_text\(\s*('(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*")\s*\)""",
    re.S,
)


def _patch_text(fname: str) -> str:
    p = PATCH_DIR / fname
    if not p.is_file():
        sys.exit(f"BLAD: brak patcha {p} (uruchom najpierw tools/fetch_repo_artifacts.sh)")
    text = p.read_text(encoding="utf-8")
    # KOŃCOWY NEWLINE JEST OBOWIĄZKOWY: bez niego git apply mówi "corrupt patch"
    return text if text.endswith("\n") else text + "\n"


def _writer_cell(target_path: str, patch_file: str, header: str) -> list[str]:
    """Komórka w ich konwencji: `from pathlib import Path as _P` + write_text(literal)."""
    src = (
        f"{header}\n"
        "from pathlib import Path as _P\n"
        f"_P({json.dumps(target_path)}).write_text({json.dumps(_patch_text(patch_file))})\n"
        f"print('wrote {target_path}', "
        f"len(_P({json.dumps(target_path)}).read_text()), 'chars')\n"
    )
    return src.splitlines(keepends=True)


def _find_writer_cell(cells: list[dict], target_path: str) -> int | None:
    for i, c in enumerate(cells):
        if c.get("cell_type") != "code":
            continue
        src = "".join(c.get("source") or [])
        for m in _WRITER_RE.finditer(src):
            try:
                if ast.literal_eval(m.group(1)) == target_path:
                    return i
            except (ValueError, SyntaxError):
                continue
    return None


def _update_variant(cells: list[dict]) -> bool:
    """Podmienia ARC3_VARIANT = {...} w komórce deklarującej wariant."""
    for c in cells:
        if c.get("cell_type") != "code":
            continue
        src = "".join(c.get("source") or [])
        if "ARC3_VARIANT" not in src or "patch_files" not in src:
            continue
        start = src.find("ARC3_VARIANT")
        brace = src.find("{", src.find("=", start))
        if brace < 0:
            continue
        end = src.find("\n", brace)          # ich JSON jest w jednej linii
        literal = src[brace:end if end > 0 else len(src)]
        try:
            variant = json.loads(literal)
        except json.JSONDecodeError as exc:
            print(f"  OSTRZEZENIE: nie udało się sparsować ARC3_VARIANT ({exc}) - "
                  "zaktualizuj env i nazwy patchy ręcznie", file=sys.stderr)
            return False

        env = variant.setdefault("env", {})
        env.update(NEW_ENV)
        for k in ORPHANED_ENV_ZERO:
            if k in env:
                env[k] = "0"

        names = variant.setdefault("patches", [])
        variant["patches"] = [RENAME_PATCH_NAMES.get(n, n) for n in names]

        new_literal = json.dumps(variant, sort_keys=True)
        c["source"] = (src[:brace] + new_literal + (src[end:] if end > 0 else "")
                       ).splitlines(keepends=True)
        return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("notebook_in")
    ap.add_argument("notebook_out")
    ap.add_argument("--dry-run", action="store_true", help="tylko raport, bez zapisu")
    args = ap.parse_args()

    nb = json.loads(Path(args.notebook_in).read_text(encoding="utf-8"))
    cells = nb["cells"]
    print(f"wczytano {args.notebook_in}: {len(cells)} komórek")

    for target, patch_file in REPLACEMENTS.items():
        i = _find_writer_cell(cells, target)
        if i is None:
            print(f"  OSTRZEZENIE: nie znaleziono komórki zapisującej {target} - ich "
                  "notebook ma inną strukturę, sprawdź ręcznie", file=sys.stderr)
            continue
        old_len = len("".join(cells[i].get("source") or []))
        header = (f"# ARC3 Duck harness patch: patches/{patch_file}\n"
                  "# REPLACES their 0003-early-abandon.patch in this slot:\n"
                  "#   (a) their 0003 does not apply after harness-changes.patch and cell 10\n"
                  "#       uses check=True -> notebook dies before any GPU work;\n"
                  "#   (b) 0004 supersedes it (own ABANDON logic + free level RESET).\n"
                  "# Verified chain: franzen -> 0001 -> 0002 -> this = all OK, py_compile OK,\n"
                  "# 16/16 unit tests OK. Do NOT also apply 0003b: 0004 conflicts with it at\n"
                  "# solver.py:46.")
        cells[i]["source"] = _writer_cell(target, patch_file, header)
        new_len = len("".join(cells[i]["source"]))
        print(f"  komórka {i}: {target} <- {patch_file} "
              f"({old_len} -> {new_len} znaków)  [NAPRAWA RUN-KILLERA + patch 0004]")

    if _update_variant(cells):
        print("  ARC3_VARIANT: patches + env zaktualizowane")
        for k, v in sorted(NEW_ENV.items()):
            print(f"    + {k}={v}")
        for k in ORPHANED_ENV_ZERO:
            print(f"    ~ {k}=0  (osierocone po usunięciu 0003)")
    else:
        print("  OSTRZEZENIE: ARC3_VARIANT nie zaktualizowany", file=sys.stderr)

    print(f"komórek po zmianach: {len(cells)} (struktura niezmieniona)")
    if args.dry_run:
        print("--dry-run: nie zapisuję")
        return 0
    out = Path(args.notebook_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"ZAPISANO {out} ({out.stat().st_size} B)")
    print()
    print("Następny krok OBOWIĄZKOWY - bez niego nie wiemy, czy łańcuch się nakłada:")
    print("  1) wydobyć patche z wygenerowanego notebooka (patrz docstring: końcowy NEWLINE")
    print("     i oba rodzaje cudzysłowów), 2) nałożyć je komendami z komórki 10 na pristine")
    print("     drzewo ARC3-Inference, 3) py_compile solver.py, 4) testy jednostkowe.")
    print("  Gotowy skrypt: bash tools/verify_patch_chains.sh")
    return 0


if __name__ == "__main__":
    sys.exit(main())
