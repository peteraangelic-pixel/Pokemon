# ARC-AGI-3 (ARC Prize 2026) — wszystko, co ustaliłem o ich gałęzi i konkursie

Komplet wyników audytu gałęzi `peteraangelic-pixel/Smak-Domu-Konkurs`
@ `arena/5ed750ef-smak-domu-konkurs`, wykonanego **24.10.2026**. Nic tu nie jest
zgadywane: każda liczba ma źródło (plik i linie w ich repo, log z runa, albo mój pomiar
z podaną metodą), a każdy patch jest zweryfikowany przez `git apply` na prawdziwym drzewie.

Ten katalog jest **samowystarczalny dla innej gałęzi / innej sesji**: są tu wnioski, dowody,
kod, testy i narzędzia do odtworzenia wszystkiego od zera (łącznie z instrukcją pobrania
ich drzewa, bo piaskownica nie ma `git clone` do tego repo).

## Od czego zacząć (3 minuty)

1. **`PATCH-0004-I-SEARCH.md`** — najważniejsze: **run-killer** w ich linii `duck-v7`
   (patch 0003 nie nakłada się po patchu Franzena, a cell 9 ma `check=True` → notebook umiera
   przed pobraniem wag), dwa bugi czyniące `v7-abandon` martwym kodem, oraz co dostarczam
   w zamian. Tam jest też gotowe wpięcie do notebooka i rekomendowane env.
2. **`FAKTY-I-POMIARY.md`** — kompendium: silnik, **punktacja z dowodem**, 25 gier, ich
   konfiguracja, serwer, pomiary runów, stan Kaggle, kolejka ops, pułapki narzędziowe, mapa repo.
3. **`FAKTY-I-POMIARY.md` §1bis** — jak naprawdę wyglądają gry click-owe (skan 4096
   współrzędnych), odkrycie wewnętrznego API silnika `_get_valid_actions()` wraz z
   **ostrzeżeniem, że nie wolno go używać w submisji**, i legalny zamiennik na publicznym
   API (kalibracja po efekcie), który odblokował ft09.
4. **`DIAGNOZA-45plus.md`** — dlaczego nie ma 45+ punktów: wypukłość punktacji w głębokości,
   arytmetyka budżetu tokenów, ranking dźwigni, plan na 9 dni, lista „czego nie robić".
   Na końcu sekcja *AKTUALIZACJA 24.10* z trzema poprawkami do tej diagnozy.

## Najważniejsze liczby (skrót)

| fakt | wartość | źródło |
|---|---|---|
| ich najlepszy wynik na LB | **26.25** (duck v3, 16.10) | `ops/results/r062-submissions` |
| próg nagrody $40k (5. miejsce) | **40.97** (NVARC3) | `public_leaderboard.csv` 10.10 |
| średni score smoke r019 | **27.21**, sufit z głębokości **29.0** | `r019/benchmark.json` |
| +1 poziom w każdej grze | **44.8** · +2 poziomy → **64.5** | j.w., przeliczone ich formułą |
| tokeny na akcję | **841** (1.74 M / 2065) | j.w. |
| tokeny i akcje na poziomie, który **nigdy nie został ukończony** | **35%** (tn36 86%, ls20 91%) | j.w. |
| realny budżet tokenów na grę | **~175k** = ~208 akcji, przy `ΣBas ≈ 685` potrzebnych | arytmetyka z `serve.log` |
| cała wartość optymalizacji **efektywności** ruchu | **1.75 pkt** (29.0 − 27.21) | §2 FAKTY |
| nasz playbook (search offline, **0 tokenów LLM**) | **11/25 gier, 16 poziomów = 3.18 pkt LB**, każdy replay-verified | `results/playbook.json` |
| najgłębsze rozwiązanie | **tu93: 5 poziomów = 33.33 pkt** (dokładnie w capie) | j.w. |
| postęp z samej kalibracji ruchów | **+3 gry** (ar25, cn04, ft09), 2.59 → **3.08 pkt LB** | `tools/sweep2.py`, §1bis FAKTY |
| postęp z 5× większego capa | **+1 gra** (s5i5, 21 akcji), 3.08 → **3.18 pkt LB** — i dowód, że tylko tryb `cap_cut`/`time_cut` leczy się budżetem | `results/sweep3_bigcap.jsonl`, §1bis(g) FAKTY |

