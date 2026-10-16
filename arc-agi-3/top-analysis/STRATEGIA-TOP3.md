# Analiza strategii Top 3 - ARC-AGI-3

## Data: 2026-10-16

---

## Tufa Labs (68.91) - Duck Harness

### Architektura:
1. **Triple-channel perception**: 
   - Rendered image (obraz gry)
   - ASCII grid (tekstowa reprezentacja)
   - Segmentation zoom tool (narzędzie do precyzyjnego badania regionów)

2. **REPL (Read-Eval-Print Loop)**:
   - Agent pisze kod Python
   - Inspektuje zmienne
   - Wywołuje helper functions
   - Kod jest wykonywany w sandboxie

3. **Context management**:
   - "Infinite play via eviction" - automatyczne usuwanie najstarszych wiadomości
   - Kontekst utrzymywany krótki
   - Tylko system prompt + recent history

4. **Multimodalność**:
   - Model dostaje obraz gry jako Python data
   - Jednocześnie widzi: obraz + ASCII + segmentation

### Kluczowe odkrycia:
> "Adding hand-crafted specialized tools **hurt** performance. The model improvised more effectively with a clean, general interface than with purpose-built shortcuts."
> 
> "The gains came from **multimodality and better base models**, not hand-built tools."

**Wniosek**: Zamiast dodawać więcej narzędzi (goal classifier, value gate, early abandon), lepiej dać modelowi czysty interfejs i pozwolić mu improwizować.

### Model:
- **Qwen 3.6 27B FP8** (lokalnie na Kaggle GPU)
- Optymalizacja: multimodalność, nie hand-crafted tools

---

## Daniel Franzen's Milestone 2 solution (47.25)

### Architektura (bazuje na Duck harness):
- **Model**: Qwen3.8-Flash-Next (nowszy niż Qwen3.6-27B)
- **Context management**: 
  - Calibrated text-token estimates
  - Image-size-aware token accounting
  - Blockwise history trimming
- **Perception**:
  - Większe obrazy board
  - Board-difference images
  - Animation frames
  - Timeline accessible in Python
- **Agent tools**:
  - Executable undo
  - Optional reset
  - Guidance for transferring knowledge across levels
  - Retention of eligible Python functions

### Kluczowe ulepszenia vs Duck:
- Lepsze zarządzanie kontekstem (więcej tokenów na grę)
- Lepsza percepcja (różnice między klatkami, animacje)
- Lepsze narzędzia (undo, reset, transfer wiedzy)

---

## OpenAI experiment

> "Two configuration changes, no model update, and Sol's score tripled to 38.3%"
> 
> **Scaffolding beats model upgrades!**

**Wniosek**: Architektura harnessu (scaffolding) jest ważniejsza niż sam model. Dwie zmiany konfiguracji dały 3x lepszy wynik na tym samym modelu.

---

## Nasze problemy (v7):

1. ❌ **Brak multimodalności** (tylko ASCII, brak obrazów)
2. ❌ **Brak REPL** (agent nie pisze kodu, tylko wybiera akcje)
3. ❌ **Za dużo hand-crafted tools** (goal classifier, value gate, early abandon, etc.)
4. ❌ **Brak "infinite play via eviction"** (context management)

---

## Opcje:

### Opcja A: Skopiować Duck harness bezpośrednio
- **Źródło**: `Tufalabs/duck-harness` (open-source, MIT)
- **Zalety**: sprawdzona architektura, 68.91
- **Wady**: wymaga pobrania kodu, zbudowania notebooka, testowania
- **Czas**: ~2-3 godziny (pobranie, adaptacja, build notebooka)

### Opcja B: Użyć Daniel Franzen's Milestone 2 solution
- **Źródło**: `junpenglao/arc-agi-3-solution` (open-source)
- **Zalety**: lepszy context management, perception
- **Wady**: wymaga Qwen3.8-Flash-Next (inny model), adaptacja
- **Czas**: ~3-4 godziny

### Opcja C: Dodać multimodalność + REPL do naszego v7
- **Zalety**: zachowujemy nasze improvements (early abandon, goal classifier)
- **Wady**: OGROMNA praca, nie zdążymy przed sobotą
- **Czas**: ~10-15 godzin

---

## Rekomendacja:

**Opcja A (Duck harness)** - najszybsza droga do 40+

Druga gałąź już pracuje nad tym:
- "Push CPU `duck-original`" (bez kwoty GPU!)
- "Auto-submit" o 00:00 UTC (sobota)
- Expected: ~40-56

**Nie kolidować z ich łańcuchem nocnym!**

---

## Plan na sobotę:

1. **00:00 UTC** - druga gałąź uruchomi auto-submit (duck-original)
2. **01:30-04:30 UTC** - submit z atrybucją Tufy Labs
3. **14:00-15:00 PL** - LB reruna (9h)
4. **Expected**: ~40-56 (próg 40.97!)

**Prośby drugiej gałęzi:**
1. Nie ruszać `arc-agi-3/kaggle/ops/request.json`
2. Nie dispatchować `arc3-ops.yml` ręcznie
3. Nie submittować niczego w sobotę przed ich potwierdzeniem

**Nasz status:**
- ✅ Duck v3: 26.25 (zsubmitowana)
- ✅ v7: gotowa (bugi naprawione), ale wymaga GPU
- ⏳ Czekamy na GPU quota (sobota 00:00 UTC)
- 🚫 Nie kolidujemy z łańcuchem nocnym drugiej gałęzi
