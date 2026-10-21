# Weryfikacja benchmark_v2 / v2.1 (c87, 21 paz) — 2026-10-21

Ich `tools/benchmark_v2.py`. Naglowkowe liczby (old wrapper 5 gier/s,
FFI 125 gier/s, Rust 750 gier/s, "150x vs OLD = 6x vs FFI", soft lethal
+2-3% narzutu) sa **wpisane na sztywno w prints/docstringu**.

## Co kod realnie robi
- Phase1: mirror FFI, sekwencyjnie, 1 proces (domyslnie 20 gier) — jedyny
  prawdziwy pomiar. "Test lethal" to atrapa: iteruje opcje ATTACK nie
  liczac obrazen, wiec 1-3% to narzut pustej petli, nie logiki +200.
- Fazy 2-5 (frozen liga, belief Judge, transformer inference, PPO
  throughput) NIE istnieja w kodzie — tylko opis commita/docstring.
  Phase6 = same prints.

## Nasze pomiary (sandbox 2 rdzenie)
- Ich Phase1 (v67 mirror, 100g): **66.6 gier/s** = 15 ms/gra (koszt
  polityki), nie 125. 125 (8 ms/gra) to liczba z epoki PORTING przy
  lzejszym ustawieniu — rzad wielkosci OK, ~2x optymizmu.
- Rust natywny `gauntlet_rust`: 600 gier w 4.0 s = **150 gier/s @2 watki
  (75/watek)**, 0 bledow. Ich 750 gier/s to ekstrapolacja na ~10 watkow
  PC, NIE pomiar tego benchmarku. Realne na PC 8-16 watkow.
- `rust_full`: 20 gier bez crasha. "Rust BROKEN capacity:7" dotyczy
  starej prymitywnej polityki (PORTING), nie dzisiejszego gauntlet_rust.
- Nasz BENCH_PC (16 paz): policy_rollout sweep + epoka JAX; Actions
  ~70 gier/s @4 jobs (tryb train z logowaniem decyzji — ciezsza sciezka).

Werdykt: benchmark_v2.1 to dokument narracyjny (sami przyznaja, ze 150x
bylo vs old wrapper). Kierunkowo OK; twardy jest tylko Phase1. Koszt
lethal override to jakosc decyzji (v75l 0.442 < 0.493), nie milisekundy.
