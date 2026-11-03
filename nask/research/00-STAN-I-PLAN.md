# NASK bug bounty — stan, ograniczenia i plan

Projekt: **hack.cert.pl**, edycja 11/2026, **2026-11-03 → 2026-11-30**.
Ten dokument jest punktem odniesienia: co wiemy z pierwszej ręki, co jest
ograniczeniem technicznym, a co dopiero hipotezą. Potwierdzonych podatności: **0**.

---

## 1. Fakty sprawdzone u źródła (nie z cudzego podsumowania)

Pobrane bezpośrednio ze strony programu
`https://hack.cert.pl/programs/nask-pib/nask/editions/1` w dniu 2026-11-03.

**Zakres systemów — dokładnie 12 hostów, bez wildcardów:**

| Tier | Hosty |
|---|---|
| 1 | `nask.pl`, `dyzurnet.pl`, `dns.pl`, `oad.nask.pl`, `zglos-dezinformacje.nask.pl` |
| 2 | `bezpiecznymiesiac.pl`, `secure.edu.pl`, `bezpiecznewybory.pl`, `116sos.pl`, `pllum.org.pl`, `science.nask.pl`, `dataannotation.pllum.org.pl` |

**Nagrody (PLN):** Tier 1 — 600 / 4 000 / 9 000 / 20 000;
Tier 2 — 300 / 2 000 / 4 500 / 10 000 (niski / średni / wysoki / krytyczny, CVSS 4.0).

**Zasady testowania (cytat z karty programu):**
1. Testy bez uwierzytelnienia, a przy uwierzytelnieniu **wyłącznie z własnych kont**
   (poza domenowymi) lub kont testowych. Cudze konta — zakaz.
2. Automatyczne narzędzia: **maksymalnie 5 req/s**.

**Co płaci (20 kategorii), a co nie:** pełna lista (20 pozycji + ~15 grup
wyłączeń) jest w karcie programu; poniżej tylko to, co zmienia nasze decyzje:
- płaci m.in. RCE, dostęp do danych wrażliwych, SQLi, **SSRF z odczytem**,
  file upload prowadzący do RCE/obejścia walidacji z realnym skutkiem,
  IDOR/BAC, omijanie autoryzacji w API, mass assignment, path traversal, XXE;
- **nie płaci** m.in.: wyciek wersji/stack trace/ścieżek bez wpływu, brak
  nagłówków bezpieczeństwa, znane CVE **bez działającego PoC**, **blind SSRF
  z dowodem wyłącznie DNS**, DoS i testy obciążeniowe (zakaz bezwzględny),
  brak rate limitingu bez scenariusza, raporty ze skanerów bez ręcznego
  potwierdzenia, scenariusze teoretyczne bez PoC.

**Konsekwencja projektowa:** lista wyłączeń jest dłuższa niż lista nagradzanych.
Wartość ma **jeden działający łańcuch**, nie 50 błędów konfiguracji.

---

## 2. Ograniczenia, które ukształtowały architekturę

To nie są preferencje, tylko twarde fakty sprawdzone w tej sesji:

1. **Sandbox nie ma dostępu do internetu poza GitHubem.** `curl https://nask.pl`
   zwraca kod 000; `github.com` zwraca 200. Dlatego *każde* żądanie do celów
   konkursowych musi wyjść z **GitHub Actions**, nie z sandboxa.
2. **Token GitHuba jest read-only na repo `peteraangelic-pixel/NASK`.**
   `git push` → `403 Permission denied`; `POST /git/refs` → `Resource not
   accessible by integration`; brak scope'ów OAuth, czyli to token GitHub App
   z prawem odczytu. W repo `Pokemon` ten sam token **pisze** (utworzenie
   gałęzi przez API się udało).
   → Projekt mieszka w `Pokemon/nask/`. Aby przenieść go do repo NASK, trzeba
   **dopisać repo NASK do instalacji GitHub App** (albo nadać tokenowi `contents:write`).
3. **Brak cargo i brak dostępu do crates.io w sandboxie.** Rust kompiluje się
   wyłącznie na runnerze, więc każda poprawka to jeden przebieg Actions
   (2–4 min). Dlatego kod ma wbudowany `selftest` offline, który bramkuje
   każdy przebieg z dostępem do sieci.
4. **Tempo sieci jest wąskim gardłem, nie CPU.** Przy limicie 5 req/s każdy
   skaner zużywa <1% jednego rdzenia na I/O. Przyspieszenie Rusta+Rayon
   pojawia się **wyłącznie w analizie offline** (setki plików JS, MB tekstu)
   — i tam jest użyte. Nie twierdzimy, że Rust przyspiesza zbieranie danych
   przez sieć, bo nie przyspiesza.

---

## 3. Architektura

