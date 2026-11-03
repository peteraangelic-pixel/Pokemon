# NASK lab — offline prototype

**Stan: wyłącznie offline, dane fikcyjne. Nie znajduje ani nie weryfikuje rzeczywistych luk. Nie wysyła żadnych żądań HTTP ani DNS.** Wbudowany fixture wykorzystuje wyłącznie syntetyczne domeny `*.example.invalid`; nazwy programów są etykietami demonstracyjnymi, a kod HTTP i różnice są wymyślone.

## Uruchomienie (Python 3.9+)

```bash
python -m unittest discover -s nask/lab/tests -v
python nask/lab/lab.py nask/lab/fixtures/demo.json
```

Wyjście porównuje wyłącznie fikcyjne metadane wariantów dla tego samego URL. Różnica w kodzie lub fingerprint nie jest dowodem luki; brak różnicy nie dowodzi bezpieczeństwa. Fixture należy traktować jak kod testowy, nie wkładać do niego prawdziwych odpowiedzi, tokenów, URL z sekretami, danych osobowych ani wyników produkcyjnych. Walidacja danych to nie system zapobiegania wyciekom.

Prototyp zawiera planowanie round-robin z wagą dwa dla NASK i limiter bez burstu jako **niezależny komponent demonstracyjny**. CLI nie wywołuje limitera: to tylko odczyty lokalnego słownika. Limiter nie jest współdzielony między procesami, maszynami lub Actions i **nie nadaje się do bezpiecznego skanowania produkcji**. Brak HTTP klienta, kont, prawdziwego scope, PoC i wyzwalaczy sieciowych.

## Actions

`.github/workflows/nask-offline-lab.yml`: push zmian laboratorium na gałęzi sesji lub ręczne wywołanie, instalacja Rust stable, testy prostego modułu Rust i Python, syntetyczne dane, brak skanów i eksportu artefaktów. Workflow nie został wysłany na GitHub ani uruchomiony. Moduł `rust-analysis` i `ffi_analysis.py` realizują offline Python/ctypes → Rust/Rayon; kod analizy pochodzi z `peteraangelic-pixel/NASK`, commit `8b3228a470d7714e2315bf20fff31fdb0568ee8f`. Workflow testuje prawdziwe wywołanie FFI na syntetycznych danych. Osobny mały moduł `rust` porównuje metadane. Nie został skompilowany ani przetestowany w tym środowisku (brak cargo). Publiczne repo i logi nie nadają się do przechowywania poufnych wyników.

## Warunki przed jakimkolwiek późniejszym użyciem sieci

- Zweryfikować aktualne regulaminy wszystkich programów i wyjaśnić niejasne domeny. Dodać dokładną, przeglądaną listę dozwolonych celów i wyłączeń, zgodną z każdym regulaminem; kontrolować także port, schemat oraz każde przekierowanie.
- Tylko jeden zatwierdzony proces wysyłający ruch ze wspólnym limitem łącznie dla wszystkich narzędzi i operacji, bez niezależnych runnerów; testy bezpieczeństwa limitera, retry/redirectów, stopów przy 429/503, błędach i ręcznym kill-switchu. Przy niepewnym stanie limitera brak żądania. Pozostać wyraźnie poniżej 5 req/s i nie robić testów obciążeniowych.
- Odrębnie zaprojektować minimalizację zbieranych danych, poufne przechowywanie, kontrolę dostępu i procedurę zatrzymania przy przypadkowym kontakcie z cudzymi danymi. Nigdy publiczne artefakty lub logi.
- Wybrać mały, nieniszczący scenariusz i tylko własne zasoby/konta tam, gdzie pozwala regulamin. Wynik automatu to hipoteza, nie zgłoszenie; przed zgłoszeniem konieczna bezpieczna weryfikacja i ocena CVSS.
- Dopiero po pomiarze kosztów offline rozważyć Rust/Rayon lub FFI; brak cargo w obecnym środowisku, a operacje sieciowe limitowane 5 req/s nie uzasadniają automatycznie FFI. Dodać testy FFI i wsparcie Windows przed zależnością od rodzimej biblioteki.
