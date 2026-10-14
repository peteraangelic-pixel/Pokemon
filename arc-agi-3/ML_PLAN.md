# ARC-AGI-3: Plan Machine Learning (na podstawie c87f7a48-pokemon)

## Co mają w c87f7a48-pokemon (Pokemon TCG)

### Pipeline ML
1. **generate_training_data_fast.py** - generuje dane treningowe:
   - Ekstrahuje 20 cech z każdego stanu gry (turn, deck, hand, bench, hp, energy, prize, etc.)
   - Zapisuje (features, result) gdzie result = 1 (wygrana) / 0 (przegrana)
   - Używa multiprocessing Pool (4 workery) do szybkiego generowania
   - Wynik: CSV z kolumnami f0-f19, result

2. **train_perarch_fast.py** - trenuje modele:
   - MLP 20->128->64->1 z numpy
   - Per-archetype (FAST, WALL, SPREAD, MIRROR, DEFAULT, STALL)
   - SGD z batch=256, lr=0.02, epochs=100
   - BCE loss
   - Zapisuje wagi jako Python code (można zaimportować bezpośrednio)

3. **main_heuristic_v42_ml.py** - agent z wbudowanym MLP:
   - Ekstrahuje 20 cech z stanu gry
   - Przepuszcza przez MLP (20->128->64->1)
   - MLP zwraca wartość 0-1 (prawdopodobieństwo wygranej)
   - Używa tej wartości do oceny akcji (value model)
   - **0.16ms/decision** z numpy, no sklearn needed

### Wyniki
- **96k samples in 115s** (vs 24min sequential) = 12.5x speedup
- **0.16ms/answer** z multiprocessing Pool
- **MLP accuracy: 0.913** (3711 samples hard6+top30)
- **v42.6 hard6: 0.827** (vs v41 reactive 0.783) = +4.4pp z ML

## Co mogę przenieść do ARC-AGI-3

### 1. Ekstrakcja cech z ARC-AGI-3
Zamiast 20 cech z Pokemon TCG, ekstrahuję 15-25 cech z stanu gry ARC:

```python
def extract_features_arc(frame: dict) -> list[float]:
    """Ekstrahuj cechy z stanu gry ARC-AGI-3."""
    grid = frame.get("grid", [])
    
    # Podstawowe cechy
    grid_height = len(grid)
    grid_width = len(grid[0]) if grid else 0
    grid_size = grid_height * grid_width
    
    # Kolory i obiekty
    unique_colors = len(set(cell for row in grid for cell in row))
    non_zero_cells = sum(1 for row in grid for cell in row if cell != 0)
    
    # Obiekty (connected components)
    objects_count = count_connected_components(grid)
    
    # Postęp
    levels_completed = frame.get("levels_completed", 0)
    current_level = frame.get("current_level", 1)
    actions_taken = frame.get("action_count", 0)
    actions_since_level = frame.get("actions_since_level", 0)
    
    # Zasoby
    lives = frame.get("lives", 0)
    score = frame.get("score", 0)
    step_limit = frame.get("step_limit", 0)
    steps_remaining = step_limit - actions_taken
    
    # No-op detection
    no_op_count = frame.get("no_op_count", 0)
    no_op_ratio = no_op_count / max(1, actions_taken)
    
    # Goal class (z GOAL_CATALOG)
    goal_class_encoded = encode_goal_class(frame.get("goal_class", "UNKNOWN"))
    
    # Affordances (klikalne obiekty)
    affordances_count = count_affordances(grid)
    
    # Symetria
    symmetry_score = compute_symmetry(grid)
    
    # Density
    density = non_zero_cells / max(1, grid_size)
    
    # Edge ratio (obiekty na krawędziach)
    edge_ratio = compute_edge_ratio(grid)
    
    # Pattern similarity (jeśli jest wzorzec do skopiowania)
    pattern_similarity = compute_pattern_similarity(grid)
    
    return [
        grid_height / 30.0,
        grid_width / 30.0,
        grid_size / 900.0,
        unique_colors / 10.0,
        non_zero_cells / max(1, grid_size),
        objects_count / 20.0,
        levels_completed / 5.0,
        current_level / 5.0,
        actions_taken / 400.0,
        actions_since_level / 100.0,
        lives / 5.0,
        score / 100.0,
        steps_remaining / max(1, step_limit),
        no_op_ratio,
        goal_class_encoded,
        affordances_count / 10.0,
        symmetry_score,
        density,
        edge_ratio,
        pattern_similarity,
    ]
```