**Najważniejszy wniosek strategiczny** (dowód w `FAKTY-I-POMIARY.md` §2): przy grze
≤1.07× baseline **cap punktacji zawsze wiąże**, więc
`score_gry = 100 · Σ(wag ukończonych poziomów) / Σ(wag wszystkich)`.
Czyli wynik zależy **wyłącznie od tego, KTÓRE poziomy się ukończyło** — liczba akcji ponad
ten próg jest warta dokładnie zero. Jeden poziom w 7-poziomowej grze to maksymalnie 3.57 pkt;
pięć poziomów w 9-poziomowej to 33.33. **Głębokość jest jedyną dźwignią.**

## Zawartość katalogu

```
README.md                     ten plik
PATCH-0004-I-SEARCH.md        run-killer + bugi 0003 + patch 0004 + wyniki searcha (GŁÓWNY)
FAKTY-I-POMIARY.md            kompendium zmierzonych faktów z proweniencją (11 sekcji)
DIAGNOZA-45plus.md            diagnoza „dlaczego nie ma 45+" + ranking dźwigni + plan 9 dni
arc3_level_budget.py          czysta logika patcha 0004 (bez harnessa, bez GPU)
arc3_search.py                wyszukiwarka offline: BFS / beam + segmentacja kandydatów kliku

patches/
  0003b-early-abandon-rebased.patch      NASZ: ich 0003, logika 1:1, POPRAWIONY kontekst
  0004-level-token-cap.patch             NASZ: budżet poziomu (wymaga 0003b)
  0004-standalone-level-token-cap.patch  NASZ, ZALECANE: to samo bez zależności od 0003
  # cztery poniżej to ICH patche, skopiowane żeby verify_patch_chains.sh działał bez
  # pobierania ich repo (wydobyte z duck-v7.ipynb przez extract_notebook_patches.py):
  0000-franzen-harness-changes.patch     ich cell 4 (498 KB, 16 plików) - nakładany PIERWSZY
  duck-extra-00.patch                    ich cell 5 = "0001" (tool_agent)
  duck-extra-01.patch                    ich cell 6 = "0002" (world model + nudge, 4 pliki)
  duck-extra-02.patch                    ich cell 7 = "0003-early-abandon" <- RUN-KILLER

tests/
  test_arc3_level_budget.py   16 testów; OK na drzewie z 0003b, OK (skipped=2) na standalone

tools/
  sweep2.py                   PRZEGLĄDARKA v2: kalibracja ruchów po EFEKCIE (hash ramki),
                              pruning martwych ruchów, tryb po efektywnym rozgałęzieniu.
                              To ona rozwiązała ft09 (0 poziomów -> 1 poziom w 4 akcjach).
  fetch_repo_artifacts.sh     pobranie ich drzewa przez gh api (25 gier + metadata + 42 pliki
                              bundle + notebooki + migawka 492 blobów) — obejście limitu 1 MB
  extract_notebook_patches.py wydobycie patchy z komórek 4-7 notebooka (dwie różne postaci)

Katalog `notebook/` (osobny, z własnym README) zawiera GOTOWY naprawiony notebook:
  notebook/arc3-duck-fixed.ipynb  ich duck-v7 po naprawie run-killera i z patchem 0004.
                                  Wygenerowany przez tools/make_notebook_patch.py,
                                  zweryfikowany end-to-end (łańcuch z komórki 10: 4/4 OK,
                                  py_compile 3/3 OK, testy 16/16 OK). W README obok są
                                  SHA-256 źródła i wyniku, więc zestarzenie się wykrywalne.
  notebook/README.md              proweniencja, co dokładnie zmieniono (2 rzeczy), czego
                                  NIE ruszono, kill-switch i lista „czego nie robić".
  calib_probe.py              SONDA diagnostyczna BEZ searcha (0.5-8 s/grę): mierzy
                              available_actions, liczbę różnych efektów kliku, medianę
                              zmiany px, efektywne rozgałęzienie i signal_quality.
                              Importuje funkcje sweep2, więc metoda jest identyczna.
                              UWAGA: pomiar na 25 grach obalił używanie signal_quality
                              jako PREDYKTORA - patrz FAKTY §1bis(e)
  make_notebook_patch.py      GENERATOR NAPRAWIONEGO NOTEBOOKA: bierze ich arc3-duck.ipynb,
                              podmienia treść komórki 7 (run-killer 0003) na nasz
                              0004-standalone i aktualizuje ARC3_VARIANT (env + nazwy patchy).
                              Struktura notebooka bez zmian (30 komórek przed i po).
                              Wynik zweryfikowany end-to-end: results/verification_notebook.txt
  verify_patch_chains.sh      DOWÓD: łańcuchy A/B/B'/C + py_compile + testy (patrz niżej)
  score_formula.py            formuła punktacji + weryfikacja na r019 + wartość playbooka
  sweep.py                    przegląd v1 (BFS/beam + segmentacja blobów) — źródło wyników
                              w results/sweep_*.jsonl; zachowany dla odtwarzalności,
                              ale ma ślepy generator klików (patrz §1bis FAKTY)
  build_playbook.py           budowa playbooka + WERYFIKACJA REPLAYEM na świeżej instancji

results/
  playbook.json               11 gier / 16 poziomów, sekwencje akcji, replay-verified, 3.18 pkt
  game_metadata.json          25 gier: baseline, tagi, ΣBas, sufity głębokości, wynik searcha
  sweep_results.jsonl         przebieg płytki (3k węzłów/grę)
  sweep_deep.jsonl            przebieg głęboki v1 (12k węzłów/grę)
  sweep2_results.jsonl        przebieg v2 z kalibracją po efekcie (8/25 gier — proces
                              zabity przez presję pamięci przy 2 workerach z deepcopy)
  sweep2_rest.jsonl           dokończenie v2 na 12 grach (1 worker): 11/12 zapisanych,
                              lf52 zabity po 1783 s — blokada na animacji, patrz FAKTY
                              („Limit czasu jest NIEWYMUSZALNY z wnętrza pętli")
  sweep_merged.jsonl          scalone najlepsze z przebiegów v1
  sweep_best.jsonl            scalone najlepsze ze WSZYSTKICH 4 przebiegów (źródło playbooka); przy remisie bierze przebieg z bogatszą diagnostyką (v2 > v1)
  sweep_shallow.log, sweep_deep.log, sweep2.log, sweep2_rest.log   surowe logi
  their_tree_snapshot.tsv     migawka ich gałęzi: 492 bloby (SHA / rozmiar / ścieżka)
  verification_output.txt     zapisany output verify_patch_chains.sh (dowód run-killera)
  verification_notebook.txt   PRAWDZIWY przebieg weryfikacji WYGENEROWANEGO notebooka:
                              skróty SHA wydobytych patchy, łańcuch z komórki 10 (4/4 OK),
                              py_compile (3/3 OK), testy jednostkowe 16/16 OK
```

