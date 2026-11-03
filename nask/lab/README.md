# NASK lab — offline prototype

**Stan: analizator `lab.py` i testy są offline; osobny `safe_client.py` może wykonywać ograniczone żądania po ręcznym włączeniu. Żaden z nich nie znajduje ani nie weryfikuje rzeczywistych luk.** Wbudowany fixture wykorzystuje wyłącznie syntetyczne domeny `*.example.invalid`; nazwy programów są etykietami demonstracyjnymi, a kod HTTP i różnice są wymyślone.

## Uruchomienie (Python 3.9+)

```bash
python -m unittest discover -s nask/lab/tests -v
python nask/lab/lab.py nask/lab/fixtures/demo.json
```

Wyjście porównuje wyłącznie fikcyjne metadane wariantów dla tego samego URL. Różnica w kodzie lub fingerprint nie jest dowodem luki; brak różnicy nie dowodzi bezpieczeństwa. Fixture należy traktować jak kod testowy, nie wkładać do niego prawdziwych odpowiedzi, tokenów, URL z sekretami, danych osobowych ani wyników produkcyjnych. Walidacja danych to nie system zapobiegania wyciekom.

Prototyp zawiera planowanie round-robin z wagą dwa dla NASK i limiter bez burstu jako **niezależny komponent demonstracyjny**. CLI nie wywołuje limitera: to tylko odczyty lokalnego słownika. Limiter nie jest współdzielony między procesami, maszynami lub Actions i **nie nadaje się do bezpiecznego skanowania produkcji**. Ten prototyp nie zawiera klienta HTTP, kont ani PoC; odrębny klient statusów opisano niżej.

## Actions

`.github/workflows/nask-offline-lab.yml`: push zmian laboratorium na gałęzi sesji lub ręczne wywołanie, instalacja Rust stable, testy prostego modułu Rust i Python, syntetyczne dane, brak skanów i eksportu artefaktów. Workflow nie został wysłany na GitHub ani uruchomiony. Moduł `rust-analysis` i `ffi_analysis.py` realizują offline Python/ctypes → Rust/Rayon; kod analizy pochodzi z `peteraangelic-pixel/NASK`, commit `8b3228a470d7714e2315bf20fff31fdb0568ee8f`. Workflow testuje prawdziwe wywołanie FFI na syntetycznych danych. Osobny mały moduł `rust` porównuje metadane. Nie został skompilowany ani przetestowany w tym środowisku (brak cargo). Publiczne repo i logi nie nadają się do przechowywania poufnych wyników.

## Warunki przed jakimkolwiek późniejszym użyciem sieci

- Zweryfikować aktualne regulaminy wszystkich programów i wyjaśnić niejasne domeny. Dodać dokładną, przeglądaną listę dozwolonych celów i wyłączeń, zgodną z każdym regulaminem; kontrolować także port, schemat oraz każde przekierowanie.
- Tylko jeden zatwierdzony proces wysyłający ruch ze wspólnym limitem łącznie dla wszystkich narzędzi i operacji, bez niezależnych runnerów; testy bezpieczeństwa limitera, retry/redirectów, stopów przy 429/503, błędach i ręcznym kill-switchu. Przy niepewnym stanie limitera brak żądania. Pozostać wyraźnie poniżej 5 req/s i nie robić testów obciążeniowych.
- Odrębnie zaprojektować minimalizację zbieranych danych, poufne przechowywanie, kontrolę dostępu i procedurę zatrzymania przy przypadkowym kontakcie z cudzymi danymi. Nigdy publiczne artefakty lub logi.
- Wybrać mały, nieniszczący scenariusz i tylko własne zasoby/konta tam, gdzie pozwala regulamin. Wynik automatu to hipoteza, nie zgłoszenie; przed zgłoszeniem konieczna bezpieczna weryfikacja i ocena CVSS.
- Dopiero po pomiarze kosztów offline rozważyć Rust/Rayon lub FFI; brak cargo w obecnym środowisku, a operacje sieciowe limitowane 5 req/s nie uzasadniają automatycznie FFI. Dodać testy FFI i wsparcie Windows przed zależnością od rodzimej biblioteki.

## Osobny klient statusów korzeniowych (2026-11-03)

