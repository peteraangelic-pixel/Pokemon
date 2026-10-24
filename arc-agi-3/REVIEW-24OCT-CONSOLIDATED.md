# Konsolidacja opinii z innych gałęzi — 24.10.2026

Trzy sesje (c87/a450 „Smak", c4eeb067 „Gemma", 6d081d52 „Gemma") przysłały analizy.
Sprawdziłem każdą liczbę i każde twierdzenie o mechanizmie w naszym własnym kodzie
i logach. Poniżej: co się potwierdza, co jest nieaktualne, i czego **nikt z nich nie
zauważył**, a co jest w naszym własnym ledgerze.

---

## 1. Co się potwierdza (i jest cenne)

### 1.1 Wąskie gardło to liczba decyzji, nie ich jakość — POTWIERDZONE

Z naszego `duck/notebook/EXPERIMENTS.md` i artefaktów r018:

| metryka | wartość |
|---|---|
| r018 (v5): akcje / poziomy / czas | 2065 / 32 / 3516 s |
| akcje na minutę (10 gier równolegle) | **35,2** |
| akcje na minutę na grę | **3,5** |
| przy ~3 akcje/decyzję → decyzje/min/grę | **~1,2** |

Sesja „Gemma" oszacowała ~1,0 decyzji/min. **Zgadza się.** A gra potrzebuje
~240–300 decyzji (ΣH≈730 akcji / 3). Przy 1,2 decyzji/min to ~200–250 min,
przy capie ~48–132 min. Wniosek: **kończy się czas, zanim gra się skończy.**

### 1.2 Poziom dominuje nad wydajnością akcji — POTWIERDZONE (mocniej niż twierdzą)

Porównanie dwóch naszych przebiegów (z ledgera):

| run | poziomy | akcje | smoke |
|---|---|---|---|
| r013 (v3) | **35** | 2318 | **29,02** |
| r018 (v5) | 32 | 2065 | 27,21 |

r018 zrobił **mniej akcji** (lepiej na wydajność) i dostał **niższy wynik**, bo
ukończył 3 poziomy mniej. To bezpośredni dowód, że wynik ≈ ważony odsetek
**ukończonych** poziomów, a nie efektywność ruchu. Zgadza się z `rust/src/score.rs`:

```
RHAE = (1/|L|) · Σ_l  w_l · min(H_l/A_l, 1.15)²
```

Nieukończony poziom = 0, ale **zostaje w mianowniku**. Czyli: każdy dodatkowy
ukończony poziom to do +132,25·w, a oszczędzanie ruchów na poziomie już ukończonym
daje najwyżej 32% (1,15²).

### 1.3 `n_passes = 1` jest wymuszone — POTWIERDZONE

```
bm.n_passes = 1
bm.game_weights = None
```

### 1.4 `game_weights` nie jest żadną dźwignią — POTWIERDZONE

W naszym notebooku to **`None`**. Sesja „Smak" sama to z czasem skorygowała
(„wpływa tylko na agregację diagnostyki HTML"). Czyli połowa jej planu na 45
(optymalizacja budżetu przez game_weights) **nie istnieje jako mechanizm**.

### 1.5 Świat model psuł wynik — POTWIERDZONE

v4 (r015) = 23,11 vs v3 (r013) = 29,02. Zgadza się z waszym wcześniejszym wnioskiem.

---

## 2. Co jest nieaktualne lub błędne

| twierdzenie | rzeczywistość (sprawdzone dziś) |
|---|---|
| „lider ma 55,89" (Smak, 1. wiadomość) | **68,91** (Tufa) — sam to potem poprawił |
| „45+ to dziś miejsca 5–8" (Smak, korekta) | **#10** (45,03 = Majkel1337) |
| „Franzen 47,25" | jego wpis na LB: **38,85**; 47,25 to stary snapshot z 15.10 |
| „próg nagród ~41" | nieaktualne — 10. miejsce to 45,03, 20. to 37,98 |
| „commit duck-v8 5f397df" | ~~nie istnieje~~ **BŁĄD Z MOJEJ STRONY — istnieje** na `arena/a450b00f-pokemon`, 5 plików. Patrz `DUCK-V8-VERIFIED.md` |
| „smoke 1 gry, potem submit" (Gemma) | **sprzeczne z naszym własnym ledgerem** — patrz §3 |

---

## 3. Czego nikt nie zauważył — a jest w naszym ledgerze

`duck/notebook/EXPERIMENTS.md`, pierwsze akapity, napisane przez naszą własną
gałąź duck:

> Eval set: cn04 dc22 g50t ka59 ls20 m0r0 s5i5 sc25 su15 tn36.
> **Per-game single-run spread is huge** (Franzen's own 4 passes: m0r0 **0–100**,
> tn36 **3,6–100**, cn04 **4,8–47,6**), so a single 10-game run **only detects
> effects of roughly +10 or more**.

To znaczy, że **cała nasza historia eksperymentów jest nieodróżnialna od szumu**:

| run | wariant | smoke |
|---|---|---|
| Franzen 4×25 | baseline | 29,48 |
| r007 | v2 think-less | 30,54 |
| r013 | v3 | 29,02 |
| r015 | v4 world model | 23,11 |
| r018 | v5 world model | 27,21 |

Rozrzut 23,11–30,54 przy zmianach, które ledger sam opisuje jako „noise".
m0r0 potrafi dać 0 albo 100 w tym samym wariancie.

**Konsekwencje, które zabijają dwie rekomendacje z opinii:**

1. **„Smoke na 10 grach, zgłaszać gdy bije 29,02"** (Smak) — próg jest **wewnątrz
   szumu**. r007 miało 30,54 i ledger nazywa to szumem. Ten test nic nie wykryje.
2. **„Smoke 1 gry, potem submit"** (Gemma) — przy rozrzucie 0–100 na grę to jest
   rzut monetą. To dokładnie ten błąd, który już popełniliśmy pięć razy.

To jest jedyna rzecz, której nie powiedziała żadna z trzech sesji, a która jest
napisana w naszym repo. I dlatego `local/abtest.py` (parowane seedy, CI, wymagane n)
jest wart więcej niż wszystkie trzy plany razem.

---

## 4. Jedyna dźwignia z potwierdzonym wynikiem: notebook Franzena

Ranking publicznych notebooków (Kaggle, dziś):

| notebook | public score |
|---|---|
| **Franzen — ARC-AGI-3 Milestone 2 Solution** | **33,68** (best 34,30) |
| red-down — franzen dprime | 33,55 |
| Jingshui Fu — M2 Solution | 33,22 |
| 8 kolejnych forków Franzena | 31,7–32,6 |

Wszystko powyżej 32 to forki Franzena. On sam na LB: 38,85.

**+7,4 do +8,1 względem naszych 26,25 — i to zmierzone, nie estymowane.**
Model: Qwen3.8-Flash-Next W4A16 + drafter MTP + SGLang (Pennyroyal), GPU RTX Pro 6000.
Wszystkie wejścia publiczne (2 datasety + 2 modele).

Sesja „Smak" radzi „podmienić model w naszym ducku" — ale to jest dokładnie to,
czym Franzen już jest, + jego 6 miesięcy poprawek harnessu. Prościej skopiować jego
notebook niż odtwarzać go na naszym 26,25.

---

## 5. Odpowiedź na „czy damy radę 45+"

**Nie.** I to jest arytmetyka, nie defetyzm:

- 45,03 = **#10** na tablicy (dziś).
- Sufit **publiczny** = 34,30. Luka 34,3 → 45,03 = **10,7 pkt, której nikt
  publicznie nie przeszedł**.
- Żeby wyjść z 26,25 na 45 potrzeba ~+31 poziomów (przy ~0,6 pkt smoke/poziom).
  v3 zrobił 35 poziomów na 10 gier. Trzeba by 54–66, czyli śr. 5,4–6,6/grę,
  przy 6–10 poziomach na grę. To 2× obecnego tempa — a wąskie gardło (decyzje/min)
  jest sprzętowe/modelowe, nie promptowe.
- Mamy **1 submit dziennie** i ~9 h na rerun. Do 2.11 to ~9 prób, ale każda
  wykrywa tylko efekty ≥ +10.

**Realistyczny cel: 34–35.** To +8 i wejście w okolicę, gdzie stoi połowa
publicznych rozwiązań.

---

## 6. Plan (9 dni do 2.11, nie 2)

### Dziś — decyzja
**Skopiować notebook Franzena.** 33,68–34,30 zmierzone > 26,25 nasze.

1. https://www.kaggle.com/code/dfranzen/arc-agi-3-milestone-2-solution
2. Copy & Edit → GPU **RTX Pro 6000** → zostaw wszystkie wejścia → Save & Run All (~8,5 h)

### Potem — jedyne, co ma sens mierzyć
Nasze `local/abtest.py` na danych z **nagranych przebiegów**, nie na nowych zgadywaniach:
```bash
python local/abtest.py ab --seeds 120 --workers 14 --params-a '{...}' --params-b '{...}'
```
Wynik `significant: false` = nie wysyłać. To jedyne narzędzie w repo, które umie
odróżnić efekt od szumu przy tym rozrzucie.

### Czego NIE robić
- ❌ Smoke 1 gry → submit (rozrzut 0–100)
- ❌ „Bije 29,02" jako próg (wewnątrz szumu)
- ❌ game_weights (to `None`)
- ❌ Odtwarzać duck-v8 z opisu — nie istnieje w remote, trzeba by pisać od zera
- ❌ Dokładać world model (zmierzone: szkodzi)

### Jeśli zostanie czas
Replay ukończonych poziomów **ma sens tylko jeśli gra restartuje od poziomu 1 po
game over**. Najpierw sprawdzić to jednym przebiegiem z logiem, potem pisać kod.
Kolejność z opisu „Smaka" była odwrotna — kod przed weryfikacją założenia.

---

## 7. Źródła weryfikacji

| fakt | jak sprawdzony |
|---|---|
| r018: 2065 akcji, 32 poziomy, 3516 s | `EXPERIMENTS.md` na `origin/arena/98ddb59f-pokemon` |
| rozrzut 0–100 na grę | tamże, nagłówek ledgera |
| `n_passes=1`, `game_weights=None` | `grep` po `duck-harness-original.ipynb` |
| RHAE = ważona, cap 1,15² | `rust/src/score.rs` + testy |
| LB: 45,03 = #10, Tufa 68,91 | leaderboard Kaggle, 24.10 |
| sufit publiczny 34,30 | `/code?sortBy=scoreDescending`, 24.10 |
| duck-v8 istnieje (5f397df) | poprawione w `DUCK-V8-VERIFIED.md` — mój wcześniejszy `git ls-tree` na niepobranych gałęziach dał fałszywy negatyw |
| deadline entry 26.10 / finał 2.11 | `STATUS.md` |

---

## 8. Korekta (24.10, po dostarczeniu linków)

Twierdzenie „duck-v8 nie istnieje w żadnym remote" było **błędne** — commit `5f397df`
istnieje na `arena/a450b00f-pokemon` z 5 plikami. Przyczyna: `git ls-tree` na gałęzi
niepobranej lokalnie kończy się błędem, który `2>/dev/null` ukrywał, więc „brak
gałęzi" wyglądał jak „brak plików".

Sprawdziłem pakiet i **przesłankę** na prawdziwym silniku: `GameAction.RESET` cofa
licznik poziomów do zera, a replay odtwarza poziom bajt w bajt (4/4 gry).
Szczegóły i pełna ocena: [`DUCK-V8-VERIFIED.md`](DUCK-V8-VERIFIED.md).
