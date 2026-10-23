# Benchmark v2.9 (merge a450 v2.7 + c87 v2.8) — 2026-10-22

Odpowiedz na pytanie "czy nasz benchmark jest lepszy niz ich 2.7":
- Na etapie 2.7: TAK — nasz mierzyl naprawde (binarki z repo),
  ich 2.7 mnozyl (311=77.8x4, 750=75x10). Werdykt 582774b.
- Ich v2.8 (9055b08) przyjela audyt: Pool.map MIERZONY (zweryfikowane:
  10 gier/2 workerow realnie), bin-win w kandydatach, no-data w fazie 6.
  Dogonila i poszerzyla pokrycie (cos mierzy wszedzie).
- v2.9 (ten commit, tools/benchmark_v2.py): polaczenie — odkrywanie
  binarek CLI-safe + jawna sciezka libcg + cwd (a450) ORAZ mierzony
  fallback Pool i no-data (c87 v2.8). Test: Rust 110 gier 73.1 g/s;
  fallback Pool dziala po ukryciu binarek.
Resztki: ich RUST_BINS ma rust_gauntlet (inne CLI) przed target —
u nas usuniety z kandydatow. Jedna wersja w repo = v2.9.
