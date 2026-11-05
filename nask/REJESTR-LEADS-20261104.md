# Rejestr leadów + log żądań (noc 3/4.11.2026) — dowód zgodności

**Zasada rejestru:** lead żyje tylko z nazwaną klasą z regulaminu i planem PoC na własnych
kontach. Wszystko, co poniżej oznaczone WYKLUCZONE, **nie idzie do zgłoszenia** (regulamin §8).
**Brak w tym pliku działających payloadów do czegokolwiek pozytywnego — bo pozytywnych nie ma.**

> **STAN WYPŁACALNOŚCI (05.11.2026, ~13:10): 0 potwierdzonych podatności. Nie ma czego
> zgłaszać na `hack.cert.pl`.** Bilans: **374 żądania GET** moich (321 do 04.11 + 31 w run 9
> + 22 w run 10) + ~2 800 żądań 6 sesji ⇒ zero wyników spełniających próg PoC; 19 znalezisk
> zespołu koordynatora sklasyfikowanych jako `severity: none` / `accepted: false`.
> **Zmiana po run 9/run 10 (`WYNIKI-RUN9-RUN10-20261105.md`): L20 i L9 ZAMKNIĘTE bez pracy
> usera** (liczniki PII z korekty #43 + arytmetyka + domeny instytucji), a **L13 zawężony**
> (trasa `/trendy` = 404 w 3 wariantach, korekta #49) — zostaje wyłącznie 30-sekundowe
> sprawdzenie samego URL-a embedu PowerBI w incognito.

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
| L5 | dns.pl | 3.3 / 12.2 | **ZAMKNIĘTY (05.11, run 9/10)** — mapa API dns.pl dla GET ostateczna: żywe = `/api/zone-stats` (JSON `stats.{time,day,rows}`, 2 757 995 domen) i `/api/count-deleted-domains` (`{"count":"+1467"}`, 17 B), plus `/deleted_domains.txt`; **404** = `/api/stats/`, `/api/who-is-xml/`, `/api/domain-browser/`, `/api/funny-name/`. Dodatkowo odkryty mechanizm brzegowy (L25) | nie wracać; run 11 (`dns-L07`) sprawdza tylko, jak UI `/przegladarka` odpytuje dane (404 w GET ⇒ POST albo captcha) |
| L6 | oad `/podglad-pdf` | 5 / 15 | **MARTWY (dowód: wiersze 8–12 logu)**; uzupełnione 04.11: na tym brzegu 500 nie niesie informacji (App Router daje 500 na każdą obcą ścieżkę) | nie testować ponownie |
| L7 | `science.nask.pl/api/media/` traversal | 15 (path traversal/LFI) | **ZAMKNIĘTY NEGATYWNY z MECHANIZMEM (04.11, run1+2+3+8)** — allow-lista katalogów i typów + normalizacja nginx (szczegóły: L21) — `%2e` normalizuje nginx; aplikacja nie dekoduje drugi raz (`%252e%252e` → 404); ucieczka = `RemoteDisconnected`/nginx 400/404 aplikacji; **0 plików spoza `wp-content`** | nie wracać; dowód w `reports/rawpath-00{1,2,3}-run*.json` |
| L8 | `116sos.pl/api/fetch-cookie-hash` | 3 | **ZAMKNIĘTY NEGATYWNY (04.11)** — wartość stała `6a9963b75ab63` w 3 próbkach przy nowym ciastku `stickounet` za każdym razem; brak wpływu (informacja bez danych wrażliwych = wykluczone) | nie wracać |
| L9 | `116sos.pl/api/centres-search` | 3.1/3.3 | **ZAMKNIĘTY jako dane instytucjonalne (05.11, run 9)** — 200 JSON 13 306 B, **`PII_EMAIL: 10`**, `personal_like` puste, 0 PESEL/telefon/IBAN; mining `hosts` z tej odpowiedzi dał 8 domen **instytucji**: `gops.slawno.ibip.pl`, `mops.krakow.pl`, `jarocin.naszops.pl`, `gopsosieck.pl`, `gopschelmno.naszops.pl`, `kolaki.pl`, `markot.pila.pl`, `www.gops.ugslawno.pl` (GOPS/MOPS = publiczne ośrodki z własnymi stronami i BIP); schemat `centres[]` opisuje **placówkę** (`canSleep`, `open24`, `centreAimedTo`), nie osobę | hipoteza wypłacalna (dane opiekunów/dzieci) MARTWA. Resztka do zdjęcia w 2 min **tylko jeśli user chce**: czy zbiór placówek z API jest równy zbiorowi w publicznej wyszukiwarce (gdyby API oddawało placówki o **niejawnych adresach**, to zmienia postać rzeczy). Run 11 (`sos-L02/L03`) próbuje domknąć to bez usera |
| L10 | `www.nask.pl` (apex `nask.pl` → 302) | — | **BLOKADA FORMALNA** — apex daje 302 na `www` w 8/8 żądań (run007), a §5 wymienia literał `nask.pl` bez `*` ⇒ cały Tier-1 host praktycznie nietestowalny | pytanie do organizatora (L0 pkt 3) |
| L11 | `info-trace.116sos.pl` | — | **POZA §5** — subdomena ujawniona w nagłówku `Access-Control-Allow-Origin` (run1, `sos-D01/D02/D03`); nie testuję bez interpretacji organizatora | to samo pytanie co L10 |
| L13 | `oad.nask.pl` — embed PowerBI | 3 (dostęp do danych wrażliwych) | **AKTYWNY, ale ZAWĘŻONY (05.11, korekta #49)** — `oad.nask.pl/trendy` = **404** (13 814 B), `/en/trendy` = **404** (identyczny sha256 `286f1682796c…`), `/trendy/` = **308** z `location: /trendy`. Chunk z embedem (`41lk95l8op7nz.js`, 34 692 B) jest nadal ładowany przez `/wyniki-wyszukiwania`, więc kod żyje, ale trasy nie ma. Prawdopodobieństwo, że raport jest żywy: **obniżone**, nie wykluczone | **user, 30 s, incognito — TYLKO sam embed** (instrukcja z `oad.nask.pl/trendy` była błędna): `https://app.powerbi.com/reportEmbed?reportId=470044cf-1a84-4ecb-87f1-7e914afdbb19&autoAuth=true&ctid=95dc45af-07b0-4179-a598-9740073a6e4a`. Rekordy/dane osobowe bez logowania → klasa 3, Tier 1 (9 000/20 000 zł); agregaty albo błąd logowania → zamykamy. `app.powerbi.com` = Microsoft, **poza §5** — nigdy automatem |
| L14 | `bezpiecznymiesiac.pl/ecsm/zglos-inicjatywe/` | 7 (upload), 13 (mass assignment), 8 (stored XSS) | **AKTYWNY — wymaga GO** (żądanie zapisujące, Tier 2) | formularz z pola `forms` w `analysis-run003.json`: `name`, `description`, …; ta sama klasa co sendForm, mniejsza konkurencja |
| L15 | `science.nask.pl/contact` | 7/8 | **AKTYWNY (niski)** — wymaga GO | pola `name`, `email`, …; prawdopodobnie tylko wysyła maila |
| L16 | `116sos.pl/otrzymaj-pomoc/formularz` | — | **WYKLUCZONE DECYZJĄ WŁASNĄ — NIE TESTUJEMY NIGDY** | formularz „otrzymaj pomoc" przy telefonie zaufania dla dzieci/młodzieży w kryzysie: testowe zgłoszenie może uruchomić realną procedurę pomocową i zająć zasób potrzebujący. Regulamin tego nie zakazuje wprost — właśnie dlatego wykluczamy (realny, nieodwracalny wpływ na osoby trzecie) |
| L17 | `dns.pl/translations/domainBrowser?locales=pl` (+`delegation`, `domainCount`, `deletedDomainCount`) | 12 | **AKTYWNY (offline)** — pobrane w RAWPATH-004 | tłumaczenia Symfony/Bazinga zawierają nazwy pól i parametrów ⇒ najtańsza droga do ożywienia `/api/domain-browser/` (404 bez właściwego parametru, `5ed750ef` bieg 4/5) |
| L18 | HIVE `assets/index-ClBZuP56.js` = 2,77 MB | 9/10/13 | **ZAMKNIĘTY offline (05.11, run 9)** — bundel 2 770 426 B pobrany w całości i zminowany: **71 literałów tras klienta** (TanStack Router: `/projects/$projectShortName/conversation/$recordId/edit/$editedItem`, `/projects/{create,$x}/edit/{annotators,basic-info,description,interaction-tags,labels,llm-models,samples,system-prompt,system-prompt-tags,tools,tools-tags}`, `/admin/logs`, `/account`, `/register`, `/unauthorized`) oraz **0 literałów API** ⇒ ścieżki API budowane dynamicznie, host API = ten sam | mapa **ekranów** gotowa na chwilę przyznania konta; mapy **API** z bundla nie ma i nie będzie — daje ją wyłącznie HAR z zalogowanej sesji (`vendor/a450b00f/har_triage.py`, 11/11). Run 10 potwierdził brak mapowania 1:1: `/api/v1/projects/test/conversation/1` → **404**, `/api/v1/annotators` → **404** (`{"detail":"Not Found"}`, sha `37ec4665a810…`), przy `/api/v1/projects/` → **401** i `/api/v1/users/1` → **405** z run1 |
| L20 | `dns.pl/deleted_domains.txt` | 3 (dane wrażliwe) — **prawdopodobnie wykluczone** | **ZAMKNIĘTY NEGATYWNY bez pracy usera (05.11, run 9)** — 200 `text/plain` **46 440 B** (wzrost z 37 343 B w ~24 h), **znaczniki PII: puste = 0 e-maili, 0 PESEL-i, 0 telefonów +48, 0 IBAN-ów**; arytmetyka: `/api/count-deleted-domains` = `{"count":"+1467"}` ⇒ 46 440 B / 1 467 ≈ **31,6 B na wiersz** = sama nazwa domeny | nie wracać: dane publiczne rejestru, klasa wykluczona §8. Dowód: `WYNIKI-RUN9-RUN10-20261105.md` §7 |
| L21 | `science/api/media` — mechanizm | — | **ZAMKNIĘTY z pełnym wyjaśnieniem** | proxy statycznych assetów z allow-listą katalogów (`wp-content/`, `wp-includes/`) i typów (`.php` → 404) za nginx normalizującym `%2e`/`..` przed aplikacją; dowód: `wp-includes/js/jquery/jquery.min.js` → 200 (jQuery 3.7.1, 87 553 B) przy `wp-includes/version.php` → 404 |
| L22 | mining bundli (28 endpointów, 0 sekretów w 10,47 MB) | 1 (poświadczenia) | **ZAMKNIĘTY (05.11)** — ostatni nieznany kąt (czyste nazwy parametrów `dns.pl/api/*`) domknięty: `statisticsUrl` i `domainName` to zmienne **klienta** z `main-3.3.0.02aeae80.js`, nie parametry API — oba endpointy dają 404 (run 9), a 200 przy wzorcach ataku w query to przechwycenie brzegowe (L25, run 10) | nie wracać |
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
| embed PowerBI — **tylko sam URL embedu** (trasa `/trendy` = 404 ×3, korekta #49); prawdopodobieństwo obniżone, nie wykluczone | **user, 30 s w incognito** | **user, 2 min w incognito** |
| `dns.pl/deleted_domains.txt` — **ZAMKNIĘTY bez usera**: 0 znaczników PII w 46 440 B + 31,6 B/wiersz przy 1 467 pozycjach = same nazwy domen | zamknięte (run 9) | **user, 10 s** |
| **L23** | `sendForm` — **wariant bez tworzenia rekordu** (walidacja serwerowa + egzekwowanie reCAPTCHA). Opis niżej | ja, **wyłącznie po jawnym GO** |
| L3 | `sendForm` — pełny test (SSRF z odczytem, walidacja uploadu, stored XSS w panelu, mass assignment) | **ODRADZAM — tworzy fałszywe zgłoszenie dezinformacji** (patrz korekta #41) |
| `centres-search` — **ZAMKNIĘTY jako dane instytucjonalne**: 10 e-maili, 8 domen GOPS/MOPS w tej samej odpowiedzi, `personal_like` puste | zamknięte (run 9); resztka: run 11 `sos-L02/L03` | user, 2 min |
| L14 | `bezpiecznymiesiac.pl/ecsm/zglos-inicjatywe/` (klasa 7/13/8, Tier 2 — ta sama klasa co `sendForm`, mniejsza konkurencja) | user + jawne GO |
| L15 | `science.nask.pl/contact` (7/8, niski — prawdopodobnie tylko wysyła maila) | user + jawne GO |
| L1/L2 | HIVE: IDOR/BAC/mass assignment/reset hasła | po koncie od organizatora (wniosek = L0 pkt 2) |
| L10/L11 | zakres `www.nask.pl` (apex → 302, §5 bez `*`) i `info-trace.116sos.pl` | pytanie do organizatora (L0 pkt 3) |
| mapa HIVE — **ZAMKNIĘTA offline**: 71 tras klienta, 0 literałów API ⇒ API tylko z HAR-a | zamknięte (run 9/10) | ja, offline |
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

---

# DOPISEK 05.11 (run 9 + run 10 + run 11) — zamknięcia z mechanizmem i nowe leady

Źródło dowodów: `WYNIKI-RUN9-RUN10-20261105.md` (pełne tabele), `PRZEGLAD-REPO-NASK-20261105.md`
(przegląd repo `peteraangelic-pixel/NASK`), `reports/rawpath-006-run9.json`,
`reports/rawpath-007-run10.json`, `reports/mine-rawpath-00{6,7}-run{9,10}.json`,
`reports/logs-run{9,10}/`.

## Log żądań 05.11

| kanał | przebieg | żądania | tempo | hosty | wynik |
|---|---|---:|---|---|---|
| Actions `42020874553` (run 9) | RAWPATH-006 | 31 | 1,0 req/s, 47,08 s, min. odstęp 1,000 s | 7 hostów §5 (dns.pl, science, oad, bezpiecznymiesiac, pllum, dataannotation, 116sos) | 1 kandydat (`CANDIDATE-PII-IN-RESPONSE` = `centres-search`, 10 e-maili instytucji); 13×404, 4×400, 1×transport-error; 30 ciał 3 646 132 B; mining 29 plików, **71 tras HIVE** |
| Actions `42022263875` (run 10) | RAWPATH-007 | 22 | 1,0 req/s, 21,37 s, min. odstęp 1,000 s | 5 hostów §5 (dns.pl, science, oad, pllum, dataannotation) | **0 kandydatów**; 8 grup rozstrzygnięć A–H; 22 ciała 460 469 B; mining 20 plików, 17 endpointów |

**Razem: 321 (do 04.11) + 31 (run 9) + 22 (run 10) = 374 żądania GET** do celów + 7 `fetch_page`
+ 2 zablokowane `curl` w sandboxie. Wszystkie przebiegi: 1,0 req/s (sufit §6 pkt 2 = 5),
najmniejszy zmierzony odstęp 1,000 s, **GET-only, zero POST/PUT/DELETE, zero zmian stanu,
zero hostów spoza §5, zero zgłoszeń, zero użycia znalezionych wartości** (porównywaliśmy
wyłącznie odciski sha256 — korekta #33).

Celowo pominięte hosty ujawnione w run 9 (poza literałami §5, więc **nie odpytywane**):
`panel.dns.pl`, `tracker.dns.pl` (z bundla dns.pl), `www.nask.pl` (L10), `info-trace.116sos.pl`
(L11), `app.powerbi.com` (Microsoft).

## Zamknięcia 05.11 — nie wracamy

| co | dowód | wniosek |
|---|---|---|
| **L24** `dns.pl /api/stats/?statisticsUrl=` = SSRF | `/api/stats/` → **404** (40 914 B, Drupal) w 4 wariantach; run10 `dns-K06` `/api/zone-stats?x=%0D%0A` → **200 text/html 51 225 B** (strona główna) przy `dns-K07` `/api/zone-stats?x=1` → **200 application/json 11 761 B** | **MARTWE z mechanizmem**: `statisticsUrl` to zmienna klienta, a 200+HTML to **przechwycenie brzegowe** (L25), nie pobranie czegokolwiek |
| **L25** mechanizm `200 + ~51,2 kB + _event_transid` na dns.pl | `dns-K06` vs `dns-K07` (ta sama ścieżka, różni się tylko query) **oraz** `dns-K08` (ścieżka nieistniejąca + obcy URL w query → **200**) vs `dns-K09` (ta sama ścieżka bez query → **404**) | Warstwa brzegowa rozpoznaje wzorce ataku w query (CRLF, absolutny URL obcego hosta) i oddaje stronę główną z licznikiem zdarzenia **przed routingiem**. **Reguła dla wszystkich sesji:** na dns.pl `200 + ~51,2 kB + transid` = *żądanie oflagowane*, **nie** *zasób istnieje*. Samo przechwycenie **nie jest wypłacalne** (brak obejścia, brak zmiany stanu, brak danych) — **nie zgłaszamy** |
| **L26** kandydat na sekret w dns.pl (111 znaków, entropia 5,5) | 3 różne strony ⇒ 3 różne odciski: `b2c856bd7b5c` (111), `aeedb50f4571` (112), `ee5b2b574f12` (109); te same 3 żądania `/api/who-is-xml/?domain=nask.pl` raz dają kandydata, raz nie | **Nonce na-odpowiedź, nie poświadczenie** ⇒ klasa 1 ZAMKNIĘTA NEGATYWNY. Znany fałszywy pozytyw `generic_assignment` na stronach dns.pl (warstwa śledząca: `tracker.dns.pl`, `_event_transid`) |
| **L27** `dns.pl /api/who-is-xml/` (proxy WHOIS + CRLF) | **404** w 5 wariantach: bez parametru, `domainName=nask.pl`, `domainName=<nieistniejąca>`, `domainName=nask.pl%0D%0Aexample.pl`, `domain=nask.pl` | Endpoint **nie istnieje** jako GET ⇒ hipotezy wstrzyknięcia do zapytania WHOIS i wycieku danych abonenta **bezprzedmiotowe**. Run9 `dns-J10` (200) to przechwycenie brzegowe (L25) |
| **L28** `science.nask.pl/api/search` | `?query=hive&post_status=draft` → **sha256 `b4c9ddfdb205…` IDENTYCZNY** z `?query=hive` (run 9); `page=2` → `{"pageData":[],"page":0,"perPage":0,"lastPage":0}`; `perPage=100` → **400** `{"error":"Invalid pagination"}`; bez `query` / `q` / `searchPhrase` → **400** `{"error":"Query must be at least 3 characters"}` (identyczny sha256 w 3 próbach); **PII = 0** | Nowy żywy endpoint (nikt z 6 sesji go nie testował), ale oddaje **wyłącznie treści opublikowane** (wpisy WP + `typeName:"Osoba"` = kadra publiczna + metadane załączników). Walidacja serwerowa, paginacja ograniczona, `post_status` ignorowany ⇒ **klasa 3 ZAMKNIĘTA NEGATYWNY z kontrolą**. Zostaje z tego `/api/contact` → **405** `{"error":"Method not allowed"}` (= trasa POST-owa, L15 wymaga GO) |
| **L29** `pllum.org.pl` previewToken | `/api/_content/query?preview=test-123` i `/api/_content/query` → **identyczny sha256 `78516d89b48f…`**, 9 543 B, dokumenty Nuxt Content z jawnym polem `_draft` | Parametr `preview` **ignorowany** ⇒ trop ZAMKNIĘTY NEGATYWNY. Kryterium falsyfikacji na przyszłość: pozytyw = wpisy z `_draft: true` w tej odpowiedzi (do sprawdzenia z kontem CMS) |
| **L30** `oad.nask.pl/trendy` | **404** (13 814 B), `/en/trendy` → **404** (identyczny sha256), `/trendy/` → **308** `location: /trendy`; chunk `41lk95l8op7nz.js` → **200, 34 692 B**, w środku trasy `/about-us`, `/news`, `/trendy`, `/o-nas`, `/aktualnosci`, `/media/` + szablony `/${t.L}`, `/${t.H.EN}` i host `app.powerbi.com` | Trasa **nie istnieje** w bieżącym deploy-u, choć kod jest wysyłany ⇒ **korekta #49**: instrukcja L13 sprowadza się do samego URL-a embedu. Run 11 (`oad-L04/L05`) ustala aktualną tabelę tras |
| **L31** `access_token` w bundlu `bezpiecznymiesiac.pl` | run9 `bm-J26` → **404, 9 B** (chunk usunięty przez redeploy); lista literałów tego chunka z `analysis-run003.json`: `sharer.php`, `graph.facebook.com/?id=`, `api.pinterest.com/v1/urls/count.json`, `api.tumblr.com/v2/share/stats`, `vk.com/share.php`, `connect.mail.ru/share`, `b.hatena.ne.jp/add?mode=confirm&url=`, `getpocket.com/save`, `gab.com/compose`, `connect.ok.ru/dk`, `social-plugins.line.me/lineit/share` | **Biblioteka przycisków udostępnij**, nie poświadczenie NASK ⇒ **nie zgłaszamy**. **Korekta #46:** w mojej notatce z fali 2 ścieżki `/news/`, `/post-data/`, `/events/?${r.toString()}` były błędnie przypisane do `dns.pl` — należą do tego bundla i do cudzych serwisów. Nauczka: nazwy chunków Next.js/Turbopack żyją ~dobę ⇒ lead z bundla wymaga re-weryfikacji przed wydaniem żądania |
| mapa API HIVE z bundla (L18) | 71 tras **klienta**, **0** literałów `/api/…` w 2 770 426 B; `/api/v1/projects/test/conversation/1` → **404**, `/api/v1/annotators` → **404** (sha `37ec4665a810…`) przy `/api/v1/projects/` → **401** i `/api/v1/users/1` → **405** | Kształt API **nie wynika z bundla** ⇒ mapę API da wyłącznie HAR z zalogowanej sesji. `/admin/logs` jest trasą klienta, co wyjaśnia shell 713 B (H10 obalony słusznie) |
| sweep `downloadFile?fileId=` (60 ID) z `NASK@b2cf80a4:nask-lab/naskhunt/checks.json` | wykonany i zamknięty wcześniej (Gemma-B runda 6: same publiczne zdjęcia); potwierdzone w run1 i run10 `sci-K20`/`sci-J20` → 400 `{"error":"Invalid file id"}` | **Nie powtarzamy.** Uwaga: ich pole `class: "8.9"` to **oczekiwane CVSS** (widełki Wysoka 7.0–8.9 z §7), nie klasa z §8 |

## Nowe leady z 05.11

| id | cel | klasa | status | plan |
|---|---|---|---|---|
| L32 | `zglos-dezinformacje.nask.pl/api/sendForm` — **GET** (405 + nagłówek `Allow`) | — (rozpoznanie) | **AKTYWNY (run 11, `zglos-L01`)** — zero zmiany stanu: odczyt trasy, nie wysyłka | bez tego L23/L3 są planowane na ślepo (nie wiemy, jakie metody serwer przyjmuje) |
| L33 | `116sos.pl` — trasa katalogu placówek + `mapa-serwisu` | 3 (tylko warunkowo) | **AKTYWNY (run 11, `sos-L02/L03`)** | domknięcie resztki L9 **bez** 2 minut usera: porównanie zbioru placówek z API ze zbiorem tras publicznych |
| L34 | `oad.nask.pl/en/` + chunk nawigacji `0gnc331ufzpqs.js` | 3 (warunkowo, przez L13) | **AKTYWNY (run 11, `oad-L04/L05`)** | aktualna tabela tras deploy-u: czy strona z PowerBI istnieje pod inną nazwą |
| L35 | `dns.pl/lista_domen_usunietych` i `/przegladarka` | — | **AKTYWNY (run 11, `dns-L06/L07`)** | drugie, niezależne potwierdzenie L20 przez UI + ustalenie, jak `/przegladarka` odpytuje dane (`/api/domain-browser/` = 404 w GET) |
| L36 | `NASK@b2cf80a4:nask-lab/tools/bundle_scan.py` | — (narzędzie, compliance) | **DEFEKT ZGŁOSZONY** | ich kopia **mojego** narzędzia sprzed korekty #33 zapisuje `preview` = 4 pierwsze + 2 ostatnie znaki wartości sekretu (a dla wartości ≤ 8 znaków — **całą wartość**) do raportu commitowanego w publicznym repo. Dowód odtworzony 05.11 na syntetycznym kluczu: ich wersja `{"preview":"aK91…3w"}`, moja `{"length":20,"fingerprint":"6e2ae262d780"}`. Brak też #39/#44/#45/#48 |

## Korekty własne z 05.11

* **#43** — narzędzie nie rozróżniało danych publicznych od osobowych; dodane liczniki PII
  (e-mail / PESEL z pełną sumą kontrolną / telefon +48 / IBAN PL) raportowane **wyłącznie jako
  liczby**, podgląd wyciszany przy trafieniu, nowy werdykt `CANDIDATE-PII-IN-RESPONSE`,
  liczenie tylko dla odpowiedzi DANYCH (nie HTML/JS — `mailto:` w stopce dawałoby kandydata
  na każdym żądaniu). **To dzięki temu L20 i L9 zamknęły się bez pracy usera i bez
  publikowania czegokolwiek.**
* **#44** — `bundle_scan` nie wydobywał literałów ścieżek ani hostów, więc bundel HIVE
  (2,77 MB) dawał 0 tras; dodane `paths` (priorytet nie-statyczne, cap 300), `hosts` (cap 80)
  i sekrety w query-stringu (`?access_token=WARTOŚĆ`) jako odcisk.
* **#45** — `generic_assignment` łapał sklejenia minifikatora (`token="+encodeURIComponent(t)+"`
  → 23 znaki, entropia 3,73), co skończyłoby się fałszywym zgłoszeniem; dodany filtr kształtu
  wartości (`looks_like_credential`).
* **#46** — błędne przypisanie `/news/`, `/post-data/`, `/events/?…` do `dns.pl` (należą do
  biblioteki share z `bezpiecznymiesiac.pl`).
* **#48** — **moja własna regresja z #45**: obniżyłem próg entropii z 3,5 do 3,0 dla wszystkich
  kandydatów, przez co run 9 zgłosił 8-znakowy szum z bundla HIVE. Przywrócone 3,5 (i 4,0 dla
  wartości < 12 znaków); test asertuje oba progi.
* **#49** — instrukcja L13/L0.5 („otwórz `oad.nask.pl/trendy`") była **błędna**: trasa daje 404
  w 3 wariantach. Poprawione w runbooku i w rejestrze: sprawdzenie dotyczy wyłącznie URL-a embedu.
* **Stan testów:** 92 testy `unittest` OK (76 → 92) + `rawpath.py --selftest` **13 grup** OK
  + vendored `a450b00f` 11/11 OK.
