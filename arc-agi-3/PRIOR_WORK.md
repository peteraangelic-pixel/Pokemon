# Co już zostało zrobione w ARC-AGI-3 (repo `riemann`, gałęzie `arena/01a*-riemann`)

**Nie odkrywaj tego koła na nowo.** Właściciel ma drugie repo, w którym we
wrześniu 2026 r. powstał kompletny pipeline ARC-AGI-3. Ten plik jest
skrótem tamtej pracy: co działało, co **nie działało**, i dlaczego wątek
zamknięto.

Repo: `https://github.com/peteraangelic-pixel/riemann`, katalog `arc_agi3/`
(20 plików, 56 testów). Pliki do przeczytania w pierwszej kolejności:
`arc_agi3/EXPERIMENT_LOG.md`, `ARC_AGI3_PLAN.md`, `arc_agi3/README.md`.

## ⚠️ Najpierw: wątek został ZAMKNIĘTY 2026-09-04

`ARC_AGI3_PLAN.md` (status: zamknięty) podaje trzy powody:

1. **Eligibility odpada** — nagrody ARC Prize wymagają open-source (CC0/MIT-0),
   publicznego notebooka, **angielskich write-upów**, a przy wygranej
   weryfikacji przez organizatorów (rozmowy, wyjaśnianie podejścia) i KYC/tax
   przy wypłacie. Właściciel świadomie z tego rezygnuje.
2. **Szanse na leaderboard uznane za znikome** — lider Kaggle ARC-AGI-3 miał
   ~7.5% (stan na 2026-08-31); zwycięzcy Milestone #1 to zespoły z lokalnymi
   LLM (Qwen 27B / Gemma 31B) + pamięcią.
3. **Ściana mechaniki** w diagnostyce (niżej).

**Rozstrzygnięcie tej sprzeczności:** tamta decyzja dotyczyła nagród
**ARC Prize Foundation** (Grand Prize $700K za 100% — nieosiągalny, przechodzi
na 2027). Konkurs **Kaggle** (`arc-prize-2026-arc-agi-3`) to osobna torba
pieniędzy: **$75 000 dla top 5**, ocena wyłącznie wynikiem, **bez write-upu i
bez rozmowy**. To, czy KYC przy wypłacie nadal odpada, jest pytaniem do
właściciela — ale write-up/rozmowa, czyli punkt 1, na Kaggle nie występują.

## Agent z `riemann` — czym jest

**Deterministyczny baseline bez modelu.** Brak inference, brak providera API,
brak GPU — celowo, bo ewaluacja na Kaggle biegnie bez internetu. Eksploracja
nowości: mały graf stanów + heurystyki wizualne (rzadkość kolorów, rozmiar
komponentu, ostatnio zmienione piksele; weryfikacja ruchu odwrotnego przed
zejściem w głąb; rozpoznawanie labiryntu z kafelków; dopasowywanie badge'a do
glifu pod obrót o 90° i relabeling palety; nauka wyczerpujących się liczników).

**To nie jest podejście, które my planujemy.** My celujemy w zarządzanie
kontekstem + percepcję przy modelu LLM. Ich kod jest więc użyteczny jako
**pipeline i diagnostyka**, nie jako polityka.

## Twarde wyniki negatywne — NIE POWTARZAJ

Scorecard zamarznięty na **5.3585** przez 15+ ewaluacji (ls20 poziom 2
`NOT_FINISHED`, vc33 poziom 1 `NOT_FINISHED`).

1. **Nie blokuj kafelków na podstawie samego wymuszonego przemieszczenia
   awatara.** Próba z `811d6f5` dodała blokowanie kafli powodujących
   *forced avatar displacement* — agent wypadł z nawigacji, zginął 3× zamiast
   2×, wynik bez zmian. **Wycofane w `73d5f2f`.** Przemieszczenie to może być
   zwykły teleport lub mechanika sterowania, nie dowód śmierci.