`safe_client.py` jest **ograniczonym zamiennikiem pierwszego etapu**, nie forkiem ani naprawą oryginalnego kodu na gałęzi repo NASK i nie skanerem podatności. Realizuje tylko niezalogowane GET `/` dla wbudowanych dokładnych hostów NASK/CERT/Gov/mSzyfr, bez Władysławowa, bez zgadywania i bez `www` aliasów. Sporne pary `pllum/plum`, `mwdb/wmdb` i CTF są wstrzymane; `dataannotation.pllum.org.pl` widnieje osobno w obu wersjach regulaminu. Dla mSzyfr jest jeden dokładny host wykryty w publicznym indeksie, a nie automatyczna enumeracja wildcardu.

- Domyślnie **dry-run**, bez połączeń. Plan: `python nask/lab/safe_client.py --program nask --program cert --program gov --program mszyfr --requests 4`.
- W kodzie ścieżka rzeczywistego pobrania wymaga `--execute`, własnoręcznie potwierdzonej dzisiejszej daty weryfikacji regulaminów (`--reviewed-on YYYY-MM-DD`) i `--sole-operator` (żaden inny proces, komputer ani runner nie prowadzi równoległych testów). To oświadczenia użytkownika, nie automatyczna weryfikacja. Ten klient **nie wykonuje rzeczywistych żądań w Actions**.
- Jedno żądanie naraz, minimum 1 s odstępu rozpoczęcia, maks. 16 na uruchomienie; bez retry, bez przekierowań, TLS z weryfikacją, bez ciasteczek, nagłówków autoryzacji ani proxy z otoczenia. 403/429/5xx i błędy transportu zatrzymują całą kampanię. Selekcję kolejkuje round-robin.
- Przyjmuje wyłącznie nazwy programów z zakodowanej listy; nie przyjmuje dowolnych URL, ścieżek czy hostów. Nie czyta i nie zapisuje treści odpowiedzi ani nagłówków, nie wysyła formularzy. Wypisuje tylko nazwę programu, host i status. Jest to ograniczenie ryzyka, nie dowód, że w nagłówkach lub danych wymienianych podczas połączenia nigdy nie pojawią się informacje wrażliwe. Nie nadaje się do badania logowania ani cudzych zasobów.
- Blokada `~/.nasklab-network.lock` chroni tylko procesy tego klienta korzystające z tego samego konta/komputera; nie synchronizuje innych narzędzi, runnerów, maszyn czy innych użytkowników. Jeśli program zostanie brutalnie przerwany i plik zostanie, należy najpierw potwierdzić, że proces nie działa, a potem usunąć stary plik blokady. Żadnych równoległych kampanii; bez pewności co do łącznego ruchu nie uruchamiać.

Testy kontrolne używają atrap odpowiedzi i nie łączą się z prawdziwymi usługami. Nadal potrzebny jest przegląd operatora, aktualnego scope i warunków hostingu przed rzeczywistym uruchomieniem. Zbieranie statusów nie dowodzi istnienia ani braku luki.

## Audyt czasów wielu procesów

`audit_events.py` działa całkowicie offline i przyjmuje wyłącznie celowo zredukowany JSONL z polami `source` i `started_at` (czas ISO 8601 ze strefą i co najmniej milisekundami). Zlicza łączne rozpoczęcia w ruchomym oknie jednej sekundy oraz źródła okna o największej liczbie; nie zapisuje adresów ani treści. Brak kompletnych logów, niska precyzja znaczników, różnice zegarów lub brak dowodów czasu rozpoczęcia oznaczają, że wynik nie wykazuje zgodności z limitem. Surowych danych z odpowiedziami, URL-ami, sekretami i PII nie używać jako wejścia ani nie publikować. Wyłącznie dane syntetyczne są w testach.

## Kontrola dostępu — wyłącznie analiza offline

`auth_matrix.py` porównuje tylko dostarczone kody statusu i deklarowaną relację zasobu (prywatny/współdzielony/nieznany). Użytkownik otrzymujący dostęp do udostępnionego mu zasobu nie jest IDOR-em. Nawet 200/200 dla prywatnego zasobu to wyłącznie sygnał do sprawdzenia faktycznej treści, właściciela, stanu uprawnień i zgodności zakresu — nigdy automatyczne stwierdzenie luki. 401/403/404 to odmowa lub ukrycie, nie dowód bezpieczeństwa całej aplikacji. Nie przechowywać ani nie przekazywać tu cudzych danych, tokenów ani surowych odpowiedzi.
