#!/usr/bin/env python3
"""Wydobywa patche harnessa z notebooka ARC3 (komórki 4-7 w duck-v7).

Notebook trzyma patche w DWÓCH różnych postaciach i obie trzeba obsłużyć inaczej:

  cell 4  `%%writefile /kaggle/harness-changes.patch`
          -> cała reszta komórki JEST treścią patcha (498 KB, patch Franzena, 16 plików)

  cells 5,6,7  `_P('/kaggle/duck-extra-NN.patch').write_text("...")`
          -> treść jest stringiem w kodzie Pythona. Komórki zaczynają się od
             `from pathlib import Path as _P`, więc NAIWNE exec() zapisuje do /kaggle
             (którego nie ma) i jeszcze czyta plik z powrotem w print().
             Trik: wyciąć tę linię importu i podstawić własny FakePath, który łapie
             write_text/read_text w pamięci.

Wyjście: katalog z 4 patchami gotowymi do `git apply`.
Użycie:  python3 extract_notebook_patches.py <duck-v7.ipynb> <katalog_wyjsciowy>
"""
from __future__ import annotations

import json
import pathlib
import sys


class FakePath:
    """Podstawienie za pathlib.Path - łapie zapis w pamięci zamiast na /kaggle."""

    store: dict[str, str] = {}

    def __init__(self, p):
        self.p = str(p)

    def write_text(self, txt, **kw):
        FakePath.store[self.p] = txt
        return self

    def read_text(self, **kw):
        if self.p not in FakePath.store:
            raise FileNotFoundError(self.p)
        return FakePath.store[self.p]


def main() -> None:
    nb_path = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "duck-v7.ipynb")
    out = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else "patches")
    out.mkdir(parents=True, exist_ok=True)
    nb = json.loads(nb_path.read_text())

    # --- cell 4: %%writefile -> reszta komórki to patch ---
    src4 = "".join(nb["cells"][4]["source"]).splitlines()
    assert src4[0].startswith("%%writefile"), f"cell 4 to nie writefile: {src4[0][:60]}"
    dest = src4[0].split()[-1]
    franzen = out / "0000-franzen-harness-changes.patch"
    franzen.write_text("\n".join(src4[1:]) + "\n")
    files = [l.split(" b/")[-1] for l in src4[1:] if l.startswith("diff --git")]
    print(f"{franzen.name}: {franzen.stat().st_size} B z {dest}, {len(files)} plików")

    # --- cells 5,6,7: patch jako string w kodzie ---
    for i in (5, 6, 7):
        code = "".join(nb["cells"][i]["source"])
        code = "\n".join(l for l in code.splitlines()
                         if "from pathlib import Path as _P" not in l)
        FakePath.store.clear()
        exec(compile(code, f"cell{i}", "exec"), {"_P": FakePath, "Path": FakePath, "__name__": "cell"})
        for k, v in FakePath.store.items():
            name = pathlib.Path(k).name
            # numeracja ich patchy jest myląca: duck-extra-00 = ich "0001",
            # duck-extra-01 = "0002", duck-extra-02 = "0003-early-abandon"
            (out / name).write_text(v)
            diffs = [l.split(" b/")[-1] for l in v.splitlines() if l.startswith("diff --git")]
            print(f"{name}: {len(v)} B (cell {i}), pliki: {diffs}")

    print(f"\nZAPISANO do {out}/")
    print("UWAGA: duck-extra-02 (ich 0003) NIE nakłada się po patchu Franzena -")
    print("       patrz patches/0003b-early-abandon-rebased.patch i PATCH-0004-I-SEARCH.md §1")


if __name__ == "__main__":
    main()
