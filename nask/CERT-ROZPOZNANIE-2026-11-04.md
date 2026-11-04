# CERT Polska — rozpoznanie pozostałych celów (04.11.2026)

Uzupełnienie do `CERT-MOJE-ROZPOZNANIE-2026-11-03.md`. Zakres: program CERT Polska na hack.cert.pl, edycja 11/2026 (03–30.11), stawki Tier 1 600/4000/9000/20000 zł, pula 100 000 zł. Wszystkie obserwacje poniżej pochodzą z publicznych źródeł, cudzych raportów gałęzi zespołu oraz publicznie dostępnych dokumentów regulaminowych — **nie wykonano żadnych aktywnych sond ani skanów podatności**. Zero potwierdzonych luk.

## Cele w programie CERT Polska (Tier 1)

Z §5 regulaminu CERT Polska (pełny tekst PDF w `NASK@codex/multi-program-lab-20261103`):

- `cert.pl`, `m.cert.pl`, `incydent.cert.pl`, `moje.cert.pl`, `n6portal.cert.pl`, `mwdb.cert.pl`, `hack.cert.pl` — Tier 1
- `*.cert.pl`, `ctf.hack.cert.pl` — Tier 2
- Wykluczone: `*.hack.cert.pl` poza samym `hack.cert.pl`, `*.lab.cert.pl`

### mwdb.cert.pl — MWDB (baza złośliwego oprogramowania)

Źródło publiczne: `https://github.com/CERT-Polska/mwdb-core`, commit `50d8b15` (30.10.2026), 172 plików `.py`, ~8,8 tys. linii w `mwdb/resources`. Przegląd kodu wykonany przez sesję Gemma-A (`nask/PRZEGLAD-KODU-MWDB.md`).

**Ustalenia:**
- Jedna wspólna ścieżka autoryzacji: `access_object → Object.access`. Klasyczny IDOR po identyfikatorze jest **mało prawdopodobny** — kod ma jedną, wspólną i poprawną ścieżkę kontroli dostępu do obiektu.
- Nie znaleziono endpointu pobierającego obiekt po ID z uwierzytelnieniem, ale bez sprawdzenia właściciela (poza dwiema publicznymi metodami OAuth wymagającymi zalogowania).
- Prawdziwe ryzyko to **konfiguracja wdrożenia**, nie kod: capabilities `access_all_objects`, `share_queried_objects`, `sharing_with_all`, `manage_users`. Testowanie ich wymagałoby cudzych uprawnień (§8 poz. 1) — niedozwolone.
- Zostaje warstwa logiki: `share.py` (semantyka `give_access`, grupy), `oauth.py` (865 linii, przepływy `state`/`redirect_uri`, największa powierzchnia), `remotes.py` (kilka endpointów biorących identyfikator), `api_key.py` (zakres tokena).

