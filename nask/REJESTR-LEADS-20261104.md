# Rejestr leadów + log żądań (noc 3/4.11.2026) — dowód zgodności

**Zasada rejestru:** lead żyje tylko z nazwaną klasą z regulaminu i planem PoC na własnych
kontach. Wszystko, co poniżej oznaczone WYKLUCZONE, **nie idzie do zgłoszenia** (regulamin §8).
**Brak w tym pliku działających payloadów do czegokolwiek pozytywnego — bo pozytywnych nie ma.**

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
| L1 | HIVE | 9.1–9.3, 12.1–12.2, 13 | **ZABLOKOWANY (04.11)** — brak publicznej rejestracji: `/register`, `/api/v1/register` → 404 w 2 kanałach; `/api/v1/projects/` → 401; `/api/v1/users/1` → 405 | runbook rev 2 **L4**; wymaga konta od organizatora (wniosek = L0 pkt 2) |
| L2 | HIVE reset | 2.1–2.3 | **ZABLOKOWANY (04.11)** — jw., bez konta nie ma przepływu do zbadania | runbook rev 2 L4 krok 4.5 |
| L3 | zglos-dezinformacje | 7 (upload ze skutkiem), 5 (SSRF **z odczytem**) | **AKTYWNY — najwyższa wartość**; automatem niewykonalny (reCAPTCHA v3 + żądanie zapisujące) | runbook rev 2 **L1** (przeglądarka usera + jawne GO); korekta #31: dowodem jest żądanie do własnego kontrolera **z odczytem**, nie tylko refleksja w UI |
| L4 | 116sos / science / dyzurnet | 3.1/3.3, 12.2 | **CZĘŚCIOWO ZAMKNIĘTY (04.11)**: `116sos/api/{fetch-cookie-hash,announcements,og-image,centres-search}` = negatywy/dane publiczne (run2); `science/api/media` = zamknięty (run1+2+3, 22 próby); `science/wp-json` = 404 | zostało: porównanie `totalItems` z UI 116sos (2 min usera) |
| L5 | dns.pl | 3.3 / 12.2 | **AKTYWNY (niski)**; uwaga: host oddaje stronę główną z kodem 200 na obce ścieżki + `_event_transid` (korekta #32) ⇒ bez normalizacji każde porównanie jest fałszywe | runbook rev 2 L5 (mapa z bundli Drupal `domain-browser`) |
| L6 | oad `/podglad-pdf` | 5 / 15 | **MARTWY (dowód: wiersze 8–12 logu)**; uzupełnione 04.11: na tym brzegu 500 nie niesie informacji (App Router daje 500 na każdą obcą ścieżkę) | nie testować ponownie |
| L7 | `science.nask.pl/api/media/` traversal | 15 (path traversal/LFI) | **ZAMKNIĘTY NEGATYWNY (04.11, run1+2+3)** — `%2e` normalizuje nginx; aplikacja nie dekoduje drugi raz (`%252e%252e` → 404); ucieczka = `RemoteDisconnected`/nginx 400/404 aplikacji; **0 plików spoza `wp-content`** | nie wracać; dowód w `reports/rawpath-00{1,2,3}-run*.json` |
| L8 | `116sos.pl/api/fetch-cookie-hash` | 3 | **ZAMKNIĘTY NEGATYWNY (04.11)** — wartość stała `6a9963b75ab63` w 3 próbkach przy nowym ciastku `stickounet` za każdym razem; brak wpływu (informacja bez danych wrażliwych = wykluczone) | nie wracać |
| L9 | `116sos.pl/api/centres-search` | 3.1/3.3 | **AKTYWNY (2 min pracy usera)** — 28 kluczy, dane instytucjonalne placówek; jeśli API oddaje więcej niż publiczne UI (placówki niepubliczne / dane opiekunów) → klasa 3, Tier 2 do 10 000 zł | porównać `totalItems` z wyszukiwarką na `116sos.pl` |
| L10 | `www.nask.pl` (apex `nask.pl` → 302) | — | **BLOKADA FORMALNA** — apex daje 302 na `www` w 8/8 żądań (run007), a §5 wymienia literał `nask.pl` bez `*` ⇒ cały Tier-1 host praktycznie nietestowalny | pytanie do organizatora (L0 pkt 3) |
| L11 | `info-trace.116sos.pl` | — | **POZA §5** — subdomena ujawniona w nagłówku `Access-Control-Allow-Origin` (run1, `sos-D01/D02/D03`); nie testuję bez interpretacji organizatora | to samo pytanie co L10 |
| L12 | mapy API z bundli (zglos flight-data 13+ chunków, dyzurnet app-router, dns.pl Drupal) | 9/12 | **AKTYWNY (ja, offline)** — bez wysyłania żądań; potem jedna sonda celowana na endpoint, nie sweep | `bundle_scan.py` + runbook rev 2 L5 |

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

Źródła: `PRZEGLAD-GALEZI-20261104.md` (przegląd + dowody), `RUNBOOK-REV2-20261104.md` (nowa
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
| L3 / runbook L1 | `sendForm` (SSRF z odczytem przez własny kontroler, walidacja uploadu, stored XSS w panelu, mass assignment) | **user w przeglądarce + jawne GO** |
| L9 | `totalItems` z `/api/centres-search` vs liczba placówek w publicznym UI | user (2 min) |
| L1/L2 | HIVE IDOR/BAC/mass assignment/reset hasła | po koncie od organizatora |
| L10/L11 | zakres `www.nask.pl` i `info-trace.116sos.pl` | pytanie do organizatora (L0) |
| L12 | mapy API z bundli (zglos flight-data, dyzurnet app-router, dns.pl Drupal) — offline | ja |
| L5 | `dns.pl` z normalizacją `_event_transid` | ja (niski priorytet) |