### 2. Generowanie danych treningowych
```python
def generate_training_data_arc():
    """Generuj dane treningowe z 25 gier ARC-AGI-3."""
    # Uruchom agenta (v5.0) na 25 grach treningowych
    # Dla każdego stanu: ekstrahuj cechy + result (score)
    # Zapisz do CSV: f0-f19, result
    
    games = ["ar25", "bp35", "cd82", "ft09", "lf52", "lp85", "r11l", "re86", 
             "sb26", "sk48", "sp80", "tr87", "tu93", "vc33", "wa30",
             "cn04", "dc22", "g50t", "ka59", "ls20", "m0r0", "s5i5", "sc25", "su15", "tn36"]
    
    all_rows = []
    for game in games:
        # Uruchom agenta
        result = run_game_with_feature_extraction(game)
        # result = [(features, score), (features, score), ...]
        all_rows.extend(result)
    
    # Zapisz do CSV
    with open("data/train_arc_v5.csv", "w") as f:
        writer = csv.writer(f)
        writer.writerow([f"f{i}" for i in range(20)] + ["result"])
        for features, score in all_rows:
            writer.writerow(features + [score])
    
    print(f"Generated {len(all_rows)} samples")
```

### 3. Trenowanie MLP
```python
def train_mlp_arc():
    """Trenuj MLP 20->128->64->1 na danych z ARC-AGI-3."""
    # Load data
    X, y = load_csv("data/train_arc_v5.csv")
    
    # Train MLP (numpy SGD)
    W0, b0, W1, b1, W2, b2, acc = train_one_arch(
        X, y, 
        epochs=100, 
        lr=0.02, 
        batch=256, 
        h1=128, 
        h2=64
    )
    
    print(f"MLP accuracy: {acc:.3f}")
    
    # Save weights as Python code
    save_code({"ARC": (W0, b0, W1, b1, W2, b2, acc)}, "ml_code_arc.py")
```

### 4. Integracja z LLM (v5.1)
```python
class LLMPolicyV5_1:
    """LLM Agent v5.1 z MLP value model."""
    
    def __init__(self, llm_client, mlp_weights):
        self.client = llm_client
        self.mlp_weights = mlp_weights
        self.state = GameState()
        
    def get_action(self, frame: dict) -> dict:
        # Ekstrahuj cechy
        features = extract_features_arc(frame)
        
        # MLP value prediction
        ml_value = mlp_predict(features, self.mlp_weights)  # 0-1
        
        # LLM reasoning
        llm_actions = self._get_llm_actions(frame)
        
        # Połączenie: LLM + MLP
        # LLM daje rozumowanie, MLP daje szybką ocenę
        # Jeśli MLP value < 0.3 → agent jest w złym stanie, zmień strategię
        if ml_value < 0.3:
            # Dodaj warning do promptu
            self.messages.append({
                "role": "system",
                "content": f"WARNING: ML model predicts low success probability ({ml_value:.2f}). Consider different approach."
            })
        
        # Zwróć akcję z LLM
        return llm_actions[0] if llm_actions else {"action": "RESET"}
```

## Oczekiwane wyniki

### Na podstawie Pokemon TCG:
- **MLP accuracy:** ~0.85-0.95 (vs 0.913 w Pokemon)
- **Speedup:** 0.16ms/decision (vs ~2s LLM call)
- **Score improvement:** +2-5 pkt (vs v5.0 27-35 pkt)

### Realistyczny cel v5.1:
- **v5.0:** ~35-42 pkt (z LEVEL_NOTES + STUCK_AUDIT + GOAL_CATALOG)
- **v5.1:** ~37-47 pkt (z MLP value model)
- **Próg nagród:** 40.97 pkt
- **Lider:** 67.49 pkt

### Co daje MLP:
1. **Szybka ocena stanu** - 0.16ms vs 2s LLM call
2. **Detekcja złych stanów** - jeśli value < 0.3, zmień strategię
3. **Meta-learning** - MLP uczy się które stany prowadzą do wygranej
4. **Uzupełnienie LLM** - LLM daje rozumowanie, MLP daje intuicję

## Harmonogram implementacji

### Tydzień 1 (14-20 X):
- [ ] Ekstrakcja cech z ARC-AGI-3 (extract_features_arc)
- [ ] Generowanie danych treningowych (generate_training_data_arc)
- [ ] Trenowanie MLP (train_mlp_arc)
- [ ] Integracja z LLM (LLMPolicyV5_1)

### Tydzień 2 (21-27 X):
- [ ] Testy A/B na 25 grach (v5.0 vs v5.1)
- [ ] Per-game models (osobny MLP dla każdej gry)
- [ ] Optymalizacja hiperparametrów (lr, batch, epochs)
- [ ] Zgłoszenie v5.1 na Kaggle

### Tydzień 3 (28 X - 3 XI):
- [ ] Iteracja na podstawie wyników
- [ ] Counter-picking (dostosowanie do konkretnych gier)
- [ ] Finalne zgłoszenie przed deadline (2 XI)

## Źródła
- **c87f7a48-pokemon:** generate_training_data_fast.py, train_perarch_fast.py, main_heuristic_v42_ml.py
- **Wyniki:** 96k samples in 115s, 0.16ms/answer, MLP accuracy 0.913
- **v42.6 hard6:** 0.827 (vs v41 reactive 0.783) = +4.4pp z ML

## Commit
`[pending]` - feat: v5.1 z MLP value model (na podstawie c87f7a48-pokemon)
