# v14 — plan wersji lepszej od 13.2

**Data:** 2026-10-30 · **Status:** projekt + działający moduł + symulator; **nic nie wysłane.**
**Poprzednicy:** v13 (`3782f8c`), v13.1 (`cbefdd4`), v13.2 (`6b10853`).
**Kod:** `local/v14_policy.py`, testy `local/test_v14.py` (13/13 PASS), liczby z `local/token_budget.py`.

---

## 0. Odpowiedź w trzech zdaniach

Tak, mam plan — ale **nie taki, jakiego oczekujesz**. Zmierzyłem trzy lewary
i tylko jeden ma właściwy znak i skalę: **tokeny na akcję** (853 → ~479 daje sufit 50).
Drugi (porzucanie poziomów) **jest zakładem od −19,5 do +2,9**, więc nie wolno go
wysyłać w ciemno. Trzeci (priorytet krótkich gier) jest darmowy, ale mały.

v14 to nie „więcej funkcji". To **jedna zmiana plus jeden pomiar**, który jako
pierwszy w całym tym sporze rozstrzyga, czy główna dźwignia w ogóle działa.

---

## 1. Punkt wyjścia — co już wiemy na pewno

| fakt | wartość | źródło |
|---|---|---|
| budżet na grę | **2 945 s** (9 h × 10 slotów / 110 gier) | `EVAL-BUDGET-MODEL.md` §2; niezależnie potwierdzone przez c87 |
| tempo silnika (u nas) | **15,8 ms/token** | zmierzone z `history[]`, `token_budget.py` |
| budżet tokenów na grę | **~186 200** | 2945 s / 15,8 ms |
| akcji na generację | **4,61** | 6034 / 1308 |
| tokenów na akcję | **853** | 6034 akcji, 5,1 M tokenów |
| akcji na grę | **~219** | zgodne z obserwowanymi 140–370 |
| pokrycie / efektywność | **29% / 90%** | r018 |

**Wynik = pokrycie × efektywność².** Efektywność jest już blisko sufitu. Cały
zapas jest w pokryciu, a pokrycie jest ograniczone **tokenami**, nie czasem
i nie liczbą tur.

### 1.1 Czego NIE kopiować z c87

c87 znalazł mnożnik **3,6× w tempie silnika** (17,2 vs 62,6 ms/token, ten sam
model 8B). To ważne odkrycie — ale **nie dla nas.** Nasze runy są w szybkim
reżimie: **15,8 ms/token**, czyli szybciej niż ich najlepszy przypadek.
Nie mamy tu czego odzyskiwać. Warto to wiedzieć, żeby nie przepalić slotu
na „optymalizację puli KV", która u nas nie boli.

---

## 2. Lewar 1 (główny): tokeny na akcję — mnożnik, znak zawsze dodatni

```
akcji na grę = budżet_tokenów / (tokeny na akcję)
             = 186 200 / 853 = 219   (dziś)
             = 186 200 / 479 = 389   (cel)
```

| akcji/grę | wymagane tok/akcję | vs dziś | sufit wyniku |
|---|---|---|---|
| 219 (dziś) | 853 | 1,00× | ~19–31 |
| **389** | **479** | **−44%** | **~51** |
| 600 | 310 | −64% | ~62 |

**Dlaczego to mnożnik, a nie zakład:** mniej tokenów na akcję = więcej akcji
w tym samym budżecie. Więcej akcji nigdy nie szkodzi — zawsze można ich nie użyć.
Jedyne realne ryzyko to spadek jakości rozumowania (gorsza efektywność), i to
jest mierzalne.

### 2.1 Skąd wziąć −44% — trzy konkretne cięcia

**Cięcie A: dłuższe plany (największe i najpewniejsze).**
Model robi 4,61 akcji na generację przy ~3933 tokenach. Jeśli to samo
rozumowanie obsłuży 10 akcji, tokeny na akcję spadają o ~54%.

