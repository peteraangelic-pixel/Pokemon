# IDEE NA WYGRANĄ — hack.cert.pl edycja 11/2026 (rank + kalibracja)

Stan: noc 3/4.11.2026. Założenia regulaminowe: max **5 req/s** automatyki, konta
**własne/testowe**, PoC + instrukcja odtworzenia **obowiązkowe**, raporty ze skanerów
bez ręcznego potwierdzenia **wykluczone** (§8), płacą tylko **pierwsze** zgłoszenia,
Władysławowo pomijamy (stawki + tłok).

## Kalibracja (uczciwie)

- Anonimowy skan 26 hostów (pomiary innych sesji): 0 zgłoszeń, 19 trafień odrzuconych
  przez §8. **Skan bez sesji nie płaci.** Więcej skanowania = zero.
- Realny scenariusz dla 1 osoby z 2–3 wieczorami pracy: **1–2 trafienia w przedziale
  4–9k zł/mies.** Wypłaty 20k wymagają łańcucha (RCE / pełne ATO / SSRF z odczytem) —
  to loteria, ale jedyna w klasie „duża”.
- Przewaga czasowa: program trwa do 30.11 (NASK). Łatwe IDORY na panelach polegną
  pierwszemu, kto je sprawdzi. **Liczę się tempo, nie objętość skanów.**

## Rank pieniędzy (co i po co, w kolejności łączenia)

### 1. mSzyfr — `*.komunikator.narodowy.gov.pl` (600–20000) ← najlepszys stosunek szansa/kwota
Komunikator = dane prywatne innych użytkowników = klasa „cudze wiadomości” (wysoka/krytyczna).
Plan wymaga 2 KONT WŁASNYCH (użytkownik rejestruje oba):
- 2 konta → A wysyła do B → testy, czy liste/uuid/tokeny rozmów odseparowane (IDOR poziomy),
- reset hasła / logowanie tokenem — czy da się przejąć SESJĘ bez dostępu do skrzynki (pełne ATO),
- webhooki/invite-linki — czy join po zgadnięciu ID daje dostęp do cudzego pokoju,
- eksport/wyszukiwanie — czy filtrowanie po `userId`/`roomId` uwzględnia właściciela.
Sesje → nie skaner, ale ręczne żądania z DevTools (limit 5 req/s i tak trzymamy).

### 2. hack.cert.pl — sam portal konkursu (300–20000, w zakresie przez `*.cert.pl`)
**Najmłodszy kod** w ekosystemie, ciężka praca pod obciążeniem startu 3.11.
- rejestracja / formularz zgłoszeniowy / załączniki PoC — te same klasy co sendForm
  (upload, mass assignment, walidacja),
- role (zgłaszający vs program) — pionowa eskalacja,
- widoczność cudzych zgłoszeń (IDOR w panelu zgłoszeń) = dane prywatne = płatne,
- uwaga: incydent.cert.pl — **nie wysyłać fikcyjnych zgłoszeń testowych**.

### 3. CERT Polska panele — moje.cert.pl / n6portal / mwdb.cert.pl (300–20000)
- moje.cert.pl ma publiczne `/accounts/signup/` → rejestracja WŁASNA,
- panele zgłoszeniowe = klasyczne IDOR (numeracja zgłoszeń, `/api/incidents/{id}`),
- mwdb (platforma malware): konta własne; co ciekawe — upload/hash, share, query,
  eksport; klasa „cudze prywatne treści” przy błędzie autoryzacji.

### 4. Portal Gov.pl — `www.gov.pl` TYLKO (600–20000)
Portal treściowy → nisko, chyba że formularze/konta (newsletter, ePUAP-widgey)
wykażą logikę. Nie stracić tu wieczoru.

### 5. NASK reszta — `science.nask.pl`, `116sos.pl`, `pllum.org.pl` (T2, 300–10000)
Mniejsze aplikacje = mniejsza konkurencja, ale też niższe stawki. Miner pasywnie,
potem ręczna weryfikacja formularzy/kont.

## Czego NIE robić (marnowanie czasu / ryzyko odrzucenia)

- skanery słownikowe, nagłówki, CSP/HSTS, wersje, user enumeration, open redirect
  „goły”, self-XSS, clickjacking, brak rate limitu, DoS — wszystko §8,
- panel.dns.pl / partner.dns.pl — **niepotwierdzone w zakresie, nie dotykać**,
- incydent.cert.pl — bez fikcyjnych zgłoszeń,
- cudze konta / domenowe konta pracowników — zakaz,
- publikowanie czegokolwiek przed poprawką — dyskrecja.

## Podział ról (granice)

**Agent (ja):** mapy zakresu i endpointów, narzędzia offline (Rust/Rayon), drafty
hipotez z warunkami odrzucenia, szkielety raportów. **NIE zakładam kont, NIE
eksploatuję, NIE wysyłam zgłoszeń.**
**User:** rejestracja na hack.cert.pl + konta własne w aplikacjach (mSzyfr ×2,
moje.cert.pl, mwdb), ręczna weryfikacja hipotez w DevTools, submit przez formularz,
decyzje o wysyłce (pierwszeństwo).