2. **Guardy terminal-landing działają, ale nie wystarczą.** Zatrzymanie
   kafelków, na których skończył się poziom (`GAME_OVER`), po ≥1 zgonie: nauczył
   się **8 różnych śmiertelnych kafli** (`learned: 8`, `rerouted: 818`,
   9 zgonów) i **nadal nie ukończył ls20 poziomu 2 nawet w 1200 akcjach**.
   **Wniosek: plateau ls20 to ściana mechaniki, nie artefakt budżetu.**
   Omijanie śmiertelnych kafli pojedynczo nigdy nie ukończy poziomu — trzeba
   zrozumieć, *dlaczego* interakcje w strefie badge/control zabijają.
3. **Budżet akcji jest ciasny z powodu geometrii, nie limitu:** każda próba
   poziomu 2 w ls20 kosztuje **~133 akcje** samo podejście korytarzem, więc
   400-akcyjny przebieg mieści tylko ~3 próby, a trzecia jest ucinana po ~80
   krokach.
4. **vc33 poziom 1: zero rozpoznanej mechaniki.** 394 z 400 akcji to
   `graph-click-frontier`; agent umiera od klikania w krawędzie. Najpierw
   trzeba zrozumieć, jaka wizualna właściwość w tej grze w ogóle powinna być
   klikana.
5. **Feedback terminalny nie jest zachowywany między resetami.** Agent po
   każdym `GAME_OVER` powtarza identyczną trasę i identyczną fatalną decyzję.

## Infrastruktura do wzięcia (działa, przetestowana)

- `arc_agi3/Makefile` — `configure-kaggle` / `setup` / `test` / `list-games` /
  `play-local` / `verify-local` / `evaluate-public` / `notebook` / `submit` /
  `status` / `clean`. Python **3.12+** (wymóg pakietu `arc-agi`).
- `scripts/configure_kaggle.py` — kopiuje `key` z rootowego `kaggle.json` do
  ignorowanego `.kaggle/access_token` (mode 600), **nigdy go nie drukuje**.
- `scripts/build_notebook.py` — generuje notebook pod `ACCELERATOR=cpu|t4|p100|rtx6000`.
- `.github/workflows/arc-agi3.yml` — testy offline zawsze; realne odpalanie
  gier publicznych **tylko** na marker `[arc-smoke]` / `[arc-eval]` w
  wiadomości commita albo ręcznym dispatchu. Nigdy na harmonogramie.
- **Wyniki publikowane jako GitHub Check** (`scripts/publish_check_summary.py`)
  — obok komitowania wyników to jedyny kanał czytelny z sandboxa.

## Ograniczenia, o których trzeba pamiętać

- **Kaggle pozwala na jedno oficjalne zgłoszenie dziennie.** `make submit` tylko
  wypycha notebook do fazy *Save & Run All*; kliknięcie *Submit to Competition*
  to osobna, świadoma czynność.
- Kernel metadata jest domyślnie prywatne.
- Ten agent (bez modelu) to realnie **~0–1% w metryce RHAE** — to nie jest
  punkt startu do nagród, tylko do nauki mechaniki gier.

## Co z tego bierzemy

1. **Infrastrukturę Kaggle** (sekcja sekretów, pobieranie wyników, replaye) —
   wzorzec jest już przeniesiony do `.github/workflows/arc-agi-3-kaggle.yml`.
2. **Konkretne hipotezy do sprawdzenia** na prawdziwym agencie: czy ściana
   ls20/vc33 znika, gdy wchodzi model z pamięcią, czy pozostaje. To jest
   testowalne i tanie.
3. **Ostrzeżenie o budżecie:** ~133 akcje na podejście w ls20 oznacza, że przy
   limicie akcji liczy się każda próba. Nasz nacisk na redukcję zmarnowanych
   akcji jest tu trafiony — ale to nie wystarczy, jeśli mechanika nie będzie
   zrozumiana.