## Jak odtworzyć dowody (bez GPU, bez slota Kaggle, ~1 minuta)

Patche ich linii są **skopiowane do `patches/`**, więc dowód run-killera działa od razu,
bez pobierania ich repozytorium:

```bash
cd arc3-handoff/tools
# pristine drzewo PRE-patch (42 pliki ARC3-Inference) - patrz niżej, skąd je wziąć
WORK=/tmp/arc3-verify ./verify_patch_chains.sh <sciezka>/bundle/src ../patches
python3 score_formula.py --verify              # formuła odtwarza tn36 3.57 i ls20 3.27
python3 score_formula.py --playbook ../results/playbook.json
```

`<sciezka>/bundle/src` to stan **przed** jakimkolwiek patchem: `./fetch_repo_artifacts.sh /tmp/arc3`
daje to w `/tmp/arc3/bundle/src` (42 pliki z `r033-recon-bundle`, `solver.py` = blob `0b69d62`).
Do pełnego odtworzenia od zera:

```bash
./fetch_repo_artifacts.sh /tmp/arc3            # 25 gier, metadata, 42 pliki bundle, notebooki
python3 extract_notebook_patches.py /tmp/arc3/bundle/duck-v7.ipynb /tmp/patches   # ich 4 patche
```

`verify_patch_chains.sh` buduje pristine drzewo i nakłada patche **dokładnie komendami z ich
cell 9** (`git apply --include=ARC3-Inference/*`, cwd = `<bundle>/src`), potem raportuje:

