# Raport nocy 2026-11-03/04 — 256 sond, 0 potwierdzonych podatności

Praca nocna: sześć przebiegów, **256 sond**, wszystko **GET, read-only, bez POST,
bez zakładania kont, wyłącznie hosty z §5** programu NASK (edycja 11/2026).
Tempo 3 req/s przy limicie 5. Każda odpowiedź odejmowana od **catch-all**
(catch-all = kontrolna odpowiedź na losowy, nieistniejący adres) tego hosta.

**Wynik: nie znalazłem podatności.** Poniżej co dokładnie sprawdziłem, dlaczego
to jest zamknięte, i co pozostaje — bo to drugie jest ważniejsze.

---

## 1. Przebiegi

| run | sond | co | wynik |
|---|---:|---|---|
| 003 | 479 | mapa 12 hostów, 6 ścieżek + assety | mapa; brak podatności |
| 004b | 28 | `download-file` traversal/SSRF, API dns/116sos | 0 |
| 005 | 34 | `/_next/image` SSRF, CORS, zakodowany schemat | 0 |
| 006 | 34 | to samo z podążaniem za 308 | 0 |
| 007 | 86 | macierz 10 hostów × 8 (`.env`, `.git`, backupy) | 0 |
| 009 | 54 | Wagtail `/api/v2/*` × 7 hostów + refleksje XSS | 0 |
| 010 | 20 | Drupal `?_format=json`, WP `?rest_route=`, Nuxt `_draft`, Next `/_next/data` | 0 |

## 2. Co jest ZAMKNIĘTE (i dowód)

**`bezpiecznymiesiac.pl/download-file?fileUrl=`** — endpoint czyta pliki z dysku
(kontrola: prawdziwy PDF, 603 523 B, `application/pdf`). 20 wariantów:
`../../../../etc/passwd`, `%2e%2e%2f`, `..%2f`, `%252e%252e%252f`, `....//`,
`..%5c` (Windows), `file:///`, `/media/./../../`, `https://…`, `//host/…`,
`http%3A%2F%2F`, `https:%2F%2F`, `HTTPS://`, `/proc/self/environ`,
`/media/../../../../`. **Wszystkie 400 lub 404.** Filtr dekoduje wartość przed
sprawdzeniem i odrzuca schematy oraz `..` niezależnie od kodowania.

**`/_next/image?url=`** (SSRF w optymalizatorze Next.js) — 7 hostów:
`oad`, `zglos` → 403 (blokada brzegowa); `dyzurnet` → 404 (brak trasy);
`science` → 400; `bezpiecznymiesiac` → 308 → `/_next/image/` → **400
„Nieprawidłowe żądanie obrazu"**; `116sos` → 502. Na jedynym hoście, gdzie
optymalizator istnieje, zdalny URL jest **odrzucany** — `remotePatterns`
ograniczone. To poprawna konfiguracja.

**CORS** — `Origin: https://evil.example` na 9 endpointach. **Żaden** nie
zwrócił `Access-Control-Allow-Origin` równego wysłanemu Origin. Jedyny
`Access-Control-Allow-Credentials: true` (HIVE) występuje **bez** `ACAO`, czyli
jest bezużyteczny.

**Pliki konfiguracyjne i backupy** — 10 hostów × 8 ścieżek: `.env`, `.env.local`,
`.git/config`, `.git/HEAD`, `wp-config.php.bak`, `backup.zip`, `db.sql`,
`server-status`. **Zero trafień.**

**Wagtail API** — `/api/v2/`, `/api/v2/pages/`, `/documents/`, `/images/`,
`/admin/`, `/search/?q=test` na 7 hostach → 308 → **404**. API niewystawione.

**Drupal (`dns.pl`)** — `/user/login`, `/user/register`, `/user/password`,
`/node/1?_format=json`, `?_format=hal_json`, `/core/install.php`,
`/jsonapi/node/page` → **404**. JSON:API wyłączone, rejestracja zamknięta.

**WordPress (`science`, `116sos`)** — obejście blokady `/wp-json` przez
`?rest_route=/wp/v2/posts` zwraca **HTML strony** (162 KB / 103 KB), nie JSON.
`xmlrpc.php`, `wp-login.php` → 404.

**Nuxt (`pllum`)** — `/api/_content/query?_draft=true` zwraca ten sam publiczny
zestaw (`_draft: false`), `?where={"$draft":true}` → `[]`. Wersje robocze
**nie są** wystawione.

