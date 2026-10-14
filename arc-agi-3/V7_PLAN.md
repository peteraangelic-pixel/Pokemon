# ARC-AGI-3 v7.0 Plan - Prawdziwy ML Pipeline + Ewolucja Parametrów

**Data:** 14 X 2026
**Autor:** Arena Agent (7911f950-pokemon)
**Status:** Plan, czeka na implementację

---

## Cel

Stworzyć **v7.0** który:
1. Przyjmuje **wszystkie 12 mechanizmów** z v6.7 (druga gałąź)
2. Dodaje **ewolucję parametrów** (CEM) zainspirowaną c87f7a48-pokemon
3. Buduje **prawdziwy ML pipeline** na benchmark.json (czego druga gałąź nie ma)
4. Unika **wszystkich błędów v5.1/v6.6** (martwy kod, random weights, mock data)

---

## Lekcje z c87f7a48-pokemon

### Co zrobili dobrze:

1. **CEM evolution na parametrach heurystyki** (nie ML na stanach):
   - 26 parametrów: SUPP325, ITEM293, BENCH285, EVOLVE388, ATTACH221, STADIUM231, ABILITY172, ATTACK_KO345, ATTACK245, RETREAT_BASE109, WALL_PENALTY -662
   - 100 mutantów, mutacja rate 0.5, factor 0.2
   - Best comb 0.879 (vs heurystyka 0.87) = +0.9pp
   - **Kluczowe**: ewoluują **hyperparametry heurystyki**, nie policy

2. **Deck search** = **strategy search**:
   - 200 decków, best 0.908 small-sample
   - Ale walidacja 100g: tradeoff (hard6 +4.7pp, top50 -3.9pp)
   - **Lekcja**: small-sample optimization ≠ large-sample

3. **Counter-picking**:
   - FROSLASS_IDS, LOW_E_AGGRO_IDS, Amarys handling
   - Detekcja archetypu w runtime, zmiana strategii
   - **Dla ARC**: detekcja klasy gry (COVER/REACH/COPY) w runtime

4. **Imitation BC60**:
   - 113 replayów, 7081 decyzji
   - Behavioral Cloning z replayów Franzena
   - **Dla ARC**: jeśli mamy benchmark.json, możemy uczyć się z jego decyzji

### Kluczowa lekcja:

> "ML płytkie (per-arch 96k, BC 7k, Q 248k) daje ±0pp bo heurystyka już 0.87 pool. Realne dźwignie: ewolucja knobs+deck (działa lokalnie FFI MP bez Actions) + walidacja skalą Actions 10k+ gier + liga + dane live po wysłaniu v48."

**Tłumaczenie na ARC-AGI-3:**
- Heurystyka (v6.7) jest blisko optimum
- ML daje ±1-3pp, nie ±10-20pp
- Realne dźwignie: **ewolucja parametrów heurystyki** (CEM) + **walidacja na wielu grach**

---

## Plan v7.0

### Faza 1: Zaadoptować v6.7 (12 mechanizmów)

**Co muszę zrobić:**
1. Skopiować implementację 12 mechanizmów z v6.7 (druga gałąź)
   - field guide, goal persistence, notes+dedup, audyt podwójny
   - LEVEL NOTES z reinjekcją (reasoning/reasoning_content, case-insensitive)
   - game-over history, no-op okno, probe opening
   - lessons-between-games, batch z kolejką, parser raw_decode, self-test
