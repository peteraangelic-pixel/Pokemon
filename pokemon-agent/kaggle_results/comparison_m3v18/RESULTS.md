# Porównanie: nasz v11/v18 vs druga gałąź v11m3 (2026-10-11, FFI libcg.so, deck v12_30_boss4 30W)

Wszystko policzone lokalnie (FFI, 2 workers). Druga gałąź = arena/8560a56a-pokemon @ d99ed65
(mirror_fix_2026_10_11.md: v11m3 = D "full", v11m3_B = atk-only, v11m3_C = atk+retreat; ich verdict: neutral @100-200g).
Agenci v11m3* skopiowani do naszych agents/ (commit obok) — testowani z tego samego katalogu,
card_index.json osiągalny (uniknięta pułapka „crippled agent from /tmp" z ich dokumentacji).

## 1) Deck-only gauntlet (przeciwnik = ta sama polityka, inna talia)

| agent | top30_live 30g (23 talie) | broad_field 30g (56 talii) | mirror gen8 300g×2 | mirror 35W live 200g×2 | regres broad 100g×2 | regres top30 100g×2 |
|---|---|---|---|---|---|---|
| **v11 (submission)** | 0.797 | 0.605 | 0.462 | 0.497 | 0.720 | 0.895 |
| v18 (nasz najnowszy) | 0.796 | 0.610 | 0.475 | 0.495 | 0.780 | 0.870 |
| **v11m3_C (ich najnowszy)** | **0.813** | 0.604 | **0.495** | **0.502** | 0.775 | 0.905 |
| v11m3 = D (ich full) | 0.809 | **0.625** | 0.463 | 0.492 | 0.735 | 0.900 |

Suma mirrorów (1000 g/agent): v11 0.476, v18 0.483, **v11m3_C 0.498**, D 0.475.
σ przy 1000 g ≈ 1.6pp → wszystkie różnice ≤1.4σ. Żaden wariant nie spełnia progu
akceptacji z protokołu drugiej gałęzi (≥ +5pp na 200g mirrorów AND bez regresji >3pp).

## 2) Head-to-head (polityka vs polityka, ten sam deck env, 300 g, zmienne strony)

| para | wynik |
|---|---|
| v11 vs v11m3_C | **0.523** dla v11 (1.5σ — remis stat.) |
| v11 vs v18 | **0.520** dla v11 (remis stat.) |
| v11m3_C vs v11m3(D) | 0.473 (remis stat.) |

## 3) Werdykt

- **Plateau potwierdzone niezależnie na naszych pulach**: v11, v18, v11m3_C, v11m3(D)
  są statystycznie nierozróżnialne (~7k gier FFI + 900 g H2H w tej sesji; ~30k gier u nich).
- v11m3_C to najlepiej wyglądający wariant mirrorowy (jedyne ≥0.495 na obu zestawach
  mirrorów), ale +2.2pp vs v11 to za mało vs próg +5pp. Zgodne z ich oceną: „C jest
  najczystszy, gdyby kiedykolwiek stawiać na mirror".
- v18 nie bije v11 (H2H 0.520 dla v11; broad +0.5pp = szum). v11m3(D) na broad 0.625
  (+2.0pp, 1.7σ) — obiecujące, ale ich 200g konfirmacja ablacji była neutralna.
- **Decyzja: submission v11+30W (phase1_tuned_v15_30_boss4_v11) bez zmian**, uzbrojony
  na 00:00 UTC. Backup kandydat #2: v11m3_C (gdyby kiedyś potrzebny wariant mirrorowy).

Surowe logi: ten katalog, pliki `main_heuristic_*__*.txt` i `h2h__*.txt`.

---

# DODATEK (19:20 UTC): pełna matryca "best z obu gałęzi" — v13/v19/v19b/v11m3_B/gen8r + @100g

Kontekst: c87f7a48 dodała v19/v19b (v18 + early gust T0-1 vs walls + retrieval-vs-Hammer),
8560a56a odrzuciła v19 @100g (0.630 top30) i wykazała, że claim "v18 +5.4pp" nie reprodukuje się.
Nasza niezależna weryfikacja (FFI, deck v12_30_boss4):

## @30g (top30_live 23 talie / broad_field 56 talii)

| agent | top30 | broad | uwagi |
|---|---|---|---|
| **v11 (submission)** | 0.797 | 0.605 | baseline |
| v13 | 0.801 | 0.603 | remis |
| v18 | 0.796 | 0.610 | remis |
| **v19** | **0.591** | **0.536** | **KATASTROFA — reject potwierdzony niezależnie** |
| **v19b** | **0.810** | 0.612 | v18 + 2×łagodny bonus +30 (gust vs wall T≤2, retrieval przy ≤1E) |
| v11m3_B | 0.803 | 0.612 | remis |
| v11m3_C | 0.813 | 0.604 | najlepszy wariant mirrorowy (see below) |
| v11m3(D) | 0.809 | 0.625 | 30g; broad edge nie potwierdzony @100g u nas |
| gen8r | 0.783 | 0.624 | najsłabszy top30, broad ok |

## @100g (deep)

| test | v11 | v18 | v19b | wniosek |
|---|---|---|---|---|
| broad_field 5600g | **0.621** | 0.608 | 0.617 | claim c87f7a48 "v18 0.641 @100g" NIE reprodukuje się (ich per-deck wariancja: DavideSanta 0.290 vs nasz ~0.43) |
| top30_live 2300g | 0.785-0.797* | — | **0.814** | v19b najlepszy top30 @100g w projekcie (+1.7-2.9pp vs v11; z≈2-3) |
| mirror gen8 300g×2 | 0.480 | 0.475* | 0.480 | coin flip wszyscy (m3_C 0.495, m3_B 0.485, gen8r 0.492) |
| mirror 35W live 200g×2 | 0.497 | 0.495* | 0.468 | remisy (m3_C 0.502) |
| H2H v11 vs v19b 300g | 0.483 | — | 0.517 | remis statystyczny |

*v18/m3 z poprzedniej sesji, ten sam protokół (katalog). v11 top30 @100g: 0.785 (8560a56a) / 0.797 (my 30g).

## Werdykt końcowy "best per branch"

- **c87f7a48: v11+30W** — po obaleniu claimów (v18 broad 0.641 ✗, v19 katastrofa ✗).
  Jedyny żywy ślad: **v19b** top30 +1.7-2.9pp @100g bez regresji — PONIŻEJ progu +5pp,
  do obserwacji (re-test @200g gdyby v19b miał być kandydatem).
- **8560a56a: v11+30W** (ich tabela @100g: v11 wygrywa 3/4 pule); artefakty m3_C/m3_B/gen8r — wszystkie remisy.
- **Winner across branches: v11 + 30W (phase1_tuned_v15_30_boss4_v11)** — i to leci po resecie 00:00 UTC
  z c87f7a48 (nasz egzemplarz DISARM-ed, żeby nie spalić 2 slotów na identyczny submit).

---

# 19:55 UTC — "Czy da się ulepszyć v11+30W?" — pełna odpowiedź empiryczna (v20/v20b/v20c)

## Odkrycie nr 1: warstwa ulepszeń v18/v19/v19b była MARTWYM KODEM
`MIRROR_IDS`, `RIPTIDE_ID`, `HAMMER_ID`, `WALL_IDS` nie są zdefiniowane w ŻADNYM agencie
(w tym w v11) — NameError połykany przez `except: pass`. **v18 ≡ v19b ≡ v11 funkcjonalnie**
(wer. programistyczna: brak symboli w namespace po załadowaniu). Wszystkie porównania
"v18 vs v11" na WSZYSTKICH gałęziach były porównaniami v11 z v11. Jedyne żywe zmiany
w rodzinie: v19 (katastrofa 0.591 — miał aktywne, nie-dominujące-na-wall reguły poza warstwą).

## Odkrycie nr 2: kto realnie przegrywa z v11+30W w aktualnym top30 (@300g/matchup)
Bill_Vlasak (**#1 na leaderboardzie, 1243.5**) → **0.613** (Mega Lucario ex 340HP/pt4,
Mega Brave 270, Aura Jab re-attach 3F, **20× Fighting Energy** — głodowanie niemożliwe);
Mengfei_Li 0.710; reszta top30 0.77-0.83; vs ミワハルキ (Banette stall) 12% REMISÓW (36/300).
Prize math: nasz Mega Abomasnow pt=4, Kyogre/Snover pt=1 — meczup z Lucario to aukcja
4-prize'owych Mega.

## Próby ulepszeń (napisane OD PODSTAWY, działające — zweryfikowane wrapper+namespace)
| wariant | reguły | Bill @600g | leo @300g | broad @100g | mirrory 300×2 | top30 @100g |
|---|---|---|---|---|---|---|
| v11 baseline | — | 0.608/0.613/0.630 (3 runy) | 0.767/0.783/0.733 | 0.621/0.613 | 0.480 | ~0.79 |
| v20 | B + Riptide boost + Hammer guard | 0.645 (1 run) | 0.817 | 0.596/0.591 ✗ | 0.480 | 0.801 |
| v20b | tylko B (anti-Mega) | 0.603 | 0.783 | 0.611 ✓ | 0.493 | 0.811 |
| **v20c** | **B + Hammer guard ≤10** | **0.638/0.603/0.610 → 0.617** | **0.823/0.757/0.790 → 0.790** | 0.603 | 0.508 | — |

Reguła A/Riptide: systematycznie rani WSZYSTKIE talie Water-line (5/5 najgorszych spadków
broad miały 721/722/723) → wykreślona. Reguła B: Leo +8.4pp (1 run) rozpłynęło się w +1.5pp
po powtórzeniach. Bill: v20c 0.617 vs v11 0.617 (3×600g każdy) — REMIS ABSOLUTNY.

## Werdykt
**NIE — na poziomie reguł decyzyjnych tej rodziny heurystyki v11+30W pozostaje optimum.**
Plateau potwierdzone teraz kodem DZIAŁAJĄCYM (wcześniej martwym), na świeżych danych live
(#1 leaderboardu w puli), z powtórzeniami 3×600g. Sufit szumu międzyrunowego silnika:
±3pp na 600g/meczup — nic nie przekracza progu +5pp.
**Realne rezerwy są głębiej:** plan atakujący vs Mega/stall (skład atakujących), deck
(31-35W przetestowane przez innych), lub hybida 2-agentowa (reguły per-archetyp) — to
już projekt na osobną sesję z większym compute. v20c zostaje jako artefakt (neutralny,
najlepiej przebadany kandydat na przyszłe modyfikacje).

---

# 20:40 UTC — v21: agent-hybryda (skan archetypu) + remisownik→zwycięzca — PRZEŁOM vs stall

## Diagnoza (tools/gauntlet_ffi_dbg.py — nowy instrument: obs dump + draw/end snapshots)
1. **Talia przeciwnika NIE jest widoczna** (tylko deckCount; ręka None). WIDOCZNE: ich aktyw+ława (id) i discard.
2. Remisy vs stall = 100% `step_limit` przy turze ~1240-1660. Stan: nasz ostatni pokemon (Kyogre 1-2W albo Abomasnow 1W) vs ich ściana (Latias 210/Clefairy 190/Slowking 120/Fezandipiti 210/Meowth 170), **prize 0-0, oba decki ~0, ręka pusta**.
3. Mechanizm: (a) Riptide tasuje W z discardu do decku → W-discard=0 → 0 dmg; (b) Hammer wy-millował nam deck; (c) silnik NIE egzekwuje deckoutu przy draw stebie → wieczna pętla. Ich deck wypala się SAM (~T35-51: wygrane z oppDeckCount=0!).

## v21 (agents/main_heuristic_v21.py) = v11 + skan (aktyw/ława/discard) + 3 tryby:
- STALL (Slowpoke/Latias/Clefairy/Meowth/Fezandipiti/Kyurem/Smoochum/Annihilape/Conkeldurr/Zeraora w boardzie): Hammer -40 gdy deck≤30, -200 gdy ≤20 (nie wypalaj sobie amunicji — ich deck padnie pierwszy), Riptide -120 przy deck>12 (koniec pętli 0-dmg), +30 do ataków (ściany się nie leczą).
- LUCARIO (677/678): ochrona 4-prize Abomasnow (retreat/Frost gdy zagrożony, z v20b).
- MIRROR (721/722/723): Hammer guard ≤10 na prawdziwym deckCount.

## Lokalne wyniki (deck v12_30_boss4; baseline v11 z wielu runów)
| matchup | v11 | v21 | Δ |
|---|---|---|---|
| **stall やる気 200g** | 0.780-0.850 (draws 12-16%) | **0.915 (draws 7.5%, L 1%)** | **+7-13pp** |
| Bill_Vlasak #1 (Lucario) 300g | 0.617±0.011 | **0.663** | **+4.6pp** |
| mirror gen8 300g×2 | 0.480 | **0.525** | +4.5pp (?) |
| top30_live @100g | 0.785-0.801 | **0.833** (draws 8/2300) | +3-5pp |
| broad_field @100g | 0.613-0.621 | 0.618 | neutralnie ✓ |
| leo_turing 300g | 0.775 | 0.740 | -3.5pp (szum/poza jedną próbą) |

## Weryfikacja na skali (GitHub Actions matrix, 13 jobów × 4 rdzenie, PAROWANE v11+v21 w tym samym runie)
Uruchomione (hybrid-verify); wyniki: kaggle_results/hybrid_verify/. Kryterium: potwierdzenie +Δ w parach na ≥2/3 kluczowych meczupach i brak regresji >2pp na broad/top30.

---

# 21:55 UTC — 3-way matrix (hybrid_verify2): v11 vs v21 vs v22 (v21 + early-gust c87f7a48)

48 200 parowanych gier/agent (13 jobów Actions; pełne logi: kaggle_results/hybrid_verify2/).

| job | v11 | v21 | v22 |
|---|---|---|---|
| bill600 | 0.607 | **0.648** | 0.593 |
| leo600 | 0.735 | 0.767 | **0.798** |
| mirror30_600 | 0.542 | 0.512 | 0.468 |
| mirror35_600 | 0.493 | 0.488 | **0.532** |
| mirror_live300 | **0.522** | 0.499 | 0.499 |
| stall_yaruki600 | 0.847 | 0.855 | **0.870** |
| top30_a/b200 | 0.808/0.806 | **0.837/0.827** | 0.834/0.822 |
| broad q1-q4 | 0.603-0.617 | 0.620-0.629 | 0.615-0.627 |
| utility300 | 0.909 | **0.921** | 0.913 |
| **AGREGAT** | 0.6554 | **0.6694 (+1.40pp)** | 0.6680 (+1.26pp) |

**Wnioski:** (1) v21 potwierdzony w drugim niezależnym matrixie (+1.10pp → +1.40pp; ~92k gier łącznie).
(2) v22 (early gust +25 T0-1 z ich v25 nałożony na v21) = **wymiana, nie dodatek**: leo +3.1pp,
mirror35W +4.4pp, stall +1.5pp, ALE Bill -5.5pp, mirror30 -4.4pp; agregat -0.14pp vs v21.
(3) Early-gust nie łączy się addytywnie z trybami v21 (oba atakują wczesne tempo). Ewentualny
kolejny krok: gust warunkowy (pomiń boost gdy tryb LUCARIO/MIRROR) — do testu.
