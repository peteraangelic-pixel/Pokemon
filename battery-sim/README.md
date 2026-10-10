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
- **Metryki rynkowe**: Wh/kg na poziomie **pakietu** (×0.72), **Wh/L**
  (gęstości powłok + grubość elektrod), **koszt materiałowy $/kWh**
  (materiały aktywne + elektrolit) — liczby porównywalne z kartami katalogowymi.
- **Benchmark i raport**: `benchmark` (nasi kandydaci kontra ogniwa komercyjne)
  oraz `report --lang pl|en` (raport Markdown gotowy do pokazania komuś).

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
cargo run --release -- list           # baza materiałów (+ koszt USD/kg)
cargo run --release -- benchmark      # nasi kandydaci kontra rynek
cargo run --release -- report --lang en --out report.md   # raport po angielsku
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
# 11 katod x 5 anod x 4 elektrolity x 5 loadingow x 4 N/P x 3 temperatury = 13200 kombinacji
```

Pełna domyślna siatka (220 kombinacji chemicznych: 11×5×4) liczy się w sekundy,
13200 kombinacji — w minuty. Wyniki (CSV) warto zapisywać: to mapa „co warto zbudować".

### CI (GitHub Actions)

`.github/workflows/ci.yml` (w katalogu głównym repo): przy każdym pushu/PR oraz
ręcznie (`Run workflow`) — `cargo fmt --check`, `cargo clippy` (obie konfiguracje:
z rayon i bez), build release, `demo`, sweep z wynikami jako artefakt do
pobrania, `benchmark` oraz raporty PL/EN jako artefakt (`raporty-pl-en`).

## Materiały w bazie

- **Katody Li** (vs Li/Li+): NMC811, NMC532, NCA, LFP, LCO, LMR (Li-rich), LNMO (spinel 5 V), SULFUR (Li-S)
- **Katody Na** (vs Na/Na+): NA_O3 (tlenek warstwowy), NA_PW (biel pruska),
  NA_NFPP (polianionowy Na₃V₂(PO₄)₃) — ogniwa sodowe mają kolektor **Al po obu
  stronach** (Na nie tworzy stopów z Al — oszczędność masy i kosztu vs Cu)
- **Anody**: GRAPHITE, LTO, SIC (Si-C), LIMETAL (lit metal), HC (hard carbon, Na-ion)
- **Elektrolity**: LP57 (ciekły, palny, okno 4.4 V), **GEL** (żelowy/półstały —
  kierunek CATL condensed / WeLion; z separatorem ceramicznym: T zwarcia 200 °C,
  rozkład 250 °C, okno 4.6 V), IONIC (ciecz jonowa, niepalny, okno 5 V),
  SOLID (stały, niepalny, okno 5 V)
- **Koszty materiałów** (USD/kg, 2025): `cost_*_usd_kg` w `src/materials.rs`

Nowe materiały dopisuje się w `src/materials.rs` (parametry + krzywe OCV).

## Metryki rynkowe — jak czytać liczby

Każde ogniwo dostaje trzy metryki **porównywalne z kartami katalogowymi producentów**:

- **Wh/kg pakietowe** = Wh/kg ogniwa × 0.72 (BMS, obudowa, chłodzenie; typowy
  współczynnik branżowy, np. WeLion 360 Wh/kg ogniwo → 260 Wh/kg pakiet).
- **Wh/L** = energia / objętość ogniwa (z gęstości powłok elektrod i ich grubości;
  bez obudowy pakietu).
- **Koszt materiałowy $/kWh** = (katoda + anoda + elektrolit) wg cen 2025
  (`cost_*_usd_kg` w `src/materials.rs`); **bez** folii, separatora, spoiw,
  capex i marży — to dolna granica kosztu, nie cena sprzedaży.

## Benchmark kontra rynek

`battery-sim benchmark` drukuje naszych kandydatów obok ogniw komercyjnych
(dane producentów / prasa, 2025–2026):

| ogniwo | Wh/kg ogniwo | Wh/kg pakiet | Wh/L | uwagi |
|---|---|---|---|---|
| CATL Qilin (NMC) | bd | 255 | bd | Zeekr 009, AITO, Li Auto (od 2023) |
| BYD Blade (LFP) | 160 | 140 | bd | >3000 cykli, bez kobaltu |
| WeLion × NIO (półstałe) | 360 | 260 | bd | pierwsze półstałe w produkcji seryjnej (2024) |
| CATL condensed | 500 | bd | bd | lotnictwo; samolot 4 t oblatany 2025 |
| Amprius SiMaxx (Si) | 500 | bd | 1300 | nanodruty krzemowe, wysyłki komercyjne |
| StoreDot XFC (Si 40%) | 300 | bd | bd | 1000 cykli XFC (deklaracja), 10–80% <10 min |
| CATL Naxtra (Na-jon) | 175 | bd | bd | produkcja od końca 2025, −40 °C, GB 38031-2025 |
| QuantumScape (Li-metal) | 301 | bd | 844 | próbki 2026, auta 2028 (VW) |
| Samsung SDI SolidStack | bd | bd | 900* | produkcja H2 2027 |
| BYD FinDreams (stałe) | ~400* | bd | bd | auto demo 2027, skala ~2030 |

Źródła: greencarreports.com, newatlas.com (CATL condensed); spectrum.ieee.org,
insideevs.com, evtechinsider.com (WeLion/NIO, IM L6); thestreet.com (BYD 2026);
ainvest.com (Amprius); eepower.com, emobility-engineering.com, store-dot.com
(StoreDot); electrichybridvehicletechnology.com, zvepow.com (Naxtra);
curionic.net (QuantumScape); exoswan.com (Samsung SDI); techcrunch.com,
autoevtimes.com (Sila); carnewschina.com, paultan.org, interestingengineering.com,
insideevs.com (Shenxing 4C–6C, Golden Brick 5.5C).

## Raport PL/EN

`battery-sim report --lang pl|en [--out plik.md]` generuje raport Markdown:
kryteria, metodyka, kandydaci (tabela), porównanie z rynkiem, wnioski,
ograniczenia modelu i ścieżka walidacji. PL domyślnie (`raport.md`), EN przez
`--lang en` (`report.md`). W CI raporty są artefaktami do pobrania.

## Prezentowanie wyników — ścieżka walidacji

Symulacja to narzędzie do **selekcji kandydatów**, nie certyfikat. Zanim
pokażesz wyniki firmie, warto mieć:

1. **zamrożony model + wyniki** (raport + CSV z CI — reprodukowalne),
2. **coin cells** 2–3 kandydatów (materiały: Si-C, żel, hard carbon) i testy
   cykliczne @2C,
3. **pouch cells + testy abuse** w zewnętrznym labie (TÜV / UL 9540A /
   GB 38031-2025 / UN 38.3),
4. **przegląd patentów** (freedom-to-operate) — przestrzeń Si-C + żel/stałe
   elektrolity jest gęsto opatentowana (CATL, WeLion, StoreDot, QuantumScape),
5. dopiero potem: rozmowy z producentami ogniw / dostawcami materiałów / OEM,
   a finansowanie: NCBR, PARP, EIC Accelerator, Horizon Europe.

Uczciwe sformułowanie przewagi: **nie** „mamy 500 Wh/kg" (rekordy CATL/Amprius
są wyżej), tylko „**łączy naraz** energię ≥ Li-ion + ≥500 cykli @2C + przeżycie
abuse + koszt materiałowy na poziomie LFP/Na-jon" — oraz **otwarte narzędzie**,
którym można to pokazać i zweryfikować.

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
  src/benchmark.rs      # nasi kandydaci kontra ogniwa komercyjne
  src/doc.rs            # generator raportu Markdown (PL/EN)
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
