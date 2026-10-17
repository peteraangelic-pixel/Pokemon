# NOTES_STRATEGY — droga do 1000+ (update 2026-10-17 15:00 po weryfikacji v83/v84/v85)

## Obecny stan (2026-10-17 15:00)
- Live 57290311 v63_super_fix_a450: 30W-50L=0.375, vs KYOGRE 11W-19L=0.37 (mirror słaby), rating 399.7 po szczycie 773.7 — potwierdza że mirror to klucz.
- Weryfikacja drugiej gałęzi: v83 z poprawnym deckiem Kyogre (c87_v44.csv) vs base 600g: 285W-315L=0.475 WR, nie 0.125 — ich 0.125 wynikał z buga deck.csv (Alakazam w bundle Kyogre). Po fixie v83 nie jest katastrofą, ale słabszy od championa (avg prizes 1.96 vs 2.94).
- A/B 2 idei na championie 600g: v84a retreat only 299W-301L=0.498, v84b energy bench Snover 288W-312L=0.480, v84 both 293W-307L=0.488, base mirror 297W-303L=0.495 — retreat idea neutralna, energy idea lekko gorsza. vs new_losses 20g: v84a 0.800 vs base 0.796 — tie, ale vs jazivxt mirror 3-17=0.15 vs base 9-11=0.45 — retreat szkodzi w mirrorze.
- Nowy trop: imitacja z słabszego nauczyciela szkodzi (second branch: PG z v70 słabszy). Testy:
  - v85 no imit mirror (c87_v44 + wyłącz imitację tylko w MIRROR mode): 1200g vs base 631W-569L=0.526 WR (vs base mirror 609W-591L=0.507) +1.9pp, new_losses 40g 0.802 vs base 0.796 +0.6pp, top30 40g 0.908 vs 0.928 -2.0pp — **najlepszy mirror fix**
  - v86 no imit at all: 1200g 607W-593L=0.506 vs base 0.507 tie, new_losses 0.796 tie
  - v86b imit20: 0.488 vs base gorszy
- Wniosek: v85 to pierwszy wariant który bije championa c87_v44 w mirrorze 1200g (0.526) i poprawia new_losses (0.802), kosztem -2pp top30. To jest kierunek per second branch: nie bench guard, tylko tempo i usunięcie słabego nauczyciela.

## Obecny stan (2026-10-17 12:00) [archiwum]
- Live v63: 33W-50L (83 gry) rating 399.7 po szczytach 773.7/611.8; v70g: 39W-33L (72 gry) rating 354.2 po dołku 220.5. Obie zbiegają do ~400. Różnica winrate 0.54 vs 0.40 zawyżona ścieżką ratingu.
- Najlepsze lokalne: v74 0.665 new_losses / 0.650 top30 (v80 bundle), v83 Kyogre tempo 0.681 new_losses / 0.552 top30, v83 Alakazam fix 0.635 / 0.635.
- v78 odrzucony: 59 kart -> BattleStart null -> 392 drawy/540 (0.111) - silnik odrzuca nielegalną listę, harness liczył jako drawy.

## Kluczowa korekta drugiej gałęzi (2026-10-17)

**Sprawdzone — liczby się zgadzają, ale wniosek prostujemy:**

- Ich WIPE 52.6% to opis końca gry, nie przyczyny. Moja klasyfikacja nagrodowa: v63 52% porażek nie wzięliśmy ani jednej nagrody, w mirrorze przegrany bierze śr. 1.0 nagrody. Większość gier kończy się wipe'em, bo już dawno przegrywaliśmy wyścig — ławka pustoszeje na końcu głodowej gry, a nie odwrotnie.
- Najmocniejszy dowód: żadna wersja z dyscypliną ławki nie bije bazowej (v74 0.614 vs v70 0.618 new_losses różnica w szumie; v76/v77 wprost gorsze). Dokładnie to samo u nich z v64-guardem. Gdyby przyczyną była dyscyplina ławki, guard musiałby pomagać. Nie pomaga, bo wąskim gardłem jest tempo stawiania Abomasnowa i przeżywalność Snoverów.
- Bug promocji Alakazam: Kadabra 80 HP promowana przed Dudunsparce 140 HP poza warunkiem końcówki — realny, tani mikro-fix.

**Odpowiedź na pytanie końcowe drugiej gałęzi:**
- Ani v80b, ani PG z nauczycielem v70. v80b to ściana + guardy już przetestowane bez zysku. PG z v70 to uczenie od słabszego nauczyciela (v70 lokalnie pod hybrydą: siatka 0.591 vs 0.611), w dodatku łańcuchem Rust, o którym wiemy że bramki nie przenoszą się na agenta Kaggle. Jeśli PG, to z hybrydy v65 i w spójnym loopie pythonowym.
- Rekomendacja "nie wysyłaj teraz" słuszna — popieram. Następny ruch to pilot pod mirror Abomasnowa i głód nagród, bo tam jest 15 z 44 porażek ściany.

## Wyniki testów na nowych przegranych (13 decków z live losses)

### Gauntlet 20g (gauntlet_ffi, 2 workers)
- v79 Kyogre resistant: new_losses 0.581 ±0.060, top30 0.583 ±0.042, pool_v3 0.263
- v82 mirror resistant: new_losses 0.558 ±0.060, top30 0.631 ±0.041
- **v83 Kyogre mirror tempo (nowy)**: new_losses **0.681 ±0.057** (best!), top30 0.552 ±0.042, pool_v3 0.362
  - mirror prizetest 100g: 58W-42L=0.580, **zero-prize losses 0/42=0.00%** (target <30%), avg prizes in losses 1.64, dist {1:30,2:6,3:3,6:3}
  - vs v82: 50W-50L=0.500, zero-prize 6% (3/50), avg 3.60 — v83 lepszy na zero-prize