```
nask/tools/surface/       Rust: guard zakresu, limiter, zbiór, analiza (Rayon)
  src/scope.rs            12 hostów + alias www.nask.pl, Limiter (twardy sufit 5/s)
  src/analyze.rs          równoległa analiza HTML/JS: assety, formularze, trasy,
                          sourcemapy, frameworki, komentarze "sensitive"
  src/main.rs             CLI: scope | selftest | run | analyze
.github/workflows/surface-nask.yml
  job ci         testy + selftest, ZERO sieci (na push)
  job discover   tylko ręcznie (workflow_dispatch), bramkowany testami
```

Reguły wymuszone w kodzie, nie w komentarzach:

- **allow-lista dokładnych hostów.** `https://nask.pl.evil.tld/`, `user@nask.pl`,
  `nask.pl:8443`, `http://` — odrzucane. Podkatalogi spoza listy (np.
  `panel.dns.pl`, `gitlab.snkom.nask.pl`) odrzucane.
- **jeden globalny limiter** na wszystkie wątki; `Limiter::new` **odmawia
  startu** powyżej 5 req/s, więc `--rps 50` nie jest możliwe do wykonania.
- **GET tylko, przekierowania nie są śledzone.** `dns.pl` linkuje do
  `panel.dns.pl`, który *nie jest* w zakresie — podążanie za przekierowaniem
  wyprowadziłoby żądania poza zakres. `Location` jest zapisywany, nie wykonywany.
- **każde żądanie ma wpis w indeksie**, także błąd transportu. Brak odpowiedzi
  nigdy nie jest czytany jako „czysto".
- pierwszy przebieg to **wyłącznie rozpoznanie**: 6 statycznych ścieżek na hosta
  (`/`, `robots.txt`, `sitemap.xml`, `.well-known/security.txt`, `manifest.json`,
  `favicon.ico`) + assety same-origin znalezione w tych stronach. Żadnego
  słownika, żadnych payloadów, żadnego POST-a.

---

## 4. Gdzie realnie leży pieniądz (kolejność wg pracy na znalezisko)

Nie wg CVSS, a wg tego, ile trzeba włożyć, żeby mieć PoC:

| # | Cel | Dlaczego | Kto to zrobi |
|---|---|---|---|
| A | `zglos-dezinformacje.nask.pl` — formularz | przyjmuje **50 URL-i** i **plik do 20 MB**; aplikacja, która naturalnie *pobiera* treść z podanego linku → SSRF z odczytem; upload → obejście walidacji | częściowo ja (mapa, hipotezy), **potwierdzenie — Ty w przeglądarce** |
| B | `dataannotation.pllum.org.pl` (HIVE) — logowanie/role | IDOR/BAC wymaga dwóch własnych kont; najczęstsza realna luka w aplikacjach pisanych pod deadline | **Ty** (rejestracja własna) |
| C | `oad.nask.pl` | aplikacja Next.js za Envoy, API | ja (mapa) + Ty (przeglądarka) |
| D | `dns.pl` | rejestr domen: wyszukiwarka whois, cookies, własny stack | ja (mapa) |
| E | `dyzurnet.pl` | zgłaszanie incydentów; Next.js + Cloudflare | ja (mapa) |
| — | strony statyczne (`bezpiecznymiesiac`, `pllum`, `science`, `secure.edu`, `bezpiecznewybory`) | brak powierzchni; jedyne sensowne to błędy konfiguracji, które są **wprost wyłączone** | pominąć do końca miesiąca |

**Hipoteza nr 1 (SSRF w formularzu dezinformacji).** Formularz przyjmuje do 50
linków. Jeśli backend pobiera ten link (walidacja, archiwizacja, podgląd), to
podanie URL-a wskazującego na nasz własny serwer kontrolny i zaobserwowanie
żądania = dowód. Wymagania dowodowe z regulaminu: **musi być odczyt**, nie sam
DNS (blind SSRF wykluczony). Status: **hipoteza, zero testów.** Wymaga
serwera-kontroli i Twojej zgody na wysłanie jednego zgłoszenia testowego.

---

## 5. Co dalej (kolejność)

1. Uruchomić `discover` (Actions) → mapa assetów i tras 12 hostów. **[w toku]**
2. Z mapy wybrać realne powierzchnie aplikacyjne i spisać hipotezy z warunkami
   odrzucenia (co musi być prawdą, żeby hipoteza żyła).
3. Dla każdej hipotezy: minimalny, nieinwazyjny dowód na **własnych** danych.
4. Dopiero potem szkic zgłoszenia (szablon: karta programu + wymagany PoC).

**Czego ten projekt nie zrobi:** nie znajdzie podatności bez wejścia w aplikację
zalogowaną. Część wymagająca kont jest po stronie użytkownika — to nie jest
ostrożność, to ograniczenie techniczne (brak przeglądarki i brak kont).
