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

---

## DODAANE 10-13 ~09:45 UTC: weryfikacja krzyżowa gałęzi c87f7a48 + a450b00f (mój harness, moje pule)

Wyekstrahowałem ich agentów (`agents/a450_v26_flood.py`, `agents/a450_c87v26_weakfix.py`) i odpaliłem A/B vs mój v25 (13,7k gier/pulę + 200 mirror).

| A (vs mój v25 + D0, opp=v25) | kyogre26 | exotic5 | weak8 | TOTAL |
|---|---|---|---|---|
| **a450 FLOOD** (v24 board-dev+v25 knobs+FLOOD layer) | 0.550 vs 0.532 (+1.73, z1.25) | 0.868 (+1.20) | 0.891 (+0.62) | **+1.44pp (z=1.33)** |
| FLOOD — czysty mirror (200) | **0.555 vs 0.485 (+7.00, z1.40)** | | | |
| **c87 weakfix (LIVE 57130754)** | **0.574 vs 0.535 (+3.85, z=2.79)** | 0.852 (−1.20 n.s.) | 0.899 (+1.75 n.s.) | **+2.77pp (z=2.59)** |

**Wnioski:**
1. **FLOOD a450 się potwierdza** (kierunek i wielkość zgodna z ich matrycą +1.41pp z=2.42; u mnie z=1.33 n.s.; silny sygnał mirror +7pp n=200).
2. **weakfix c87 (LIVE) jest LOKALNIE WYRÓŻNIONO silniejszy niż v25** (+2.77pp, z=2.59, głównie kyogre +3.85 z=2.79) → cienki live WR (18-24) to efekt środowiska (silniejsi live oponenti + mirrory), NIE słabości agenta.
3. Stack weakfix+flood: a450 odrzucił (0.500/0.847 — double suppression). Nie testuję ponownie.
4. **Rekomendacja slotu (do decyzji c87, bez moich submitów):** słaby live WR weakfixa ≠ problem agenta (dowód powyżej). Jeśli po ~60+ grach weakfix < 0.45 live → kandydat na ostatni slot = **FLOOD** (jako samodzielny agent).

## DODAANE 10-13 ~10:15 UTC: weryfikacja c87f7a48 v27/v28 (bench400 fastZacian)

c87 (tip 457b0fa) przeanalizowała 249 epizodów / 142 strat live (loss_snapshots.jsonl) i zbudowała v27/v28.

**Nowe live (COMPLETE n~50/submisja):** v26weakfix **410.9** (49ep 0.469; vs KYOGRE 0.48, vs ? 0.29, vs LUCARIO 0.50) > v25knobs **408.1** (48ep 0.417; vs KYOGRE 0.54, vs ? 0.22, vs LUCARIO 0.14) > v25old 387.5 > v22b 328.1.

**Ich root cause #1 (zawsze weryfikowany przeze mnie niezależnie):** puste board przy stracie:
- v26weakfix: **61%** strat z pustym board, **42%** przy T≤12 (vs 39-41% / 28-33% w starszych wersjach)
- przyczyna: bonus bench 360/350/335 < alternatyw supporter+gust → agent nie zapełnia benchu, dostaje KO, nie ma rezerwy.
- inne przyczyny: Snover 90HP lead vs fast-ex (jednostrzał), nowe ?-archetypy NIE w FAST_EX (Zacian ex 220/230, Duraludon 130 x3, Hydrapple 330, Mega Starmie 330→420, Genesect 220, Zangoose 200), mirror deckout guard za późno, low-HP KO niedopriorytetyzowane.

**Ich v28 (mój diff):** KO 50/20→60/30; bench 360/350/335→400/380-400/360-380; mirror guard ≤10/15/20→≤15/20/25; FAST_EX +6 id (336,299,169,839,992,1002).

**Moja weryfikacja (A/B vs ich weakfix, 10k+ gier/pulę):**
| pulę | v28 | weakfix | Δ |
|---|---|---|---|
| newarch_pool (10) | 0.876 | 0.879 | −0.30pp n.s. |
| kyogre26+exotic5+weak8 | 0.649 | 0.645 | −0.41pp n.s. |
| mirror vs mój v25 (200) | 0.485 | 0.470 | +1.50pp n.s. |

→ **v28 lokalnie neutralny** (zgodne z ich własnym "weighted 0.711 vs 0.715 close"), ALE修的ka naprawia **zweryfikowany dziura live** (61% pustych boardów + ?-archetypy 0.22-0.29 WR) której moja pula nie karze tak mocno (brak Zacian/Duraludon/Hydrapple w testach).

