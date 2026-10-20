# Local CPU harness — co realnie daje Twój PC (16 rdzeni / 64 GB)

Ten katalog uruchamia **prawdziwy silnik gier ARC-AGI-3 lokalnie**, bez LLM, bez GPU,
bez Kaggle. Wszystko poniżej jest zmierzone, nie oszacowane.

## Zmierzone liczby (sandbox 2 rdzenie, `arc-agi==0.9.9`, `arcengine==0.9.3`)

| Operacja | Czas |
|---|---|
| krok gry (`perform_action`) | **0.10 ms** (p95: 0.32 ms) |
| `reset()` + init wrappera | ~17 ms |
| `copy.deepcopy(game)` | 3–14 ms (bp35/lf52: 30–80 ms) |
| pełny epizod (~200–500 kroków) | ~30–60 ms |
| gauntlet: 150 epizodów / 25 gier | **4.9 s na 2 rdzeniach** (30 ep/s) |
| CEM: 48 epizodów na generację | 1.1–1.4 s na 2 rdzeniach |

Na 16 rdzeniach skaluje się ~liniowo (każdy epizod to osobny proces, brak współdzielonego
stanu): **~250–350 epizodów/s** → pełny przegląd 25 gier × 20 prób w ~2 s.

## Narzędzia

### `gauntlet.py` — równoległa ewaluacja
```bash
python local/gauntlet.py --games all --rollouts 20 --workers 16
python local/gauntlet.py --games all --rollouts 20 --workers 16 --policy solution
```
Raport per gra: średnia/best poziomów, histogram, kroki, błędy, poziom ukończenia.
To jest **bramka przed subem**: zanim wydasz jedyny dzienny submit, sprawdzasz lokalnie,
czy zmiana w ogóle coś daje.

### `evolve.py` — CEM/ES na prawdziwym silniku
```bash
python local/evolve.py --generations 30 --population 64 --workers 16
```
Zastępuje `mock_evaluator` z `llm-agent/evolve_parameters.py`. Fitness = średnia liczba
poziomów + spójność − marnowane kroki. 8 parametrów heurystyki (temp, novelty_weight,
noop_penalty, reverse_penalty, epsilon, click_rate, memory_decay, progress_bonus).

### `solver.py` — offline rozwiązywanie poziomów
```bash
python local/solver.py --games all --budget 20000 --depth 40 --workers 16 \
    --out local/solutions.json
```
BFS po sekwencjach akcji z deduplikacją po hashu klatki i deepcopy stanu. Znaleziona
ścieżka = **gwarantowane przejście poziomu**, niezależne od jakości LLM-a.

Wynik pierwszego przebiegu (budżet tylko 700 węzłów, 2 rdzenie, 86 s):

```
cd82  1/6  [[3],[2],[2],[4],[5]]        -> replay OK: level 1, 5 kroków
sp80  1/6  [[4],[4],[4],[5]]            -> replay OK: level 1, 4 kroki
```

Po podłączeniu biblioteki (`--policy solution`) te gry wchodzą na **1.00 poziomu
w 100% epizodów** (vs 0.00 dla czystej heurystyki), a potem gra dalej heurystyką.

### `engine.py`, `policies.py` — silnik i polityki
`random`, `anti-reverse`, `heuristic` (8 ewoluowalnych parametrów), `solution` (replay
biblioteki + fallback). Polityki są LLM-free — to nie jest zamiennik Duck harnessu,
tylko szybki sygnał fitness i warstwa "gwarantowanych" ruchów.

## Czego ten PC NIE zrobi

1. **Nie zastąpi Kaggle GPU.** Duck harness używa Qwen 3.6 27B FP8 → wymaga CC ≥ 8.9
   (RTX PRO 6000 / Blackwell) i ~30 GB VRAM. Na typowym 24 GB (4090) się nie zmieści.
   Można odpalić 7–14B albo 27B w 4-bit, ale jakość reasoningu spada → wyniki nie
   przenoszą się na leaderboard.
2. **Nie odpali submission.** Submisja to notebook na Kaggle z GPU; lokalnie tylko
   przygotowujesz i weryfikujesz zmiany.
3. **Nie da się na nim zrobić BC/PPO bez danych.** Nie mamy trajektorii eksperta —
   dopóki nie ściągniemy nagrań z runów Kaggle, trening RL nie ma z czego się uczyć.

## Cztery realne zastosowania (w kolejności wartości)

1. **Bramka przed dziennym subem** — jedyna rzecz chroniąca przed spaleniem 1/1 suba
   na ślepą zmianę. Koszt: sekundy.
2. **Solver offline → biblioteka gwarantowanych poziomów** — uruchamiany nocą na 16
   rdzeniach z dużym budżetem (np. 50k węzłów/gra). Każdy znaleziony poziom to
   punkty niezależne od LLM-a i od wariancji modelu.
3. **CEM nad parametrami** — 30 generacji × 64 osobników × 25 gier × 3 seedy
   ≈ 144k epizodów ≈ 8–10 min na 16 rdzeniach. Wcześniej nie było to w ogóle możliwe.
4. **Analiza nagrań + segmentacja w Rust** — `arc-agi-3/rust/` (Rayon, 276× vs Python,
   patrz `rust/BENCHMARK.md`). Realny use case: 1e6 klatek w Pythonie = 11 h,
   w Rust na 16 rdzeniach ≈ 1.3 min. Budowa: `cd rust && cargo build --release`.

## Instalacja na PC

```bash
# wymagany Python 3.12+ (arc-agi 0.9.x deklaruje >=3.12)
python3.12 -m venv .venv && . .venv/bin/activate
pip install "arc-agi>=0.9.9"
python local/gauntlet.py --games all --rollouts 20 --workers 16
```

## Ograniczenia solvera

- BFS znajduje **krótkie** rozwiązania; poziomy wymagające >~15 akcji nie wpadną przy
  małym budżecie — trzeba `--budget 50000+` albo beam z lepszą heurystyką nowości.
- Deduplikacja po klatce zakłada, że stan jest widoczny. Gry z ukrytym stanem
  (licznik, klucze) mogą zostać przycięte błędnie → `--beam 3` jako obejście.
- Przestrzeń klików (ACTION6) to 64×64; obecnie próbkujemy tylko piksele nie-tła.
  To główne miejsce na poprawę (segmentacja + kandydaci na obiekty).
- Gry, w których proste akcje nie zmieniają klatki (ft09, sc25, lp85: 2–8 węzłów),
  wymagają klików albo innej akcji specjalnej — dla nich BFS po kierunkach jest ślepy.
