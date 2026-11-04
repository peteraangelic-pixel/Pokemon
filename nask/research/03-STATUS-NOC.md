# Status pracy nocnej — 2026-11-03/04

## Co jest zrobione i wypchnięte

Ostatni mój commit w repo: **`72b9ce5`** (+ commit bota `595a132` z raportem 006).
Wszystkie przebiegi sieciowe: `nask/reports/probe-run004b.json`, `probe-run005.json`,
`probe-run006.json`.

**68 sond, 3 przebiegi, 0 potwierdzonych podatności.** Szczegóły i dowody:
`02-SONDY-004-006.md`.

Klasy sprawdzone i **zamknięte**:
- path traversal / LFI w `download-file` (20 wariantów, w tym kodowanie i schemat),
- SSRF przez proxy mediów i `/_next/image` (6 hostów),
- CORS na 8 endpointach (brak odbicia Origin),
- HIVE: SPA, brak `openapi.json`, brak listingu `/api/v1`,
- `dns.pl/api/*` (404), `116sos.pl/api/*` (502 — backend nie żyje).

## Co leży na dysku NIEWYPCHNIĘTE (bash padł przed commitem)

1. `nask/tools/surface/src/main.rs` — dodana **macierz `hosts × paths`** w planie
   sond (kompaktowy zapis szerokich, płytkich przebiegów; limit 400 rozwinieć).
2. `nask/run/PROBES.json` — **przebieg 007**, gotowy do uruchomienia:
   macierz 10 hostów × 8 ścieżek (`.env`, `.git/config`, `wp-config.php.bak`,
   `backup.zip`, `db.sql`, `server-status`) + 6 sond `..%2f` na `/api/media/`.
3. `nask/run/PROBES-008.json` — **przebieg 008**, zaległy: Wagtail/Django
   `/api/v2/pages|documents|images`, `/admin/`, `?rest_route=` na WordPressie.
4. `nask/research/02-SONDY-004-006.md` — dokument z dowodami dead-endów.

## Pierwsze polecenia po powrocie bash

```bash
cd /home/user/Pokemon
git add -A
git commit -m "probe: macierz hostow x sciezek + fala 3 (007) i 008 + raport 004-006"
git push origin arena/7911f950-pokemon     # uruchamia przebieg 007
```

Potem czytać `nask/reports/probe-run007.json` (bot commit sam).

## Czego NIE zrobiłem i dlaczego

- **Nie wysłałem formularza** na `zglos-dezinformacje` — POST tworzy prawdziwe
  zgłoszenie w NASK. To zmiana stanu po stronie organizacji, wymaga zgody
  użytkownika i jego przeglądarki (reCAPTCHA v3).
- Nie zgadywałem ścieżek paneli słownikiem — regulamin wyklucza raporty ze
  skanerów bez ręcznego potwierdzenia, a to jest dokładnie ten przypadek.
- `secure.edu.pl` (brak odpowiedzi) i `bezpiecznewybory.pl` (WAF 403) — nie
  da się ich ocenić tą metodą; to nie to samo co „czyste".

## Uczciwa ocena

Publiczna powierzchnia NASK jest utwardzona na klasy dostępne bez kont. Po 68
sondach nie mam dowodu podatności i nie będę tego nazywał sukcesem. Realne
szanse na nagrodę wymagają: (a) plików konfiguracyjnych/backupów — przebieg 007,
(b) **własnych kont** w HIVE i formularzu — IDOR/BAC, gdzie bez przeglądarki
i rejestracji nie wejdę, (c) serwera-kontroli do pełnego dowodu SSRF.