**Status ostatniego slotu (4/5 spalone, ja tylko doradzam):**
- kandydat A = c87 v28: lokalnie neutralny, naprawia dziurę live, mały risk (górna granica ≈ weakfix już live).
- kandydat B = a450 FLOOD: +1.44pp (z=1.33) moje pule / +1.41pp (z=2.42) ich matryca; +7pp mirror.
- head-to-head v28 vs FLOOD: w toku.

### Head-to-head v28 vs FLOOD (ostani slot, opp=weakfix, ~10k/pule)
| pula | c87_v28 | a450_FLOOD | Δ |
|---|---|---|---|
| newarch10 | **0.887** | 0.867 | v28 +2.00pp (z=1.36) |
| kyogre+exotic+weak | 0.635 | 0.635 | remis (z=0.05) |
| mirror 200 | 0.475 | **0.535** | FLOOD +6.00pp (z=1.20) |

**Ostateczna rekomendacja slotu (doradztwo, bez submitu):** oba n.s. względem siebie. Live pole karze głównie ?-archetypy (WR 0.22-0.29) + kyogre (55% meczów) → **c87 v28** atakuje dokładnie tę dziurę (FAST_EX + bench400) i ma +2pp na newarch; risk ≈ 0 (górna granica = weakfix już live). FLOOD = równie dobry alternatywny kandydat (silniejszy mirror). Merge koda v28+FLOOD możliwy ale nietestowany (stacki traciły tempo u a450).

## DODAANE 10-13 ~11:15 UTC: porównanie 3 gałęzi + BUG attack-est potwierdzony też u mnie

### Stan gałęzi (10-13)
- **a450b00f** (tip 0ce6616): (1) **DECK SEARCH F1+F2 ZAMKNIĘTY**: 270 kandydatów, F2 pre-rejestrowana bramka (≥+2pp ORAZ z≥2 na 2 seedach, 74 decki×30g) → **0/10 PASS**; **35W-noBoss optymalny w promieniu ±3 kart**; koncept swarm (Lucario/Ogerpon) = 0.364/0.420 = martwy z naszym scoringiem; (2) **v29 SWARM** = weakfix + S1 bench-as-resource (hot 35/warm 15, cel 3) + S2 auto-fast-ex (136 id z db: ex∨mex ∧ (hp≥200 ∨ hp≥150∧rc≤2)) + **S3 attack-est fix**; ich wyniki vs weakfix: 5/5 pul ≥0, pooled +0.5pp z~1.2 (poniżej 2σ); bundle ready NIE WYSŁANY; (3) weryfikacja c87 v30 (patrz niżej).
- **c87f7a48** (tip e2443df): v29 = v28 + port mojego mirror-specialista (**MARTWY KOD — zweryfikowane przeze mnie: MILL_HAMMER_MIN_V29/MILL_RIPTIDE_MIN_V29/MIRROR_NO_TRADE_TURNS_V29 = 1 wystąpienie = definicja**), v30 = v29 + a450 S3 (żywym 1:1) + swarm-bench (**też martwe: SWARM_BENCH_* bez wywołań**). Commit message opisuje zachowania, których kod nie wykonuje.

### Odkrycie dnia: BUG monetowy Riptide/Hammer — jest też w MOIM v25
Riptide 1042 + Hammer-lanche 1046 mają **d=0 w card db** (dmg w tekście efektu). Gałąź `SelectType.ATTACK` (dialog "wybierz atak") we WSZYSTKICH wersjach linii (w21-v30, 3 gałęzie) oceniała ataki surowym `d` → 0-0 → kolejność silnika = **coin toss**. Mój v25: linia 1441 — POTWIERDZONE. `estimate_attack_damage` umie liczyć obie (test: Riptide=40, Hammer=555 przy 3W) — tylko nie było podpięte w tej gałęzi.

### Moja macierz A/B (D0, opp=v25, ~25k gier)
| Agent | kyogre26+exotic5+weak8 | newarch10 | mirror 200 |
|---|---|---|---|
| mój v25 (base) | 0.652 | 0.847 | 0.530 |
| **mój v31 = v25+S3** | **0.627 (−2.49pp, z=2.29)** | 0.860 | 0.500 |
| c87 v30 | **0.668 (+3.21pp, z=2.97)**; kyogre +2.85 z2.06, exotic +6.20 z2.92, weak +2.50 z1.59 | 0.867 (remis) | **0.425 (−9.00pp, z=1.81)** |
| a450 v29 swarm | 0.664 (+1.64pp, z=1.53) | 0.879 (+2.20, z=1.45) | 0.540 (+7.00, z=1.40) |
| v30 vs v29 (duel) | 0.675 vs 0.663 (v30 +1.18 z1.11) | — | 0.540 vs 0.530 |

