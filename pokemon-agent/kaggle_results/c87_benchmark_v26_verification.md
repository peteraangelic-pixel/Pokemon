# Weryfikacja benchmark v2.6 REAL (c87 58026a9) — 2026-10-22

- Phase6 z CLI: **dziala** (alias _true_ablation + stara nazwa jako
  alias). Pelny przebieg --games 100 (600 gier) bez crasha.
- Pomiar ablacji (400 gier/porownanie, seat swap): kontrola 0.4675,
  lethal on 0.3825 -> **delta -8.5pp** (CI ~+-5pp). Wrapper zna juz
  obrazenia z card_index i bramke nagröd my<=opp jak v81; wniosek
  zgodny z cala seria: lethal-priority jako twarde przelaczenie
  szkodzi nawet w wersji produkcyjnej (v75l 0.442<0.493, wrapper
  HP<=150 dal -18.8pp przy n=80).
- Parser 1b dzialal juz w v2.5 (33.2 gps mikro / 150 przy 600).
- Drobne: winrate_our_v85=0 przy braku pliku (zamiast null) psuje
  delta_our poza c87; gauntlet_ffi: szerszy fallback szukania libcg
  + unikanie importu kaggle_environments (tylko ALLOW_KE_IMPORT=1) —
  higiena OK, ale teza "import KE psuje FFI (capacity 7)" niezwery-
  fikowana (find_spec i tak importuje pakiet nadrzedny; historyczny
  capacity:7 byl crasha natywnego rust_full wg PORTING).

Werdykt: benchmark dojrzal — wszystkie fazy dzialaja z CLI, ablacja
metodologicznie poprawna. Zostaje kosmetyka raportu (null vs 0).