**Next.js `/_next/data`** — działa na `116sos` (8 256 B, `application/json`),
ale to `pageProps` **publicznej** strony (teksty, tooltipy). Na `science` → 404,
na `bezpiecznewybory` → 403 (WAF).

**XSS** — jedyna refleksja markera: `bezpiecznymiesiac.pl/?s=…` trafia do
payloadu **RSC Next.js jako zescapowany string JSON** (`"q":"?s=zzqx9…"`).
To nie jest wykonanie kodu; regulamin wyklucza content injection bez JS.
Na `dns.pl`, `science`, `116sos`, `pllum`, `oad`, `zglos`, `dyzurnet` marker
**nie wystąpił** w treści.

## 3. Błędy własnego narzędzia, które znalazłem po drodze

Warto je zapisać, bo każdy generował fałszywe trafienia:

1. `dns.pl` dokleja do **każdej** odpowiedzi unikalny `_event_transid` → hash
   dwóch identycznych stron 404 nigdy się nie zgadzał i **wszystko** przechodziło
   jako „inne niż baseline". Naprawa: `normalize()` (ciągi cyfr → `#`) po obu
   stronach porównania.
2. Pierwsza wersja `normalize()` miała błąd priorytetu operatorów
   (`a || b && c && d`) — przepuszczała litery. Przepisana.
3. Biblioteka HTTP **normalizuje `../` w ścieżce przed wysłaniem**. Dowód z logu:
   `https://science.nask.pl/api/media/../../../etc/passwd` wyszło jako
   `https://science.nask.pl/etc/passwd`. Trawersal w ścieżce jest **niemierzalny**
   tym klientem — dlatego powstały sondy z `..%2f`. Równoległa sesja
   (`arena/c87f7a48-pokemon`) robi to samo przez surowe gniazdo.

## 4. Czego NIE sprawdziłem — i dlaczego to nie jest „czyste"

- **`secure.edu.pl`** — brak odpowiedzi transportowej (DNS/HTTPS).
- **`bezpiecznewybory.pl`** — WAF blokuje 403 na wszystko, także `/_next/data`.
- **`dataannotation.pllum.org.pl` (HIVE)** — dostęp **zaproszeniowy**
  (potwierdzone przez użytkownika: trzeba być członkiem organizacji).
  Rejestracja publiczna nie istnieje, więc IDOR/BAC **nie jest dla nas dostępny**.
- **`zglos-dezinformacje` — POST `/api/sendForm`** — nie wysłany. Tworzy
  **prawdziwe zgłoszenie** w NASK, a klient wymaga reCAPTCHA v3. To zmiana stanu
  po stronie organizacji i wymaga zgody użytkownika oraz jego przeglądarki.
- **Ścieżki paneli zgadywane słownikiem** — nie robiłem. Regulamin wprost
  wyklucza raporty ze skanerów bez ręcznego potwierdzenia, a to jest ten przypadek.

## 5. Uczciwa ocena

Po 256 sondach obraz jest spójny: **publiczna powierzchnia NASK jest utwardzona
na klasy dostępne bez kont** — trawersal, SSRF przez proxy i optymalizator,
CORS, pliki konfiguracyjne, API CMS, refleksje. To nie znaczy „nie ma luk".
Znaczy, że **te klasy zostały sprawdzone** w miejscach, gdzie dane wskazywały
parametr sterujący ścieżką lub URL-em.

Realne szanse na nagrodę wymagają rzeczy, których nie mam:
1. **Konta w aplikacji z logowaniem** — HIVE odpada (zaproszenia). Zostaje
   ewentualnie konto w innym serwisie z rejestracją otwartą — żadnego takiego
   nie znalazłem w zakresie.
2. **Przeglądarki i zgody na wysłanie formularza** — hipoteza SSRF przez pole
   `urls` (50 linków) jest testowalna **tylko** w ten sposób, plus webhook.site
   jako serwer-kontroli.
3. **Czasu** — zostało 26 dni edycji; publiczna powierzchnia jest już
   przebadana, więc dalsze sondowanie bez kont ma malejący zwrot.

**Nie mam dowodu podatności i nie nazwę tego sukcesem.** Mam za to mapę,
narzędzie i listę dead-endów, która oszczędza dni kolejnej osobie.
