# Status mojej pracy (arena/7911f950-pokemon)

**Data:** 2026-10-13 13:45 UTC

## Najnowsze ustalenia z drugiej gałęzi (13 X 2026)

### 1. Duck harness nie ma licencji ⚠️
- `gh api repos/Tufalabs/duck-harness` → `license: null`
- Nie możemy kopiować ani modyfikować kodu Duck w publicznym repo
- Konsekwencja: każda poprawka ma być własnym kodem (clean-room) albo dotyczyć wyłącznie własnych agentów
- **Poprawione w README llm-agent** (usunięte błędne "MIT")
- Pełny dokument: `arc-agi-3/FINDINGS-2026-10-13.md`

### 2. Pamięć między passami — problem jest w Duck, nie w naszym agencie ✅
- Duck: `_ensure_session` zeruje `_summarized_knowledge` przy zmianie `runtime_dir`
- Duck: nowy `ToolAgent` dla każdego passu, plik stanu kasowany w `finally`
- Nasz `llm-agent`: jeden pass na grę (budżet 400 akcji), `reset_game` czyści wiedzę dopiero przy nowej grze
- **Ten bug u nas nie występuje**

### 3. Zgłoszenie z atrapą (postmortem 11 X) ⚠️
- Zgłoszenie 57075036 oceniono na `placeholder` (score 0.0)
- Notebook zapisał atrapę w fazie "save", a prawdziwa gra wymaga `KAGGLE_IS_COMPETITION_RERUN`
- **Nieustalone:** dlaczego ocena poszła z atrapy
- Do wyjaśnienia przed kolejnym zgłoszeniem

### 4. Sprzęt lokalny
- Użytkownik: GPU z 8 GB VRAM
- Qwen3.6-27B lokalnie nie wchodzi
- Lokalnie realnie: model 7-8B w Q4 do testów pętli agenta
- Pełne przebiegi tylko na Kaggle

## Co jest błędne (usunięte)

### 1. WIN-CONDITION-HYPOTHESES.md ❌
Druga sesja sprawdziła w kodzie gier że:
- "TimerBased: wygrywa, gdy czas się skończy" (ft09, ls20) - **NIEPRAWDA!**
  - W rzeczywistości: licznik to limit kroków, wyzerowanie = przegrana (self.lose())
  - Prawdziwy warunek w ls20 (pbznecvnfr): dotarcie do wszystkich pól docelowych przy spełnionym warunku dopasowania
- "PatternClearing: usuń kolory 8 i 13" (cn04) - **NIEPRAWDA!**
  - W rzeczywistości: łamigłówka z dopasowywaniem kształtów, elementy trzeba obracać i ustawiać tak żeby zakrywały nawzajem zaznaczone pola

### 2. rust-simulator ❌
Druga sesja sprawdziła że:
- To **mock** - nie uruchamia prawdziwych gier
- Warunek wygranej to `agent_actions <= baseline * 2` - nie ma logiki gier
- RHAE scoring był błędny:
  - Limit 1.15 był nałożony na sumę całej gry zamiast na pojedynczy poziom
  - Prawdziwy wzór: osobno dla każdego poziomu, min(115, 100·(base/agent)²), z wagą k dla poziomu k
- Benchmark mierzył szukanie spójnych obszarów na losowych klatkach - nie jest to wąskie gardło

### 3. Główny problem to nie (b) zły cel, ale (a) niezrozumiana mechanika
Druga sesja sklasyfikowała 110 przebiegów (100 Franzena + 10 v2):
- **(a) nowa mechanika niezrozumiana: 6 przypadków** (bp35, ka59, lf52, sp80, g50t, sc25)
- **(b) zły cel: 3 przypadki** (sk48, wa30, v2 ka59)
- **(c) dobry model ale brak rozwiązania: 1 przypadek** (s5i5)
- **(d) pętla: 0 przypadków**

**Wniosek:** Agent nie błądzi i nie kręci się w kółko. Dużo myśli (81k tokenów = 43% budżetu), a mało robi (0.58 akcji na ruch człowieka). Prompt "eksperymentuj więcej" ledwo to ruszył (0.40 → 0.46).

