# Inspiracje z projektu Pokemon TCG (gałęzie a450b00f i c87f7a48)

**Data analizy:** 2026-10-16  
**Cel:** Zidentyfikować techniki z Pokemon TCG które mogą pomóc w ARC-AGI

---

## 🎯 Kluczowe odkrycia

### 1. **Rust + Rayon = 200x speedup vs Python**

**Co to jest:**
- System do masowej paralelizacji gier Pokemon TCG
- FFI do native C library (`libcg.so`)
- Rayon do fan-out na poziomie gier (nie pojedynczych kroków)
- Thread-local storage dla engine instances (unika lock contention)

**Wyniki:**
- Single-core: ~8 ms/game (20x faster niż Python wrapper)
- Multi-core (8 workers): ~1000 games/s → 10k gier w ~10 sekund
- vs Python: 125 games/s → 10k gier w ~2 minuty

**Czy pomoże w ARC-AGI?** ⚠️ **OGRAICZENIE**
- ARC-AGI nie ma native C engine (to Kaggle environment w Pythonie)
- Ale możemy użyć Rayon/parallelizm do:
  - Równoległego uruchamiania wielu gier ARC-AGI
  - Parallel hyperparameter search
  - Batch evaluation wielu wariantów agenta
  - Mass rollout do generowania danych treningowych

**Jak to zrobić:**
```python
# Zamiast sekwencyjnego:
for game in games:
    play_game(game)

# Użyj ProcessPoolExecutor:
from concurrent.futures import ProcessPoolExecutor
with ProcessPoolExecutor(max_workers=8) as executor:
    executor.map(play_game, games)
```

---

### 2. **Transformer + Pointer Network (JAX/Flax)**

**Co to jest:**
- Architektura modelu RL: transformer encoder nad board tokens + pointer head
- ~0.6M parametrów przy d=128
- Multi-task learning: policy + value head
- Self-attention nad stanem gry (nie fixed feature vector)

**Kluczowe cechy:**
- Pointer network: wyjście to rozkład nad **legalnymi opcjami** (nie fixed action space)
- Transformer: self-attention nad board tokens (kartami, Pokemonami)
- Flattened bundle: 1.9M, easy deploy na Kaggle

**Czy pomoże w ARC-AGI?** ✅ **TAK**
- ARC-AGI ma **variable action space** (różne gry mają różne legalne akcje)
- Pointer network może wybrać spośród legalnych akcji (jak w Pokemon)
- Transformer może przetwarzać stan gry (grid 2D → tokens)
- Multi-task: policy (wybór akcji) + value (ocena stanu)

**Jak to zrobić:**
```python
# Transformer nad grid tokens
class PolicyNet(nn.Module):
    d: int = 128
    layers: int = 3
    heads: int = 4
    
    def __call__(self, grid_tokens, legal_actions_mask):
        # grid_tokens: [B, H*W, features]
        # legal_actions_mask: [B, num_actions]
        
        # Self-attention nad grid
        x = self.transformer(grid_tokens)
        context = x.mean(axis=1)  # [B, d]
        
        # Pointer head nad legal actions
        action_features = self.project(legal_actions)  # [B, num_actions, d]
        logits = einsum('bod,bd->bo', action_features, context)
        logits = logits + (1 - legal_actions_mask) * (-1e9)
        
        # Value head
        value = self.value_head(context)
        
        return logits, value
```

---

### 3. **BC (Behavior Cloning) + PPO (Proximal Policy Optimization)**

**Co to jest:**
- **BC:** Uczenie z replay'ów ekspertów (top 30 graczy Kaggle)
  - 6000 gier × 2500 kroków = ~15M ejemplos
  - Loss: cross-entropy nad akcjami eksperta
- **PPO:** Fine-tuning z self-play
  - 60 iteracji × 300 gier × 2500 kroków = ~4.5M ejemplos
  - Policy gradient z clipping (stabilizacja treningu)
  - League training: agent gra vs pool of opponents

**Wyniki:**
- BC only: 0.500 win rate vs top 30
- BC + PPO: 0.700+ win rate vs top 30
- Kaggle rating: 715.4 (top 10% competition)

