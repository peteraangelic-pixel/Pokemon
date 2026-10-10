# Inspiracje z repo riemann (Kaggriculture) → PTCG

Przejrzane gałęzie: `arena/01a06bce`, `01a075fa`, `01a087c0` itd. – tam był konkurs Kaggle **Kaggriculture** (2 graczy, 720 tur, $50k, 5 sub/dzień, liczą się 2 ostatnie – identyczny format jak PTCG Playground).

## Co działało w Kaggriculture i jak przenieść na PTCG

### 1. Scripted tape vs reactive – 2x różnicy
- **Najlepsze agenty to były frozen tape**: pre-komputowane optymalne sekwencje (opening + zapis gry elitarnego gracza), skompresowane zlib+base85, ~140-147k cash
- **Reactive policies** (900 linii Pythona, decyzja co turę z obserwacji) – ~70k, czyli 2x gorzej
- Gap = zoptymalizowany opening + scripted schedule
- **Wniosek PTCG**: Nasz heuristic jest reactive (jak `agent_v8_fert.py`). Top decki PTCG to trochę jak tape – zoptymalizowany deck + opening (T1 Snover, T2 Aboma). Możemy zrobić **tape opening**: np. jeśli ręka startowa ma Snover + Water, zawsze zagraj Snover na bench, a dopiero potem przełącz na reactive. W `kaggriculture_meta_lab/agents/current/` mają `B21/S16` = buy21 wheat / sell16 jako opening – my możemy mieć `Snover2 + Water1` jako B21.

### 2. Stable foundation (pszenica) vs premium (marchew, melon)
- **Pszenica** – krzywa logarytmiczna, nie da się zepchnąć do min ceny przez 2 graczy. Harvest w wieku 3 dni (3 sztuki zamiast 4 w wieku 4) – strata 7% wydajności, ale zysk z harmonogramu (czeka do wieku 5 bez gnicia).
- **Marchew** – premia za deficyt, areał dobierany do widocznego popytu miasteczka (PET_CAFE, FARMERS_MARKET) z `CARROT_KAPPA=0.7` i limitem 40%, sadzona tylko gdy cena >=1.15× pszenicy (self-repairing valve).
- **Melon** – najwyższa marża, ratusz kupuje 1 dziennie (30/sezon), 10-dniowa roślina daje 6 sztuk, ale 6 komórek przesyca rynek (sq) i psuje wynik, więc liczba stała (4 komórki).

**Przeniesienie PTCG:**
- **Water 34W = pszenica** – stabilny fundament, 34W daje 340 dmg, odporny na Hammer, nie da się zepchnąć jak 29W Powerglass (live 600→308). Nasze testy: 34W Signal4 Boss4 = 0.932 vs top7 BEST.
- **Boss x4 = marchew** – premia za deficyt gustu, areał dobierany do widocznego popytu (czy opp ma wall? Crustle/Sylveon → zwiększ gust). Nasz `v9_final` Boss4 naprawia walls 0.250→0.750.
- **Powerglass / Cyrano = melon** – wysoka marża, ale limitowana. 1x Powerglass ok, 2x przesyca i psuje (0.705 vs top7). Tak jak melon 4 ok, 6 psuje.

### 3. Ziemia: tylko NE ($1k) i SW ($2k), SE ($4k) nieopłacalna
- Offline potwierdzone jako nieopłacalna – późno w sezonie nie zwraca się.

**PTCG:** Judge1 Haul1 Waitress3 vs Waitress2 – testowaliśmy `v10_33_boss3_wait3` 0.750/0.567 gorszy niż `v10_34_sig4` 0.932/0.567. Niektóre trainery jak Haul, Judge są jak SE – nieopłacalne vs top.

### 4. 5 krów = druga noga gospodarki
- Dedykowane ręce budują pastwiska przy szopie, przenoszą krowy, karmią, CARE, zbierają mleko i nawóz. Sweep: cow5 stabilniejsze niż cow8 i znacznie lepsze niż goose5 (55.3k vs 40.5k vs 27.0k, 16/18 wygranych).

**PTCG:** Druga noga = Night Stretcher + Pad. `v10_32_final` Pad2 Night1 Cyrano1 = 0.733 vs losses BEST (vs 0.567 dla Pad1). Tak jak cow5 vs cow8 – więcej nie zawsze lepiej, 5 krów > 8 krów.

### 5. Rust port – 100x speedup
- Port **wyłącznie symulatora**, sweep i statystyki zostają w Pythonie. Rust dostaje rozpakowane taśmy JSON, nie wykonuje Pythona.
- Plansze `[Tile;100]`, produkty w tablicach, enumy zamiast stringów, małe ekwipunki zachowują kolejność wstawiania słownika Pythona (ważne przy przepełnieniu szopy), pamięć pomocników rezerwowana przed grą, hot path nie alokuje, MT19937 odtwarza CPython seed, cena zaokrąglana ties-to-even, log(1+x) nie zastąpione log1p, zlecenia przetwarzane jednostka po jednostce.
- Weryfikacja: SHA źródeł, cash bitowo jako binary64, pełne stany tur, Rayon 1 vs wiele wątków identyczne jako bajty JSONL, 120k MT19937 outputs, 270k wycen.

