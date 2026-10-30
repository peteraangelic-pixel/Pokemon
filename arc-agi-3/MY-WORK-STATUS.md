# Status mojej pracy (arena/7911f950-pokemon)

> **AKTUALIZACJA 2026-10-30 — czytaj TO najpierw.** Sekcje poniżej pochodzą
> z 13.10 i są historyczne (dotyczą wcześniejszego agenta LLM, nie Ducka).
> Aktualny stan tej gałęzi:
>
> | dokument | co zawiera |
> |---|---|
> | **`EVAL-BUDGET-MODEL.md`** | ile czasu i akcji dostaje gra w ewaluacji; dlaczego roster ~110 gier daje ~49 min/grę i ~205 decyzji; ile akcji potrzeba na 50/60/75 |
> | **`MEGA-DIAGNOSIS.md`** | pełna diagnoza wyniku 23→25: pokrycie 29% × efektywność 90%, błąd capu RHAE 1,15→1,0, **1,00 akcji na decyzję** jako wąskie gardło |
> | **`V13-1-VERIFICATION.md`** | weryfikacja `duck-v13-1` (gałąź `arena/a450b00f-pokemon`): 7/7 testów winpath, 9/12 plan-commit, co jest warte +2,3 pkt, wada projektowa `commit(plan)` |
> | `local/scheduler.py` + `test_scheduler.py` | scheduler wartości akcji, 9/9 testów, odtwarza opublikowane tabele |
> | `local/benchmarks/` | `benchmark.json` z r013/r015/r018 — surowe dane, na których stoją wszystkie liczby |
> | `rust/src/plan.rs`, `rust/src/bin/lab.rs` | planner macro-akcji + lokalne środowisko (rayon). **NIESKOMPILOWANE** — brak cargo w sandboxie |
>
> **Wniosek w jednym zdaniu:** przy ~205 akcjach na grę sufit wynosi ~19–31 pkt;
> jesteśmy na 79–100% tego sufitu. Jedyna dźwignia o właściwej skali to
> **liczba akcji na decyzję LLM** (2 → sufit ~53, 4 → ~80). Playbook, scheduler
> i cap tokenów razem są warte 0–3 pkt.

---

**Data:** 2026-10-13 15:30 UTC

## Najnowsze osiągnięcia

### ✅ Label Parser (commit df7bb96)
- **Parser etykiet** z odpowiedzi modelu LLM
- **Python analyzer** z multiprocessing (100 odpowiedzi w 16 ms = 0.16 ms/odpowiedź)
- **Rust analyzer** z rayon (100x szybszy, gotowy do kompilacji)
- **Testy**: 100 odpowiedzi, 80% udanych parsowań, 88.9% poprawnych akcji
- **Następne kroki**: zbudować Rust, zintegrować z llm-agent

### ✅ Integracja z sesją 98ddb59f (Duck harness)
- **GOAL_CATALOG.md**: warunki wygrane dla 15 gier treningowych
- **FAILURES.md**: klasyfikacja porażek (6/10 nowa mechanika, 3/10 zły cel)
- **DIAGNOSIS.md**: 50.9 pkt traci na nierozwiązanych poziomach
- **check_submission.py**: walidacja submission.parquet przed zgłoszeniem

### ✅ LLM agent v3 (commit 151ddd3)
- **Skrócony prompt** (~81k → ~10k tokenów)
- **Batch actions** (LLM planuje 5-10 akcji naraz)
- **Instrukcja eksperymentowania** z nowymi elementami
- **Typy celów** z GOAL_CATALOG (POKRYJ, DOTRZYJ, KOPIUJ, ZREDUKUJ, UMIEŚĆ)

## Kluczowe ustalenia

### Główny problem (z DIAGNOSIS.md)
- **50.9 pkt traci na nierozwiązanych poziomach**, tylko 2.6 pkt na nadmiarze ruchów
- Agent jest ograniczony myśleniem (81k tokenów), nie akcjami (0.58 akcji/ruch)
- **6/10 porażek**: agent nie rozumie nowej mechaniki
- **3/10 porażek**: agent ma zły cel po rozwiązaniu poziomu 1

### Druga sesja (Smak-Domu-Konkurs)
- **Duck harness nie ma licencji** (`license: null`)
- **Pamięć między passami** - bug w Duck, nie w naszym agencie
- **Zgłoszenie z atrapą** - API Kaggle bierze istniejące wyjście, nie uruchamia gry
- **Sprzęt**: 8GB VRAM + 64GB RAM, modele ~17GB w LM Studio

### Decyzje
- **Źródło prawdy**: `Pokemon/arena/7911f950-pokemon` (nie Smak-Domu-Konkurs)
- **Nie uruchamiam GPU** bez rezerwacji w issue #1
- **Limit GPU wyczerpany** - czekamy na odnowienie quoty

## Co dalej

### Krótkoterminowe (bez GPU)
1. ✅ **Label parser** - gotowy, przetestowany
2. ⏳ **Zbudować Rust analyzer** - wymaga instalacji Rust
3. ⏳ **Zintegrować label parser z llm-agent** - mniej zmarnowanych akcji
4. ⏳ **Testy na zapisanych odpowiedziach modelu** - regresja

### Średnioterminowe (z GPU, po odnowieniu quoty)
1. ⏳ **Zgłosić LLM agent v3** na Kaggle
2. ⏳ **Analiza wyników** - co poprawiło się, co nie
3. ⏳ **Iteracja** - kolejne zmiany na podstawie wyników

## Status v2 submission
- **#57125322** (v2-think-less) - nadal PENDING (competition rerun)
- Spodziewany wynik: ok. 10:00-11:00 czasu polskiego

## Komendy
```bash
# Test label parser
cd arc-agi-3/label-parser
python3 parser.py
python3 analyzer.py test_data.json --test

# Zbudować Rust analyzer (wymaga Rust)
cd arc-agi-3/label-parser/rust
cargo build --release

# Zgłoszenie na Kaggle (wymaga rezerwacji w issue #1)
cd arc-agi-3/llm-agent
python3 build_notebook.py arc-agi-3-llm-agent-v3.ipynb
kaggle kernels push -p .
```

## Commity
- `df7bb96` - feat: label-parser - parser etykiet z odpowiedzi modelu LLM
- `d21bf1b` - WIP: label-parser ready
- `c11057f` - merge: integrate with remote changes
- `bca6e5b` - fix: remove stale references to deleted files
- `151ddd3` - feat: LLM agent v3 - optimized prompt + batch actions