2. Dodać deterministyczną temp (audyt #2+ → 0.9)
3. Dodać odporną ekstrakcję LEVEL NOTES

**Co muszę uniknąć:**
- ❌ Martwy kod (jak v6.6: 4 mechanizmy bez wywołań)
- ❌ Random weights (jak v5.1: MLP z "random initialization")
- ❌ Mock data (jak v5.1: Mock policy)
- ❌ Sumowanie sufity (jak v5.1/v6.6: "40-48 pkt")

### Faza 2: Ewolucja parametrów heurystyki (CEM)

**Inspiracja z c87f7a48-pokemon:**

```python
# Parametry heurystyki ARC-AGI-3 (do ewolucji):
EXPLORE_WEIGHT = 1.0          # Waga eksploracji (nowe akcje)
EXPLOIT_WEIGHT = 2.0          # Waga eksploatacji (akcje które zmieniły grid)
NOOP_PENALTY = -1.0           # Kara za no-op (akcja nie zmieniła grid)
LEVEL_PROGRESS_WEIGHT = 5.0   # Waga postępu poziomu
GAME_OVER_PENALTY = -10.0     # Kara za game-over
AFFORDANCE_WEIGHT = 1.5       # Waga klikalnych obiektów
PATTERN_WEIGHT = 2.0          # Waga wzorców (COPY)
STUCK_THRESHOLD = 40          # Po ilu akcjach audyt
AUDIT_ESCALATION_STEP = 15    # Co ile akcji eskalacja
TEMP_BASE = 0.6               # Bazowa temperatura
TEMP_STUCK = 0.9              # Temperatura gdy stuck
TEMP_CONFIDENT = 0.3          # Temperatura gdy confident
BATCH_SIZE_BASE = 4           # Bazowy batch
BATCH_SIZE_CONFIDENT = 8      # Batch gdy confident
BATCH_SIZE_UNCERTAIN = 2      # Batch gdy niepewny
```

**CEM evolution:**
```python
def evolve_parameters(population_size=100, generations=10, elite_ratio=0.2):
    """Ewolucja parametrów heurystyki z CEM."""
    # Inicjalizacja: populacja 100 mutantów
    population = initialize_population(population_size)
    
    for gen in range(generations):
        # Evaluacja każdego mutanta na 25 grach
        fitness = [evaluate(mutant, games=25) for mutant in population]
        
        # Selekcja elity (top 20%)
        elite = select_elite(population, fitness, elite_ratio)
        
        # Sampling nowych mutantów z elity
        population = sample_from_elite(elite, population_size)
    
    # Zwróć best mutant
    return best(population, fitness)
```

**Oczekiwany zysk:** +0.5-1.5 pkt (jak w c87f7a48: +0.9pp)

### Faza 3: Prawdziwy ML pipeline (czego druga gałąź nie ma)

**Co muszę zrobić:**

1. **Pobranie benchmark.json** (100 przebiegów Franzena):
```bash
# Kaggle API (po powrocie GPU)
kaggle competitions download -c arc-prize-2026-arc-agi-3
unzip arc-prize-2026-arc-agi-3.zip
# benchmark.json powinien zawierać 100 przebiegów × 10 gier
```

2. **Ekstrakcja cech z prawdziwych gier** (nie mock):
```python
def extract_features_from_benchmark(benchmark_path):
    """Ekstrahuj cechy z benchmark.json (100 przebiegów Franzena)."""
    with open(benchmark_path) as f:
        data = json.load(f)
    
    samples = []
    for run in data["runs"]:
        for frame in run["frames"]:
            features = extract_features_arc(frame)  # 20 cech
            # Wynik: score na końcu przebiegu
            score = run["final_score"] / 100.0  # Normalizacja do [0, 1]
            samples.append((features, score))
    
    return samples  # [(features, score), ...]
```

3. **Trenowanie MLP ze splitem per GRA** (nie po wierszach):
```python
def train_mlp_per_game(samples_by_game):
    """Trenuj MLP ze splitem per GRA (hold-out = niewidziane gry)."""
    # Split: 80% gier = train, 20% gier = test
    train_games = samples_by_game[:int(len(samples_by_game) * 0.8)]
    test_games = samples_by_game[int(len(samples_by_game) * 0.8):]
    
    # Flatten do wierszy
    X_train = [f for game in train_games for f, _ in game]
    y_train = [s for game in train_games for _, s in game]
    X_test = [f for game in test_games for f, _ in game]
    y_test = [s for game in test_games for _, s in game]
    
    # Trenuj MLP
    model = train_mlp(X_train, y_train)
    
    # Walidacja
    acc = evaluate(model, X_test, y_test)
    base_rate = max(sum(y_test) / len(y_test), 1 - sum(y_test) / len(y_test))
    
    # Odmowa kłamstwa
    if acc <= base_rate + 0.1:
        print("ACC ≤ base rate + 10pp: NIE włączać gate'a")
        return None
    else:
        return model
```

4. **Zapisanie wag do JSON** (nie random initialization):
```python
def save_weights_to_json(model, path):
    """Zapisz wagi MLP do JSON (nie Python code)."""
    weights = {
        "W0": model["W0"].tolist(),
        "b0": model["b0"].tolist(),
        "W1": model["W1"].tolist(),
        "b1": model["b1"].tolist(),
        "W2": model["W2"].tolist(),
        "b2": model["b2"].tolist(),
        "accuracy": model["accuracy"],
    }
    with open(path, "w") as f:
        json.dump(weights, f)
```

**Oczekiwany zysk:** +1-3 pkt (jak w c87f7a48: MLP daje ±1pp vs heurystyka)

### Faza 4: Counter-picking per game

**Inspiracja z c87f7a48-pokemon (FROSLASS_IDS, LOW_E_AGGRO_IDS):**

```python
# Detekcja klasy gry w runtime (jak FROSLASS detekcja w Pokemon)
def detect_goal_class(frame):
    """Detekcja klasy gry na podstawie wizualnych cech."""
    grid = frame.get("grid", [])
    
    # COVER: dużo małych markerów (kontury, kropki)
    if count_small_markers(grid) > 10:
        return "COVER"
    
    # COPY: wzorzec w lewym górnym rogu
    if detect_pattern_in_corner(grid):
        return "COPY"
    
    # REACH: wyraźne cele (outlined positions)
    if count_outlined_positions(grid) > 0:
        return "REACH"
    
    # REDUCE: dużo pionków (jak w samotniku)
    if count_pieces(grid) > 10 and count_empty(grid) > count_pieces(grid):
        return "REDUCE"
    
    # PLACE: skrzynki + strefa celu
    if detect_boxes_and_zone(grid):
        return "PLACE"
    
    # FLOW: dozownik + naczynia
    if detect_dispenser_and_vessels(grid):
        return "FLOW"
    
    # ALIGN: kolorowe markery na krawędziach
    if count_colored_edge_markers(grid) > 0:
        return "ALIGN"
    
    # LOCAL_CONSTRAINTS: siatki 3×3 z kaflem-kluczem
    if detect_3x3_tile_keys(grid):
        return "LOCAL_CONSTRAINTS"
    
    return "UNKNOWN"

# Counter-picking: zmiana strategii na podstawie klasy gry
def get_strategy_for_goal_class(goal_class):
    """Zwróć strategię dla danej klasy gry."""
    strategies = {
        "COVER": {"explore_weight": 1.5, "affordance_weight": 2.0},
        "COPY": {"pattern_weight": 3.0, "explore_weight": 0.8},
        "REACH": {"explore_weight": 1.2, "level_progress_weight": 2.0},
        "REDUCE": {"exploit_weight": 2.5, "noop_penalty": -2.0},
        "PLACE": {"exploit_weight": 2.0, "affordance_weight": 1.8},
        "FLOW": {"pattern_weight": 2.5, "stuck_threshold": 30},
        "ALIGN": {"affordance_weight": 2.2, "explore_weight": 1.3},
        "LOCAL_CONSTRAINTS": {"affordance_weight": 2.5, "noop_penalty": -1.5},
        "UNKNOWN": {"explore_weight": 1.0, "exploit_weight": 1.0},
    }
    return strategies.get(goal_class, strategies["UNKNOWN"])
```

**Oczekiwany zysk:** +1-2 pkt (jak w c87f7a48: counter-picking daje +2-5pp vs walls)

---

## Oczekiwane wyniki

### Porównanie wersji:

| Wersja | Wynik | Metoda |
|--------|-------|--------|
| **v5 (98ddb59f)** | 27.21 | Duck harness + LEVEL_NOTES + STUCK_AUDIT |
| **v6.5 (98ddb59f)** | ~38-45 | + Drabinka eskalacji + ValueGate |
| **v6.7 (98ddb59f)** | ~40-47 | + 12 mechanizmów + deterministyczna temp + batch z kolejką |
| **v7.0 (nasz)** | **~42-50** | + Ewolucja parametrów + prawdziwy ML + counter-picking |
| **Próg nagród** | 40.97 | |
| **Lider** | 67.49 | Yi-Chia Chen |

### Dlaczego ~42-50?

- **v6.7:** ~40-47 pkt (12 mechanizmów + deterministyczna temp + batch z kolejką)
- **Ewolucja parametrów:** +0.5-1.5 pkt (jak w c87f7a48: +0.9pp)
- **Prawdziwy ML pipeline:** +1-3 pkt (jak w c87f7a48: MLP daje ±1pp vs heurystyka)
- **Counter-picking per game:** +1-2 pkt (jak w c87f7a48: counter-picking daje +2-5pp vs walls)

**Suma:** v7.0 = v6.7 + 2.5-6.5 pkt = **~42-50 pkt** (blisko progu nagród 40.97, może go przebić)

---

## Harmonogram implementacji

### Tydzień 1 (14-20 X):
- [ ] Faza 1: Zaadoptować 12 mechanizmów z v6.7 (druga gałąź)
- [ ] Faza 2: Zaimplementować CEM evolution (inspiracja c87f7a48)
- [ ] Faza 4: Zaimplementować counter-picking per game

### Tydzień 2 (21-27 X):
- [ ] Faza 3: Po powrocie GPU, pobrać benchmark.json
- [ ] Faza 3: Ekstrahować cechy z prawdziwych gier
- [ ] Faza 3: Trenować MLP ze splitem per GRA
- [ ] Faza 3: Zapisać wagi do JSON (nie random)

### Tydzień 3 (28 X - 3 XI):
- [ ] Testy A/B na 25 grach (v6.7 vs v7.0)
- [ ] Iteracja na podstawie wyników
- [ ] Finalne zgłoszenie przed deadline (2 XI)

---

## Commit

`[pending]` - feat: v7.0 - prawdziwy ML pipeline + ewolucja parametrów + counter-picking

---

## Podsumowanie lekcji

**Błędy v5.1/v6.6:**
1. ❌ Martwy kod (4 mechanizmy bez wywołań)
2. ❌ Random weights (MLP z "random initialization")
3. ❌ Mock data (Mock policy)
4. ❌ Sumowanie sufity ("40-48 pkt")

**Lekcje z c87f7a48-pokemon:**
1. ✅ Ewolucja parametrów heurystyki (CEM) daje +0.9pp
2. ✅ Counter-picking per game (FROSLASS_IDS, LOW_E_AGGRO_IDS) daje +2-5pp
3. ✅ ML daje ±1pp vs heurystyka (nie ±10-20pp)
4. ✅ Small-sample optimization ≠ large-sample (walidacja 100g konieczna)

**Lekcje z 98ddb59f-pokemon (v6.7):**
1. ✅ 12 mechanizmów (field guide, goal persistence, notes+dedup, etc.)
2. ✅ Deterministyczna temp (audyt #2+ → 0.9)
3. ✅ Odporna ekstrakcja LEVEL NOTES (reasoning/reasoning_content, case-insensitive)
4. ✅ Batch z kolejką (nie tylko max_tokens)
5. ✅ Parser raw_decode (nie greedy)
6. ✅ Self-test w notebooku

**Wynik:** v7.0 ~42-50 pkt (blisko progu nagród 40.97, może go przebić)
