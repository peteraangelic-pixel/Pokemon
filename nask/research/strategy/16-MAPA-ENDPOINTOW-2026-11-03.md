# MAPA ENDPOINTÓW — rekonesans pasywny 2026-11-03 (noc)

**Metoda:** 3 GET-y na strony główne + 46 publicznych bundli JS (1 req/s, UA przeglądarki),
analiza OFFLINE przez `rust/endminer` (590 obserwacji / 71 ms na 2 rdzeniach).
**Zero testów aktywnych, zero POST, zero probowania endpointów.** Log: `LOG-POBRAN-20261103.md`,
surowe dane: `evidence-20261103/`, pełny wynik: `MINER-WYNIKI-20261103.jsonl`.

## zglos-dezinformacje.nask.pl (NASK T1, priorytet #1 — decyzja Codexa)

Next.js (App Router, `[locale]`). Jedyny wywoływany API widoczny w kodzie klienta:

| Obserwacja | Znaczenie |
|---|---|
| **`/api/sendForm`** | przyjęcie zgłoszenia o dezinformacji (najpewniej multipart z załącznikiem) |
| routing `[locale]` | `/pl`, `/en` — szum minifikacyjny `/${e}` |
| Next.js server actions | fragmenty obsługujące komunikaty formularza |

**Hipotezy (każda z warunkiem odrzucenia — do weryfikacji RĘCZNEJ, na własnych danych testowych):**

1. **Walidacja załącznika w sendForm** — co akceptuje: rozszerzenie? MIME? magic bytes? rozmiar?
   Gdzie ląduje plik i czy jest osiągalny publicznie (bez auth)?
   *Odrzucenie:* serwer przyjmuje wyłącznie obrazki/PDF ≤ limitem, pliki lądują w storage
   bez dostępu publicznego → brak wpływu, brak zgłoszenia.
2. **Mass assignment w JSON/multipart** — czy pola spoza formularza (np. `role`, `status`,
   `admin`, `internalNote`) przechodzą i zmieniają przetwarzanie?
   *Odrzucenie:* serwer whitelistuje pola (typowe w Next) → nic.
3. **SSRF z pola URL** — formularz zgłasza URL dezinformacji; czy serwer WERYFIKUJE treść
   (fetchuje adres)? Tylko jeśli kod/błędy na to wskażą. Samo pole URL ≠ SSRF.
   *Odrzucenie:* brak dowodu fetchowania po stronie serwera → nie testować dalej na ślepo.
4. **Brak weryfikacji typu / spam → odrzucone przez §8** (spam i brak rate-limitu NIE są
   zgłaszalne). Nie marnować czasu.

## oad.nask.pl (NASK T1)

| Obserwacja | Znaczenie |
|---|---|
| **PowerBI `app.powerbi.com/reportEmbed?...autoAuth=true`** | publicznie osadzony raport statystyczny |
| `/zglos-dezinformacje` | to samo okno formularza (spójność) |
| `/_next/image`, `/media/` | assety |

**Hipoteza (niska próg sprawdzenia, czysto pasywna):** otworzyć embed w przeglądarce i
obejrzeć, CO raport pokazuje — jeśli ma służyć wyłącznie do statystyk, a udostępnia
rekordy z danymi osobowymi/dane niepubliczne bez logowania, to klasa „dane wrażliwe / masowy odczyt”.
*Odrzucenie:* raport pokazuje agregaty → zero (i tak jest najbardziej prawdopodobne).

## www.nask.pl (NASK T1)

Portal treściowy (WP-like + Next). API: tylko zewnętrzne (analytics Azure, share-countery).
Klasa treściowa — niski priorytet zgodnie ze strategią (jak www.gov.pl).

## Wnioski dla dalszej nocy

- Serce programu NASK to **`/api/sendForm`** — ale bez konta i bez PoC nie ma zgłoszenia;
  testy wyłącznie na własnych danych (np. plik-obrazek z dopiskiem test).
- Prawdziwe pieniądze edycji są poza NASK w aplikacjach Z SESJAMI: mwdb.cert.pl,
  moje.cert.pl, n6portal, hack.cert.pl (sam portal — najmłodszy kod), mSzyfr
  (2 WŁASNE konta → testy odseparowania rozmów = IDOR/ATO, klasa 9–20k).
