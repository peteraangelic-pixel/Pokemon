# Wyniki przebiegów RAWPATH-006 (run 9), RAWPATH-007 (run 10) i RAWPATH-008 (run 11) — 05.11.2026

**Bilans uczciwy: 60 żądań GET w trzech przebiegach (31 + 22 + 7), 0 nowych podatności
wypłacalnych, 7 leadów zamkniętych z mechanizmem (w tym L9 drugim, niezależnym kanałem),
1 nowy żywy endpoint (treści publiczne), 1 nowe narzędzie rozstrzygające (liczniki PII),
1 mapa offline (HIVE, 71 tras klienta), 1 nowa trasa publiczna znaleziona w run 11
(`116sos.pl/osrodki-pomocowe`).**

Zgodność: run 9 = 31 żądań / 47,08 s / 7 hostów §5 / min. odstęp 1,000 s; run 10 = 22 żądania /
21,37 s / 5 hostów §5 / min. odstęp 1,000 s; run 11 = 7 żądań / 7,81 s / 4 hosty §5 / min. odstęp
1,000 s. GET-only, 0 POST, 0 zmian stanu, 0 hostów spoza §5, 0 zgłoszeń. Rekordy:
`reports/rawpath-00{6,7,8}-run{9,10,11}.json`, mining:
`reports/mine-rawpath-00{6,7,8}-run{9,10,11}.json`, logi: `reports/logs-run{9,10,11}/`.

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

---

## 12. RUN 11 (`RAWPATH-008`, przebieg `42024136601`) — 7 żądań, 7 rozstrzygnięć

Zgodność (z `logs-run11/40-audit.log`): **7 żądań / 7,81 s / 4 hosty §5** (`zglos-dezinformacje.nask.pl`,
`116sos.pl`, `oad.nask.pl`, `dns.pl`) / **min. odstęp 1,000 s** / 6 ciał 304 447 B / **0 kandydatów
do ręcznego potwierdzenia** / 0 identycznych ciał / 0 błędów transportu / 0 odmów wyjścia poza zakres
/ **AUDYT OK**. Mining: 5 plików, 1 endpoint, `idor_prerank` 0.
Werdykty: `html-page` 4, `method-not-allowed-route-exists` 1, `other-200` 1, `redirect-not-followed` 1.

| id | żądanie | status | bajty | sha256[:16] | werdykt |
|---|---|---:|---:|---|---|
| `zglos-L01` | `GET /api/sendForm` | **405** | **0** | — (`content-length: 0`) | method-not-allowed-route-exists |
| `sos-L02` | `GET /` (116sos) | 200 | 103 227 | `2f4719a3b0029506` | html-page |
| `sos-L03` | `GET /mapa-serwisu` | 200 | 103 104 | `11ffb7ff61702063` | html-page |
| `oad-L04` | `GET /en/` | **308** → `location: /en` | 3 | `7a4ba3ba0fb8f6c3` | redirect-not-followed |
| `oad-L05` | `GET /_next/static/chunks/0gnc331ufzpqs.js` | 200 | 14 147 | `06473846a4098a33` | other-200 (JS) |
| `dns-L06` | `GET /lista_domen_usunietych` | 200 | 41 998 | `004dfdaa0883e442` | html-page |
| `dns-L07` | `GET /przegladarka` | 200 | 41 968 | `be30e4a3b57d21b6` | html-page |

### 12.1 L32 ZAMKNIĘTY — `GET /api/sendForm` = 405 z **pustym ciałem i bez nagłówka `Allow`**

Trasa istnieje (405, nie 404), ale serwer **nie ujawnia listy metod**: `content-length: 0`,
nagłówki tylko `x-frame-options: SAMEORIGIN` i `x-cache: CONFIG_NOCACHE`.

* Wartość praktyczna: **pasywne rozpoznanie metod jest niemożliwe** ⇒ L23/L1-A (POST bez rekordu)
  pozostaje jedyną drogą i nadal wymaga jawnego GO oraz przeglądarki usera. Zero zmiany stanu w run 11.
* Ocena uczciwa: brak `Allow` w odpowiedzi 405 to odstępstwo od RFC 9110 §15.5.6, ale **bez skutku
  bezpieczeństwa** — kategoria informacyjna, czyli dokładnie to, co §8 wyklucza. **Nie zgłaszamy.**
  (Zgłoszenie takiego drobiazgu to ryzyko odrzucenia, a trzy odrzucenia mogą zablokować składanie
  kolejnych — to jest realny koszt, nie formalność.)

### 12.2 L9 ZAMKNIĘTY **drugim, niezależnym kanałem** — 116sos ma publiczną trasę katalogu placówek

Mining dwóch stron 116sos (`/` + `/mapa-serwisu`) dał **326 unikalnych tras publicznych**. Wśród nich:

```
/osrodki-pomocowe
/osrodki-pomocowe/dodaj
/osrodki-pomocowe/dziekujemy
```

Czyli: serwis **sam publikuje katalog ośrodków pomocowych** i ma formularz samoobsługowego dodania
placówki (`/dodaj`) ze stroną podziękowania (`/dziekujemy`). To domyka L9 bez 2 minut pracy usera
i bez porównywania czegokolwiek ręcznie:

