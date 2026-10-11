# ARC-AGI-3: co robi czołówka i co musimy zbudować

Stan na 11 X 2026. Wnioski z analizy publicznych notebooków konkursu
(`kaggle/results/PUBLIC_APPROACHES.md`), ogłoszeń ARC Prize i raportów
zespołów.

## Dlaczego jesteśmy nisko — i to nie jest kwestia „dopracowania"

Nasz agent jest **deterministyczny i nie ma modelu**. Cała czołówka używa
**lokalnego LLM**. To nie jest różnica w jakości tylko w skali — to różnica
rodzaju.

Skala przepaści, dla orientacji:

| | my | czołówka publicznych notebooków |
|---|---|---|
| model | **brak** | Qwen3.8-Flash-Next W4A16 + MTP draft |
| równoległość gier | 1 | **10 slotów, concurrency 10** |
| kontekst | — | 128k, hysteresis trimming przy 58k |
| zapętlania | heurystyka | interwencja przy turze 12 + UNDO/RESET |
| pamięć między poziomami | częściowa | **episodic memory, transfer niezmienników** |

## Kluczowe odkrycie: budżet to prawie wyłącznie czas modelu

Z repo uczestnika (`anandsingh8687`):

- 110 ukrytych gier, **9 godzin**, jedno GPU, bez internetu, 1 zgłoszenie/dzień
- silnik gry: **~800 akcji/sekundę na CPU**
- żeby dojść do poziomu 3 w każdej grze: **0.577 akcji/sekundę podtrzymywane**
- **„praktycznie cały budżet to czas modelu"**

To oznacza, że nasza praca nad szybkością segmentacji (Rust, ~121×) **nie
dotyka wąskiego gardła**. Liczy się: ile wywołań modelu zmieścimy w 9 h i jak
dobre jest każde z nich.

Zasada z tego samego repo, którą warto zapamiętać:
> zmiana, która poprawia rozumowanie, ale spada poniżej wymaganego tempa akcji,
> **nie jest poprawą**.

## Architektura, która wygrywa (złożona z publicznych źródeł)

### 1. Dwie linie, z których wszyscy forkują

- **Tufa Labs „The Duck"** (zwycięzca Milestone 1, MIT):
  agent **pisze i uruchamia Python w żywym REPL**, traktując grę jak
  interaktywny problem programistyczny. Qwen 3.6 27B FP8.
  **Najważniejsza uwaga Tufy: dorabiane ręcznie narzędzia PSują wynik —
  model lepiej radzi sobie, gdy improwizuje.**
- **Daniel Franzen (Milestone 2)** — baza większości obecnych top notebooków.

### 2. Stos, który się powtarza w topie

- **Model**: Qwen3.8-Flash-Next, kwantyzacja **W4A16 AutoRound** (Intel)
- **Dopisek**: osobny skwantowany **MTP draft model** do speculative decoding
- **Serwowanie**: vLLM / SGLang, BF16 host offload, **128k kontekstu**,
  **hysteresis trimming przy 58k**
- **Harmonogram**: 10 aktywnych slotów, concurrency 10

### 3. Różniczki, które dają punkty

Z opisów autorów (własne słowa, nie nasze domysły):

1. **Solved-Level Episodic Memory** — transfer niezmienników fizycznych
   między poziomami + zachowane helpery
2. **Multi-Tier Anti-Loop Strategy Audit** — interwencja w turze 12 z jawnym
   prowadzeniem UNDO / RESET
3. **Death-Loop Avoidance Warning** — ostrzeżenie po wielu resetach
4. **Slot priority (D′)** — zamiast dzielić czas myślenia po równo, dawać go
   grom, gdzie najpewniej zarobi punkty („31.54 in a single sub")
5. **Fast Commit Bypass**

### 4. Co mówi raport ARC

> „Context management is a central challenge in ARC-AGI-3. Ramki to siatki
> 64×64 i naiwne okno przewijane szybko wyczerpuje kontekst. Harness pozwala
> modelowi **wykonywać dowolny kod Python, by selektywnie pobierać i
> przekształcać informacje ze swojej historii akcji**."

To jest ta sama oś, którą Tufa nazwała niewyeksploatowaną.

## Co z tego wynika dla nas — plan

### Etap A (do zrobienia): infrastruktura pod model

1. ~~Potwierdzić dostępność modelu~~ — **POTWIERDZONE 11 X 2026.**
   Notebook nie ma internetu, więc model musi być dodany jako Kaggle Model.
   Dokładnie te checkpointy, których używa czołówka, są dostępne:

   | ref | co to |
   |---|---|
   | `dfranzen/intel-qwen3.8-flash-next-w4a16-autoround` | model W4A16 AutoRound — ten sam, który ma czołówka |
   | `dfranzen/albucino-qwen3-8-flash-next-drafter` | **MTP draft model** do speculative decoding |
   | `nvidia/qwen3-8-flash-next-nvfp4` | wersja NVIDIA NVFP4 |
   | `boristown/qwen3-8-flash-next-nvfp4-reap-448e` | przycięty (512→448 ekspertów), żeby **zwolnić VRAM pod kontekst 128K** |
   | `foysalemonshanto/qwen3-8-27b-fp8-repacked-v1` | Qwen3.8 27B FP8 (model z Duck harness) |

   Droga jest więc otwarta: nie musimy niczego trenować ani ściągać z sieci.
2. Zbudować agenta na licencji MIT (duck-harness) zamiast naszej heurystyki:
   REPL + lokalny LLM.
3. Ustawić concurrency i harmonogram slotów.

### Etap B: różniczki w kolejności spodziewanego zysku

1. **Anti-loop przy turze 12 + UNDO/RESET** — bezpośrednio uderza w nasz
   zmierzony problem (82% powtórzeń, cd82 utknięte na 5 stanach)
2. **Episodic memory między poziomami**
3. **Priorytet slotów** (D′) — darmowy zysk przydziału czasu
4. **Speculative decoding (MTP draft)** — czysty zysk przepustowości

### Czego NIE robić

- Nie dorabiać ręcznych narzędzi per gra — **Tufa zmierzyła, że to psuje**
- Nie optymalizować segmentacji — to nie jest wąskie gardło
- Nie zgadywać progu wydajności: mierzyć akcje/sekundę przy każdej zmianie

## Uczciwa ocena szans

Czołówka ma 27–31 punktów w publicznych, powtarzalnych zgłoszeniach; próg
nagrody na leaderboardzie to **40.97**. Dogonienie tego wymaga **całej**
architektury z Etapu A, nie pojedynczej poprawki. To jest projekt na wiele
dni, nie godzin — i każdy test kosztuje 9 godzin GPU lub jedno zgłoszenie
dziennie.

**Realistyczny wniosek:** jeśli chcemy realnie walczyć o top 5, musimy
przestać rozwijać deterministycznego agenta i zbudować agenta REPL z modelem.
Jeśli nie chcemy w to wchodzić, należy przesunąć środek ciężkości na inne
konkursy (patrz rewizja 4 w `konkursy-ai-2026.md`).
