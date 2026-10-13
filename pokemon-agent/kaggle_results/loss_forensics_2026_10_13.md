# Loss forensics 2026-10-13 — dlaczego submisje przegrywają ("cieńkie" wyniki)

Źródła: `our_replays/forensics_summary.md` (Rust+Rayon `loss_forensics`, 100 epizodów live z 4 subów),
`our_replays/submissions_list.csv` (świeży μ), dekodowanie raw replayów (np. `replays/episode-123167323-replay.json`),
lokalne A/B (ab_two_decks, 10k+ gier).

## 1. Wyniki Kaggle (stan 10-13 ~09:00 UTC)

| sub | agent + deck | μ live | status |
|---|---|---|---|
| 57130779 | v25 knobs + 35W | **434.6** | COMPLETE |
| 57130754 | v26_strong_weakfix (innej gałęzi) + 35W | **389.1** | COMPLETE |
| 57125516 | v25 knobs + 35W (stary) | 387.5 | COMPLETE |
| 57125561 | v22b + 35W (kontrola) | 328.1 | COMPLETE |

Szum live μ ≈ ±110 na podpróbkę — 434.6 vs 387.5 to ten sam agent w dwóch próbach (spójne).
v22b (328) potwierdza: **knoby v25 + deck 35W to najlepsza znana kombinacja**.

## 2. Wzorce porażek (100 epizodów: 40W/60L)

Klasy (Rust forensics):
- **EARLY_COLLAPSE (turn ≤ 10): 49/60 = 82% wszystkich przegranych**
- DAMAGE_RACE_LOST: 7, KO_RACE_LOST: 2, OTHER: 2

W-L wg suba × archetypu przeciwnika (z forensics_summary.md):

| sub | arch | W-L | W% | uwag |
|---|---|---|---|---|
| 57125516 (v25) | KYOGRE | 8-5 | 62% | mirror — najczęstszy matchup live (~40% gier) |
| 57125516 (v25) | ? (egzotyka) | 7-17 | 29% | **główny zlewnik** |
| 57125561 (v22b) | KYOGRE | 5-12 | 29% | v22b traci mirrora 3-krotnie mocniej niż v25 |
| 57125561 (v22b) | LUCARIO_ALT | 2-5 | 29% | |
| 57130754 (v26fix) | KYOGRE | 0-4 | 0% | mała próba |
| 57130779 (v25 new) | KYOGRE | 3-0 | 100% | mała próba |

"?" = egzotyczne decki słabszych graczy: Raging Bolt ex/Ogerpon ex (240/210 HP),
Marnie's Grimmsnarl ex (320), Mega Kangaskhan ex (300), Mega Starmie ex (330), Cinderace ex (320), Alakazam itd.

## 3. ROOT CAUSE — z dowodem z replayu (123167323, t6, v26fix vs KYOGRE)

Sekwencja krok po kroku (dekodowane akcje + observation):

1. **Ręka otwierająca: 6× Basic {W} Energy + 1× Mega Signal. Zero Pokémonów** (poza aktywnym Snover).
   Przy 10 Pokémon / 35 Energy w 60 kartach: oczekiwana liczba Pokémonów w ręce 7 = **1.17**;
   P(dokładnie 1) ≈ 41%.
2. T1: gracz używa Mega Signal (dobrze), ściąga Mega Abomasnow ex, attach 1 Energy, END.
3. T2: przeciwnik (Kyogre) sieka Snovera (90 HP).
4. T3: evolve w Mega Abomasnow ex (350 HP) — **jedyny Pokémon na całym boardzie**.
5. T4-6: 350 HP pada pod Kyogre, promowany Kyogre (150, bez energy) pada, **bench = 0 przez CAŁĄ grę**
   (6-8 kart w ręce, z czego 5-6 to Energy — nie ma czego postawić).

Wniosek: **przegrywamy mecze, w których jedyny aktywny pada, zanim ręka dostarczy backupa.**
Wszystkie 49 EARLY_COLLAPSE mają ten sam kształt (KO 0/0, bench pusty).

### Dlaczego to strukturalne, a nie bug agenta

