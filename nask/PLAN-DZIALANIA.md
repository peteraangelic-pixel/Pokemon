# Plan działania — dzień po dniu

Kalendarz konkursu: **3–30.11.2026**. Nagrody przyznawane sukcesywnie (§7 pkt 5), więc
**każde znalezisko wysyłamy natychmiast** — nie zbieramy na koniec.

---

## Dzień 1 (dziś)

- [ ] Konto na hack.cert.pl + akceptacja **regulaminu platformy i regulaminu konkursu**
      (bez tego zgłoszenie nie zostanie przyjęte — §1 pkt 3).
- [ ] `naskrecon sweep` — potwierdzić, które domeny odpowiadają.
- [ ] Sprawdzić `secure.edu.pl` (DNS) i `bezpiecznewybory.pl` (z przeglądarki).
- [ ] Zarejestrować **własne** konto na `dataannotation.pllum.org.pl`.
- [ ] Wysłać formularz na `zglos-dezinformacje.nask.pl` z **własnymi** danymi testowymi
      (żeby zobaczyć cały przepływ, nie żeby cokolwiek zepsuć).

## Dni 2–4 — mapa HIVE (`dataannotation.pllum.org.pl`)

To domniemany najlepszy cel: aplikacja do anotacji = role, przypisania, cudze zadania.

- [ ] Założyć **drugie** własne konto (potrzebne do testów IDOR — dwóch kont wymaga §6 pkt 1).
- [ ] DevTools → Network. Zapisać każdy request XHR: metoda, ścieżka, ciało, odpowiedź.
- [ ] Zidentyfikować **identyfikatory w ścieżkach i ciałach**: `/task/{id}`, `/annotation/{id}`,
      `userId=`, `projectId=`.
- [ ] Sprawdzić, czy identyfikatory są sekwencyjne (`/task/1`, `/task/2`) czy losowe (UUID).
      Sekwencyjne = natychmiastowy kandydat na IDOR.
- [ ] Pobrać bundle JS i przepuścić przez `naskrecon scan --files ...` (wyciąga endpointy,
      parametry, wzorce sekretów — offline, pełny Rayon).

**Test IDOR (poz. 9.2):** zalogowany jako konto B, żądanie o zasób utworzony przez konto A.
- 200 z cudzą treścią → **podatność**. Kwota: 9 000 zł (wysoka), 20 000 zł jeśli masowy odczyt.
- 403 → dobrze, idziemy dalej.
- 200 ale z pustą/domyślną treścią → sprawdzić, czy to nie catch-all.

**Test kontroli roli w API (poz. 9.3):** czy panel administracyjny jest chroniony tylko w UI?
Żądanie z sesji zwykłego użytkownika do endpointu admina.

**Test mass assignment (poz. 13):** do ciała `PATCH /api/user` dodać `"role":"admin"`,
`"is_staff":true`, `"approved":true`, `"verified":true`. Potem odczytać własny profil —
czy pole się zmieniło.

## Dni 5–7 — mapa `zglos-dezinformacje.nask.pl`

Najbardziej obiecujący ze względu na naturę: przyjmuje **treść od obywateli** i **linki**.

- [ ] Cały przepływ zgłoszenia: co wolno wgrać, jakie pola, jaki limit rozmiaru.
- [ ] **Upload (poz. 7):** sprawdzić walidację typu — czy decyduje `Content-Type`, rozszerzenie,
      czy zawartość. Testy: `.jpg` z treścią PHP, podwójne rozszerzenie `x.php.jpg`,
      SVG z `<script>`, ZIP bez sprawdzania zawartości.
      **Ważne:** znaleziskiem jest obejście z realnym skutkiem (RCE, dostęp do zasobów) —
      samo „przyjął plik" jest wykluczone (§8 poz. 7).
- [ ] **SSRF (poz. 5):** jeśli jest pole „link do źródła" i serwer go pobiera — podać URL
      do kontrolowanego przez nas endpointu i sprawdzić, czy przychodzi żądanie.
      Potem: czy da się odczytać odpowiedź z sieci wewnętrznej. Blind SSRF jest wykluczony.
- [ ] **IDOR na zgłoszeniach:** czy `/zgloszenie/{id}` pozwala odczytać cudze zgłoszenie?
      Tu są **dane osobowe** — to podnosi CVSS do krytycznej.
- [ ] Sprawdzić eksport (CSV/PDF) — klasyczne miejsce wycieku masowego.

## Dni 8–12 — `oad.nask.pl` i `dyzurnet.pl`

- [ ] Test ominięcia middleware Next.js (CVE-2025-29927): `naskrecon hypotheses --paths /admin,/panel`.
      Sprawdzić wersję Next.js z `_next/static/...` i z `buildId`.
- [ ] `dyzurnet.pl` — formularz zgłaszania incydentów. Te same testy co powyżej.
- [ ] `dns.pl` — wyszukiwarka whois/rejestru: sprawdzić, czy parametry nie pozwalają
      na odczyt danych abonenta (dane osobowe = krytyczna).

## Dni 13–20 — drugi przebieg + klasy trudniejsze

- [ ] XSS z realnym wpływem (poz. 8) — tylko jeśli prowadzi do przejęcia sesji/konta.
      Self-XSS i content injection bez JS są wykluczone.
- [ ] CSRF zmieniający stan konta (poz. 16) — zmiana e-maila, dodanie użytkownika, usunięcie konta.
- [ ] Path traversal / LFI (poz. 15) — jeśli gdziekolwiek widać nazwę pliku w parametrze.
- [ ] HTTP request smuggling (poz. 19) — tylko jeśli front to Envoy/nginx + backend z rozjazdem.
- [ ] Web cache poisoning (poz. 18) — Azure Front Door cache'uje; sprawdzić, czy nagłówki
      `X-Forwarded-Host` wchodzą do odpowiedzi.

## Dni 21–30

- [ ] Domknąć i wysłać to, co się zebrało.
- [ ] Jeśli któryś cel okaże się pusty — przejść na `116sos.pl` (dane wrażliwe: zdrowie,
      psychologia) i `science.nask.pl` (WordPress — wtyczki bez PoC są wykluczone, więc
      tylko realne łańcuchy).

---

## Zasady pisania raportu (bez tego raport jest odrzucany)

1. **PoC krok po kroku** — każde żądanie z pełnymi nagłówkami i ciałem, plus odpowiedź.
2. **Własne dwa konta** jako dowód — nigdy dane innego użytkownika.
3. **Wpływ po ludzku** — „mogę odczytać imię, e-mail i treść zgłoszenia innej osoby",
   nie „endpoint nie sprawdza autoryzacji".
4. **Klasa z §8** — wpisać numer pozycji, to przyspiesza wycenę.
5. **Nie wysyłać duplikatów** — ta sama przyczyna w dwóch serwisach to jedna podatność (§7 pkt 9).
6. **Zero danych osobowych w raporcie** — maskować, pokazywać tylko dowód dostępu.

## Czego nie robić nigdy

- Żadnych testów obciążeniowych ani DoS — **natychmiastowa dyskwalifikacja** (§8 poz. 10).
- Nie przekraczać 5 req/s.
- Nie usuwać ani nie modyfikować cudzych rekordów.
- Nie publikować niczego przed poprawką.
