# Benchmark v2.9.1 — weryfikacja i synchronizacja na `arena/a450b00f-pokemon` (25.10)

## Stan przed synchronizacją

- Nasza gałąź: `pokemon-agent/tools/benchmark_v2.py` = **v2.9** (796 linii).
- `arena/c87f7a48-pokemon`: **v2.9.1 FINAL FIX** (921 linii) + zipy
  `benchmark_v2.9.1_*` w korzeniu repo. Unifikacja „bajt w bajt" (9247fc6)
  była prawdziwa dla v2.9, ale od tamtej pory gałęzie znowu się rozeszły.

## Co sprawdziłem w v2.9.1 (kod + bieg końcowy)

- Baner i fixy obecne w kodzie: `_find_cg_lib()` (jawna ścieżka cg.dll/.so),
  `_find_card_index()` + `--card-index` do binarki, `RUST_BINS` tylko
  `gauntlet_rust` (CLI `--our-deck/--live-dir`; `rust_gauntlet` usunięty —
  inne CLI, dawał 0), wybór binarki zależny od platformy (.exe nie odpalane
  na Linuxie), faza 6: brak pliku = „no data, not 0".
- **Bieg końcowy u mnie (sandbox Linux, 2 rdzenie)**: `--phase 1b --games 10
  --jobs 2` z `kaggle-environments` z PyPI: benchmark sam znalazł
  `rust/bin/gauntlet_rust`, `libcg.so` i `assets/card_index.json`; tryb
  raportowany jako „Rust+Rayon REAL measured", **69,7 gier/s** na tej próbce,
  a „750/s na 10 rdzeniach" jawnie oznaczone jako ekstrapolacja, nie pomiar.
- Oba pliki (v2.9 i v2.9.1) kompilują się; CLI degraduje się łagodnie bez
  zależności (ostrzeżenie zamiast crasha).

## Synchronizacja

`tools/benchmark_v2.py` na tej gałęzi = teraz v2.9.1 (kopia 1:1 z c87).
To jest jedyna kanoniczna wersja; dalsze zmiany robić w jednym miejscu
i kopiować, zamiast utrzymywać równoległe wersje.

## Resztówka (tylko PC usera)

Ścieżka windowsowa (.exe + cg.dll) jest w sandboxie niewykonywalna. Test
dymny na PC: `pip install kaggle-environments`, potem
`python tools/benchmark_v2.py --phase 1b --games 40 --jobs 4`.
Wynik >0 gier/s domyka paczkę wykonawczo także na Windows.