- v83 Alakazam fix Dudunsparce>Kadabra: new_losses 0.635 ±0.059, top30 0.635 ±0.041
- v74 baseline: new_losses 0.665 ±0.057, top30 ~0.650 (z v80 bundle)

### Prizetest — metryka głodu nagród (mirror same deck)
- v63 baseline c87_v44: 46W-54L=0.460, zero-prize 1/54=1.85% lokalnie vs 52% live — rozbieżność, lokalny mirror nie reprodukuje live 1:1, drugi branch miał 56% zero avg 1.17 co pasuje do live
- v82: 10.42% zero (poprawa vs live 52% ale gorszy niż lokalny baseline)
- **v83 tempo: 0.00% zero — spełnia cel <30% i rozwiązuje głód nagród**

## Odporne wersje zbudowane (2026-10-17)

- `v80_resistant_650top30_614newloss.tar.gz` 77.1 KiB v74 + v66 deck — best balanced 0.650/0.614
- `v81_kyogre_resistant_benchguard.tar.gz` 76.2 KiB v79 + c87_v44 — bench guard (odrzucony, nie pomaga)
- `v82_kyogre_mirror_resistant_fa4fe68.tar.gz` 77.2 KiB v82 — mirror resistant per fa4fe68 (protect Snover, early Kyogre snipe Boss gust, Mega Signal boost)
- `v83_kyogre_mirror_tempo_per_second_branch_correction.tar.gz` 78.5 KiB **v83 — tempo pilot per correction**: early Snover T1-3 z Water, energy priority bench Snover 0E > active Kyogre 1E+, Mega Signal boost gdy Snover board no Aboma hand, retreat Snover vs Aboma, Hammer-lanche real damage estimate, avoid self-mill deckCount<=7, Boss snipe benched Snover 130, promotion Aboma ready 150 > Kyogre 110 > Aboma not ready 100 > Snover 50 (Snover -50 jeśli opp Aboma może KO)
- `v83_alakazam_fix_dudunsparce_gt_kadabra.tar.gz` 76.7 KiB — fix promocji: DUDUNSPARCE 70 > KADABRA 60 (było 55 vs 60)

## Decyzja submit per reguła 02:20

> "dopiero jak przetestujesz na nowych przegranych meczach za 3h i okaże się że twoja nowa wersja super radzi sobie z tymi przegranymi.. szkoda slotu!"

Kryteria: >0.63 new_losses AND >0.65 top30 AND zero-prize <30%

- v83 tempo: 0.681 ✅ / 0.552 ❌ / 0.00% ✅ — spełnia new_losses i zero-prize, nie top30
- v74/v80: 0.665 ✅ / 0.650 ✅ / — borderline, ale najbliżej spełnienia obu
- v83 Alakazam fix: 0.635 ✅ / 0.635 ❌

**Nie wysyłamy teraz** — zgodnie z drugą gałęzią. Najlepszy balanced to v80 (v74), najlepszy mirror-resistant to v83 tempo (0% zero-prize, 0.681 new_losses). Następny krok: v84 hybryda oparta na c87_v44 full heuristic (2700 linii, ma wall/fast/mirror adaptacje) + tempo patche z v83, by odzyskać top30 >0.65 przy zachowaniu 0.68 new_losses.

## Plan dla 1000+ (zrewidowany po korekcie)

### Faza A — mirror tempo (zrobione v83)
- [x] Pilot pod mirror Abomasnowa i głód nagród — 15 z 44 porażek ściany
- [x] v83 tempo: 0.681 new_losses, 0% zero-prize vs 52% live — sukces na metryce głodu, ale bundle miał bug deck.csv Alakazam
- [x] v83 fixed deck: vs base 600g 0.475 WR (nie 0.125), avg prizes 1.96 vs 2.94 — słabszy od championa, bug decku naprawiony
- [x] v84 A/B: retreat only 0.498, energy bench 0.480, both 0.488 vs base 0.495 — brak zysku, retreat szkodzi vs jazivxt mirror 0.15 vs 0.45
- [x] v85 no imit mirror: c87_v44 + wyłącz imitację w MIRROR — 1200g 0.526 WR vs base 0.507 (+1.9pp), new_losses 40g 0.802 vs 0.796 (+0.6pp), top30 40g 0.908 vs 0.928 (-2.0pp) — **best mirror fix, rekomendowany do submitu**
- [x] v86 no imit all: 1200g 0.506 vs 0.507 tie

### Faza B — walidacja 4800g (zrobione 40g)
- Grupy: trolley, Crustle wall, Mengfei Kangaskhan, top30_live split top10/reszta, live_killers 18 decków, new_losses 13 decków
- Każda grupa 600 gier, łącznie ~4800, raport winrate per grupa, worst5, zero-prize % w mirror
- Używać multiprocessing.Pool + gauntlet_ffi — 84k próbek 128s, Rust+Rayon w Actions dla >20g/s

### Faza C — PG tylko z hybrydy v65, nie v70
- Jeśli PG, to z hybrydy v65 (0.611 grid) i w spójnym loopie pythonowym, nie Rust chain (bramki nie przenoszą się)
- BC seed z v65, nie v70 (v70 słabszy lokalnie)

### Faza D — submit hygiene
- Distinct nazwy bundle dla różnej zawartości — 5 slotów może mieć różne nazwy
- DISARM auto-submit — tylko ręczny workflow_dispatch za zgodą
- Tylko 2 ostatnie suby aktywne — nie zapychać slotów
