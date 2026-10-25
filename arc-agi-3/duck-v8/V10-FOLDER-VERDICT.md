# Folder `arc-agi-3/e499c604-…/` (pakiet v10, inna sesja) — werdykt po inspekcji

Data: 25.10.2026. Obiekt: folder `e499c604-b61e-4a81-b5ea-33f729bccc1f/` na tipie Smak `698de64`
oraz stan operacyjny Smak do `a6cede8` (r080). Wszystko poniżej uruchomiłem/przeliczyłem sam.

## Stan operacyjny (kontekst, z ops/results Smak)

- Smoke c45 (r076, prawdziwy output z Kaggle): **26,78** śr. — poniżej bramki v3 smoke 29,02.
  Zyski: cn04 71,4 / m0r0 46,3 / ka59 49,9; regresy: su15 13,3 (z 56,4), sc25 17,1, dc22 27,7.
  Hipoteza sesji Smak: cap 45k tnie długie poziomy. Jedna obserwacja, bez A/B — hipoteza, nie fakt.
- Submit c45 `57629847`: nadal **PENDING** (r080, 14:50 PL). Best COMPLETE nadal 26,25 (v3).
- Kernel v9 v1 wypchnięty (r079, po dwóch nieudanych próbach r077/r078); outputu jeszcze nikt nie ściągnął.
- **BEZPIECZNIK (user 25.10)**: sesja Smak ma zakaz push/submit bez GO; auto-decyzja 26.10 zawieszona.

## Główne twierdzenie v10 („v9/v7 by nie ruszyły") — FAŁSZ na Kaggle, prawda lokalnie

- Komórka patcha 498 799 znaków jest **bajt-identyczna** w duck-v7, duck-c45 i duck-v9
  (sha256 `6fdcd1ae…`, zweryfikowane). Wyekstrahowana wprost i puszczona przez `git apply`
  (git 2.39.5) daje `corrupt patch at line 10086` — odtwarzalne; przyczyną jest brak końcowego `\n`
  (z dodaną linią patch aplikuje się w całości).
- Ale: **c45 z tą samą komórką realnie zadziałał na Kaggle** — `arc3-duck-c45.log:53`
  w r076: „harness patch applied successfully", potem 3 patche extra i 10 gier z benchmarkiem.
  Platforma Kaggle najwyraźniej dostarcza brakujący newline przy wykonaniu. Katastrofa zapowiadana
  w README v10 („każdy slot na v9 spaliłby się w ~2 minuty") **nie występuje w prawdziwym środowisku**.
- Zysk z „kompletności" jest behawioralnie ~zerowy na ścieżce notebooka: po zbudowaniu obu drzew
  `segmentation.py` jest **identyczny** (252 linie), `solver.py` identyczny; pełny patch dokłada tylko
  `CONFIGURATION.md`, `Makefile`, `README.md` i `viewer/*` (UI diagnostyki) — nic, co zmienia grę.

## Sam pakiet v10 — co się broni

- `verify.py` (statyczny): ALL PASSED u mnie; kawałki składają się bajt w bajt, sha256 zgodne z `ARC3_VARIANT`.
- Patch 0010 realnie ma 660 020 B / 24 pliki (wszystkie pod `ARC3-Inference/*`).
- **Testy `commit()`: 12/12 OK** na spatchowanym drzewie (po doinstalowaniu requests/pillow/pydantic;
  w tym 3 prawdziwe testy integracyjne przez sandbox). Bench odtwarza liczby autora:
  3,7 ms/akcję przy pustej historii, 148,6 ms przy 200 przejściach.
- Implementacja `commit()` jest prawdziwa: krok po kroku, `expect` vs realna klatka, stop na mismatch /
  zmianie poziomu / game over / `max_actions`. Eskalacja i addendum promptu są bramkowane
  `ARC3_PLAN_COMMIT=1`, więc profil `c45` jest kodowo czysty. `ZIP` = oryginały autora (SHA256SUMS 7/7 OK);
  kopie folderowe mają CRLF po uploadzie webowym (sumy niezgodne, semantyka zachowana).

## Wady krytyczne przed jakimkolwiek pushem

1. **Patch v10 NIE aplikuje się na drzewo bundle (proxy Kaggle r033)**: `git apply` pada na
   `Makefile:40` i `README.md:1` (dryf kontekstu względem da-fr: linia `RE_ARC_ENVIRONMENTS_DIR`).
   Aplikacja w notebooku to `check=True` bez wyjątków i git apply jest atomowy → kernel v10 umarłby
   w komórce środowiskowej dokładnie tak, jak autor przewidział dla v9 — gdyby żywy dataset = r033.
   Ich `verify --pristine` przechodził na ich własnym drzewie da-fr, nie na bundle. Naprawa:
   regeneracja diffa na bundle-copy albo `--exclude` tych dwóch plików (oba pozaruntime'owe).
   Do weryfikacji na żywym datasecie przed pushem.
2. **`PROFILE = "plan"` jest domyślny** w wysłanym notebooku, mimo że ich własny plan mówi:
   pierwszy slot = kontrola `c45`. Push as-is = eksperyment `plan` z trzema zmianami naraz.
   Przestawić na `c45` przed slotem kontrolnym.
3. Obcy artefakt w korzeniu folderu: `01a1273f-…patch` (4 905 linii, projekt „culture-bridge"/Render) —
   niezwiązany z ARC, do usunięcia; nie jest częścią `arc-v10/`, ale zaśmieca folder sesji.
4. Ryzyko znane z historii: eskalacja wymuszająca procedurę `model_state/model_step` przypomina
   warstwę world-model z v5/v6, która na LB kosztowała (23,94 < 24,66 < 26,25). Sam `commit()` jest
   bezpieczniejszy (tylko weryfikacja), ale to hipoteza do pomiaru, nie zaleta z dowodem.

## Werdykt

v10 to rzetelnie wykonany pakiet z jedną prawdziwą nowością (`commit()`), ale jego główny argument
sprzedażowy („ratuje sloty, które v9 by spalił") jest empirycznie fałszywy, a sam wymaga dwóch
poprawek (apply na bundle, domyślny profil), zanim w ogóle może lecieć. Kolejność bez zmian:
wynik c45 (PENDING) → decyzja usera → ewentualnie v10 z `PROFILE=c45` jako kontrola.
Nic nie wysyłam; BEZPIECZNIK usera obowiązuje.
