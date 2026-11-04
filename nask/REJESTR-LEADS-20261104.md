# Rejestr leadów + log żądań (noc 3/4.11.2026) — dowód zgodności

**Zasada rejestru:** lead żyje tylko z nazwaną klasą z regulaminu i planem PoC na własnych
kontach. Wszystko, co poniżej oznaczone WYKLUCZONE, **nie idzie do zgłoszenia** (regulamin §8).
**Brak w tym pliku działających payloadów do czegokolwiek pozytywnego — bo pozytywnych nie ma.**

> **STAN WYPŁACALNOŚCI (04.11.2026, ~11:40): 0 potwierdzonych podatności. Nie ma czego
> zgłaszać na `hack.cert.pl`.** Bilans: 321 żądań GET moich + ~2 800 żądań 6 sesji ⇒ zero
> wyników spełniających próg PoC; 19 znalezisk zespołu koordynatora sklasyfikowanych jako
> `severity: none` / `accepted: false`. Otwarte leady L13/L20/L9 to **hipotezy wymagające
> 10 s–2 min pracy usera w przeglądarce**, nie znalezione luki.

## Log żądań wysłanych w nocy (wszystkie: GET, bez uwierzytelnienia, sekwencyjne ≪ 5 req/s, tylko §5)

| # | żądanie | wynik | wniosek |
|---:|---|---|---|
| 1 | `zglos-dezinformacje.nask.pl/` | 200 | formularz: e-mail opcjonalny, ≤50 linków, 250 znaków, **załącznik .png/.jpg ≤20 MB** (powierzchnia klasy 7) |
| 2 | `dataannotation.pllum.org.pl/` | 302→`/login` | HIVE = SPA z logowaniem; publiczne: login + forgot-password |
| 3 | `dyzurnet.pl/` | 200 | CMS publiczny; media `/media/2026/…` (listingi WYKLUCZONE) |
| 4 | `dataannotation.pllum.org.pl/forgot-password` | 200 | formularz resetu (klasa 2 do testu rano na własnym koncie) |
| 5 | `dns.pl/` | 200 | Drupal; whois publiczny z definicji; `sites/default/files/` publiczne |
| 6 | `oad.nask.pl/` | 200 | **odkrycie powierzchni:** `/podglad-pdf?url=<ścieżka>` przy każdej publikacji |
| 7 | `science.nask.pl/wp-json/` | 404 | WP REST niewystawione (Next shell) → martwe |
| 8 | `oad.nask.pl/podglad-pdf?url=<legalny PDF z /media/>` | 200 | powłoka viewera „Ładowanie PDF…" |
| 9 | `oad.nask.pl/podglad-pdf?url=/media/…/nie_istnieje.pdf` | 200 | walidacja **tylko prefiksu** `/media/`, pobranie leniwe/klienckie |
| 10 | `oad.nask.pl/podglad-pdf?url=/etc/passwd` | **500** | poza prefiksem = nieobsłużony wyjątek, **bez danych** |
| 11 | `oad.nask.pl/podglad-pdf?url=http://169.254.169.254/metadata/…` | **500** | **brak odczytu SSRF** (metadata nie wraca) |
| 12 | `oad.nask.pl/podglad-pdf?url=https://example.com/x.pdf` | **500** | brak fetcha zewnętrznego po stronie serwera |

**Suma: 12 żądań, 0 zmian stanu, 0 hostów spoza §5, 0 payloadów niszczących.**

## Leady

