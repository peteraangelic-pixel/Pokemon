# Optymalizacja zwycięskich architektur — `optim_winners.csv` (2880 kombinacji) + drabiny

Zadanie: drobna siatka wokół trzech zwycięzców z `ANALIZA_GRID.md`
(NMC811/LFP/DRX × LIFREE/SIC/GRAPHITE × LP57/GEL/IONIC/SOLID × load 20–35
× N/P 1.02–1.2 × T −10…45 °C), potem drabiny testowe (`ladder`) dla top 12 PASS.
Komenda na PC: `bash tools/optimize-winners.sh`.

**PASS: 420 / 2880 (14,6%)** — otoczenie zwycięzców jest gęste od dobrych kombinacji
(dla porównania: w szerokiej siatce 2,2%).

## Udoskonaleni zwycięzcy (optymalne ustawienia)

| rodzina | optymalna konfiguracja | Wh/kg (pakiet) | $/kWh | cykle @2C | abuse max | moc (25 °C) |
|---|---|---|---|---|---|---|
| **Energia** | NMC811 + anode-free + **GEL**, load 35, −10…0 °C | **358.7 (258)** | **$50** | 543 | 170 °C | 5C |
| **Energia (25 °C ref.)** | NMC811 + anode-free + **SOLID**, load 30, 25 °C | 348.1 (251) | $89 | 512 | 170 °C | — |
| **Koszt** | LFP + anode-free + **LP57**, load 35, 10–25 °C | **270.2 (195)** | **$27** | 534 | ~150 °C | — |
| **Nowatorska** | DRX + Si-C + **GEL**, load 35, −10 °C | **354.3 (255)** | **$41** | 590 | 150 °C | 5C |
| **Nowatorska (cieplej)** | DRX + Si-C + IONIC, load 35, 0 °C | 354.3 (255) | $131 | 605–623 | 150 °C | 3C |

(Wszystkie: energia ≥ 236.9 Wh/kg baseline + ≥500 cykli @2C + przeżycie abuse 150 °C.)

## Co się zmieniło vs szeroka siatka

- **Load 35 > load 30**: energia rośnie (NMC811/LIFREE/GEL: 348→359 Wh/kg; LFP/LIFREE: 262→270),
  koszt bez zmian, cykle podobne (542 vs 512). **Wyższy loading = lepsza energia, bez kary
  w cyklach — ale 3C odpada przy load 35** (rate-limited), więc:
  - load 35 → maksymalna energia, ładowanie 2C,
  - load 30 → wciąż 3C dla DRX (580 cykli @3C).
- **N/P 1.02–1.2 praktycznie bez różnicy** — anode-free dobrze znosi cienką nadwyżkę.
- **Temperatura**: −10…10 °C najlepsze dla żywotności (średnio 649–675 cykli);
  25 °C = 633; **45 °C wciąż tylko 8 PASS** (wyłącznie LFP/LIFREE/SOLID).

## Drabiny (top 12 PASS)

**C-rate (cykle do EOL):** wszystkie topowe konfiguracje mają sufit **2C** przy ≥500 cyklach
(przy load 35; DRX/Si-C przy load 30 robi 3C/580 cykli). 3C/4C/6C przy load 35 → rate-limited.
Uczciwe twierdzenie do raportu: **„≥500 cykli przy 2C”** (3C to bonus dla DRX przy load 30).

**Abuse (piec + overcharge, margines):** NMC811/LIFREE/GEL → **170 °C** (EXPL przy 200 °C);
DRX/SIC/GEL i wszystkie IONIC → 150 °C (SHORT przy 170 °C — topnienie separatora);
SOLID → przeżywa 170 °C **bez eksplozji** (przy 200 °C sam piec = próg runaway 200 °C).
Wniosek: GEL + anode-free = najlepszy margines wśród elektrolitów ciekłych/żelowych.

**Moc (rozładowanie przy 25 °C):** NMC811/LIFREE/GEL i DRX/SIC/GEL → **5C** (deliv 52–59%);
IONIC → 3C (deliv 34–47% przy 5C). Czyli żel + Si-C/anode-free = też dobra moc rozładowania.

**Derating w zimnie (z drabiny, pomiar przy temperaturze konfiguracji):** przy 0…−10 °C
ogniwo ładuje się tylko do ~55% SOC przy 1C i oddaje ~52–56% przy 1C — realistyczny
efekt zimna (jak w EV: BMS musi podgrzać baterię przed szybkim ładowaniem).

## Wnioski praktyczne (co budować pod jaki zastosowanie)

1. **Maksymalna energia (EV premium):** NMC811 + anode-free + GEL, load 35 → 359 Wh/kg
   (258 pakiet), 543 cykle @2C, $50/kWh, abuse 170 °C, moc 5C.
2. **Maksymalny zasięg za pieniądz (EV mass / magazyny):** LFP + anode-free + LP57,
   load 35 → 270 Wh/kg (195 pakiet), 534 cykle @2C, **$27/kWh**.
3. **Bez kobaltu/niklu (novel):** DRX + Si-C + GEL, load 35 → 354 Wh/kg (255 pakiet),
   590 cykle @2C, $41/kWh — najlepsze w zimnym klimacie.
4. **Klimat gorący / brak chłodzenia:** LFP + anode-free + **SOLID** (jedyny przechodzi 45 °C).
5. **Szybkie ładowanie 3C+:** DRX + Si-C przy load 30 (580 cykli @3C) — albo zejść
   z loadingiem; 2C jest bezpiecznym sufitem dla wszystkich.
