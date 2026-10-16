# Instrukcja submitowania Duck Harness na Kaggle

## 📋 Co to jest

Notebook `duck-harness-original.ipynb` to **kompletne rozwiązanie Tufa Labs** które zdobyło **68.91 punktów** na leaderboardzie.

**Architektura:**
- Model: Qwen 3.6 27B FP8
- Framework: TAAF (Tufa ARC-AGI Framework)
- Technika: REPL z triple-channel perception (image + ASCII + segmentation)
- Kluczowe: "infinite play via eviction" + multimodal input

---

## 🚀 Jak submitować

### Krok 1: Wejdź na Kaggle Competition

1. Otwórz: https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/code
2. Kliknij **"New Notebook"**

### Krok 2: Załaduj notebook

1. W nowym notebooku kliknij **"File" → "Import"**
2. Wybierz plik: `arc-agi-3/kaggle-submissions/duck-harness-original.ipynb`
3. Poczekaj na załadowanie (17 komórek)

### Krok 3: Dodaj wymagane datasety

Notebook potrzebuje **3 datasety** jako inputy. Kliknij **"+ Add Input"** w prawym panelu i dodaj:

#### Dataset 1: TAAF Source Bundle
- **Nazwa:** `jeroencottaar/taaf-kaggle-source-share`
- **URL:** https://www.kaggle.com/datasets/jeroencottaar/taaf-kaggle-source-share
- **Zawartość:** Kod źródłowy TAAF + pickled benchmark + setup commands

#### Dataset 2: vLLM Wheels
- **Nazwa:** `driessmit1/arc3-vllm-h100-wheelhouse-v3`
- **URL:** https://www.kaggle.com/datasets/driessmit1/arc3-vllm-h100-wheelhouse-v3
- **Zawartość:** Offline wheels dla vLLM (nie ma internetu w Kaggle submission)

#### Dataset 3: Model Weights (Qwen 3.6 27B FP8)
- **Nazwa:** `driessmit1/vrfai-qwen3-6-27b-fp8-hf-snapshot`
- **URL:** https://www.kaggle.com/datasets/driessmit1/vrfai-qwen3-6-27b-fp8-hf-snapshot
- **Zawartość:** Wagi modelu Qwen 3.6 27B w formacie FP8

**Jak dodać:**
1. Kliknij **"+ Add Input"** w prawym panelu
2. Wpisz nazwę datasetu (np. `jeroencottaar/taaf-kaggle-source-share`)
3. Wybierz dataset z listy
4. Powtórz dla wszystkich 3 datasetów

### Krok 4: Skonfiguruj runtime

1. Kliknij **"Settings"** w prawym panelu (ikona ⚙️)
2. Ustawienia:
   - **Environment:** `Kaggle` (domyślne)
   - **Internet:** **OFF** (notebook nie potrzebuje internetu)
   - **GPU:** **GPU P100** lub **GPU T4 x2** (minimum)
   - **Memory:** minimum 16 GB RAM
   - **Max runtime:** 9 godzin (domyślne)

**UWAGA:** Notebook wymaga **H100 GPU** dla optymalnej wydajności. Jeśli H100 nie jest dostępne:
- Użyj **A100** (dostępne w Kaggle)
- Lub **2x T4** (może być wolniejsze)

### Krok 5: Zapisz i uruchom

1. Kliknij **"Save Version"** (prawy górny róg)
2. Wybierz **"Save & Run All (Commit)"**
3. Kliknij **"Save"**
4. Notebook zacznie się uruchamiać (pokaże się jako "Running")

### Krok 6: Czekaj na wyniki

- **Czas wykonania:** ~2-4 godziny (zależy od GPU)
- **Status:** Sprawdzaj w "Your Work" → "Notebooks"
- **Wyniki:** Po zakończeniu sprawdź "Submissions" na stronie competition

---

## ⚠️ Ważne ostrzeżenia

### 1. GPU Quota
- Kaggle ma **limit GPU godzin** (30h/tydzień na darmowym koncie)
- Duck harness zużywa ~3-4h GPU na jeden run
- Jeśli nie masz quota, poczekaj do **soboty 17.10 00:00 UTC** (reset)

### 2. Daily Submission Limit
- Kaggle limituje **2 submisje dziennie** na competition
- Upewnij się że nie wyczerpałeś limitu (sprawdź w "Submissions")

### 3. Dataset Availability
- Wszystkie 3 datasety są **publiczne** i powinny być dostępne
- Jeśli któryś dataset nie istnieje, sprawdź alternatywne wersje:
  - `driessmit1/vrfai-qwen3-6-27b-fp8-hf-snapshot` → szukaj "qwen3.6 fp8"

### 4. Notebook Compatibility
- Notebook wymaga **Python 3.12**
- Wymaga **arc-agi** package (instalowane z wheels w Cell 4)
- Wymaga **vLLM** + **PyTorch** (instalowane z wheels w Cell 8)

---

## 🔧 Troubleshooting

### Problem: "TAAF source bundle not found"
**Rozwiązanie:** Sprawdź czy dataset `jeroencottaar/taaf-kaggle-source-share` jest poprawnie zamontowany.

### Problem: "vLLM installation failed"
**Rozwiązanie:** Sprawdź czy dataset `driessmit1/arc3-vllm-h100-wheelhouse-v3` jest zamontowany.

### Problem: "Model not found"
**Rozwiązanie:** Sprawdź czy dataset `driessmit1/vrfai-qwen3-6-27b-fp8-hf-snapshot` jest zamontowany.

### Problem: "Out of memory"
**Rozwiązanie:** Zwiększ RAM do 32 GB lub użyj mocniejszego GPU (A100/H100).

### Problem: "Runtime exceeded"
**Rozwiązanie:** Zwiększ "Max runtime" do 12h lub użyj szybszego GPU.

---

## 📊 Oczekiwane wyniki

**Na podstawie leaderboardu:**
- Tufa Labs: **68.91** (oryginalny wynik)
- Daniel Franzen (M2): **47.25** (lekko zmodyfikowana wersja)
- Yi-Chia Chen: **67.49** (podobna architektura)

**Twój wynik powinien być w zakresie 45-68** w zależności od:
- GPU (H100 > A100 > T4)
- Konfiguracji vLLM
- Losowych fluktuacji (model jest nondeterministyczny)

---

## 🎯 Strategia na 45+ punktów

1. **Pierwszy run:** Użyj Duck harness bez modyfikacji (cel: 45-50)
2. **Jeśli < 45:** Sprawdź logi, zoptymalizuj GPU/memory
3. **Jeśli > 45:** Spróbuj Franzen M2 (jeszcze lepsza wersja)
4. **Jeśli > 55:** Eksperymentuj z parametrami (temperatura, context window)

---

## 📝 Alternatywa: Franzen M2 Solution

Jeśli Duck harness nie działa, użyj **Daniel Franzen M2 solution**:
- **URL:** https://github.com/junpenglao/arc-agi-3-solution
- **Score:** 47.25
- **Model:** Qwen3.8-Flash-Next (nowszy model)
- **Ulepszenia:** Blockwise history trimming, board-difference images

Instrukcja w repozytorium GitHub.

---

## 🆘 Potrzebujesz pomocy?

1. Sprawdź oryginalny write-up Tufa Labs: https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/discussion/717133
2. Blog post: https://tufalabs.ai/research/duck-harness/
3. GitHub: https://github.com/Tufalabs/duck-harness

---

**Powodzenia! 🦆**
