# ARC-AGI-3 LLM Agent v5.0

**Wynik v4.1:** ~27 pkt (na podstawie danych drugiej gałęzi)
**Cel v5.0:** ~35-42 pkt (+8-15 pkt z ulepszeń)
**Próg nagród:** 40.97 pkt
**Lider (Yi-Chia Chen):** 67.49 pkt

---

## Co nowego w v5.0 (vs v4.1)

Na podstawie analizy drugiej gałęzi (98ddb59f-pokemon) i ich Duck harness:

### 1. ✅ GOAL_CATALOG.md - szczegółowa analiza 15 gier treningowych
**Źródło:** Zaadoptowane z drugiej gałęzi
**Oczekiwany zysk:** +7 pkt (samo rozpoznanie celu)
**Mechanizm:** Model wie jakie klasy celów istnieją (COVER/REACH/COPY/REDUCE/PLACE/FLOW/ALIGN) i jakie sygnały wizualne je zdradzają

### 2. ✅ LEVEL_NOTES - pamięć między poziomami
**Źródło:** Patch 0001 do Duck harness (druga gałąź)
**Oczekiwany zysk:** +3-4 pkt
**Mechanizm:** Po rozwiązaniu poziomu model pisze "LEVEL X NOTES:" który jest zachowywany przez całą grę (przeżywa eviction historii)

### 3. ✅ STUCK_AUDIT - audyt hipotez po utknięciu
**Źródło:** Patch 0001 do Duck harness (druga gałąź)
**Oczekiwany zysk:** +1-2 pkt
**Mechanizm:** Co 40 akcji bez ukończenia poziomu (i co 15 potem) model robi audyt: co przetestował, co obalił, co nieexplorowane

### 4. ✅ AFFORDANCE_HINTS - rozpoznawanie klikalnych obiektów
**Źródło:** Ustalenia z GOAL_CATALOG.md
**Oczekiwany zysk:** +1-2 pkt
**Mechanizm:** Field guide mówi: kontury, kropki, strzałki = cele do kliknięcia; nie-interaktywny obszar = wzorzec do skopiowania

### 5. ✅ FAILURE_RECOVERY - unikanie powtarzania błędów
**Źródło:** Analiza transcriptów
**Oczekiwany zysk:** +0.5-1 pkt
**Mechanizm:** Po game-over model zapisuje "GAME OVER at action X, cause: Y" i nie powtarza tego samego błędu

### 6. ✅ NO-OP DETECTION - wykrywanie bezsensownych akcji
**Źródło:** Inspiracja z SmartExplorer (ale jako komponent, nie agent)
**Oczekiwany zysk:** +0.5-1 pkt
**Mechanizm:** Jeśli 3 ostatnie akcje nie zmieniły grid → WARNING w prompcie

---

## Realistyczna ocena: dlaczego ~35-42, nie 50+?

### Twarda granica: 86% straty to utknięcia PO rozwiązaniu poziomu 1

Dane z drugiej gałęzi (loss_split.py):
- **7 pkt/grę** strata z nierozwiązanego poziomu 1
- **43.9 pkt/grę** strata z utknięcia PO ≥1 rozwiązanym poziomie
- GOAL_CATALOG daje max ~7 pkt (rozpoznanie celu)
- LEVEL_NOTES + STUCK_AUDIT daje ~4-6 pkt (pamięć + audyt)

**Suma:** +7 + 4 + 2 = **+13 pkt max** z tych ulepszeń
**Z 27 v4.1:** 27 + 13 = **40 pkt** (blisko progu nagród 40.97)

### Dlaczego nie więcej?

1. **World model zamknięty** - druga gałąź testowała v3/v4/v5 z world modelem (29.0/23.1/27.2 vs 29.5 baseline). Modele zbyt niedokładne, plan() nie pomaga.
2. **Per-game spread ogromny** - Franzen 4×25 przebiegów: m0r0 0-100, tn36 3.6-100, cn04 4.8-47.6. Pojedynczy przebieg = szum ±10-20 pkt.
3. **Najsłabsze gry** - ls20 (3.3), tn36 (3.6), g50t (10.7) - agent nie rozumie mechaniki. Żaden prompt tego nie naprawi.

### Co może dać +10-20 pkt więcej (droga do 50-60)?

1. **Meta-learning między grami** - zapisywanie co zadziałało w grze A i używanie w grze B. Ale wymaga 100+ gier treningowych.
2. **Multimodal input** - obrazy zamiast ASCII. Ale to wymaga vision model (Qwen-VL, GPT-4V).
3. **Fine-tuning na ARC-AGI-3** - ale wymaga GPU i czasu.
4. **Lepszy model bazowy** - Qwen3.6-27B-FP8 to nie SOTA. Claude 3.5/GPT-4o mogą być lepsze.

