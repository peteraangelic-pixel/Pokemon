# v20 — co Codex wrzucił na moją gałąź, co to zmienia, i gdzie jest droga do 50

**Data:** 2026-11-01 · **Kod:** `local/road_to_50.py` + `local/test_road_to_50.py` (19/19).

---

## 0. Co jest na gałęzi

Codex dołożył **trzy commity** (`a05a556`, `c443ba9`, `d356195`) na wierzch mojego
`20f2674`. **Moja praca jest nietknięta** — sprawdzone `merge-base --is-ancestor`,
`20f2674` jest w historii origin. Dodali:

| katalog | co zawiera |
|---|---|
| `peer-review/codex-v3-control-20261101/` | **świeża kontrola v3** na Kaggle: notebook, `benchmark.json`, metadane |
| `peer-review/codex-v3-slim-20261101/` | wariant „slim" (sekcje pamięci) — **ODRZUCONY**, plus `COMPARISON.json` |
| `analysis/...` | surowe logi, snapshoty promptów, `ACTIVATION.json`, `MANIFEST.json` |

Wszystko to są **pomiary**, nie patche. Żaden nie zmienia kodu harnessu.

---

## 1. Najważniejszy nowy fakt: świeża v3 potwierdza, że łańcuch v13 szkodzi

Ta sama lista 10 gier, ten sam budżet 48 min, concurrency 10, kod dokładnie
odzyskanej v3 (`SHA 8d0195f9…`):

| | **v3 świeża (01.11)** | **r121 = v13.7 (wysłany)** |
|---|---|---|
| wynik publiczny | **27,49667** | 22,58848 |
| ukończone poziomy | **33** | 25 |
| akcje ogółem | 1877 | 2275 |
| **akcji na nieukończonych** | **300 (16,0%)** | **1015 (44,6%)** |
| akcji na ukończony poziom | **47,8** | 50,4 |

To jest **najczystszy dowód, jaki mamy**: łańcuch v13 nie tylko nie pomógł —
zwiększył udział akcji wyrzucanych na poziomy, które nigdy się nie kończą,
z 16% do 45%. Nic dziwnego, że rerun dał 13,28 przy 26,25.

### 1.1 Wariant „slim" (sekcje pamięci) — odrzucony, i to jest dobry pomiar

| | kontrola v3 | slim |
|---|---|---|
| poziomów | **33** | 24 |
| wynik | **27,50** | 17,35 |
| marnotrawstwo | **16,0%** | **34,1%** |
| akcji/ukończony poziom | **47,8** | 52,2 |

Sekcje pamięci **podwoiły marnotrawstwo** i pogorszyły efektywność. 6 z 10 gier
straciło poziomy. Codex sam pisze uczciwie, że pojedyncze przebiegi nie rozdzielają
wariancji od wpływu sekcji — zgoda, ale kierunek jest spójny z mechanizmem.

---

## 2. Mój model przewiduje wszystkie trzy runy

`score = 0,93 × pokrycie`, waga poziomu `k`, na podstawie samych list
`levels_completed` i `number_of_levels`:

| run | model | rzeczywisty | błąd |
|---|---|---|---|
| v3 świeża | 27,15 | **27,50** | 0,35 |
| r085 (c45) | 27,70 | 26,78 | 0,92 |
| r121 (v13.7) | 21,87 | 22,59 | 0,72 |
| **rerun 57811453** | **12,8** | **13,28** | **0,48** |

Cztery runy, dwie konfiguracje, trzy tygodnie, **maksymalny błąd 0,92 pkt**.
Model jest gotowy do użycia jako narzędzie decyzyjne.

---

## 3. Korekta mojego V19 — mechanizm był źle nazwany

W `V19-ROAD-TO-50.md` napisałem: *„akcji/poziom 66,4 → 91,0, +37%, łańcuch kazał
modelowi marnować ruchy"*. **Kierunek był dobry, liczba była artefaktem.**

Dla r085 podzieliłem **wszystkie** akcje przez ukończone poziomy (66,4), a dla v3
**tylko akcje na ukończonych** (47,8). To dwie różne wielkości. Jedną metodą:

| run | akcji na ukończony poziom | **marnotrawstwo** | tok/akcję | akcji/wywołanie |
|---|---|---|---|---|
| v3 świeża | **47,8** | **16%** | 908 | 4,48 |
| r085 (c45) | 51,8 | 22% | 667 | 4,51 |
| r121 (v13.7) | 50,4 | **45%** | 733 | 5,01 |

**Efektywność jest płaska: 47,8 – 51,8, różnica 8%.** Zmienną jest
**marnotrawstwo: 16% – 45%, różnica 29 punktów procentowych.**

Czyli: łańcuch v13 **nie spowolnił modelu — zwiększył utratę akcji.** Moje
„+37%" było nieporównaniem dwóch mianowników, dokładnie ta sama klasa błędu
co wcześniejsze `head -20`.

