# Jak dać mi dostęp do uwierzytelnionego API **bez** podawania hasła — instrukcja HAR (05.11.2026)

Masz konto na `hack.cert.pl`. To zmienia dokładnie jedną rzecz po mojej stronie: **mogę wreszcie
zobaczyć kształt uwierzytelnionego API** — ale tylko jeśli sam dostanę zrzut ruchu z Twojej
przeglądarki. Nie chcę i nie wezmę loginu ani hasła.

## 1. Dlaczego nie chcę hasła (cztery powody, każdy wystarczający osobno)

1. **Zasada sesji:** nigdy nie proszę o hasła, tokeny, OAuth ani kody 2FA i nigdy ich nie
   przechowuję. To nie jest kurtuazja — to warunek, żeby Twoje poświadczenie nie wylądowało
   w logach, w czacie ani w publicznym repo.
2. **Regulamin §6:** testować wolno **wyłącznie własne konta/konta testowe**. Sesja użyta z mojej
   strony (runner GitHuba w innym kraju, inne IP) wygląda jak współdzielenie konta i może skończyć
   się blokadą konta — a bez konta nie ma udziału w konkursie. Ryzyko niewspółmierne do zysku.
3. **Technika:** runner Actions jest **blokowany przez WAF na hostach cert.pl** (zmierzone: 403 /
   brak odpowiedzi), a sandbox tej sesji **w ogóle nie ma wyjścia TCP** do celów (`curl` → 000).
   Twoje hasło nic by mi nie odblokowało — fizycznie nie wykonałbym nim żądania.
4. **Nie jest potrzebne.** Do mapy API i do hipotez IDOR wystarczy **kształt** ruchu: metody,
   ścieżki, kody, nazwy pól, rozmiary, odciski odpowiedzi. Wszystko to mam ze zrzutu HAR po
   redakcji, bez ani jednej wartości poświadczenia.

## 2. Co dokładnie zrobić (3–5 minut, Chrome/Edge/Firefox)

1. Otwórz **nowe okno incognito** (Ctrl+Shift+N) — zrzut będzie mały i nie będzie zawierał ruchu
   z innych serwisów.
2. DevTools: **F12** → zakładka **Network / Sieć** → zaznacz **Preserve log / Zachowaj dziennik**
   → filtr **Fetch/XHR**.
3. Zaloguj się na `hack.cert.pl` i **klikaj powoli** (1–2 s na ekran) kolejno:
   * pulpit / lista edycji,
   * regulamin lub strona edycji 11/2026,
   * **lista Twoich zgłoszeń** (jeśli masz puste konto — sam ekran listy),
   * **profil / ustawienia konta** (rola, e-mail — to pokazuje `me/*`),
   * zakładka z **załącznikami** lub **płatnościami/wynikami**, jeśli istnieje,
   * na końcu **wyloguj się** (to pokazuje, jak gaśnie sesja — cenna informacja).
4. **Nie** zakładaj zgłoszenia, **nie** wysyłaj formularza, **nie** wgrywaj plików. Chodzi wyłącznie
   o odczyt ekranów.
5. W DevTools kliknij prawym na listę żądań → **Save all as HAR with content** (Chrome/Edge) albo
   **Export HAR** (Firefox) → zapisz jako `hack.cert.pl.har`.

**Ważne:** HAR *z treścią* zawiera dane osobowe (Twój e-mail, może imię). Dlatego plik trafia
**wyłącznie** do katalogu ignorowanego przez gita i jest kasowany zaraz po redakcji (§4).

## 3. Gdzie położyć plik

```
nask/har/raw/hack.cert.pl.har      ← tutaj (katalog jest w .gitignore, never committowany)
```

Wgraj plik do workspace (przeciągnij w oknie sesji albo wskaż ścieżkę). **Nie wklejaj jego treści
do czatu** — to jest ~1–10 MB JSON-a z żywymi poświadczeniami.

## 4. Co robię z plikiem (krok po kroku, wszystko w jednym obrocie)

```bash
python3 nask/tools/har_sanitize.py \
  --in nask/har/raw/hack.cert.pl.har \
  --out-dir nask/har/sanitized \
  --map-out nask/har/mapa-api.json
```

Narzędzie (`nask/tools/har_sanitize.py`, 17 testów + selftest 7 grup):

* **wyrzuca wartości**: `Cookie`, `Set-Cookie`, `Authorization`, tokeny CSRF, hasło z ciała
  logowania, tokeny w query (`token`, `access_token`, `code`, …) i każdą wartość w query, która
  wygląda na dane osobowe (e-mail / PESEL / telefon PL),
* **wyrzuca treści**: ciała odpowiedzi i ciała żądań w całości — zostaje rozmiar, `mimeType`,
  **nazwy pól** i odcisk `sha256[:12]`,
* **zostawia kształt**: metoda, host, szablon ścieżki z ID znormalizowanym do `{id}`
  (`/api/v1/reports/1024/internal-notes` → `/api/v1/reports/{id}/internal-notes`), kod,
  rozmiar, nazwy nagłówków, nazwy parametrów, nazwy pól formularza,
* **dodaje `session_fingerprint`** = `sha256[:8]` poświadczenia — pozwala analizować asymetrię
  uprawnień między dwoma kontami bez znajomości czegokolwiek,
* **na końcu skanuje własne wyjście** pod kątem wszystkich wartości zobaczonych na wejściu:
  jedno trafienie = przerwanie i brak plików (`assert_clean`). Asertowane w teście.
* redakcja jest **idempotentna** (test): drugi przebieg po zredagowanym HAR nic nie zmienia
  i nie podnosi fałszywego alarmu na własnych maskach.

