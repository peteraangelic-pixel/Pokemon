# ARC3 Duck v13 „MEGA" — kandydat do zgłoszenia

Kontynuacja zweryfikowanej v11 (ta sama baza c45 bajt-w-bajt, ten sam
łańcuch patchy), z trzema dźwigniami naraz. **Nic nie zostało wysłane —
push i klik „Submit to Competition" należą do właściciela konta.**

## Co zmienia v13 względem v11 (slot A, który dał ~23)

| zmiana | mechanizm | podstawa |
|---|---|---|
| `PLAN_COMMIT = "1"` | commit(plan): model planuje, harness wykonuje plan krokowo z kontrolą oczekiwań; eskalacja co 60 akcji | patch 0005 z v11, testy 12/12 |
| `ARC3_LEVEL_TOKEN_CAP = "0"` | wyłącza cap 45k na poziom (a z nim darmowy RESET/ABANDON z 0004) | smoke na tych samych 10 grach: z capem 26,78 < bez 27,21 < 29,02 |
| **patch 0006: pamięć zwycięskich ścieżek + replay** | każdy ukończony poziom jest zapamiętywany (sekwencja akcji + hashe klatek); w kolejnych passach / po resecie poziom jest **odtwarzany deterministycznie** przez `_execute_action` z `generated_tokens=0`, z weryfikacją klatka-po-klatce i powrotem do LLM przy pierwszej niezgodności | NOWE; testy 6/6 na podrobionym kontrakcie solvera |
| **playbook offline** | 14 poziomów / 9 gier rozwiązanych BFS-em na PC usera, każda sekwencja **ponownie zwalidowana na prawdziwym kodzie gry** (`tools/build_playbook.py`: 14/14 OK, łącznie 184 akcje) | sweep2 z PC 27.10 |
| `ARC3_DEAD_SKIP = 1` | passy ≥4 gier, które po ≥3 passach mają 0 poziomów, kończą się od razu — sloty generacji idą do gier z postępem | część patcha 0006 |
| fix concurrency = 10 | bez zmian względem v11 (c45 z 120 dostał 0.00) | v11 |

Replay nie oszukuje licznika akcji: odtworzone akcje przechodzą przez
normalną ścieżkę wykonania i są liczone — oszczędność to tokeny (≈0 na
poziom) i zamiana setek akcji re-eksploracji na krótką zapisaną ścieżkę
(3–28 akcji). Przy kwadratowej karze RHAE to jest największa z dostępnych
dźwigni. Dodatkowo każdy poziom rozwiązany przez LLM w passie 1 działa
jak playbook dla passów 2–20.

## Weryfikacja (offline, na czystym bundle r033)

`tools/verify_v13.py --bundle <r033> --tests` → **ALL CHECKS PASSED**:
notebook 35 komórek, wszystkie komórki kodu się kompilują, 6/6 patchy
aplikuje się w kolejności notebooka na czystym drzewie, drzewo się
kompiluje, 12/12 testów plan-commit i 6/6 testów winpath **na
spatchowanym drzewie**. Przełącznik przetestowany w obie strony
(„1" włącza, „0" czyści env — poprawka względem v11).

## Jak wypchnąć (właściciel konta)

```bash
kaggle kernels push -p arc-agi-3/duck-v13-mega
```

potem w UI Kaggle: Run → **Submit to Competition** (sam „Save & Run All"
daje atrapę 0.0). W logu muszą się pojawić:
`v13 profile=plan plan_commit=1`, `v13 playbook: 9 gier, 14 poziomów`,
`ARC3 candidate-45: level_token_cap=0`.

## Kill-switche (każdy niezależny, edycja jednej wartości)

- commit szkodzi → w komórce przełącznika `PLAN_COMMIT = "0"`.
- replay szkodzi → w komórce wariantu `"ARC3_WINPATH": "0"`.
- dead-skip szkodzi → `"ARC3_DEAD_SKIP": "0"`.
- cap jednak pomagał → `"ARC3_LEVEL_TOKEN_CAP": "45000"`.

## Szczerze o oczekiwaniach

Nikt nie zagwarantuje 50+. Realistycznie (recenzje Gemma/c87/Smak,
29–30.10, zweryfikowane w kodzie): **28–38**. Sam playbook to podłoga
~2,9 pkt średniej na rosterze publicznym; reszta zależy od commita
(niezmierzony) i od tego, czy roster powtarza gry (wtedy pamięć między
wpisami dokłada głębię w kolejnych wpisach). 45–55 wymagałoby
wszystkiego naraz: rosteru klonów gier publicznych, działającego
replayu między wpisami i silnego commita. Rozbudowa playbooka na PC
(pakiet `../pc-sweep-pack`, cap 600–1200 s) to najtańszy sposób, by
przesunąć widełki w górę przed finałem 2.11.

## Korekty po recenzjach (v13.1, 30.10)

Trzy niezależne recenzje (Gemma 29.10; c87 i Smak 30.10) potwierdziły:
łańcuch patchy 6/6 na czystym r033, testy 12/12 + 6/6, playbook 14/14
i 184/184 hashe na prawdziwym silniku (trzy niezależne reprodukcje).
Wykryły też, że w punktowanym rerunie `n_passes=1`, więc pierwotny
opis dźwigni („passy 2–20") był błędny, a DEAD_SKIP oparty o
`pass_index` był martwy. v13.1 naprawia: magazyn kluczowany bazowym
kodem gry (pamięć działa między wpisami tej samej gry) oraz dead-skip
oparty o liczniki magazynu. `SERVER_STARTUP_TIMEOUT` (12 min) celowo
bez zmian — recenzja c87 domknęła, że nie przerywa biegu.
