# battery-sim

Symulator projektowania nowych typów baterii — wybierasz **katodę / elektrolit / anodę** (3 komponenty), a symulator liczy energię, żywotność przy szybkim ładowaniu i odporność na ekstremalne warunki (abuse).

**Kryteria „nowej baterii”:**

- ⚡ energia **≥ Li-ion** (baseline: 236.9 Wh/kg dla NMC811/grafit/LP57)
- 🔁 **≥ 500 cykli** przy szybkim ładowaniu (2C–3C)
- 🧯 **nie eksploduje** — test: piec 150 °C + overcharge 1C przez 3 h

## Szybki start

```sh
cd battery-sim
cargo run --release -- demo          # baseline Li-ion + scenariusze + testy abuse
cargo run --release -- sweep --quick # mini-sweep 36 kombinacji
cargo run --release -- list          # katalog materiałów (11 katod, 5 anod, 4 elektrolity)
cargo run --release -- benchmark     # nasi kandydaci kontra ogniwa komercyjne
cargo run --release -- report --lang en --out report.md   # raport po angielsku
cargo run --release -- sweep --csv wyniki.csv
```

Duża siatka na wielordzeniowym CPU (np. 16 rdzeni → 13200 kombinacji w minuty):

```sh
cargo run --release -- sweep \
  --loadings 10,15,20,25,30 --nps 1.05,1.1,1.2,1.3 --temps 0,25,45 \
  --c-rates 2,3 --csv grid.csv
```

## Najlepszy kandydat (symulacja)

**NMC811 + Si-C (anoda krzemowo-węglowa) + GEL (elektrolit żelowy/półstały), loading 30 mg/cm² → 278.8 Wh/kg ogniwo (200.7 Wh/kg pakiet), 994 Wh/L, ~$67/kWh materiałowo, ~670 cykli @2C — przeżywa test abuse 150 °C** (wszystkie trzy kryteria naraz).

Ekonomiczna alternatywa (Na-jon): **Na-PW + hard carbon + LP57 → 175.7 Wh/kg, ~$39/kWh** — odpowiednik kierunku CATL Naxtra.

Pełna dokumentacja po polsku: [`battery-sim/README.md`](battery-sim/README.md) — modele materiałowe, fizyka (SEI, Li-plating, dead Li, thermal runaway), metryki rynkowe (pakiet, Wh/L, $/kWh), wszystkie komendy CLI, formaty CSV, duże siatki, benchmark kontra rynek.

## CI

`.github/workflows/ci.yml` — `lint` (cargo fmt + clippy, obie konfiguracje), `test` (build + demo + quick sweep + benchmark + raporty PL/EN jako artefakty), `sweep-full` (pełna siatka chemiczna → CSV). Push/PR na `main` + ręczny „Run workflow”.

## Struktura

- `battery-sim/` — crate Rust (równoległość: **rayon** domyślnie; fallback `std::thread` przez `--no-default-features`)
- `battery-sim/tools/model_prototype.py` — prototyp modelu w Pythonie (kalibracja; zgodność z Rust 1:1)
- `.github/workflows/ci.yml` — CI
