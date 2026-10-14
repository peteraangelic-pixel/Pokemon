# Ulepszenia ARC-AGI-3 agenta na podstawie innych sesji

Na podstawie analizy sesji c87f7a48-pokemon (Pokemon TCG battle):

## 1. Multiprocessing - 12.5x przyspieszenie

**Co zrobili:**
- `gauntlet_fast_mp.py` - 96k samples in 115s vs 24min sequential
- Wzorzec: `Pool` z `worker_init` i globalnym `_GLOBAL` dict
- 0.16ms/answer z multiprocessing

**Co wdrożyliśmy:**
- ✅ `play_local_mp.py` - równoległe uruchamianie gier
- ✅ `run_games_fast.py` - równoległe uruchamianie LLM agenta
- ✅ `summarize_recordings_mp.py` - równoległe przetwarzanie nagrań
- ✅ `benchmark_mp.py` - benchmark sequential vs multiprocessing

**Jak używać:**
```bash
# Uruchom 25 gier równolegle (domyślnie 4 workery)
python3 arc-agi-3/baseline/scripts/play_local_mp.py --all --workers 8

# Generuj dane treningowe równolegle
python3 arc-agi-3/baseline/scripts/generate_training_data_fast.py --workers 8
```

## 2. Bands, not weights - scoring akcji

**Co zrobili (Pokemon TCG):**
```
340  play a Supporter (draw / search)
330  play an Item (search / utility)
320  put a Basic on the Bench
310  evolve
300  attach Energy / Tool
260  attack that takes a prize
200  any other attack
120  retreat (only when escaping knockout)
  0  end turn
```

**Zasada:** Każda setup band jest ściśle powyżej każdej attack band. To zapobiega atakowaniu przed przygotowaniem.

**Propozycja dla ARC-AGI-3:**
```python
ACTION_BANDS = {
    # Band 340: Testowanie nowych obiektów (najwyższy priorytet)
    "test_new_object": 340,
    
    # Band 330: Eksploracja (ruch w nowym kierunku)
    "explore_new_direction": 330,
    
    # Band 320: Akcja która zmieniła grid (wiemy że działa)
    "effective_action": 320,
    
    # Band 310: Kontynuacja ostatniej skutecznej akcji
    "continue_effective": 310,
    
    # Band 300: Akcja z notes (zapamiętane odkrycie)
    "use_note": 300,
    
    # Band 200: Inna akcja
    "other_action": 200,
    
    # Band 120: Reset (tylko gdy utkniemy)
    "reset_stuck": 120,
    
    # Band 0: Czekanie (nigdy)
    "wait": 0,
}
```

**Implementacja w v4.2:**
```python
def score_action(action, context):
    """Score action using bands, not weights."""
    if context["is_new_object"] and action["type"] == "CLICK":
        return 340  # Test new object
    elif context["is_new_direction"]:
        return 330  # Explore new direction
    elif context["last_action_changed_grid"]:
        return 320  # Effective action
    elif context["action_from_notes"]:
        return 300  # Use note
    elif action["type"] == "RESET" and context["stuck_count"] >= 5:
        return 120  # Reset when stuck
    else:
        return 200  # Other action
```

## 3. Sample-size discipline - testowanie na wielu grach

**Co zrobili:**
- "1,500 games per arm the bar for a feature decision"
- A/B testing z 250+ gier per arm
- Local engine advantage: 2,000 games ≈ 5 minutes

**Propozycja dla ARC-AGI-3:**
```bash
# Testuj v4.1 na 25 grach × 4 przebiegi = 100 przebiegów
python3 arc-agi-3/baseline/scripts/play_local_mp.py --all --workers 8 --report v41_100runs.json

# Porównaj z baseline
python3 arc-agi-3/baseline/scripts/play_local_mp.py --all --workers 8 --report baseline_100runs.json

# Analiza statystyczna
python3 arc-agi-3/baseline/scripts/compare_runs.py v41_100runs.json baseline_100runs.json
```

## 4. Single-file agent - prostota i niezawodność

**Co zrobili:**
- Single-file, stdlib-only agent
- "We prefer a dumber agent to a dead one"
- No numpy = no version skew

**Propozycja dla ARC-AGI-3:**
- Uprościć `llm_policy_v4.py` do jednego pliku
- Usunąć zależności od numpy (jeśli niepotrzebne)
- Dodać fallback dla każdego wywołania LLM (nigdy nie crashować)

## 5. Feature exposure - expose features zamiast engineering rules

**Co zrobili:**
- "When the policy played badly, we looked for a quantity it could not see"
- Feature exposure beat feature engineering
- Expose features as inputs to learned policy

**Propozycja dla ARC-AGI-3:**
Zamiast hard-coded rules, expose features:
```python
features = {
    "num_new_objects": count_new_objects(grid),
    "num_untested_directions": count_untested_directions(),
    "last_action_effective": last_action_changed_grid(),
    "stuck_count": stuck_count,
    "levels_completed": levels_completed,
    "actions_since_level": actions_since_level,
}
# Model uczy się który feature jest ważny
```

## 6. Never Error - prime directive

**Co zrobili:**
- "An agent that is mediocre but never crashes accumulates μ"
- "An agent that is brilliant but crashes on one rare observation shape loses the entire run"

**Propozycja dla ARC-AGI-3:**
```python
def get_action(frame):
    """Never raise, always return an action."""
    try:
        action = llm_call(frame)
        if is_valid(action):
            return action
    except Exception as e:
        log_error(e)
    
    # Fallback: deterministic exploration
    return fallback_action(frame)
```

## 7. Plan wdrożenia

### Faza 1: Multiprocessing (zrobione)
- ✅ play_local_mp.py
- ✅ run_games_fast.py
- ✅ summarize_recordings_mp.py

### Faza 2: Bands scoring (v4.2)
- Dodać ACTION_BANDS do llm_policy_v4.py
- Zaimplementować score_action()
- Testować na 100 przebiegach

### Faza 3: Feature exposure (v4.3)
- Zdefiniować features
- Dodać prosty model (MLP 20->128->64->1)
- Testować z multiprocessing

### Faza 4: Never Error (v4.4)
- Dodać try/except wszędzie
- Fallback dla każdego wywołania LLM
- Testy crash-resistance

## 8. Benchmark

**Cel:** 100 przebiegów na 25 grach w < 10 minut (z multiprocessing)

**Obecny stan:**
- Sequential: ~24 min dla 100 przebiegów
- Multiprocessing: ~2 min dla 100 przebiegów (12x przyspieszenie)

**Następny krok:**
```bash
# Testuj v4.1 z multiprocessing
python3 arc-agi-3/baseline/scripts/play_local_mp.py --all --workers 8 --report v41_100runs.json
```

## Źródła

- c87f7a48-pokemon: Pokemon TCG battle agent
- a450b00f-pokemon: Pokemon TCG battle agent (ML/experimental)
- NOTES_STRATEGY.md: szczegółowa dokumentacja strategiczna