> **Ale patch 0005 tego zabrania.** `PLAN_COMMIT_TOOL_ADDENDUM` mówi:
> *„A step you claim to understand should carry an expectation computed before it runs."*
> Czyli **każdy krok planu płaci tokenami za `expect={...}`**. To jest podatek,
> który zjada dokładnie ten zysk, o który walczymy. v13.2 tego nie rusza.

Rekomendacja: **expectation obowiązkowy tylko na pierwszym i ostatnim kroku planu**
albo tylko na krokach, które autor planu oznaczy jako „niepewne". Reszta kroków
idzie bez `expect`. To odwraca domyślną politykę patcha.

**Cięcie B: krótsza dyrektywa eskalacyjna.**
Obecna ma ~550 znaków i każe modelowi wykonać **cztery** kroki naraz
(`model_state`, `model_step`, `check_model`, `commit`). Przy `ESCALATE_ACTIONS=10`
trafia do promptu **~20 razy na grę** (189 eskalacji / 10 gier, `V13-AUDIT-30OCT` §1A.1).
Zamienić na jedno zdanie: *„Ten poziom nie jest ukończony — wyślij `commit()` z co najmniej 5 krokami."*

**Cięcie C: przestać opisywać planszę w każdej turze.**
Tego **nie zmierzyłem** (logi nie mają `uncached_input_tokens` — wszystkie 0),
więc nie podaję liczby. Ale to jedyne miejsce, gdzie 3933 tokenów na generację
może się schować poza rozumowaniem. Wymaga pomiaru, nie założenia.

### 2.2 Zastrzeżenie, którego nie pomijam

**Nie wiem, jak dużo z 853 tok/akcję jest ściśliwe.** Cięcie A jest oszacowaniem
z arytmetyki (3933 tok / 10 akcji = 393), nie pomiarem. Bezpieczny przedział:
**−20% do −55%**. Przy −20% (682 tok/akcję) sufit to ~34; przy −55% (384) — ~63.

To jest **cała różnica między „warte wysłania" a „nie warto"**, i dlatego punkt 5
(pomiar) jest ważniejszy niż samo wdrożenie.

---

## 3. Lewar 2: porzucanie poziomów — **ZAKŁAD, nie lewar**

Zmierzone: **21–35% akcji idzie na poziomy, których nie ukończymy**
(r013 21%, r015 21%, r018 35%). Najgorsze: ls20 spaliło **227 akcji** na jednym
poziomie i dało 3,27 pkt; tn36 — 124 akcje, 3,57 pkt.

Wygląda jak oczywista strata. Symulacja (`local/v14_policy.py`, dwa warianty
bo koszt nieukończonego poziomu jest **nieznany**):

| założenie o zablokowanym poziomie | cap 20 | cap 30 | cap 45 | cap 60 | cap 90 | cap 120 | bez capa |
|---|---|---|---|---|---|---|---|
| **pesymistyczne** (nigdy nie padnie) | 28,5 | 28,5 | 27,1 | 26,2 | 25,2 | 26,6 | **25,6** |
| **optymistyczne** (padnie za 2× tego, co wydaliśmy) | 11,2 | 11,7 | 10,9 | 12,4 | 25,5 | 29,7 | **30,7** |

**Zakres: od −19,5 do +2,9.** Przy naszej wariancji ±3 pkt to **szum albo strata.**

**Wniosek: nie wysyłać porzucania w ciemno.** To jest ten sam błąd, który zrobiło
v13 stackując pięć zmian. Jedyna sensowna wersja to cap **liczony per gra**, nie
stały: np. `2 × mediana kosztu ukończonych poziomów w tej grze` (w r018 mediana 26
→ cap ~52). Ale i to wymaga pomiaru, bo górna widełka nadal jest ujemna.

---

## 4. Lewar 3: priorytet krótkich gier — darmowy, mały, bez ryzyka

Waga poziomu `l` w grze o `L` to `l / (1+…+L)`. Pierwszy poziom gry 4-poziomowej
to **1/10 = 10%** tej gry; gry 9-poziomowej **1/45 = 2,2%** — **4,5× różnica** za tę
samą pracę.

