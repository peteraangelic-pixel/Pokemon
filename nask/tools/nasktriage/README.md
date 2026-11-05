# nasktriage

Offline'owa analiza zrzutów HAR z **dwóch własnych kont** — szuka hipotez na IDOR / złamaną
kontrolę dostępu. **Nie wysyła żadnych żądań sieciowych** i nie zapisuje treści odpowiedzi.

## Po co

Limit 5 żądań/s i zakaz outputu skanerów bez ręcznego PoC (`§8 poz. 14`) sprawiają, że
automatyczne skanowanie jest bezwartościowe. Wartościowe jest **porównanie tego, co widzi konto A,
z tym, co widzi konto B** — i to robi to narzędzie, na materiale, który i tak zbierasz klikając.

## Użycie

```bash
# 1. w przeglądarce: DevTools → Network → Preserve log → przejdź aplikację → Save all as HAR
#    (zalogowany jako konto A, potem jako konto B)

cargo run --release -- scan hive-A.har hive-B.har \
    --account A:sessionid=AAA --account B:sessionid=BBB \
    --scope scope.example.json \
    --md raport.md --json raport.json
```

`--account L:fragment` — fragment nagłówka `Cookie`, który identyfikuje konto. Wystarczy
unikalny kawałek wartości ciasteczka sesyjnego.

## Co zwraca

| flaga | znaczenie |
|---|---|
| `permission_asymmetry` | ten sam endpoint: jedno konto 2xx, drugie 401/403 |
| `idor_candidate` | endpoint z `{id}`: ≥2 różne identyfikatory, wszystkie 2xx, identyczny zestaw kluczy JSON |
| `token_in_url` | parametr nazywa się jak token/klucz/sesja — wycieka w logach i `Referer` |
| `unauth_access` | żądanie bez ciasteczka dostało 2xx na endpoincie, którego używa konto |
| `sensitive_cached` | `Cache-Control: public, max-age=…` przy JSON-ie lub `Set-Cookie` |

Wszystkie pozycje to **hipotezy**. Potwierdzenie = Twoje jedno ręczne żądanie, na własnych
syntetycznych danych.

## Bezpieczniki

- `scope.rs` — host spoza listy `§5` jest odrzucany; wildcardy i sufiksy nie przechodzą.
- `rate.rs` — wspólny limiter; `TokenBucket::new(5.1)` **zwraca błąd**, nie ostrzeżenie.
- brak modułu HTTP — nie da się „przypadkiem” wysłać żądania.

## Testy

```bash
cargo test --all-targets     # 12 testów: zakres, limiter, parser HAR, analiza, render
cargo clippy --all-targets   # 0 ostrzeżeń
```

CI: `.github/workflows/nask-triage-ci.yml` (kompilacja → clippy → testy → build → dymny test CLI).
Logi z przebiegu lądują w `ci/` w katalogu głównym repo.
