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
