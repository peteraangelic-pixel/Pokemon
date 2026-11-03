# Niezależny przegląd pakietu START-HERE — 31.10.2026

## Materiał i metoda

Załącznik START-HERE oraz repo `Smak-Domu-Konkurs`, gałąź `codex/arc-local-lab-v18-20261030`, commit `3926007e`. Przeczytane cztery raporty wskazane w załączniku, kod `template_transfer.py`, `template_hook.py`, testy, zapis porównania i wyników 25 gier oraz CSV submisji. Sprawdzono hash notebooka i uruchomiono testy kontrolera w czystym Python venv (NumPy, pytest): **35 passed**. Nie odtworzono Duck/Qwen ani 25 gier; nie sprawdzono oficjalnych reguł konkursowych w pełnym zakresie. Bez wysyłki do Kaggle.

## Submisja

Zapis `analysis/submission-score-check-20261031/own-submissions.csv` podaje v13.7 `57811453`, COMPLETE, 13,28; v11 23,89; historyczne v3 26,25. CSV jest zapisem odczytu, a nie nowym bezpośrednim odczytem Kaggle przeze mnie. Różnica v13.7 vs v3 to −12,97 pkt; te dwa wyniki nie stanowią kontrolowanego A/B. Nie znamy przyczyny różnicy i nie można przypisać jej żadnemu konkretnemu patchowi.

Moja wcześniejsza rekomendacja v13.7 jako podstawy jest wycofana. Także wskazania `a/call ≥ 6` nie wolno traktować jako prognozy 50. Wcześniejsze twierdzenie, że cap 25–30k tnie gry bezproduktywne, było zbyt mocne: replay nie sprawdza skutków RESET na przyszłą trajektorię ani faktycznej poprawy wyniku.

## Kontroler

Notebook `duck-lab-candidates/template/agent.ipynb` ma hash `550eb185aa12efe9450e011c794ff12625adc18db287cf9f8248fa716208d5fa`, zgodny z raportem. Oglądany moduł wprost korzysta z siatki, dozwolonych akcji i poziomu; w nim nie znalazłem czytania game ID, silnika czy odpowiedzi. Jest to przegląd wskazanego modułu, nie pełny audyt konkursowej zgodności wszystkich komponentów notebooka.

Zapisane porównanie wskazuje 3 poziomy/25 akcji vs 0/2 na ft09, jeden seed, lokalny Qwen, ta sama konfiguracja testowa wg manifestów. `diagnosis.json` wykazuje 56 wywołań narzędzi i jeden NameError, a nie błędy API; agregat `error_free` nie obejmuje błędów narzędzi. Nie odtwarzałem tego testu. Publiczny ft09 był używany w rozwoju, więc nie jest testem ślepym. Pozostałe 24 gry w public25 nie miały akcji modułu i zatrzymały się na pierwszej obserwacji: to nie dowodzi, że moduł nigdy nie aktywuje się na ich późniejszych planszach w hybrydzie.

Podstawowy fallback przy `act() is None` rzeczywiście wywołuje oryginalne `analyze` i przetestowany został z mockiem. Izolacja testem obejmuje zmianę ścieżki pliku stanu; nie dowodzi bezpieczeństwa przy powtórnym użyciu tej samej ścieżki dla innej gry. Sama reguła `runtime = str(state_path.resolve())` zachowuje kontroler dopóki ścieżka ta sama. Trzeba ustalić cykl życia realnych ścieżek i dodać testy resetu i równoległości. Stan `learned` celowo przechodzi między poziomami, co jest potrzebne dla ft09, ale zwiększa ryzyko błędnego rozpoznania w odmiennym poziomie. Sprawdzenie efektu następuje dopiero po kliknięciu, a przy zmianie numeru poziomu oczekująca predykcja jest czyszczona; dlatego nie jest to gwarancja, że nie wykona szkodliwej pierwszej akcji ani że sprawdzi każdą akcję kończącą poziom. Wyjątki podczas ekstrakcji/aktu nie są obsługiwane jako fallback: możliwy wyjątek wymaga osobnego testu, a nie założenia bezpieczeństwa.

`kernel-metadata.json` włącza GPU, natomiast metadane wewnątrz notebooka mają `isGpuEnabled: false` oraz `accelerator: nvidiaRtxPro6000`. Nie przesądzam, które ustawienie Kaggle zastosuje; przed jakimkolwiek przyszłym użyciem należy sprawdzić rzeczywistą konfigurację i preflight, bez uploadu bez zgody.

## Dalsze działania

1. Zachować odzyskany historyczny v3 jako punkt odniesienia, ale nie twierdzić, że osiągnie ponownie 26,25.
2. Zweryfikować pochodzenie i hash odzyskanego notebooka wobec rzeczywistego źródła submisji; zestawić rzeczywiste konfiguracje v3 i v13.7.
3. Przetestować kontroler w hybrydzie na wspólnym korpusie, w tym późniejsze stany, mylące struktury, różne seedy, restarty, tę samą ścieżkę dla różnych gier oraz błędy/wyjątki. Mierzyć ukończone poziomy, score i regresje per gra, a nie tylko akcje; docelowo paired A/B na Flash-Next, nie ekstrapolować Qwena 27B.
4. Wybierać następną rodzinę mechanik na podstawie dostępnych śladów i spodziewanego pokrycia; nie używać testowych gier jako jedynego materiału rozwojowego. W aktualnym przeglądzie nowej rodziny nie zaimplementowano ani nie przetestowano.

Stan: nie ma dowodu na 50+, ani na wzrost Kaggle po dodaniu template; jest obiecujący, wąski wynik lokalny. Raport źródłowy sam prawidłowo akcentuje te ograniczenia.
