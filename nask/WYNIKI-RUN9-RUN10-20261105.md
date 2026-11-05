# Wyniki przebiegów RAWPATH-006 (run 9) i RAWPATH-007 (run 10) — 05.11.2026

**Bilans uczciwy: 53 żądania GET, 0 nowych podatności wypłacalnych, 6 leadów zamkniętych
z mechanizmem, 1 nowy żywy endpoint (treści publiczne), 1 nowe narzędzie rozstrzygające
(liczniki PII), 1 mapa offline (HIVE, 71 tras klienta).**

Zgodność: run 9 = 31 żądań / 47,08 s / 7 hostów §5 / min. odstęp 1,000 s; run 10 = 22 żądania /
21,37 s / 5 hostów §5 / min. odstęp 1,000 s. GET-only, 0 POST, 0 zmian stanu, 0 hostów spoza §5,
0 zgłoszeń. Rekordy: `reports/rawpath-006-run9.json`, `reports/rawpath-007-run10.json`,
mining: `reports/mine-rawpath-00{6,7}-run{9,10}.json`, logi: `reports/logs-run{9,10}/`.

---

## 1. ROZSTRZYGNIĘCIE A — kandydat na sekret w dns.pl: **to nonce, nie poświadczenie**

Run 9 znalazł w odpowiedzi dns.pl kandydata `generic_assignment`: **111 znaków, entropia 5,50,
odcisk `b2c856bd7b5c`**. Run 10 powtórzył i dodał kontrole. Porównujemy **odciski**, więc sama
wartość nigdy nie trafiła do repo (korekta #33):

| próba | URL | status | bajty | odcisk kandydata | długość | entropia |
|---|---|---:|---:|---|---:|---:|
| run9 `dns-J11` | `/api/who-is-xml/?domain=nask.pl` | 404 | 40 910 | `b2c856bd7b5c` | 111 | 5,50 |
| run10 `dns-K09` | `/api/nie-istnieje-xyz-123` | 404 | 40 911 | `aeedb50f4571` | 112 | 5,55 |
| run10 `dns-K08` | `/api/nie-istnieje-xyz-123?statisticsUrl=https://example.com/` | 200 | 51 204 | `ee5b2b574f12` | 109 | 5,52 |
| run10 `dns-K01/K02/K03` | `/api/who-is-xml/?domain=…` ×3 | 404 | 40 919/40 920/40 926 | **brak** | — | — |
| run10 `dns-K04` | `/` | 200 | 51 127 | brak | — | — |
| run10 `dns-K05` | `/statystyki/liczba_aktywnych_IDN` | 200 | 42 289 | brak | — | — |

**Wniosek: trzy różne strony ⇒ trzy różne odciski (109/111/112 znaki, entropia ~5,5), a te same
trzy żądania `dns-J11`/`dns-K01`/`dns-K02` raz dają kandydata, a raz nie.** Wartość zmienia się
między odpowiedziami i pojawia nieregularnie ⇒ to **token na-odpowiedź (nonce)**, nie stały
literał. Hipoteza klasy 1 (poświadczenia w kodzie/stronie) **ZAMKNIĘTA NEGATYWNY**.

Kontekst mechanizmu: w bundlu dns.pl (run 9, `hosts`) są **`tracker.dns.pl`** i `panel.dns.pl`,
a w HTML każdej strony `var _event_transid='<liczba>'` (run9 `dns-J06`: `'2072802715'`,
run10 `dns-K06`: `'2072802802'` — licznik rośnie). To warstwa śledząca/antybotowa rejestru.
**Znany fałszywy pozytyw do allow-listy:** `generic_assignment` na stronach dns.pl = ten token.
(`tracker.dns.pl` i `panel.dns.pl` są **poza §5** — §5 wymienia literal `dns.pl` bez `*`,
więc ich nie odpytujemy; to samo stanowisko co L10/L11.)

## 2. ROZSTRZYGNIĘCIE B — „200 + strona główna" na dns.pl to **przechwycenie na brzegu**, nie odpowiedź aplikacji

Decydująca para (ten sam przebieg, ta sama ścieżka, różni się tylko query):

| próba | URL | status | Content-Type | bajty |
|---|---|---:|---|---:|
| `dns-K07` (kontrola) | `/api/zone-stats?x=1` | **200** | **application/json** | **11 761** |
| `dns-K06` | `/api/zone-stats?x=%0D%0A` | **200** | **text/html** | **51 225** |
| `dns-K09` (kontrola) | `/api/nie-istnieje-xyz-123` | 404 | text/html | 40 911 |
| `dns-K08` | `/api/nie-istnieje-xyz-123?statisticsUrl=https%3A%2F%2Fexample.com%2F` | 200 | text/html | 51 204 |

Ciało `dns-K06`/`dns-K08` to strona główna dns.pl ze wstrzykniętym `_event_transid`
(podgląd: `<script type="text/javascript">. var _event_transid='2072802802';.</script>`),
`cache-control: max-age=0, must-revalidate, private, s-maxage=300`.

**Mechanizm: warstwa brzegowa rozpoznaje wzorce ataku w query (CRLF, absolutny URL obcego hosta)
i zamiast blokady 403 oddaje stronę główną z licznikiem zdarzenia — PRZED routingiem do
aplikacji.** Dowód: żywy endpoint `/api/zone-stats` traci swoją odpowiedź JSON, gdy do query
doklei się `%0D%0A`, a ścieżka nieistniejąca daje 200 zamiast 404, gdy query zawiera obcy URL.

Konsekwencje:
1. **Hipoteza SSRF na `/api/stats/?statisticsUrl=` MARTWA z mechanizmem**: `/api/stats/` daje 404
   (Drupal, 40 914 B) w run9 bez i z parametrem; `statisticsUrl` to zmienna klienta z
   `main-3.3.0.02aeae80.js`, nie parametr API. Run9 `dns-J06` (200 na `statisticsUrl=https://example.com/`)
   **nie był** pobraniem czegokolwiek — to przechwycenie.
2. **Hipoteza wstrzyknięcia CRLF do zapytania WHOIS MARTWA**: `/api/who-is-xml/` daje 404 w 5/5
   wariantów (`bare`, `domainName=`, `domain=`, domena nieistniejąca, CRLF) ⇒ endpoint
   **nie istnieje** jako GET; run9 `dns-J10` (200) to przechwycenie, nie odpowiedź WHOIS.
3. **Reguła dla wszystkich sesji (metodologiczna, warta więcej niż niejeden „finding"):**
   na `dns.pl` odpowiedź `200 + ~51,2 kB + _event_transid` znaczy **„żądanie zostało oflagowane"**,
   a NIE „zasób istnieje". Kto to pomyli, zgłosi fałszywy SSRF/open-redirect/bypass.
4. Samo przechwycenie **nie jest wypłacalne**: brak obejścia (nie zademonstrowano dostępu do
   niczego), brak zmiany stanu, brak danych. §8 wyklucza „raporty z samych skanerów" i informacje
   o wersjach/ścieżkach. **Nie zgłaszamy.**

**Mapa API dns.pl po run9/run10 (ostateczna dla GET):** żywe = `/api/zone-stats` (JSON:
`errors, lang, stats.{time,day,rows}`, w `rows` m.in. `2 757 995` domen i `+1467` usuniętych)
oraz `/api/count-deleted-domains` (`{"count":"+1467"}` = komórka z zone-stats, 17 B przy
`text/html`), plus `/deleted_domains.txt`. **404** = `/api/stats/`, `/api/who-is-xml/`,
`/api/domain-browser/`, `/api/funny-name/`. To domyka L5/L22 („nieznany kąt dns.pl/api/*").

## 3. ROZSTRZYGNIĘCIE C — `science.nask.pl/api/search`: **nowy żywy endpoint, treści publiczne, klasa 3 zamknięta**

Run 9 dowiódł istnienia (nikt z 6 sesji go nie testował):

| próba | URL | status | bajty | dowód |
|---|---|---:|---:|---|
| `sci-J16` | `/api/search` | 400 | 47 | `{"error":"Query must be at least 3 characters"}` |
| `sci-J18/J19` | `/api/search?q=`, `?searchPhrase=` | 400 | 47 | **identyczny sha256 `4d4c455f…` w 3 próbach** ⇒ walidowany jest dokładnie `query` |
| `sci-J17` | `/api/search?query=hive` | **200** | 2 121 | JSON `pageData[]` |
| `sci-K13` | `/api/search?query=hive&post_status=draft` | 200 | 2 121 | **sha256 `b4c9ddfdb205…` IDENTYCZNY z `sci-J17`** ⇒ parametr ignorowany ⇒ **brak wycieku wersji roboczych** |
| `sci-K11` | `/api/search?query=hive&page=2` | 200 | 49 | `{"pageData":[],"page":0,"perPage":0,"lastPage":0}` ⇒ paginacja normalizowana |
| `sci-K12` | `/api/search?query=hive&perPage=100` | **400** | 30 | `{"error":"Invalid pagination"}` ⇒ **brak masowego odczytu** |
| `sci-K14` | `/api/contact` | **405** | 30 | `{"error":"Method not allowed"}` ⇒ trasa istnieje, tylko POST (= L15, wymaga GO) |
| `sci-K15` | `/sitemap.xml` | 404 | 17 524 | **kontrola G nie wyszła** — sitemap nie istnieje; rozstrzygnięcie dał `sci-K13` przez identyczność sha256 |
| `sci-K10` | `/api/search?query=aaa` | 200 | 1 790 | `pageData[0] = {id:13276, title:"Mgr inż. …", typeName:"Osoba", imageUrl:{ID:13360,…}}` |

Schemat odpowiedzi (`json_keys`): `page`, `lastPage`, `perPage`, `pageData[].{id,title,description,
typeName,imageUrl.{ID,id,filename,filesize,author,caption,date,link,menu_order,…}}` — czyli
publiczne wpisy WordPress + metadane załączników (te same ID, które je `/api/downloadFile`).
**Liczniki PII = 0** w obu odpowiedziach (brak e-maili/telefonów/PESEL/IBAN), mimo że
`typeName:"Osoba"` występuje ⇒ to osoby publiczne (kadra/projekty) prezentowane na stronie.

**Wniosek: wyszukiwarka oddaje wyłącznie treści opublikowane, walidacja jest serwerowa
(min. długość, paginacja), `post_status` nie jest sterowalny. Klasa 3 ZAMKNIĘTA NEGATYWNY
z kontrolą w tym samym przebiegu.** Zostaje z tego tylko `/api/contact` = POST (L15, wymaga GO).

## 4. ROZSTRZYGNIĘCIE D — `oad.nask.pl/trendy` **nie istnieje**: instrukcja L0.5 była błędna (korekta #49)

| próba | URL | status | dowód |
|---|---|---:|---|
| run9 `oad-J23` | `/trendy` | **404** | 13 814 B, strona 404 Next (`sha 286f1682796c…`) |
| run10 `oad-K17` | `/en/trendy` | **404** | **ten sam sha256 `286f1682796c…`** ⇒ ta sama strona 404 |
| run10 `oad-K18` | `/trendy/` | **308** | `location: /trendy`, ciało 7 B ⇒ przekierowanie do trasy, której nie ma |
| run10 `oad-K16` | `/_next/static/chunks/41lk95l8op7nz.js` | 200 | **34 692 B** — chunk wciąż żywy (ładuje go `/wyniki-wyszukiwania`) |

Mining chunka (korekta #44 `paths`/`hosts`): trasy `/about-us`, `/news`, `/trendy`, `/o-nas`,
`/aktualnosci`, `/media/`, `/_next/image` **oraz szablony** `/${e}`, `/${n}${l}`, `/${t.H.EN}`,
`/${t.L}` (budowanie tras z obiektami lokalizacji); hosty: **`app.powerbi.com`**, `nextjs.org`,
`www.w3.org`; parametry: `autoAuth, ctid, current, dpl, reportId, total, year`.

**Wniosek dla L13:** kod z embedem PowerBI **jest wysyłany do przeglądarki**, ale trasa `/trendy`
została usunięta/przeniesiona (404 w 3 wariantach, w tym `/en/`). To **obniża** prawdopodobieństwo,
że raport jest żywy — ale go nie rozstrzyga, bo embed z `autoAuth=true` działa niezależnie od
naszej strony. **Korekta #49: instrukcja „otwórz `oad.nask.pl/trendy`" była błędna** — sprawdzenie
sprowadza się do **samego URL-a embedu** (30 sekund, incognito):
`https://app.powerbi.com/reportEmbed?reportId=470044cf-1a84-4ecb-87f1-7e914afdbb19&autoAuth=true&ctid=95dc45af-07b0-4179-a598-9740073a6e4a`.
`app.powerbi.com` pozostaje poza §5 (Microsoft) — **nigdy nie odpytujemy go automatem**.

## 5. ROZSTRZYGNIĘCIE E — `pllum.org.pl` previewToken: **parametr ignorowany**

| próba | URL | status | bajty | sha256 |
|---|---|---:|---:|---|
| `pllum-K19` | `/api/_content/query?preview=test-123` | 200 | 9 543 | `78516d89b48f…` |
| `pllum-K20` | `/api/_content/query` | 200 | 9 543 | **`78516d89b48f…` (identyczny)** |

Odpowiedź to tablica dokumentów Nuxt Content z jawnym polem **`_draft`** (`[]._draft`,
`[]._path:"/form"`, `[]._locale`, `[].consortium.*`). Token celowo niepoprawny ⇒ **identyczny
sha256 z kontrolą dowodzi, że `preview` nie jest przetwarzany**. Trop ZAMKNIĘTY NEGATYWNY.
Zostaje z tego użyteczne **kryterium falsyfikacji na przyszłość**: pozytyw wyglądałby jako
wpisy z `_draft: true` w tej samej odpowiedzi — do sprawdzenia, gdyby ktoś dostał konto CMS.

## 6. ROZSTRZYGNIĘCIE F — HIVE: mapa **tras klienta**, nie API (L18 zamknięty offline)

`dataannotation.pllum.org.pl/assets/index-ClBZuP56.js` = **2 770 426 B pobrane w całości**
(run9 `hive-J29`) i zminowane nowym ekstraktorem:

* **71 literałów tras** (składnia TanStack Router z `$param`):
  `/login`, `/register`, `/forgot-password`, `/reset-password`, `/account`, `/admin`, `/admin/logs`,
  `/unauthorized`, `/search`, `/annotators`, `/projects`, `/projects/create`,
  `/projects/$projectShortName`, `/projects/$projectShortName/conversation`,
  `/projects/$projectShortName/conversation/$recordId`,
  `/projects/$projectShortName/conversation/$recordId/edit/$editedItem`,
  `/projects/$projectShortName/edit/{annotators,basic-info,description,interaction-tags,labels,llm-models,samples,system-prompt,system-prompt-tags,tools,tools-tags}`,
  `/projects/create/{…te same 11…}`
* **0 literałów API** (`/api/…`, `/v1/…`, `graphql`) w 2,77 MB ⇒ ścieżki API są budowane
  dynamicznie; hosty w bundlu: `dataannotation.pllum.org.pl` (własny), `github.com`,
  `tanstack.com`, `react.dev`, `radix-ui.com`, `cdn.jsdelivr.net`, `fontawesome.com`,
  `www.apache.org`, `www.ibm.com`, `www.w3.org`, `fb.me`, `empty.invalid` ⇒ **API jest
  same-origin, nie ma osobnego hosta API**.
* Run10 potwierdził, że trasy klienta **nie mapują się 1:1** na API:
  `/api/v1/projects/test/conversation/1` → **404** `{"detail":"Not Found"}` (22 B) i
  `/api/v1/annotators` → **404**, ten sam sha256 `37ec4665a810…` co 404 z run1. Razem z run1
  (`/api/v1/projects/` → **401**, `/api/v1/users/1` → **405**) mamy: API istnieje pod
  `/api/v1/`, ale jego kształt **nie wynika z bundla**.

**Wniosek: L18 ZAMKNIĘTY jako praca offline — bundel daje mapę EKRANÓW (do czego będzie konto),
nie mapę API.** Mapę API da wyłącznie **HAR z zalogowanej sesji** (do tego jest zwendoryzowany
`nask/tools/vendor/a450b00f/har_triage.py` + `auth_matrix.py`, 11/11 testów). Dodatkowo:
`/admin/logs` jest **trasą klienta**, co wyjaśnia, dlaczego `GET /admin/logs` dawał shell 713 B
(H10 obalony słusznie — serwer nie ma takiej trasy, SPA rysuje ekran po zalogowaniu).
**Bez konta od organizatora L1/L2 pozostają zablokowane** i nie da się tego obejść żadną liczbą
żądań.

## 7. L20 (`dns.pl/deleted_domains.txt`) — **ZAMKNIĘTY bez pracy usera**, dwa niezależne argumenty

| dowód | wynik |
|---|---|
| run8 `dns-I01` | 200 `text/plain; charset=UTF-8`, **37 343 B**, `no_preview:true` |
| run9 `dns-J15` | 200 `text/plain`, **46 440 B**, `cache-control: no-cache, private`, **znaczniki PII: `{}` ⇒ 0 e-maili, 0 PESEL-i, 0 telefonów, 0 IBAN-ów** |
| arytmetyka | `/api/count-deleted-domains` → `{"count":"+1467"}`; 46 440 B / 1 467 pozycji ≈ **31,6 B na wiersz** = sama nazwa domeny + znak nowej linii. Na dane abonenta (imię, nazwisko, e-mail) nie ma miejsca w tym pliku |
| wzrost | 37 343 B → 46 440 B w ~24 h ⇒ plik jest generowany na bieżąco z listy usuniętych domen |

**Wniosek: publiczne dane rejestru (nazwy domen), klasa wykluczona §8. User NIE musi tego
otwierać.** Uczciwe zastrzeżenie: liczniki PII wykrywają e-mail/PESEL/telefon/IBAN — nie
wykryłyby samego „imię nazwisko" bez kontaktu; argument arytmetyczny (31,6 B/wiersz) domyka
tę szczelinę niezależnie.

## 8. L9 (`116sos.pl/api/centres-search`) — **zamknięty jako dane instytucjonalne**

`sos-J30` → 200 JSON **13 306 B**, znaczniki **`PII_EMAIL: 10`** (werdykt
`CANDIDATE-PII-IN-RESPONSE` — pierwszy i jedyny kandydat runu 9), `no_preview:true`,
`access-control-allow-origin: https://info-trace.116sos.pl`,
`cache-control: public, max-age=30, s-maxage=60, stale-while-revalidate=300`.

Schemat: `centres[].{id,name,email,phone?,address.{street,building,apartment,city,postcode,
voivodeships},geoCords.{lat,lon},latitude,longitude,canSleep,open24,centreAimedTo,
centreSupports,…}`.

Rozstrzygnięcie **czyje to dane**: mining (korekta #44, `hosts`) wyciągnął z tej odpowiedzi
8 domen własnych placówek — `gops.slawno.ibip.pl`, `www.gops.ugslawno.pl`, `jarocin.naszops.pl`,
`gopsosieck.pl`, `gopschelmno.naszops.pl`, `mops.krakow.pl`, `kolaki.pl`, `markot.pila.pl`.
To **gminne/miejskie ośrodki pomocy społecznej i organizacje prowadzące placówki** — instytucje
z własnymi publicznymi stronami (w tym BIP). Do tego `centres[]` opisują **placówkę**
(`canSleep`, `open24`, `centreAimedTo`), nie osobę.

**Wniosek: 10 adresów e-mail w tej odpowiedzi to kontakty instytucjonalne, a katalog jest
publiczny z założenia (cały sens 116sos to pomóc dziecku znaleźć placówkę). Klasa 3
ZAMKNIĘTA jako wykluczona.** Resztka ryzyka, którą user może zdjąć w 2 minuty (i tylko jeśli
chce): czy zbiór placówek z API jest **równy** temu w publicznej wyszukiwarce — gdyby API
zwracało placówki o **niejawnych adresach** (np. ośrodki interwencji kryzysowej dla ofiar
przemocy), to zmienia postać rzeczy. Ale hipoteza wypłacalna („dane osobowe opiekunów/dzieci")
jest martwa: `personal_like` puste, PII = 10 e-maili instytucji, 0 PESEL-i, 0 telefonów
w formacie +48, 0 IBAN-ów.

## 9. Co nowego dały narzędzia (korekty #43/#44/#45/#48 — wszystkie z testami)

| korekta | co | efekt w run9/run10 |
|---|---|---|
| **#43** | liczniki PII (`PII_EMAIL`/`PII_PESEL` z pełną sumą kontrolną/`PII_PHONE_PL`/`PII_IBAN`) — **tylko liczby**, podgląd wyciszany przy PII, nowy werdykt `CANDIDATE-PII-IN-RESPONSE`; liczone wyłącznie dla odpowiedzi DANYCH (nie HTML/JS), bo `mailto:` w stopce dawałoby kandydata na każdym żądaniu | rozstrzygnął **L20** (0 PII) i **L9** (10 e-maili instytucji) **bez udziału usera i bez publikowania czegokolwiek** |
| **#44** | `bundle_scan`: `paths` (literały ścieżek, priorytet nie-statyczne, cap 300), `hosts` (cap 80), sekrety w query-stringu (`?access_token=WARTOSC`) jako odcisk | **71 tras HIVE** (L18), hosty `tracker.dns.pl`/`panel.dns.pl` (poza §5 — wykluczone), 8 domen placówek w `centres-search` (rozstrzygnięcie L9), `app.powerbi.com` + trasy `/trendy`,`/news`,`/about-us` w chunku oad |
| **#45** | filtr kształtu wartości sekretu: `generic_assignment` łapał sklejenia minifikatora (`token="+encodeURIComponent(t)+"` → 23 znaki, entropia 3,73) | usunął klasę fałszywych pozytywów, która skończyłaby się fałszywym zgłoszeniem |
| **#48** | **moja własna regresja z #45**: obniżyłem próg entropii 3,5 → 3,0 dla wszystkich, przez co run 9 zgłosił 8-znakowy szum z bundla HIVE (entropia 3,0) | przywrócone 3,5 (i 4,0 dla wartości < 12 znaków); test asertuje oba progi |
| **#49** | instrukcja L0.5 („otwórz `oad.nask.pl/trendy`") była **błędna** — trasa daje 404 | runbook poprawiony: sprawdzenie dotyczy wyłącznie URL-a embedu |

## 10. Falsyfikacja tropu `access_token` na `bezpiecznymiesiac.pl` (nie zgłaszamy)

Run9 `bm-J26` (`/_next/static/chunks/35g9u-wrehnzi.js`) → **404, 9 B** ⇒ chunk zniknął
(redeploy; run9 `bm-J27` pokazuje już inne nazwy chunków, np. `37h7yb8yf4x5-.js`,
`2ltfyi30sim0d.js`). Rozstrzygnięcie oparte na liście literałów z `analysis-run003.json`
(7911f950) dla **dokładnie tego** chunka:

`facebook.com/sharer/sharer.php`, `graph.facebook.com/?id=`, `facebook.com/dialog/send`,
`work.facebook.com/sharer.php`, `pinterest.com/pin/create/button/`, `api.pinterest.com/v1/urls/count.json`,
`api.tumblr.com/v2/share/stats`, `reddit.com/submit`, `telegram.me/share/`, `vk.com/share.php`,
`connect.mail.ru/share`, `livejournal.com/update.bml`, `gab.com/compose`, `connect.ok.ru/dk`,
`getpocket.com/save`, `instapaper.com/hello2`, `b.hatena.ne.jp/add?mode=confirm&url=`,
`bookmark.hatenaapis.com/count/entry`, `social-plugins.line.me/lineit/share`, `sharing/share-offsite`

**To biblioteka przycisków „udostępnij"**: `access_token`, `fields`, `id`, `mode`, `src`,
`title`, `url` to nazwy parametrów cudzych API, a `/news/`, `/post-data/`, `/events/?${r.toString()}`
to ścieżki w **tych** serwisach. **Korekta #46: w mojej notatce z fali 2 te trzy ścieżki były
błędnie przypisane do `dns.pl`** — należą do `bezpiecznymiesiac.pl` i do biblioteki share.
**Nie ma poświadczenia NASK. Nie zgłaszamy.** Dodatkowo: `graph.facebook.com` jest poza §5 —
nawet gdyby token był, użycie go byłoby testem cudzej infrastruktury (zakaz).

**Nauczka procesowa: nazwy chunków Next.js/Turbopack są nietrwałe (redeploy w ~24 h) ⇒ lead
oparty na bundlu ma czas życia liczony w dniach i musi być re-weryfikowany przed wydaniem żądania.**

## 11. Stan po run9/run10 — co zostało i co jest warte czegokolwiek

Zamknięte w tych dwóch przebiegach (nie wracamy): `/api/stats/` i `/api/who-is-xml/` (404,
SSRF/CRLF martwe z mechanizmem), przechwycenie brzegowe dns.pl (mechanizm, niewypłacalne),
token dns.pl (nonce), `/api/search` science (treści publiczne, `post_status` ignorowany,
paginacja walidowana), `/api/contact` (405 = POST, L15), `/trendy` oad (404 ×3), `preview`
pllum (ignorowany), mapa API HIVE z bundla (nie istnieje — potrzebny HAR), `deleted_domains.txt`
(dane publiczne), `centres-search` (dane instytucjonalne), `access_token` bm (biblioteka share).

Otwarte, z realną (warunkową) wartością — **wszystko wymaga usera lub organizatora**:

| # | co | kto | warunek wypłaty |
|---|---|---|---|
| L13 | embed PowerBI (`app.powerbi.com/reportEmbed?reportId=470044cf-…&autoAuth=true`) | **user, 30 s, incognito** | renderuje rekordy/dane osobowe bez logowania → klasa 3, Tier 1 (9 000/20 000 zł); agregaty albo błąd logowania → zamykamy. Prawdopodobieństwo **obniżone** po 404 na `/trendy` |
| L0 | rejestracja `hack.cert.pl` + jedno pytanie do organizatora (3 wątki: `www.nask.pl`, konto HIVE, `info-trace.116sos.pl`) | **user, 15 min** | warunek wejścia; odblokowuje 542 literały tras `www.nask.pl` i całą gałąź HIVE (L1/L2 z mapą ekranów z §6) |
| L23 | `sendForm` — wariant bez tworzenia rekordu | ja, **po jawnym GO** | walidacja serwerowa / egzekwowanie reCAPTCHA (klasa 7/13) |
| L14/L15 | `bezpiecznymiesiac.pl/ecsm/zglos-inicjatywe/`, `science.nask.pl/api/contact` (405 = POST) | user + jawne GO | żądania zapisujące, Tier 2 |

Do potwierdzenia w następnym przebiegu (tanio, bez ryzyka): `Allow`/405 na `GET /api/sendForm`
(zero zmiany stanu), trasa katalogu placówek 116sos (żeby domknąć L9 bez usera), angielska
tabela tras oad (żeby ustalić, gdzie naprawdę jest strona z PowerBI), `/lista_domen_usunietych`
i `/przegladarka` na dns.pl (niezależne potwierdzenie §7 i mapa UI dla `/api/domain-browser/`).