**PTCG:** My mamy `rust_gauntlet` który spawni 38 Pythonów via Rayon – 3-6x speedup (20s vs 66s), ale crash przy buffer full. Docelowo: przenieść heurystykę do Rusta i wołać `libcg.so` via `libloading` + Rayon, tak jak w Kaggriculture – wtedy 100x (0.01s/gra vs 1.5s Python). Obecnie `search_deck_rust.py` timeoutuje bo `Command::output()` bez timeoutu przy 2 vCPU.

### 6. TOP30 nie jest jedną rodziną
- W TOP30 współistnieją high-turnover (SpaTaro 523 buy, 308 sell, first sell t11) i delayed-sale (Otter Vibe first sell t37). Prosty cel "więcej buy" jest zły – potrzebne parametry warunkowe: kiedy sprzedawać, kiedy trzymać kasę, kiedy wysoka rotacja.

**PTCG:** Top7_live też nie jest jedną rodziną – 35W mirrors (Atharva, Pawit), low-energy aggro (Dragapult Hammer x4 Boss3, Duraludon 11E gust4, Lucario 15E), walls (Crustle, Sylveon). Nasz `v10_34_sig4` 0.932 vs top7, ale 0.567 vs losses – bo losses to inna rodzina. Potrzeba warunkowego kroku jak w Kaggriculture.

### 7. Promotion rules (CURRENT_20260907.md)
- Same seedy i obie strony, porównanie z obecnym V7/V8 Aastik/V8 hybrid – nie ze starymi fertilizer agents, zero crashy, positive margin, win improvement, preserve exact TOP49 open-loop, używaj archiwalnych setów tylko dla finalistów, nigdy nie wnioskuj closed-loop rating strength tylko z open-loop tape.

**PTCG:** Powinniśmy mieć podobne: same seedy, obie strony, porównanie z obecnym best `v10_34_sig4` (0.932 top, 0.777 weighted), nie ze starym `v2_boss`, zero crashy, win improvement vs top7 i losses, preserve vs walls.

### 8. Endgame
- Przestać sadzić pod koniec sezonu (nasiona bez zwrotu) i zoptymalizować podział pracy.

**PTCG:** Przestać attachować energię gdy prize race tight (rem==1) i focus na gust lethal DFS – testowaliśmy lethal only rem==1, ale hurt vs walls. Może warunkowy endgame jak w Kaggriculture: tylko gdy discard Water>=2 i remaining<8 (H1 ma Night Stretcher boost).

## Konkretne pomysły do zaimplementowania w PTCG

1. **Tape opening**: Jeśli opening hand ma 2x Snover + Water, zawsze zagraj Snover na bench T1, Aboma T2 – frozen sekwencja, potem reactive. Tak jak B21/S16.
2. **Self-repairing valve**: Sadź Powerglass tylko gdy discard Water>=1 i active Kyogre (jak marchew >=1.15× pszenicy). Obecnie score tool 288+8 active, bez recycle value.
3. **Cow5 vs Cow8**: Przetestuj Pad2 vs Pad1, Night1 vs Night2 – `v10_32_final` Pad2 Night1 Cyrano1 = 0.733 vs losses BEST, ale `v10_34_sig4` Pad1 Night1 = 0.932 vs top7 BEST. Tak jak cow5 vs cow8 – 5 > 8.
4. **Rust full port**: Przenieś `_score_generic_context` do Rusta, wołaj `libcg.so` via libloading, dodaj per-match timeout 30s + limit rayon threads 2 + wait_timeout – naprawi timeouty przy 22 deckach x2 gry =44 Pythonów na 2 vCPU.
5. **Adversarial benchmark**: 18 real action streams (jak w Kaggriculture) – my mamy `all_eval` 39 decków, `top7_live` 22, `losses_v8` 16, `walls` 2. Róbmy sweep jak w Kaggriculture: `jobs.csv` z seed,tape_a,tape_b,reverse, Rayon 16 threads, wyniki w kolejności wejściowej.
6. **Conditional families**: Nie jeden deck na wszystko – tak jak TOP30 ma high-turnover i delayed-sale, my mamy 35W mirrors vs low-energy aggro vs walls. Zróbmy warunkowy deck: jeśli opp ma 35W (Eugen, Pawit, Anthony) → więcej draw (Pad2 Cyrano1), jeśli opp ma Hammer x4 → więcej Boss.

## Co już mamy z Riemann przeniesione

- ✅ `rust_gauntlet` + Rayon – 3-6x speedup (jak Kaggriculture Rust port, ale jeszcze nie 100x)
- ✅ `search_deck.py` + `gauntlet_live.py` – jak `bench_tune.py` monkeypatchujący stałe i mierzący średnią z wielu seedów
- ✅ `SUBMISSION_LOG.md` + `NOTES_STRATEGY.md` – jak `CURRENT_20260907.md` + `FINDINGS.md`
- ✅ GitHub Actions bridge bez sekretów w repo – identyczna architektura jak Kaggriculture
- ✅ Validation Episode + smoke test – jak w Kaggriculture

## Next z Riemann

- [ ] Zaimplementować tape opening dla T1 Snover
- [ ] Dodać reactive overlay dla walls (jeśli opp active Crustle/Sylveon → +25 do EVOLVE/BENCH jak mirror bonus, ale tylko vs walls, nie vs wszystkie Water)
- [ ] Full Rust heuristic + libcg.so FFI
- [ ] Endgame: stop attach gdy prize race tight i lethal DFS tylko rem==1