---

## 4. Trzy stałe, które opisują całą konkurencję

```
poziomy/gę = akcje/gę × (1 − marnotrawstwo) ÷ akcje_na_poziom
```

| run | akcje/gę | × (1−straty) | ÷ akcji/poziom | = poziomy/gę |
|---|---|---|---|---|
| v3 świeża | 187,7 | × 0,84 | ÷ 47,8 | **3,30** ✓ |
| r085 | 212,6 | × 0,78 | ÷ 51,8 | **3,20** ✓ |
| r121 | 227,5 | × 0,55 | ÷ 50,4 | **2,48** ✓ (zmierzone 2,50) |

Model odtwarza wszystkie trzy z dokładnością 0,02 poziomu. **To jest cała gra.**

---

## 5. Droga do 50 — trzy dźwignie i ich prawdziwa cena

Na poziomie v3 (188 akcji, 16% strat, 47,8 akcji/poziom = 27,50):

| dźwignia | wynik | zysk |
|---|---|---|
| **marnotrawstwo 16% → 0** | **37,6** | **+10,3** |
| akcji/gę 188 → 220 (szybkość) | 36,5 | +9,0 |
| akcji/poziom 47,8 → 45,8 | ~29 | +1,5 |
| wszystko naraz | ~47 | +19,5 |

**Najtańsza dźwignia to marnotrawstwo — 300 akcji, które nie kończą poziomu.**
Warta +10,3 pkt przy zerowym koszcie budżetu. To **więcej, niż cały łańcuch v13
kosztował** (10,61).

### 5.1 Skąd bierze się sufit

Serwer jest wysycony i dzielony na 10 gier, więc
`akcje/gę = budżet_tokenów ÷ (tok/call ÷ akcji/call)`. Zmierzone `tok/call`:
3009 / 3675 / 4066. Zmierzone `akcji/call`: **4,48 / 4,51 / 5,01 — praktycznie stałe.**

| akcji/call | akcji/gę | wyniki |
|---|---|---|
| 4,48 (dziś) | 187 | 27,5 |
| 6,0 | 251 | 43,9 |
| **8,0** | 334 | **62,4** |

**50 punktów wymaga ~6,8 akcji na wywołanie** — albo równoważnego cięcia `tok/call`
z 4066 do ~2700.

I tu jest zła wiadomość o hintcie: **on już jest włączony w r121 i dał 4,48 → 5,01,
czyli +12%**, a nie +22%, jak zakładałem. Do 6,8 brakuje +52%. Sam hint tego nie zrobi.

---

## 6. Co to znaczy dla dwóch pozostałych slotów

**1.11 — dokładny rerun v3.** Artefakt jest, `SHA 8d0195f9`, świeży kontrolny bieg
potwierdza 27,50 na tej samej liście gier.

**2.11 — jedna zmiana, celująca w marnotrawstwo.** Nie w pamięć (slim: −10,15 pkt),
nie w cap, nie w eskalację. Kod Codexa wskazuje właściwy trop: **25 zaobserwowanych
błędów narzędzi — 9 `NameError`, 9 `StaleStateActionError`** — czyli akcje tracone
na wywołania, które nie mogą się udać. Ich własna propozycja (`retained functions`
ograniczone do poziomu) jest jedyną, która adresuje utratę akcji, a nie tokenów.

**Czego nie robić:** nie dokładać sekcji pamięci (zmierzone −10,15), nie wracać do
capów poziomu (V18: −8,06), nie liczyć na hint (zmierzone +12%, potrzeba +52%).

---

## 7. Czego nie wiem

1. **Czy 16% marnotrawstwa v3 da się ściąć bez utraty głębokości.** Część tych 300
   akcji to uczciwe próby na poziomach, których nie da się skończyć. To nie jest
   w pełni odzyskiwalne.
2. **Czy różnica tok/call (3009 vs 4066) to v3 czy wariancja.** Jeden bieg na wariant.
3. **Czy wynik 27,50 przełoży się na rerun.** Smoke ≠ rerun, i to jest najmocniejsza
   lekcja tej kampanii: 22,59 smoke → 13,28 rerun. Kontrola v3 jest **nadal smokiem**
   (Codex nazywa to `PUBLIC_SAVE_RUN_NOT_SCORED_RERUN`) — 27,50 nie jest prognozą 26,25+.

**Czego nie zrobiłem:** nie tknąłem cudzych gałęzi, nie wysłałem submitu, nie mam
bundla r033 ani dostępu do Kaggle. Wszystkie liczby pochodzą z plików, które Codex
wrzucił na tę gałąź (`benchmark.json`, `COMPARISON.json`, `CONTROL-RESULT.md`)
oraz z `r085`/`r121` pobranych z `Smak-Domu-Konkurs` przez `gh api`.
