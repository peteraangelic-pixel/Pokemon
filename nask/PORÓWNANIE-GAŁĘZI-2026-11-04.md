# Porównanie nowości z innych gałęzi — 2026-11-04

Przegląd conducted na gałęziach:
- `peteraangelic-pixel/Pokemon`: `arena/c87f7a48-pokemon`, `arena/7911f950-pokemon`, `arena/a450b00f-pokemon` (nasza)
- `peteraangelic-pixel/Gemma-konkurs`: `arena/6d081d52-gemma-konkurs`, `arena/c4eeb067-gemma-konkurs`
- `peteraangelic-pixel/Smak-Domu-Konkurs`: `arena/5ed750ef-smak-domu-konkurs`

Nie ingerowano w pracę innych sesji, nie anulowano ani nie modyfikowano ich Actions. W tej sesji nie wykonano aktywnych skanów podatności. Wszystkie obserwacje poniżej pochodzą z publicznych repozytoriów i są tylko hipotezami do weryfikacji, nie potwierdzonymi lukami.

## Najciekawsze pomysły do naszego laboratorium

| Źródło | Pomysł | Jak może ulepszyć nasz projekt | Status |
|---|---|---|---|
| Gemma `6d081d52` / `c4eeb067` | `nasktriage`: offline porównanie zrzutów HAR z dwóch własnych kont; kategorie `permission_asymmetry`, `idor_candidate`, `token_in_url`, `unauth_access`, `sensitive_cached`; kod scope i rate bez modułu sieciowego. | Dodaliśmy `nask/lab/har_triage.py` z tymi kategoriami i testami. Jest to rozszerzenie `auth_matrix.py`, nadal bez sieci i bez prawdziwych danych. | Zrobione |
| Gemma `c4eeb067` | Przy 5 req/s wąskim gardłem nie jest CPU, tylko decyzja, co wysłać; Rust/Rayon ma sens tylko w analizie offline (kod, bundle JS), nie w fuzzerze sieciowym. | Potwierdza nasz kierunek: `safe_client.py` i `lab.py` są offline/ograniczone; FFI tylko po pomiarze. | Potwierdzone |
| Gemma `6d081d52` | `moje.cert.pl`: nagłówki `x-original-url` / `x-forwarded-prefix` zmieniają odpowiedź dla ścieżek `/panel`, `/admin`, `/dashboard`, `/profil`, `/konto`, `/moje` (403/404/429), przy czym bez nagłówka `GET /` zwraca 200. Podobnie `incydent.cert.pl` 429. | Traktować jako hipotezę routingu/proxy/WAF, nie jako potwierdzone omówienie autoryzacji. Może być wartościowa tylko po wyjaśnieniu z organizatorem, czy testy nagłówkowe na własnym koncie są w scope. | Zapisane jako hipoteza |
| Gemma `c4eeb067` | Przegląd `mwdb-core`: jedna wspólna ścieżka `access_object → Object.access`, klasyczny IDOR po ID mało prawdopodobny; większe ryzyko w OAuth, udostępnianiu i capabilities wdrożenia. | Nie polować na IDOR w `mwdb` bez dwóch własnych kont i wyjaśnienia scope; analiza kodu offline jest bezpieczniejsza niż fuzowanie. | Uwzględnione |
| Smak `5ed750ef` | Nocny skan Actions: 0 sekretów w 47 bundle'ach, `_next/image` SSRF zamknięte, brak refleksji XFH, `science.nask.pl /api/downloadFile` żywy ale redundantny wobec publicznego `/api/media/`, `dataannotation` wymaga konta, `oad.nask.pl/podglad-pdf` nie jest SSRF/LFI (prefiks `/media/`, 500 bez danych). | Nie powtarzać zamkniętych ścieżek; `oad` wykluczone z dalszych testów; nie raportować skanerowych „kandydatów 200+JSON" bez ręcznego PoC. | Uwzględnione |
| Pokémon `c87f7a48` / `7911f950` | Rejestr leadów, runbook, wykluczenia, bundle_scan, surface probe Next.js i przechwytywanie nagłówków przed `r.bytes()`. | Przydatne jako wzór dokumentacji leadów i runbooków; nasze `nask/lab` pozostaje offline, aktywne probes tylko po zgody użytkownika i na własnych kontach. | Uwzględnione |

## Co nie jest luki — wykluczone z dalszej pracy (według obcych raportów, nie nasze ustalenia)

- Brak nagłówków/HSTS, flag cookie, mixed content, SPF/DKIM/DMARC bez spoofingu, wersje/ścieżki/IP, stack trace, listingi katalogów, user enumeration, autocomplete, publiczne endpointy debug bez eskalacji, CVE bez PoC, self-XSS, tabnabbing, clickjacking bez krytycznej akcji, czysty HTML injection, CSRF bez wpływu na stan, blind SSRF tylko DNS, open redirect bez scenariusza, DoS/testy obciążeniowe, brak rate-limitu bez scenariusza, subdomain takeover bez PoC, błędy UX, raporty samych skanerów.
- `moje.cert.pl` zmiany 403/404 po nagłówkach `x-original-url`/`x-forwarded-prefix` bez dowodu dostępu do cudzych danych — sygnał do sprawdzenia, nie zgłoszenie.
- `science.nask.pl /api/downloadFile`: contract live, ale widoczne ID to publiczne zdjęcia; brak dowodu dostępu do niepublicznego pliku.
- `oad.nask.pl/podglad-pdf`: prefiks walidowany serwerowo, poza nim 500 bez danych; próby SSRF 500 bez odczytu.

## Następne kroki

1. Uruchomić nowe testy `nask/lab/tests/test_har_triage.py` i całe `nask/lab/tests` przed dalszym rozwojem.
2. Jeśli użytkownik udostępni kontrolowane konta na `moje.cert.pl` lub `dataannotation.pllum.org.pl`, przygotować porównanie dwóch własnych kont na podstawie `har_triage.py`, tylko w przeglądarce i tylko własne zasoby.
3. Nie testować `oad.nask.pl/podglad-pdf`, `secure.edu.pl` z Actions, `www.nask.pl` bez wyjaśnienia scope, ani Władysławowa.
4. Przed jakimikolwiek testami sieciowymi poprosić organizatora o wyjaśnienie, czy regulamin usługi `moje.cert.pl` (powstrzymanie się od testowania omijania zabezpieczeń) pozwala na testy konkursowe na własnym koncie.

Wszystkie commity tej sesji są na `arena/a450b00f-pokemon`; ostatni [CI 41736316785](https://github.com/peteraangelic-pixel/Pokemon/actions/runs/41736316785) zakończony sukcesem.
