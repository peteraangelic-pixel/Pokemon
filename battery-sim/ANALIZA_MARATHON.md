# Maraton, nowe materiały i starzenie kalendarzowe

Trzy rozszerzenia modelu i symulacji (stan na 2026-10):

1. **Dłuższe horyzonty** — sweep do **20 000 cykli** (`marathon.csv`, 312 kombinacji z nowymi materiałami).
2. **Nowe materiały** — katoda **LMFP** (LiMnFePO₄) i anoda **SIO** (tlenek krzemu SiO).
3. **Starzenie kalendarzowe (shelf life)** — nowa komenda `storage`: ogniwo stoi przy SOC i temperaturze.

## 1. Maraton (20 000 cykli przy 2C/3C)

**Nikt nie dotarł do 10 000 cykli przy szybkim ładowaniu** — uczciwy wniosek: 2C/3C skraca życie radykalnie. Najdłużej żyją:

| kombinacja | Wh/kg | cykle (EOL) |
|---|---|---|
| **LMFP/LTO/SOLID** | 96.9 | **7659** (fade80 @3C) |
| LFP/LTO/IONIC | 83.0 | 3339 |
| NCA/LTO/SOLID | 108.5 | 3023 |
| LMFP/GRAPHITE/SOLID | 199.5 | 2939 @2C |
| NMC811/GRAPHITE/SOLID | 236.9 | 795 @2C |

**13 kombinacji zalicza PASS (≥500 cykli + energia + bezpieczeństwo)** przy horyzoncie 20k — w tym nowa perełka:

- **LMFP/LIFREE/LP57: 253.7 Wh/kg (182.7 pakiet), 524 cykle @2C, $27/kWh, PASS** — energia jak NMC, koszt jak LFP, bezpieczeństwo klasy LFP (t_stable 400 °C). LMFP/LIFREE/GEL: $34/kWh, 531 cykli.
- NMC811/SIC (631–730 cykli) i NCA/SIC (640–735) — potwierdzenie wcześniejszych zwycięzców.

## 2. Nowe materiały — werdykt

| materiał | wynik w modelu | werdykt |
|---|---|---|
| **LMFP** (katoda, ~3,9 V) | 253.7 Wh/kg z LIFREE (PASS, $27/kWh); 7659 cykli z LTO; ~200 Wh/kg z grafitem | ✅ **świetny** — "LFP z energią NMC", kierunek komercyjny 2025–26 |
| **SIO** (anoda, SiO) | NMC811/SIO → 265.3 Wh/kg ale tylko 313–350 cykli @2C; LIO2/SIO → 358 Wh/kg (rekord energii) | ⚠️ energia tak, życie krótkie (dead Li + SEI) — uczciwie: gorszy od Si-C w tym modelu |

## 3. Starzenie kalendarzowe (shelf life) — `storage`

Pytanie było: *czy warto liczyć, jak bateria leży na półce?* **Tak — to często dominujący tryb starzenia** (EV stoi 95% czasu, magazyny miesiącami, telefony na 100%). Model osobny: SEI ~√t (najszybciej przy 100% SOC), utlenianie elektrolitu przy wysokim potencjale katody, samo-rozładowanie. Kalibracja: NMC/grafit 25 °C/100% SOC → ~3%/rok (shelf life ~8 lat), 45 °C → ~3× szybciej; LFP/LTO praktycznie nie starzeje się na półce.

Tabela kandydatów (pełna w sekcji 8 raportu; komenda `storage --all`):

| kandydat | shelf 25 °C/50% SOC | shelf 45 °C/100% SOC | retencja 10 lat @45 °C/100% |
|---|---|---|---|
| NMC811/LIFREE/GEL (load 35) | 16.5 lat | 3.5 lat | 39% |
| NMC811/SIC/GEL (load 30) | 17.0 lat | 3.5 lat | 39% |
| NMC811/LIFREE/SOLID (load 30) | 17.5 lat | 3.5 lat | 39% |
| **LFP/LIFREE/LP57** (load 35) | **>20 lat** | **15.0 lat** | 85% |
| **LFP/GRAPHITE/LP57** (klasa Blade) | **>20 lat** | **17.5 lat** | 88% |
| DRX/SIC/GEL (load 35) | 7.0 lat | 1.5 lat | 0% |
| NA_PW/HC/LP57 (Na-jon) | 7.0 lat | 4.0 lat | 52% |
| **NA_NFPP/HC/SOLID** (NASICON) | **>20 lat** | **>20 lat** | 90% |
| LIO2/LIMETAL/IONIC (Li-air) | 0.5 lat | 0.5 lat | 0% |
| KPB/GRAPHITE/LP57 (K-jon) | 11.5 lat | 7.0 lat | 70% |

**Wnioski:**
- NMC starzeje się ~3× szybciej przy 45 °C/100% SOC niż przy 25 °C/50% — **SOC i temperatura przy przechowywaniu to dźwignie gwarancji**.
- **LFP i NASICON (NA_NFPP) to mistrzowie półki** (>15–20 lat) — idealne na magazyny i floty.
- **DRX przy pełnym naładowaniu starzeje się najszybciej spośród naszych kandydatów** (wysokie napięcie katody 4,5 V) — przechowywać przy ~50% SOC.
- **Li-air umiera na półce w miesiące** — kolejny powód, dla którego nie ma go na rynku.
- Praktyka: EV/magazyny warto trzymać przy 30–60% SOC i unikać długiego postoju w upale — model to teraz liczy (`storage --soc 0.5 --temp 45`).

## Co to zmienia w projekcie

- **LMFP/LIFREE/LP57** (253.7 Wh/kg, $27/kWh, PASS) dołącza do głównych kandydatów — i to **produkowalne dziś** (LMFP to modyfikacja linii LFP; kierunek CATL/innych 2025–26).
- **Shelf life** wchodzi do raportu (sekcja 8) i one-pagera (punkt 5) — inwestorzy o to pytają ("a jak to wygląda po 5 latach na magazynie?").
- **Maraton** potwierdza: przy 2C nikt nie robi 10k cykli; długowieczność (LTO/NASICON) to osobna liga — gra o cykle kontra gra o energię.