**Czy pomoże w ARC-AGI?** ⚠️ **CZĘŚCIOWO**
- ARC-AGI nie ma replay'ów ekspertów (nie ma "top players")
- Ale możemy:
  1. **BC z synthetic data:** Generować rozwiązania z LLM (GPT-4, Claude) → uczyć small model
  2. **PPO z self-play:** Agent gra vs siebie, ewoluuje strategię
  3. **League training:** Pool of agents (różne strategie) → robust policy

**Jak to zrobić:**
```python
# 1. Generuj dane treningowe z LLM
for game in arc_games:
    solution = gpt4_solve(game)
    bc_data.append((game.state, solution.action))

# 2. Train BC
model.train(bc_data, epochs=10)

# 3. Fine-tune z PPO
for iter in range(60):
    # Self-play
    for game in arc_games:
        state = game.reset()
        while not game.done:
            action = model.sample(state)
            next_state, reward = game.step(action)
            ppo_buffer.add(state, action, reward, next_state)
    
    # PPO update
    model.ppo_update(ppo_buffer, clip_ratio=0.2)
```

---

### 4. **Analiza stylu gry przeciwników (Meta-learning)**

**Co to jest:**
- Analiza 45 replay'ów z top 30 Kaggle
- Statystyki: Gust timing, retrieval patterns, energy usage
- Per-team playstyle profiles (np. "aggressive early gust" vs "late game closure")

**Przykład:**
```
Team: Darren Sheehan
Games: 5, Win%: 0.20
Gust/game: 6.20, First gust turn avg: 4.0
Retrieval/game: 7.80, Energy/game: 14.80
→ Aggressive early disruption, low energy investment
```

**Czy pomoże w ARC-AGI?** ⚠️ **NIE BEZPOŚREDNIO**
- ARC-AGI nie ma "przeciwników" (to single-player puzzle)
- Ale możemy:
  1. **Klasyfikacja gier:** Typy celów (FLOW, COPY, LOCAL_CONSTRAINTS)
  2. **Per-goal strategies:** Różne policy dla różnych typów gier
  3. **Meta-learning:** Agent uczy się rozpoznawać typ gry → wybiera strategię

**Jak to zrobić:**
```python
# Goal classifier (już mamy w goal_classifier.py)
goal_type = classify_goal(game.state)

# Per-goal policy
if goal_type == "FLOW":
    policy = flow_policy
elif goal_type == "COPY":
    policy = copy_policy
else:
    policy = default_policy

action = policy(game.state)
```

---

### 5. **FFI do native code (C/Rust)**

**Co to jest:**
- Python wrapper wokół native C library
- Unikamy overhead Pythona (JSON parsing, object creation)
- Thread-safe: każdy thread ma swoją instancję engine

**Wyniki:**
- 20x faster niż Python wrapper
- ~8 ms/game single-core

**Czy pomoże w ARC-AGI?** ❌ **NIE**
- ARC-AGI environment jest w Pythonie (nie ma native library)
- Nie możemy przyspieszyć samego environmentu
- Ale możemy przyspieszyć **agent decision** (np. inference modelu w C++)

---

### 6. **Workflow do masowego treningu RL**

**Co to jest:**
- GitHub Actions workflow: 5.5h timeout
- BC: 6000 gier × 2500 kroków
- PPO: 60 iteracji × 300 gier
- Evaluacja: 200 gier
- Automatyczny commit params back do repo

**Czy pomoże w ARC-AGI?** ✅ **TAK**
- Możemy stworzyć podobny workflow dla ARC-AGI
- Długi trening (5-10h) w GitHub Actions
- Automatyczny eval + commit najlepszych params
- Iteracja: train → eval → commit → repeat

**Jak to zrobić:**
```yaml
# .github/workflows/arc3-rl-train.yml
name: arc3-rl-train
on:
  push:
    paths: ['arc-agi-3/rl_train.trigger']
  workflow_dispatch: {}
jobs:
  train:
    runs-on: ubuntu-latest
    timeout-minutes: 600  # 10h
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - name: Install deps
        run: pip install jax flax optax vllm
      - name: Train BC + PPO
        run: |
          python -m arc3_rl.train \
            --bc-games 10000 \
            --ppo-iters 100 \
            --out arc3_rl/params_best.npz
      - name: Commit params
        run: |
          git add arc3_rl/params_best.npz
          git commit -m "arc3: BC+PPO training [skip ci]"
          git push origin HEAD:arena/7911f950-pokemon
```

---

## 🎯 Podsumowanie: Co możemy wziąć z Pokemon TCG

