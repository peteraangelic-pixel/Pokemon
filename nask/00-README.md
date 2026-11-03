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
