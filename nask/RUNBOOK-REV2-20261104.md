# RUNBOOK rev 2 (04.11.2026) — kolejność po przeglądzie 6 gałęzi

**Ten plik zastępuje kolejność L1–L5 z `RUNBOOK-RANO-20261104.md`.** Powód: dwie z pięciu
pozycji okazały się niewykonalne (korekty własne #26 i #27 — dowody w
`PRZEGLAD-GALEZI-20261104.md` §4 i §6). Stary plik zostaje jako zapis stanu wiedzy z nocy.

Zasada nadrzędna: **zgłoszenie wysyłamy tylko z działającym PoC i ręcznym potwierdzeniem.**
Trzy odrzucone zgłoszenia pod rząd mogą zablokować możliwość zgłaszania (Gemma-B `IDEAS` §0),
a skaner-only jest wykluczony §8.

---

## L0 — 15 minut usera, bez tego reszta stoi

1. Rejestracja na `hack.cert.pl` + akceptacja **regulaminu platformy** i **regulaminu konkursu
   NASK PIB** (edycja 11/2026). Bez tego nie ma gdzie zgłaszać.
2. **Wniosek do organizatora o konto testowe** na `dataannotation.pllum.org.pl` (HIVE).
   Dowód, że inaczej się nie da: `/api/v1/register` i `/register` → 404 w dwóch niezależnych
   kanałach (Gemma-B + mój run1), `/api/v1/projects/` → 401, `/api/v1/users/1` → 405.
3. **Pytanie o zakres**: §5 wymienia literał `nask.pl`, a apex odpowiada 302 → `www.nask.pl`
   (run007: 8/8 żądań na apexie = 302). Czy `www.nask.pl` jest w zakresie? Bez odpowiedzi cały
   Tier-1 host jest praktycznie nietestowalny. To samo pytanie dla `info-trace.116sos.pl`
   (pojawił się w nagłówku `Access-Control-Allow-Origin` w run1).
4. (Opcjonalnie, osobna decyzja) Czy wchodzimy w program **CERT Polska**? Stawki i pula
   identyczne jak NASK, a `hack.cert.pl`/`mwdb.cert.pl` są w jego Tier 1 (§5 regulaminu CERT —
   sprawdzone w pełnym PDF). **Ale**: regulamin *usługi* `moje.cert.pl` IV §4.2 zakazuje
   testowania zabezpieczeń ⇒ najpierw pisemne wyjaśnienie organizatora (ustalenie `a450b00f`).

## L1 — `zglos-dezinformacje.nask.pl` / `POST /api/sendForm` (najwyższa wartość, Tier 1)

Wymaga **przeglądarki usera + jawnego GO** (żądanie zapisujące: tworzy prawdziwe zgłoszenie
u operatora rządowego; reCAPTCHA v3 nie przechodzi automatem — `executeRecaptcha is not ready`).

Kontrakt (z bundle'a, `7911f950` run003): `multipart/form-data`, pola `accept` (wymagane,
niepuste), `email`, `file` (klient: `image/png`, `image/jpeg`, ≤ 20 MB), `reason` ≤ 250 znaków,
`urls` (wymagane, **do 50 linków, po jednym w linii**), `g-recaptcha-response`.

Kolejność prób (każda = jedno zgłoszenie testowe, własne dane, własny kontroler):

| krok | co wysyłamy | co obserwujemy | klasa §8 / stawka |
|---|---|---|---|
| 1.1 | w `urls` **jeden** link do własnego kontrolera (np. własny serwer z logiem; nie cudzy webhook) | czy serwer **pobiera** link: żądanie GET z jego IP/UA + **odczyt** treści. Sam DNS nie wystarcza — **blind SSRF jest wykluczony** | SSRF z odczytem: 4 000 → 9 000 zł |
| 1.2 | jeśli 1.1 dało odczyt: ten sam test z celem wewnętrznym **własnym** (nie `169.254.169.254` na cudzej infrastrukturze bez zgody — najpierw pytamy organizatora) | czy czyta metadane/usługi wewnętrzne | jw., wyżej |
| 1.3 | `file` = **własny** plik `.png` z dopisanym payloadem / podwójne rozszerzenie / `image/svg+xml` z `<script>` | czy walidacja puszcza; czy plik jest serwowany z tej samej domeny i czy wykonuje się w panelu | obejście walidacji uploadu + stored XSS w kontekście **moderatora**: 4 000 → 9 000 zł |
| 1.4 | `reason`/`urls` z `<i>test</i>` (nieszkodliwy znacznik) | czy treść wraca niezeskapowana w panelu analityka | HTML injection sam w sobie jest wykluczony; XSS z wykonaniem — nie |
| 1.5 | pola dodatkowe przy wysyłce (`role`, `is_admin`, `status`, `assignedTo`) przez DevTools | czy odpowiedź/zapis przyjmuje pola spoza UI | mass assignment / eskalacja: 4 000 → 9 000 zł |

**Dyscyplina**: jedno zgłoszenie = jedna hipoteza; nie wysyłamy niczego, czego nie potrafimy
odtworzyć zrzutem ekranu i dokładnymi krokami; nie zgłaszamy komunikatów błędów (500 na obcych
ścieżkach to App Router, klasa wykluczona).

## L2 — `science.nask.pl /api/media/` (prowadzę ja, Actions)

Stan po run1+run2: **dekodowanie `%2e` jest** (A03: sha256 identyczny z kontrolą),
**ucieczki z katalogu mediów nie ma** (0 plików spoza `wp-content`), `%2e%2e` z literalnym `/`
daje 200 o skrócie identycznym z kontrolą (G02), a próba ucieczki kończy się **`400 Bad Request`
z nginx** (G04) ⇒ blokuje brzeg. RAWPATH-003 rozstrzyga, czy G02 to normalizacja nginx
(prawdopodobne) czy drugi przebieg dekodera w aplikacji, i testuje ucieczkę do `robots.txt`
korzenia oraz `/etc/hostname` (cele nieszkodliwe).

