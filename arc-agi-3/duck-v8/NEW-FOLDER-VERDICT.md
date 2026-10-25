# Folder `arc-agi-3/new/` (pakiet v9 od DeepSeeka) — werdykt po inspekcji

Data: 25.10.2026. Obiekt: folder `new/` na tipie Smak `9fb6641` („Add files via upload").
Wszystkie liczby poniżej przeliczyłem/u ruchomiłem sam w tej sesji; nic nie jest przepisane z dokumentów.

## Co to jest

Realny, kompletny pakiet, nie szkic: `arc3-duck-v9.ipynb` + `kernel-metadata.json`
+ `tools/build_v9.py` + `tools/v9_metrics.py` + `tools/test_v9_metrics.py`
+ `tools/verify_offline.py` + `verify.sh` + `src/base-c45.ipynb`
+ `examples/r019-benchmark.json` + `README.md` + `OCENA-I-PLAN.md` + `LEPSZA-DROGA.md`.
To dokładnie ta sama treść, którą DeepSeek linkował z freebuff — teraz nareszcie zacommitowana w repo.

## Zweryfikowane (uruchomione przeze mnie)

- `bash verify.sh <bundle r033> examples/r019-benchmark.json` → **43 sprawdzenia, 0 błędów, 0 pominiętych**:
  metadana kompletna i spójna z notebookiem, łańcuch 4 patchy aplikuje się na czysty bundle r033,
  spatchowane drzewo kompiluje, enve `ARC3_SYSTEM_PROMPT_PREFIX` / `ARC3_MAX_ACTIVE_STREAMS` /
  `ARC3_LEVEL_TOKEN_CAP` honorowane, testy analizatora OK, formuła wyniku odtwarza r019.
- `tools/test_v9_metrics.py` → **7/7 OK**.
- `v9_metrics.py examples/r019-benchmark.json` → odtwarza **27,21**, formula check max diff **0,0**,
  bramka FAIL zgodna z baseline'em (to celowe: r019 jest poniżej progu v3 smoke 29,02).
- **Odtwarzalność buildu**: `tools/build_v9.py` regeneruje `arc3-duck-v9.ipynb` **bajt w bajt**
  (sha256 zgodne: `29a9ce1a…`). Rzadka rzecz w tym projekcie — duży plus.
- `src/base-c45.ipynb` to kopia przyjętego c45 **z poprawką** `TAAF_MINIMAL_DIAGNOSTICS` ALWAYS —
  pakiet nie cofa znanej poprawki antykryzysowej.
- `kernel-metadata.json` v9: prawdziwe źródła Franzena + id `petersharps/arc3-duck-v9` — poprawne
  (w przeciwieństwie do starego `duck-c45/kernel-metadata.json`, który Smak naprawił osobno w `2623460`).

## Wady i niespójności (znalezione, nie zmyślone)

1. **`v9_metrics` miesza dwie definicje średniej.** `summarize()` liczy średnią z proporcji per gra
   (na r019: a/call **5,2**, tok/act **933**), a stałe baseline w tym samym pliku
   (`R019_ACTIONS_PER_CALL=4.36`, `R019_TOK_PER_ACTION=841`) są **agregatami** (suma/suma).
   Skutek: analizator uruchomiony na samym r019 raportuje „batching lever moved +0,84" —
   fałszywy sygnał przy zerowej zmianie kodu. Przed użyciem bramkowym ujednolicić na agregaty.
2. Tabela w `OCENA-I-PLAN.md` §2.2: kolumna wywołań sumuje się do **474** (średnia 47,4/grę),
   a wiersz ŚREDNIA podaje 42,2. Drobiazg, ale to ta sama tabela, z której biorą się wnioski o dźwigniach.
3. **`LEPSZA-DROGA.md` jest w tym folderze najsłabszym dokumentem** i sama `OCENA-I-PLAN.md` ją częściowo
   unieważnia: „1,13 akcji/request" pochodzi z `*_requests.jsonl` (u mnie: 1 417 requestów/8 gier,
   nie 1 777), a `v9_metrics` używa konwencji wpisów historii (4,36). Profil `deep` (dyrektywa 8–15 akcji/call)
   stoi na tej słabszej liczbie; kontrprzykład jest w samej OCENIE: ls20 ma 13,9 akcji/call i 3,27 pkt.
   `deep` ma sens tylko jako tani pomiar, nie jako zakład.
4. `verify.sh` po uploadzie przez web GitHub stracił bit wykonywalności → `./verify.sh` = Permission denied;
   uruchamiać `bash verify.sh`. Bez argumentów pomija 2 sprawdzenia (34 zamiast 43).
5. Profile `deep`/`wide` są **niezmierzone**; `wide` (MAXREQ 14) przy zmierzonym KV 0,71 med / 0,99 max
   na 10 strumieniach może wywrócić run — słusznie nie jest domyślny.

## Wartość praktyczna (po odjęciu tego, co już macie)

- Naprawę metadany Smak zrobił niezależnie (`2623460`) i c45 już poszedł: r075 utworzył
  **ref `57629847` (PENDING)** i zużył dzisiejszy slot. Push v9 z `PROFILE=c45` powtórzyłby dzisiejszą pracę.
- Unikalna wartość pakietu na kolejne sloty: **komórka pomiarowa** (actions/need/calls/a-call/tok-act
  w każdym runie, zero tokenów) + profile jako pojedyncze przełączniki + odtwarzalny build.
- Arytmetyka OCENY zgadza się z moimi przeliczeniami co do znaku i rzędu: głębokość 28,8% (206/718 akcji),
  sufit efektywności ruchów ~29,0, +1 poziom/grę ≈ 44, widełki v9 33–42 uczciwe, 45+ to zakład, nie plan.

## Rekomendacja

1. Czekać na wynik `57629847` (c45) — to pierwszy pomiar linii szybkiej; v9 dziś nie jest kandydatem
   na żaden slot.
2. Przed pierwszym użyciem `v9_metrics` jako bramki: poprawić agregację (pkt 1) — inaczej profile
   będą porównywane złą miarą.
3. Następny eksperyment po c45: jeden profil naraz (decyzja z pomiaru c45, nie z dokumentu),
   z meteringiem włączonym. `deep` traktować jako hipotezę do sfalsyfikowania, nie jako „lepszą drogę".
