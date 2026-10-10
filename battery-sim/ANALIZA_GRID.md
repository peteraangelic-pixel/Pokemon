# Analiza wielkiego sweepu — `grid.csv` (14 640 kombinacji)

Źródło: `grid.csv` (commit `86ddc65`, wygenerowane na PC — siatka:
61 zgodnych par katoda/anoda × 4 elektrolity × 5 loadingów × 4 N/P × 3 temperatury).
**PASS** = wszystkie trzy kryteria naraz: energia ≥ 236.9 Wh/kg (baseline Li-ion)
**i** ≥ 500 cykli przy 2C/3C **i** brak eksplozji/runaway/zwarcia (cyklowanie + abuse 150 °C).

## Wynik w jednej liczbie

**321 / 14 640 = PASS (2,2%)**. Kryteria osobno: energia 40%, cykle 27%,
bezpieczeństwo 83% — **żywotność przy szybkim ładowaniu to wąskie gardło**,
potem energia; bezpieczeństwo jest najłatwiejsze (przy stabilnej anodzie i/lub
elektrolicie niepalnym/żelowym).

## Trzy zwycięskie architektury (to zmienia obraz projektu)

| # | Architektura | Wh/kg (pakiet) | Wh/L | cykle @2C/3C | koszt | uwagi |
|---|---|---|---|---|---|---|
| 1 | **NMC811 + anode-free (LIFREE) + SOLID**, load 30, 25 °C | **348 (251)** | 1514 | 512 @2C | $89/kWh | najwyższa energia wśród PASS; wariant IONIC droższy ($139/kWh) |
| 2 | **LFP + anode-free (LIFREE) + LP57**, load 30, 25 °C | **262 (188)** | ~700 | 512 @2C | **$27/kWh** | najtańszy PASS z energią powyżej baseline; z SOLID — **jedyna rodzina przechodząca też 45 °C** |
| 3 | **DRX + Si-C + GEL**, load 30, **0 °C** | **344 (248)** | 1197 | 516 @3C | **$41/kWh** | nowatorska, bez kobaltu/niklu; 22 kombinacje PASS (prawie wszystkie przy 0 °C) |

## TOP 15 PASS wg score

| kombinacja | load | N/P | T °C | Wh/kg (pakiet) | Wh/L | $/kWh | cykle | score |
|---|---|---|---|---|---|---|---|---|
| DRX/SIC/IONIC | 30 | 1.05 | 0 | 343.7 (247.5) | 1197 | 132 | 580 @3C | 0.90 |
| DRX/SIC/IONIC | 30 | 1.10 | 0 | 340.5 (245.2) | 1175 | 133 | 589 @3C | 0.90 |
| NMC811/LIFREE/IONIC | 30 | 1.05 | 0 | 348.1 (250.6) | 1514 | 139 | 517 @2C | 0.89 |
| NMC811/LIFREE/IONIC | 30 | 1.10 | 0 | 347.9 (250.5) | 1511 | 139 | 518 @2C | 0.89 |
| NMC811/LIFREE/IONIC | 30 | 1.20 | 0 | 347.7 (250.3) | 1506 | 139 | 518 @2C | 0.89 |
| NMC811/LIFREE/IONIC | 30 | 1.30 | 0 | 347.4 (250.1) | 1501 | 140 | 519 @2C | 0.89 |
| NMC811/LIFREE/SOLID | 30 | 1.05 | 25 | 348.1 (250.6) | 1514 | 89 | 512 @2C | 0.89 |
| NMC811/LIFREE/SOLID | 30 | 1.10 | 25 | 347.9 (250.5) | 1511 | 89 | 512 @2C | 0.89 |
| NMC811/LIFREE/SOLID | 30 | 1.20 | 25 | 347.7 (250.3) | 1506 | 90 | 513 @2C | 0.89 |
| NMC811/LIFREE/SOLID | 30 | 1.30 | 25 | 347.4 (250.1) | 1501 | 90 | 513 @2C | 0.89 |
| DRX/SIC/IONIC | 30 | 1.20 | 0 | 334.5 (240.8) | 1135 | 135 | 607 @3C | 0.89 |
| DRX/SIC/GEL | 30 | 1.05 | 0 | 343.7 (247.5) | 1197 | 41 | 516 @3C | 0.89 |
| NMC811/SIC/LP57 | 30 | 1.05 | 0 | 281.3 (202.5) | 1011 | 58 | 753 @2C | 0.88 |
| DRX/SIC/GEL | 30 | 1.10 | 0 | 340.5 (245.2) | 1175 | 42 | 521 @3C | 0.88 |
| NMC811/SIC/LP57 | 30 | 1.10 | 0 | 278.8 (200.7) | 994 | 59 | 755 @2C | 0.88 |

