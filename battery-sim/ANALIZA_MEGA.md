# Mega-siatka — `mega.csv` (99 840 kombinacji) + wyniki z PC użytkownika

Pliki od użytkownika (commit `479b02a`, wyniki z jego PC — Ryzen 5950X):
`mega.csv` (99 840 kombinacji) i `marathon.csv` (zrzut konsoli: blok `storage`
+ blok `ladder` + CSV sweepu 312 wierszy — stąd „2 ekstra wyniki na początku”:
to wynik `storage` i wyniki `ladder`, dołożone przed CSV maratonu).

**Ważne — determinizm potwierdzony:** drabiny z `marathon.csv` (blok ladder)
są **identyczne co do cyfry** z moimi wynikami z tej samej wersji modelu
(top 12 PASS, podsumowanie 2C / 170 °C / 5C) — model daje te same wyniki
na każdej maszynie. To najsilniejsza walidacja, jaką mamy: niezależna
instalacja, ten sam wynik.

## Mega — konfiguracja

78 par katoda/anoda × 4 elektrolity × 8 loadingów (5–40) × 5 N/P (1.02–1.3)
× 8 temperatur (−20…60 °C) = **99 840 kombinacji**, C-rate'y kryterium {1,2,3,4,6}.

## Wynik — i uczciwa korekta o C-rate

**PASS: 5 788 (5,8%)** — ale uwaga: kryterium cykli w mega to „najlepsze C ze
zbioru {1,2,3,4,6}”, więc rozkład zwycięskiego C wśród PASS:
**c_best=1: 4 410 | c_best=2: 1 253 | c_best=3: 125**.
Czyli twarde „≥500 cykli przy 2C” = **1 253 kombinacje**, a przy 3C — 125.
Do „1C też się liczy” służy ten sweep; do twardego „szybkie ładowanie ≥2C”
służą maraton i `ladder` (tam fast_rates = {2,3}).

## Nowi/aktualizowani zwycięzcy (load 40 odblokowuje kolejne ~6–9 Wh/kg)

| tytuł | konfiguracja | Wh/kg (pakiet) | $/kWh | cykle | uwagi |
|---|---|---|---|---|---|
| **Energia (rekord)** | **NMC811/LIFREE/LP57, L=40, −20 °C** | **367.1 (264)** | $43 | 629 (best@1C) | najwyższa energia wśród PASS; przy 2C też ≥500 (patrz maraton) |
| **Energia + szybkie 2C** | **DRX/SIC/GEL, L=40, −10 °C** | **361.0 (260)** | $41 | 641 @2C (best@2C) | bez Co/Ni; najwyższa energia wśród „best@2C” |
| **Koszt (rekord)** | **LMFP/LIFREE/LP57, L=40, −20 °C** | **298.0 (214)** | **$27** | 824 (best@1C) | LMFP skaluje się z loadingiem; patrz też maraton (253.7 przy L=20) |
| **Trwałość (rekord)** | NMC811/GRAPHITE/SOLID, L=25, 10 °C | 242.0 | $99 | **1681 @1C** | najdłużej żyjące PASS w mega |

## Mapa temperatur (PASS ogółem | best@2C | best@3C+)

| T | PASS | best@2C | best@3C+ | wniosek |
|---|---|---|---|---|
| −20 °C | 769 | 163 | 38 | zimno OK — DRX/SIC i LCO dominują |
| −10 °C | 923 | 220 | 33 | |
| 0 °C | 976 | 245 | 29 | |
| **10 °C** | **1037** | **263** | 25 | **sweet spot** (zimno hamuje degradację, ciepło trzyma kinetykę) |
| 25 °C | 833 | 252 | 0 | |
| 35 °C | 639 | 109 | 0 | |
| 45 °C | 500 | **1** | 0 | tylko LFP/LIFREE/SOLID |
| 60 °C | 111 | **0** | 0 | **żadne ogniwo nie robi ≥500 cykli przy ≥2C w 60 °C**; przeżywają tylko LFP/LIFREE i **LMFP** (LIFREE/SIC) |

## LMFP i SIO w mega

- **LMFP: 1 064 PASS** (najwięcej ze wszystkich katod!), max 298.0 Wh/kg (L=40),
  i — jak LFP — **przechodzi 60 °C** (t_stable 400 °C). LMFP to najbezpieczniejsza
  „wysokoenergetyczna” katoda w modelu.
- **SIO: 232 PASS**, max 390.8 Wh/kg (DRX/SIO/GEL L=40 — rekord energii w ogóle),
  ale max 585 cykli — uczciwie: energia tak, życie krótkie.

## Poprawki w programie (z tej inspekcji plików użytkownika)

- `storage` (pojedynczy wynik) drukuje teraz **nazwę ogniwa** (wcześniej w wyniku
  nie było widać, która to bateria — widać to było w `marathon.csv`).
- Krzywa retencji drukuje lata z 2 miejscami po przecinku (wcześniej ostatni
  wiersz wyświetlał się dwa razy jako „rok 10.0” — artefakt zaokrąglenia).

## Uwaga o rozmiarach w repo

`mega.csv` = **12,9 MB**, `grid.csv` = 1,9 MB — oba weszły przez upload WWW
(omija `.gitignore`). To jeszcze OK jako artefakt „wyniki referencyjne”, ale
kolejne duże siatki lepiej trzymać poza gitem (CI artifacts / Releases) albo
odciąć od śledzenia: `git rm --cached battery-sim/mega.csv`.