- Następne hosty do tego samego minera (pasywnie): moje.cert.pl, n6portal.cert.pl,
  hack.cert.pl, komunikator.narodowy.gov.pl, science.nask.pl, 116sos.pl.

---

# DODATEK (ta sama noc, po rozszerzeniu rekonesansu): hack.cert.pl, moje.cert.pl, mSzyfr

## hack.cert.pl — PEŁNA MAPA `/api/v1` z bundle SPA (index-B5IFYBO_.js)  ← NAJWAŻNIEJSZE

Portal konkursu jest w zakresie T1 (`*.cert.pl`). SPA ujawnia komplet endpointów.
Kluczowe rozdzielenie: **`reports/{id}` = widok PROGRAMU**, **`me/reports/{id}` = widok UCZESTNIKA**.

```
/api/v1/auth/{me,session,session/activity,logout}     /api/v1/me/reports{,/rejected-reports,/creation-eligibility}
/api/v1/me/reports/{id}{,/submit,/submit-response}    /api/v1/me/reports/{id}/attachments{,/{aid}}
/api/v1/me/reports/{id}/reward-offers/latest          /api/v1/me/reports/{id}/reward-offers/{rid}/accept
/api/v1/reports/{id}  (staff) {,/classification,/reject,/close,/resume-review,
    /start-review,/accept-analysis,/accept-report,/forward-for-verification,
    /return-from-verification,/return-analysis-for-rework,/request-participant-response}
/api/v1/reports/{id}/attachments/{aid}/download       /api/v1/reports/{id}/events{,/filter-options}
/api/v1/reports/{id}/internal-notes{,/{nid},/authors/{uid}/avatar}
/api/v1/reports/{id}/reward-offers{,/{rid}}{,/activate,/cancel}
/api/v1/reports/{id}/participant-attachment-upload-permission
/api/v1/institutions/{slug}{,/logo,/users,/programs,/memberships,/invitations}
/api/v1/institutions/{slug}/memberships/{mid}{,/role,/revoke}
/api/v1/institutions/{slug}/programs/{prog}{,/editions,/logo}
/api/v1/institutions/{slug}/programs/{prog}/editions/{num}
    {,/plan,/budget,/members,/activate,/suspend,/resume,/resolve,/cancel,/close,
     /submit-for-review,/revert-to-draft,/payout-export,/terms[/{tid},/{tid}/download]}
/api/v1/institutions/{slug}/programs/{prog}/editions/{num}/reports
/api/v1/institutions/{slug}/programs/member-candidates
/api/v1/institutions/{slug}/invitations/{iid}/resend
/api/v1/users/{uid}{,/role,/email}    /api/v1/public/institutions/... (publiczne, już znane)
/api/v1/profile{,/account,/consents}  /api/v1/complete-profile   /login
```

**Hipotezy IDOR/BAC (płatna klasa) — WERYFIKACJA RĘCZNA po zalogowaniu, minimalizacja
odczytu (pojedyncze żądania potwierdzające, zero masowego zrzutu, zero zmian cudzych stanów):**

| # | Test | Co potwierdza trafienie | Klasa |
|---|---|---|---|
| H1 | `GET /api/v1/reports/{ID_CUDZEGO}` jako zwykły uczestnik (ID wziąć z kolejności własnych zgłoszeń / events) | 200 + treść cudzego zgłoszenia (403/404 = OK) | IDOR / dane prywatne |
| H2 | `GET /api/v1/reports/{ID}/attachments/{AID}/download` dla cudzego ID | pobranie cudzego załącznika PoC | cudze prywatne treści |
| H3 | `GET /api/v1/reports/{ID}/internal-notes` dla cudzego ID | notatki wewnętrzne CERT (najwyższa waga gdy działa) | krytyczna |
| H4 | stan WŁASNEJ oferty: `me/reports/{ID}/reward-offers/latest` → `.../{rid}/accept` dwukrotnie / cancel po accept | stan zmienia się poza dozwolonym automatem stanów | logika stanów |
| H5 | `PATCH/PUT /api/v1/users/{SWOJ_uid}/role` i `/email` → obserwować; analogicznie `memberships/{mid}/role` WŁASNEJ instytucji | przyjęcie zmiany roli | eskalacja pionowa |
| H6 | `GET /api/v1/reports/{ID}/events` cudzego ID | historia cudzego zgłoszenia | IDOR |
| H7 | `me/reports/creation-eligibility` + `rejected-reports` | wyciek powodów/limitów innych użytkowników | dane prywatne |