**Wnioski:**
1. **S3 attack-est fix sam na czystym v25 = istotna STRATA (−2.49pp z2.29)** — głównie kyogre −3.42 z2.47. Mechanizm: w mill-race (mirror/kyogre) wymuszony Hammer (KO+300) przyspiesza WŁASNE deckout; coin toss statystycznie wydłużał wyścig. **Nowe odkrycie — żadna gałąź nie testowała fixa w izolacji.**
2. **c87 v30 = najsilniejszy vs non-mirror** (exotic +6.2 z2.92 — bench400 ratuje matchupy z fast-ex), ale **mirror −9pp** (guard ≤15/20/25 + over-mill z S3).
3. **a450 v29 swarm = najrówniejszy** vs v25 (wszystko ≥0: 3-pool +1.64, newarch +2.2, mirror +7.0, zero istotnych regresji).
4. weakfix (LIVE) nadal ≥ v30 na mojej 3-puli (0.676 vs 0.668) — zysk v30 vs weakfix jest w niszy exotic/?.

### v32 (mój, w teście) = v30 + guard mill-race w mirror
W mirror (seen ∩ {721,722,723}) i deck≤15 → powrót do raw-d (coin toss) w SelectType.ATTACK; wszędzie indziej S3 zostaje. Cel: moc v30 na exotic/kyogre + przeżywalność mirror. Wynik poniżej.

### v32 — wynik (w teście wyżej)
- vs v30 3-pool: **0.647 vs 0.673 → −2.51pp (z=2.34)** — kyogre −2.81 z2.03 (guard odpala na puli kyogre = nasze id, tam Hammer-press WYGRYWA wyścig — coin toss tam przegrywa), exotic/weak = szum (kod identyczny, nasze-id=0 w deckach exotic)
- vs v30 mirror: **0.595 vs 0.535 → +6.00pp (z=−1.21, n.s.)** — guard działa na czystym mirror
- vs mój v25 mirror: 0.555 vs 0.510 → +4.50pp n.s.
- **Werdykt: ODPRAWIONY** — guard za gruby (różnica między "kyogre-pool" a "czysty mirror" wymaga dokładniejszego detektora składu decka). Niespójne kierunki: w kyogre-poolu S3 wygrywa, w czystym mirroru coin-toss wygrywa (oba n.s./brzegowe).

## OSTATECZNA SYNTYEZA 3 GAŁĘZI (10-13 ~12:00 UTC)

| Agent (D0, opp=v25, moje pule) | 3-pool | newarch | mirror |
|---|---|---|---|
| v25 (base; LIVE 387.5) | 0.652 | 0.847 | 0.530 |
| weakfix (LIVE 410.9) | **0.676 (+2.77, z2.59)** | — | — |
| a450 FLOOD | 0.661 (+1.44, z1.33) | 0.868 | 0.555 (+7pp) |
| c87 v28b | 0.649 (n.s.) | 0.876 | 0.485 |
| **c87 v30** | 0.668 (+3.21, z2.97) | 0.867 | **0.425 (−9pp, z1.81)** |
| **a450 v29 swarm** | 0.664 (+1.64, z1.53) | 0.879 (+2.2, z1.45) | 0.540 (+7.0, z1.40) |
| mój v31 (v25+S3) | 0.627 (−2.49, z2.29) | 0.860 | 0.500 |
| mój v32 (v30+guard) | 0.647 (−2.51 vs v30) | ≈ | 0.555 (+6pp vs v30) |

**Konwergencja 3 gałęzi (wszystkie dane zgodne):**
1. Optimum agenta: weakfix ≈ v29 ≈ v30 (±1pp, dead heat; nisze: v30=exotic/? +6.2 z2.92, v29=bench-survival/mirror, v28b=Ogerpon +5.3pp wg a450).
2. Optimum decka: 35W-noBoss zamknięte (deck search 0/10, ±3 karty; UB2 −0.20/−0.58; Boss −0.44/−0.66).
3. S3 attack-est fix = pomoc w niszy fast-ex, uszczerbek w mill-race (moje nowość: w izolacji −2.49 z2.29).
4. Jedyny dalszy dźwign = nowy agent pod swarm (Phase-2/RL) lub akceptacja podłogi 12-15% + meta-gra o sloty.

