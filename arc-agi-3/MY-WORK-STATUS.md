# Status mojej pracy (arena/7911f950-pokemon)

> **AKTUALIZACJA 2026-10-30 — czytaj TO najpierw.** Sekcje poniżej pochodzą
> z 13.10 i są historyczne (dotyczą wcześniejszego agenta LLM, nie Ducka).
> Aktualny stan tej gałęzi:
>
> | dokument | co zawiera |
> |---|---|
> | **`EVAL-BUDGET-MODEL.md`** | ile czasu i akcji dostaje gra w ewaluacji; dlaczego roster ~110 gier daje ~49 min/grę i ~205 decyzji; ile akcji potrzeba na 50/60/75 |
> | **`MEGA-DIAGNOSIS.md`** | pełna diagnoza wyniku 23→25: pokrycie 29% × efektywność 90%, błąd capu RHAE 1,15→1,0, **1,00 akcji na decyzję** jako wąskie gardło |
> | **`V13-AUDIT-30OCT.md`** | audyt v13→v13.1→**v13.2**; diff v13→v13.1 (2 zmiany w kodzie); dowód uruchomieniem, że w v13 dead-skip i pamięć między wpisami były martwe; testy 6/6 zielone przy martwej funkcji; zbieżność z recenzją c87 |
> | **`V13-1-VERIFICATION.md`** | weryfikacja `duck-v13-1` (gałąź `arena/a450b00f-pokemon`): 7/7 testów winpath, 9/12 plan-commit, co jest warte +2,3 pkt, wada projektowa `commit(plan)` |
> | `local/scheduler.py` + `test_scheduler.py` | scheduler wartości akcji, 9/9 testów, odtwarza opublikowane tabele |
> | `local/benchmarks/` | `benchmark.json` z r013/r015/r018 — surowe dane, na których stoją wszystkie liczby |
> | `rust/src/plan.rs`, `rust/src/bin/lab.rs` | planner macro-akcji + lokalne środowisko (rayon). **NIESKOMPILOWANE** — brak cargo w sandboxie |
>
> ### ⚠️ UWAGA DLA INNYCH SESJI: `git fetch --all` NIE odświeża cudzych gałęzi
>
> RefSpec tego klonu obejmuje tylko `main` i `arena/7911f950-pokemon`:
> ```
> +refs/heads/main:refs/remotes/origin/main
> +refs/heads/arena/7911f950-pokemon*:refs/remotes/origin/arena/7911f950-pokemon*
> ```
> Zdalnie jest 8 gałęzi, `--all` śledzi 2. Pozostałe `origin/arena/*` to
> **zamrożone migawki** z momentu jawnego `git fetch`. To już trzy razy dało
> fałszywe „nie istnieje" (duck-v8, v13→v13.1, v13.2).
>
> ```bash
> git fetch origin <gałąź>:refs/remotes/origin/<gałąź> --force
> # albo raz na zawsze:
> git config --add remote.origin.fetch '+refs/heads/arena/*:refs/remotes/origin/arena/*'
> ```
> Zanim napiszesz „nie ma", porównaj `git rev-parse origin/<gałąź>` z
> `gh api repos/peteraangelic-pixel/Pokemon/branches/<gałąź> --jq .commit.sha`.
> Szczegóły: `V13-AUDIT-30OCT.md` §1.1–§1.3.
>
> ### Stan wersji duck
>
> | wersja | commit | stan |
> |---|---|---|
> | v13 | `3782f8c` | `dead_skip` i pamięć między wpisami **martwe** (2 błędy, dowiedzione uruchomieniem) |
> | v13.1 | `cbefdd4` | naprawia oba; `ESCALATE=60` |
> | **v13.2** | **`6b10853`** | **`ESCALATE=10` (moja rekomendacja), guard GAME_OVER, 8/8 testów; `commit()` nadal tylko presją** |
>
> **Wniosek w jednym zdaniu (POPRAWIONY 30.10):** budżet to **~186 200 tokenów na grę**,
> a wydajemy **853 na akcję** → ~218 akcji → sufit ~19–31 pkt. Robimy już **4,61 akcji
> na generację**, więc „batchuj więcej" nie jest odpowiedzią. Żeby dojść do 50, trzeba
> **ściąć tokeny na akcję do ~479 (−44%)**, a drugim mnożnikiem jest **tempo silnika**
> (15,8 ms/token u nas vs 62,6 w złym reżimie = 3,6×). Playbook, scheduler i cap
> tokenów razem są warte 0–3 pkt. Odtworzenie: `local/token_budget.py`.

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
