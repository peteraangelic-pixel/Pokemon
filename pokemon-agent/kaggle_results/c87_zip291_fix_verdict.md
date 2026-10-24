# Werdykt: benchmark v2.9.1 FIX (c87 05f30c6 + zipy) — 2026-10-23

Wszystkie 3 zarzuty z werdyktu 3f8d8ae naprawione naprawde:
- assets/card_index.json JEST w zipie (minimal: 78 plikow) ORAZ
  benchmark ma _find_card_index() i przekazuje --card-index jawnie
  -> sciezka CWD przestala miec znaczenie.
- agents/ w paczce (14 plikow, w tym v67 i v85) -> wszystkie fazy
  maja czym grac.
- Nota o 750/s poprawiona na EKSTRAPOLACJA w kodzie i instrukcji.

Test koncowy z rozpakowanej paczki (czysty katalog, Linux):
- Phase1 FFI: 20 gier, 78.2 gier/s — dziala z agents/ paczki.
- Phase1b: fallback Pool mierzony (na Linux brak binarki .exe —
  sciezka Windows niezweryfikowalna wykonawczo w sandboxie, ale
  binarka = ten sam blob CI, ktory z ukladem assets/ przechodzi A/B).
- Phase4: forwardy mierzone (8.0 ms L4 / 34.3 ms L8).

Drobne: blob "MINIMAL_1.5MB" ma 2.32 MB. Werdykt: paczka funkcjonalnie
100% do deklarowanego celu; ostatni smoke test .exe musi zrobic user
na swoim PC (30 s: --phase 1b).
