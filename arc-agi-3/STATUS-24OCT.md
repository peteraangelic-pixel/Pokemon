# Stan na 24.10.2026 — czy damy radę 45+?

## 1. Termin: Kaggle pokazuje **9 dni**, nie 2

Strona konkursu (`arc-prize-2026-arc-agi-3`): **"Featured Code Competition · 9 days to go"**
→ deadline ≈ **2.11.2026**. Zgadza się z wcześniejszym zapisem w repo.

Jeśli Twoje „2 dni" dotyczy czegoś innego (milestone, osobisty cutoff, inny konkurs)
— powiedz, bo to zmienia plan. Poniżej zakładam 9 dni, ale plan układam tak, żeby
dało się go wykonać w 2.

## 2. Gdzie jesteśmy

| | |
|---|---|
| nasz najlepszy wynik | **26.25** (duck v3, ref 57247568, 16.10) |
| ostatni submit | **16.10** — 8 dni temu |
| ostatni run workflow na naszej gałęzi | 16.10 |
| submity po 16.10 | **zero** |

Nocny łańcuch, na który czekaliśmy, **nigdy nie wystartował**. To najważniejszy fakt
w całej analizie — nie brak pomysłów, a brak wysyłki.

## 3. Tablica się podniosła (dane z dziś, 24.10)

| # | zespół | score | było 15.10 |
|---|---|---|---|
| 1 | Tufa Labs | 68.91 | 68.91 |
| 2 | Yi-Chia Chen | 68.21 | 67.49 |
| 3 | Team Turducken | 56.02 | — |
| 4 | mtg | **50.37** | 45.00 |
| 5 | the last dance | 49.85 | 49.85 |
| 6 | Grigoriy Zatravkin | 47.19 | 40.63 |
| 7 | 復活の混テキスト | 46.82 | — |
| 8 | NVARC3 | 45.90 | 43.94 |
| 9 | artificialagencylab.com | 45.41 | 41.74 |
| 10 | Majkel1337 | **45.03** | 44.84 |
| 15 | Daniel Franzen | 38.85 | — |

**Wniosek: 45+ to dziś miejsce #10.** Poprzeczka urosła — mtg z 45.00 na 50.37.

## 4. Cztery gałęzie, które kazałeś sprawdzić

Wszystkie cztery **nie mają ani jednego pliku ARC-AGI**. To trzy różne konkursy:

| gałąź | repo | konkurs | pliki ARC | ostatni commit |
|---|---|---|---|---|
| `c87f7a48-pokemon` | Pokemon | Pokemon TCG | **0** | 23.10 |
| `a450b00f-pokemon` | Pokemon | Pokemon TCG | **0** | **24.10 (dziś)** |
| `c4eeb067-gemma` | Gemma-konkurs | Gemma | **0** | 18.10 |
| `6d081d52-gemma` | Gemma-konkurs | Gemma | **0** | 16.10 |

Ich osiągnięcia (rating 715.4, benchmark v2.9.1, Rust gauntlet, pakiety V6.4)
są realne, ale **nie przenoszą się na leaderboard ARC**.

Co faktycznie wziąłem z tych gałęzi wcześniej:
- **dyscyplina pomiarowa** (kontrola tego samego agenta, parowane próby, wymagane n)
  → `local/abtest.py`, commit `5be877f`
- **wzorce Rust+Rayon** → mostek JSONL, commit `f59449a`

Czego **nie** da się wziąć: ich wyniki. Inne domeny.

## 5. Sufit publicznych notebooków: **34.3**

Ranking publicznych notebooków w konkursie (dziś):

| # | notebook | score |
|---|---|---|
| 1 | **Daniel Franzen — ARC-AGI-3 Milestone 2 Solution** | **34.30** |
| 2 | red-down — ARC3 franzen dprime | 33.55 |
| 3 | Jingshui Fu — ARC3 M2 Solution | 33.22 |
| 4 | Affectify ARC Dfranzen Form D1 | 32.61 |
| 5 | Try merging it | 32.60 |
| 6 | ARC3 M2 Solution v3 | 32.60 |
| 7 | ARC3 D-prime public base | 32.59 |
| 8 | UP ARC 3 | 32.38 |

**Nikt publicznie nie przekroczył 34.3.** Wszystkie czołowe publiczne notebooki to
forki Franzena, a on sam na LB ma 38.85.

**Luka: 34.3 → 45.03 = 10.7 punktu.** Ta luka jest prywatna. Nie da się jej
przeskoczyć kopiowaniem — dokładnie to odróżnia top 10 od reszty.

## 6. Odpowiedź na pytanie

**45+ w 2 dni: nie.** W 9 dni: bardzo mało prawdopodobne bez oryginalnej pracy.

Powody są arytmetyczne, nie motywacyjne:
- Najlepszy publiczny artefakt = 34.3. To +8 nad nami.
- Do 45 brakuje 10.7, a nikt publicznie tego nie osiągnął.
- Mamy 1 submit dziennie → maks. 2 próby w 2 dni, 9 w 9 dni.
- Każda próba na RTX Pro 6000 to ~8.5 h z 30 h/tygodniowej kwoty.

**Realny cel: 33–35.** To +7 do +9 względem 26.25, czyli wyjście z okolic 26 do
poziomu, na którym jest połowa publicznych rozwiązań. To jest wykonalne i sprawdzone.

## 7. Co robić (w kolejności)

### Krok 1 — od razu: Franzen, 34.3
1. Otwórz https://www.kaggle.com/code/dfranzen/arc-agi-3-milestone-2-solution
2. **Copy & Edit**
3. Ręcznie wybierz GPU **RTX Pro 6000** (nie P100/T4 — model to W4A16, ale runtime
   wymaga CC ≥ 8.9)
4. Zostaw wszystkie wejścia włączone (2 datasety + 2 modele — są publiczne)
5. Save & Run All → ~8.5 h
6. Wynik zgłoś do konkursu

To jedyna zmiana, która ma **zmierzony** publiczny wynik 34.3.

### Krok 2 — nasz wkład (opcjonalny, ryzykowny)
Mamy `local/solutions.json`: cztery gry z gwarantowanym poziomem 1
(`cd82`, `sp80`, `lp85`, `vc33`). Wpięcie tego w harness Franzena to jedyny
pomysł, którego nikt publicznie nie ma. Ale: wymaga modyfikacji harnessu,
a mamy ograniczoną liczbę prób. Wchodzić **tylko** jeśli krok 1 zadziała
i zostanie czas.

### Krok 3 — czego nie robić
- Nie wysyłać ponownie duck v3 — to ten sam notebook (zweryfikowane: identyczny
  z `taaf-duck-harness-kaggle-share.ipynb`), który dał 26.25.
- Nie liczyć na „rerun da 52-56". Ta liczba pochodziła z założenia, nie z pomiaru —
  i już raz została obalona przez nasz własny submit.

## 8. Weryfikacja faktów z tej analizy

| twierdzenie | jak sprawdzone |
|---|---|
| notebook duck = identyczny z Tufą | `diff` → IDENTYCZNE |
| Tufa public repo martwe od 1.07 | `git log -1` → 2026-07-01 |
| 4 gałęzie bez ARC | `git ls-tree -r \| grep -ci 'arc-agi'` → 0 w każdej |
| sufit publiczny 34.3 | ranking Kaggle `/code?sortBy=scoreDescending` |
| 45+ = #10 | leaderboard Kaggle, dziś |
| termin | „9 days to go" na stronie konkursu |
