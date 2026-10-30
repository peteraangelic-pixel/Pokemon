# Odtworzenie weryfikacji duck-v13.1

`V13-1-VERIFICATION.md` twierdzi, że `tests/test_winpath.py` przechodzi 7/7
i `tests/test_plan_commit.py` 9/12. Ten katalog zawiera brakujący element, żeby
te liczby dało się odtworzyć bez bundla Franzena i bez GPU.

## Skąd wziąć kod v13.1

Pliki v13.1 **nie są** w tym drzewie — leżą na innej gałęzi:

```bash
git fetch origin arena/a450b00f-pokemon
git archive origin/arena/a450b00f-pokemon arc-agi-3/duck-v13-1 | tar -x -C /tmp
```

## Testy winpath (7/7)

`arcengine.py` w tym katalogu to wierny stub oryginalnego modułu silnika. Odtwarza
tylko to, czego dotyka `arc3_winpath.py`: `GameAction[name]` (enum, `.value` = id
akcji, `.name` = etykieta) oraz `ActionInput(id=..., data=...)`.

Bez niego 4 z 7 testów kończy się `ModuleNotFoundError` — i to jest jedyny powód,
dla którego nie przechodzą. Nie jest to błąd logiki v13.1.

```bash
cd /tmp/duck-v13-1
PYTHONPATH=/home/user/Pokemon/arc-agi-3/local/v13_verify \
  python3 -m unittest tests.test_winpath -v
# Ran 7 tests ... OK
```

## Testy plan-commit (9/12)

`tests/test_plan_commit.py` importuje `inference.utils.plan_commit` z bundla.
Moduł można wyciągnąć z patcha 0005, który notebook zapisuje do
`/kaggle/duck-extra-03.patch` (komórka 10 `arc3-duck-v13.ipynb`).

Trzy pozostałe testy wymagają `inference.agent.python_tool_sandbox` — prawdziwego
sandboxa z bundla. Tego nie da się zastąpić stubem bez zmiany tego, co test
mierzy, więc **zostają niesprawdzone offline** i tak są opisane w raporcie.

## Czego ten katalog nie udowadnia

- Że kod działa w środowisku Kaggle (RTX PRO 6000, SGLang Pennyroyal).
- Że `init`-hashe playbooka zgadzają się z klatkami prawdziwego silnika. To
  wymaga uruchomienia gry; patrz sekcja 4 raportu (ryzyko cichej awarii).
- Żadnych pomiarów wydajności ani wyniku.
