# `nask/har/` — zrzuty HAR z przegladarki usera (TYLKO po redakcji)

| katalog / plik | czy w gicie | co zawiera |
|---|---|---|
| `raw/` | **NIE** (`.gitignore`) | surowe zrzuty HAR z cookie sesji, `Authorization: Bearer`, haslem logowania i tresciami odpowiedzi. Istnieja tylko lokalnie i sa kasowane po redakcji |
| `sanitized/*.sanitized.har` | tak | ten sam zrzut po `har_sanitize.py`: nazwy naglowkow/parametrow/pol, metody, szablony sciezek z `{id}`, kody, rozmiary, odciski `sha256[:12]`, `session_fingerprint` = `sha256[:8]` poswiadczenia. **Zero wartosci poswiadczen, zero tresci** |
| `mapa-api.json` | tak | zageszczona mapa endpointow (host, metoda, szablon, statusy, rozmiary, odciski, nazwy) — wejscie do analizy IDOR przez `vendor/a450b00f/har_triage.py` |

Instrukcja pobrania zrzutu: **`nask/JAK-POBRAC-HAR-20261105.md`**.
Narzedzie redakcji: `nask/tools/har_sanitize.py` (selftest 7 grup, 17 testow jednostkowych,
asercja antywyciekowa `assert_clean`, redakcja idempotentna).

Reguly:
1. Surowego HAR **nigdy** nie commitujemy i nie wklejamy do czatu.
2. Zadnego zadania z poswiadczeniem usera nie wykonuje agent — mapa sluzy do planowania
   zadan nieuwierzytelnionych albo zadan, ktore user klika sam (§6: wylacznie konta wlasne/testowe).
3. Przed commitem kazdego pliku z tego katalogu przechodzi asercja: zadna wartosc zobaczona
   na wejsciu nie moze istniec na wyjsciu (jedno trafienie = przerwanie i brak plikow).