## Co mam (użyteczne)

### 1. Kod źródłowy 25 gier demo ✅
**Lokalizacja:** `arc-agi-3/games/environment_files/`
- Wszystkie 25 gier z kodem Python i metadata.json
- baseline_actions dla każdego poziomu
- Druga sesja może to wykorzystać do budowy GOAL_CATALOG.md

### 2. GAME-CATALOG.md ✅
**Lokalizacja:** `arc-agi-3/games/GAME-CATALOG.md`
- Podstawowe dane: liczba poziomów, baseline_actions, FPS, tags
- Druga sesja może to rozszerzyć o prawdziwe warunki wygranej

### 3. Kod źródłowy gier ✅
**Lokalizacja:** `arc-agi-3/games/environment_files/`
- Wszystkie 25 gier z kodem Python
- Druga sesja sprawdziła w nich prawdziwe warunki wygranej

## Co ma druga sesja (działa)

### 1. play.py ✅
- Uruchamia gry lokalnie na CPU, bez API i bez GPU
- Można testować agenta bez Kaggle

### 2. replay.py ✅
- Odtwarza zapisane przebiegi agenta
- 100/100 zgodnych wyników z przebiegami Franzena
- 110 przebiegów = 40s w Pythonie

### 3. GOAL_CATALOG.md ✅ (w przygotowaniu)
- 8 klas celów: dotrzyj, umieść, pokryj, kopiuj wzorzec, ograniczenia lokalne, zredukuj, przepływ, wyrównaj
- Każda klasa opisana z perspektywy agenta (co widzi na ekranie)
- Zbudowany z 15 gier spoza zestawu testowego
- Każdy warunek sprawdzony w kodzie gry

### 4. FAILURES.md ✅ (w przygotowaniu)
- Klasyfikacja porażek: (a) nowa mechanika 6, (b) zły cel 3, (c) dobry model 1, (d) pętla 0
- Mediana tokenów spalonech na poziomie utknięcia: 81k (43% budżetu)
- Akcje wykonane / ruchy człowieka: 0.58 (duży niewykorzystany zapas)

### 5. Plan zmian w agencie ✅
Dwie zmiany które mogą pomóc z problemem (a):
1. Po wejściu na nowy poziom kod sam wskazuje które obiekty są nowe
2. Kod sam wykonuje 1-3 tanie próby na każdym nowym obiekcie i podaje modelowi tabelę "akcja → co się zmieniło" zanim model zacznie długo myśleć

## Co dalej

### Moja rola:
- Czekam na GOAL_CATALOG.md i FAILURES.md od drugiej sesji
- Mogę pomóc z analizą transkryptów jeśli druga sesja potrzebuje
- Nie uruchamiam GPU ani zgłoszeń bez rezerwacji

### Status v2 submission:
- #57125322 (v2-think-less) - nadal PENDING (competition rerun trwa)
- Spodziewany wynik: ok. 10:00-11:00 czasu polskiego

### Nie uruchamiam Rust:
- Druga sesja powiedziała: "Rust tam gdzie Python jest wolny na actions"
- Na razie takiego miejsca nie ma (110 przebiegów = 40s w Pythonie)
- Rust pomoże tylko jeśli (c) okaże się częstsze niż myślimy

### Następne kroki (z FINDINGS-2026-10-13.md):
1. Wyjaśnić, dlaczego rerun nie zagrał (postmortem), i uszczelnić notebook tak, żeby atrapa nie mogła wyglądać jak wynik
2. ✅ Poprawić README `llm-agent` (usunięte błędne "MIT")
3. Lokalny smoke test agenta z modelem 7-8B (po stronie użytkownika z GPU)

---

**Commity:**
- 7899884 - remove: błędny WIN-CONDITION-HYPOTHESES.md i mock rust-simulator
- 4963162 - update: MY-WORK-STATUS.md - usunąłem błędną pracę, czekam na GOAL_CATALOG.md
