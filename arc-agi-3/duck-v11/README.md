# arc3-duck-v11 — kandydat na slot (NIE wysłany; czeka na GO usera)

Baza: `duck-c45` — notebook, który **realnie zadziałał na Kaggle** (smoke COMPLETE,
log „harness patch applied successfully", 10 gier). v11 dokłada dwie rzeczy
i naprawia jedną, każdą osobno przełączalną:

| zmiana | gdzie | domyślnie |
|---|---|---|
| fix `concurrency=120` → `ARC3_TRUE_CONCURRENCY` (rerun c45 = 0.00) | komórka solvera | **10** |
| `commit(plan)` + eskalacja (patch `0005-plan-commit`, 4 pliki) | `duck-extra-03.patch` | **OFF** (`PLAN_COMMIT="0"`) |
| komórka pomiarowa (jak v9, zero tokenów) | koniec notebooka | zawsze |

## Dlaczego nie v10 (pakiet e499c604)?

v10 przebudowuje cały patch harnessu (660 KB z drzewa da-fr). U nas ten patch
**nie aplikuje się na drzewo bundle** (`git apply` pada na `Makefile:40`
i `README.md:1` — dryf kontekstu względem da-fr), a aplikacja w notebooku jest
atomowa z `check=True`. v11 bierze z v10 tylko wartość — `commit()` i eskalację —
jako minimalny diff (19,7 KB) na łańcuchu patchy, który na Kaggle działa.
Chunkowanie patcha z sha256 (dobra inżynieria z v10) można przejąć później;
diagnoza „v9 by nie ruszyło" jest obalona (patrz DECYZJA.md).

## Przełącznik (komórka 2)

- `PLAN_COMMIT = "0"` — kontrola: zachowanie identyczne z c45 poza fixem
  concurrency. Pierwszy slot v11, jeśli chcemy czysty pomiar samego fixa.
- `PLAN_COMMIT = "1"` — `commit(plan)` z `expect` per krok + dyrektywa
  eskalacyjna co 60 akcji na niedokończonym poziomie.
- Jedna zmiana na slot. Bramka: liczba ukończonych poziomów i score,
  nie a/call (koreluje odwrotnie: ls20 13,89 → 3,27 pkt; su15 1,85 → 56,42).

## Weryfikacja offline (powtarzalna)

```
python3 tools/build_v11.py            # odtwarza notebook z src/base-c45.ipynb (bajt-determinist.)
python3 tools/verify_v11.py --bundle <katalog r033 bundle> --tests
```

Wynik u nas: **ALL CHECKS PASSED** — notebook się buduje odtwarzalnie,
wszystkie 5 patchy aplikuje się na czysty bundle, drzewo kompiluje,
**12/12 testów `commit()`** przechodzi (w tym integracyjne przez sandbox),
przełącznik rozwiązuje się poprawnie w obu pozycjach, metadana zgodna.

## Czego to nie dowodzi

Zachowania na żywym gatewayu ani zysku punktowego `commit()`. Rerun c45 (0.00)
naucza, że ścieżka TRUE_SUBMISSION różni się od smoke — dlatego fix concurrency
jest domyślny, a `commit()` jedzie za osobnym przełącznikiem i bramką.
Pełna synteza i plan slotów: `DECYZJA.md`.
