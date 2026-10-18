# c87_v72_verification – druga gałąź vs nasza v72

**Sprawdziłem ich v72_genial — to nasza v70 w ich wykonaniu, bez przewagi**

**Co zrobili:** v71 bez twardego override'u +5000 (przyznali, że psuł kolejność silnika), miękka ławka v3 + reguła Judge. Talia to **dokładnie nasza kompozycja Judge** (trolley −1 Petrel +1 Judge) — tu pełna konwergencja składników. Deklarują broad 0,933 i Alakazam 0,64.

**Moje pomiary (artefakt z paczki, 1200g FFI):**

| test | v72_odniesienie | mirror vs champion | H2H vs v67 | H2H vs moja v70 (ta sama talia) | vs Alakazam | siatka 4800g |
|------|----------------|-------------------|------------|--------------------------------|-------------|--------------|
| v72_genial | 0,485 | v67: 0,527 · moja v70: 0,505 | 0,467 | **0,502 remis pilotów** | 0,539 (głód 36%) moja v70: 0,543 · v67: 0,507 | 0,700 v67: 0,714 |

**Werdykt:** deklarowane 0,64 na Alakazam i 0,933 broad znów się nie odtwarzają (realnie 0,539 i 0,700 z ich harnessu FFI). Na identycznej talii ich pilot remisuje z moją v70 (0,502), a w mirrorze jest słabszy od żywej v67. **Brak jakiegokolwiek powodu, by wysyłać ich v72 zamiast naszej v70_meta** — a v67 (443,2) nadal zostaje najlepszą submisją.

Obie gałęzie stoją teraz w tym samym miejscu: ten sam składnik (Judge), te same liczby ±2pp, ten sam sufit. Dalsze wersje regułowe — obojętnie z której gałęzi — będą się różnić tylko nazwą.

## Nasza replikacja

- v72 vs v73: 112-88 (v72 wygrywa 56%)
- v73 vs v67: 102-98 tie
- broad top30 8g: v72 0.889, v73 0.954 – szum ±0.04
- broad_field 67x4g: v72 0.698 vs v67 0.668 – v72 lepszy broad, ale siatka 4800g 0.700 vs 0.714 v67 per druga gałąź

## Wniosek: sufit heurystyki 600-700 (Mastering without ML)

Heurystyka ma sufit 600-700, wiedzieliśmy od 2 dni, a mimo to brnęliśmy w większe bonusy. Dalsze wersje regułowe bez sensu.

Aby >1000 (7th place ~10.7M param transformer encoder-decoder + GRU belief core, conditioned on card text, pointer head, RL vs league 70+ frozen, greedy + lethal check + mask dominated):

- Transformer encoder-decoder + GRU belief
- Każda legalna akcja kodowana z tekstu karty + live state
- Pointer head, softmax po legalnych – bez fixed action space
- RL vs league 70+ frozen opponents
- MCTS + lethal check + mask dominated
- League + belief

Nasz musi być transformer z RL, MCTS, league + belief i inne zacytowane wyżej rzeczy by mieć jakiekolwiek szanse.

## v74 scaffold

- `agents/v74_transformer_rl.py` – transformer + GRU belief + pointer + value head, numpy inference, post-processing lethal+mask+Judge, gated search margin>=250
- `tools/train_transformer.py` – BC training JAX, 400 games 61k decisions, 61% acc tiny, target 77%+ with 2400 games
- `tools/train_ppo_league.py` – TODO: PPO vs frozen league 8-12 pilotów
- Deck trolley34w+Judge (konwergencja)

Następne kroki: frozen liga, PPO self-play vs liga (nie mirror), tani search w wąskich bramkach margin>=250, belief GRU + pointer head, meta-counter rotacja z replayów.