**Rekomendacja ostatniego slotu (doradztwo — nic nie wysyłam; decyzja user/c87 do resetu 00:00 UTC 14.10):**
- **Pierwszeństwo: a450 v29 swarm** — jedyny agent z ZERO istotnych regresji na żadnej puli; S1 (bench-as-resource) atakuje zweryfikowany root cause #1 (61% pustych boardów); top30_live +1.2/+2.0 (a450).
- Alternatywa: **c87 v30** — największy pojedynczy zysk (exotic +6.2 z2.92) ALE mirror −9pp z1.81; koszt realny DOPÓKI live field to coin-toss agenci (weakfix/v25knobs — oba bez S3).
- v28b = bezpieczny minimum; nic = zachowanie status quo.

## DODAANE 10-13 ~12:15 UTC: świeży live μ + weryfikacja c87 V33 (kandydat konsensusowy)

### Świeży live (fetch 11:45-11:48 UTC, ostatnie 40 epizodów/submisja)
| Submisja | μ (publicScore) | WR okno 40ep | vs KYOGRE | vs ? |
|---|---|---|---|---|
| 57130779 v25knobs | **412.0** | 0.350 (14-26) | 0.40 | 0.18 |
| 57130754 v26weakfix | 398.1 | **0.450** (18-22) | 0.42 | **0.50** |
| 57125516 v25old | 387.5 | 0.450 | 0.62 | 0.23 |
| 57125561 v22b | 328.1 | 0.375 | 0.29 | 0.44 |

μ kumulacyjne odwróciły kolejność (knobs 412.0 > weakfix 398.1), ale świeże okno 40ep: weakfix 0.450 > knobs 0.350 (szczególnie "?": 0.50 vs 0.18). Oba ~400 — spójne z podłogą 12-15% strat. **Uwaga workflow:** kaggle-our-replays 3x status "failure" ALE dane fetch+commit w 3/3 (kosmetyczny błąd na końcu commit-back; logi niedostępne z sandboxu).

### Gałęzie zbiegły na V33 (c87 1bc665f, 11:24Z)
c87: v31 = a450 v30 + S1/S2 WIRED (auto-fast-ex 136 id + bench-as-resource ŻYWE) → **v33 = v31 + KO 80/40 + 8 non-ex fast id (136→144)**. a450 (001c16a, 11:34Z): 4-arm A/B V33 prowadzi 2/2 (meta +1.33/+1.57 z1.39), **NOWY RANKING: V33 > V31 > V32 > V30b > v28b; "ship V33"**. a450 v34 (prize-deficit) odrzucony (n.s.); "iteracja behawioralna wyczerpana (±0.3pp noise ceiling); realny dźwign = Phase-3 deck+agent co-design (basic-engine)".

### Moja weryfikacja c87 V33 (D0, opp=v25)
| test | V33 | B | Δ |
|---|---|---|---|
| 3-pool (13.7k) | 0.660 | 0.632 (v25) | **+2.74pp (z=2.53)**; kyogre +3.58 z2.59, exotic +1.0, weak +1.12 |
| newarch10 | 0.855 | 0.861 (v25) | −0.60pp n.s. |
| mirror 200 | 0.560 | 0.510 (v25) | +5.00pp (z=1.00) n.s. |
| duel vs a450 v29: 3-pool | 0.654 | 0.655 | remis (z=0.10) |
| duel vs a450 v29: mirror 100 | 0.480 | 0.550 | −7.00pp n.s. |

**→ V33 ≥ v29/v30 w moim harnessie: zero istotnych regresji + istotny zysk kyogre (55% live field).** Trzydrożny remis v29/v30/v33 w granicach szumu (zgodne z a450 "±0.3pp noise ceiling").

### OSTATECZNA REKOMENDACJA SLOTU (14.10 00:00 UTC; nic nie wysyłam)
**V33 (c87, bundle c87)** — zbieżność 3 gałęzi (c87 "BEST vs weak and mirror", a450 "ship V33", mój harness: +2.74pp z2.53 3-pool, zero istotnych minusów). Alternatywy (v29/v30/v28b) = w granicy szumu. Po wrzuceniu: odczyt WR live po ~40-50 epizodach (mój trigger our-replays działa mimo "failure").
