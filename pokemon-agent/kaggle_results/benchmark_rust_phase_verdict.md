# Faza Rust w benchmarku: teza c87 + naprawa (2026-10-22)

## Teza "Bez Rusta benchmark dziala w 100%" — PRAWDA (na c87)
Na galazi c87 `rust/` zawiera TYLKO zrodla: brak `rust/bin/`,
`bin-win/`, `target/`. Benchmark v2.x szuka binarki w repo, a sandbox
nie ma cargo -> faza 1b zawsze zwraca blad "no rust bin". Fazy
pythonowe faktycznie dzialaja w 100%. U nas binarki sa zacommitowane
przez CI (rust/bin linux + rust/bin-win .exe), wiec faza dziala.

## Naprawa (tools/benchmark_v2.py = c87 v2.6 + patch a450 "v2.7")
- Odkrywanie tylko binarek o zgodnym CLI (gauntlet_rust): rust/bin,
  rust/bin-win (.exe), rust/target/release. `rust_gauntlet` (inne CLI)
  usuniety z kandydatow — wczesniej mogl byc wybrany i dawal 0.
- Jawna sciezka libcg (cg.dll/libcg.so/.dylib) z .venv/sysconfig/site,
  subprocess z cwd=korzen repo — koniec zaleznosci od miejsca startu.
- Brak binarki = {"skipped": ...}, nie blad.
Dla c87: cherry-pick tego pliku + wziasc rust/bin(-win) z naszej
galezi albo puszcic workflow rust-build.

## Predkosc — uczciwie (sandbox 2 rdzenie)
- Faza 1 FFI (mirror v67, 100 gier): 66.0 gier/s.
- Faza 1b Rust (pula top7_live 22 talie, 1094 gry): **63.1 gier/s**.
- Wczesniejsze 150 gier/s to byl MIRROR (600 gier/4.0 s) — krotkie gry.
Czyli w tym benchmarku Rust NIE jest "kilka razy szybszy": gra inna
(rodzima, uproszczona) heurystyka i dluzszymi meczami (sciany).
Zysk Rusta = skalowanie Rayona na rdzeniach PC + brak kosztu decyzji
Pythona DOPIERO po porcie prawdziwej polityki (etap 2 PC_PLAN).
Na PC 8-16 watkow spodziewany wyrazny przod, nie obiecane "kilka x".
