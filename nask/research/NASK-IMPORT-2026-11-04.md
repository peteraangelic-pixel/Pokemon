# Import z NASK (arena/a29ca234-nask @ b2cf80a459) — 04.11.2026

Co zostało przeniesione do naszej gałęzi `arena/a450b00f-pokemon` i dlaczego.

## Narzędzia offline (w `nask/tools/`)

| plik/katalog | źródło | rola |
|---|---|---|
| `nask/tools/bundle_scan.py` + `test_bundle_scan.py` | `nask-lab/tools/` | Offline analiza publicznych bundle'ów JS: endpointy, parametry, ID-formaty (int/UUID/ULID/hash → pre-ranking IDOR), sekrety z filtrem entropii i allow-listą. Multiprocessing (Ryzen 9 5950X). Zero sieci. |
| `nask/tools/nasktriage/` (Rust) | `nask-lab/nasktriage/` | Offline analiza zrzutów HAR z **dwóch własnych kont**: `permission_asymmetry`, `idor_candidate`, `token_in_url`, `unauth_access`, `sensitive_cached`. Scope guard (§5), rate limiter ≤5 req/s (odmowa startu powyżej), Rayon. Brak modułu HTTP — nie da się „przypadkiem” wysłać żądania. 12 testów, clippy czysty. |
| `nask/tools/recon/` (Rust) | `nask-lab/recon/` | Rate-limited pasywny recon + probing (ureq z TLS, `redirects(0)`, scope guard, RateLimiter domyślnie 4,5 req/s, sufit 5 req/s). Komendy: Scope, Check, Sweep, Hypotheses, Scan, Paths. Rayon do analizy offline pobranych plików. |

Wszystkie narzędzia są **offline-first** — zgodne z naszym podejściem (najpierw analiza lokalna, ruch sieciowy tylko po wyjaśnieniu zakresu i na własnych kontach).

## Dokumenty strategii (w `nask/research/strategy/`)

| plik | źródło | zawartość |
|---|---|---|
| `NASK-STRATEGIA.md` | `STRATEGIA.md` | Plan wygrania: 5 programów, pula 1M PLN, max 20k za błąd, ranking ataków (A–H), podział ról agent vs user |
| `13-STRATEGIA-5-PROGRAMOW.md` | `drive_materials/13-...` | Strategia 5 programów, tabela stawek (NASK/CERT/Gov/mSzyfr/Władysławowo), ranking pieniędzy: 1. mwdb.cert.pl, 2. moje.cert.pl/n6portal.cert.pl, 3. hack.cert.pl, 4. komunikator.narodowy.gov.pl, 5. www.gov.pl, 6. Władysławowo |
| `16-MAPA-ENDPOINTOW-2026-11-03.md` | `drive_materials/16-...` | Mapa endpointów z rekonesansu pasywnego (endminer Rust+Rayon, 590 obserwacji): zglos-dezinformacje `/api/sendForm`, oad PowerBI embed, moje.cert.pl Django, komunikator Element Web/Matrix, n6portal OIDC/MFA/API-key |
| `17-IDEE-ZAROBEK-2026-11-03.md` | `drive_materials/17-...` | Idee na wygraną: kalibracja (skan bez sesji = 0 findingów), realny scenariusz 1–2 trafienia 4–9k zł/mies, podział ról (agent: mapy+narzędzia+drafty, user: konta+weryfikacja+submit) |
| `18-PLAN-NOCNY-2026-11-03.md` | `drive_materials/18-...` | Plan nocny 3/4.11: rekonesans pasywny, guardy (5 req/s, własne konta, zero DoS), granice roli agenta |
| `05-REGULAMIN-wyciag.md` | `drive_materials/05-...` | Wyciąg z regulaminu NASK: §3 czas (3–30.11.2026), §5 zakres (Tier 1/2 hosty), §6 zasady (5 req/s, własne konta), §7 nagrody (CVSS 4.0, 600/4000/9000/20000), §8 klasy i wyłączenia |

## Dane programowe (w `nask/research/programs/`)

| plik | zawartość |
|---|---|
| `2026-11.json` | Rekord publicznych regulaminów: 5 programów, 26 hostów dokładnych + 2 strefy wildcard, stawki, wykluczenia, daty edycji, limity req/s |
| `coordinator-findings-20261103.json` | Wynik koordynatora na 26 hostach: 208 żądań, 0 do zgłoszenia, 19 odrzuconych przez §8 (brak nagłówków, security.txt) |
| `templates/zgloszenie.md` | Szablon zgłoszenia (zakres, problem i wpływ, warunki wstępne, odtworzenie, dowody, klasyfikacja, propozycja poprawy) |

## Kluczowe wnioski z importu (dotyczą dalszej pracy)

1. **Skan anonimowy bez sesji = 0 findingów.** 26 hostów, 208 żądań, zero do zgłoszenia. Prawdziwe pieniądze (IDOR, mass assignment, SSRF z odczytem, upload→RCE) wymagają zalogowanych kont.
2. **Podział ról:** agent przygotowuje mapy, narzędzia offline i drafty hipotez z warunkami odrzucenia; **user zakłada konta, weryfikuje ręcznie w DevTools i wysyła zgłoszenia.** Agent nie zakłada kont, nie eksploatuje, nie wysyła zgłoszeń.
3. **Najlepsze cele (kolejność EV):** mwdb.cert.pl (serwer 2.20.0 — XSS Rich zamknięte), moje.cert.pl / n6portal.cert.pl (panele użytkownika, IDOR), hack.cert.pl (portal konkursu, `/api/v1`, `/users/me/profile/payout` — dane wypłat), komunikator.narodowy.gov.pl (mSzyfr, Element Web, ×2 własne konta, odseparowanie roomów).
4. **Konflikt prawny:** regulamin usługi `moje.cert.pl` (IV §4.2) zakazuje testowania zabezpieczeń mimo programu bug bounty — **nie testować `moje.cert.pl` do pisemnego wyjaśnienia organizatora**.
5. **www.nask.pl** poza literałem §5 (apex 302 → www) — pytanie do organizatora przed testem.
6. **Guardy:** ≤5 req/s (nasze narzędzia: 4,5 req/s max, domyślnie 1 req/s), tylko własne/testowe konta, zero cudzych domen, dyskrecja do poprawki.

## Następne kroki

- Użytkownik zakłada konto na `hack.cert.pl` + ewentualnie konta testowe w aplikacjach (mSzyfr ×2, moje.cert.pl, mwdb.cert.pl) — bez tego dalszy postęp w klasach płatnych jest zablokowany.
- Agent przygotowuje instrukcje PoC krok-po-kroku i drafty raportów na podstawie map z `16-MAPA-ENDPOINTOW-2026-11-03.md`.
- Przed jakimikolwiek testami sieciowymi: wyjaśnienie zakresu `www.nask.pl` i statusu `moje.cert.pl` z organizatorem.

Wszystko na gałęzi `arena/a450b00f-pokemon`; nie ingerowano w pracę innych sesji.
