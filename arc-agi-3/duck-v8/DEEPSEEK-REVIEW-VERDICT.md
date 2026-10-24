# Werdykt: review DeepSeeka 4.1 o pipeline ARC (2026-10-24, sesja Pokemon)

## Twierdzenie 1: submit 400 przez ścieżkę w `-f` — PRAWDA (kod + źródło CLI + dane)
- `ops.py:459` (op_auto_submit): default file = "arc-agi-3/kaggle/results/submission.parquet".
  Uwaga: `op_submit` (ops.py:136) ma POPRAWNY default "submission.parquet" — bug dotyczy
  wyłącznie ścieżki auto-submit/chain.
- Kaggle CLI 2.2.5 (kaggle_api_extended.py:2188-2189): `submit_request.file_name = file_name`
  bez normalizacji; docstring: "the name of the output file created by the kernel".
- Dane z ops/results: 12 submitów ze ścieżką = 12x rc=1 (ostatni: r066, kernel v8);
  2 z samą nazwą = 2x rc=0 (r016 -> 23.94, s201 -> 26.25).
- Zastrzeżenie: wszystkie padające submity miały też KernelWorkerStatus.ERROR
  (fallback_submit). Z samych danych nie da się wykluczyć statusu wersji jako
  współprzyczyny 400. Fix jest jednak darmowy i zgodny z kontraktem API;
  pierwszy submit po fixie robić na wersji COMPLETE (fallback_submit=false) —
  to jednocześnie test rozstrzygający.

## Twierdzenie 2: martwy guard kwoty — PRAWDA z drobną nieścisłością
- duck-original, komórka 14: soft_end=now+40min jest nadpisywane; wartość końcowa
  to NOTEBOOK_START + (max_runtime_s 32400 - 600)s ~= +8.8h. DeepSeek pisze
  "soft_end = None kasuje" — None to tylko krok pośredni; wniosek ten sam:
  guard 40-min nie działa.
- Dowód r050: guard wydrukował soft_end=08:24, a log notebooka obejmuje 8911s
  (~2.5h) dla JEDNEJ gry; sam bm.run bounded przez max_runtime_s_per_game=7920s
  (2h12m — liczba DeepSeeka). Gałąź except dokłada drugi bm.run (+25 min).
- Konsekwencja (s202: quota 30h/tydz. wyczerpana -> push odmówiony) spójna.
- Fix: w gałęzi save-run liczyć soft_end raz, po bloku budżetowym
  (min(now+40min, deadline budżetowy)); TRUE_SUBMISSION zostaje z None.

## Twierdzenie 3: token nie dociera do ops.py — MECHANIZM BŁĘDNY, objaw historyczny
- write_creds.py DOPISUJE KAGGLE_API_TOKEN do $GITHUB_ENV (jest od cb80c48),
  a GitHub Actions udostępnia takie zmienne kolejnym krokom także w kontekście
  env (udokumentowany wzorzec). Krok "Run op" token więc dostaje.
- r014 (401) jest sprzed/z okolic wdrożenia tej rury i dotyczy tylko opsów na
  bezpośrednim API (kernel-info), nie submitów (CLI czyta ~/.kaggle/access_token).
- Usunięcie linii 48 nieszkodliwe, ale niczego nie naprawia. Nie blokuje niczego.

## Kolejność napraw
1. ops.py:459 -> "submission.parquet" (1 linia) + submit testowy na wersji COMPLETE.
2. Guard soft_end przed kolejnymi smoke'ami (odzysk ~2h GPU na smoke).
3. Twierdzenie 3: ignorować / higiena opcjonalna.
