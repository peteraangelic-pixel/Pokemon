# NASK Bug Bounty — narzędzie i strategia

Konkurs: [hack.cert.pl](https://hack.cert.pl), edycja 11/2026, 3–30.11.2026, pula 100 000 zł.
Zakres: 12 domen (5 w Tier 1, 7 w Tier 2). Regulamin: §5 (zakres), §6 (max 5 req/s), §7 (stawki), §8 (co płaci).

- **`STRATEGIA.md`** — pełny plan: mapa celu, kolejność ataków, stawki, kalibracja oczekiwań
- **`recon/`** — narzędzie w Rust (Rayon), 16 testów jednostkowych

## Szybki start

```bash
cd recon
cargo test --release          # 16 testów: guard zakresu, catch-all, limiter, stawki
cargo build --release
./target/release/naskrecon scope       # 12 domen + stawki z regulaminu
./target/release/naskrecon sweep       # przegląd nagłówków i technologii
./target/release/naskrecon hypotheses  # ekspozycje plików z odejmowaniem catch-all
```

## Trzy zabezpieczenia wbudowane w narzędzie

1. **Sufit 4,5 req/s** wspólny dla wszystkich wątków. `--rps 6` → program odmawia startu i wychodzi z kodem 2.
2. **Guard zakresu** — host spoza §5 nie dostanie żądania; `check <host>` zwraca kod 1.
3. **Odejmowanie catch-all** — znaleziskiem jest tylko odpowiedź nie-HTML, różna od wzorca
   pobranego z losowego nieistniejącego URL-a. Bez tego SPA generuje 200 fałszywych trafień.

## Status rekonesansu (2026-11-03)

204 żądania na 12 domenach, wynik: **zero realnych ekspozycji**. To poprawny wynik negatywny —
wszystkie podejrzane ścieżki zwracały catch-all SPA. Powierzchnia ataku jest w aplikacjach
za logowaniem, nie w plikach konfiguracyjnych.

**Nie testujemy niczego poza 12 domenami z §5.** `*.snkom.nask.pl`, `*.ebsi.nask.pl`,
`zakupy.nask.pl`, `zamowienia.nask.pl`, `taskmanagement.nask.pl`, `ksod.nask.pl`,
`certyfikacja.nask.pl` — poza konkursem.

## Konfiguracja GitHub Actions

Workflow `.github/workflows/recon.yml` kompiluje, testuje i (na żądanie) uruchamia skan pasywny.
Wymaga tylko `workflow_dispatch` albo pusha do `main`. Ustawienia repo → Actions → Read and write
permissions, jeśli chcesz commitem zapisywać wyniki.