| id | cel | klasa regulaminu | status | plan |
|---|---|---|---|---|
| L1 | HIVE | 9.1–9.3, 12.1–12.2, 13 | **ZABLOKOWANY (04.11)** — brak publicznej rejestracji: `/register`, `/api/v1/register` → 404 w 2 kanałach; `/api/v1/projects/` → 401; `/api/v1/users/1` → 405 | runbook rev 3 **L4**; wymaga konta od organizatora (wniosek = L0 pkt 2) |
| L2 | HIVE reset | 2.1–2.3 | **ZABLOKOWANY (04.11)** — jw., bez konta nie ma przepływu do zbadania | runbook rev 3 L4 krok 4.5 |
| L3 | zglos-dezinformacje | 7 (upload ze skutkiem), 5 (SSRF **z odczytem**) | **ODRADZONY (04.11, korekta #41)** — pełny test tworzy fałszywe zgłoszenie dezinformacji u operatora rządowego; zastąpiony przez **L23** (wariant bez tworzenia rekordu) | runbook rev 3 **L1** (przeglądarka usera + jawne GO); korekta #31: dowodem jest żądanie do własnego kontrolera **z odczytem**, nie tylko refleksja w UI |
| L4 | 116sos / science / dyzurnet | 3.1/3.3, 12.2 | **CZĘŚCIOWO ZAMKNIĘTY (04.11)**: `116sos/api/{fetch-cookie-hash,announcements,og-image,centres-search}` = negatywy/dane publiczne (run2); `science/api/media` = zamknięty (run1+2+3, 22 próby); `science/wp-json` = 404 | zostało: porównanie `totalItems` z UI 116sos (2 min usera) |
| L5 | dns.pl | 3.3 / 12.2 | **AKTYWNY (niski)**; uwaga: host oddaje stronę główną z kodem 200 na obce ścieżki + `_event_transid` (korekta #32) ⇒ bez normalizacji każde porównanie jest fałszywe | runbook rev 3 L5 (mapa z bundli Drupal `domain-browser`) |
| L6 | oad `/podglad-pdf` | 5 / 15 | **MARTWY (dowód: wiersze 8–12 logu)**; uzupełnione 04.11: na tym brzegu 500 nie niesie informacji (App Router daje 500 na każdą obcą ścieżkę) | nie testować ponownie |
| L7 | `science.nask.pl/api/media/` traversal | 15 (path traversal/LFI) | **ZAMKNIĘTY NEGATYWNY z MECHANIZMEM (04.11, run1+2+3+8)** — allow-lista katalogów i typów + normalizacja nginx (szczegóły: L21) — `%2e` normalizuje nginx; aplikacja nie dekoduje drugi raz (`%252e%252e` → 404); ucieczka = `RemoteDisconnected`/nginx 400/404 aplikacji; **0 plików spoza `wp-content`** | nie wracać; dowód w `reports/rawpath-00{1,2,3}-run*.json` |
| L8 | `116sos.pl/api/fetch-cookie-hash` | 3 | **ZAMKNIĘTY NEGATYWNY (04.11)** — wartość stała `6a9963b75ab63` w 3 próbkach przy nowym ciastku `stickounet` za każdym razem; brak wpływu (informacja bez danych wrażliwych = wykluczone) | nie wracać |
| L9 | `116sos.pl/api/centres-search` | 3.1/3.3 | **AKTYWNY (2 min pracy usera)** — 28 kluczy, dane instytucjonalne placówek; jeśli API oddaje więcej niż publiczne UI (placówki niepubliczne / dane opiekunów) → klasa 3, Tier 2 do 10 000 zł | porównać `totalItems` z wyszukiwarką na `116sos.pl` |
| L10 | `www.nask.pl` (apex `nask.pl` → 302) | — | **BLOKADA FORMALNA** — apex daje 302 na `www` w 8/8 żądań (run007), a §5 wymienia literał `nask.pl` bez `*` ⇒ cały Tier-1 host praktycznie nietestowalny | pytanie do organizatora (L0 pkt 3) |
| L11 | `info-trace.116sos.pl` | — | **POZA §5** — subdomena ujawniona w nagłówku `Access-Control-Allow-Origin` (run1, `sos-D01/D02/D03`); nie testuję bez interpretacji organizatora | to samo pytanie co L10 |
| L13 | `oad.nask.pl` — embed PowerBI | 3 (dostęp do danych wrażliwych) | **AKTYWNY — 2 minuty usera, najwyższy stosunek wartości do pracy** | otworzyć w incognito `oad.nask.pl/trendy` albo sam embed: `https://app.powerbi.com/reportEmbed?reportId=470044cf-1a84-4ecb-87f1-7e914afdbb19&autoAuth=true&ctid=95dc45af-07b0-4179-a598-9740073a6e4a` (URL wydobyty z `oad.nask.pl/_next/static/chunks/41lk95l8op7nz.js` w `analysis-run003.json` 7911f950). Agregaty → zamykamy; rekordy/dane osobowe bez logowania → klasa 3, Tier 1 (9 000/20 000 zł). **`app.powerbi.com` nietestowane automatem** (własność Microsoftu, poza §5) |
| L14 | `bezpiecznymiesiac.pl/ecsm/zglos-inicjatywe/` | 7 (upload), 13 (mass assignment), 8 (stored XSS) | **AKTYWNY — wymaga GO** (żądanie zapisujące, Tier 2) | formularz z pola `forms` w `analysis-run003.json`: `name`, `description`, …; ta sama klasa co sendForm, mniejsza konkurencja |
| L15 | `science.nask.pl/contact` | 7/8 | **AKTYWNY (niski)** — wymaga GO | pola `name`, `email`, …; prawdopodobnie tylko wysyła maila |
| L16 | `116sos.pl/otrzymaj-pomoc/formularz` | — | **WYKLUCZONE DECYZJĄ WŁASNĄ — NIE TESTUJEMY NIGDY** | formularz „otrzymaj pomoc" przy telefonie zaufania dla dzieci/młodzieży w kryzysie: testowe zgłoszenie może uruchomić realną procedurę pomocową i zająć zasób potrzebujący. Regulamin tego nie zakazuje wprost — właśnie dlatego wykluczamy (realny, nieodwracalny wpływ na osoby trzecie) |
| L17 | `dns.pl/translations/domainBrowser?locales=pl` (+`delegation`, `domainCount`, `deletedDomainCount`) | 12 | **AKTYWNY (offline)** — pobrane w RAWPATH-004 | tłumaczenia Symfony/Bazinga zawierają nazwy pól i parametrów ⇒ najtańsza droga do ożywienia `/api/domain-browser/` (404 bez właściwego parametru, `5ed750ef` bieg 4/5) |
| L18 | HIVE `assets/index-ClBZuP56.js` = 2,77 MB | 9/10/13 | **AKTYWNY (offline)** — RAWPATH-004 czyta całość (limit 4 MB) | ich analiza wyciągnęła z niego tylko 75 literałów tras (vs 10 005 dla dns.pl) ⇒ mapa API HIVE **nie została wydobyta**; potrzebna w chwili przyznania konta (formaty ID = koszt IDOR-a) |
| L20 | `dns.pl/deleted_domains.txt` | 3 (dane wrażliwe) — **prawdopodobnie wykluczone** | **AKTYWNY — 10 sekund usera**: plik 200/`text/plain`/37 343 B, `cache-control: no-cache, private`. Treści celowo nie pobrałem (`no_preview: true`). Otworzyć w przeglądarce: sama lista nazw domen → dane publiczne rejestru, klasa wykluczona; dane abonenta (imię/nazwisko/email/PESEL) → klasa 3, Tier 1 | otworzyć `https://dns.pl/deleted_domains.txt` i powiedzieć, co widać (bez wklejania treści do czatu) |
| L21 | `science/api/media` — mechanizm | — | **ZAMKNIĘTY z pełnym wyjaśnieniem** | proxy statycznych assetów z allow-listą katalogów (`wp-content/`, `wp-includes/`) i typów (`.php` → 404) za nginx normalizującym `%2e`/`..` przed aplikacją; dowód: `wp-includes/js/jquery/jquery.min.js` → 200 (jQuery 3.7.1, 87 553 B) przy `wp-includes/version.php` → 404 |
| L22 | mining bundli (28 endpointów, 0 sekretów w 10,47 MB) | 1 (poświadczenia) | **ZAMKNIĘTY NEGATYWNIE** (2 niezależne przebiegi: mój 129 plików + `5ed750ef` 47 bundli) | nie wracać; jedyny nieznany kąt = czyste nazwy parametrów `dns.pl/api/*` po filtrze #39 (19 żądań, niska wartość: dane rejestru są publiczne) |
| L23 | `zglos-dezinformacje.nask.pl/api/sendForm` — wariant **bez tworzenia rekordu** | 7/13 (walidacja), 8 | **AKTYWNY — czeka na jawne GO**; 1 próba + 2 kontrole, ≤4 żądania POST. Multipart z brakującym `accept`, pustym `urls`, **bez** `g-recaptcha-response`: mierzy walidację serwerową i egzekwowanie reCAPTCHA, nie tworząc zgłoszenia (o ile aplikacja jest poprawna). **Nie da** klasy 5 (SSRF z odczytem), walidacji uploadu ani stored XSS w panelu — te wymagają realnego rekordu ⇒ patrz korekta #41 | dopisek 04.11 ~11:40, sekcja L23 |
| L17 | `dns.pl/translations/*` | 12 | **ZAMKNIĘTY — hipoteza niepotwierdzona**: to etykiety UI (Bazinga Translator, 1 666 B `application/javascript`), nie nazwy parametrów API | — |
| L19 | `har_triage` (kod `a450b00f@bb17ccdc`) | — (narzędzie) | **DEFEKT ZGŁOSZONY + naprawiony lokalnie** | `normalize_template("/api/tasks/abc123deadbeef")` nie normalizuje (HEX_LONG_RE `{16,}` vs ich test oczekujący `{id}`) → 1/11 testów FAIL na ich HEAD. U mnie: vendored + 1 udokumentowana poprawka (`{12,}`) → 11/11 OK. `nask/tools/vendor/a450b00f/PROWENIENCJA.md` |
| L12 | mapy API z bundli (zglos flight-data 13+ chunków, dyzurnet app-router, dns.pl Drupal) | 9/12 | **AKTYWNY (ja, offline)** — bez wysyłania żądań; potem jedna sonda celowana na endpoint, nie sweep | `bundle_scan.py` + runbook rev 3 L5 |

## Wprost WYKLUCZONE z nagród (nie zgłaszamy, żeby nie palić reputacji zgłoszeń)

brak nagłówków/HSTS/captchy/flag cookie · mixed content · SPF/DKIM/DMARC bez spoofingu ·
TLS bez scenariusza · wersje/ścieżki/IP/stack trace/listingi katalogów · user enumeration ·
autocomplete · publiczne endpointy debug bez eskalacji · CVE bez PoC · MITM/fizyczny/DevTools ·
self-XSS · tabnabbing · clickjacking bez krytycznej akcji · czysty HTML injection ·
CSRF bez wpływu na stan · **blind SSRF z samym DNS** · open redirect bez scenariusza ·
DoS i testy obciążeniowe (**dyskwalifikacja**) · brak rate-limitu bez scenariusza ·
subdomain takeover bez PoC · błędy UX/literówki · **raporty z samych skanerów**.

## Kalibracja (podtrzymana)

typowo 600–4 000 zł · IDOR z realnym odczytem = 9 000 zł · masowy odczyt/przejęcie = 20 000 zł ·
ta sama przyczyna na dwóch hostach = **jedna** nagroda · duplikat = zero · wysyłka natychmiast po PoC.

---

# DOPISEK 04.11 (dzień) — log żądań i rozstrzygnięcia po przeglądzie 6 gałęzi

Źródła: `PRZEGLAD-GALEZI-20261104.md` (przegląd + dowody), `RUNBOOK-REV3-20261104.md` (nowa
kolejność), `reports/rawpath-00{1,2,3}-run*.json` (rekordy wszystkich żądań).

## Log żądań 04.11 (łącznie 59 do celów w 4 przebiegach + 5 przez `fetch_page` + 2 `curl` zablokowane w sandboxie)

| kanał | przebieg | żądania | tempo | hosty | wynik |
|---|---|---:|---|---|---|
| `curl` (sandbox) | test kanału | 2 (kod `000` — TCP zablokowane, nie wyszły) | — | `science.nask.pl`, `dns.pl` | potwierdzenie: sandbox nie ma wyjścia do celów, `github.com` = 200 |
| `fetch_page` | rozstrzygnięcia treści | 5 | sekwencyjnie ≪ 5 req/s | `dns.pl`, `dyzurnet.pl`, `zglos-dezinformacje.nask.pl`, `science.nask.pl` ×2 | `dns.pl/.env` = strona główna Drupal; `dyzurnet/server-status` = „Nie znaleziono strony"; `zglos/server-status` = „Ups! … 404" |
| Actions `41814163117` | RAWPATH-001 | 35 | 1,0 req/s (min. odstęp 1,000 s), 70,13 s | science, dns, dyzurnet, zglos, dataannotation, bezpiecznymiesiac, 116sos | **0 kandydatów**; 3 grupy identycznych ciał (dowody) |
| Actions `41814928560` | RAWPATH-002 | 10 | 1,0 req/s, 10,94 s | 116sos, science | **0 kandydatów**; `cookieHash` stały; `license.txt` = 404 (timeout z run1 przejściowy); 400 = **nginx** |
| Actions (run 3) | RAWPATH-003 | 7 | 1,0 req/s, 7,28 s | science | `%252e%252e` → **404** (aplikacja nie dekoduje 2×); ucieczki → `RemoteDisconnected`; H06 → 404 aplikacji |
| Actions `41816135053` (run 4) | RAWPATH-003 — **reprodukcja** | 7 | 1,0 req/s, 6,55 s | science | **identyczne statusy/rozmiary/sha256 w 7/7**; jedyna różnica = etykieta `/robots.txt` po korekcie #30. Wynik negatywny odtwarzalny |

**Zero POST/PUT/DELETE · zero hostów spoza §5 · zero zmian stanu · zero użycia znalezionych
poświadczeń · zero zgłoszeń (nic nie spełnia progu PoC) · Władysławowo i inne programy nietknięte.**
Każde żądanie — także błąd transportu — ma rekord: status, `Content-Type`, rozmiar, sha256, czas,
znaczniki treści (nazwy, nie fragmenty), `Set-Cookie` tylko jako nazwy. Dla ścieżek wrażliwych
(`wp-config.php`) zapisywane są wyłącznie metadane; małe ciała błędów (≤ 1024 B, status ≥ 400) tak.

## Co zamknąłem dziś dowodem (nie wracamy)

1. **23 „interesting" z `7911f950` run007 = szum.** `dns.pl/.env`, `/.git/config`, `/db.sql`,
   `/server-status` → 200 `text/html` ~51,2 kB = strona główna Drupal z wstrzykniętym
   `_event_transid` (licznik rośnie: …175/176/177/178) i odbitą ścieżką w kotwicach; kontrola `/`
   = 51 142 B bez skryptu. `dyzurnet/server-status` → soft-404 (`SOFT404_PL`×8).
   `zglos/server-status` → soft-404 (`SOFT404_PL`×4). `dataannotation/.env` → sha256 **identyczny**
   z `/` (713 B shell SPA).
2. **`science.nask.pl/api/media/`** — 22 próby, 3 przebiegi, mechanizm opisany w przeglądzie §6.4:
   dekoduje i normalizuje **nginx**, aplikacja nie dekoduje drugi raz, ucieczka blokowana
   (reset / nginx 400 / 404 aplikacji), **0 plików spoza `wp-content`**. Trop zamknięty.
3. **`116sos.pl/api/fetch-cookie-hash`** — wartość stała w 3 próbkach ⇒ brak wpływu (lead H14
   zespołu `5ed750ef` zamknięty jako negatyw).
4. **`116sos.pl/api/announcements`, `/api/og-image`** — publiczne newsy (603 B) i statyczny JPEG
   (16 264 B). Host żyje (502 od 23:00 minęło).
5. **HIVE** — potwierdzone drugim kanałem dokładnie te same ciała co u Gemmy-B: 405
   `{"detail":"Method Not Allowed"}`, 401 `{"detail":"Not authenticated"}`, 404
   `{"detail":"Not Found"}` ×2 (identyczny sha `37ec4665…`). Kontrola na poziomie routera działa,
   rejestracji brak ⇒ L1/L2 czekają na konto od organizatora.
6. **`science.nask.pl/api/downloadFile`** — kontrakt potwierdzony: `?fileId=18864` → 200
   `image/png` (z metadanymi C2PA), `?fileId=-1` → 400 `{"error":"Invalid file id"}`.
7. **`bezpiecznymiesiac.pl/download-file/`** — kontrola dodatnia klasyfikatora: 200
   `application/pdf`, `%PDF-1.7`, `/Linearized 1/L 603523/` (publiczny poradnik NASK).

## Co zostało otwarte (i kto to robi)

| lead | co | kto |
|---|---|---|
| **L13** | `oad.nask.pl` — embed PowerBI: agregaty → zamykamy; rekordy/dane osobowe bez logowania → klasa 3, Tier 1 (9 000/20 000 zł). **Najwyższy stosunek wartości do pracy w całym rejestrze** | **user, 2 min w incognito** |
| **L20** | `dns.pl/deleted_domains.txt` (200/`text/plain`/37 343 B; treści celowo nie pobrałem — `no_preview: true`): same nazwy domen = klasa wykluczona; dane abonenta = klasa 3, Tier 1 | **user, 10 s** |
| **L23** | `sendForm` — **wariant bez tworzenia rekordu** (walidacja serwerowa + egzekwowanie reCAPTCHA). Opis niżej | ja, **wyłącznie po jawnym GO** |
| L3 | `sendForm` — pełny test (SSRF z odczytem, walidacja uploadu, stored XSS w panelu, mass assignment) | **ODRADZAM — tworzy fałszywe zgłoszenie dezinformacji** (patrz korekta #41) |
| L9 | `totalItems` z `/api/centres-search` vs liczba placówek w publicznym UI (`q`/`id` ignorowane ⇒ prawie domknięty) | user, 2 min |
| L14 | `bezpiecznymiesiac.pl/ecsm/zglos-inicjatywe/` (klasa 7/13/8, Tier 2 — ta sama klasa co `sendForm`, mniejsza konkurencja) | user + jawne GO |
| L15 | `science.nask.pl/contact` (7/8, niski — prawdopodobnie tylko wysyła maila) | user + jawne GO |
| L1/L2 | HIVE: IDOR/BAC/mass assignment/reset hasła | po koncie od organizatora (wniosek = L0 pkt 2) |
| L10/L11 | zakres `www.nask.pl` (apex → 302, §5 bez `*`) i `info-trace.116sos.pl` | pytanie do organizatora (L0 pkt 3) |
| L18 | mapa API HIVE z `assets/index-ClBZuP56.js` (2,77 MB, pobrany w RAWPATH-004; ich analiza dała tylko 75 literałów tras) | ja, offline |
| L12 | mapy API z bundli (zglos flight-data, dyzurnet app-router, dns.pl Drupal) | ja, offline |
| L5 | `dns.pl` z normalizacją `_event_transid` (korekta #32) | ja, niski priorytet |
| L16 | `116sos.pl/otrzymaj-pomoc/formularz` | **NIGDY — wykluczone decyzją własną** |

Zamknięte dziś dowodem (szczegóły w tabeli leadów wyżej): L4, L6, L7, L8, L17, L19, L21, L22.

## Log żądań 04.11 — ciąg dalszy (run 6/7/8)

| kanał | przebieg | żądania | tempo | hosty | wynik |
|---|---|---:|---|---|---|
| Actions (run 6) | RAWPATH-004 — **dane utracone przez mój błąd CI** | 129 | 1,0 req/s | 9 hostów §5 (publiczne assety JS) | przebieg/mining/audyt OK, krok commitujący padł ⇒ raport przepadł z workspace runnera (korekta #37) |
| Actions `41821385075` (run 7) | RAWPATH-004 powtórzone | 129 | 1,0 req/s, 216,42 s, min. odstęp 1,000 s | jw. | 121×200, 2×404, 6×timeout; 123 ciała (10,47 MB) w `RUNNER_TEMP`; mining: 108 plików, 28 endpointów, **0 sekretów** |
| Actions (run 8) | RAWPATH-005 | 4 | 1,0 req/s, 3,46 s | `dns.pl`, `science.nask.pl` | `deleted_domains.txt` 200/37 343 B (`no_preview`), translations = etykiety UI, `wp-includes/js/jquery` 200 vs `version.php` 404 ⇒ allow-lista potwierdzona |


**Razem dziś: 59 (fala 1) + 129 (run 6, utracone) + 129 (run 7) + 4 (run 8) = 321 żądań GET**
do celów + 7 przez `fetch_page` + 2 próby `curl` zablokowane w sandboxie. Wszystkie przebiegi:
1,0 req/s (sufit regulaminowy 5, inne sesje 3–4,5), najmniejszy zmierzony odstęp 1,000 s,
GET-only, zero POST/PUT/DELETE, zero hostów spoza §5, zero zmian stanu, zero zgłoszeń.

## Zamknięcia z fali 2 (04.11, 10:14–10:55) — nie wracamy

| co | dowód | kto |
|---|---|---|
| **H10 `/admin/logs` = „guardy tylko klienta"** (wycena 4,5–10k) | **OBALONE**: 200/713 B = **identyczne z catch-all** hosta; `/api/v1/admin/logs` → 404; `/api/v1/users/` → 401 | Gemma-B runda 7 (`e46c9169`) |
| HIVE = dostęp **zaproszeniowy** (nie „brak rejestracji" przejściowy) | potwierdzone przez usera: trzeba być członkiem organizacji | `7911f950` raport nocy §4 |
| `mwdb.cert.pl` XSS Rich attributes | `server_version` = **2.20.0** ⇒ poprawka #1272/#1274 wdrożona (program CERT, nie NASK) | Gemma-A przebieg 4 + Drive 15 |
| `centres-search` filtrowanie | `q` i `id` **ignorowane** (13 306 B zawsze) ⇒ „testy SQLi na `q`" mierzyły szum; L9 prawie domknięty | Gemma-B runda 7 |
| `pllum` Nuxt drafts | `_draft=true` → `200, 2 B = []` | Gemma-B + `7911f950` run010 |
| Wagtail `/api/v2/*` | × 7 hostów → 308 → 404 (API niewystawione) | `7911f950` run009 |
| Drupal `dns.pl` | `?_format=json`/`hal_json`, `/jsonapi/node/page`, `/user/login`, **`/user/register`**, `/core/install.php` → 404 | `7911f950` run010 |
| WordPress `science`/`116sos` | `?rest_route=/wp/v2/posts` → **HTML** (162/103 kB), `xmlrpc.php`, `wp-login.php` → 404 | `7911f950` run010 |
| `/_next/data` | `116sos` → 8 256 B `application/json`, ale `pageProps` **publicznej** strony; `science` → 404; `bezpiecznewybory` → 403 | `7911f950` run010 |
| XSS refleksyjny | jedyna refleksja `bezpiecznymiesiac/?s=` trafia do payloadu RSC jako **zescapowany string JSON** → wykluczone §8 | `7911f950` run009 |
| `dyzurnet/api` | 404 + 38 981 B (catch-all App Routera) — API nie istnieje pod tą ścieżką | Gemma-B runda 7 |
| cache poisoning przez `X-Forwarded-Host` | brak refleksji na `/api/fetch-cookie-hash` | Gemma-B runda 7 |
| `download-file` prefiks | elastyczny (`%2Fmedia%2F`, `/MEDIA/`, `media/` → **ten sam plik** 540 927 B), ale `.`/`..` → 400 ⇒ nie poszerza dostępu | Gemma-B runda 7 |
| `science/api/media` traversal | **22 próby / 3 przebiegi + reprodukcja 1:1** — `%2e` normalizuje nginx, aplikacja nie dekoduje 2×, ucieczka = reset/nginx 400/404, 0 plików spoza `wp-content` | **ja (c87)**, run1–run4 |
| `116sos/api/fetch-cookie-hash` | wartość **stała** — 3 próbki w jednym przebiegu (ja) + 2 dni/2 żądania bez ciastka (Gemma-B) | dwa kanały |

---

# DOPISEK 04.11 (~11:40) — korekta #41: co dokładnie znaczy „czekam na jawne GO"

Pytanie usera: *„ale co chcesz wysłać? odkryłeś luki w ich zabezpieczeniach, za które dostanę
nagrodę?"* Odpowiedź: **nie**. Moja wcześniejsza formuła była nieprecyzyjna i mogła sugerować,
że mam gotową lukę do zgłoszenia. Rozdzielam dwie rzeczy, które w tamtym zdaniu się zlały.

## 1. Zgłoszenie podatności (bug bounty) — **nie ma czego wysyłać**

Składane przez usera na platformie `hack.cert.pl`, dopiero gdy istnieje potwierdzony PoC.

**Stan: 0 potwierdzonych podatności.** 321 moich żądań GET + ~2 800 żądań 6 sesji ⇒ zero
wyników spełniających próg PoC. Jedyne „znaleziska" zespołu koordynatora (208 żądań) to 19
pozycji z `severity: none` / `accepted: false` — klasy wykluczone przez §8 (brak
`X-Frame-Options`, clickjacking bez akcji krytycznej, `security.txt`, `ACAO: *` bez
poświadczeń). Kalibracja z `17-IDEE-ZAROBEK`: anonimowy skan 26 hostów → 0 raportów.

Wartość, którą realnie wytworzyłem do tej pory, jest **procesowa, nie wypłacalna**:
dowodowe zamknięcie ~15 ślepych tropów (żeby inne sesje nie marnowały żądań), rejestr leadów
z klasami z regulaminu, `rawpath.py` (surowe ścieżki bez normalizacji klienta — 76 testów),
`bundle_scan.py`, `ci_commit.sh`, zwendoryzowany `har_triage` z naprawionym defektem (L19).

## 2. `POST /api/sendForm` — **to nie jest zgłoszenie luki**

To żądanie **testowe** do formularza „zgłoś dezinformację" na `zglos-dezinformacje.nask.pl`
(Tier 1). Skutek udanego żądania = **prawdziwy rekord w systemie operatora rządowego**:
zgłoszenie dezinformacji z listą do 50 URL-i, powodem ≤250 znaków i załącznikiem. Testowanie
go w pełnej formie oznacza więc **wysłanie fałszywego zgłoszenia dezinformacji** — dokładnie
tę samą kategorię, którą przy L16 (formularz „otrzymaj pomoc" telefonu zaufania) wykluczyłem
decyzją własną, i dokładnie to, co `17-IDEE-ZAROBEK` ma na liście zakazanej.

**Dlatego zmieniam rekomendację: L3 w pełnej formie ODRADZAM.** Zastępuję je leadem **L23**.

## L23 — `sendForm`: wariant bez tworzenia rekordu

**Cel:** uzyskać część sygnału z L3 nie tworząc niczego w systemie operatora.

**Żądanie:** `POST https://zglos-dezinformacje.nask.pl/api/sendForm`, ciało multipart
z **brakującym polem wymaganym** (`accept`) i pustym `urls`, **bez** `g-recaptcha-response`.
Kontrakt pochodzi z miningu bundla (`analysis-run003.json`) i **nie był weryfikowany
żądaniem** — stąd brak pewności co do nazw pól.

**Co mierzy:**
- czy walidacja jest **serwerowa**, czy tylko kliencka (200 przy brakującym `accept` =
  dowód, że serwer przyjmuje zgłoszenie bez akceptacji regulaminu i bez captchy → klasa 7/13);
- czy reCAPTCHA v3 jest **egzekwowana po stronie serwera** (żądanie bez tokenu);
- czy odpowiedź 4xx nie ujawnia stack trace / nazw wewnętrznych (korekta #29: na tym brzegu
  **500** nie niesie informacji — tu celowo sprawdzamy 4xx, nie 500);
- czy odpowiedzi różnią się w zależności od brakującego pola (logika biznesowa na wierzchu).

**Czego NIE da (i to jest uczciwa granica tego leadu):** SSRF z odczytem przez własny
kontroler (klasa 5), walidacji uploadu pliku (klasa 7), stored XSS w panelu operatora
(klasa 8). Te trzy wymagają **realnego rekordu** ⇒ pozostają dla nas zamknięte, chyba że
user świadomie zdecyduje inaczej, znając skutek po stronie operatora.

**Koszt i ryzyko:** 1 próba + 2 kontrole, ≤4 żądania POST, 1,0 req/s. Ryzyko: jeśli
aplikacja jest poprawna — rekord **nie powstaje** (odrzucona na walidacji/captchy). Jeśli
jest niepoprawna — powstanie śmieciowy rekord bez URL-i i bez akceptacji. Dlatego:
**wyłącznie po jawnym GO usera**, a wynik (także negatywny) natychmiast do tego rejestru.

## Co realnie ma szansę stać się wypłacalne — i nie wymaga żadnego POST-a

| # | co | koszt usera | warunkowa wycena (tylko JEŚLI hipoteza się potwierdzi) |
|---|---|---|---|
| L13 | `oad.nask.pl/trendy` lub embed PowerBI **w incognito** | 2 min | rekordy/dane osobowe bez logowania → klasa 3, Tier 1: 9 000 / 20 000 zł; agregaty → zamykamy |
| L20 | `dns.pl/deleted_domains.txt` — **tylko jaki to rodzaj danych**, bez wklejania treści | 10 s | dane abonenta → klasa 3, Tier 1; same nazwy domen → wykluczone |
| L9 | `totalItems` z `/api/centres-search` vs publiczna wyszukiwarka 116sos | 2 min | placówki niepubliczne / dane opiekunów → klasa 3, Tier 2: do 10 000 zł (prawdopodobnie zamknięty) |
| L0 | rejestracja na `hack.cert.pl` + **jedno** pytanie do organizatora z 3 wątkami (`www.nask.pl`, konto HIVE, `info-trace.116sos.pl`) | 15 min | nie wyceniam: to **warunek wejścia** do programu i odblokowanie 542 literałów tras `www.nask.pl` oraz HIVE |

Cztery pozycje, łącznie ~20 minut pracy usera, zero żądań zapisujących. To jest obecnie
cała droga do pierwszej nagrody — nie mam innej i nie będę udawał, że mam.
