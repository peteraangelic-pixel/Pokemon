# ARC-AGI-3 LLM Agent v4

**Wynik v2:** 24.66 (poprawa z 0.01!)
**Cel v4:** 40+ (próg nagród)

## Kluczowe ulepszenia v4

1. **Ultra-krótki prompt** (max 500 tokenów vs 81k w v2)
2. **Agresywna eksploracja** - więcej akcji, mniej myślenia
3. **Automatyczne testowanie nowych obiektów** - wykrywanie i klikanie
4. **Wykrywanie utknięcia** - zmiana strategii po 5 akcjach bez zmiany

## Jak uruchomić lokalnie (LM Studio)

```bash
# 1. Uruchom LM Studio z modelem 7-8B (np. Qwen2.5-7B)
#    Ustaw serwer na http://localhost:9000/v1

# 2. Ustaw zmienne środowiskowe
export LLM_BASE_URL="http://localhost:9000/v1"
export LLM_MODEL="qwen2.5-7b"
export OPENAI_API_KEY="dummy"

# 3. Uruchom agenta
python3 run_local_v4.py
```

## Jak uruchomić na Kaggle

```bash
# 1. Zbuduj notebook
python3 build_notebook_v4.py arc-agi-3-llm-agent-v4.ipynb

# 2. Wyślij na Kaggle
kaggle kernels push -p .

# 3. Po zakończeniu runu, kliknij "Submit to Competition" w UI
```

## Status

- ✅ Notebook v4 zbudowany
- ⏳ Testy lokalne (wymaga LM Studio)
- ⏳ Zgłoszenie na Kaggle (wymaga rezerwacji w issue #1)

## Analiza wyników

**v2 (24.66):**
- Podstawowy LLM agent
- Długi prompt, dużo myślenia
- Mało eksploracji

**v4 (cel 40+):**
- Ultra-krótki prompt
- Agresywna eksploracja
- Automatyczne testowanie nowych obiektów
- Wykrywanie utknięcia

## Oczekiwane wyniki

Na podstawie FAILURES.md:
- 6/10 porażek: agent nie rozumie nowej mechaniki → v4 testuje nowe obiekty
- 3/10 porażek: agent ma zły cel → v4 ma krótszy prompt, mniej błędów
- Agent myśli za dużo → v4 myśli mniej, działa więcej

**Szacunkowa poprawa:** 24.66 → 35-45 (zależnie od modelu i gier)
