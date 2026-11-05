# NASK Bug Bounty 11/2026 — pakiet roboczy

Katalog roboczy do konkursu [hack.cert.pl](https://hack.cert.pl). Wszystko oparte na
przeczytanym regulaminie (11 stron) i **własnych pomiarach** z 2026-11-03.

## Czytaj w tej kolejności

| # | plik | co zawiera |
|---|---|---|
| 1 | `01-STRATEGIA.md` | pełna strategia: mapa celu, gdzie leżą pieniądze, kalibracja oczekiwań |
| 2 | `02-REKONESANS-20261103.md` | zmierzone dane: 12 domen, nagłówki, tech, wynik negatywny, hosty poza zakresem |
| 3 | `03-PLAN-DZIALANIA.md` | plan dzień po dniu z konkretnymi testami |
| 4 | `04-REJESTR-ZGLOSZEN.md` | rejestr: co wysłane, co w toku, co sprawdzone i puste |
| 5 | `05-REGULAMIN-wyciag.md` | najważniejsze paragrafy przepisane z PDF |
| 6 | `06-narzedzie-naskrecon.zip` | kod źródłowy (Rust + Rayon, 16 testów) + workflow GitHub Actions |
| 7 | `07-log-rekonesansu.jsonl` | surowe wiersze z przebiegu (host, ścieżka, kod, bajty, tech) |

## Trzy liczby, które streszczają sytuację

1. **100 000 zł** puli na **12 domen** — NASK spodziewa się kilkunastu–kilkudziesięciu zgłoszeń, nie jednego zwycięzcy.
2. **204 żądania, zero realnych ekspozycji** — powierzchnia ataku nie jest w plikach konfiguracyjnych.
3. **5 aplikacji** ma sens: `zglos-dezinformacje`, `dataannotation.pllum` (HIVE), `oad`, `dyzurnet`, `dns.pl`.

## Najkrótsza wersja planu

Zarejestruj **dwa własne konta** na HIVE i szukaj IDOR-a. To najczęstsza realna luka
w aplikacjach pisanych pod deadline, nie wymaga exploitów, a płaci 9 000–20 000 zł.
Reszta to kolejność w `03-PLAN-DZIALANIA.md`.

## Ostrzeżenia, których nie wolno zignorować

- Zakres to **dokładnie** 12 domen z §5. `gitlab.snkom.nask.pl`, `nextcloud.snkom.nask.pl`,
  `zakupy.nask.pl`, `taskmanagement.nask.pl`, `secret.eadministracja.nask.pl` — **poza konkursem**,
  mimo że należą do NASK. Testowanie ich to problem prawny, nie „brak nagrody".
- **Max 5 req/s.** Narzędzie ma sufit 4,5 i odmawia startu wyżej.
- **Zero testów obciążeniowych** — natychmiastowa dyskwalifikacja (§8 poz. 10).
- **PoC obowiązkowe.** Wynik skanera bez ręcznego potwierdzenia jest odrzucany (§8 poz. 14).

## Zastrzeżenie

Rekonesans był **pasywny**: Certificate Transparency, nagłówki HTTP, treść stron publicznych.
Nie wykonano żadnego testu atakującego, nie założono konta, nie wysłano payloadu.
Wszystko, co wymaga logowania, jest w planie — do wykonania ręcznie.

## Aktualne na 04.11.2026 (po przeglądzie 6 gałęzi zespołu)

| plik | co zawiera |
|---|---|
| `PRZEGLAD-GALEZI-20261104.md` | przegląd 6 gałęzi + repo NASK: co przejmuję, co **prostuję z dowodem** (m.in. 23 „interesting" z run007 = szum), co wnoszę; wyniki 3 przebiegów RAWPATH (52 żądania) |
| `RUNBOOK-REV3-20261104.md` | **obowiązująca** kolejność L0–L5 (L1/L2 HIVE zablokowane — brak publicznej rejestracji; L3 sendForm tylko z przeglądarki usera i po GO) |
| `REJESTR-LEADS-20261104.md` | baza prawdy leadów: L1–L12 ze statusem i dowodem + log wszystkich żądań (noc + dzień) |
| `PRZEGLAD-GALEZI-20261104-FALA2.md` | **fala 2**: commity 10:14–10:55 + 7 nowych plików Drive (20 razem) — H10 obalony, HIVE zaproszeniowy, mwdb 2.20.0, PowerBI embed (URL), 3 nowe formularze (w tym jeden **wykluczony decyzją własną**), defekt w `har_triage` znaleziony przez uruchomienie |
| `tools/vendor/a450b00f/` | przejęty offline-triage HAR z dwóch własnych kont (+ `PROWENIENCJA.md`: commit, 1/11 FAIL u źródła, nasza 1 poprawka, 11/11 OK) |
| `tools/rawpath.py` + `tools/test_rawpath.py` | sonda o **surowej ścieżce** (bez normalizacji klienta), klasyfikator z dowodu, schemat kluczy JSON bez wartości, redakcja sekretów; 52 testy + selftest 11 grup |
| `run/RAWPATH-00{1,2,3}.json` | plany przebiegów (35 + 10 + 7 prób) z uzasadnieniem i warunkami odrzucenia |
| `reports/rawpath-00{1,2,3}-run*.json` | rekordy każdego żądania: status, typ, rozmiar, sha256, czas, znaczniki, błędy |
| `.github/workflows/nask-rawpath.yml` | bramka offline (testy) → przebieg 1,0 req/s → audyt zgodności → commit raportu |

## Aktualne na 05.11.2026 (run 9–12 + przegląd repo NASK)

| plik | co zawiera |
|---|---|
| `WYNIKI-RUN9-RUN10-20261105.md` | **najnowszy stan**: 67 żądań GET w Actions (run 9 = 31, run 10 = 22, run 11 = 7, run 12 = 7), tabela wszystkich son z dowodami, 8 grup rozstrzygnięć (A–H), mechanizm przechwycenia brzegowego dns.pl, zamknięcia L5/L9/L18/L20/L22 + nowe L24–L36, korekty #43–#51; §12 = run 11, §13 = run 12 (**kandydat `PII_EMAIL: 1596` rozstrzygnięty jako publiczny katalog instytucji i zatrzymany bez enumeracji**, 24 trasy 116sos z `_buildManifest.js`, 69 tras oad/en bez PowerBI, `/statystyki/*` na dns.pl); run 11: `/api/sendForm` → 405 bez `Allow`, **326 tras publicznych 116sos** w tym `/osrodki-pomocowe` (drugi kanał dla L9), nawigacja oad bez PowerBI, UI dns.pl linkujące `deleted_domains.txt`, świeży buildId |
| `PRZEGLAD-REPO-NASK-20261105.md` | przegląd gałęzi i repo `peteraangelic-pixel/NASK` z 05.11 (commit `b2cf80a4`): co przejmuję (`har_triage`, mapa `hack.cert.pl`), co prostuję (defekt ich `bundle_scan.py` = kopia mojej wersji sprzed korekty #33, `class: "8.9"` = CVSS nie klasa §8, sweep `downloadFile?fileId=` już zamknięty, `ctf.hack.cert.pl` = konflikt zakresu) |
| `run/RAWPATH-00{4…9}.json` | plany przebiegów: 129 sond na assety JS (run 7), 4 kontrole (run 8), 31 (run 9), 22 rozstrzygnięcia (run 10), 7 (run 11), 7 (run 12 — wykonany: `/osrodki-pomocowe`, propsy Next.js z kontrolą, `_buildManifest.js`, `/en`, `/raporty`, `/search-results`) |
| `reports/rawpath-00{4..9}-run{7..12}.json` | surowe rekordy żądań ze statusem, typem, rozmiarem, sha256, licznikami PII i odciskami sekretów (**bez wartości** — korekta #33) |
| `reports/mine-rawpath-00{4,6,7,8,9}-run{7,9,10,11,12}.json` | analiza pobranych ciał: trasy, hosty, parametry, sekrety (odciski), formaty ID — m.in. **71 tras klienta HIVE**, 91 literałów `dns.pl`, 8 domen instytucji w odpowiedzi `centres-search` |
| `reports/logs-run{7,8,9,10}/` | logi audytu zgodności z Actions (tempo, hosty, brak wzorców kluczy) |
| `tools/rawpath.py` (v. po korekcie #43) | liczniki PII jako liczby + wyciszanie podglądu + werdykt `CANDIDATE-PII-IN-RESPONSE`; selftest **13 grup** |
| `tools/bundle_scan.py` (po korektach #44/#45/#48) | literały ścieżek (`paths`), hostów (`hosts`), sekrety w query-stringu, `looks_like_credential()`; 3,9 MB / 0,58 s / rdzeń; **92 testy OK** |
