# arc3-duck-fixed.ipynb — naprawiony notebook duck-v7

**Gotowy do uruchomienia** wynik działania `tools/make_notebook_patch.py`. Nie edytować
ręcznie: każda zmiana powinna iść przez generator, bo tylko wtedy jest powtarzalna
i weryfikowalna.

## Proweniencja (żeby dało się wykryć zestarzenie)

| pole | wartość |
|---|---|
| źródło | `arc-agi-3/kaggle/duck-v7/arc3-duck.ipynb` |
| repo / gałąź źródła | `peteraangelic-pixel/Smak-Domu-Konkurs` @ `arena/5ed750ef-smak-domu-konkurs` |
| SHA-256 źródła | `93fa1a58dbce6d00aa71bc736a9bcda6bebf068346200ba23392bdcfd766ba52` |
| SHA-256 tego pliku | `5d772795a5794cf59db4b34744299e7bcdaa4d4ab5e2c06ea3dfa1ae56d128b1` |
| rozmiar | źródło 635 575 B → wynik 643 866 B |
| komórki | 30 → 30 (struktura niezmieniona, nic nie dodane ani nie usunięte) |
| wygenerowano | 2026-10-24 |
| generator | `tools/make_notebook_patch.py` |
| dowód weryfikacji | `results/verification_notebook.txt` |

**Jeśli ich notebook się zmienił** (inny SHA-256 źródła niż wyżej), ten plik jest
PRZESTARZAŁY i trzeba go wygenerować ponownie:

    python3 tools/make_notebook_patch.py <ich-arc3-duck.ipynb> notebook/arc3-duck-fixed.ipynb

## Co zostało zmienione (dokładnie dwie rzeczy)

1. **Komórka 7** — treść zapisywana do `/kaggle/duck-extra-02.patch` zastąpiona naszym
   `patches/0004-standalone-level-token-cap.patch`.

   Powód: ich `0003-early-abandon.patch` nie nakłada się po patchu Franzena
   (`error: patch failed: solver.py:35`), a komórka 10 aplikuje patche z `check=True`, więc
   notebook umierał **przed załadowaniem wag GPU** — cała linia duck-v7 nie mogła wystartować.
   Do tego 0003 jest merytorycznie podwójnie nieskuteczny: warunek
   `levels_completed > min_levels()` przy `ARC3_ABANDON_MIN_LEVELS=0` chroni przed abandonem
   dokładnie te gry, które najbardziej przeciekają, a licznik tokenów jest liczony od
   `token_baseline` (kursor per krok) zamiast `game_token_baseline`, więc cap 60 000 jest
   nieosiągalny. Szczegóły: `FAKTY-I-POMIARY.md` §9.1 i §9.2.

2. **Komórka 1** — `ARC3_VARIANT`:
   - `patches`: nazwa `0003-early-abandon.patch` → `0004-level-token-cap.patch`
   - `env` **dodane**: `ARC3_LEVEL_TOKEN_CAP=45000`, `ARC3_LEVEL_RESETS_MAX=1`,
     `ARC3_LEVEL_MIN_DONE=0`
   - `env` **wyzerowane**: `ARC3_ABANDON_TOKENS=0`, `ARC3_ABANDON_MIN_LEVELS=0` — osierocone,
     bo modułu `arc3_abandon` nie ma już w drzewie (sprawdzone: 0 referencji w `solver.py`,
     8 referencji `arc3_level_budget`). Zerowane celowo, żeby nikt nie wyczytał
     z `ARC3_VARIANT`, że abandon działa na 60 000 tokenów.

**Nie ruszone:** model i drafter, dataset, konfiguracja SGLang (komórka 17), budżety
i `TRUE_SUBMISSION` (komórka 21), lista gier smoke, `ONLY_RESET_LEVELS=true`, preflight,
`patch_files` (kolejność i liczba bez zmian).

## Weryfikacja (wykonana, nie zadeklarowana)

Patches wydobyte **z tego pliku** i nałożone dokładnie komendami z komórki 10
(`git apply --include=ARC3-Inference/*`, `cwd=<bundle>/src`) na pristine drzewo
ARC3-Inference (42 pliki z bundle r033, stan PRE-patch):

    harness-changes.patch  498780 B  — SHA identyczny z oryginałem Franzena (bit-w-bit)
    duck-extra-00.patch     11350 B  — ich 0001, nietknięty
    duck-extra-01.patch     33408 B  — ich 0002, nietknięty
    duck-extra-02.patch     10582 B  — SHA identyczny z 0004-standalone-level-token-cap.patch

    git apply (łańcuch z komórki 10)                      : 4/4 OK
    py_compile solver.py / tool_agent.py / arc3_level_budget.py : 3/3 OK
    referencje arc3_level_budget w solver.py              : 8
    referencje arc3_abandon w solver.py (oczekiwane 0)    : 0
    testy jednostkowe                                     : Ran 16 tests — OK (skipped=2)

Pełny przebieg: `results/verification_notebook.txt`.

Dwa testy są `skipped`, bo dotyczą dowodu bugów ich patcha 0003, a modułu `arc3_abandon`
w wariancie standalone nie ma — to oczekiwane, nie luka w pokryciu.

## Kill-switch

`ARC3_LEVEL_TOKEN_CAP=0` wyłącza całą funkcjonalność 0004 i przywraca zachowanie stockowe
(przetestowane w testach jednostkowych). To jest **pierwsza rzecz do zrobienia**, jeśli
cokolwiek w smoke pójdzie nie tak — zamiast debugowania wystarczy wyzerować tę jedną
zmienną i mieć pewność, że reszta notebooka jest nietknięta.

## Czego NIE robić z tym plikiem

- **Nie dokładać `0003b` obok 0004.** Zmierzone: łańcuch
  `franzen → 0001 → 0002 → 0003b → 0004-standalone` **nie nakłada się**
  (`error: patch failed: solver.py:46`) — oba patche wchodzą w ten sam rejon `solver.py`.
  Poprawna konfiguracja to **ZASTĄPIĆ** ich 0003 w tym samym slocie, nie dodać czwarty plik.
- **Nie zakładać, że to podniesie wynik samo z siebie.** 0004 odcina wyciek tokenów
  (35% tokenów i akcji w ich r019 poszło na poziom, który nigdy nie został ukończony),
  ale oczekiwany zysk trzeba zmierzyć smoke'em, nie extrapolować. Ich własna krzywa
  „200k→41.8, 300k→45.7" jest sprzeczna z ich własnym pomiarem — patrz `DIAGNOZA-45plus.md` §5.
- **Nie pushować `ops/request.json`, dopóki wisi run** (r057: push anuluje pending).
- **Nie zgłaszać bez dymu z `ARC3_SMOKE_OK`.**
- **Nie używać wewnętrznego API silnika** (`_get_valid_actions`, `_score`, `_win_score`)
  w żadnej submisji — docstring mówi wprost, że to dane nigdy nieudostępniane agentom.
  Patrz `FAKTY-I-POMIARY.md` §1bis.
