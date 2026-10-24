# Weryfikacja ustaleń innych gałęzi — co potwierdziłem w kodzie, a co jest błędne

**Data: 24.10.2026, wieczór. Gałąź: `arena/c87f7a48-pokemon`.**

Przeczytałem ustalenia czterech innych sesji i **sprawdziłem w kodzie** każde twierdzenie,
które da się sprawdzić bez Kaggle API i bez GPU. Podział jest ostry: trzy rzeczy
potwierdziłem co do linii, trzy są **błędne** i kosztowałyby slot, a jedna otwiera dźwignię,
której nikt nie zauważył.

Zasada, którą stosowałem: czytam ich wnioski jako **hipotezy do sprawdzenia**, nie jako fakty.
Sam w tej sesji opublikowałem trzy niezweryfikowane intuicje, które pomiar obalił
(FAKTY §1bis(a), (e) i sprostowanie w §1bis(b)) — więc tym bardziej nie wolno mi przepisywać
czyichś.

Źródła: `arena/a450b00f-pokemon` (katalog `arc-agi-3/duck-v8/`, commit `33a9f7e`),
`arena/5ed750ef-smak-domu-konkurs` (gałąź ARC), dwie gałęzie Gemma-konkurs.

---

## 1. POTWIERDZONE: bug `-f` w `ops.py` — to on blokuje wszystkie zgłoszenia

Najwyższa stawka spośród wszystkich twierdzeń, więc sprawdziłem ją w ich własnym pliku
(`arc-agi-3/kaggle/ops/ops.py` @ `arena/5ed750ef-…`, blob `e8a1c44`). **Jest prawdziwa**,
i to z pełnym łańcuchem wywołań, którego tamta gałąź nie rozpisała:

```
L434  def op_auto_submit(args, out_dir):
L459      "file": str(args.get("file") or "arc-agi-3/kaggle/results.submission.parquet"),  ← ŚCIEŻKA
L463      text += "== submit ==" + op_submit(sub_args, out_dir)                            ← przekazuje ją dalej
L124  def op_submit(args, out_dir):
L136      file = str(args.get("file") or "submission.parquet")                             ← default POPRAWNY, ale
                                                                                              NIE UŻYTY, bo args["file"] jest ustawione
L140      cmd += ["-f", file, "-m", msg]                                                   ← do CLI idzie ŚCIEŻKA z ukośnikami
```