**Reguła eskalacji**: jeśli którakolwiek próba zwróci plik spoza poddrzewa mediów —
**przerywamy enumerację** (jeden dowód wystarczy), nie używamy znalezionych danych,
przygotowuję zgłoszenie z PoC i daję userowi do wysłania. Jeśli nie — wpis dostaje status
„zamknięty negatywnie" i nie wracamy do niego.

## L3 — `116sos.pl` (host żyje od rana; prowadzę ja)

Zamknięte w run2: `/api/fetch-cookie-hash` = **wartość stała** (`6a9963b75ab63` w 3 próbkach,
przy nowym ciastku `stickounet` za każdym razem) ⇒ brak wpływu; `/api/announcements` = publiczne
newsy; `/api/og-image` = statyczny JPEG; `/api/centres-search` = katalog placówek (28 kluczy,
dane instytucjonalne: adres/telefon/email/strona/godziny).

**Zadanie dla usera (2 minuty, rozstrzyga resztę)**: porównać liczbę placówek w publicznej
wyszukiwarce na `116sos.pl` z `totalItems` z `/api/centres-search`. Jeśli API oddaje więcej niż
UI (np. placówki niepubliczne, dane osobowe opiekunów) — to jest klasa 3 (dostęp do danych
wrażliwych, Tier 2 do 10 000 zł). Jeśli tyle samo — zamykamy jako publiczne z definicji.

## L4 — HIVE `dataannotation.pllum.org.pl` (po koncie od organizatora)

Trasy z bundle'a (mapa funkcji, nie dowód): `/admin`, `/admin/logs`, `/annotators`, `/account`,
`/forgot-password`, `/basic-info`, `/conversation`, `/projects`, `/edit`; API
`https://dataannotation.pllum.org.pl/api/v1`; backend FastAPI; SPA React Router/TanStack
(catch-all 713 B — każde porównanie wymaga odejmowania wzorca).

| krok | co | kryterium znaleziska |
|---|---|---|
| 4.1 | dwa konta A i B; canary: własny obiekt o znanej, unikalnej treści | odczyt canary z sesji B = IDOR (2 000 → 4 500 zł) |
| 4.2 | `id ± 1..5` **wyłącznie wokół własnych zasobów**, bez iteracji po całej przestrzeni | odpowiedź z danymi cudzymi = dowód; zbieranie cudzych danych jest zakazane |
| 4.3 | `/admin`, `/admin/logs` z sesji zwykłego użytkownika (guardy są po stronie klienta — `5ed750ef`) | 200 z treścią administracyjną = BAC (4 500 → 10 000 zł) |
| 4.4 | mass assignment na **własnym** profilu (`role`, `is_admin`, `approved`, `verified`) | pole zapisane i użyte = eskalacja |
| 4.5 | przepływ `/forgot-password`: token w URL, jego entropia, wielokrotne użycie, brak wygaśnięcia | przejęcie konta = klasa 2.1 (krytyczna) |

## L5 — mapa API z bundli (ja, offline)

`bundle_scan.py` (6/6 testów) na: `zglos-dezinformacje` (13+ chunków flight-data — logika siedzi
w chunkach lazy, nie w głównym HTML), `dyzurnet` (app-router), `dns.pl` (Drupal, `domain-browser`
— routing po parametrze), `116sos`/`science` (`_next/data` po buildId `8CjJwbyxpVqpWnorny23T`,
`Grl_YQ5SCHd1ahmhesPv6`). Wynik = lista endpointów + formatów ID + kandydatur na IDOR,
**bez wysyłania żądań** (potem jedna sonda celowana na endpoint, nie sweep).

Uwaga z run1: na `dns.pl` każde porównanie bajtowe musi najpierw znormalizować
`_event_transid` i odbicie ścieżki w kotwicach — inaczej generuje fałszywe trafienia w nieskończoność.

---

## Czego NIE robimy (zmierzone i zamknięte — lista antyduplikacyjna)

`oad/podglad-pdf` (martwe) · `bezpiecznymiesiac/download-file` (20 wariantów, filtr dekoduje przed
sprawdzeniem) · `science/downloadFile` enum (60 ID, same publiczne) · `/_next/image` SSRF (6–7 hostów)
· CORS (brak odbicia `Origin`) · CVE-2025-29927 (negatyw na 4 hostach) · SQLi przez GET (WAF zrywa)
· `.env`/`.git`/backupy (2 niezależne przebiegi: 0 kandydatów; 200-ki na `dns.pl` to strona główna)
· sourcemapy (0 z 47 bundli) · refleksje w wyszukiwarkach · takeover subdomeny bez PoC ·
DoS/testy obciążeniowe (**dyskwalifikacja**) · hosty spoza §5 (`www.nask.pl`, `panel.dns.pl`,
`info-trace.116sos.pl`, `*.snkom.nask.pl`) · Władysławowo (polecenie usera) ·
zgłaszanie komunikatów błędów/brak nagłówków/wersji (wykluczone §8).

## Tempo i koordynacja (6 sesji na tych samych hostach)

Mój limit: **1,0 req/s**, sekwencyjnie, jedna grupa `concurrency`, wpis do rejestru **przed** testem.
Regulamin dopuszcza 5 req/s dla narzędzi automatycznych, ale sposób sumowania między sesjami nie
jest jednoznaczny, a `incydent.cert.pl` już oddał **429** sesji Gemma-A. Każde żądanie jest
audytowalne w `nask/reports/rawpath-*.json` (status, typ, rozmiar, sha256, czas, błąd).
