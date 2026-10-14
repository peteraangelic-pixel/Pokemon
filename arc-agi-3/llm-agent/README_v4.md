# ARC-AGI-3 LLM Agent v4.1

**Wynik v2:** 24.66 (poprawa z 0.01!)
**Cel v4.1:** ~24-32 (realistycznie, na podstawie danych z rejestru)

## Kluczowe ulepszenia v4.1

Na podstawie analizy FAILURES.md i koordynacji z sesją Smak-Domu-Konkurs (v6):

1. **FIELD GUIDE** - klasy celów z GOAL_CATALOG.md:
   - COVER: pokryj wszystkie znaczniki (ar25, re86)
   - REACH: dotrzyj do wszystkich pozycji (bp35, r11l, tu93)
   - COPY: skopiuj wzorzec (cd82, sb26, sk48)
   - REDUCE: zostaw dokładnie 1 element (lf52)
   - PLACE: umieść wszystkie obiekty w strefie (wa30)
   - FLOW: wypełnij wszystkie naczynia (sp80)
   - ALIGN: wyrównaj pozycje według koloru (vc33)

2. **GOAL PERSISTENCE** - jedna gra = jeden warunek wygranej
   - Po rozwiązaniu poziomu 1, zapamiętaj klasę celu
   - Wszystkie poziomy w tej samej grze mają ten sam typ celu

3. **STUCK PROTOCOL** - audyt co 15 akcji po 40 bez ukończenia poziomu
   - Lista hipotez: co zadziałało (✓), co nie (✗)
   - Tani test jednej hipotezy

4. **NOTATION** - model dodaje "notes" do akcji
   - Polityka trzyma ostatnie 4 notatki
   - Wstrzykuje je co turę do promptu

5. **ANTI-DISSERTATION** - max ~60 słów reasoning
   - Batch do 8 akcji naraz
   - Krótkie, konkretne uzasadnienia

## Realistyczna ocena poprawy

**Dlaczego ~24-32, nie 35-45?**

Na podstawie danych z rejestru drugiej gałęzi:
- Poprawki promptowe ruszały wynik o ±1-6 pkt (29.0-30.5 vs 29.5 baseline)
- Sufit z samego rozpoznania celu to ~+7 pkt (z GOAL_CATALOG.md)
- Skok o +10-20 pkt nie pojawił się ani razu w rejestrze

v4.1 ma:
- Field guide (klasy celów) - jedyna dźwignia z twardym uzasadnieniem (43.9 pkt straty w klasie "zły cel")
- Stuck protocol - audyt hipotez
- Notation - zapamiętywanie odkryć
- Anti-dissertation - mniej myślenia, więcej działania

**Oczekiwany pas: ~24-32**
- Przebicie 24.66 realne, nie pewne
- Plan B: przenieść warstwę promptową (field guide/notes/stuck audit) w sprawdzoną rurę Franzena

## Koordynacja z sesją Smak-Domu-Konkurs

**Problem:** v4.1 i v6 (Smak-Domu-Konkurs) niezależnie robią podobne zmiany:
- Field guide / klasy celów
- Notatki gry
- Audyt utknięcia
- Anti-dissertation

**Przy limicie 1 zgłoszenia/dzień nie ma sensu mierzyć dwa razy tego samego.**

**Propozycja koordynacji:**
1. Po powrocie GPU (~17.10): 3 × 2h testy na 25 grach
   - v4.1 (nasza wersja)
   - v6 (Smak-Domu-Konkurs)
   - baseline Franzena
2. Porównanie wyników
3. Zgłoszenie tylko zwycięzcy

## Jak uruchomić lokalnie (LM Studio)

```bash
# 1. Uruchom LM Studio z modelem 7-8B (np. Qwen2.5-7B)
#    Ustaw serwer na http://localhost:9000/v1

# 2. Ustaw zmienne środowiskowe
export LLM_BASE_URL="http://localhost:9000/v1"
export LLM_MODEL="qwen2.5-7b"
export OPENAI_API_KEY="dummy"

# 3. Uruchom agenta
python3 run_local_v4.py
```

## Jak uruchomić na Kaggle

**UWAGA:** Nie uruchamiaj GPU ani zgłoszeń bez rezerwacji w issue #1!

```bash
# 1. Zbuduj notebook
python3 build_notebook_v4.py arc-agi-3-llm-agent-v4.ipynb

# 2. Zarezerwuj w issue #1 (koordynacja sesji)
# Komentarz: "Rezerwuję GPU na 2h testy v4.1"

# 3. Wyślij na Kaggle
kaggle kernels push -p .

# 4. Po zakończeniu runu, kliknij "Submit to Competition" w UI
```

**Alternatywa:** Użyj workflow `arc3-ops.yml` z dispatchem w `ops/request.json`:
```bash
# Stwórz request.json
echo '{"operation": "test_v4", "games": 25}' > arc-agi-3/duck/ops/request.json
git add arc-agi-3/duck/ops/request.json
git commit -m "dispatch: test v4.1"
git push

# Workflow uruchomi testy, wyniki dostaniesz jako commit "ops: results"
```

## Status

- ✅ Notebook v4.1 zbudowany
- ✅ Field guide z klasami celów
- ✅ Stuck protocol
- ✅ Notation system
- ⏳ Testy lokalne (wymaga LM Studio)
- ⏳ Testy na Kaggle (wymaga rezerwacji GPU w issue #1)
- ⏳ Koordynacja z v6 (Smak-Domu-Konkurs)

## Pliki

- `llm_policy_v4.py` - polityka z field guide i stuck protocol
- `build_notebook_v4.py` - buduje notebook Kaggle
- `run_local_v4.py` - uruchamia lokalnie z LM Studio
- `README_v4.md` - dokumentacja (ten plik)