Kluczowy niuans, który tłumaczy **całą** historię: `op_submit` ma poprawny default
(`"submission.parquet"`), więc każda ścieżka wywołania, która NIE ustawia `file`, działa.
Dlatego 2 submity przeszły (23.94 i 26.25), a 12 padło z 400 — te 12 szło przez
`op_auto_submit`, który zawsze podstawia ścieżkę. To spójne z ich danymi 12:2 i usuwa
ich własne zastrzeżenie („może winny jest status ERROR kernela"): zmienną rozstrzygającą
jest obecność ścieżki w `-f`, nie status.

Kaggle CLI traktuje `-f` jako **nazwę pliku wyjściowego kernela**, nie ścieżkę w repo.

**Naprawa: jedna linia** — `L459` na `"submission.parquet"`. Zero GPU, zero slotu.
To jest pierwsza rzecz do zrobienia przed czymkolwiek innym, bo bez tego każdy nowy kernel
jest bezwartościowy (nie da się go zgłosić automatycznie).

Zastrzeżenie, którego nie zdejmuję: nie mam dostępu do Kaggle API, więc nie wykonałem
submitu testowego. Dowód jest z kodu i z ich danych 12:2, nie z mojego uruchomienia.

---

## 2. BŁĘDNE: „`_PERSISTENT_HISTORY_ASSISTANT_TURNS = 30` (twardy limit)"

To twierdzenie krążyło jako dowód, że Duck gubi kontekst. **Jest nieprawdziwe dla duck-v7.**

W spatchowanym drzewie (`tool_agent.py`, stan po patchu Franzena) nie ma takiej stałej jako
limitu — jest funkcja czytająca env:

```
L297:    return _get_env_int("ARC3_HISTORY_ASSISTANT_TURNS", 30)
```

czyli **30 to tylko wartość domyślna**. A komórka 9 ich notebooka ustawia:

```
'ARC3_HISTORY_ASSISTANT_TURNS': 150
```

**Efektywny limit w duck-v7 to 150, nie 30 — pięć razy więcej.** Docstring tej samej funkcji
mówi dodatkowo dwie rzeczy, które zmieniają interpretację:

- licznik dotyczy **wiadomości assistant**, nie tur analizatora: „a turn that inspects, then
  computes, then acts spends three of them, so 30 is closer to ten or fifteen turns of real
  history than to thirty" — więc 150 ≈ 50–75 realnych tur;
- „0 or negative disables the cap entirely, leaving the token budget as the only limit".

Ktoś, kto wydałby slot na „podniesienie limitu historii", **poprawiałby coś, co już jest
poprawione**. To jest dokładnie ten rodzaj błędu, który kosztuje dzień przy 1 zgłoszeniu/dzień.

---

## 3. BŁĘDNE: „Duck nie ma żadnego streszczania — tylko przycinanie"

Teza brzmiała: harness przycina kontekst zamiast go streszczać, a to jest ta dźwignia, która
w kontrolowanym eksperymencie dała 4.9×. **Mechanizm kompakcji w Ducku ISTNIEJE** — jest
tylko **wyłączony przełącznikiem env**.

W kodzie (patch Franzena):

```
def _memory_sections_disabled() -> bool:
    """ARC3_MEMORY_SECTIONS=off removes the persistent-memory mechanic entirely:
    no carried block, no section guidance, no nudges, no parsing, and the
    world-model lines drop out of the system prompt too. The model is left to
    reason from history alone, which is what an unmodified run does before any
    of this machinery existed."""
    return os.environ.get("ARC3_MEMORY_SECTIONS", "").strip().lower() == "off"

def _memory_section_labels():
    mode = os.environ.get("ARC3_MEMORY_SECTIONS", "").strip().lower()
    if mode == "slim":   return ("World model", "Plan")
    if mode == "medium": return ("World model", "Plan", "Action model")
    return None          # wszystkie sekcje
```

Sekcje to trwała pamięć strukturalna: `World model`, `Goal model`, `Action model`,
`Recent findings`, `Open questions`, `Plan` — wstrzykiwane do promptu przez
`_summarized_knowledge_lines()` (`tool_agent.py:1236`), czyli **przeżywają przycinanie
historii**. To jest dokładnie wzorzec „kompakcja zamiast kasowania".

A komórka 9 ich notebooka ustawia:

```
'ARC3_MEMORY_SECTIONS': 'off'
```

Więc prawdziwe zdanie brzmi: **Duck ma zaimplementowaną kompakcję z czterostopniową skalą
(`off` / `slim` / `medium` / wszystkie) i v7 jedzie na `off`.** To nie jest brak funkcji —
to wyłączona funkcja, a włączenie jej jest **jednoliniową zmianą env, bez patcha**.

Uczciwe zastrzeżenie, które muszę dodać: ich własna historia mówi, że mechanizmy pamięciowe
szkodzą (v5-world-model 23.94 < v2 24.66, a v7 ma `ARC3_WORLD_MODEL=0`). **Nie wiem**, czy
v5 jechał z `ARC3_MEMORY_SECTIONS` włączonym — nie mam konfiguracji v5. Więc to jest
kandydat na smoke, **nie** pewniak. Rozstrzyga jeden grep po konfiguracji wariantu v5.

Trzecia rzecz, którą trzeba tu powiedzieć uczciwie: przycinanie **też** jest skonfigurowane
świadomie i ma własne, łagodniejsze mechanizmy — `ARC3_MIDDLE_TRUNCATION=1`,
`ARC3_HISTORY_TURN_DRAIN=30`, `ARC3_HISTORY_DRAIN_COALESCE=1`,
`ARC3_CONTEXT_DRAIN_TOKENS=58k`. To nie jest „kasowanie najstarszych bloków i nic więcej".

---

## 4. ROZSTRZYGNIĘTE: pytanie o `reasoning` vs `reasoning_content`

Tamta gałąź zostawiła to jako otwarte ryzyko („jeśli serwer ignoruje pole, dźwignia nr 1 jest
pozorna"). Kod już na nie odpowiada — i to z pomiarem w docstringu:

```
def _reasoning_history_keys() -> tuple[str, ...]:
    """Backends disagree: OpenRouter returns and reads `reasoning`, while
    llama.cpp returns `reasoning_content` and its chat template reads ONLY
    that - so reasoning stored under `reasoning` is silently discarded there
    (measured: 69 prompt tokens vs 3670 for the same text under the two keys)."""
```

Komórka 9 ustawia `'ARC3_REASONING_HISTORY_KEY': 'reasoning_content'`, czyli **wybrali
wariant zachowujący stan rozumowania**, i to świadomie (znają objaw: „a dropped reasoning
block is invisible except as prompt growth that falls short of the tokens generated").

Czego nadal nie wiem: czy **SGLang/vLLM** (ich serwer) czyta `reasoning_content` tak jak
llama.cpp. Docstring wymienia OpenRouter i llama.cpp, nie SGLang. Rozstrzyga to pomiar
wzrostu promptu między turami w prawdziwym logu — jedna liczba, zero GPU.

---

## 5. NIEZALEŻNE POTWIERDZENIE mojego twierdzenia o capie (najważniejsze merytorycznie)

Ich analiza r019 (gałąź Gemma `c4eeb067`) i moje twierdzenie z FAKTY §2 to **ten sam wynik,
wyprowadzony dwiema niezależnymi drogami**:

| | ich sformułowanie | moje sformułowanie |
|---|---|---|
| obserwacja | 17 z 27 ukończonych poziomów siedzi na capie 115; efektywność 0.83–1.00 (średnio ~0.95) | przy `akcje ≤ 1.0724·baseline` każdy ukończony poziom dostaje 115, więc cap **zawsze** wiąże |
| wniosek | „nie ma czego poprawiać w efektywności — maks. +1.4 pkt" | „cała praca nad efektywnością ruchów jest warta **1.75 pkt** łącznie" |
| co rządzi wynikiem | procent ukończonej **wagi** | `score_game = 100 · Σ(w ukończonych) / Σ(w wszystkich)` |

Dwa niezależne rachunki (ich: per poziom z r019; mój: algebraicznie z `game.py:381-413`
plus weryfikacja co do setnej na tn36 3.57 i ls20 3.27) dają tę samą liczbę. **To jest
najsilniejszy pojedynczy fakt w całym audycie** i powinien być traktowany jako ustalony:

> Wynik zależy wyłącznie od tego, **KTÓRE** poziomy zostały ukończone — nie od tego,
> iloma akcjami.

### Konsekwencja dla ich patcha replay (0004-replay) i dla `game_weights`

Z twierdzenia o capie wynika bezpośrednio, że **replay nie dodaje punktów**: odtwarzanie
rozwiązanego poziomu zmniejsza liczbę akcji na poziomie, który **już i tak** dostaje 115.
Oni sami doszli do tego samego („replay podnosi wyłącznie efektywność, a ta jest już 0.95"),
więc nie jest to spór — tylko dwie drogi do tego samego.

Ich `RESET-VERDICT.md` domyka to od drugiej strony: przy `ONLY_RESET_LEVELS=true`
(sprawdziłem — komórka 9, linia 50: `os.environ["ONLY_RESET_LEVELS"] = "true"`) śmierć
**nie** cofa do poziomu 1, a `n_passes=1` nie daje drugiego przejścia. Czyli nie ma
powtórnych przejść przez znane poziomy, które replay mógłby zdyskontować.

**Uwaga na moją własną korzyść z tego samego rozumowania** — żeby nie wyglądało, że
uzasadniam swój patch: mój `0004-level-token-cap` **nie** jest dźwignią efektywnościową,
więc twierdzenie o capie go nie kasuje. On tnie marnotrawstwo na poziomie, który **nigdy nie
został ukończony** (r019: 35% tokenów i akcji poszło na taki poziom; tn36 86%, ls20 91%),
a odzyskany budżet idzie na poziomy, które mogą zostać ukończone. Różnica jest zasadnicza:

| patch | co oszczędza | czy to marnotrawstwo istnieje w realnej konfiguracji |
|---|---|---|
| ich 0004-replay | ponowne przechodzenie **znanych** poziomów | **NIE** (pin `ONLY_RESET_LEVELS` + `n_passes=1`) |
| mój 0004-level-token-cap | tokeny na poziomie **nigdy nie ukończonym** | **TAK** (zmierzone w r019: 35%) |

Oba są dźwigniami budżetowymi, nie zdolnościowymi. Ale tylko jeden z nich celuje
w marnotrawstwo, które faktycznie występuje.

---

## 6. KOLIZJA NUMERACJI PATCHY — do naprawienia przed jakimkolwiek kernelem

**Dwie gałęzie niezależnie stworzyły patch o numerze `0004` dla tego samego harnessa:**

| plik | gałąź | co robi |
|---|---|---|
| `0004-level-token-cap.patch` (+ `0004-standalone-…`) | `c87f7a48` (ta) | budżet tokenów na poziom + darmowy RESET poziomu + marginal abandon |
| `0004-solved-level-replay.patch` | `a450b00f` | nagrywanie i odtwarzanie rozwiązanych poziomów |

To jest pułapka gotowa do odpalenia: `ARC3_VARIANT["patches"]` w ich notebooku zawiera nazwy
`0001…0004`, więc dwie różne treści pod jedną nazwą dają niejednoznaczność, a oba patche
wchodzą w `tool_agent.py` / `solver.py`. **Rekomendacja: mój zostaje `0004`, replay powinien
dostać `0005`** (mój jest wcześniej zweryfikowany łańcuchem `git apply` na pristine drzewie
i ma 16 testów jednostkowych; ale to decyzja organizacyjna, nie techniczna — ważne, żeby
numery były rozłączne).

Dodatkowo, z mojego własnego pomiaru (FAKTY §1bis, `results/verification_notebook.txt`):
**żaden patch nie nakłada się po `0003b`** w tym samym rejonie `solver.py`
(`error: patch failed: solver.py:46`). Kolejność i sloty mają znaczenie — przed budową
kernela trzeba przepuścić cały łańcuch przez `git apply` z `check=True`, dokładnie tak jak
robi to komórka 10.

---

## 7. SPROSTOWANIE MOICH WŁASNYCH DOKUMENTÓW: próg nagród jest nieaktualny

Miałem zapisane (FAKTY §6, DIAGNOZA §1, README): **NVARC3 40.97 = 5. miejsce / próg nagrody**,
lider Yi-Chia Chen 62.96, Tufa Labs 56.52. To snapshot z **10–11.10** i jest **przedawniony**:

- ich CHAT-LOG z 14.10: Tufa **68.91**, Chen **67.49** — lider >68 (zgodne z tym, co mówił
  użytkownik: „lider ma ponad 68");
- nagrody są **za miejsca**, nie za próg punktowy ($75k/40k/15k/10k/5k/5k), więc „40.97"
  nie jest żadną stałą barierą — to było po prostu 5. miejsce w tamtym snapshocie,
  a cel przesuwa się razem z tabelą;
- przy liderze 68.91 wynik „45+" to dziś okolice **miejsc 5–8**, nie podium.

Co z tego **nie** wynika: arytmetyka „+1 poziom na grę" pozostaje ważna, bo jest liczona
z ich własnego r019 (27.21 → 44.8 przy +1 poziomie), a nie z pozycji w tabeli. Zmienia się
tylko to, **ile** poziomów trzeba, żeby wejść w nagrody — a tego bez aktualnego snapshotu LB
nie policzę. Wszystkie trzy dokumenty mają tę korektę dopisaną w miejscu.

---

## 8. Czego NIE zweryfikowałem (uczciwie)

- **Submitu testowego** — nie mam dostępu do Kaggle API. Bug `-f` jest dowiedziony z kodu
  i z ich danych 12:2, nie z mojego uruchomienia.
- **Czy v5 (23.94) jechał z `ARC3_MEMORY_SECTIONS` włączonym** — nie mam konfiguracji v5.
  Bez tego nie wiem, czy włączenie kompakcji jest już zmierzone jako szkodliwe.
- **Czy SGLang czyta `reasoning_content`** — docstring wymienia OpenRouter i llama.cpp.
- **Eksperymentu 4.9×** (7.8% → 38.3%) — nie mam źródła pierwotnego, tylko ich opis.
  Traktuję go jako przesłankę, nie obietnicę: był na innym modelu i innej infrastrukturze.
- **`game_weights` jako mechanizmu** — ich wniosek („tylko diagnostyka HTML") przyjmuje
  za nimi; nie czytałem `benchmark.py` w tym miejscu.
- **Ile punktów da jakakolwiek zmiana** — zero pomiarów po stronie którejkolwiek gałęzi.
  Pierwszy pomiar to smoke na Kaggle, i przy 1 zgłoszeniu/dzień to jest najdroższy zasób
  w całym projekcie.

---

## 9. Kolejność, którą bym wykonał (na podstawie powyższego, nie na podstawie wrażeń)

1. **`ops.py:459` → `"submission.parquet"`** (1 linia, 0 GPU, 0 slotu). Bez tego auto-submit
   jest martwy i każdy następny punkt jest bezwartościowy.
2. **Smoke na wersji COMPLETE, nie ERROR** — to jednocześnie test rozstrzygający, czy 400
   było wyłącznie z `-f`.
3. **Patch 0004 (budżet poziomu)** przez `tools/make_notebook_patch.py` — celuje w jedyne
   zmierzone marnotrawstwo, które istnieje w realnej konfiguracji (35% tokenów na poziom
   nigdy nie ukończony). Kill-switch `ARC3_LEVEL_TOKEN_CAP=0`.
4. **`ARC3_MEMORY_SECTIONS`: `off` → `slim`** jako osobny smoke (jedna linia env, bez patcha)
   — ale dopiero po rozstrzygnięciu, czy v5 już tego nie testował. `slim` = tylko
   `World model` + `Plan`, czyli najmniej inwazyjny wariant.
5. **Playbook offline** (`results/playbook.json`, 11 gier / 16 poziomów / 3.18 pkt) jako
   podłoga — 0 tokenów, 0 GPU, zweryfikowany replayem.
6. **Czego nie robić**: replay na slot przed pomiarem (twierdzenie o capie mówi, że ~0 pkt),
   `game_weights` (nie alokuje budżetu), podnoszenie limitu historii (już 150), dokładanie
   world model (zmierzone jako szkodliwe).
