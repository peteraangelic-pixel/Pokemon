# Dlaczego agent utyka na kolejnych poziomach: klasyfikacja (a)–(d)

Stan na 2026-10-13. Wszystko liczone na CPU, bez GPU.

**Dane wejściowe:**
- 100 przebiegów Franzena (4 przebiegi × 25 gier) i 10 przebiegów v2, wszystkie odtworzone lokalnie przez `replay.py`. Zgodność odtworzenia: 100/100.
- Metryki zachowania na poziomie, na którym agent utknął: `stuck_metrics.py`, wyniki w `stuck_franzen.csv` i `stuck_v2.csv`.
- 10 publicznie dostępnych transkryptów (8 przebiegów Franzena p0 + 2 przebiegi v2). Fragmenty dotyczące poziomu utknięcia czytałem przez `stuck_digest.py`.
  Ocenę hipotezy agenta porównywałem z prawdziwym warunkiem wygranej z kodu gry.

## 1. Metryki zachowania (67 nieukończonych przebiegów Franzena)

| Metryka na poziomie utknięcia | Mediana | p25–p75 |
|---|---|---|
| Akcje | 66 | 37–88 |
| Ruchy bazowe człowieka na tym poziomie | 96 | 58–162 |
| **Akcje / ruchy bazowe** | **0,58** (na naszych 10 grach 0,40) | |
| Akcje bez efektu (no-op) | 2% | 0–11% |
| Różne stany / akcje | 95% | 83–100% |
| Maks. powtórzeń tego samego stanu | 2 | 1–3 |
| Resety | 0 | 0–0 |
| **Tokeny na tym poziomie** | **81k** | 47k–100k |
| Udział w budżecie tokenów gry | 43% | 30–78% |

Wnioski:
- **(d) pętle praktycznie nie występują.** 0 z 67 przebiegów ma mniej niż 50% różnych stanów.
- **Agent jest ograniczony myśleniem, a nie akcjami.** Na poziomie, którego nie rozwiązał, zrobił tylko ok. 0,4–0,6 tylu ruchów, ile człowiek potrzebuje na *rozwiązanie*.
  Do tego spalił ok. 81k tokenów na rozważania.
  v2 („eksperymentuj więcej”) zmienił to minimalnie: 0,40 → 0,46.

## 2. Transkrypty: przypadek po przypadku

| Przebieg | Poziom | Prawdziwy cel (kod) | Co robił agent | Klasa |
|---|---|---|---|---|
| Franzen sk48 | 1 | wagony w kolejności wzorca | 36 bloków myślenia nad celem; poprawną hipotezę miał dopiero pod koniec; zły model popychania kaskadowego | **b** + a |
| Franzen bp35 | 2 | dotrzyj do klejnotu | cel znany; błąd w regule „bezpieczeństwa” we własnym planerze blokował poprawną ścieżkę; 5 akcji, 52k tokenów | **a** |
| Franzen ka59 | 2 | każde gniazdo wypełnione | cel prawie dobry; nie umiał dotrzeć do jednego gniazda (mechanika portali i pchania) | **a** |
| Franzen wa30 | 2 | wszystkie skrzynki w strefie i puszczone | z poz. 1 wyniósł regułę „wypełnij wszystkie pola paska” i szukał nieistniejącego 6. obiektu | **b** (przeuczona hipoteza z poz. 1) |
| Franzen lf52 | 2 | zostaw 1 pionek | cel znany; nowy element (żeton) niezrozumiany | **a** |
| Franzen sp80 | 3 | wszystkie naczynia pełne bez rozlania | zmyślone ograniczenie dotyczące czerwonych belek; model przepływu niezgodny z grą | **a** (+b) |
| Franzen g50t | 3 | klocek w pierścieniu celu | cel znany; mechanika linii i węzłów niezrozumiana | **a** |
| Franzen sc25 | 5 | (gra testowa) | nowa mechanika fali; robił postępy, zabrakło budżetu | **a** |
| v2 ka59 | 3 | każde gniazdo wypełnione | niepewne, czy „pokrycie” ma być dokładne czy częściowe; plus mechanika pchania | a + **b** |
| v2 s5i5 | 3 | kropki na plusach | cel znany; złożone przyciąganie i dołączanie; planowanie | **c** + a |

**Bilans (klasa dominująca):** a = 6, b = 3, c = 1, d = 0.

## 3. Wnioski dla strategii

1. **Główny problem to (a): nowa mechanika na kolejnym poziomie.**
   Agent próbuje ją wydedukować z pikseli, np. „let me print rows 26-40…”, zamiast przetestować ją kilkoma tanimi akcjami.
   Koszt akcji w punktach jest niski: do 1× ruchów bazowych na poziom nie traci się prawie nic (kredyt min(115, 100·(base/agent)²)).
   Na poziomie utknięcia agent zużywa tylko ok. 0,4×.
2. **(b) zdarza się częściej po poziomie 1 niż na nim** (wa30, ka59).
   Hipoteza celu dopasowana do poziomu 1 („wypełnij wszystkie pola”) przestaje działać na poziomie 2.
   Pomaga katalog celów: cel jest zawsze typu „wszystkie X spełniają Y”, a jedna gra ma jeden warunek wygranej.
   Do tego warto sprawdzać po wygranej, która hipoteza *naprawdę* odróżnia stan wygrany od poprzedniego.
3. **(c) przeszukiwanie jest rzadkie.** Szybkie przeszukiwanie (Rust + rayon) nie ma dziś uzasadnienia w danych.
   Jedyny konkret: Python w narzędziu agenta ma limit 30 s (`python_timeout_seconds: 30`), a agent w sk48 ograniczał przez to swoje BFS.
4. **Promptowe „eksperymentuj więcej” nie działa** (v2). Potrzebna jest zmiana strukturalna w harnessie, np.:
   - **automatyczny raport o nowych elementach:** po wejściu na nowy poziom harness porównuje obiekty z poprzednim poziomem i wskazuje, co jest nowe (żeton w lf52, fala w sc25…);
   - **wymuszona sonda:** dla każdego nowego elementu harness sam wykonuje 1–3 tanie akcje (klik, wejście, pchnięcie) i podaje modelowi tabelę „akcja → zmiana”, zanim model zacznie się rozpisywać;
   - limit tokenów „rozmyślania” na poziom, po którym harness wymusza eksperyment.
   Wszystkie te rzeczy można testować na CPU na lokalnych grach (bez modelu) pod kątem poprawności, a ich efekt na GPU, 10 gier w 1 h.

## 4. Ograniczenia

- Tylko 10 transkryptów: Franzen publikuje 8, a nasze v2 miało 2 pliki poniżej 2 MB.
  Pozostałe 8 transkryptów v2 jest w wyjściu kernela i da się je pobrać jako skróty (digest) przez CI, bez wrzucania 25 MB do gita.
- Klasyfikacja ręczna, jedna osoba. Granica a/b bywa rozmyta (sp80, ka59).