### ✅ **WARTO TRANSFEROWAĆ:**

1. **Transformer + Pointer Network** (architektura)
   - Variable action space (legal actions mask)
   - Self-attention nad stanem gry
   - Multi-task: policy + value

2. **BC + PPO training pipeline**
   - BC z synthetic data (LLM solutions)
   - PPO z self-play
   - League training (pool of agents)

3. **Workflow do masowego treningu**
   - GitHub Actions z długim timeout (10h)
   - Automatyczny eval + commit
   - Iteracja: train → eval → commit

4. **Parallel evaluation** (nie Rust, ale Python multiprocessing)
   - ProcessPoolExecutor do równoległego uruchamiania gier
   - Batch hyperparameter search
   - Mass rollout do generowania danych

5. **Goal classification + per-goal strategies**
   - Meta-learning: rozpoznawanie typu gry
   - Różne policy dla różnych typów celów

### ❌ **NIE TRANSFERUJEMY:**

1. **Rust FFI do native engine** (ARC-AGI jest w Pythonie)
2. **Analiza stylu gry przeciwników** (ARC-AGI to single-player)
3. **Replay analysis z top players** (nie ma ekspertów w ARC-AGI)

---

## 🚀 Plan działania dla ARC-AGI

### Krok 1: Transformer + Pointer Network (inspirowane Pokemon)
- Architektura: transformer nad grid tokens + pointer head nad legal actions
- Multi-task: policy (wybór akcji) + value (ocena stanu)
- ~1M parametrów (mały, szybki inference)

### Krok 2: BC z synthetic data
- Generuj rozwiązania z GPT-4/Claude (1000 gier)
- Train BC na tych danych (teacher forcing)
- Cel: 0.3+ win rate vs random

### Krok 3: PPO z self-play
- Agent gra vs siebie (self-play)
- PPO z clipping (stabilizacja)
- Cel: 0.4+ win rate vs random

### Krok 4: Goal classification + per-goal strategies
- Klasyfikuj typ celu (FLOW, COPY, LOCAL_CONSTRAINTS)
- Per-goal policy (różne strategie)
- Cel: 0.5+ win rate vs random

### Krok 5: Workflow do masowego treningu
- GitHub Actions: 10h timeout
- BC → PPO → eval → commit
- Iteracja: codziennie nowy model

### Krok 6: Parallel evaluation
- ProcessPoolExecutor do równoległego uruchamiania gier
- Batch hyperparameter search
- Cel: 10x speedup vs sequential

---

## 📊 Oczekiwane wyniki

| Krok | Metoda | Expected win rate vs random | Czas treningu |
|------|--------|----------------------------|---------------|
| 0 | Baseline (random) | 0.01 | 0 |
| 1 | Heuristics (current v7) | 0.10 | 0 |
| 2 | BC (GPT-4 data) | 0.30 | 2h |
| 3 | BC + PPO (self-play) | 0.40 | 5h |
| 4 | + goal classification | 0.50 | 5h |
| 5 | + parallel eval | 0.50 (10x faster) | 5h |

**Cel końcowy:** 0.5+ win rate vs random → **~50+ punktów na LB** (z 26.25)

---

## ⚠️ Ograniczenia

1. **Czas:** Mamy mało czasu (deadline 02.11), więc musimy priorytetyzować
2. **GPU:** GitHub Actions nie ma GPU, więc training musi być CPU-friendly
3. **Dane:** Nie mamy replay'ów ekspertów (jak w Pokemon), więc musimy generować z LLM
4. **Complexity:** ARC-AGI jest trudniejszy niż Pokemon (general intelligence vs domain-specific)

---

## 🎯 Rekomendacja

**Największy impact w krótkim czasie:**
1. **BC z GPT-4 data** (2h, +0.20 win rate)
2. **Parallel evaluation** (1h, 10x speedup)
3. **Goal classification** (1h, +0.10 win rate)

**Długoterminowo (po 17.10):**
4. **Transformer + Pointer** (10h, architecture upgrade)
5. **PPO self-play** (20h, +0.10 win rate)
6. **Workflow automation** (5h, codzienna iteracja)

---

**Podsumowanie:** Pokemon TCG ma wiele technik które mogą pomóc w ARC-AGI, ale musimy priorytetyzować. Największy impact w krótkim czasie: BC z synthetic data + parallel eval. Długoterminowo: transformer architecture + PPO self-play.