Roster jest stały, więc nie wybieramy gier. Ale gdy kolejka się kończy (a przy
110 grach i 11 falach kończy się), **kolejność ma znaczenie**: gry obsłużone
później mogą zostać obcięte. Ustawienie krótkich gier na początek oznacza, że
obcina się te, które i tak płacą najmniej.

**Zysk: niezmierzony, ale znak nie może być ujemny.** Implementacja: sortowanie
`bm.games` po `win_levels` rosnąco. Jedna linia. `short_game_priority()` w module.

---

## 5. Pomiar, który rozstrzyga wszystko — ważniejszy niż zmiany

**Nikt w tym sporze nie zmierzył `tokenów na akcję` w prawdziwym biegu.**
Ani autorzy v13/13.1/13.2, ani c87, ani ja. To jedna liczba i ona decyduje
o wszystkim.

Wymagane: **jedna linia logu na grę**, na koniec:

```
v14 metrics: game=<id> actions=<n> tokens=<n> tok_per_action=<x> plans=<n> avg_plan_steps=<x> levels=<k>/<L>
```

`LevelGovernor.tokens_per_action()` liczy to samo w module. Z `history[]`
da się to wyciągnąć po biegu **tak samo, jak wyciągnąłem 4,61 tutaj** —
procedura jest w `token_budget.py`.

**Kryterium decyzyjne z góry:**
- `tok_per_action ≤ 500` → cięcie A działa, wdrażać agresywniej, cel 60+
- `500 < tok_per_action ≤ 750` → działa słabo, zwiększyć długość planu
- `> 750` → cięcie A nie działa, problem jest w inpucie (cięcie C), nie w outpucie

---

## 6. Co konkretnie zbudowałem

| plik | co | stan |
|---|---|---|
| `local/v14_policy.py` | `LevelGovernor` (cap poziomu, nudge na plany, metryka tok/akcję), `simulate()` z dwoma wariantami, `short_game_priority()` | ✅ |
| `local/test_v14.py` | 13 testów, m.in. że cap **może zaszkodzić** i że budżet jest w tokenach | ✅ 13/13 |
| `local/token_budget.py` | odtwarza 4,61 / 853 / 186 200 z surowych logów | ✅ |
| `V14-PLAN.md` | ten dokument | ✅ |

Czego **nie** zbudowałem i dlaczego: patcha do harnessu. Nie mam bundla
Franzena ani GPU, więc każde twierdzenie „patch aplikuje się i działa" byłoby
zgadywaniem. Specyfikacja patcha jest w §2.1 — to trzy zmiany w
`prompts.py` (usunięcie obowiązkowego `expect`, skrócenie eskalacji) i jedna
w `tool_agent.py` (wymóg `min_plan_steps`).

---

## 7. Realna ocena — czy to jest lepsze od 13.2

| kryterium | v13.2 | v14 |
|---|---|---|
| Atakuje wąskie gardło? | częściowo (presja na plany) | **tak, wprost w tokeny/akcję** |
| Czy efekt jest mnożnikiem? | nie, to presja | **tak (`1/tok_na_akcję`)** |
| Czy ma pomiar, który może obalić tezę? | nie | **tak, §5, z góry ustalone progi** |
| Czy dokłada ryzykowne zmiany? | 5 naraz | **1 pewna + 1 darmowa + 1 wyłączona** |
| Oczekiwany wynik | 28–38 (wg ich README) | **30–52, zależnie od ściśliwości tokenów** |

**Nie obiecuję 50.** Widełki są szerokie, bo jedna liczba jest nieznana.
Ale v14 jest **jedyną** wersją, która (a) atakuje właściwe wąskie gardło,
(b) nie dokłada zakładów, (c) zawiera pomiar mogący ją obalić.

---

## 8. Kolejność wdrożenia (jeśli mam robić to dalej)

1. **Sam pomiar** — dodać linię logu z §5 do v13.2, wysłać jako **jeden slot**.
   To nie jest wersja „na 50"; to wersja „żeby wiedzieć". Koszt: 1 slot z 4 dni.
2. **Cięcie A** (dłuższe plany, `expect` tylko na kluczowych krokach) na podstawie
   wyniku z 1.
