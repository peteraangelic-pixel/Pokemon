# Finalne portfolio — 6 kandydatów (2026-10)

**Jedyna, kanoniczna lista** baterii, którymi jesteśmy zadowoleni i które idą
do prezentacji. Wszystkie inne nazwy w projekcie (LIO2, KPB, CHEVREL/MG, FEF3,
SIO, LFP/GRAPHITE/LP57, NA_NFPP) to **referencje albo odrzucone eksperymenty** —
patrz ostatnia sekcja.

Kryteria wewnętrzne (chyba że zaznaczono): energia ≥ 236.9 Wh/kg (baseline
Li-ion), ≥ 500 cykli @2C, brak eksplozji / runaway / zwarcia (cyklowanie + abuse 150 °C).

## Nasze baterie vs najlepsze na rynku

| # | Nasza bateria | Energia (pakiet) | Cykle @2C | Koszt | Bezpieczeństwo / specyfika | Najbliższe na rynku — i czym je bijemy | Kiedy |
|---|---|---|---|---|---|---|---|
| 1 | **NMC811 + Si-C + GEL** (flagship) | 279 Wh/kg (201) | 670 | $67/kWh | abuse 170 °C; moc 5C (klasa żel+Si-C) | CATL Qilin 255 pak; WeLion 260 pak (półstałe, drogie) — **bijemy: energia + koszt + abuse** | 1–2 lata (istniejące linie) |
| 2 | **NMC811 + anode-free + GEL/LP57** (premium) | 359–367 (258–264) | 512–543 | $43–50/kWh | abuse 150–170 °C; moc 5C | WeLion 360 ogniwo (półstałe, Li-metal); Amprius 500 (lotnictwo, nisza) — **bijemy: podobna energia, niższy koszt** | 2027+ (anode-free) |
| 3 | **LMFP/LFP + anode-free + LP57** (masowy) | 270–298 (195–214) | 512–824 | **$27/kWh** | klasa bezpieczeństwa LFP; LMFP: żyje w 60 °C | BYD Blade 160 (LFP); CATL Naxtra 175 — **bijemy: 1,7–1,9× energii przy tej samej klasie bezpieczeństwa** | 2–3 lata (linie LFP + anode-free) |
| 4 | **DRX + Si-C + GEL** (nowatorski) | 354–361 (255–260) | 590–641 | $41/kWh | abuse 150 °C; moc 5C; **bez Co/Ni** | brak odpowiednika; najbliżej NMC wysokoniklowe — **bijemy: bez kobaltu/niklu, koszt** | 2027+ (katoda DRX = pilot) |
| 5 | **LFP + anode-free + SOLID** (specjalista) | 250–262 (~180–188) | 519–521 @45 °C | $78–89/kWh | **jedyny żyje w 60 °C**; shelf >20 lat | BYD Blade (LFP) i wszystko inne — **bijemy: odporność na 60 °C + życie na półce** | 2027+ (solid) |
| 6 | **Na-jon: Na-PW + hard carbon + LP57** (wejściowy) | 176 (127) | 259 | $39/kWh | −40 °C; bezpieczny | CATL Naxtra 175 (produkcja od końca 2025) — **nie bijemy parametrami; sprzedajemy narzędzie + optymalizację** | **dziś** (drop-in) |

## Testowane i odrzucone / tylko referencje (NIE w portfolio)

| nazwa | wynik w modelu | werdykt |
|---|---|---|
| LIO2 (Li-air) | ~400–500 Wh/kg, ~21–55 cykli | ❌ ginie (reakcje pasożytnicze) — dlatego nie ma jej na rynku |
| KPB (K-jon) | ~160 Wh/kg, do 1881 cykli | ⚠️ za mało energii na kryterium „≥ Li-ion” |
| CHEVREL/MG (Mg-jon) | ~40 Wh/kg | ❌ niskie napięcie ogniwa |
| FEF3 (konwersyjna) | ~209 Wh/kg, rate-limited @2C | ❌ kinetyka konwersji |
| SIO (anoda SiO) | do 391 Wh/kg (z DRX), ≤585 cykli | ⚠️ energia tak, życie krótkie |
| LFP + grafit + LP57 (Blade-class) | 184 Wh/kg, 1465 cykli @2C, abuse FAIL (cell-level) | 📎 referencja rynku (BYD Blade) |
| NA_NFPP/HC/SOLID | 150 Wh/kg, 961 cykli, shelf >20 lat | 📎 referencja shelf-life (za mało energii na kryterium) |

## Dlaczego w różnych miejscach różne liczby?

- **Ten dokument (6)** = kanoniczne portfolio produktowe (5 naszych baterii + Na-jon jako produkt wejściowy).
- **Pitch (5–6)** = to samo portfolio w wersji produktowej (lider + warianty + wejście Na-jon).
- **Benchmark / raport (10 wierszy)** = 6 kandydatów + 4 referencje/kontrast (Blade-class, LIO2, KPB, NA_NFPP).
- **„3 zwycięskie architektury” (ANALIZA_GRID / ANALIZA_OPTIM)** = pierwsza trójka z siatki 14k — sprzed dodaniem LMFP/SIO i przed ułożeniem portfolio.
- **Mega / maraton** = wspominają też eksperymenty (LMFP, SIO) jako dane, nie jako produkty.