- Agent **nie crashuje** (fuzz_robustness: 80 gier, 0 wyjątków, 0 naruszeń kontraktu).
- Agent **priorytetyzuje Pokémony** (scoring PLAY=320+, Waitress/Lillie preferują Pokémon 100+ vs Energy 40).
- Agent **idzie pierwszy** (GO_FIRST=1) i **buduje wall jak najszybciej** (Mega Signal T1, evolve T3).
- **35 Energy to nie błąd — to tożsamość decka**: win-condition to silnik mill:
  - Kyogre "Riptide": 20 dmg za każde {W} w discardzie (ramp do 300+),
  - Mega "Hammer-lanche": mill 6, 100 dmg za każde {W} (one-shot 350 walla),
  - Kyogre "Swirling Waves": 130 za 2 energy.
  Więcej Pokémonów = mniej Energy = wolniejszy mill → **D6b (12 Pokémon, 33W) przegrał z D0**
  (weak_gate −3.0pp z=1.75, exotic −1.2pp, mirror n.s.).

Lokalnie v25 "wygrywa" z tą słabością, bo pilot lokalny (v22b) ma TEN SAMY cienki board —
symetryczny wyścip. Live przeciwnicy mają różne decki: fast egzotyka (240-330 HP ex)
przecina nasz jedyny aktywny szybciej, niż ręka daje backupa.

## 4. Co zostało przetestowane (wszystkie A/B tej sesji)

| wariant | weak (wolne) | KYOGRE pool | top30 | exotic (fast) | werdykt |
|---|---|---|---|---|---|
| v26 (board-dev) | −0.72pp z−0.84 | — | −0.31pp | −5.25pp z−1.49 (thickbot) | **REJECTED** |
| v27 (aggro weak/endgame) | −0.75pp n.s. | n.s. | n.s. | +0.27pp n.s. | n.s. |
| v28 (mirror specialist) | — | +0.12pp n.s. | n.s. | +1.60pp n.s. | n.s. |
| D1 36W | +2.03 z1.66 | −1.92 z−1.28 | — | — | n.s. (split) |
| D2 Waitress4 | −1.51 | +0.64 | — | — | rejected |
| D4 34W+Boss | −1.28 | +0.72 | — | — | rejected |
| D5 Ultra Ball | −0.39 | −1.44 | — | — | rejected |
| D6b 12 Pokémon (33W) | −3.00 z−1.75 | +1.31 n.s. | −0.16 | −1.20 n.s. | **REJECTED** (zabija mill) |
| **v25 + D0 (35W)** | **87.9%** | **53.5% vs v25-pilot** | **82.7%** | **85.6%** | **BASELINE / OPTIMUM** |

Knob sweep (kyogre+exotic, opp=v25, n≈3.6k/stronę):
- RETREAT_WALL=300: total −0.42pp n.s. (kyogre +1.12, exotic −3.20 z1.44 — split)
- RETREAT_WALL=400: total −1.65pp z−1.31 (v25 lepsze)
- GUST_BONUS=100: total −1.68pp z−1.34 (v25 lepsze)
→ obecne knoby v25 (350/70) są dotuned; żadna kombinacja nie wygrywa obu pooli.

## 5. Wnioski i rekomendacje

1. **v25+35W to stabilne optimum lokalne** — 7 celowanych wariantów (2 agent + 5 deck) nie dało
   istotnej poprawy. Nie ma taniego "mocnego" upgrade'u w ramach tego decka.
2. **Gwarancja "0 strat z słabymi" jest niemożliwa** (gra stochastyczna: ręka 7 kart), ale mierzona
   podłoga v25 to **12-15% strat vs słabe/egzotyczne decki** (84.9-87.9% win). Mechanizm strat
   (cienki board vs fast ex) jest znany i udokumentowany powyżej.
3. Realna ścieżka do wyraźnego skoku wymaga **nowego conceptu decka** (np. linia z 12-14 Pokémon
   i szybszą win-condition zamiast milla) — to pełny deck search (dziesiątki A/B), nie jeden turn.
4. Do momentu takiego searchu: **nie zmieniać subów** (v25+35W = najlepszy znany),
   obserwować μ z kolejnych epizodów (submissions_list.csv aktualizowany każdym runem).
5. Inna gałąź (v26_strong_weakfix, 389.1) daje ~taki sam wynik jak nasz v25 (387.5-434.6) —
   zbieżność między gałęziami potwierdza, że 35W+v25-ish to ceiling bieżącego approachu.