1. `/api/centres-search` (run 9: 13 306 B, `PII_EMAIL: 10`, `personal_like` puste, 0 PESEL / 0 telefonów
   / 0 IBAN) oddaje **placówki**, a nie osoby — schemat `centres[]` ma pola `canSleep`, `open24`,
   `centreAimedTo`;
2. ta sama odpowiedź ma `access-control-allow-origin: https://info-trace.116sos.pl`, czyli jest
   zaprojektowana jako backend publicznej aplikacji;
3. 8 domen instytucji wydobytych z tej odpowiedzi (`gops.slawno.ibip.pl`, `mops.krakow.pl`,
   `jarocin.naszops.pl`, `gopsosieck.pl`, `gopschelmno.naszops.pl`, `kolaki.pl`, `markot.pila.pl`,
   `www.gops.ugslawno.pl`) to publiczne ośrodki z własnymi stronami i BIP;
4. **run 11: serwis ma jawną, linkowaną w mapie serwisu trasę `/osrodki-pomocowe`.**

Wniosek: dane są **publicznie przeznaczone do udostępniania** ⇒ §8 wyklucza, lead zamknięty.
Hipoteza wypłacalna (dane opiekunów/dzieci) jest martwa od run 9, a teraz nie ma już nawet resztki
do sprawdzenia. **Nie odpytujemy `/osrodki-pomocowe/dodaj`** — to formularz zapisujący (zmiana stanu),
wymagałby GO tak jak `sendForm`.

Reszta tabeli tras 116sos (dla porządku): `/artykuly/**` 277, `/_next/**` 26, `/dokumenty/**` 6
(w tym `/dokumenty/klauzula-informacyjna-ipz-ptp`), `/favicons/**` 5, `/otrzymaj-pomoc{,/czat,/formularz}`
(**wyłączone decyzją własną** — interwencja kryzysowa), `/api/og-image`, `/aktualnosci`, `/o-platformie-sos`,
`/IPZ-PTP`, `/NASK`, `/mapa-serwisu`. Parametry w HTML: tylko `imageId` i `page`.
**Zero tras** pasujących do `placow*`, `centr*`, `interwenc*`, `telefon*`, `116*` poza wymienionymi.

### 12.3 L13 — prawdopodobieństwo **spada dalej**: nawigacja oad nie zna żadnej strony z PowerBI

Chunk nawigacji/stopki `0gnc331ufzpqs.js` jest żywy (200, 14 147 B, `last-modified: Wed, 04 Nov 2026
12:46:11 GMT`, `cache-control: public, max-age=31536000, immutable`) i zawiera **17 literałów tras**:

```
/bip  /deklaracja-dostepnosci  /en/  /logo.svg  /oad-logo-footer.svg  /polityka-prywatnosci
/wyniki-wyszukiwania?type=project  /wyniki-wyszukiwania?type=publication  /zglos-dezinformacje
/icons/{MC.png,glob.svg,naskLogoWhite.svg,socials/footer/{facebook,instagram,linkedIn,twitter,youtube}.svg}
```

