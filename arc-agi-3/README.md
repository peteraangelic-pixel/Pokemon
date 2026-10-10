# ARC-AGI-3 — analiza harnessu i plan poprawy

Konkurs: [ARC Prize 2026 — ARC-AGI-3](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3)
Baseline: [Tufalabs/duck-harness](https://github.com/Tufalabs/duck-harness) (MIT) — 55,89 RHAE, 1. miejsce na leaderboardzie
Deadline: **2 XI 2026** (entry: 26 X) · wyniki 4 XII 2026
Do wzięcia: **$75 000** dla top-5 ($40k/$15k/$10k/$5k/$5k) · **28 aktywnych teamów**

---

## 1. Jak działa The Duck

```
vLLM (Qwen3.6-27B-FP8, 1 GPU, ctx 32768)
  └─ ToolAgent  ── jedno narzędzie: `python` (REPL, 30 s limit, output 1024 tok.)
       ├─ Stan wstrzykiwany do REPL-a:
       │    current_frame (.ascii / .segmentation / .step / .level / .shape)
       │    previous_frame, history[], transitions[], last_action_result, valid_actions
       │    action([...]) — wykonuje ruchy w środowisku z poziomu Pythona
       └─ World model: 7 slotów tekstowych przenoszonych między turami
```

**Percepcja (3 kanały):**
1. `current_frame.ascii` — siatka 64×64 jako litery kodujące kolory ARC (prompt zabrania skanowania całości)
2. `current_frame.segmentation` — **główny widok**: obiekty 4-connected, każdy z `id, color, hash, pixels, boundary, children` + `adjacency_list`
3. Obraz PNG aktualnej siatki (upscale ×4), tylko tryb `current_grid`

**Zarządzanie kontekstem:**
- Okno 32 768 tokenów; `_trim_messages_for_context` usuwa najstarsze bloki aż zmieści się w budżecie
- `_keep_recent_history_turns` → zostaje ostatnie **30 tur asystenta**
- `_persistent_history_messages` przenosi to, co przetrwało, do kolejnej tury

**World model** (`_summarized_knowledge`) — 7 slotów:
`world_model` · `goal_model` · `action_model` · `recent_findings` · `open_questions` · `current_plan` · `cross_level_notes`

Model emituje bloki w tekście (`World model: ...`), są parsowane (`_extract_labeled_blocks`) i wstrzykiwane do następnego promptu jako
*„Working world model carried from earlier turns:"*

---

## 2. Siedem słabych punktów — i co z tym zrobić

Uporządkowane według **spodziewanego wpływu / kosztu**.

### 🥇 A. Brak pamięci między passami (największa luka)
**Fakt:** `configs/inference.json` → `n_passes: 20`. `solver.py:1212-1229` — każdy pass tworzy nowy `_HarnessGameSession` → nowy `runtime_dir` → `_ensure_session()` (tool_agent.py:975-985) zeruje `_history_messages` **i** `_summarized_knowledge`.
**Skutek:** wszystkie 20 passów odkrywa tę samą grę od zera. Wiedza z passu 1 przepada.
**Fix:** zapis world modelu do pliku kluczowanego `game_id` (nie `runtime_dir`), ładowany przy starcie sesji.
**Wpływ:** passy 2–20 startują z wiedzą passu 1. Przy metryce RHAE (efektywność akcji względem człowieka) to prawdopodobnie największa pojedyncza dźwignia w całym harnessie.

### 🥈 B. Wiedza kasowana przy przejściu poziomu
**Fakt:** `tool_agent.py:1113-1126` — przy `level_transition` / `run_complete` / `game_over` kasowane jest **6 z 7 slotów**. Zostaje tylko `cross_level_notes`.
**Skutek:** a ARC-AGI-3 jest zbudowany na założeniu, że *„Levels often build on earlier mechanics"*. Mechanizm transferu istnieje, ale jest w praktyce wyłączony.
**Fix:** (1) jawna instrukcja w prompcie: przy końcu poziomu wpisz przenaszalne mechaniki do `Cross-level notes`; (2) przy przejściu poziomu **migruj** treść do `cross_level_notes` zamiast kasować.
**Wpływ:** wysoki, koszt niski — czysta zmiana w logice + prompt.

### 🥉 C. Nadpisywanie zamiast akumulacji
**Fakt:** `tool_agent.py:1105-1111` → `self._summarized_knowledge[key] = value`. Czysty overwrite.
**Skutek:** jeśli model w którejś turze pominie fakt, znika on bezpowrotnie.
**Fix:** merge z historią (append + dedup), kasowanie tylko przy jawnej sprzeczności.

### D. Brak pamięci negatywnej
**Skutek:** model nie ma gdzie zapisać „akcja X to no-op" / „hipoteza Y obalona" — więc testuje te same ślepe zaułki w kółko, w każdym passie.
**Fix:** nowy slot `Ruled out` + instrukcja: zapisz obalone hipotezy i nie testuj ich ponownie.
**Wpływ:** uderza bezpośrednio w RHAE — mniej zmarnowanych akcji.

### E. Kruchy parser etykiet (łatwy, pewny zysk)
**Fakt:** `_extract_labeled_blocks` (tool_agent.py:227-256) wymaga, by linia zaczynała się od `label:` po zdjęciu wiodących `-`/`*`. `**World model:**` (markdown bold) **nie zadziała** — po zdjęciu `*` zostaje `**World model:` → brak dopasowania.
**Skutek:** wiedza, którą model faktycznie wyemitował, po cichu przepada.
**Fix:** przed dopasowaniem zdejmuj markdown (`*`, `_`, `#`, backticki), akceptuj też `-` i `=` jako separator.
**Koszt:** ~15 minut. Czystszy zysk niż większość pomysłów modelowych.

### F. Percepcja bez sygnału czasowego
**Fakt:** obraz to pojedynczy PNG bieżącej siatki. Brak poprzedniej klatki, brak delty, brak wyróżnienia zmienionych komórek.
**Fix (do przetestowania):** (a) obraz prev|current obok siebie; (b) overlay delty; (c) kompaktowy diff segmentacji w tekście. 64×64 przy upscale ×4 = 256×256 — bardzo tanio, więc (a) i (b) mieszczą się w budżecie.
**Uwaga:** Tufa Labs raportowało, że *„gains came from multimodality and better base models, not hand-built tools"* — więc więcej multimodalności idzie zgodnie z ich wynikiem. Ale ich drugie zdanie jest ostrzeżeniem: **dorabianie specjalistycznych narzędzi szkodzi**. Trzymać się czystego, ogólnego interfejsu.

### G. Konfiguracja — tanie eksperymenty A/B
`analyzer.temperature: 0.6` · `top_p: 0.95` · `top_k: 20` · `tool_output_tokens: 1024` · `max_runtime_minutes: 45` · `n_passes: 20`
Jeśli naprawimy punkt A, opłaca się **rozdzielić role passów**: pass 1 z wysoką temperaturą (eksploracja, buduje wiedzę), passy 2–20 z niską (~0.2–0.3) korzystają z zapisanej wiedzy. Koszt eksperymentu: prawie zero.

---

## 3. Metryka — i dlaczego wygrywa się oszczędnością, nie mocą

**RHAE** (Relative Human Action Efficiency), per level, potem średnia:

```
RHAE = (1/|L|) · Σ_l  min( H_l / A_l , 1.15 )²
```

`H_l` = mediana akcji człowieka na tym levelu · `A_l` = akcje agenta · późniejsze levele ważą więcej.

**Trzy konsekwencje, które rozstrzygają o strategii:**

| Agent zużywa | Wynik za level |
|---|---|
| tyle samo akcji co człowiek | 1.00 |
| 2× więcej | **0.25** |
| 5× więcej | **0.04** |
| 10× więcej | **0.01** |
| mniej niż człowiek | do **1.32** (cap 1.15²) |

1. **Kara jest kwadratowa.** Zmarnowane akcje niszczą wynik znacznie szybciej, niż intuicja podpowiada.
2. **Cap 1.15² premiuje bycie lepszym od człowieka** — jest z czego brać, nie tylko do odrabiania strat.
3. **Mniejsza liczba akcji = wyższy wynik *i* mniej obliczeń.** Poprawki z punktu 2 (pamięć, transfer między poziomami, `Ruled out`) idą dokładnie w tę samą stronę co budżet czasu. **To nie jest kompromis — to jedno i to samo.**

Zestaw ewaluacyjny: **25 gier publicznych + 55 prywatnych** (to one dają wynik).

---

## 4. ⚠️ Budżet obliczeniowy — co jest naprawdę ograniczeniem

### Fakty o sprzęcie

| Gdzie | Sprzęt | Czas | Internet |
|---|---|---|---|
| **Kaggle (finał)** | **RTX 6000 (96 GB VRAM)** — zmienione z H100 w trakcie konkursu; właśnie dlatego limit poszedł z 6 h na **9 h** | 9 h | wyłączony |
| Kaggle (iteracja) | T4 ×2 / P100 | 9 h | wyłączony |
| Lokalnie | 5950X (16C) + 64 GB RAM | bez limitu | jest |

RTX 6000 ma **96 GB VRAM** — Qwen3.6-27B FP8 (~27 GB) mieści się z ogromnym zapasem na KV cache i batching.

### Czy potrzebne jest mocne GPU? **Tak — do inferencji.**

Agent to LLM 27B. Tu nie ma drogi na skróty:

- **5950X + 64 GB RAM** może *technicznie* utrzymać 27B w Q4/FP8 (16–27 GB), ale CPU inference jest ograniczony przepustowością pamięci (~50 GB/s DDR4) → rzędu **1–3 tokeny/s** (jeden token wymaga przeczytania całych wag).
- Duck na klastrze: 25 gier × 20 passów na **2×B200, 13 h**, przy 32 równoległych jobach.
- Szacunek: RTX 6000 ≈ ¼ przepustowości B200. Jeden pass po 55 grach ≈ **rzędu 10 h** — czyli **minimalnie ponad limit**.

⚠️ To są szacunki z grubymi zaokrągleniami. **Trzeba to zmierzyć, nie zgadywać.**

### Co NIE jest ograniczeniem: środowisko gry

Oficjalny **ARC-AGI-3 Kaggle Starter** ([github.com/arcprize/ARC-AGI-3-Kaggle-Starter](https://github.com/arcprize/ARC-AGI-3-Kaggle-Starter)): paczka `arc-agi` z PyPI hostuje **ten sam silnik gier, który odpala bramka Kaggle**. `make play-local` = agent gra w prawdziwe gry **lokalnie, w sekundach, bez GPU**.

Czyli: pętlę agenta, logikę akcji, obsługę ramek, scoring — **wszystko można iterować lokalnie na 5950X**. Tylko inferencja LLM wymaga GPU.

### Podział pracy (zatwierdzony)

| Warstwa | Gdzie | Język |
|---|---|---|
| Inferencja LLM (27B) | **Kaggle RTX 6000** | — (vLLM) |
| Pętla agenta, logika, testy | **lokalnie, 5950X** | Python |
| Segmentacja 64×64, flood fill, diffy ramek | **obie** | **Rust** |
| Replay/przeszukiwanie offline, analiza setek transkryptów | **lokalnie, 16 rdzeni** | **Rust + rayon** |
| Precompute offline (cache pre-solve, tablice ruchów) | **lokalnie**, potem jako artefakt do notebooka | **Rust + rayon** |
| A/B harness, liczenie RHAE | lokalnie | Rust |

**Rust + rayon ma sens wszędzie poza samą inferencją LLM** — a to jest ~99 % czasu GPU, więc nie koliduje. Największy zysk: **precompute offline.** Zgłoszenie z papera (arXiv 2605.25931) osiągnęło **RHAE = 0.30 solverem BFS z cache pre-solve** — czyli przeniosło pracę z czasu gry na czas offline. To jest dokładnie miejsce, gdzie 16 rdzeni i rayon robią różnicę.

### GitHub Actions — ważne zastrzeżenie

**Standardowe runnery Actions nie mają GPU.** Nie da się tam odpalić 27B. Actions nadaje się do: budowania i testowania crate'a Rust, CI, analizy zakomitowanych artefaktów (transkrypty, logi). Free tier: 4 vCPU.

### ⚠️ Do sprawdzenia przed założeniem

Czy precompute (cache pre-solve, wyszukane sekwencje) można wnieść do notebooka jako artefakt. Regulamin pozwala na „freely & publicly available external data... including pre-trained models" — ale gotowy cache rozwiązań to szara strefa między „danymi" a „rozwiązaniem". Fakt, że istnieją zgłoszenia oparte na `offline pre-solve cache`, sugeruje że to przechodzi — **ale trzeba to potwierdzić na forum konkursu przed włożeniem w to pracy.**

---

## 5. Kolejność pracy (budżet: 22 dni)

| Dzień | Krok | Gdzie | Cel |
|---|---|---|---|
| 1 | `ARC-AGI-3-Kaggle-Starter` + `make play-local` | lokalnie | pętla działa w sekundach, bez GPU |
| 1–2 | Szkielet crate'a Rust (`grid`, `replay`, `score`), CI na Actions | lokalnie | fundament pod resztę |
| 2–3 | Odpalić Ducha bez zmian na Kaggle (T4, potem RTX 6000) | **Kaggle** | liczba baseline'u + **realny czas passu** |
| 3–5 | **E** (parser etykiet) + **D** (`Ruled out`) | lokalnie | odzyskać wiedzę, która dziś przepada |
| 5–8 | **B** (transfer między poziomami) | lokalnie | mechaniki idą dalej |
| 8–13 | **A** (pamięć między passami) | lokalnie | passy 2–N startują z wiedzą |
| 13–17 | **Precompute offline w Rust+rayon** (BFS / cache pre-solve) | **lokalnie, 16C** | przenieść pracę z czasu gry na czas offline |
| 17–20 | **G** (temperatura, podział ról passów) + pomiar, czy mieścimy się w 9 h | Kaggle | wycisnąć % z działającego |
| 20–22 | Zapas + finałowa submision | Kaggle | — |

**Zasady:**
- Każdy krok mierzony na 25 grach publicznych. Brak wzrostu = powrót do poprzedniego wariantu. **Nie kumulujemy zmian bez pomiaru.**
- Iteracja lokalnie (`make play-local`), Kaggle tylko do pomiarów, które wymagają GPU. RTX 6000 jest zarezerwowany dla tego konkursu i szybko pali kwotę — nie marnować go na wczesne eksperymenty.
- **Pierwszy pomiar to czas, nie wynik.** Bez znajomości realnego czasu passu nie da się zaplanować dni 13–22.

---

## 5. Linki

- Konkurs: https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3
- Repo baseline'u: https://github.com/Tufalabs/duck-harness
- Write-up Tufa Labs na Kaggle (diskusja #717133): https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/discussion/717133
- Blog: https://tufalabs.ai/research/duck-harness/
- Stan i przekazanie dalej: `STATUS.md`
