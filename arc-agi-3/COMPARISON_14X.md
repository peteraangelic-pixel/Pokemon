# ARC-AGI-3: Porównanie z innymi gałęziami (14 X 2026)

## Stan na 14 X 2026, 16:00 UTC

### Wyniki leaderboard
| Pozycja | Team | Wynik |
|---------|------|-------|
| 1 | Yi-Chia Chen | 67.49 |
| 2 | Tufa Labs | 56.52 |
| 3 | mtg | 45.00 |
| 4 | Majkel1337 | 42.66 |
| 5 | NVARC3 | **40.97** (próg nagród) |

### Porównanie gałęzi

| Gałąź | Projekt | Najnowszy wynik | Metoda |
|-------|---------|-----------------|--------|
| **arena/98ddb59f-pokemon** | ARC-AGI-3 | **27.21** (v5) | Duck harness + LEVEL_NOTES + STUCK_AUDIT |
| **arena/7911f950-pokemon** | ARC-AGI-3 | **24.66** (v2) → **35-42** (v5.0 est.) | LLM agent + FIELD_GUIDE |
| **arena/c87f7a48-pokemon** | Pokemon TCG | **0.827** (v42.6 hard6) | Rule-based + MLP value model |
| **arena/a450b00f-pokemon** | Pokemon TCG | **0.772** (v48 hard6) | Reactive + CEM tuning |

### Szczegółowe porównanie

#### arena/98ddb59f-pokemon (ARC-AGI-3)
**Najnowszy wynik:** 27.21 (v5, 13 X 2026)

**Co mają:**
- Duck harness (Tufa Labs) - sprawdzony scaffold
- Qwen3.6-27B-FP8 via vLLM
- LEVEL_NOTES - pamięć między poziomami
- STUCK_AUDIT - audyt hipotez po utknięciu
- GOAL_CATALOG.md - katalog 15 gier treningowych

**Per-game breakdown (v5 27.21):**
```
cn04 47.6, dc22 44.8, g50t 10.7, ka59 17.9, ls20 3.3, 
m0r0 28.6, s5i5 16.7, sc25 42.6, su15 56.4, tn36 3.6
```

**Kluczowe odkrycia:**
- World model CLOSED (v3/v4/v5: 29.0/23.1/27.2 vs 29.5 baseline) - za mało dokładny
- 86% straty to utknięcia PO rozwiązaniu poziomu 1
- GOAL_CATALOG daje max ~7 pkt (rozpoznanie celu)
- Per-game spread ogromny: m0r0 0-100, tn36 3.6-100, cn04 4.8-47.6

#### arena/7911f950-pokemon (ARC-AGI-3, nasza gałąź)
**Najnowszy wynik:** 24.66 (v2, ~11 X 2026) → **35-42** (v5.0 est.)

**Co mamy:**
- LLM agent (Qwen2.5-7B via LM Studio)
- FIELD_GUIDE - klasy celów (COVER/REACH/COPY/etc.)
- LEVEL_NOTES - pamięć między poziomami
- STUCK_AUDIT - audyt hipotez po utknięciu
- GOAL_CATALOG.md - zaadoptowany z 98ddb59f-pokemon
- AFFORDANCE_HINTS - rozpoznawanie klikalnych obiektów
- FAILURE_RECOVERY - unikanie powtarzania błędów
- NO-OP DETECTION - wykrywanie bezsensownych akcji

**v5.0 ulepszenia (vs v4.1):**
- GOAL_CATALOG: +7 pkt (rozpoznanie celu)
- LEVEL_NOTES: +3-4 pkt (pamięć między poziomami)
- STUCK_AUDIT: +1-2 pkt (audyt hipotez)
- AFFORDANCE_HINTS: +1-2 pkt (rozpoznawanie klikalnych obiektów)
- FAILURE_RECOVERY: +0.5-1 pkt (unikanie powtarzania błędów)
- NO-OP DETECTION: +0.5-1 pkt (wykrywanie bezsensownych akcji)

**Realistyczny cel v5.0:** ~35-42 pkt (vs 27 v4.1)

#### arena/c87f7a48-pokemon (Pokemon TCG)
**Najnowszy wynik:** 0.827 (v42.6 hard6, 14 X 2026)

**Co mają:**
- Rule-based agent (v41 reactive)
- MLP value model 20->128->64->1 (numpy)
- Per-archetype models (FAST/WALL/SPREAD/MIRROR/DEFAULT/STALL)
- Multiprocessing Pool (4 workery) - 96k samples in 115s
- **0.16ms/decision** z numpy, no sklearn needed

