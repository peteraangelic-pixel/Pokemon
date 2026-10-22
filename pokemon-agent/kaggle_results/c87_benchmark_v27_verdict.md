# Werdykt: benchmark v2.7 (c87 eec80a7) — 2026-10-22

UWAGA: kolizja nazw — nasza tools/benchmark_v2.py (20c2d9a) tez nazywa
sie v2.7, a to INNY wariant (odkrywanie binarek z repo, bez fallbacku).

Ich v2.7:
- Phase6 no-data: NAPRAWIONE (brak v85 = {"error":"no data"}).
- Phase1b bez cargo: dziala, lecz przez fallback "parallel FFI", ktory
  mierzy predkosc 1 procesu i MNOZY przez liczbe workerow (77.8x4=311).
  To estymacja, nie pomiar rownolegly. "750 gier/s @10c" = 75/watek x10
  ekstrapolacja; "311 @4c" identycznie. Zaden z tych wynikow nie byl
  zmierzony rownolegle.
- Sciezka Rust (--jobs Rayon) poprawna w kodzie, ale na c87 NADAL brak
  zacommitowanych binarek rust/bin -> w praktyce zawsze fallback.
- Zip "rust_rayon_idealnie" (8.6MB, 0af8ce0): agenci+benchmarki+README,
  lecz ZERO plikow .exe/.dll/libcg — na PC odpali fallback Python.

Do realnego Rust na PC dzis: nasze rust/bin-win/*.exe (CI) + cg.dll
z `pip install kaggle-environments` (patrz rust/PC_PLAN.md).
Rekomendacja: jedna wersja benchmarku w repo i liczby rownolegle
MIErzone (Pool/--workers/--jobs), nie mnozone.
