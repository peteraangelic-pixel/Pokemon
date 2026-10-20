# ARC-AGI-3 RL Training Pipeline

**Inspirowane Pokemon TCG (gałęzie a450b00f i c87f7a48)**

## 📊 Status

- ✅ **Parallel evaluation**: `baseline/scripts/play_local_mp.py` (96k samples in 115s)
- ✅ **Policy network**: `rl/policy_network.py` (MLP, can upgrade to Transformer)
- ✅ **BC trainer**: `rl/policy_network.py` (cross-entropy loss, SGD)
- ⏳ **Data collection**: TODO (use LLM agent v7 to generate demonstrations)
- ⏳ **PPO training**: TODO (self-play after BC)

## 🎯 Plan

### Phase 1: BC (Behavior Cloning) - 2h
1. **Collect demonstration data**: Use LLM agent v7 to solve 100 games
2. **Extract features**: Convert game states → feature vectors
3. **Train MLP policy**: BC with cross-entropy loss
4. **Evaluate**: Compare with LLM agent

### Phase 2: PPO (Proximal Policy Optimization) - 20h
1. **Self-play**: Agent plays against itself
2. **Policy gradient**: Update with clipping (stabilization)
3. **League training**: Pool of agents → robust policy
4. **Evaluate**: Compare with BC baseline

### Phase 3: Transformer+Pointer - 10h
1. **Upgrade architecture**: Replace MLP with Transformer encoder
2. **Pointer head**: Choose from valid actions (not fixed action space)
3. **Multi-task**: Policy + value heads
4. **Evaluate**: Compare with MLP baseline

## 🏗️ Architecture

### Policy Network (Current: MLP)
```
Input: state_features [input_dim]
  ↓
Hidden: Dense(128) + ReLU
  ↓
Output: action_logits [num_actions]
  ↓
Softmax → action_probs
```

### Policy Network (Future: Transformer+Pointer)
```
Input: 
  - grid_tokens [H*W, features]
  - valid_actions_mask [num_actions]
  ↓
Transformer Encoder (self-attention over grid tokens)
  ↓
Context: mean pooling [hidden_dim]
  ↓
Pointer Head: einsum(action_features, context) + mask
  ↓
Softmax → action_probs
```

### Training Pipeline
```
1. Collect Data
   LLM agent v7 → play 100 games → save (state, action) pairs
   
2. BC Training
   (state, action) pairs → feature extraction → MLP policy
   Loss: cross-entropy(predicted_action, actual_action)
   
3. PPO Training (optional)
   MLP policy → self-play → policy gradient update
   Loss: clipped surrogate objective
   
4. Evaluation
   Play games → compute win rate → compare with baseline
```

## 📁 Files

- `policy_network.py`: MLP policy + BC trainer
- `README.md`: This file
- `../baseline/scripts/play_local_mp.py`: Parallel evaluation
- `../llm-agent/llm_policy_v7.py`: LLM agent for data collection

## 🚀 Usage

### Collect BC Data (TODO)
```bash
cd arc-agi-3
python rl/data_collector.py \
  --games ls20,vc33,sc25 \
  --agent llm_policy_v7 \
  --output rl/bc_data.json
```

### Train BC Policy (TODO)
```bash
cd arc-agi-3
python rl/train_bc.py \
  --data rl/bc_data.json \
  --epochs 10 \
  --batch-size 32 \
  --output rl/bc_policy.npz
```

### Evaluate Policy (TODO)
```bash
cd arc-agi-3
python rl/evaluate_policy.py \
  --policy rl/bc_policy.npz \
  --games ls20,vc33,sc25 \
  --workers 4
```

## 📊 Expected Results

**Uczciwie: brak wiarygodnych liczb.** Nie mamy jeszcze danych eksperta, więc każda
tabela "expected win rate" byłaby zgadywaniem. Zmierzone jest tylko to, co poniżej.

| Element | Status | Zmierzone |
|---|---|---|
| Silnik lokalny (krok gry) | ✅ działa | 0.10 ms/krok, ~300 epizodów/s na 16 rdzeniach |
| Polityka LLM-free (heurystyka) | ✅ działa | 0.27% poziomów, 2/25 gier z postępem |
| Biblioteka gwarantowanych rozwiązań | ✅ działa | cd82 i sp80 → 100% poziomu 1 |
| BC / PPO / Transformer | ⛔ zablokowane | brak trajektorii eksperta do uczenia |

Kolejność ma znaczenie: **najpierw dane** (nagrania z runów Kaggle → replay lokalnie →
pary (obserwacja, akcja)), **potem** BC. Trening na danych syntetycznych z LLM-a ma sens
dopiero, gdy lokalna pętla replay działa — inaczej nie ma jak zweryfikować, że polityka
naśladuje cokolwiek użytecznego.

## 🔧 Implementation Details

### Feature Extraction
Convert game state → feature vector:
- Grid values (flattened 2D array)
- Player position (x, y)
- Score, level, lives, time
- Enemy positions (if available)
- Goal position (if visible)

### BC Training
- **Loss**: Cross-entropy between predicted and actual actions
- **Optimizer**: SGD with learning rate 0.001
- **Batch size**: 32
- **Epochs**: 10

### PPO Training (Future)
- **Loss**: Clipped surrogate objective
- **Clip ratio**: 0.2
- **Discount factor**: 0.99
- **GAE lambda**: 0.95
- **Batch size**: 64
- **Iterations**: 100

### Transformer Architecture (Future)
- **Hidden dim**: 128
- **Layers**: 3
- **Heads**: 4
- **Parameters**: ~1M

## 🎓 Lessons from Pokemon TCG

1. **Parallel evaluation is critical**: 10x speedup vs sequential
2. **BC provides good initialization**: Start with expert demonstrations
3. **PPO improves beyond BC**: Self-play discovers better strategies
4. **Transformer > MLP**: Self-attention captures spatial patterns
5. **Pointer network handles variable actions**: Choose from valid options

## 📝 Notes

- **Current bottleneck**: We don't have demonstration data yet
- **Next step**: Wait for Duck harness results (tonight), then collect data from successful games
- **Alternative**: Use GPT-4 to generate synthetic demonstrations
- **GPU**: Can use Kaggle GPU (T4/P100) for training, but GitHub Actions has no GPU
- **Timeline**: Phase 1 (BC) after Duck harness results, Phase 2-3 in following weeks

## 🔗 References

- Pokemon TCG Rust+Rayon: `a450b00f-pokemon:pokemon-agent/rust/`
- Pokemon TCG RL: `c87f7a48-pokemon:pokemon-agent/rl/`
- Duck Harness: `/tmp/duck-harness/`
- ARC-AGI-3 environment: `arc-agi-3/games/environment_files/`