| łańcuch | sekwencja | oczekiwane | znaczy |
|---|---|---|---|
| **A** | franzen → 0001 → 0002 → **0003b** → **0004** | OK | nasz pełny zestaw działa |
| **B** | franzen → 0001 → 0002 → 0004 | FAIL `solver.py:47` | 0004 kotwiczy się na imporcie z 0003b |
| **B'** | franzen → 0001 → 0002 → **0004-standalone** | OK | wpięcie zalecane |
| **C** | franzen → 0001 → 0002 → **ich stary 0003** | FAIL `solver.py:35` | **run-killer** |

Zapisany wynik: `results/verification_output.txt`.

## Jak odtworzyć search

```bash
python3 -m pip install --user --break-system-packages -q numpy pydantic pillow
python3 -m pip install --user --break-system-packages -q --no-deps --ignore-requires-python arcengine
python3 tools/sweep.py --games-dir /tmp/arc3/games --node-cap 12000 --sec-cap 300 \
        --max-levels 6 --beam 120 --click-candidates 28 --workers 2 --out /tmp/sweep.jsonl
python3 tools/build_playbook.py /tmp/sweep.jsonl     # + weryfikacja replayem każdej sekwencji
```

~45 min na 2 rdzeniach. `sweep.py` wymaga `metadata`/ścieżek w nagłówku — domyślne ścieżki
są w stałych na górze pliku (`GAMES`, `META` w `build_playbook.py`).

### Pułapka w NASZYM własnym narzędziu (znaleziona i naprawiona 24.10)

`sweep.py` zapisywał numer poziomu jako `base + lvl`, ale `base` **samo rośnie** po każdym
rozwiązanym poziomie (to liczba już ukończonych), więc indeksy wychodziły `0, 2, 4, 6, 8`
zamiast `0, 1, 2, 3, 4`. Objaw: `score_formula.py --playbook` dawał tu93 = **55.56**, a
`--game tu93 --actions 18,10,19,17,29` dawał **33.33** — bo pierwszy czytał pole `level`
z playbooka, a drugi liczył od zera.

`build_playbook.py` używa `enumerate`, więc **wartość playbooka (wtedy 2.59 pkt, dziś 3.18 pkt po kalibracji ruchów po efekcie i przebiegu z capem 60 000) i `expected_game_score`
były poprawne cały czas** — błędne było tylko pole `level` w JSON-ie. Naprawione w `sweep.py`
(`"level": base`), a istniejące artefakty w `results/` zreparowane renumeracją
(`level = indeks kolejny`). Gdyby to zostało, harness kluczujący replay po polu `level`
podstawiłby sekwencje pod złe poziomy.

Wniosek ogólniejszy: **numer poziomu w tych danych zawsze == indeks kolejny wśród
ukończonych**, bo poziomy padały po kolei. Nie licz go z `levels_completed + licznik pętli`.

## Stan operacyjny na 24.10 ~16:45 UTC (żeby nic nie zepsuć)

- **Nie pushować `arc-agi-3/kaggle/ops/request.json`** do ich gałęzi, dopóki wisi run:
  `42bb78b` in_progress od 13:48, `ad8b804` (r065) pending od 14:02. Push kasuje wiszące runy
  (lekcja z ich r057).
- Kolejka r065 idzie na kernel **`arc3-duck-original`**, którego notebook ma **zero patchy** →
  run-killer go nie dotyczy. Dotyczy każdej następnej próby linii **`duck-v7`** (ich 26.25).
- GPU quota 30 h/tydz. wyczerpana 16.10; API submit daje `400 CreateCodeSubmission` → klik w UI.
- **Final submission deadline 2 XI 2026** (~9 dni, ~8 slotów przy 1/dzień), wyniki 4 XII.
  26 X to był deadline **zgłoszenia** (spełniony, 6 zaliczonych submisyji).
- Ich własne zasady, których nie łamać: jedna dźwignia na submisję, nie prowadzić dwóch torów
  naraz, nie submitować bez `ARC3_SMOKE_OK`, nie planować na niezweryfikowanych krzywych,
  nie sumować nakładających się sufitów.
