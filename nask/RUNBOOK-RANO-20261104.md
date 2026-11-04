> **UWAGA (04.11, po przeglądzie 6 gałęzi): ten runbook jest NIEAKTUALNY w części L1–L3.**
> L1/L2 (HIVE) są **zablokowane** — brak publicznej rejestracji (`/register`, `/api/v1/register`
> → 404 w dwóch niezależnych kanałach); L3 (zglos-dezinformacje) **nie jest wykonalny automatem**
> — reCAPTCHA v3 + żądanie zapisujące. Obowiązuje **`RUNBOOK-REV2-20261104.md`**, a dowody i
> rozstrzygnięcia są w `PRZEGLAD-GALEZI-20261104.md`. Ten plik zostaje jako zapis stanu z nocy.

# Runbook na rano (4.11.2026) — kolejność wg stosunku szansy do pracy

**Warunek wstępny (bez tego nic poniżej):** konto na hack.cert.pl + akceptacja regulaminu
platformy i konkursu; **dwa własne konta** na `dataannotation.pllum.org.pl`; przejście formularza
`zglos-dezinformacje.nask.pl` z własnymi danymi testowymi. Dyscyplina: tylko domeny §5,
tylko własne konta, tylko odczyt w PoC, ≤5 req/s dla wszelkich skryptów (`naskrecon` ma sufit
4.5 i odmawia wyżej), dyskrecja do czasu poprawki, jedno zgłoszenie = jeden root cause
(instancje na innych hostach wypisane **wewnątrz** zgłoszenia, §7 pkt 9).

**Czego NIE powtarzać rano (zmierzone w nocy 3/4.11, patrz REJESTR):**
`oad.nask.pl/podglad-pdf?url=` **nie jest** SSRF ani LFI: prefiks `/media/` walidowany
serwerowo (brak pliku = 200), wszystko poza prefiksem = 500 bez danych, pobranie klienckie.
Nie tracić dnia ani nie zgłaszać 500-tki (klasa wykluczona: brak wrażliwych danych).

---

## L1. HIVE (`dataannotation.pllum.org.pl`) — IDOR/BAC + mass assignment + rola w API
**Klasy:** 9.1/9.2/9.3, 12.1/12.2, 13. **Oczekiwana półka:** 9 000 (wysoka) / 20 000 (masowy odczyt).
1. Zalogować konto A i B (osobne przeglądarki/profile). Konto A: utworzyć zadanie/anotację
   z charakterystycznym, **własnym** stringiem (`CANARY-A-<data>`).
2. W DevTools zebrać mapę: metoda, ścieżka, ciało, odpowiedź dla każdego XHR. Zapisać do
   `nask/recon/hive-endpoints.jsonl` (potem wejście dla `bundle_scan.py`).
3. **IDOR:** z sesji B zażądać zasobu A (`/task/{idA}`, `/annotation/{idA}`).
   - 200 z canary w treści → **podatność**; PoC = dwa zrzuty (sesja B + treść A), bez cudzych danych.
   - 403 → OK, idziemy dalej. 200 z pustą/domyślną treścią → sprawdzić catch-all (por. baseline).
4. **Sekwencyjność:** jeśli `{id}` to int, powtórzyć krok 3 dla id±1..±5 **wyłącznie własnych**
   zasobów (sprawdzenie zakresu, nie cudzych rekordów).
5. **Rola tylko w UI?** Z sesji B wywołać endpoint admina/listy projektów. 200 z danymi → 9.3/12.2.
6. **Mass assignment:** `PATCH`/`PUT` na własny profil/zadanie z dodatkowym polem
   (`role`, `is_staff`, `approved`, `verified`, `ownerId=<idB>`). Odczytać własny zasób:
   pole się zmieniło → **podatność** (13); zmienić udało się tylko własne pole → notatka, nie raport.
7. CVSS draft: Confidentiality High + brak authz → 8.x–9.x; wpisać wektor do raportu.

