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

## 3. ⚠️ Ograniczenie, które rozstrzyga o wszystkim: 9 godzin

Kaggle: **notebook GPU ≤ 9 h, CPU ≤ 9 h, bez internetu.**

Tymczasem config z repo: `25 gier × 20 passów × 45 min`. To się **nie mieści** — nawet przy `concurrent_jobs: 32` (na Kaggle mamy jedną kartę).

**Wniosek operacyjny:** pierwszy problem do rozwiązania to nie pomysł, tylko **budżet czasu**. Trzeba:
- zredukować `n_passes` (np. 4–6) i/lub `max_runtime_minutes`
- uruchamiać gry sekwencyjnie na jednej karcie, a nie 32 równolegle
- zmierzyć realny czas jednego passu na Kaggle przed planowaniem reszty

Dlatego **kolejność ma znaczenie**: najpierw punkty **E → B → A** (tanie, duży wpływ na jakość *jednego* passu), dopiero potem skalowanie.

---

## 4. Kolejność pracy (zgodna z budżetem 22 dni)

| Dzień | Krok | Cel |
|---|---|---|
| 1 | Odpalić `taaf-duck-harness-kaggle-share.ipynb` na Kaggle **bez zmian** | liczba baseline'u + realny czas passu |
| 2–4 | **E** (parser) + **D** (`Ruled out`) | odzyskać wiedzę, która dziś przepada |
| 4–7 | **B** (transfer między poziomami) | mechaniki przenoszone dalej |
| 7–12 | **A** (pamięć między passami) | passy 2–20 startują z wiedzą |
| 12–16 | **F** (percepcja: delta/prev-frame) — tylko jeśli budżet pozwala | sygnał czasowy |
| 16–20 | **G** (temperatura, podział ról passów) | wycisnąć % z już działającego |
| 20–22 | Czas zapasu + finałowa submision | — |

**Zasada:** każdy krok mierzony na 25 grach publicznych, wracamy do poprzedniego wariantu, jeśli nie ma wzrostu. Nie kumulujemy zmian bez pomiaru.

---

## 5. Linki

- Konkurs: https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3
- Repo baseline'u: https://github.com/Tufalabs/duck-harness
- Write-up Tufa Labs na Kaggle (diskusja #717133): https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/discussion/717133
- Blog: https://tufalabs.ai/research/duck-harness/
- Stan i przekazanie dalej: `STATUS.md`
