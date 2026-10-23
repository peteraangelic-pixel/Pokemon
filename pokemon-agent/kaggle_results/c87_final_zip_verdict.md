# Werdykt: benchmark_v2.9_FINAL_z_binarkami.zip (c87 1ffa3f9) — 2026-10-22

Zawartosc OK: nasza CI binarka gauntlet_rust.exe (2 833 072 B = ten sam
blob co arena450 bin-win), benchmark v2.9 platform-aware, 22 talie
top7_live, zrodla, card_index.json (w KORZENIU paczki), INSTRUKCJA.

## BUG: faza Rust z paczki pada od razu (reprodukcja A/B)
Exe domyslnie czyta `assets/card_index.json` wzgledem CWD
(CardIndex::load -> read_to_string, bez fallbacku). Zip trzyma
card_index.json w korzeniu `benchmark/`, katalogu `assets/` brak.
Pomiar (binarka Linux, ten sam kod, prawdziwy libcg):
- cwd bez assets/: "Our deck ... (60 cards)" -> Error: No such file
  or directory (os error 2). Faza 1b w paczce = martwa.
- cwd z assets/card_index.json: dziala (Overall 0.744, 22x2 gry, 0.8 s).
W repo tego nie widac, bo pokemon-agent/assets/card_index.json istnieje.
Fix: wrzucic card_index do `assets/` w zipie ALBO przekazac
`--card-index` w phase1b.

## Inne
- Brak katalogu agents/ w zipie -> fazy 1/2/3/5/6 niedzialajace z samej
  paczki ("WSZYSTKIE FAZY" w instrukcji to przesada); dziala 1b (po
  fixie) i 4.
- INSTRUKCJA dalej obiecuje "750/s 10c" (ekstrapolacja, nie pomiar).
- 2 nazwy talii z mojibake (UTF-8 w zipie) — kosmetyka.

Postep realny (binarka w paczce, instrukcja Win/Linux), lecz teza
"dziala w 100% z binarkami" przed fixem sciezki assets/ nieprawdziwa.