Do gita trafiają **tylko** `nask/har/sanitized/*.sanitized.har` i `nask/har/mapa-api.json`
(reguły negacji w `.gitignore`). Surowy plik kasuję w tym samym obrocie i mówię Ci o tym w czacie.

## 5. Co z tego powstaje (realny produkt, nie obietnica)

1. **Mapa uwierzytelnionego API `hack.cert.pl`** — `hack.cert.pl` jest w §5 Tier 1 programu CERT,
   czyli to cel sam w sobie, nie tylko platforma zgłoszeń.
2. **Macierz hipotez IDOR H1–H7** z materiału Drive-16 (`/api/v1/reports/{id}/internal-notes`,
   `/attachments/{aid}/download`, `/editions/{num}/payout-export`, `/users/{uid}/role`,
   `me/reports/creation-eligibility`) — z **konkretnymi, Twoimi własnymi** identyfikatorami
   obiektów zamiast zgadywania, plus listą żądań do wykonania.
3. **Test asymetrii** przez `nask/tools/vendor/a450b00f/har_triage.py` (11/11 po mojej poprawce):
   jeśli dasz **drugi** zrzut z drugiego konta (np. z drugiego adresu e-mail, na który też możesz
   się zarejestrować), narzędzie pokaże, gdzie konto A widzi zasób konta B. Zasada autorów, którą
   przyjmuję: **wspólny dostęp do wspólnego zasobu nie jest IDOR-em samym w sobie** — różnica musi
   dotyczyć zasobu, do którego konto nie powinno mieć dostępu.
4. **Dokładna lista żądań do kliknięcia przez Ciebie** (albo do wykonania przeze mnie, jeśli
   organizator potwierdzi zakres i WAF przepuści runner) — z uzasadnieniem każdego i z warunkiem
   odrzucenia, tak jak w planach `RAWPATH-*`.

Czego **nie** zrobię: nie wyślę żadnego żądania z Twoją sesją, nie enumeruję ID cudzych zgłoszeń,
nie złożę zgłoszenia bez Twojej decyzji, nie zapiszę żadnej wartości poświadczenia.

## 6. Drugi HAR, który jest wart więcej: HIVE (`dataannotation.pllum.org.pl`)

Jeśli organizator odpowie na pytanie o **konto testowe HIVE** (w pliku programu NASK
`own_or_test_accounts_only: true`, ale `no_dedicated_test_accounts_notice: false` — czyli nigdy nie
napisali, że kont testowych nie ma, więc pytanie jest uzasadnione), zrób **dokładnie ten sam zrzut**
po zalogowaniu: `/projects`, dowolny projekt, `/conversation/{recordId}`, `/account`, `/admin`.
Mam już zmapowane **71 tras klienta** z bundla (run 9/10), ale **0 literałów API** — ścieżki API
budowane są dynamicznie, więc bez HAR-a nie zgadnę ich, a HIVE to jedyny cel w programie, do którego
konkurencja nie wejdzie (zaproszeniowy).

## 7. Gotowy tekst pytania do organizatora (wklej w panelu `hack.cert.pl`)

> Dzień dobry, uczestniczę w edycji 11/2026. Proszę o potwierdzenie zakresu i zasad:
> 1. Czy `www.nask.pl` jest w zakresie? §5 wymienia `nask.pl`, a apex zwraca 302 na `www.nask.pl`.
> 2. Czy w zakresie są `panel.dns.pl`, `tracker.dns.pl`, `info-trace.116sos.pl` oraz
>    `116sos.multisite.lab.nob.pib.nask.pl`? (Wszystkie cztery są linkowane z serwisów §5, ale nie
>    ma ich w liście literalnej.)
> 3. Czy dla platformy HIVE (`dataannotation.pllum.org.pl`) istnieją **konta testowe** dla
>    uczestników? Serwis jest zaproszeniowy, więc bez konta nie da się zweryfikować żadnej hipotezy
>    dotyczącej autoryzacji, a §6 dopuszcza wyłącznie konta własne/testowe.
> 4. Czy testy z adresów IP usług CI (GitHub Actions) są dozwolone? Obecnie żądania z runnerów są
>    blokowane przez WAF — chcę ustalić, czy to zamierzona blokada, czy mogę prosić o allowlist.
> 5. Czy zgłoszenie dotyczące **samej platformy** `hack.cert.pl` (aplikacja konkursowa) jest
>    przyjmowane na zasadach ogólnych programu CERT, czy podlega osobnym zasadom?
>
> Z góry dziękuję. Testy wykonuję wyłącznie metodami odczytu (GET), ≤1 req/s, bez zmian stanu.

## 8. Stan bezpieczeństwa tej procedury

| ryzyko | środek |
|---|---|
| wyciek sesji do publicznego repo | `.gitignore`: `*.har`, `*.har.json`, `nask/har/raw/`; do gita tylko `sanitized/` i `mapa-api.json` |
| wyciek w czacie | zakaz wklejania treści HAR; plik wgrywany do workspace |
| wyciek przez narzędzie | asercja `assert_clean` skanująca wyjście pod kątem **każdej** wartości zobaczonej na wejściu + test jednostkowy |
| dane osobowe w ciałach | ciała odpowiedzi i żądań usuwane w całości (rozmiar + `sha256[:12]` + nazwy pól) |
| przypadkowe użycie Twojej sesji | nie wykonuję żądań z poświadczeniami; mapa służy do planowania żądań **nieuwierzytelnionych** albo do żądań, które **Ty** klikasz |
| powtórka żądań objętych STOP | `nask/run/WYKONANE.txt` + straż w workflow (korekta #54) |
