# battery-sim — symulator nowego typu ogniwa (katoda | elektrolit | anoda)

Symulator w **Rust** do testowania kandydatów na nowy typ akumulatora.
Modeluje ogniwo jako trójkę **katoda | elektrolit | anoda** (czyli może być
3-składnikowe, jak Li-ion, ale też inne chemie: Li-S, Na-ion, stałe elektrolity…).

## Co potrafi

- **Energia**: Wh/kg i mAh/g z krzywych OCV + pełnego bilansu masowego
  (powłoki, folie Al/Cu, separator, elektrolit, obudowa) — na poziomie ogniwa.
- **Szybkie ładowanie**: opór wewnętrzny (jonowy + aktywacja Butler-Volmer +
  interfaza), plating litu przy dużym C-rate i niskiej temperaturze → martwy Li
  i dendryty, czas ładowania do 80% SOC (t80).
- **Żywotność cykliczna**: wzrost SEI (paraboliczny, Arrhenius), straty
  inwentarza litu, degradacja katody zależna od napięcia i temperatury, stres
  oksydacyjny elektrolitu przy katodach wysokonapięciowych, shuttle (Li-S),
  dead Li (Li metal, Si). EOL = 80% pojemności początkowej / zwarcie / runaway.
- **Bezpieczeństwo (termika)**: bryła o stałej pojemności cieplnej,
  I²R + aktywacja + reakcje uboczne (rozpad SEI, reakcja litowanej anody
  z elektrolitem — lawinowa od ~150 °C, spalanie elektrolitu, rozpad katody,
  stopienie litu). Separator PP: shutdown 130 °C, melt 160 °C → zwarcie.
- **Test abusów**: piec 150 °C + przeładowanie 1C przez 3 h — ogniwo nie może
  wybuchnąć ani wejść w thermal runaway.

## Kryteria projektu (wbudowane w sweep)

1. **Energia** właściwa ≥ referencyjnego Li-ion (NMC811/grafit/LP57, ~237 Wh/kg).
2. **Bezpieczeństwo**: brak eksplozji / thermal runaway / zwarcia — ani podczas
   cyklowania, ani w teście abusów.
3. **Szybkie ładowanie**: ≥ 500 cykli przy ładowaniu ≥ 2C.

Każda kombinacja dostaje też `score` (0..1) do rankingu:
40% energia, 30% żywotność, 20% bezpieczeństwo, 10% szybkość (t80).

## Budowanie i uruchamianie (na Twoim komputerze)

```bash
cd battery-sim
cargo run --release -- sweep          # pełny sweep (rayon, wszystkie wątki)
cargo run --release -- demo           # szybka demonstracja
cargo run --release -- cell --cathode NMC811 --anode SIC --electrolyte SOLID --c-rate 2 --abuse --csv przebieg.csv
cargo run --release -- list           # baza materiałów
```

Bez rayona (czysty `std`, własny pool wątków — przydaje się bez sieci):

```bash
cargo run --release --no-default-features -- sweep
```

### przydatne opcje sweepu

```bash
cargo run --release -- sweep --quick                 # mała siatka (szybki podgląd)
cargo run --release -- sweep --cathodes NMC811,LMR,SULFUR --anodes SIC,LIMETAL
cargo run --release -- sweep --loadings 15,20,25 --c-rates 2,3 --temps 0,25,45
cargo run --release -- sweep --samples 60            # losowa próbka 60 kombinacji
cargo run --release -- sweep --csv wyniki.csv --top 50
cargo run --release -- sweep --min-cycles 1000 --energy-factor 1.2   # ostrzejsze kryteria
```

### Duże siatki (np. na 16-rdzeniowym Ryzen 5950X)

Rayon wykorzystuje wszystkie rdzenie — siatkę można śmiało rozbudować:

```bash
cargo run --release -- sweep \
  --loadings 10,15,20,25,30 --nps 1.05,1.1,1.2,1.3 --temps 0,25,45 \
  --c-rates 1,2,3,4,6 --csv wyniki.csv
# 8 katod x 5 anod x 3 elektrolity x 5 loadingow x 4 N/P x 3 temperatury = 7200 kombinacji
```

Pełna domyślna siatka (120 kombinacji chemicznych: 8×5×3) liczy się w sekundy,
7200 kombinacji — w minuty. Wyniki (CSV) warto zapisywać: to mapa „co warto zbudować".

### CI (GitHub Actions)

`.github/workflows/ci.yml` (w katalogu głównym repo): przy każdym pushu/PR oraz
ręcznie (`Run workflow`) — `cargo fmt --check`, `cargo clippy` (obie konfiguracje:
z rayon i bez), build release, `demo` oraz sweep z wynikami jako artefakt do
pobrania (`.github/workflows/ci.yml` działa po przeniesieniu projektu do nowego repo).
```

## Materiały w bazie

- **Katody**: NMC811, NMC532, NCA, LFP, LCO, LMR (Li-rich), LNMO (spinel 5 V), SULFUR (Li-S)
- **Anody**: GRAPHITE, LTO, SIC (Si-C), LIMETAL (lit metal), HC (hard carbon, Na-ion)
- **Elektrolity**: LP57 (ciekły, palny, okno 4.4 V), IONIC (ciecz jonowa, niepalny,
  okno 5 V), SOLID (stały, niepalny, okno 5 V)

Nowe materiały dopisuje się w `src/materials.rs` (parametry + krzywe OCV).

## Struktura projektu

```
battery-sim/
  Cargo.toml            # zależność rayon (opcjonalna, domyślnie włączona)
  src/main.rs           # CLI (demo / cell / sweep / list / baseline)
  src/materials.rs      # baza materiałów (katody, anody, elektrolity)
  src/cell.rs           # konstrukcja ogniwa: masa, energia, R0, okno napięć
  src/sim.rs            # symulacja cykli + degradacja + termika + bezpieczeństwo
  src/sweep.rs          # siatka kombinacji, kryteria, scoring, losowanie próbek
  src/par.rs            # równoległość: rayon albo pool std::thread
  src/report.rs         # tabele, CSV
  tools/model_prototype.py  # prototyp tego samego modelu w Pythonie
```

## Walidacja modelu

`tools/model_prototype.py` to **identyczny model** (port 1:1) w Pythonie — służy
jako referencja walidacyjna (uruchomienie: `python3 tools/model_prototype.py`).
Spodziewane wyniki referencyjne (NMC811/grafit/LP57, 20 mg/cm²): ~237 Wh/kg,
~64 mAh/g, R0 ≈ 4.2 Ω·cm²; żywotność ~950 cykli @1C, ~800 @2C, ~250 @3C;
w 0 °C plating skraca życie do ~360 cykli @1C. LFP/LTO: ~83 Wh/kg, >2000 cykli.
Test abusów 150 °C: NMC/grafit + palny elektrolit → eksplozja; LTO, Si-C,
lit-metal i elektrolity stałe → przeżywają.

Model jest **fenomenologiczny** (stałe skalibrowane na rząd wielkości
literaturowy), nie ab initio — służy do szybkiego rankingu kandydatów
i „co-jeśli” (zmień parametr w `materials.rs` / `sim.rs` i zobacz efekt).