---

## Per-game breakdown (oczekiwany v5.0)

Na podstawie danych drugiej gałęzi (v5 27.21):

| Gra | v5 (27.21) | v5.0 (oczekiwany) | Ulepszenie |
|-----|-----------|-------------------|------------|
| cn04 | 47.6 | 52-55 | +4-7 (LEVEL_NOTES) |
| dc22 | 44.8 | 50-53 | +5-8 |
| g50t | 10.7 | 15-20 | +4-9 (GOAL_CATALOG) |
| ka59 | 17.9 | 22-27 | +4-9 |
| ls20 | 3.3 | 5-8 | +2-5 (mechanika nieznana) |
| m0r0 | 28.6 | 33-38 | +4-9 |
| s5i5 | 16.7 | 21-26 | +4-9 |
| sc25 | 42.6 | 48-52 | +5-9 |
| su15 | 56.4 | 60-65 | +4-9 |
| tn36 | 3.6 | 6-10 | +3-7 (mechanika nieznana) |

**Średnia:** ~35-42 pkt (vs 27.21 v5)

---

## Jak uruchomić

### Lokalnie (LM Studio)

```bash
# 1. Uruchom LM Studio z modelem 7-8B (np. Qwen2.5-7B)
#    Ustaw serwer na http://localhost:9000/v1

# 2. Ustaw zmienne środowiskowe
export LLM_BASE_URL="http://localhost:9000/v1"
export LLM_MODEL="qwen2.5-7b"
export OPENAI_API_KEY="dummy"

# 3. Uruchom agenta
python3 run_local_v5.py
```

### Na Kaggle

**UWAGA:** Nie uruchamiaj GPU ani zgłoszeń bez rezerwacji w issue #1!

```bash
# 1. Zbuduj notebook
python3 build_notebook_v5.py arc-agi-3-llm-agent-v5.ipynb

# 2. Zarezerwuj w issue #1 (koordynacja sesji)
# Komentarz: "Rezerwuję GPU na 2h testy v5.0"

# 3. Wyślij na Kaggle
kaggle kernels push -p .
```

---

## Testy A/B (25 gier per arm)

Po powrocie GPU (~17.10):

```bash
# Test v4.1 vs v5.0 na 25 grach (paired A/B)
python3 run_games.py --policy v4.1 --games 25 > v4.1.jsonl
python3 run_games.py --policy v5.0 --games 25 > v5.0.jsonl

# Porównaj scores
python3 compare.py v4.1.jsonl v5.0.jsonl
# Expected: v5.0 = v4.1 + 8-15 pkt (±3.9 sd)
```

---

## Koordynacja z drugą gałęzią

**Problem:** v5.0 i druga gałąź (98ddb59f-pokemon) niezależnie robią podobne zmiany:
- LEVEL_NOTES + STUCK_AUDIT (patch 0001)
- GOAL_CATALOG (zaadoptowany)
- Anti-dissertation (max 60 słów reasoning)

**Przy limicie 1 zgłoszenia/dzień nie ma sensu mierzyć dwa razy tego samego.**

**Propozycja koordynacji:**
1. Po powrocie GPU (~17.10): 3 × 2h testy na 25 grach
   - v5.0 (nasza wersja z LEVEL_NOTES + STUCK_AUDIT)
   - v5 (druga gałąź, Duck harness z patch 0001)
   - baseline Franzena (29.48)
2. Porównanie wyników
3. Zgłoszenie tylko zwycięzcy

---

## Źródła

- **GOAL_CATALOG.md:** Zaadoptowany z drugiej gałęzi (98ddb59f-pokemon)
- **LEVEL_NOTES + STUCK_AUDIT:** Patch 0001 do Duck harness (druga gałąź)
- **Per-game breakdown:** Eksperymenty drugiej gałęzi (EXPERIMENTS.md)
- **86% straty:** loss_split.py (druga gałąź)
- **World model closed:** Werdykt drugiej gałęzi (29.0/23.1/27.2 vs 29.5 baseline)

---

## Następne kroki

1. ✅ GOAL_CATALOG.md (zaadoptowany)
2. ✅ llm_policy_v5.py (LEVEL_NOTES + STUCK_AUDIT + AFFORDANCE_HINTS + FAILURE_RECOVERY)
3. ✅ README_v5.md (ten plik)
4. ⏳ run_local_v5.py (test lokalny)
5. ⏳ build_notebook_v5.py (budowa notebooka Kaggle)
6. ⏳ Testy A/B po powrocie GPU (~17.10)
7. ⏳ Zgłoszenie zwycięzcy na Kaggle

---

## Commit

`[pending]` - feat: v5.0 z LEVEL_NOTES + STUCK_AUDIT + GOAL_CATALOG