Hosty w tym chunku: `www.facebook.com`, `x.com`, `www.linkedin.com`, `www.instagram.com`,
`www.youtube.com`, `www.w3.org` — **ani `app.powerbi.com`, ani żadnej trasy `/trendy`/`/raport*`**,
ani żadnego `/api/*`. Razem z run 10 (`/trendy` 404, `/en/trendy` 404 o identycznym sha256,
`/trendy/` → 308) daje to spójny obraz: **kod embedu istnieje jako martwy moduł ładowany przy
`/wyniki-wyszukiwania`, ale strona nie jest osiągalna w bieżącym deploy-u**. Zostaje wyłącznie
30-sekundowe sprawdzenie samego URL-a embedu przez usera (instrukcja po korekcie #49).

Dodatkowo: `oad.nask.pl/en/` → **308** na `/en` — mój plan miał wersję z ukośnikiem, więc run 12
(`oad-M05`) pobierze właściwy cel i da aktualną angielską tabelę tras.

### 12.4 dns.pl: UI potwierdza L20 drugim kanałem i **nie** zdradza mechanizmu przeglądarki domen

* `/lista_domen_usunietych` = 200, **41 998 B**, a `/przegladarka` = 200, **41 968 B** — dwie różne
  strony (różne sha256), obie **znacznie poniżej 51 225 B**. To drugie, niezależne potwierdzenie
  reguły L25: przechwycenie brzegowe ma charakterystyczny rozmiar ~51,2 kB i `_event_transid`,
  a te odpowiedzi go nie mają ⇒ są prawdziwymi stronami.
* HTML obu stron **nie zawiera żadnego literału `/api/*`** i żadnych parametrów poza `family`
  oraz `locales` (Google Fonts) ⇒ mechanizm odpytywania `/przegladarka` siedzi w JS
  (`main-3.3.0.02aeae80.js`, który już mamy: jego endpointy `/api/{stats,who-is-xml,domain-browser,funny-name}`
  dają 404 w GET) albo jest POST-em. Run 12 (`dns-M07`) pobierze `/search-results` — formularz
  wyszukiwarki bez query string (celowo, żeby nie wejść w warstwę brzegową).
* **Nawigacja rejestru linkuje `/deleted_domains.txt`** oraz `/en/list_of_expired_domain_names`
  ⇒ publikowanie tej listy jest **zamierzone i widoczne w menu serwisu**. To drugi kanał dla L20
  (pierwszy: 0 znaczników PII w 46 440 B + 31,6 B na wiersz).
* Nowe trasy dns.pl z run 11 (spoza bundla): `/raporty`, `/search-results`, `/site-map`,
  `/en/browser`, `/en/list_of_expired_domain_names`, `/gov.pl/wniosek`, `/RDAP_w_NASK`,
  `/NASK_extension_of_RDAP_Response`, `/punkt_kontaktowy_rejestru_do_spraw_{DSA,KSC}`,
  `/eksporty_pliku_strefy_pl`, `/lista_domen_{funkcjonalnych,regionalnych}`, `/pl_registry_lock*`,
  `/regulamin_nazw_domeny_pl_{by,ru,ua}/**`, `/cennik_dla_rejestratorow`, `/historia`, `/jakosc_w_nask`,
  `/polityka_przeciwdzialania_naduzyciom`, `/procedura-weryfikacji-danych`,
  `/polityka-rejestru-dotyczaca-danych`, `/instrukcje-dla-autorow`, `/bundles/bazingajstranslation/js/translator.min.js`
  (Symfony + BazingaJsTranslation ⇒ część serwisu jest renderowana serwerowo, nie SPA).
* Hosty w HTML dns.pl: `dns.pl`, `www.dns.pl`, `fonts.googleapis.com`, **`panel.dns.pl`**,
  **`tracker.dns.pl`** — dwa ostatnie poza literałami §5, więc **nietknięte** (pytanie do organizatora, L0).

### 12.5 Świeży `buildId` 116sos i ogólna reguła (rozszerzenie lekcji z korekty #31)

Run 11 oddał `/_next/static/eY_q-tnDts2YvuKlalLWP/_buildManifest.js` ⇒ **aktualny buildId 116sos to
`eY_q-tnDts2YvuKlalLWP`**, a `8CjJwbyxpVqpWnorny23T` z mapy sesji 7911f950 jest **nieaktualny**.
Reguła: buildId, nazwę chunka i hash assetu bierzemy **z tego samego przebiegu**, w którym ich
używamy — inaczej sonda wraca 404 i wynik jest nieinterpretowalny (dokładnie tak padły `bm-J26`
w run 9 po redeployu i `sci-J21` bez kontroli). Run 12 używa `eY_q-tnDts2YvuKlalLWP` natychmiast.

### 12.6 Nowy host ujawniony w HTML 116sos (poza §5 — **nieodpytywany**)

`116sos.multisite.lab.nob.pib.nask.pl` — środowisko lab/multisite. Poza literałami §5 programu NASK,
a w programie CERT infrastruktura `*.lab.cert.pl` jest wprost **wyłączona**, więc analogii nie
testujemy. Wpisane do rejestru jako pytanie do organizatora (razem z `www.nask.pl`,
`info-trace.116sos.pl`, `panel.dns.pl`, `tracker.dns.pl`).

### 12.7 Korekta #50 (obserwacja, bez zmiany kodu)

Znacznik `SOFT404_PL` odpalił się na **pliku JS** (`oad-L05`, 14 147 B) — minifikowany chunk zawiera
polskie frazy UI, które pasują do wzorca. To **szum kosmetyczny, nie błąd werdyktu**: logika werdyktu
bramkuje ten znacznik warunkiem `"html" in ctype` (`rawpath.py`, linia 454), więc JS dostał prawidłowy
werdykt `other-200`. Nie zmieniam kodu — zmiana bez testu na żywym materiale byłaby gorsza niż
udokumentowany, nieszkodliwy szum. Gdyby kiedykolwiek `soft-404-html` pojawił się przy `content-type`
innym niż HTML, to już jest błąd i wracamy.

### 12.8 Stan po trzech przebiegach 05.11

| rzecz | stan |
|---|---|
| potwierdzone podatności | **0** |
| zgłoszenia | **0** |
| żądania GET razem (04.11 + 05.11) | 321 + 31 + 22 + 7 = **381** |
| POST / PUT / DELETE | **0** |
| zmiany stanu | **0** |
| hosty spoza §5 odpytane | **0** |
| leady zamknięte 05.11 z mechanizmem | L5, L9 (2 kanały), L18, L20 (2 kanały), L22, L24–L31, **L32** |
| leady aktywne | **L13** (tylko URL embedu, 30 s, user), **L0** (rejestracja + pytanie do organizatora), L23/L1-A (POST, wymaga GO), L14/L15 (formularze, wymagają GO), L36 (defekt cudzego narzędzia) |
| w drodze | run 12 = `RAWPATH-009`, 7 sond (116sos `/osrodki-pomocowe` + propsy Next.js z kontrolą + manifest tras, oad `/en`, dns.pl `/raporty` i `/search-results`) |
