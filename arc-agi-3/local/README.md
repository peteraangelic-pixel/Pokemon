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

### `rust_bridge.py` + `segment-batch` / `clicks` — **Rust w pętli**

To jest odpowiedź na „po co mi Rust". Silnik gier jest w Pythonie i tego nie zmienimy
(stan gry to graf obiektów Pythona — Rust go nie dotknie). Ale **percepcja** (segmentacja
klatki na obiekty) jest w Rust i to ona decyduje, czy w grach klikowych w ogóle
trafiamy w cel.

Protokół: JSONL na stdin → JSONL na stdout, Rayon rozrzuca linie po rdzeniach.
Jeden proces na **całą partię**, nie na klatkę.

```bash
cd rust && cargo build --release      # raz
cd .. && python local/bench_rust.py --scale 1000000   # zmierzone na Twoim PC
```

W Pythonie `rust_bridge.py` sam wykrywa binarkę (`rust/target/release/arc3`, `ARC3_BIN`
albo `which arc3`) i **spada na czystego Pythona, gdy jej nie ma**. Dlatego solver
działa niezależnie od toolchainu — tylko wolniej.

Zmierzone w sandboxie (2 rdzenie, sam fallback Pythona):

```
python clicks : 5.677 ms/frame  ->  1e6 klatek = 1.58 h
```

Rust na tym samym zadaniu mierzy `bench_rust.py` u Ciebie — nie podaję liczby,
której nie zmierzyłem. Uwaga na uczciwość porównania: `segment_layer` w Rust liczy
**więcej** (kontury, zawieranie, hashe obiektów) niż mój fallback, więc różnica
Rust/Python jest raczej niedoszacowana niż przeszacowana.

### Skutek: klikowe gry dały się rozwiązać

Przed mostkiem solver losował piksele nie-tła — w grach klikowych to loteria:

| gra | strategia `naive` | strategia `objects` (segmentacja) |
|---|---|---|
| vc33 | ✗ 85 węzłów, 0 poziomów | ✓ **3 kliki**, poziom 1 |
| lp85 | ✗ 17 węzłów, 0 poziomów | ✓ **5 klików**, poziom 1 |
| ft09 | ✗ | ✗ (32/200 klików zmienia klatkę — potrzebny większy budżet, nie lepsze kandydaty) |
| sc25 | ✗ | ✗ (0/81 kandydatów zmienia klatkę) |

Czyli: 4 gry z gwarantowanym poziomem 1 zamiast 2. Na Twoich 16 rdzeniach ten sam
przebieg idzie ~8x szybciej i z większym budżetem.

### `engine.py`, `policies.py` — silnik i polityki
`random`, `anti-reverse`, `heuristic` (8 ewoluowalnych parametrów), `solution` (replay
biblioteki + fallback). Polityki są LLM-free — to nie jest zamiennik Duck harnessu,
tylko szybki sygnał fitness i warstwa "gwarantowanych" ruchów.

## Czego Rust tu NIE zrobi (i dlaczego to nie jest wymówka)

Rust przyspiesza **percepcję i analizę**: segmentację klatki, wykrywanie obiektów,
przeszukiwanie nagrań. Nie przyspieszy **pętli epizodu**, bo:

- `arcengine` to Python; `perform_action` mutuje graf obiektów Pythona,
- `copy.deepcopy(game)` jest w C Pythona i kosztuje 3–14 ms,
- żaden z tych kosztów nie da się przenieść do Rusta bez przepisania silnika.

Kolejność kosztów w solverze jest jednoznaczna: **deepcopy (3–14 ms) ≫ krok gry
(0.10 ms) ≫ segmentacja (0.005–0.04 ms)**. Dlatego Rust pomaga tam, gdzie
przetwarzamy **dużo klatek naraz** (analiza nagrań, kandydaci do klików), a nie tam,
gdzie chodzimy po drzewie stanów.

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
4. **Segmentacja + analiza klatek w Rust** — podłączone przez `rust_bridge.py`.
   `rust/BENCHMARK.md` podaje 276× (salt) i 121× (blobs) dla jądra `segment_layer`
   na 4 wątkach, mierzone w GitHub Actions. Twoja liczba wyjdzie z
   `python local/bench_rust.py --scale 1000000`.

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