**Stan 04.11 10:14:** `GET https://mwdb.cert.pl/api/server` zwraca `server_version` = **2.20.0** — poprawka XSS w atrybutach Rich (mwdb-core #1272/#1274) **jest wdrożona**. Wątek zamknięty (oszczędzone 10 min pracy z kontem).

**Wniosek:** mwdb to najlepsze miejsce do **odczytu kodu offline**, ale szansa na trafienie w miesiąc jest niższa niż początkowo zakładano. Nie polować na IDOR bez dwóch własnych kont i wyjaśnienia scope.

### n6portal.cert.pl — portal N6 (dane o zagrożeniach)

Też otwarte źródła: `https://github.com/CERT-Polska/n6portal`. Skaner `nasktriage` (offline, zero żądań) nadaje się do analizy: `python3 -m nask.tools.authz_scan <ścieżka>/src --only-suspect`.

**Mapa powierzchni (z porannego pomiaru Gemmy, 902 obserwacji, n6portal: 74):**
- `/login/oidc`, `/oidc/refresh_token` — przepływ OIDC
- MFA flow: `/mfa_config/confirm`
- `/api_key` — zarządzanie kluczami API
- `/search/events/sources` — wyszukiwanie zdarzeń
- `/incidents` — incydenty

**Kierunki:** authz / omijanie MFA, klucze API. Wymaga konta dla głębszych testów. Analiza kodu offline jest bezpiecznym punktem startowym.

### hack.cert.pl — sama platforma konkursowa (Tier 1)

Zebrane z bundle'a JS (mapa `/api/v1`, sesja Gemmy):
- `/users/{id}/view`, `/users/{id}/role`, `/users/{id}/email` — dane użytkownika
- `/users/me/profile/payout` — **dane wypłat** (najbardziej obiegujący cel w całym konkursie: sama platforma, widoczne dane wypłat)
- `/auth/session/activity` — aktywność sesji

**Uwaga:** to program **CERT Polska**, nie NASK. Nie mieszać programów w jednym rejestrze zgłoszeń (duplikat = zero, §7 pkt 9 NASK; ryzyko wewnętrznego duplikatu w zespole 6 sesji).

Sonda S7 (Gemma-A): 4 trasy × 2 identyfikatory × 2 prefiksy (``, `/api/v1`) — żadna nie zwróciła 2xx z danymi bez sesji. Wariant **z sesją pozostaje otwarty** i wymaga konta.

### incydent.cert.pl

Zrywa połączenie z runnerów GitHub Actions (WAF blokuje chmurę, status 0). Publiczny URL `https://incydent.cert.pl/instrukcje-email/gmail` zwrócił 404 (indeks wyszukiwarki może być nieaktualny). Testowalne tylko z sieci domowej, nie z Actions.

## Konflikt prawny — moje.cert.pl (istotne dla naszej gałęzi)

Regulaminusługi `moje.cert.pl`, część IV pkt 4.2, zakazuje „działań mających na celu testowanie możliwości przełamania lub ominięcia zabezpieczeń” — mimo że host jest w programie bug bounty. To potencjalna dyskwalifikacja, nie drobiazg formalny.

**Nie testować `moje.cert.pl` uwierzytelnionym do czasu pisemnego wyjaśnienia od organizatora.** Dodatkowo `moje.cert.pl` i pozostałe hosty `cert.pl` zrywają połączenie z naszego środowiska (status 0), więc i tak są niemierzalne z Actions.

Szczegóły: `nask/CERT-MOJE-ROZPOZNANIE-2026-11-03.md`.

## Co nasza gałąź (a450b00f) już ma

| plik | rola |
|---|---|
| `CERT-MOJE-ROZPOZNANIE-2026-11-03.md` | publiczne powierzchnie `moje.cert.pl` (rejestracja, regulamin, poradnik zespołów, kolekcja API) |
| `lab/auth_matrix.py` + testy | offline’owa analiza kodów statusu i relacji zasobu (prywatny/współdzielony/nieznany); 200/200 to nie IDOR |
| `lab/har_triage.py` + testy | offline’owa klasyfikacja obserwacji z HAR dla dwóch własnych kont: `permission_asymmetry`, `idor_candidate`, `token_in_url`, `unauth_access`, `sensitive_cached`; bez sieci, bez prawdziwych danych |
| `lab/safe_client.py` | ograniczony klient statusów korzeniowych, dry-run domyślnie, nie skaner |
| `lab/audit_events.py` | offline’owa analiza znaczników czasowych (nie dowodzi zgodności z limitem) |

## Kolejne kroki (dla naszej gałęzi)

1. **Ustalić CI** — oba ostatnie commity (`a143b20`, `bb17ccd`) kończą się failure; lokalnie 35/35 testów OK. Nie mogę pobrać logów CI (wymaga logowania). Podejrzenie: krok 7 workflow (`unittest discover` lub `ffi_smoke.py`) w środowisku Actions. Do wyjaśnienia po uzyskaniu dostępu do logów.
2. **Rozpoznanie CERT uzupełnione** — ten dokument (`CERT-ROZPOZNANIE-2026-11-04.md`). Kolejny krok zależy od wyjaśnienia prawnego (`moje.cert.pl`) oraz od konta na `hack.cert.pl` (dla `mwdb`, `n6portal`, `hack.cert.pl` — wszystkie wymagają zalogowania dla wartościowych testów).
3. **Nie testować aktywnie** żadnego z powyższych hostów bez jawnej zgody użytkownika i wyjaśnienia zakresu. Wszystkie wymagają dwóch własnych kont dla IDOR/BAC — ich brak to twarda bariera, nie brak pomysłu.

Wszystkie commity na `arena/a450b00f-pokemon`; ostatni [CI 41736316785 success](https://github.com/peteraangelic-pixel/Pokemon/actions/runs/41736316785) dla `40964ea`; bieżący [CI 41812843345 failure](https://github.com/peteraangelic-pixel/Pokemon/actions/runs/41812843345) dla `bb17ccd`.