3. **Cięcie C** dopiero po pomiarze inputu — jeśli pomiar z 1 pokaże `> 750`, to
   znaczy, że wąskim gardłem jest wejście, nie wyjście.
4. Porzucanie — **tylko** z capem per gra i tylko po pomiarze; widełki −19,5…+2,9
   tego nie uzasadniają.

**Czego nie zrobię bez Twojej zgody:** nie wypchnę niczego na `a450b00f`, nie
wyślę submitu, nie dotknę `request.json` ani łańcucha nocnego.

---

## 9. Zbieżność z c87 (`980deff`, 30.10 ~08:00) — i jeden niepokojący fakt

Niezależnie, w tym samym czasie, c87 opublikował `980deff`. Zbieżność jest
niemal pełna:

| rzecz | ja (`v14`, `token_budget.py`) | c87 (`980deff`) |
|---|---|---|
| formuła | `akcje/grę = budżet_tokenów / tok_na_akcję` | **identyczna**: `2945×1000/(ms/token × tok/akcję)` |
| akcji na wywołanie LLM | **4,61** (6034/1308, r013+r015+r018) | **4,357** (474 wywołań / 2065 akcji, r019) |
| wniosek | tokeny/akcję to jedyna dźwignia o skali | **to samo** |
| ocena `PLAN_COMMIT` | „tylko dopisuje narzędzie do opisu, bez wymuszenia" | **cytuje mnie dosłownie** |

Dwie sesje, różne runy, ta sama liczba w granicach 6%. To najsilniejsze
potwierdzenie, jakie mamy, że **batchowanie już działa** i nie jest wąskim gardłem.

### 9.1 Mój błąd rozprzestrzenił się na cudzą decyzję

README v13.2 uzasadnia `ESCALATE 60→10` liczbą **„dziś 1,0 akcji/decyzję → sufit
~19–31; 2,0 → ~51"**. To **moja** liczba z pierwszej wersji `MEGA-DIAGNOSIS` §4 —
tej, którą sam obaliłem w `1541d08`. Autorzy v13.2 zacytowali ją jako przesłankę
swojej zmiany.

**Wniosek: błąd w analizie nie zostaje w analizie — staje się uzasadnieniem
zmiany w kodzie.** To najdroższa lekcja z tej sesji i powód, dla którego
`local/token_budget.py` ma `assert` na 4,61: liczba ma się zepsuć, zanim zepsuje
czyjąś decyzję.

### 9.2 Luka, którą c87 widzi lepiej niż ja

c87 ostrzega: przy `ESCALATE_ACTIONS = 10` i **4,357 akcji na wywołanie**,
eskalacja odpala się **zanim model zdąży zbadać poziom** — a `commit(plan)` z
`expect` per krok zatrzymuje się przy pierwszej niezgodności.

Ja pisałem o tym jakościowo (`V13-AUDIT-30OCT` §1A.2). c87 ma to policzone
i **jest to argument przeciw v13.2 w obecnej postaci**. Zgadzam się: `10` jest
prawdopodobnie **za nisko**, a właściwa wartość to ~3× średniego kosztu
ukończonego poziomu (w r018 mediana 26 → **~30–60**), nie 10.

To zmienia moją wcześniejszą rekomendację „zejść z 60 na ~8–10": **8–10 było
oparte na błędnej premii „1 akcja na turę".** Przy 4,6 akcji na wywołanie
właściwy zakres to **30–60** (czyli mniej więcej to, co v13.1 miało, plus
skrócenie samej dyrektywy z §2.1 cięcie B).

### 9.3 Co z tego zostaje dla v14

Bez zmian: **tokeny na akcję** to jedyna dźwignia ze właściwym znakiem.
Zmienia się jedno: **nie ruszać `ESCALATE_ACTIONS` w dół poniżej ~30** — to był
mój błąd wynikający z błędnej liczby, a c87 ma rację, że przy 10 model nie ma
czasu zbadać poziomu. Zamiast tego skracać **treść** dyrektywy, nie zwiększać
**częstotliwość**.
