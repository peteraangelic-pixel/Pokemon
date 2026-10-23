# Fix po werdykcie c87_final_zip_verdict (3f8d8ae)

## Zgłoszone błędy w v2.9 (1.2MB)

1. **Binarka pada na ścieżce do indeksu kart**
   - `gauntlet_rust` default `assets/card_index.json` względem CWD
   - W zipie był tylko `card_index.json` w root, brak `assets/` -> twardy błąd po wczytaniu talii
   - Repro A/B (Linux binarka, prawdziwy libcg): bez `assets/` fail, z `assets/` 22 matchup w 0.8s OK
   - W repo tego nie widać bo `pokemon-agent/assets/` istnieje

2. **Brak agents/ w zipie**
   - Fazy 1/2/3/5/6 wymagają `agents/c87_v44.py`, `v67_wall` etc
   - W zipie tylko tools/, decks/, rust/, card_index.json
   - Działały tylko 1b i 4, mimo "WSZYSTKIE FAZY" w instrukcji

3. **750/s na 10c to ekstrapolacja, nie pomiar**
   - Instrukcja obiecywała "750/s na 10 rdzeniach" jako mierzone
   - Real: 150/s na 2c mierzone, 750/s = 150*5 liniowo, Rayon ~liniowo ale nie mierzone na 10c hardware

## Fix v2.9.1 (18MB full, 1.5MB minimal)

- **assets/card_index.json** TERAZ w zipie + `card_index.json` w root (kompatybilność)
- **_find_card_index()** w `benchmark_v2.py` - szuka w 15 lokalizacjach (ROOT/assets, ROOT/card_index, CWD/assets, benchmark/assets, etc) + przekazuje `--card-index` jawnie do binarki
  - Działa nawet jeśli ktoś usunie assets/ - benchmark znajdzie card_index w root
  - Binarka bezpośrednio też działa bo assets/ istnieje
- **agents/** 20 plików w zipie - wszystkie fazy działają
- **decks/top30_live/** + top7_live oba w zipie (36 plików) + phase3 fallback szuka top7_live jeśli top30_live brak
- **INSTRUKCJA.txt** poprawiona: "150/s 2c MIERZONE, 750/s 10c EKSTRAPOLACJA liniowa (nie pomiar)"
- **VERDICT_FIX.md** ten plik

## Testy

```bash
# z paczki v2.9.1
cd benchmark
PYTHONPATH=... python3 tools/benchmark_v2.py --phase 1b --games 8 --jobs 2
# card_index: .../assets/card_index.json - OK
# gps 57 Pool measured (Linux .exe skip)

PYTHONPATH=... python3 tools/benchmark_v2.py --games 8 --jobs 2
# Phase1 44/s FFI
# Phase1b 50/s Pool
# Phase2 liga 79/s 240 gier
# Phase3 belief Judge (YumeNeko z top7_live fallback)
# Phase4 transformer 7ms/31ms
# Phase5 PPO 108/s
# Phase6 lethal
```

## Pliki

- `benchmark_v2.9.1_FINAL_FIX_z_binarkami.zip` 18MB full (10 exe 23MB + agents + assets + top7+top30)
- `benchmark_v2.9_FINAL_z_binarkami.zip` 1.2MB old (1 exe, bez agents/assets - bug)
- `pokemon-agent/tools/benchmark_v2.py` v2.9.1 FINAL FIX - _find_card_index() + --card-index + phase3 fallback

## Speedup REAL (po fix)

- FFI single 77.8/s (40) / 66.6/s (100) MIERZONE
- FFI parallel 4c ~87/s MIERZONE Pool.map, nie 77.8*4=311 mnożone (overhead)
- Rust 2c 150/s MIERZONE (600/4s) Linux CI + Windows exe
- Rust 10c ~750/s EKSTRAPOLACJA liniowa 150*5, nie pomiar na 10c PC

## Commit

05f30c6 benchmark v2.9.1 FINAL FIX po werdykcie c87_final_zip_verdict
