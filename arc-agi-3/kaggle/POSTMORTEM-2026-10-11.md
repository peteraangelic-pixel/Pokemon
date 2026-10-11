# Post-mortem: zgłoszenie 57075036 — wynik 0.01

Data: 2026-10-11. Zgłoszenie wysłane 13:15 UTC, wynik ok. 20:53 UTC.

## Wynik

```
57075036  submission.parquet  SubmissionStatus.COMPLETE  publicScore = 0.01
```

Dla skali: na publicznym leaderboardzie jest **20 drużyn**, a
**najsłabsza ma 36.49**. Jesteśmy ~3650× pod ostatnim miejscem.

## Przyczyna: zgłosiliśmy plik-atrapę

Zawartość ocenionego `submission.parquet` (ściągnięta komendą
`kaggle kernels output`):

```
row_id         game_id      end_of_game  score
placeholder_0  placeholder  True         0.0
```

**Jeden wiersz, `game_id = "placeholder"`, score 0.0.** To jest dokładnie
ramka, którą nasz notebook zapisuje w fazie zapisu — nigdy nie zagrano
żadnej partii.

Potwierdza to drugi dowód: `kaggle competitions episodes 57075036`
zwraca **„No episodes found"** — nie ma żadnego rozegranego epizodu.

## Dlaczego tak się stało

Notebook ma rozwidlenie:

```python
is_competition_rerun = os.environ.get("KAGGLE_IS_COMPETITION_RERUN", ...) in {"1","true","yes"}
if is_competition_rerun:
    ...gra przez gateway...
else:
    ...zapisuje atrapę...      # <- poszło tędy
```

Log z biegu, którego wyniki zostały zgłoszone, kończy się w 27. sekundzie:

```
Successfully installed arc-agi-0.9.8 arcengine-0.9.3
Prepared tracked novelty-explorer source in /tmp/arc_novelty_agent
Wrote save-phase placeholder submission.parquet     <-- atrapa
```

27 sekund to czas instalacji wheeli i zapisu atrapy — **nie 9 godzin gry**.

### Wniosek o komendzie API

```
kaggle competitions submit -c COMP -k <notebook> -f submission.parquet -v N
```

**nie jest** w pełni równoważna przyciskowi „Submit to Competition".

Zgłoszenie przeszło (exit code 0, status COMPLETE), ale wzięło **istniejący
plik wyjściowy notebooka** — czyli atrapę z fazy zapisu — zamiast wymusić
ponowne uruchomienie notebooka w trybie konkursowym, gdzie dostępna jest
bramka do ukrytych środowisk (`http://gateway:8001`).

Krótko: **API potrafi dostarczyć plik, ale nie potrafi uruchomić gry.**

## Co z tego wynika

1. **Wynik 0.01 nic nie mówi o jakości naszego agenta.** Agent nie miał
   szansy zagrać. Nie wolno traktować tej liczby jako oceny heurystyki.
2. **Dzisiejszy limit zgłoszeń został zużyty na atrapę**
   (`Remaining today: 0`). Następna próba najwcześniej jutro po północy UTC.
3. **Prawdziwe zgłoszenie wymaga kliknięcia „Submit to Competition"**
   w interfejsie Kaggle na
   `kaggle.com/code/petersharps/arc-agi-3-novelty-explorer`.
   Tego nie da się zrobić z poziomu API — musi to zrobić właściciel konta.

## Jak rozpoznać ten błąd następnym razem

Przed zgłoszeniem sprawdzić, czy wyjście notebooka jest prawdziwe:

```bash
kaggle kernels output <ref> -p /tmp/chk
python3 -c "import pandas as pd; print(pd.read_parquet('/tmp/chk/submission.parquet'))"
```

Jeżeli w kolumnie `game_id` widać `placeholder` — **nie zgłaszać**.

## Czego się nauczyliśmy o API (mimo porażki)

Te komendy działają i są przydatne:

- `kaggle competitions submit -k <notebook> -f <plik> -v <wersja>`
  — przyjmuje zgłoszenie (ale nie uruchamia gry)
- `kaggle competitions submission-limits` — ile zgłoszeń nam zostało
- `kaggle competitions submissions --csv` — status i wynik
- `kaggle competitions episodes <id>` — lista rozegranych gier
  (tu: „No episodes found", bo ich nie było)
- `kaggle kernels output <ref>` — **ściąga prawdziwe wyjście biegu**,
  także log. To cenniejsze niż `kernels files`, które pokazuje tylko
  metadane i może być nieaktualne.

Uwaga: `kernels files` pokazywało `submission.parquet` 868 B,
podczas gdy `kernels output` dało 2747 B. **Nie ufać `kernels files`.**

## Status

- Agent: bez zmian, niesprawdzony w trybie konkursowym.
- Następny krok: właściciel klika „Submit to Competition" w UI.
- Dopiero wtedy dowiemy się, ile naprawdę warty jest nasz agent.