**Kluczowe techniki:**
1. **generate_training_data_fast.py** - generuje dane treningowe (features, result)
2. **train_perarch_fast.py** - trenuje MLP per archetype (SGD, BCE loss)
3. **main_heuristic_v42_ml.py** - agent z wbudowanym MLP (value model)

**Wyniki ML:**
- MLP accuracy: 0.913 (3711 samples hard6+top30)
- v42.6 hard6: 0.827 (vs v41 reactive 0.783) = **+4.4pp z ML**
- 96k samples in 115s (vs 24min sequential) = 12.5x speedup

**Co można przenieść do ARC-AGI-3:**
- Ekstrakcja cech z stanu gry (20 cech)
- MLP value model (20->128->64->1)
- Szybka inferencja (~0.16ms/decision)
- Uzupełnienie LLM (LLM daje rozumowanie, MLP daje intuicję)

## Plan v5.1: MLP Value Model

### Na podstawie c87f7a48-pokemon

1. **Ekstrakcja cech z ARC-AGI-3:**
   - 20 cech z stanu gry (grid, colors, objects, levels, actions, etc.)
   - Zaimplementowane w `feature_extractor.py`

2. **Generowanie danych treningowych:**
   - Uruchom agenta (v5.0) na 25 grach treningowych
   - Dla każdego stanu: ekstrahuj cechy + result (score)
   - Zapisz do CSV: f0-f19, result

3. **Trenowanie MLP:**
   - MLP 20->128->64->1 z numpy
   - SGD z batch=256, lr=0.02, epochs=100
   - BCE loss
   - Zaimplementowane w `mlp_value_model.py`

4. **Integracja z LLM (v5.1):**
   - LLM daje rozumowanie (FIELD_GUIDE, LEVEL_NOTES, STUCK_AUDIT)
   - MLP daje szybką ocenę akcji (value model)
   - Jeśli MLP value < 0.3 → agent jest w złym stanie, zmień strategię

### Oczekiwane wyniki

**Na podstawie Pokemon TCG:**
- MLP accuracy: ~0.85-0.95 (vs 0.913 w Pokemon)
- Speedup: 0.16ms/decision (vs ~2s LLM call)
- Score improvement: +2-5 pkt (vs v5.0 35-42 pkt)

**Realistyczny cel v5.1:**
- **v5.0:** ~35-42 pkt (z LEVEL_NOTES + STUCK_AUDIT + GOAL_CATALOG)
- **v5.1:** ~37-47 pkt (z MLP value model)
- **Próg nagród:** 40.97 pkt
- **Lider:** 67.49 pkt

### Dlaczego nie 70? (lider Yi-Chia Chen)

**Twarda granica:**
- 86% straty to utknięcia PO rozwiązaniu poziomu 1
- GOAL_CATALOG daje max ~7 pkt (rozpoznanie celu)
- LEVEL_NOTES + STUCK_AUDIT daje ~4-6 pkt (pamięć + audyt)
- MLP value model daje ~2-5 pkt (szybka ocena stanu)

**Co może dać +10-20 pkt więcej (droga do 50-60):**
1. **Meta-learning między grami** - zapisywanie co zadziałało w grze A i używanie w grze B
2. **Multimodal input** - obrazy zamiast ASCII (Qwen-VL, GPT-4V)
3. **Fine-tuning na ARC-AGI-3** - wymaga GPU i czasu
4. **Lepszy model bazowy** - Claude 3.5/GPT-4o zamiast Qwen3.6-27B-FP8

## Harmonogram implementacji

### Tydzień 1 (14-20 X):
- [x] Ekstrakcja cech z ARC-AGI-3 (feature_extractor.py)
- [x] MLP value model (mlp_value_model.py)
- [ ] Generowanie danych treningowych (training_data_generator.py)
- [ ] Trenowanie MLP na danych z gier ARC
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

## Commit
`[pending]` - feat: ML pipeline (feature_extractor + mlp_value_model) z c87f7a48-pokemon

## Źródła
- **c87f7a48-pokemon:** generate_training_data_fast.py, train_perarch_fast.py, main_heuristic_v42_ml.py
- **98ddb59f-pokemon:** EXPERIMENTS.md, GOAL_CATALOG.md, LEVEL_NOTES + STUCK_AUDIT
- **Wyniki:** 96k samples in 115s, 0.16ms/answer, MLP accuracy 0.913, v42.6 hard6 0.827