*Odrzucenie każdej z H1–H7:* spójny mechanizm autoryzacji po stronie serwera (403/404,
przynależność sprawdzana globalnie) — wtedy portal hack.cert.pl zostaje bez zgłoszenia
i przenosimy ciężar na H-mSzyfr.

**WAŻNE:** to testy autoryzacji, nie zrzut danych. Jedno żądanie potwierdzające, potwierdzenie
2×, screenshot, zapis żądania/odpowiedzi do raportu, dyskrecja. Report id może być
GUID/UUID (nie sekwencyjny) — wtedy enumerate = szum; sprawdź format w WŁASNYM zgłoszeniu.

## moje.cert.pl (Django + Cloudflare)

- front marketingowy/panel; bundle `/static/CACHE/js/output.*.js` (Django compressor) —
  mało endpointów w kliencie; ciekawostka: `/partnership/all_constituency_events_report/`.
- Cloudflare przed frontem (email-decode). Do dalszej mapy PO zalogowaniu (klasyczny
  kandydat IDOR na numerach zgłoszeń — por. strategia 13).

## komunikator.narodowy.gov.pl (mSzyfr) — **Element Web / Matrix**

- `komunikator…` = klient Element Web (fork, CSP z recaptcha.net); host auth wg ustaleń:
  `mas.komunikator.narodowy.gov.pl` (Matrix Auth Service).
- **Brama zwraca catch-all 200 (HTML) dla `.js` poza przeglądarką** — bundle nieosiągalny
  curl-em. Instrukcja: otworzyć stronę w przeglądarce (F12 → Sources → zapisać
  `bundles/622bdb601d5a4764b1d4/bundle.js`) i przepuścić przez endminera OFFLINE.
- Plan testów (2 WŁASNE konta): odseparowanie room-ów/DM (IDOR), join po zgadnięciu
  room-id/alias, invite-linki, reset hasła bez dostępu do skrzynki (ATO), widgety/integracje.
  Uwaga na znane CVE Element/Matrix — §8 wymaga WŁASNEGO PoC z wpływem w tym systemie.

## Zmiana priorytetów po dodatku

**hack.cert.pl wspina się na #2 tuż za mSzyfr** (mapa kompletna w ręce; klasa IDOR
oczywista do weryfikacji jednym żądaniem po zalogowaniu; kod najmłodszy).

---

# DODATEK 2 (4.11, rano): n6portal.cert.pl — mapa z bundla (main.9b01b47c.js, React SPA)

React SPA, jeden bundle `/static/js/main.9b01b47c.js` (511 kB). Endpointy/trasy z klienta:

- auth: `/login`, `/login/oidc`, `/login/mfa`, `/login/mfa_config/confirm`, `/login-keycloak`,
  `/login-keycloak-summary`, `/oidc/refresh_token`, `/password/forgotten`, `/password/reset`,
  `/password-reset`, `/mfa_config`, `/mfa_config/confirm`
- konto: `/account`, `/user-settings`, `/user-settings/mfa-configuration`, `/api_key`,
  `/org_config`, `/info/config`
- biznesowe: `/api`, `/search/events`, `/report/threats`, `/report/inside`,
  `/search/events/sources`, `/report/threats/sources`, `/report/inside/sources`,
  `/knowledge_base/search`, `/incidents`

**Hipotezy (po założeniu WŁASNEGO konta):** autoryzacja `/org_config` vs zwykły user
(eskalacja pozioma), MFA-config confirm bez posiadania MFA (omówienie rejestracji),
`/api_key` — czy klucze innych widoczne przez zmianę ID, `sources` — odczyt źródeł
spoza własnych uprawnień. *Odrzucenie:* serwerowa autoryzacja spójna na wszystkich
zasobach → bez zgłoszenia.
