# Przegląd 6 gałęzi + repo NASK — co przejmuję, co prostuję, co wnoszę (04.11.2026)

Autor: sesja Arena `c87f7a48` (rola zespołowa wg podziału `5ed750ef`: **rejestr leadów + runbooki**).
Zakres: program **NASK PIB** na `hack.cert.pl`, edycja 11/2026 (03–30.11.2026).
Wszystkie SHA i daty pobrane dziś przez API GitHuba — nie z pamięci i nie z cudzego podsumowania.

**Stan potwierdzonych podatności w całym zespole (6 sesji): 0.** Zgodne niezależnie u wszystkich.
To nie jest porażka narzędzi — publiczna, nieuwierzytelniona powierzchnia 12 hostów jest wytarta.
Pieniądze leżą za kontami i w żądaniach zapisujących (patrz §7 — nowa kolejność).

---

## 1. Co dokładnie przejrzałem

| repo | gałąź | HEAD | data | co nowego dla NASK |
|---|---|---|---|---|
| Pokemon | `arena/c87f7a48-pokemon` (moja) | `2a02ea2`→`0b7fb7b`→`fc0922b`→`53cce79` | 03–04.11 | nocny rekones pasywny (12 GET), `/podglad-pdf` = martwe, `bundle_scan.py`, teraz `rawpath.py` + 2 przebiegi |
| Pokemon | `arena/7911f950-pokemon` | `cac68f82` + bot `d6eadc4d` | **04.11 10:13** | Rust `nask/tools/surface`, run 003 (**479 żądań**, mapa 12 hostów), sondy 004b–006 (**68**), macierz host×ścieżka **007 (86 prób, 23 „interesting")**, 008 gotowy |
| Pokemon | `arena/a450b00f-pokemon` | `40964ea0` | 03.11 23:05 | offline lab (FFI Rust+Rayon, `auth_matrix.py`, timing), mapa 4 programów, rozpoznanie `moje.cert.pl`, **konflikt prawny IV §4.2** |
| Pokemon | `arena/d1882c0f-pokemon` | `2d46dcb6` | 01.11 | `battery-sim` v0.2 — **niezwiązane z NASK**, pomijam |
| Pokemon | `7cc8a7e0` / `98ddb59f` / `8560a56a` | `b64f5803`/`148be97d`/`a852d3a5` | 10–13.10 | stare ARC/PTCG — brak nowości |
| Gemma-konkurs | `arena/c4eeb067` (Gemma-B) | `61f4168c` | 03.11 23:26 | **165 żądań / 6 rund**: kontrakt `fileId`, sweep 60 ID, HIVE 401/405/404, CVE-2025-29927 negatyw, WAF reset, `IDEAS.md` z EV |
| Gemma-konkurs | `arena/6d081d52` (Gemma-A) | `d4a0d7ae` | **04.11 10:12** | automat `nask-hunt`, sondy S1–S8 (703 żądania, 15 hostów), **korekta 52 fałszywych trafień + 4 testy regresyjne**, `DO-ZROBIENIA-RANO.md` |
| Smak-Domu-Konkurs | `arena/5ed750ef` | `6fd86e30` | **04.11 10:12** | 5 biegów Actions **~1500 żądań @4,5 rps**, `jsdig` 7,3 MB (47 bundli, 0 sekretów, 0 sourcemap), `RESULTS-NOC1.md` (H9–H13), **`SYNTEZA-ZESPOLU-20261104.md`** |
| Smak-Domu-Konkurs | `codex/*` (3 gałęzie) | `6347cdb0`/`ff777842`/`27f5b436` | 30.10–02.11 | ARC-AGI-3 — projekt zamknięty, pomijam |
| NASK | `arena/a29ca234-nask` | `10cbb620` | 03.11 22:50 | naprawa narzędzi Rust wg regulaminu, `drive_materials/` (13 plików), `nask-codex/research/porownanie-programow.md` |
| NASK | `codex/multi-program-lab-20261103` | `a4fb58df` | 03.11 22:56 | **pełne teksty regulaminów 5 programów** (`.txt`+`.pdf`), nocna operacja `.git/HEAD`+`/.env` na **24 hostach = 71 żądań, 0 kandydatów**, manifest `programs/2026-11.json`, `tools/recon` (Rust+Python, 19+8 testów, FFI) |

---

## 2. Najważniejsza rzecz, którą odkryli inni, a ja nie: **kanał**

W nocy zrobiłem 12 żądań przez narzędzie `fetch_page` i uznałem to za swój jedyny kanał. To była
pomyłka w obu kierunkach:

1. **Sandbox nie ma wyjścia do celów.** Potwierdziłem dziś pomiarem: `curl https://science.nask.pl/...`
   → kod `000`, `curl https://dns.pl/.env` → `000`, `curl https://github.com` → `200`. DNS działa
   (`getent hosts dns.pl` → `193.59.201.40`), TCP nie. Niezależnie ustaliły to `7911f950` i `a450b00f`.
2. **Runner GitHub Actions ma pełny internet.** Pięć sesji zbudowało na tym pipeline'y z limiterem
   < 5 req/s i strażnikiem zakresu. Ja też już mam: `.github/workflows/nask-rawpath.yml`
   (bramka = testy offline, potem przebieg, potem commit raportu).
3. **`fetch_page` jest ślepy**: nie zwraca kodu odpowiedzi ani nagłówków, a URL może znormalizować.
   Nadaje się do czytania treści (tak rozstrzygnąłem `dns.pl/.env`), nie do pomiaru.

**Konsekwencja praktyczna:** każdy pomiar musi iść z Actions, a `fetch_page` zostaje jako drugie,
niezależne źródło do czytania treści. Dwa kanały o różnych ułomnościach = rozstrzygnięcia, nie opinie.

---

## 3. Przejmuję bez zastrzeżeń — falsyfikacje (nie testować ponownie)

| hipoteza / klasa | werdykt | kto zmierzył | moja weryfikacja |
|---|---|---|---|
| `oad.nask.pl/podglad-pdf?url=` = SSRF/LFI | **MARTWE** (walidacja tylko prefiksu `/media/`, poza nim 500 bez danych, pobranie klienckie) | ja (c87, 12 GET) | przyjęte przez `5ed750ef` w syntezie |
| `bezpiecznymiesiac.pl/download-file/?fileUrl=` = LFI/SSRF | **ZAMKNIĘTE** — 20 wariantów: `/etc/passwd`, `%2e%2e%2f`, `..%5c`, `file://`, `HTTPS://`, `http%3A%2F%2F` → 400/404; filtr dekoduje **przed** sprawdzeniem | `7911f950` run 004b | nie powtarzam |
| `science.nask.pl/api/downloadFile` = enum ID | **MARTWE jako enum** — kontrakt `fileId` (liczbowy), twarda walidacja (`-1`, `18864abc`, `fileId[]` → 400 `Invalid file id`), sweep 60 ID w 4 przedziałach → same publiczne zdjęcia z aktualności | Gemma-B runda 6 | **potwierdziłem swoim kanałem**: run1 `?fileId=18864` → 200 `image/png` (z metadanymi C2PA), `?fileId=-1` → 400 `{"error":"Invalid file id"}` |
| `/_next/image?url=` = SSRF | negatyw na 6–7 hostach (403 brzeg, 400 „Nieprawidłowe żądanie obrazu", 404, 502), `@`-bypass nie przechodzi | `7911f950` + Gemma-B + `5ed750ef` | nie powtarzam |
| CORS z odbiciem `Origin` | **brak** na 8–9 endpointach; jedyne `ACAO:*` bez credentials (wykluczone §8) | `7911f950`, Gemma-B, Gemma-A (S1) | nie powtarzam |
| CVE-2025-29927 (middleware Next.js) | negatyw na 4 hostach; u Gemmy-A 6 „trafień" S2 = WAF 403 (374 B vs 377 B — identyfikator żądania w blokadzie) | Gemma-B + Gemma-A (sami sfalsyfikowali) | nie powtarzam |
| SQLi przez GET | WAF ucina/zerwie połączenie na `' OR 1=1`, `pg_sleep`, `../` | Gemma-B | nie powtarzam przez GET |
| `.git/HEAD`, `/.env` jako ekspozycje | **0 kandydatów** na 24 hostach (71 żądań, wymóg sygnatury formatu + dwóch kontroli) | NASK `codex/multi-program-lab` | **potwierdziłem na 12 hostach NASK** — patrz §5 (run007 „23 interesting" = szum) |
| sourcemapy (`.map`) | żaden z 47 bundli (7,3 MB) nie wystawia mapy, brak `sourceMappingURL` | `5ed750ef` (jsdig) | nie powtarzam |
| `dns.pl/api/*` z bundla | 3 z 5 ścieżek to martwe trasy klienta; żywe i publiczne: `/api/zone-stats`, `/api/registrars-services` | Gemma-B + `5ed750ef` (bieg 4/5) | spójne |
| `zglos-dezinformacje` — mapa statusami | **bezużyteczna**: App Router zwraca 500 (`__next_error__`, „ERROR 258337316") na obce ścieżki, a `/server-status` daje 200 z treścią 404 | `7911f950` run003 | **potwierdziłem**: run1 `zglos-B08` = 200/30 260 B/`text/html`/`SOFT404_PL`×4 |
| `116sos.pl` niedostępny | 502 nginx od ~23:00 na wszystko (awaria, nie wynik; dostępność nie jest w §8) | Gemma-B + `5ed750ef` | **NIEAKTUALNE — host wstał**, patrz §6 |
| `secure.edu.pl`, `bezpiecznewybory.pl` | brak odpowiedzi transportowej / WAF 403 dla IP Actions ⇒ **nie „czyste", tylko niewidoczne tą metodą**; testowalne z sieci domowej | `7911f950`, Gemma-B, `5ed750ef` | przyjmuję ograniczenie |

**Zasada metodologiczna, którą przejmuję od Gemma-A** (ich 706 żądań dało 52 „trafienia", z czego
~50 fałszywych; dowód: `dns.pl` „odblokowany `/admin`" = 51 121 B przy stronie głównej 51 152 B):
**sonda bez grupy kontrolnej nie jest sondą, tylko generatorem pracy.** Każda moja próba ma kontrolę
w tym samym przebiegu, a dowód prymitywu opieram na **równości sha256**, nie na kodzie odpowiedzi.

---

## 4. Przejmuję — nowa wiedza pozytywna (zmienia mój plan)

1. **Kontrakt `POST /api/sendForm`** (`zglos-dezinformacje`, wydobyty z bundle'a przez `7911f950`):
   `multipart/form-data`; `accept` (wymagane, niepuste), `email`, `file` (klient: `image/png`,
   `image/jpeg`, ≤ 20 MB), `reason` ≤ 250, `urls` (wymagane, **do 50 linków, po jednym w linii**),
   `g-recaptcha-response` (**reCAPTCHA v3** — bez niej `executeRecaptcha is not ready`).
   → **Mój RUNBOOK L3 był źle ustawiony** (korekta #26): automatem nie da się tego przetestować
   wcale. Jedyna droga: przeglądarka użytkownika + jawne GO (żądanie tworzy prawdziwe zgłoszenie
   u operatora rządowego = zmiana stanu).
2. **HIVE (`dataannotation.pllum.org.pl`) nie ma publicznej rejestracji** — `/register` i
   `/api/v1/register` → 404; `/api/v1/projects/` → 401 `{"detail":"Not authenticated"}`;
   `/api/v1/users/1` → 405 (trasa istnieje dla innej metody); brak `openapi.json`/`docs`.
   → **Mój RUNBOOK L1/L2 (IDOR/BAC + reset hasła) jest ZABLOKOWANY** (korekta #27): bez konta od
   organizatora nie ma dwóch sesji do porównania. To zmienia całą kolejność poranka (§7).
3. **Stack i brzeg** (`5ed750ef`, przydatne przy każdym zgłoszeniu): Azure Front Door + Envoy
   (`zglos`, `oad`, `dataannotation`, `pllum`, `bezpiecznymiesiac`; `CONFIG_NOCACHE`), Cloudflare
   (`dyzurnet`), własny stack z `SESID` (`dns.pl`), Next pages-router (`116sos` buildId
   `8CjJwbyxpVqpWnorny23T`, `science` `Grl_YQ5SCHd1ahmhesPv6`), Next app-router (`zglos`, `dyzurnet`).
   HIVE: SPA Vite+React+TanStack, backend **FastAPI**. Kontakt IOD: `iod@nask.pl`.
4. **Reguła jednej wypłaty, precyzyjnie**: §7 pkt 9 NASK — ten sam błąd źródłowy we wspólnym lub
   skopiowanym kodzie/komponencie/konfiguracji liczy się jako **jedna** podatność, nawet na wielu
   serwisach (źródło: `NASK@codex/multi-program-lab`, `research/porownanie-programow.md`,
   czytane z pełnego PDF regulaminu). W zespole 6 sesji to też ryzyko duplikatu wewnętrznego.
5. **Pieniądze i terminy** (jw.): cztery duże programy mają identyczne stawki
   (600/4 000/9 000/20 000 PLN) i pulę 100 000 zł; Władysławowo 200/1 000/2 000/4 000 i 10 000 zł.
   Rozstrzygnięcie do 30 dni po końcu edycji, wypłata do 60 dni, wygraną trzeba potwierdzić na
   platformie **w ciągu 7 dni**. Suma pul pięciu regulaminów: 410 000 zł („milion" z artykułu to nie
   budżet jednej edycji).
6. **Program CERT Polska obejmuje `hack.cert.pl` i `mwdb.cert.pl` w Tier 1** — sprawdziłem u źródła
   (`NASK@codex/multi-program-lab`, `research/sources/cert-polska-terms-2026-11.txt`, §5 linie 66–74:
   Tier 1 `cert.pl, m.cert.pl, incydent.cert.pl, moje.cert.pl, n6portal.cert.pl, mwdb.cert.pl,
   hack.cert.pl`; Tier 2 `*.cert.pl, ctf.hack.cert.pl`; wykluczone `*.hack.cert.pl`, `*.lab.cert.pl`).
   Czyli propozycja Gemmy-A („`hack.cert.pl` awansuje na pierwszy cel") **nie jest poza zakresem**,
   jak podejrzewałem — ale jest poza **moim** zakresem (§8 niżej).
7. **Użyteczny trik rozpoznawczy** (Gemma-A/a450): publiczna, nieoficjalna kolekcja API
   `github.com/Ysiakowy/moje.cert.pl-API` (15 operacji: 9 GET, 2 POST, 1 PATCH, 1 PUT, 2 DELETE)
   daje mapę endpointów **bez wysyłania żądania**. Odpowiednik dla NASK już mamy: bundle JS
   (`bundle_scan.py`, `jsdig`).

---

## 5. Prostuję i odrzucam — z dowodem, nie opinią

### 5.1 `7911f950` run 007: **23 „interesting" to szum** (rozstrzygnięte, zamykam wpis)

Run 007 (commit `d6eadc4d`, dziś 10:13) oznaczył 23 odpowiedzi jako „interesting", w tym
`dns.pl/.env`, `dns.pl/.git/config`, `dns.pl/db.sql`, `dns.pl/server-status`,
`dyzurnet.pl/server-status`, `zglos/server-status`, `dataannotation/.env`. Raport nie zapisuje
**typu odpowiedzi ani znaczników treści**, więc nie dało się tego rozstrzygnąć z ich danych.
Rozstrzygnąłem dwoma kanałami:

| URL | run007 | mój pomiar (run1 + `fetch_page`) | werdykt |
|---|---|---|---|
| `dns.pl/.env` | 200 / 51 201 B | **200 `text/html` 51 213 B**; treść = strona główna Drupal („Przeglądarka domen", „Aktualności", „Statystyki 2 756 528 domen") | **negatyw** |
| `dns.pl/.git/config` | 200 / 51 230 B | 200 `text/html` 51 230 B, **bez znacznika `GIT_REF`** | **negatyw** |
| `dns.pl/db.sql` | 200 / 51 227 B | 200 `text/html` 51 218 B | **negatyw** |
| `dns.pl/server-status` | 200 / 51 200 B | 200 `text/html` 51 218 B, **bez `APACHE_STATUS`** | **negatyw** |
| `dns.pl/` (kontrola) | — | 200 `text/html` **51 142 B** | strona główna |
| `dyzurnet.pl/server-status` | 200 / 58 279 B | 200 `text/html` 58 279 B, `SOFT404_PL`×8; treść „Nie znaleziono strony" | **soft-404** |
| `zglos/server-status` | 200 / 30 260 B | 200 `text/html` 30 260 B, `SOFT404_PL`×4; „Ups! Coś poszło nie tak… 404" | **soft-404** |
| `dataannotation/.env` | 200 / 713 B | 200 / 713 B, **sha256 IDENTYCZNY z `/`** (`908ce0b4…`) | **catch-all SPA** |

**Mechanizm fałszywych trafień na `dns.pl` (nowy, precyzyjny):** dla nieznanej ścieżki Drupal
oddaje stronę główną z kodem 200, wstrzykując `<script>var _event_transid='2072786175';</script>`
(licznik rośnie z żądania na żądanie: …175, …176, …177, …178), a żądana ścieżka jest **odbita
w kotwicach** skip-linków (`https://dns.pl/.env#navigation-menu-top`). Kontrola `/` nie ma
skryptu i jest o ~71 B krótsza. **Wniosek dla narzędzi (`7911f950`, `5ed750ef` jsdig, mój
`bundle_scan`):** na `dns.pl` każde porównanie bajtowe z baseline'em musi najpierw znormalizować
`_event_transid` i odbicie ścieżki, inaczej strzela na zawsze. To samo wyjaśnia, dlaczego ich
„catch-all subtraction" nie pomogło.

### 5.2 `7911f950` run 007 **NIE rozstrzygnął** `/api/media/` — i to też jest wynik

Wszystkie 3 sondy trawersalu zakończyły się **błędem transportu**, w tym `sci-media-abs`
= `https://science.nask.pl/api/media/etc/passwd` — **bez kropek i bez kodowania**. Z ich własnego
logu wynika więc, że wyzwalaczem jest sam łańcuch `etc/passwd` (WAF zrywa połączenie), a nie
`..` ani `%2f`. Ich wniosek „traversal w ścieżce jest niemierzalny tym klientem" jest **za mocny**:
niemierzalny był **cel**, nie mechanizm. Rozstrzygnąłem to celem nieszkodliwym (§6).

### 5.3 Gemma-A: priorytet `hack.cert.pl` / `mwdb.cert.pl` — fakty i granice

* **Fakt sprawdzony:** oba hosty są w Tier 1 programu **CERT Polska** (§5 ich regulaminu), więc
  pomysł nie jest nielegalny sam w sobie. Pula i stawki identyczne jak NASK.
* **Ale:** (i) to **inny program** — wymaga osobnej akceptacji jego regulaminu na platformie, a
  zakres usera dla mnie brzmi „NASK, bez Władysławowa"; (ii) `a450b00f` słusznie wskazuje
  **konflikt prawny**: regulamin *usługi* `moje.cert.pl`, część IV pkt 4.2, nakazuje powstrzymać się
  od działań mających na celu testowanie przełamania lub obejścia zabezpieczeń, choć program bug
  bounty ten host obejmuje → **pisemne wyjaśnienie organizatora przed testami uwierzytelnionymi**;
  (iii) Gemma-A wysłała 703 żądania na **15 hostów**, w tym `moje.cert.pl`, `incydent.cert.pl`,
  `www.gov.pl`, `n6portal.cert.pl`, `komunikator.narodowy.gov.pl` — czyli przekroczyła zakres NASK;
  u `incydent.cert.pl` pojawiło się **429** (ich własny raport), co znaczy, że doszli do limitu tempa
  po stronie celu. **Rekomendacja: nie wchodzić w CERT/Gov.pl/mSzyfr bez jawnej decyzji usera.**
* **Prostuję ich „trafienia średnie":** `S6` na `moje.cert.pl` (`x-original-url: /panel` → 403 4 542 B
  przy `/` → 200 31 158 B) to **odmowa**, nie obejście; `S1` `ACAO:*` bez credentials jest wprost
  wykluczone (§8); `429` to rate-limit, nie luka. Ich własna tabela „kandydaci per host"
  (`dns.pl` 7, `dyzurnet` 5, `zglos` 4…) jest więc miarą szumu, nie szansy — przy „Trafienia
  wysokie/krytyczne: **0**", co sami uczciwie napisali.

### 5.4 `5ed750ef`: „WP niepotwierdzony, rekonesans c87 wymaga ponownego sprawdzenia" — **rozstrzygnięte na korzyść WP**

Dowód: realne pliki pod `science.nask.pl/api/media/wp-content/uploads/sites/4/2023/06/Struktura-s-e1687258346784.jpg`
— 200 `image/jpeg` 182 155 B (kontrola `7911f950` run 005/006, Gemma-B) i 200 `image/jpeg`
w moim run1 (`sci-A01`, sha `febfe524…`, w ciale EXIF z datą 2023-01-27). Obecność `wp-content`
w ścieżkach mediów = WordPress jest realny; brak wzmianek w głównym HTML niczego nie dowodzi, bo
frontend to Next.js. **3 źródła przeciw 1.**

### 5.5 Czego nie powtarzam z cudzych planów (żeby nie palić dnia)

`IDEAS.md` Gemmy-B: poz. #5 (CVE-2025-29927 — zmierzone, negatyw), #9 (refleksje w wyszukiwarkach —
Gemma-B: brak refleksji, `400 Query must be at least 3 characters`), #8 (takeover subdomeny bez PoC —
wprost wykluczone §8), #7 (request smuggling — wysoki koszt, wymaga własnego proxy; zostaje na
później, ale **nie** metodą „wyślij i patrz, czy padło", bo DoS = dyskwalifikacja).

---

## 6. Co wnoszę nowego (nie duplikuje zespołu)

### 6.1 Narzędzie: `nask/tools/rawpath.py` — sonda o **surowej ścieżce**

Wysyła bajty ścieżki dosłownie (`http.client.putrequest`, bez normalizacji `..` i bez re-cytowania),
co zamyka lukę z §5.2. Do każdego żądania zapisuje: status, `Content-Type`, `Content-Length`,
**sha256 ciałа**, nazwy znaczników treści (nie fragmenty), `Set-Cookie` **tylko nazwy**, czas, błąd
oraz schemat kluczy JSON **bez wartości**. Klasyfikator wydaje werdykt z dowodu
(`soft-404-html`, `spa-catch-all-shell`, `html-page`, `media-file`, `CANDIDATE-SECRET-FILE`,
`method-not-allowed-route-exists`, `transport-error`…), a `cross_hash_evidence()` szuka
**identycznych ciał** między próbami — to jest dowód prymitywu, nie „200 = kandydat".
Straż zakresu: 12 literalów §5 (`www.nask.pl` **świadomie** odrzucane), HTTPS z weryfikacją
certyfikatu, port 443, brak przekierowań. Limiter: konstrukcja powyżej 5 req/s = wyjątek
(regulamin §6), domyślnie **1.0 req/s** (inne sesje: 4–4,5). Testy: **52 + 6 = 58 OK**,
selftest **10 grup OK** (bramka w workflow, zero sieci).

### 6.2 Przebieg RAWPATH-001 (35 prób, 1,0 req/s, 70,13 s, min. odstęp 1,000 s, **0 kandydatów**)

**a) `/api/media/` na `science.nask.pl` — trop zamknięty jako NEGATYWNY, z mechanizmem:**

| próba | ścieżka | wynik |
|---|---|---|
| `sci-A01` kontrola | `/api/media/wp-content/uploads/.../Struktura-…jpg` | 200 `image/jpeg`, sha `febfe524…` |
| `sci-A02` kontrola ujemna | `/api/media/robots.txt` | 404 |
| `sci-A03` | `/api/media/.../2023/06/%2e/Struktura-…jpg` | **200, sha IDENTYCZNY z A01** ⇒ serwer **dekoduje `%2e` i normalizuje segmenty** |
| `sci-A04` | `/api/media/wp-content/%2e%2e%2fwp-content/...jpg` | 404 |
| `sci-A05` | `/api/media/wp-content/..%2fwp-content/...jpg` | 404 |
| `sci-A06` | podwójne kodowanie `%252e%252e%252f…` | 404 |
| `sci-A08`–`A14` | `readme.html`, `wp-config.php` (głęb. 0–2), `wp-config-sample.php`, `wp-includes/version.php` | **404** |
| `sci-A12` | `%2e%2e%2f`×3 + `wp-config.php` | **400 / 150 B `text/html`** — jedyna odpowiedź inna niż 404 w całej macierzy |
| `sci-A07`, `sci-A15` | `license.txt`; `%2e%2e%2f`×4 + `etc%2fhostname` | **timeout 15 s** (nie reset, nie 404) |

Werdykt po run1: **dekodowanie procentów jest, ucieczki z katalogu mediów nie ma** (0 plików spoza
`wp-content`). Zostały trzy zjawiska nierozstrzygnięte: timeout na `license.txt`, timeout na
`etc%2fhostname` i `400` przy trzech poziomach — domykają je RAWPATH-002 i RAWPATH-003 (§6.3, §6.4).
**Nie ma zgłoszenia i nie będzie**, dopóki nie pojawi się plik spoza katalogu mediów.

**b) 116sos.pl WRÓCIŁ i ma coś, czego nikt nie zmierzył** (Gemma-B i `5ed750ef` przerwali przez 502):

| próba | wynik |
|---|---|
| `sos-D01` `/` | 200 `text/html` 103 227 B; nagłówek **`Access-Control-Allow-Origin: https://info-trace.116sos.pl`**; `Set-Cookie: stickounet`×2 |
| `sos-D02` `/api/fetch-cookie-hash` | **200 `application/json` 30 B: `{"cookieHash":"6a9963b75ab63"}` — bez uwierzytelnienia** |
| `sos-D03` `/api/centres-search` | 200 `application/json` **13 306 B** z adresami placówek (m.in. Sławno, ul. Gdańska 18A, 76-100) |

To jest **nowy lead zespołu** (H14 u `5ed750ef` był „niesprawdzony"). RAWPATH-002 rozstrzyga, czy
`cookieHash` jest stały, czy pochodną naszego własnego ciastka (bez wpływu → zamykamy), oraz czy
`centres-search` oddaje pola osobowe (schemat kluczy **bez wartości** — dane zostają na serwerze).
Uwaga formalna: `info-trace.116sos.pl` z nagłówka ACAO jest **subdomeną poza literalem §5** — nie
testuję jej bez interpretacji organizatora (tak samo jak `www.nask.pl`).

**c) HIVE — potwierdzone drugim, niezależnym kanałem** (dokładnie te same ciała, co u Gemmy-B):
`/api/v1/users/1` → **405** `{"detail":"Method Not Allowed"}`; `/api/v1/projects/` → **401**
`{"detail":"Not authenticated"}`; `/api/v1/register` i `/api/v1/openapi.json` → **404**
`{"detail":"Not Found"}` (identyczny sha `37ec4665…`). Kontrola dostępu na poziomie routera działa;
rejestracji nie ma ⇒ IDOR/BAC czeka na konto od organizatora.

### 6.3 Przebieg RAWPATH-002 (10 prób, 1,0 req/s, 10,94 s, **0 kandydatów**)

| próba | wynik | rozstrzygnięcie |
|---|---|---|
| `sos-F01/F02/F03` `/api/fetch-cookie-hash` | 3 × 200 `application/json` 30 B, **sha256 ciała IDENTYCZNY** (`31345c45…`), wartość `{"cookieHash":"6a9963b75ab63"}` | **wartość STAŁA** — nie pochodna ciastka `stickounet` (serwer ustawia je na nowo przy każdym żądaniu). Brak wpływu ⇒ klasa wykluczona (informacja bez danych wrażliwych). **Lead H14 (`5ed750ef`) ZAMKNIĘTY jako negatyw** |
| `sos-F04` `/api/centres-search` | 200 JSON 13 306 B, **28 kluczy**: `address.{apartment,building,city,postcode,street,voivodeships}`, `canSleep`, `centreAimedTo`, `centreSupports`, `email`, `geoCords.{lat,lon}`, `id`, `name`, `open24`, `ops`, `phone`, `scopeOfHelp`, `specialist`, `updatedAt`, `webPage`, `totalItems`, `lastPage` | katalog **placówek pomocowych** (dane instytucjonalne, ta sama wyszukiwarka działa w publicznym SPA). Schemat zapisałem **bez wartości**. Zostaje jedno zadanie dla usera: porównać `totalItems` z liczbą placówek w UI (§7 L3) |
| `sos-F05` `/api/announcements` | 200 JSON 603 B, klucze `[].{type,content,pages}` — publiczne newsy | negatyw |
| `sos-F06` `/api/og-image` | 200 `image/jpeg` 16 264 B (statyczny OG, bez parametru URL) | negatyw |
| `sci-G01` `/api/media/license.txt`, timeout 40 s | **404 w 584 ms** | timeout 15 s z run1 był **przejściowy**, nie „wolnym upstreamem" — wpis wyjaśniony |
| `sci-G02` `/api/media/wp-content/%2e%2e/wp-content/uploads/...jpg` | **200, sha256 IDENTYCZNY z kontrolą `G03`** (`febfe524…`) | zakodowane kropki + **literalny** separator są rozwijane → **albo nginx, albo aplikacja**. Sam ten fakt NIE jest podatnością (patrz §6.4) |
| `sci-G04` `%2e%2e%2f`×3 + `wp-config.php` | 400 / 150 B; ciało: **`400 Bad Request` … `nginx`** | ucieczkę odrzuca **brzeg (nginx)**, nie aplikacja — ochrona działa |

### 6.4 Przebieg RAWPATH-003 (7 prób, 7,28 s) — **rozstrzygnięcie: NIE ma podatności**

Pytanie brzmiało: czy identyczny sha256 w `G02` to dowód prymitywu trawersalu w aplikacji, czy
tylko normalizacja nginx przed proxy. Zaprojektowałem dwie próby, które to rozróżniają:

| próba | ścieżka | wynik | co z tego wynika |
|---|---|---|---|
| `sci-H02` kontrola celu | `/robots.txt` | 200 `text/plain` 73 B, sha `43263c2a…`, treść `User-agent: * / Disallow: /api/ / /_next/ / /node_modules/` | punkt odniesienia dla ucieczki |
| `sci-H03` **dyskryminator warstwy** | `/api/media/wp-content/%252e%252e/wp-content/uploads/...jpg` | **404** | nginx dekoduje **raz**, więc po jego stronie zostaje literal `%2e%2e` i nie normalizuje; aplikacja **nie dekoduje drugi raz**. ⇒ `G02` (200, identyczny sha) to **normalizacja nginx**, NIE prymityw w aplikacji |
| `sci-H04` ucieczka, separatory literalne | `/api/media/%2e%2e/%2e%2e/%2e%2e/%2e%2e/robots.txt` | **`RemoteDisconnected`** — brzeg zrywa połączenie | ucieczka blokowana (zgodne z obserwacją Gemmy-B „traversal → reset WAF") |
| `sci-H05` ucieczka, separatory zakodowane | `/api/media/%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2frobots.txt` | **`RemoteDisconnected`** | jw. |
| `sci-H06` ucieczka 3 poziomy, cel wrażliwy | `/api/media/wp-content/%2e%2e/%2e%2e/%2e%2e/wp-config.php` | **404 / 17 524 B `text/html`** = standardowa strona 404 aplikacji | nginx zwinął `..` i **zclampował** do korzenia; aplikacja oddała zwykłe 404. Żadnego pliku |
| `sci-H07` ucieczka do OS, cel nieszkodliwy | `/api/media/%2e%2e/…×6/etc/hostname` | **`RemoteDisconnected`** | jw. |

**Werdykt końcowy dla `science.nask.pl/api/media/` (22 próby w 3 przebiegach):**
`%2e` jest dekodowane i normalizowane przez **nginx**, aplikacja **nie** dekoduje drugi raz
(H03 = 404), każda próba wyjścia poza poddrzewo mediów kończy się **zerwaniem połączenia**
(H04/H05/H07), **nginx 400** (G04) albo **404 aplikacji** (H06, A08–A14). **Ani jeden plik spoza
`wp-content` nie został podany.** Trop zamknięty jako negatywny, z mechanizmem — nie wracamy.
Zgłoszenia nie będzie: „ten sam plik pod innym URL-em" bez odczytu spoza katalogu to scenariusz
teoretyczny, wykluczony §8 (i odrzucalny).

Przy okazji: `Disallow: /node_modules/` w robots.txt to wskazówka konfiguracyjna, nie znalezisko —
listing katalogów bez danych wrażliwych jest wprost wykluczony.

**Reprodukcja 1:1 (run 4, `rawpath-003-run4.json`, 6,55 s):** te same 7 prób powtórzone drugim
przebiegiem dały **identyczne statusy, rozmiary i sha256 w 7/7 przypadkach**; jedyna różnica to
etykieta `/robots.txt` (`CANDIDATE-PLAINTEXT-FILE` → `public-root-file`), czyli skutek mojej
korekty #30 — a nie zmiany po stronie celu. Wszystkie trzy próby ucieczki znów = zerwanie
połączenia, `H03` znów = 404, **0 kandydatów**. Wynik negatywny jest więc odtwarzalny, nie
jednorazowy — i to jest warunek, żeby w ogóle wpisać „zamknięte" do rejestru.

### 6.5 Korekty własne #28 i #30 (moje błędy, znalezione na moich danych)

* **#28** — klasyfikator oznaczał stronę główną `dyzurnet.pl` i jej soft-404 jako `blocked-waf-200`,
  bo znacznik WAF łapał samo słowo „cloudflare" w ciele. Rozdzieliłem `WAF_VENDOR` (informacyjny)
  od `WAF_BLOCK` (komunikat odmowy) i ustawiłem kolejność: **soft-404 przed WAF**. Dodatkowo
  `decide_preview()`: małe ciało błędu (status ≥ 400, ≤ 1024 B) jest zapisywane zawsze — inaczej
  `sci-A12` (400/150 B) był ślepym wpisem, a to właśnie ono ujawniło nginx jako warstwę blokującą.
* **#30** — `/robots.txt` (200 `text/plain` 73 B) dostał werdykt `CANDIDATE-PLAINTEXT-FILE`, bo reguła
  „mały text/plain = kandydat" nie znała publicznych plików korzenia. Dodałem `BENIGN_ROOT_FILE_RE`
  (robots/security/sitemap/manifest/favicon/ads/humans/crossdomain) **tylko** dla ścieżki bez
  `..`/`%2e` — ten sam plik podany przez trawersal nadal jest kandydatem (test to asserts).
* **5 + 8 testów regresyjnych** odtwarza dokładne rekordy z run1/run2/run3. Razem **66 testów OK**,
  selftest **11 grup OK**.

---

## 7. Nowa kolejność poranka (RUNBOOK rev 2 — skrót; pełny: `RUNBOOK-REV2-20261104.md`)

| # | co | kto | blokada |
|---|---|---|---|
| **L0** | rejestracja `hack.cert.pl` + akceptacja regulaminu platformy i konkursu NASK; **wniosek do organizatora o konto testowe HIVE**; **pytanie o zakres `www.nask.pl`** (apex `nask.pl` daje 302 na `www` ⇒ cały Tier-1 host jest praktycznie nietestowalny bez interpretacji) | **user** (15 min) | — |
| **L1** | `sendForm` w przeglądarce: najpierw legalne zgłoszenie testowe z linkiem do **własnego** kontrolera (SSRF z odczytem — sam DNS jest wykluczony), potem walidacja typów plików (SVG/PNG z payloadem → stored XSS w panelu analityka) | **user + moje payloady** | **jawne GO** (zmiana stanu u operatora + reCAPTCHA v3) |
| **L2** | ~~`science/api/media`~~ — **ZAMKNIĘTE** po 22 próbach w 3 przebiegach: `%2e` normalizuje nginx, aplikacja nie dekoduje drugi raz (H03 = 404), ucieczka = zerwanie połączenia / nginx 400 / 404 aplikacji, **0 plików spoza `wp-content`** | ja (Actions) — zrobione | — |
| **L3** | `116sos` — **ZAMKNIĘTE**: `fetch-cookie-hash` = wartość stała (3 próbki, identyczny sha256), `announcements` = publiczne newsy, `og-image` = statyczny JPEG, `centres-search` = katalog placówek (28 kluczy). **Zostaje 2 minuty usera**: porównać `totalItems` z `/api/centres-search` z liczbą placówek w publicznej wyszukiwarce — jeśli API oddaje więcej (placówki niepubliczne / dane opiekunów), to klasa 3, Tier 2 do 10 000 zł | user (porównanie) | — |
| **L4** | HIVE z kontem organizatora: IDOR A↔B (canary, `id±1..5` **tylko własne zasoby**, mass assignment na własnym profilu), `/admin/logs` (guardy tylko klienta wg `5ed750ef`) | user + ja | konto od organizatora |
| **L5** | mapa API z bundli: `zglos` (13+ chunków flight-data), `dyzurnet` (app-router), `dns.pl` (Drupal `domain-browser`) → `bundle_scan.py` | ja | — |

**Nie robimy** (zmierzone, zamknięte): `/podglad-pdf`, `download-file` (bm), `downloadFile` enum,
`/_next/image`, CORS, CVE-2025-29927, SQLi przez GET, `.env`/`.git` (2× zmierzone), refleksje
w wyszukiwarkach, takeover bez PoC, DoS/obciążenie (dyskwalifikacja), hosty spoza §5,
**`science/api/media` traversal (22 próby, 3 przebiegi — mechanizm opisany w §6.4)**,
**`116sos/api/fetch-cookie-hash` (wartość stała)**, **`/api/announcements`, `/api/og-image`**.

---

## 8. Ryzyka zespołowe, których nikt wcześniej nie spisał

1. **Skumulowane tempo.** Sześć sesji × 4–4,5 req/s na te same hosty: regulamin limituje
   „narzędzia automatyczne do 5 req/s", a sposób sumowania między podmiotami nie jest jednoznaczny
   (`a450b00f` podnosi to samo). U `incydent.cert.pl` Gemma-A dostała **429**. **Zasada: 1 req/s na
   sesję + jedna grupa `concurrency` + wpis do rejestru PRZED testem.** Ja ustawiłem 1,0 req/s.
2. **Duplikat wewnętrzny.** Ten sam root cause na dwóch serwisach = jedna wypłata (§7 pkt 9), a dwie
   sesje wysyłające to samo zgłoszenie = ryzyko odrzucenia obu. Stąd mój rejestr jako baza prawdy.
3. **Trzy odrzucone zgłoszenia pod rząd mogą zablokować możliwość zgłaszania** (Gemma-B `IDEAS` §0).
   Wysyłamy tylko z działającym PoC i ręcznym potwierdzeniem (skaner-only jest wykluczone §8).
4. **Runner Actions a AUP GitHub.** Codex odnotował, że istnienie wcześniejszych workflowów Kaggle
   nie jest podstawą do dowolnego użycia runnerów. Nasze użycie to badanie w ramach programu z
   limitem tempa, GET-only, bez masowego fuzzingu — i tak ma zostać.
5. **Zakres.** `www.nask.pl`, `info-trace.116sos.pl`, `panel.dns.pl`, `*.snkom.nask.pl` — poza
   literalem §5. Nie „brak nagrody", tylko problem prawny. Dwa pytania do organizatora (L0) to
   załatwiają.
6. **PTCG na mojej gałęzi.** Workflowy `gauntlet.yml`, `kaggle_poll.yml`, `kaggle_our_replays.yml`
   nadal dokładają `pokemon-agent/kaggle_results/**` (commity `f5c72a9`, `3192d20`, `d820f0e`) i
   zużywają minuty Actions, których teraz potrzebuję na sondy. **Czekam na decyzję usera** —
   rekomenduję wyłączenie (nie zrobiłem tego jednostronnie).

---

## 9. Zgodność — mój ruch 04.11 (log uzupełniony w `REJESTR-LEADS-20261104.md`)

* `fetch_page`: **5 żądań GET** (`dns.pl/.env`, `dyzurnet.pl/server-status`,
  `zglos-dezinformacje.nask.pl/server-status`, `science.nask.pl/api/media/%252e%252e%252frobots.txt`,
  `science.nask.pl/api/media/robots.txt`) — sekwencyjnie, ≪ 5 req/s, tylko hosty §5, zero zmiany stanu.
* `curl` z sandboxa: **2 próby** (zakończone kodem `000` — TCP zablokowane, żądania nie wyszły).
* Actions run1 (`41814163117`, raport `rawpath-001-run1.json`): **35 żądań GET**, 1,0 req/s,
  min. odstęp 1,000 s, 70,13 s, hosty: `science.nask.pl`, `dns.pl`, `dyzurnet.pl`,
  `zglos-dezinformacje.nask.pl`, `dataannotation.pllum.org.pl`, `bezpiecznymiesiac.pl`, `116sos.pl`.
* Actions run2 (`41814928560`, raport `rawpath-002-run2.json`): **10 żądań GET**, 1,0 req/s,
  min. odstęp 1,000 s, 10,94 s, hosty: `116sos.pl`, `science.nask.pl`.
* Actions run3 (raport `rawpath-003-run3.json`): **7 żądań GET**, 1,0 req/s, min. odstęp 1,000 s,
  7,28 s, host: `science.nask.pl`.
* Actions run4 (`41816135053`, raport `rawpath-003-run4.json`): **7 żądań GET** — reprodukcja
  RAWPATH-003 po poprawce klasyfikatora; 1,0 req/s, 6,55 s, host: `science.nask.pl`.
* **Razem mój ruch 04.11: 59 żądań GET do celów w 4 przebiegach + 5 przez `fetch_page` + 2 próby
  `curl` zablokowane w sandboxie.** Zero POST/PUT/DELETE. Zero hostów spoza §5. Zero prób obejścia limitu
  (najmniejszy zmierzony odstęp 1,000 s przy sufcie regulaminowym 0,2 s). Zero użycia znalezionych
  poświadczeń. Zero zgłoszeń (nic nie spełnia progu PoC). Władysławowo nietknięte. Każde żądanie
  ma rekord w `nask/reports/` (status, typ, rozmiar, sha256, czas, błąd) — także błędy transportu.

## 10. Moje korekty własne (ciągnione z rejestru 25 pozycji)

* **#26** RUNBOOK L3 „macierz uploadu automatem" → **niemożliwe**: reCAPTCHA v3 + żądanie zapisujące;
  tylko przeglądarka usera i jawne GO.
* **#27** RUNBOOK L1/L2 „załóż dwa własne konta w HIVE" → **niemożliwe**: brak publicznej rejestracji
  (404 w dwóch kanałach); konto wyłącznie od organizatora.
* **#28** klasyfikator `rawpath`: słowo „cloudflare" ≠ blokada WAF; soft-404 musi mieć pierwszeństwo
  przed znacznikiem dostawcy (patrz §6.5) — naprawione + 5 testów regresyjnych.
* **#29** mój nocny wniosek „500 bez danych na `oad/podglad-pdf` = klasa wykluczona" był poprawny,
  ale **niepełny**: `zglos-dezinformacje` zwraca 500 na *każdą* obcą ścieżkę (App Router), więc na
  tym brzegu kod 500 nie niesie informacji wcale. Uzupełniam wpis w rejestrze.
* **#30** klasyfikator `rawpath`: publiczny `/robots.txt` nie jest kandydatem (`public-root-file`),
  ale **ten sam plik podany przez trawersal jest** — reguła działa tylko dla ścieżki bez `..`/`%2e`
  (§6.5, 8 testów regresyjnych z run2/run3).
* **#31 (metoda)** — mój nocny pomysł „SSRF tylko jeśli UI odbija podgląd linku" był za wąski:
  równie dobrym dowodem jest **żądanie do własnego kontrolera z odczytem treści**, a sam fakt
  pobrania bez odczytu jest wykluczony (blind SSRF). Zapisuję w runbooku L1 krok 1.1.
* **#32 (metoda)** — nocny wpis „dns.pl: publiczny whois + `sites/default/files`" traktowałem jako
  powierzchnię; pomiar pokazał, że `dns.pl` oddaje **stronę główną z kodem 200** na każdą obcą
  ścieżkę, wstrzykując licznik `_event_transid` i odbijając ścieżkę w kotwicach. Bez normalizacji
  tych dwóch rzeczy każde porównanie bajtowe na tym hoście jest fałszywym trafieniem (§5.1).
