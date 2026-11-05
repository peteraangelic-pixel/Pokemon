# Raport: 4.11, ciąg dalszy — runy 016–022

**493 sondy łącznie (110 w tej turze), 0 potwierdzonych podatności.**

Ta tura miała sens, bo znalazłem **błąd metodyczny we własnym podejściu** i naprawiłem
go, a nie dlatego, że przyniosła podatność. Nie przyniosła.

---

## 1. Co sprawdziłem w repo NASK

| Gałąź | Stan | Wartość |
|---|---|---|
| `main` (`e0a562e`) | „Initial commit" + README | **zero** |
| `arena/a29ca234-nask` (`b2cf80a`) | nowy commit: kopie plików 13–18 z Dysku | pliki już przeczytane (15 i 16 w całości) — **zero nowej wiedzy** |
| `codex/multi-program-lab-20261103` (`a4fb58d`) | bez zmian | bez nowości |

W środku: `naskhunt/checks.json` (sweep ID na `science /api/downloadFile` — zamknięte),
`recon/hypo.rs` (`.git/HEAD`, `.env`, actuator, bypass Next.js — wszystkie zamknięte).
**Repo nie zawiera niczego nowego o podatnościach.** Mówię to wprost, żeby nie
sprzedawać Ci wrażenia pracy tam, gdzie jej nie było.

## 2. Błąd metodyczny, który znalazłem w sobie

Wszystkie 404 na `dns.pl` sprawdzałem **wyłącznie GET-em**. A 404 na GET **nie dowodzi,
że trasa nie istnieje** — może przyjmować tylko POST. Uczciwa odpowiedź brzmiała
„nie wiem", a ja zapisałem „zamknięte". To była nieuprawniona pewność.

Dodałem do narzędzia metody GET/HEAD/**OPTIONS** z allowlistą **w kodzie**, plus blokujący
selftest, który dowodzi, że `POST/PUT/PATCH/DELETE/TRACE/CONNECT` **są nieosiągalne**.
To gwarancja binarki, nie moja obietnica.

**Wynik tego podejścia (run 016):**

| Host | OPTIONS | Wniosek |
|---|---|---|
| `zglos /api/sendForm` | **204, `Allow: OPTIONS, POST`** | trasa potwierdzona **bez wysłania POST** |
| `science /api/contact` | **405, `Allow: POST`** | potwierdzone, tylko POST |
| `116sos /api/centres` | 401 | to nie metoda — auth/upstream |
| **`dns.pl` (17 ścieżek)** | **200 `text/html` ~51 KB — wszystkie** | OPTIONS **bezużyteczne**: front controller Drupala połyka je i zwraca stronę główną, także dla żywego `/api/zone-stats` |

Więc pytanie „czy martwe trasy `dns.pl` istnieją dla POST" **pozostaje otwarte** — i tak
je zapisuję, zamiast udawać, że zamknąłem.

## 3. Nowa metoda: 405 zamiast 404 (i dlaczego działa)

Na `science.nask.pl` nieistniejąca trasa daje **404**, a trasa tylko-do-POST daje **405**.
Router **odróżnia te przypadki** — więc endpointy zapisu ujawniają się bez wysyłania POST.

Run 018 przeczesał 9 nazw (`newsletter`, `subscribe`, `zglos`, `report`, `message`,
`upload`, `form`, `search`) — **wszystkie 404 poza jedną**.

## 4. Realne odkrycie: `science.nask.pl/api/search`

```
/api/search?q=abc        → 400 {"error":"Query must be at least 3 characters"}
/api/search?query=abc    → 200 application/json
```

**Parametr to `query`, nie `q`.** Wszyscy — łącznie ze mną — sprawdzali `q`, dostawali 400
i uznawali trasę za niedziałającą albo zamykali temat „brak refleksji". Wystarczyło zmienić
nazwę. To pierwsza działająca trasa z parametrem na `science` (Tier 2).

Potem **39 sond** ją rozłożyło:

| Test | Wynik |
|---|---|
| `query=abc` / `zzqx9probe` / `<b>` / `'` / `''` / `'--` / `%_` | **200, identyczne 49 B** `{"pageData":[],"page":0,"perPage":0,"lastPage":0}` |
| `query=` puste, `query=a`, `query[]=abc` | 400, min. 3 znaki |
| `UNION SELECT` | **błąd transportu** — WAF zrywa połączenie |
| `perPage` / `per_page` / `perpage` / `sort` / `locale` / `limit` | **ignorowane** |
| `page=0` / `abc` / `-1` / `999999999` / `1.5` | **400 `{"error":"Invalid pagination"}`** |
| `page[]=1`, `query=abc&query=xyz` | 200, brak refleksji |

**Werdykt: brak refleksji, brak wycieku błędu, walidacja ścisła, zero 500.** Trasa zwraca
pustą listę dla każdego wejścia. Zgodnie z §8 próba zablokowana przez WAF **nie jest
podatnością**. **Nie ma tu zgłoszenia** — i mam to udowodnione 39 sondami, a nie założone.

## 5. Zamknięte z dowodem w tej turze

| Cel | Dowód |
|---|---|
| **`dns.pl` parametry ścieżki** | `pl`→200 (283 B), `en`→200 (276 B), a `zzqx9`/`PL`/`pl'`/pusty→**404**. Traversal `..%2f..%2fzone-stats` dekoduje się do `/zone-stats` i trafia w soft-404 Drupala — **brak ucieczki**. Run 017, 9/9 odpowiedzi. |
| **`dns.pl` HEAD/OPTIONS** | 200 `text/html` — API obsługuje **wyłącznie GET**; inne metody spada do front controllera. |
| **`pllum.org.pl /api/_content/query`** | 200 JSON, ale tylko **3 wpisy** (`/`, `/form`, `/partners`), wszystkie `_draft:false`; `where={"_draft":true}` → **`[]`**. Brak treści niepublicznych. |
| **`bezpiecznymiesiac.pl`** | żyje (200, 93 KB, Next.js), ale `/api/`, `/api/search/`, `/api/contact/`, `/api/<losowe>/` → **404**. **Brak warstwy API.** Pierwszy raz sondowany. |
| **`science /api/upload` i 8 innych** | 404 — metoda 405-vs-404 potwierdza brak endpointów zapisu. |

## 6. Czego nie zrobiłem i dlaczego

- **Ani jednego POST.** Kontaktówka `science /api/contact` i `zglos /api/sendForm` są
  potwierdzone jako POST-only, ale ich wywołanie tworzy prawdziwą wiadomość do CERT.
- **Ani jednego żądania poza 12 hostów.**
- **Ani jednego zgłoszenia** — nie mam PoC, a regulamin odrzuca scenariusze teoretyczne.

## 7. Wniosek

**493 sondy, 0 podatności.** Po tej turze powierzchnia anonimowa jest wyczerpana
dokładniej niż przed nią: doszły całe hosty (`bezpiecznymiesiac`), nowa trasa
(`/api/search?query=`) i rozstrzygnięte pytania, które wcześniej zostawiłem
z nieuprawnioną pewnością.

**Dalsze sondowanie anonimowe nie przyniesie pieniędzy.** Nie dlatego, że przestaję
szukać — dlatego, że nie ma już gdzie. Każda klasa, za którą ten program płaci
(IDOR/BAC 9–20 tys.), jest **z definicji** za loginem. Bez konta nie da się nawet
zmierzyć, czy autoryzacja istnieje.

*Surowe dane: `nask/reports/probe-run016.json` … `probe-run022.json`.
Narzędzie: `nask/tools/surface` — allowlista metod wymuszona w kodzie i selftestem.*
