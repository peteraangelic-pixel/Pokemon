# Odpowiedź na diagnozę capa i 13,28 — 31.10.2026

Materiał: załącznik `ODPOWIEDZ-na-peer-audit-20261031.md`; repo Smak `codex/arc-local-lab-v18-20261030`, commit `c0b47ca1`. Odtworzyłem źródło solvera z notebooka `duck-v13-7-final/arc3-duck-v13.ipynb` narzędziem `analysis/materialize_duck.py` i przeczytałem właściwe komórki v13.7 i odzyskanego v3. Nie odczytano rzeczywistych logów rerunu 57811453 ani nie uruchomiono nowego A/B.

## Co jest prawdą

W v13.7 (cell 29; w trybie TRUE_SUBMISSION z włączonym USE_PRIORITY_SCHEDULING) ustawiono concurrency=10 oraz max_runtime_s_per_game=532*60. Przy założeniu 110 gier, 32400 s i 600 s rezerwy podane obliczenie 31800*10/110 = 2890,9 s = 48,18 min oraz stosunek 11,04 są poprawne. Odtworzony solver ma asyncio.Semaphore(concurrency) wokół pełnej gry, zatem długie przebywanie w aktywnej grze może faktycznie blokować kolejne — mocna hipoteza do sprawdzenia. Liczba 110 i realne czasy trwania nie są przeze mnie zweryfikowane z rzeczywistego rerunu.

## Czego nie dowiedziono

- Cap jest maksimum, nie gwarancją trwania. Rzeczywiste sesje mogą kończyć wcześniej; smoke to nie ukryty rerun. Testy z historycznych zapisów nie dowodzą, że każda gra w rerunie trwa do 532 minut.
- W tym samym skrajnym scenariuszu z raportu: jeżeli 10 gier zajmuje po 532 min, a okno trwa 530 min, rozpoczęte są tylko pierwsze 10, nie 55. Aby otrzymać 55 rozpoczętych, potrzebna jest dodatkowa nieznana informacja o rzeczywistych czasach zakończenia; wartość 55 dopasowana do 13,28 nie jest dowodem. Mapowanie niepełnych gier na wynik trzeba sprawdzić w rzeczywistej ewaluacji; nie zakładać bez dowodu, że wszystkie nieuruchomione gry są w mianowniku i liczą zero.
- Nie ma podstaw do prognozy 26,78 ani do twierdzenia, że koszty patchy i inne czynniki nie mają znaczenia. Sama konstatacja że cap/fair wynosi 11 potwierdza ustawienia, nie liczbę rozpoczętych gier, czas, wynik, ani przyczynę.
- `budget_probe.json` wykonywany jest w **komórce 33 przed komórką 34**, która wymienia `bm.games` na `_competition_games()` / `_offline_games()`. Liczba gier w sondzie może dotyczyć poprzedniej listy, nie rzeczywistego rosteru. Faktycznie zapisany r121 smoke budget_probe ma 25 gier, chociaż późniejsza lista smoke jest filtrowana; plik ma `true_submission=false`, 2880 s, więc nie jest dowodem konfiguracji prywatnego rerunu. Na podstawie jednego takiego pliku nie da się rozstrzygnąć hipotezy kolejki.
- Podana poprawka przed wymianą listy powtórzyłaby ten sam błąd; prawidłowa eksperymentalna wersja musiałaby wyliczyć limit dopiero PO utworzeniu faktycznej listy i z uwzględnieniem realnie pozostałego czasu oraz teardown; nie ingerować w bazę bez porównania. Deadline, rzeczywisty harmonogram modelu, cancel i sposób zapisu score wymagają weryfikacji.
- Odzyskane v3 w komórce 20 ma inne ustawienia: w priorytetowym TRUE_SUBMISSION concurrency=120 i cap=532 min. v13.7 zmienia concurrency na 10. Tak więc „jedna linia capa” nie jest tożsama z powrotem do v3; przełączenie concurrency mogłoby też przeciążyć serwer i wymaga osobnego testu.

## Co robić

Szukać rzeczywistych telemetrii v13.7 z rerunu: faktyczny roster/przejście z kolejki do aktywnej gry, timestamp start/stop i przyczyna, liczba poziomów i score; dowiedzieć się, co dokładnie platforma uwzględnia. Sprawdzić dostępność tych artefaktów przed deklaracją ich istnienia. Lokalny pomiar 10 slotów i wielu gier, rozdzielenie czasu startu serwera i pozostałego czasu oraz sparowane testy jakości po skróceniu capu. Pierwsze rozwiązanie eksperymentalne ma liczyć po realnym `bm.games`, nie przed nim, i nie gwarantuje wyniku 26,78. Bez wyraźnego GO nie wysyłać na Kaggle.

Przy ocenie template w pełni zgadzam się z zastrzeżeniem: kontrprzykład oscylacji i sonda fałszywych rozpoznań ograniczają promocję. Bramka single-mismatch nie wykazuje uniwersalnego bezpieczeństwa. To raport analityczny w repo Pokemon, bez wprowadzenia zmian do konkursowego notebooka.
