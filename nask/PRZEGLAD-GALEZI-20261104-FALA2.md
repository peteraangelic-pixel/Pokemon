# Przegląd fala 2 — commity 10:14–10:55 + Google Drive (20 plików)

Autor: Arena `c87f7a48`. Uzupełnienie `PRZEGLAD-GALEZI-20261104.md` (fala 1, commity do ~10:13).
Wszystkie SHA, daty i liczby pobrane dziś przez GitHub API / connector Drive — nie z pamięci.

---

## 0. Co nowego od fali 1

| repo | gałąź | nowe commity | co istotnego |
|---|---|---|---|
| Pokemon | `arena/7911f950-pokemon` | `aa115b05` 10:15, `641abeff` (run009), `96c7f816` 10:20, `f8ebe515` (run010), **`ca0f3cc9` 10:28** | **RAPORT NOCY: 256 sond w 7 przebiegach, 0 podatności**; normalizacja baseline (`_event_transid`), wykrywanie refleksji, fala 6 = specyfika CMS per host (Wagtail/Drupal/WP/Nuxt/Next) |
| Pokemon | `arena/a450b00f-pokemon` | **`bb17ccdc` 10:14** | poprawka testów `har_triage` (długość ID, asymetria kont) — patrz §6: **na tym commicie 1/11 testów FAIL** |
| Gemma-konkurs | `arena/c4eeb067` (Gemma-B) | `e726f677` 10:50, `076f93fc` 10:51, **`e46c9169` 10:55** | `PRZEJETE-Z-GALEZI` (171 ln, inwentarz z prowieniencją commit→plik), `SYNTEZA-GALEZI` (69 ln), **`WERYFIKACJA-RUNDA7`** (24 żądania): H10 obalony, `download-file` i `cookieHash` domknięte |
| Gemma-konkurs | `arena/6d081d52` (Gemma-A) | `513b3949` 10:14, `ed37f4fc` 10:15, `29a1ff44` 10:31, **`48c2b217` 10:32** | przegląd 6 gałęzi + rejestr zamkniętych hipotez; sonda S9 (Wagtail/Django `/api/v2`); **przebieg 4 rozstrzyga mwdb = 2.20.0** |
| NASK | `arena/a29ca234-nask` | **`eb234af8` 10:15** | `nask-lab`: `nasktriage` + `naskhunt` + `naskrecon` w jednym (scope guard, limiter 5 req/s, HAR triage) |
| Smak-Domu | `arena/5ed750ef` | brak nowych (ostatni `6fd86e30` 10:12) | omówiony w fali 1 |
| **Drive** | folder `1tWcRm79xeYQslPACYOagZ0bmhuKnlBMo` | **20 plików (było 13)** | nowe: `13-STRATEGIA-5-PROGRAMOW.md`, `14-coordinator-findings-20261103.json`, **`15-PRZEGLAD-GALEZI-2026-11-04.md`**, **`16-MAPA-ENDPOINTOW-2026-11-03.md`** (9,7 kB), `17-IDEE-ZAROBEK`, `18-PLAN-NOCNY`, **`19-nask-noc-20261104-komplet.zip`** (3,18 MB, 10:51) |

Zipa `19-…` nie rozpakowałem: sandbox nie ma wyjścia do `drive.google.com`, a connector zwraca
binaria base64 do kontekstu (3,18 MB → ~4,2 MB) — nieproporcjonalne. Cztery nowe pliki `.md`
z tego samego wrzutu (10:51) zawierają jego wnioski; przeczytałem 15/16/17.

---

## 1. Trzy rzeczy zamknięte dziś rano przez innych (zmieniają mój runbook)

