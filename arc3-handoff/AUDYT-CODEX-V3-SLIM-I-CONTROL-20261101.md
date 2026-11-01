# Audyt nowych plików Codex na MOJEJ gałęzi: v3-slim (odrzucony) i v3-control (baza) — 1.11.2026

**Materiał.** Trzy commity Codex na `arena/c87f7a48-pokemon` (`17c0054`, `13c2c57`, `a8fde7e`,
1.11 09:58–11:39): 17 plików, **wyłącznie** `arc-agi-3/peer-review/codex-v3-slim-20261101/`
i `arc-agi-3/peer-review/codex-v3-control-20261101/`. **Żadnych innych zmian:** workflowy
`.github/` są moje i stare (`kaggle_submit.yml` i `kaggle_poll.yml` nadal tylko
`workflow_dispatch` — **BEZPIECZNIK nietknięty, żadnej nowej automatyki zgłoszeń**).

**Metoda.** Wszystko policzyłem sam z dostarczonego `benchmark.json` kontroli oraz z JSON-ów
pakietu; czego nie mogę (model docelowy, GPU) — oznaczone jako przyjęte.

---

## 1. Weryfikacja twierdzeń pakietu — wszystkie odtworzone

| twierdzenie | mój pomiar | werdykt |
|---|---|---|
| `arc3-duck.ipynb` (control) = dokładny odzyskany v3, SHA256 `8d0195f9…7bcc` | `sha256sum` = **`8d0195f9…7bcc`**, 617 470 B | ✅ co do znaku |
| smoke kontroli: **27.496670817884922**, 33 ukończenia, 10/10 gier ≥1 | przeliczone z `benchmark.json` pełną formułą RHAE: **27.4966708**, 33, **10/10** | ✅ |
| udział akcji na niedokończonych **15.9829…%** | **0.15983** (300 z 1877 akcji) | ✅ |
| slim: **17.350468479169024**, 24 ukończenia, udział **34.1399…%** | z COMPARISON.json: identycznie; per-gra `[1,1,2,3,2,5,2,3,4,1]` vs kontrola `[3,2,4,3,3,5,5,3,3,2]` = dokładnie delty z RESULT (tn36 3→1 … su15 3→4) | ✅ |
| aktywacja slim: sekcje niesione we wszystkich 10 grach | ACTIVATION.json: `all_ten_games_have_carried_sections: true`, 6–17 wystąpień/grę; `kernel_complete/smoke_ok/crashed_empty: true`; kwalifikacja uczciwa („snapshot counts are not unique turns; final_generated_tokens=0 ≠ zero inference") | ✅ |
| slim = JEDNA zmienna | MANIFEST: `changed_cell: 1`, `extra_patches: 0`, `env_delta: {ARC3_MEMORY_SECTIONS: [off, slim]}`, `base_sha256` = SHA v3, `model_budget_roster_unchanged: true` | ✅ |
| kernel-metadata obu pakietów | slugi **własne** (`…-v3-control-1031`, `…-v3-slim-1101`), `code_file` zgodny z notebookiem w katalogu — **bez driftu w stylu Gemmy i bez brakującego pliku** | ✅ |
| samoodrzucenie slim | RESULT/SLIM-REJECTED: „nie przypisujemy całego spadku jednej przyczynie; pojedyncze przebiegi nie rozdzielają wariancji od wpływu sekcji"; „liczba błędów 25→10 NIE oznacza lepszego agenta" | ✅ dyscyplina wnioskowania poprawna |

**Uwaga o mojej pierwszej próbie (self-korekta nr 24):** pierwsze przeliczenie dało mi
**30.28665** zamiast 27.49667 — **zsumowałem wagi tylko po poziomach TKNIĘTYCH**, a oficjalny
mianownik to suma wag po **wszystkich `number_of_levels`** (plus cap per-gra
`min(score, 100·max_weights/total_weights)`). Po poprawce **zgadza się co do siódmej cyfry**.
To już trzeci raz, gdy „ich liczba się nie zgadza" okazało się moim mianownikiem.

---

## 2. ❗ Moja własna hipoteza mechanizmu — OBALONA zanim spaliła GPU

Zlecenie badawcze pakietu prosi: „najpierw wskaż konkretny błąd/ograniczenie, które zmiana
naprawia". Spróbowałem kierunku (4) z ich listy: **zatrzymywanie powtarzanych nieskutecznych
planów na podstawie obserwacji**. Sygnatura: biegi ≥3 **identycznych** akcji
(`id` + `repr(data)`), poziom po poziomie, na kontroli.

| populacja | poziomów z biegami ≥3 | liczba biegów | akcji „odzyskiwalnych" (len−2) |
|---|---:|---:|---:|
| **NIEukończone** | 8 / 10 | 36 | 95 |
| **Ukończone** | **26 / 33** | **159** | **475** |

**Sygnatura NIE odróżnia przegranych od wygranych — jest silniejsza na WYGRANYCH.**
Przykłady: `ls20` L2 (ukończony, 174 akcje) ma 22 biegi, w tym wzór `[…6,5,3,6,7,8,6,5,7,8,6,5]`;
`s5i5` L5 (ukończony) = `[3,3,3,3,3,3]`; `su15` L4 (nieukończony) = bieg **15**.

**Konsekwencja: reguła „stop po ≥3 identycznych akcjach" uruchomiłaby się 159 razy na liniach
wygranych (26 z 33 poziomów) przeciw 36 razom na przegranych.** To nie bezpiecznik, to granat.
Hipoteza **obalona na danych kontroli**, bez jednego przebiegu GPU — dokładnie dyscyplina,
o którą prosi pakiet. (Self-korekta nr 25: zapisuję obalenie, nie porzucam po cichu.)

**Czego brakuje, aby odróżnić:** `benchmark.json` ma w `history` tylko `action`,
`generated_tokens`, `wallclock_seconds` — **nie ma hasza klatki PO akcji**. Powtórzenia
*identycznej akcji przy niezmienionym stanie* (prawdziwy stall, silnik deterministyczny)
od powtórzeń *legitymnych* (gry wymagające wielokrotnego kliknięcia tej samej komórki;
ponowienia po klatce przejściowej — patrz reguła `frame[-1]` z audytu Gemmy c4eeb067)
**nie da się rozdzielić offline**. **Wymóg na następny przebieg: logować hash klatki po akcji
i licznik `(akcja, hash_po) bez postępu poziomu**; dopiero ta sygnatura może być kluczem
reguły stop. Do tego czasu kierunek (4) jest **hipotezą bez klucza**, nie kandydatem.

---

## 3. Drugie nazwane ograniczenie — prawdziwe, ale bez bezpiecznego klucza

**9 z 33 ukończonych poziomów zużyło WIĘCEJ akcji niż ludzki baseline** (2 powyżej 1,5×):
`dc22` L1 **157 akcji vs baseline 59 = 2.66×** ⇒ punkt poziomu (59/157)² ≈ **0.14**;
`ka59` L1 51/28 = 1.82×; `ls20` L2 174/123 = 1.41×. To mierzalny ciągnik w dół średniej
i druga po ogonie fal kandydatka na przyczynę rozjazdu smoke/rerun.

**Ale każdy klucz, który mam, jest albo obalony (§2: powtórzenia), albo skażony historią:**
cap per-poziom względem własnej mediany to linia self-pace z v13.x, której jedyny pomiar
rerun to **13.28** (confounded kolejką, nie mechanizmem). **Zostawiam jako hipotezę do
rozdzielenia jednym env na modelu docelowym — nie jako kandydata.** Zgodnie z pakietem:
„nie scalać zmian w nadziei na sumę zysków".

---

## 4. Co to zmienia operacyjnie (stan na 1.11, final submission 2.11)

- **v3 jest teraz zmierzony najlepiej na OBU torach:** smoke na docelowym Flash-Next
  **27.49667 / 33 / 10/10 / crashed=[]** (ten pakiet) oraz historyczny rerun **26.25**.
  **To wzmacnia, nie zmienia, moją rekomendację: zgłoszenie finalne = zmierzony mistrz v3.**
  Smoke ≠ rerun (v13.7: 22.59→13.28; v11: 18.55→23.89), więc 27.5 **nie jest obietnicą** —
  jest najlepszą dostępną przesłanką o konfiguracji, która już raz rerun przeszła na 26.25.
- **Jedyny nazwany, jedynozmienny test rerun pozostaje propozycją Smaka**: v13.7 +
  `LEVEL_TOKEN_CAP=45000` + `RESETS_MAX=1` (hipoteza capu/ogona fal). Nie został uruchomiony
  w tej fali; wymaga GO usera.
- **Odrzucone pozostaje odrzucone:** slim 17.35/24, solved-level memory 28.40/32, recovery
  17.11/25 (hook się nie aktywował). **Nie scalać.** Aktywny eksperyment Codex
  (scope retained functions game→levelup) — **nie dublować** (pakiet wprost prosi).
- **Cel 60+ jest celem badawczym, nie wynikiem żadnego dostarczonego kandydata** — zgoda;
  moja arytmetyka z poprzednich audytów (a/call 6.7–7.1 przy marginalnym koszcie 87 akcji/poziom)
  pozostaje opisem DROGI, nie prognozą.

---

## 5. Czego NIE zrobiłem

Nie zmieniłem żadnego notebooka (SHA `8d0195f9…` i `9156966a…` nietknięte), nie zgłosiłem nic
na Kaggle, nie uruchomiłem przebiegu GPU/LLM, nie dotknąłem workflowów ani innych gałęzi.
`PUSH_INSTRUCTIONS`-podobnych poleceń w pakiecie nie ma; pakiet deklaruje „ten pakiet sam nie
uruchamia żadnego testu ani sesji AI" — **zgodnie z obserwacją: tylko pliki i JSON-y**.

**BEZPIECZNIK: zero zgłoszeń bez osobnego GO usera — obowiązuje.**