## L2. HIVE — przepływ resetu hasła (klasa 2.1/2.2/2.3)
**Oczekiwana półka:** 9 000–20 000 przy realnym przejęciu; niska przy samych obserwacjach.
1. Reset na **własny** e-mail: sprawdzić, czy token jest w **query** (nie fragment) linku,
   czy link wygasa, czy jest jednorazowy (drugie użycie = 4xx), czy sesja po resecie rotuje ID.
2. Czy odpowiedź „reset wysłany" różni się dla niezarejestrowanego adresu → **tylko notatka**
   (user enumeration jest WYKLUCZONY z nagród — nie zgłaszać).
3. Czy da się dokończyć reset **bez** kodu ze skrzynki (token przewidywalny/zero-token/
   odpowiedzi różnicujące) → jeśli tak: **PoC na własnym koncie** i zgłoszenie 2.1.

## L3. `zglos-dezinformacje.nask.pl` — upload + podgląd linku (klasy 7 i 5)
1. **Najpierw UI:** czy po wysłaniu zgłoszenia z własnym linkiem serwis pokazuje **podgląd /
   snapshot / tytuł / zrzut** pobranej strony? Jeśli TAK → otwiera się dowód **SSRF z odczytem**:
   własny link do publicznej strony z unikalnym canary, a potem sprawdzenie, czy canary wraca
   w podglądzie; drugi krok: link do `http://169.254.169.254/…` **tylko jeśli** podgląd
   reflektuje treść (wtedy to odczyt, nie blind). Blind (tylko DNS/czas) = **WYKLUCZONY, nie zgłaszać**.
2. **Upload (.png/.jpg ≤20 MB):** macierz do odhaczania (ręcznie, pojedynczo):
   magic-bytes PNG z doklejonym payloadem · podwójne rozszerzenie `.png.jpg` i `.jpg.png` ·
   `Content-Type` vs rozszerzenie vs zawartość · SVG (jeśli przyjmuje) z JS · nazwa z `../`.
   Znaleziskiem jest **obejście walidacji ze skutkiem** (wykonanie/odczyt/udostępnienie),
   nie „przyjął plik" (§8 poz. 7 wyklucza sam fakt przyjęcia).
3. Limit 50 linków i 250 znaków: sprawdzić walidację **serwerową** (klient to nie finding).

## L4. Dyżurnet / 116sos / science — CMS i wtyczki
1. `116sos.pl`: sprawdzić `/wp-json/` (science zwraca 404 = niewystawione; 116sos nieznane).
   Jeśli wystawione: **listingi użytkowników = WYKLUCZONE**; interesują wyłącznie endpointy
   zwracające **prywatne/wrażliwe dane** lub pozwalające na akcję (formularze pomocy = dane
   zdrowotne → każdy nieautoryzowany odczyt to klasa 3.1/3.3, półka krytyczna).
2. Formularze WP (CF7 i podobne): odbicie treści w odpowiedzi = tylko notatka, jeśli bez JS
   (czysty HTML injection WYKLUCZONY).

## L5. `dns.pl` (Drupal) — tylko publicznie uzasadnione próby
1. Kilkanaście GET-ów na publiczne ścieżki widoków/REST z **baseline'em catch-all**
   (`naskrecon hypotheses` robi to poprawnie); znaleziskiem jest odpowiedź **nie-HTML**
   z danymi (np. eksport rejestru z danymi abonentów poza danymi publicznymi whois).
2. Listingi katalogów i wersje = **WYKLUCZONE** — nie zgłaszać.

---

## Dyscyplina zgłoszeń (generator odmawia bez tego)
wektor CVSS 4.0 + oczekiwana półka z tabeli · kroki PoC odtwarzalne na **własnych** kontach ·
host z §5 · brak operacji niszczących · stemple czasowe żądań z `recon-out*.jsonl` ·
sekcja „instancje" zamiast duplikatów (§7 pkt 9) · wysyłka **natychmiast** po PoC
(nagrody sukcesywnie, duplikat = zero).