## Temperatura — najważniejsza oś w całej siatce

- **0 °C: 161 PASS** (średnio 428 cykli) — zimno spowalnia degradację (Arrhenius),
  odblokowuje DRX i wydłuża życie; model łapie też ryzyko (rate-limiting/plating).
- **25 °C: 152 PASS** (średnio 518 cykli) — punkt odniesienia.
- **45 °C: tylko 8 PASS** (średnio 390 cykli) — upał zabija żywotność;
  **jedyny ocalały: LFP/LIFREE/SOLID** (519–521 cykli) — LFP + stały elektrolit
  to najbardziej „upałoodporna” kombinacja w całej siatce.

## Nowe chemie — werdykt po 14 tys. kombinacji

| chemia | PASS | rekordy | werdykt |
|---|---|---|---|
| **DRX** (rock-salt) | **22** | 430 Wh/kg, do 633 cykli, $41–136/kWh | ✅ **viable** — najlepsze: DRX/Si-C/GEL @0 °C (344 Wh/kg, 516 cykli, $41/kWh) |
| LIO2 (Li-air) | 0 | 502 Wh/kg, ale ≤ 55 cykli | ❌ potwierdzone: nie na rynek |
| KPB (K-jon) | 0 | do 1881 cykli, ale ≤ 161 Wh/kg | ⚠️ świetne cykle, za mało energii na kryterium „≥ Li-ion” |
| NA_* (Na-jon) | 0 | NA_NFPP do 3000 cykli (limit), ≤ 178 Wh/kg | ⚠️ jw. — cykle/koszt świetne, Wh/kg za mało |
| CHEVREL/MG (Mg-jon) | 0 | 40 Wh/kg | ❌ niskie napięcie ogniwa |
| FEF3 (konwersyjna) | 0 | 209 Wh/kg, ≤ 119 cykli | ❌ kinetyka konwersji |

## Inne obserwacje

- **Anode-free (LIFREE)**: 94 PASS (średnio 280 Wh/kg) vs 227 PASS bez niego
  (263 Wh/kg) — anode-free wymienia część żywotności na energię; opłaca się
  szczególnie z NMC811 i LFP.
- **N/P (1.05–1.3)**: prawie bez wpływu na średnie cykle (649–665) — nie warto tym stroić.
- **Score ≠ werdykt**: LIO2 ma najwyższy score w całej siatce (1.11) i 0 PASS —
  score nagradza energię; zawsze patrzeć na kolumnę `passed`.
- **C-rate**: najlepsze wyniki padają zwykle na C=2 (szybsze ładowanie = szybsza degradacja).

## Co dalej (prosto z tych danych)

1. **Główni kandydaci do raportu/benchmarku**: NMC811/LIFREE/SOLID (energia),
   LFP/LIFREE/LP57 (koszt) i DRX/SIC/GEL @0 °C (nowatorska) — można dodać je
   do tabel kandydatów (`benchmark`, `report`, `pitch`).
2. **Kierunek „na gorąco”**: LFP/LIFREE/SOLID jako jedyne przechodzi 45 °C —
   kandydat na klimat tropikalny / magazyny bez aktywnego chłodzenia.
3. **Kierunek „na zimno”**: DRX i anode-free żyją najdłużej w 0 °C — zimny klimat
   (Polska, Skandynawia) sprzyja żywotności; BMS powinien grzać tylko tyle, żeby
   bezpiecznie ładować, nie przegrzewać.