1. **H10 OBALENY** — „`/admin/logs` w HIVE ma guardy tylko klienta" (wycena `5ed750ef`:
   4 500–10 000 zł). Pomiar Gemmy-B (runda 7): `GET /admin/logs` → **200, 713 B, `text/html`**,
   catch-all hostu → **200, 713 B — identyczne**; `GET /api/v1/admin/logs` → **404**
   `{"detail":"Not Found"}`; `GET /api/v1/users/` → **401**. To nie guard kliencki, tylko
   powłoka SPA serwowana na każdą nieznaną ścieżkę. **⇒ krok 4.3 mojego runbooka rev2 usunięty
   (korekta #34).** Nie ma na czym budować budżetu.
2. **HIVE = dostęp zaproszeniowy, potwierdzony przez usera** — `7911f950` raport nocy §4:
   „dostęp **zaproszeniowy** (potwierdzone przez użytkownika: trzeba być członkiem organizacji)".
   To nie jest przejściowy brak rejestracji, tylko model dostępu ⇒ klasy 9/10/13 (IDOR/BAC/mass
   assignment) są w NASK **nieosiągalne bez konta od organizatora**. Mój L0 pkt 2 (wniosek) zostaje,
   ale z tą świadomością: to prośba o wyjątek, nie o odblokowanie rejestracji.
3. **`mwdb.cert.pl` `server_version` = 2.20.0** (Gemma-A przebieg 4 + koordynator w Drive 15)
   ⇒ poprawka XSS w Rich attributes (#1272/#1274) **wdrożona** ⇒ wątek zamknięty jednym żądaniem,
   10 minut pracy usera zaoszczędzone. (Poza moim programem — odnotowuję, bo to samo konto platformy.)

**Pozostałe domknięcia z fali 2 (nie wracamy):** `centres-search` **ignoruje `q` i `id`** (13 306 B
za każdym razem ⇒ wszystkie wcześniejsze „testy SQLi na `q`" mierzyły szum); `pllum` Nuxt
`_draft=true` → `[]` (2 B); Wagtail `/api/v2/*` × 7 hostów → 308 → 404; Drupal `?_format=json`,
`?_format=hal_json`, `/jsonapi/node/page`, `/user/login`, **`/user/register`**, `/core/install.php`
→ 404 (rejestracja zamknięta, JSON:API wyłączone); WP `?rest_route=/wp/v2/posts` → **HTML**
(162 kB / 103 kB), `xmlrpc.php` i `wp-login.php` → 404; `/_next/data` na `116sos` działa, ale to
`pageProps` **publicznej** strony (8 256 B); jedyna refleksja XSS (`bezpiecznymiesiac/?s=`) trafia
do payloadu RSC jako **zescapowany string JSON** → wykluczone §8 (content injection bez JS);
`dyzurnet/api` → 404 + 38 981 B (catch-all App Routera); `X-Forwarded-Host` na `fetch-cookie-hash`
→ bez wpływu (brak wektora cache poisoning); `download-file` na `bezpiecznymiesiac` — prefiks
„elastyczny" (`%2Fmedia%2F…`, `/MEDIA/…`, `media/…` bez ukośnika → **ten sam plik** 540 927 B),
ale każdy segment `.`/`..` → 400 ⇒ elastyczność **nie poszerza dostępu**.

---

## 2. Niezależne potwierdzenie moich wyników z fali 1

* **`cookieHash` = stała.** Gemma-B: wartość `6a9963b75ab63` **identyczna wczoraj i dziś, dla dwóch
  żądań bez ciasteczka**. Ja: 3 próbki w jednym przebiegu, identyczny sha256 całego ciała
  (`31345c45…`), przy nowym `Set-Cookie: stickounet` za każdym razem. Dwa kanały, ten sam wniosek
  ⇒ lead H14 zespołu `5ed750ef` zamknięty definitywnie.
* **`dns.pl` `_event_transid`.** `7911f950` znalazł i naprawił **dokładnie ten sam** mechanizm
  fałszywych trafień, który opisałem w fali 1 §5.1 (ich `normalize()`: ciągi cyfr → `#`, plus
  druga poprawka: błąd priorytetu operatorów `a || b && c && d` przepuszczał litery). W raporcie
  nocy odnotowali: „Równoległa sesja (`arena/c87f7a48-pokemon`) robi to samo przez surowe gniazdo".
  Zbieżność dwóch sesji ⇒ mechanizm uznaję za ustalony.

---

## 3. Co koryguję w ich nowej wiedzy

**(a) „Trawersal w ścieżce jest niemierzalny tym klientem"** (`7911f950` raport nocy §3.3;
Gemma-B: „nasz `ureq` zachowuje się tak samo; dlatego traversal testujemy w query/parametrze,
nie w ścieżce") — **nieaktualne od 10:26**. Zmierzyłem to surowym gniazdem (`rawpath.py`):
22 próby w 3 przebiegach + reprodukcja 1:1 w przebiegu 4. Wynik: `%2e` dekoduje i normalizuje
**nginx**; aplikacja **nie dekoduje drugi raz** (`%252e%252e` + literalny `/` → **404**);
ucieczka → `RemoteDisconnected` ×3 / nginx **400** / **404 aplikacji**; **0 plików spoza
`wp-content`**. Trop jest więc **zamknięty negatywnie z mechanizmem**, nie „niemierzalny".
Konsekwencja dla zespołu: nie planujcie trawersalu w ścieżce na `science.nask.pl` — jest zmierzony.

**(b) `/admin/logs` → „ląduje na `/login`"** (Gemma-B `SYNTEZA` §2) versus **200/713 B**
(Gemma-B `WERYFIKACJA-RUNDA7` §1) — dwa różne opisy tego samego hosta w dwóch dokumentach
tej samej sesji. Mój nocny pomiar (`REJESTR-LEADS` wiersz 12) dotyczy **korzenia**:
`dataannotation.pllum.org.pl/` → **302 → `/login`**. Spójny model routingu HIVE:
korzeń → 302 `/login`; `/login` i każda nieznana ścieżka → 200 shell 713 B. Atrybucja
„c87 (302→/login)" przy haśle `/admin/logs` w syntezie `5ed750ef` była **za ciasna** — to był
korzeń, nie `/admin/logs`. Prostuję, bo na tej atrybucji ktoś mógłby zbudować hipotezę
„panel istnieje, tylko guarduje".

**(c) „`116sos.pl` leży od ~23:00"** — powtarzane w czterech raportach jako stan trwały.
Gemma-B słusznie to prostuje; ja zmierzyłem rano cztery endpointy (host żyje). **Wniosek
metodyczny dla rejestru: stany awaryjne muszą mieć datę ważności**, inaczej cztery sesje
dziedziczy nieaktualny fakt i planuje wokół niego pracę.

**(d) „`hack.cert.pl` = IDOR na IBAN, cel #1"** (Drive 16 i 17) — Gemma-B odrzuca: „nie nasz
program". **Zgadzam się z Gemmą-B.** `hack.cert.pl` jest w Tier 1 programu **CERT Polska**, nie
NASK PIB; mieszanie programów w jednym rejestrze zgłoszeń to prosta droga do odrzucenia.
Decyzja o wejściu w inny program należy do usera (§7).

**(e) Drive 16: „Portal konkursu jest w zakresie T1 (`*.cert.pl`)"** — nieprecyzyjne.
Sprawdziłem w pełnym PDF (`NASK@codex/multi-program-lab`, `research/sources/cert-polska-terms-2026-11.txt`,
§5): `hack.cert.pl` jest **literałem w Tier 1**, Tier 2 to `*.cert.pl` i `ctf.hack.cert.pl`,
a **`*.hack.cert.pl` jest wprost WYKLUCZONE** (§5 pkt 2). Różnica praktyczna: `ctf.hack.cert.pl`
jest w konkursie, inne subdomeny `*.hack.cert.pl` — nie.

---

## 4. Co wyciągnąłem z ICH danych (reuse offline, zero nowych żądań do tego kroku)

Źródło: `nask/reports/analysis-run003.json` (1,95 MB, 479 dokumentów, `Pokemon@7911f950`).

1. **PowerBI embed na `oad.nask.pl` — dokładny URL** (w Drive 16 był jako hipoteza, bez URL-a):
   ```
   https://app.powerbi.com/reportEmbed?reportId=470044cf-1a84-4ecb-87f1-7e914afdbb19&autoAuth=true&ctid=95dc45af-07b0-4179-a598-9740073a6e4a
   ```
   Znalezione w `oad.nask.pl/_next/static/chunks/41lk95l8op7nz.js` (34 692 B), obok literałów tras
   `/trendy`, `/about-us`, `/o-nas`, `/news`, `/aktualnosci`, `/media/`, `/_next/image`.
   **Zadanie dla usera (2 minuty, przeglądarka, zero ryzyka):** otworzyć `oad.nask.pl/trendy`
   (albo sam embed) **w trybie incognito** i zobaczyć, CO raport pokazuje.
   * Agregaty/statystyki → zamykamy (najbardziej prawdopodobne).
   * Rekordy z danymi osobowymi albo treściami niepublicznymi bez logowania → **klasa 3 na hoście
     Tier 1** (9 000 / 20 000 zł), dowód = zrzut ekranu + URL + brak sesji.
   * `app.powerbi.com` **nie jest** testowane automatem — to własność Microsoftu, poza §5.
2. **Trzy formularze zmieniające stan, których nikt nie miał w planie** (pole `forms` ich analizy):

   | host (Tier) | formularz | pola | moja ocena |
   |---|---|---|---|
   | `bezpiecznymiesiac.pl` (T2) | **`/ecsm/zglos-inicjatywe/`** | `name`, `description`, … | **wartościowy**: ta sama klasa co `sendForm` (upload / mass assignment / stored XSS w panelu), a mniejsza konkurencja |
   | `science.nask.pl` (T2) | **`/contact`** | `name`, `email`, … | średni: prawdopodobnie tylko mailuje; klasa upload/XSS możliwa, ale wymaga PoC |
   | `116sos.pl` (T2) | **`/otrzymaj-pomoc/formularz`** | `subject`, `description`, … | **WYKLUCZAM ze względów bezpieczeństwa** — patrz niżej |
   | `bezpiecznymiesiac.pl` | `/baza-wiedzy/` | `search` | tylko wyszukiwarka (GET) |
   | `science.nask.pl` | `/search` | `searchPhrase` | refleksja zescapowana (7911) — zamknięte |

   **Dlaczego wykluczam formularz 116 SOS:** to formularz „otrzymaj pomoc" przy telefonie
   zaufania 116 111 / 116 123 dla dzieci i młodzieży w kryzysie. Wysłanie testowego zgłoszenia
   może uruchomić **realną procedurę pomocową** i zająć zasób przeznaczony dla osoby w kryzysie.
   Żaden paragraf regulaminu tego nie zakazuje wprost — i właśnie dlatego nie wolno: §8 wymaga
   realnego wpływu, a wpływ „nasz test opóźnił pomoc dziecku" jest realny i nieodwracalny.
   Wpis w rejestrze: **L16 — wykluczone decyzją własną, nie testujemy nigdy**.
3. **`dns.pl/translations/domainBrowser?locales=pl`** (1 666 B, Symfony/Bazinga) oraz
   `/translations/{delegation,deletedDomainCount,domainCount}` — tłumaczenia zawierają **nazwy pól
   i parametrów** przeglądarki domen. To najtańsza droga do ożywienia `/api/domain-browser/`,
   który bez właściwego parametru daje 404 (`5ed750ef` bieg 4/5). Pobrane w RAWPATH-004.
4. **HIVE: całe SPA w jednym bundlu `assets/index-ClBZuP56.js` = 2,77 MB**, a ich analiza wyciągnęła
   z niego **75 literałów tras** (przy 10 005 dla `dns.pl` i 1 746 dla `oad`). Czyli mapa API HIVE
   **nie została wydobyta** — to luka przebiegu (prawdopodobnie limit odczytu), nie brak danych.
   RAWPATH-004 czyta go w całości (limit 4 MB/żądanie) i przepuszcza przez `bundle_scan.py`,
   żeby w momencie przyznania konta mieć gotową listę endpointów i **formatów ID**
   (sekwencyjny int = tani IDOR, UUID = drogi).
5. **`www.nask.pl` w ich `per_host`** (2 dokumenty, 542 literały tras) — run003 jednak dotknął
   `www` (prawdopodobnie po 302 z apexu). Nie zarzut: pasywne pobranie strony. Ale potwierdza,
   że pytanie o zakres (L10) blokuje **pracę**, nie tylko zgłoszenia — 542 literały tras
   największego portalu Tier 1 leżą odłogiem do czasu odpowiedzi organizatora.

---

## 5. RAWPATH-004: mining 129 bundli JS (10,92 MB) — plan z ich mapy, nie z własnego crawlu

| parametr | wartość |
|---|---|
| plików JS | **129** (9 hostów §5): pllum 28, dns.pl 19, dyzurnet 18, 116sos 15, oad 15, science 12, zglos 11, bezpiecznymiesiac 10, **HIVE 1** |
| suma rozmiarów | 10,92 MB (z ich mapy; limit odczytu 4 MB/plik) |
| tempo | 1,0 req/s sekwencyjnie (regulamin: 5) — **wolniej niż przeglądarka** |
| ciała odpowiedzi | `$RUNNER_TEMP/bodies` → **nigdy do repo**; do repo trafia manifest (id/url/rozmiar/sha256/typ) i analiza |
| analiza | `bundle_scan.py --in DIR --out nask/reports/mine-004-…json` (offline, multiprocessing) |
| guard | krok commitu **odmawia**, jeśli `git status` pokaże cokolwiek poza `nask/reports/` |
| czego NIE robi | zero sond do API, zero POST, zero zgadywania ścieżek paneli, zero hostów spoza §5 |

**Pierwsze podejście (run 5) PADŁO i wiem dlaczego** — to mój błąd, nie celów. W raporcie
`bundle_scan.py` klucz `files` jest **licznikiem** (int), a lista wyników leży pod `results`;
mój krok miningu robił `rows = d.get("files") or d.get("results")` → `for r in 129` →
`TypeError`. Odtworzyłem to lokalnie na dwóch syntetycznych bundlach (`bash -n` na wszystkich
7 blokach `run:` + symulacja audytu), poprawiłem i **dodałem krok diagnostyczny
`if: always()`**, który commituje ogony logów do `nask/reports/logs-run<N>/`. Powód, dla którego
w ogóle musiałem to robić: sandbox sesji nie sięga hosta blobów Actions
(`productionresultssa*.blob.core.windows.net` → `EOF`), więc `gh api .../logs` nie działa —
bez commitowanej diagnostyki porażka przebiegu jest nieodczytywalna. **KOREKTA #37.**

**KOREKTA #33 (mój własny błąd z nocy):** `bundle_scan.py` zapisywał `preview` sekretu =
4 pierwsze + 2 ostatnie znaki wartości. Nawet 6 znaków nie powinno trafić do publicznego repo —
jest **odcisk `sha256[:12]` + długość + entropia** (wystarcza do deduplikacji i do potwierdzenia
znaleziska bez ujawniania wartości). Test assertuje, że żadna wartość **ani jej fragment** nie
pojawia się w zserializowanym raporcie. Testy: **68 OK** (60 `rawpath` + 8 `bundle_scan`),
selftest **11 grup OK**.

---

## 6. Przejęte narzędzie (`har_triage`) i defekt znaleziony przez uruchomienie

Ściągnąłem `a450b00f@bb17ccdc` → `nask/tools/vendor/a450b00f/` (z pełną prowieniencją w
`PROWENIENCJA.md`), bo to jest dokładnie narzędzie na kroki L1/L4 runbooka: **offline** analiza
zrzutów HAR z **dwóch własnych kont** — normalizacja segmentów ID do `{id}`, grupowanie endpointów,
wykrywanie tokenów w query (`token`, `access_token`, `api_key`, `session`, `jwt`, …), asymetria
uprawnień między kontami. Zero sieci, zero poświadczeń, zero werdyktów (każdy wynik to hipoteza).
Zasada autorów, którą przyjmuję: **wspólny dostęp do wspólnego zasobu nie jest IDOR-em samym w sobie.**

**Uruchomiłem ich testy na ich własnym commicie: 1/11 FAIL.**

```
FAIL: test_normalize_ids
  normalize_template("/api/tasks/abc123deadbeef") -> "/api/tasks/abc123deadbeef"
  oczekiwane                                       "/api/tasks/{id}"
```

Przyczyna: `HEX_LONG_RE = ^[0-9a-fA-F]{16,}$` nie łapie 14-znakowego ID szesnastkowego, a ich
własny test takiego oczekuje (commit `bb17ccdc` nosi tytuł „Fix offline HAR triage tests:
**ID length**…", więc to prawdopodobnie niedokończona poprawka). Skutek praktyczny: przy ID
krótszych niż 16 znaków **każde ID staje się osobnym endpointem**, czyli tabela porównawcza dwóch
kont rozjeżdża się dokładnie tam, gdzie szukamy IDOR-a.

U mnie: **jedna udokumentowana poprawka lokalna** (`{16,}` → `{12,}`), po niej **11/11 OK**;
reszta plików nietknięta, diff zapisany w `PROWENIENCJA.md`. Ich sesja może przenieść poprawkę
na swoją gałąź albo zmienić test, jeśli 16 było zamierzone — wtedy proszę o decyzję, bo to
wpływa na czułość grupowania.

Praktyczna uwaga przejęta z Drive 15: **po odtworzeniu workspace snapshot zdejmuje bit `x`**
z binariów (`chmod +x bin/endminer`). Dotyczy to też naszych skryptów — uruchamiamy przez
`python3 …`, więc nas nie blokuje.

---

## 7. Decyzja strategiczna dla usera (nie dla mnie)

Sześć sesji doszło niezależnie do tego samego faktu: **w programie NASK nie ma ani jednej
aplikacji z otwartą rejestracją** — HIVE jest zaproszeniowy, `dns.pl` ma `/user/register` = 404,
reszta to portale treściowe albo formularze bez kont. Klasy płacące najwięcej (IDOR/BAC,
9 000–20 000 zł) wymagają **dwóch własnych kont**. Stąd dwie ścieżki:

* **A — zostajemy w NASK.** Realnie płatna powierzchnia: `POST /api/sendForm` (Tier 1, klasa 5/7,
  4 000–9 000 zł) + PowerBI embed jako tani strzał (§4.1) + odpowiedzi organizatora na trzy pytania
  (zakres `www.nask.pl`, konto HIVE, `info-trace.116sos.pl`). Kalibracja zespołu (Drive 17):
  **1–2 trafienia po 4–9k zł/mies.** dla jednej osoby przy 2–3 wieczorach; 20k wymaga łańcucha
  (RCE / pełne ATO / SSRF z odczytem) — to loteria, ale jedyna w tej klasie. Ich bilans:
  „anonimowy skan 26 hostów: 0 zgłoszeń, 19 trafień odrzuconych przez §8 — **skan bez sesji nie płaci**".
* **B — dokładamy inny program tej samej platformy.** `moje.cert.pl` ma **publiczne
  `/accounts/signup/`** (a450 + Drive 17), mSzyfr to Element Web/Matrix z własną rejestracją
  (2 konta → test odseparowania rozmów = IDOR/ATO), `hack.cert.pl` ma **pełną mapę `/api/v1`**
  z bundle'a (Drive 16, hipotezy H1–H7: `reports/{id}`, `/attachments/{aid}/download`,
  `/internal-notes`, `/payout-export`, `/users/{uid}/role`). Tam IDOR/BAC jest **osiągalny dziś**.
  Warunki: (i) każdy program wymaga **osobnej akceptacji regulaminu**; (ii) `moje.cert.pl` ma
  konflikt prawny (regulamin usługi IV §4.2) → **najpierw pisemne wyjaśnienie organizatora**;
  (iii) **nie mieszamy programów w jednym rejestrze zgłoszeń** (Gemma-B — zgadzam się);
  (iv) `incydent.cert.pl` — **zero fikcyjnych zgłoszeń incydentów**; (v) testy na
  `hack.cert.pl` = testowanie platformy, na której składamy zgłoszenia: technicznie w zakresie,
  ale ryzyko wizerunkowe i wymóg maksymalnej dyskrecji (jedno żądanie potwierdzające, zero zrzutu).

**Moja rekomendacja: A + jedno pytanie do organizatora**, a B dopiero po Twojej decyzji i po
wyjaśnieniu prawnym. Powód arytmetyczny, nie ostrożnościowy: w A zostało 26 dni i jedna
powierzchnia, której **nikt** nie przetestuje bez Ciebie; w B powierzchnie są testowalne dziś,
ale bez Twoich kont stoimy w tym samym miejscu — więc najpierw odblokowujemy to, co blokuje
obie ścieżki naraz (konto platformy + trzy pytania).

---

## 8. Zgodność (fala 2, mój ruch)

* `fetch_page`: **2 żądania** (`oad.nask.pl` × 2 chunki) — pasywne czytanie publicznej strony Tier 1.
* Actions run (RAWPATH-004): **129 żądań GET** po publiczne assety JS, 1,0 req/s, ~130 s + transfer;
  zero sond do API, zero POST, zero hostów spoza §5 (`www.nask.pl` wykluczone z planu ręcznie).
* Drive: **odczyt** 3 plików (15, 16, 17) + listing folderu. Zero zapisu, zero zmian w cudzych
  plikach, zero udostępniania, zero komentarzy.
* Vendor: odczyt 4 plików z cudzej gałęzi przez GitHub API, z zapisaną prowieniencją i testami.
* **Razem dziś: 59 + 129 = 188 żądań GET** do celów, wszystkie zaudytowane w `nask/reports/`.

## 9. Korekty własne (ciąg dalszy rejestru)

* **#33** `bundle_scan.py` ujawniał 6 znaków każdego kandydata na sekret → odcisk sha256 + długość
  + entropia (§5).
* **#34** runbook rev 2 krok 4.3 („`/admin`, `/admin/logs` z sesji zwykłego użytkownika — guardy
  tylko klienta") → **usunięty**: H10 obalony pomiarem Gemmy-B (200/713 B = catch-all).
* **#35** w fali 1 napisałem, że `116sos` „wrócił" na podstawie jednego przebiegu; teraz mam
  potwierdzenie z drugiego kanału (Gemma-B) i 4 endpointy zmierzone — wpis w rejestrze dostaje
  datę ważności zamiast stanu trwałego (wniosek z §3c).
* **#37** workflow `nask-rawpath.yml`: krok miningu czytał `files` (licznik) zamiast `results`
  (lista) → run 5 failed; naprawione + diagnostyka commitowana (`if: always()`), bo logi Actions
  są nieosiągalne z sandboxa (§5).
* **#36** mój nocny plan L4 „wtyczki WP na 116sos/dyzurnet" był oparty na `wp-json` = 404;
  fala 2 domknęła obejście (`?rest_route=` → HTML, `xmlrpc.php`/`wp-login.php` → 404), więc
  pozycja wypada z runbooka zamiast czekać na „sprawdzenie później".

---

## 10. Wyniki RAWPATH-004/005 (mining + 4 próby domykające) — stan na 11:35

### 10.1 RAWPATH-004 (run 7, `41821385075`): 129 bundli JS, 10,47 MB

| parametr | wartość |
|---|---|
| żądania | 129 GET, 1,0 req/s, 216,42 s, **min. odstęp 1,000 s** |
| odpowiedzi | 121 × 200, 2 × 404 (`_buildManifest.js`/`_ssgManifest.js` z innym buildId), 6 × timeout (chunki `116sos`/`science`) |
| ciała | 123 pliki, **10 470 052 B** w `RUNNER_TEMP` (nigdy w repo); commitowany manifest + analiza |
| mining | **108 plików, 28 unikalnych endpointów, 0 sekret-kandydatów**, `idor_prerank` = 0 |
| formaty ID w bundlach | `sequential-int-candidate` 19, `uuid` 1, `other` 153 |

**Zero sekretów w 10,47 MB publicznego JS** — zbieżne z `5ed750ef` (47 bundli / 7,3 MB → 0 sekretów,
0 sourcemap). Dwa niezależne przebiegi, ten sam wynik ⇒ klasa „wyciek poświadczeń z bundli"
zamknięta dla całego zakresu NASK.

**Endpointy wydobyte z bundli (28):** `zglos-dezinformacje` → **`/api/sendForm` i nic więcej**
(potwierdzenie z kodu klienta, że to jedyne API); `science` → `/api/{contact,downloadFile,search}`,
**`/api/media/wp-content/`**, **`/api/media/wp-includes/`**; `116sos` → `/api/{announcements,
fetch-cookie-hash}`; `dns.pl` → `/api/{zone-stats,registrars-services,registrars-list/,
registrars-countries/{pl,en},count-deleted-domains,domain-browser/,who-is-xml/,stats/,funny-name/}`,
**`/deleted_domains.txt`**, `/news/`, `/post-data/`, `/events/?…`; `pllum` → `/api/_nuxt_icon`;
wzorce `/_next/data/${buildId}…`.

### 10.2 RAWPATH-005 (run 8): cztery próby, dwie hipotezy rozstrzygnięte

| próba | wynik | rozstrzygnięcie |
|---|---|---|
| `dns.pl/deleted_domains.txt` | **200, `text/plain; charset=UTF-8`, 37 343 B**, `cache-control: no-cache, private` | plik istnieje i jest generowany dynamicznie. **Treści celowo NIE pobrałem do raportu** (`no_preview: true`) — dopóki nie wiemy, czy zawiera dane abonenta, nie kopiuję jej ani do repo, ani do kontekstu. Rejestr L20: **10-sekundowe spojrzenie usera** w przeglądarce. Jeśli to sama lista nazw domen (najbardziej prawdopodobne — rejestr publikuje takie dane, a bundel ma też `/api/count-deleted-domains`) → **klasa wykluczona** (informacja bez danych wrażliwych) |
| `dns.pl/translations/domainBrowser?locales=pl` | 200, **`application/javascript`**, 1 666 B, treść: `t.add("domain_browser_suggestion_title", "Propozycje domen dostępnych do rejestracji:", "domainBrowser", "pl")` | **hipoteza L17 NIEPOTWIERDZONA**: to etykiety UI (Bazinga Translator), nie nazwy parametrów API. Mining: 0 endpointów, 0 parametrów. L17 → zamknięty jako niska wartość |
| `science/api/media/wp-includes/js/jquery/jquery.min.js` | **200, `text/javascript`, 87 553 B, jQuery v3.7.1** | **hipoteza allow-listy POTWIERDZONA** |
| `science/api/media/wp-includes/version.php` | **404** | `.php` w dozwolonym katalogu **nie** jest serwowany |

**Mechanizm domknięty (L7 zamykam z pełnym wyjaśnieniem, nie tylko wynikiem):**
`/api/media/` na `science.nask.pl` to **proxy statycznych assetów z allow-listą dwóch podkatalogów
WordPress** (`wp-content/`, `wp-includes/`) i allow-listą typów pliku (JS/CSS/obrazy — `.php` → 404),
stojące za **nginx**, który dekoduje `%2e` i normalizuje segmenty `..` **przed** przekazaniem do
aplikacji (dowód: `%252e%252e` → 404, czyli aplikacja nie dekoduje drugi raz), a próby wyjścia
poza korzeń kończą się **zerwaniem połączenia** lub **nginx 400**. Stąd wszystkie negatywy
z run1–run3 (`robots.txt`, `license.txt`, `readme.html`, `wp-config.php` na 4 głębokościach —
wszystko 404). **To nie jest „nie udało się przetestować", tylko „tak to działa".**

### 10.3 Korekty własne z tej fali

* **#38** — 6 werdyktów `CANDIDATE-SECRET-FILE` w run7 to **fałszywe trafienia mojego
  klasyfikatora**: polyfills i chunki (112–417 kB, `application/javascript`) zawierają słowa
  `API_KEY`/`PASSWORD` z list typów `input` w React (`password:!0,range:!0,search:!0,…` — dokładnie
  ten sam szum, który Gemma-A widziała w swoich sondach S1). Kandydatem jest teraz wyłącznie
  odpowiedź, która **może** być plikiem konfiguracyjnym (`text/plain`, `application/octet-stream`,
  brak typu); JS → `js-bundle-with-keyword-hits`.
* **#39** — surowa ekstrakcja parametrów dała **662 pozycje**, w tym `null`, `return`, `this`, `NaN`,
  `ut`, `io`, `Ba`, `Ii`. Filtr `is_real_param()` (długość ≥ 3, bez słów kluczowych JS i typów
  `input`, bez zmiennych minifikatora). `type` zostaje — to realny parametr (`?type=publication`
  na `oad.nask.pl`).
* **#40** — plik pobrany z URL-a bez rozszerzenia (`/translations/x?locales=pl`) zapisywał się jako
  `.bin` i **bundle_scan go pomijał** (rglob tylko `.js/.json/.html/.map`). Rozszerzenie jest teraz
  brane z `Content-Type`. Do tego `no_preview` jako jawna flaga planu (użyta przy `deleted_domains.txt`).
* **Utrata runu 6** (mój błąd CI, korekta #37) → naprawiona strukturalnie: `nask/tools/ci_commit.sh`
  (5 prób pusha, guard „nic poza `nask/reports/`", porządkowanie po nieudanym rebase) + commity
  **etapowe** (raport, mining, diagnostyka osobno). Run 7 i 8 dały po 3 commity bota — żadne dane
  już nie przepadną wraz z workspace runnera.

**Testy: 76 OK** (68 + 8 regresji z run7), selftest **12 grup OK**, vendored `har_triage` **11/11 OK**.
