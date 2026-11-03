# NASK Bug Bounty — strategia na wygraną

Konkurs: **hack.cert.pl**, edycja 11/2026, **3–30.11.2026**, pula **100 000 zł**, 12 domen w zakresie.
Regulamin przeczytany w całości (11 stron PDF). Poniżej fakty, potem plan.

---

## 1. Twarde fakty z regulaminu, które decydują o strategii

| Fakt | Skutek dla nas |
|---|---|
| **Kto pierwszy, ten lepszy** (§7 pkt 8) | Rejestracja i praca **dziś**. Duplikat = zero. |
| **Nagrody przyznawane sukcesywnie, bez czekania na koniec** (§7 pkt 5) | Nie ma sensu trzymać raportu do 30.11. Wysyłamy, gdy tylko mamy PoC. |
| **Ta sama przyczyna w dwóch serwisach = JEDNA podatność** (§7 pkt 9) | Copy-paste tej samej luki na 3 hostach nie da 3× nagrody. Jeden dobry bug > trzy duplikaty. |
| **Maks. 5 req/s** (§6 pkt 2) | Skanowanie masowe odpada. 100 000 żądań = 5,5 godziny. To konkurs na **myślenie**, nie na fuzzing. |
| **PoC obowiązkowe, skanery automatyczne bez ręcznego potwierdzenia = odrzucone** (§8 pkt 14) | Surowy output z narzędzia jest bezwartościowy. Liczy się łańcuch ataku. |
| **CVSS 4.0 decyduje o kwocie** (§7 pkt 6) | Krytyczna (9.0+) = 20 000 zł Tier 1 / 10 000 zł Tier 2. Wysoka (7.0–8.9) = 9 000 / 4 500 zł. |
| **Zakres = dokładnie wypisane domeny** (§5) | `gitlab.snkom.nask.pl` **nie** jest w zakresie, mimo że to subdomena nask.pl. Sprawdzaj `naskrecon check <host>`. |
| **Tylko własne konta** (§6 pkt 1) | Rejestrujemy własne konto w każdej aplikacji, na której pracujemy. |

**Podatek:** nagroda jest brutto + NASK dopłaca równowartość podatku zryczałtowanego (§7 pkt 10),
czyli kwota z tabeli trafia do Ciebie w całości.

---

## 2. Mapa celu — co faktycznie stoi w zakresie

Rekonesans pasywny (Certificate Transparency + nagłówki + treść), 2026-11-03:

| domena | tier | co to jest | tech | ocena |
|---|---:|---|---|---|
| `nask.pl` | 1 | strona instytucji | Azure + own CDN | statyczna, mało powierzchni |
| `oad.nask.pl` | 1 | Ośrodek Analizy Dezinformacji | Azure + Envoy + Next.js | **aplikacja** — middleware, API |
| `zglos-dezinformacje.nask.pl` | 1 | **formularz zgłaszania dezinformacji** | Next.js + Azure | **najlepszy cel**: upload, dane osobowe, API |
| `dyzurnet.pl` | 1 | zgłaszanie incydentów | Next.js + Cloudflare | aplikacja |
| `dns.pl` | 1 | Krajowy Rejestr Domen | własny stack, cookies | rejestr = dane, wyszukiwarka whois |
| `dataannotation.pllum.org.pl` | 2 | **HIVE — aplikacja do anotacji** | Azure + Envoy, SPA 713 B | **drugi najlepszy cel**: logowanie, role, dane |
| `pllum.org.pl` | 2 | PLLuM — polski model językowy | Azure, Nuxt | mało powierzchni |
| `116sos.pl` | 2 | pomoc psychologiczna | Next.js + WP | **dane wrażliwe** (zdrowie) |
| `bezpiecznymiesiac.pl` | 2 | kampania edukacyjna | Azure | statyczna |
| `science.nask.pl` | 2 | NASK SCIENCE | Next.js + WordPress | CMS = potencjał |
| `bezpiecznewybory.pl` | 2 | — | **WAF blokuje (403)** | trudny, ale nagradzany |
| `secure.edu.pl` | 2 | — | brak odpowiedzi (DNS/HTTPS) | do sprawdzenia |

**Wniosek:** realna powierzchnia to **5 aplikacji**: `zglos-dezinformacje`, `dataannotation`, `oad`, `dyzurnet`, `dns.pl`.
Reszta to strony statyczne, na których jedyne sensowne znaleziska to błędy konfiguracji — a te są wprost wykluczone.

**Czego NIE dotykać** (poza zakresem, mimo że należą do NASK): `zakupy.nask.pl`, `zamowienia.nask.pl`,
`taskmanagement.nask.pl`, `ksod.nask.pl`, `certyfikacja.nask.pl`, `inwentaryzacja.nask.pl`,
wszystko pod `*.snkom.nask.pl`, `*.ebsi.nask.pl`, `*.sp.nask.pl`. To systemy wewnętrzne.
Testowanie ich bez zgody to nie „brak nagrody", to problem prawny.

---

## 3. Gdzie realnie leży 20 000 zł — kolejność według stosunku szansy do włożonej pracy

Regulamin jest listą tego, co płaci. Uporządkowana według **ile pracy na znalezienie**, nie według CVSS:

### A. Kontrola dostępu w aplikacjach z logowaniem (IDOR / BAC) — poz. 9, 12
**Cel:** `dataannotation.pllum.org.pl` (HIVE), `zglos-dezinformacje.nask.pl`
**Dlaczego pierwsze:** nie wymaga exploitów, tylko porównania dwóch kont. Własne konto A i B,
ten sam zasób, podmiana identyfikatora. To najczęstsza realna luka w aplikacjach pisanych pod deadline.
**Kroki:** rejestracja → zauważ identyfikatory w URL/API → sprawdź, czy zasób użytkownika A
jest dostępny z sesji B → sprawdź, czy rola w API jest sprawdzana, czy tylko w UI (§8 poz. 9.3).
**Kwota:** 9 000 zł (wysoka) / 20 000 zł jeśli daje masowy odczyt danych (krytyczna).

### B. Błędy API: mass assignment i brak autoryzacji endpointów — poz. 13, 12.2
**Cel:** te same aplikacje.
**Dlaczego:** jedno żądanie z dodatkowym polem `role=admin`, `is_staff=true`, `approved=true`.
Albo odczyt `/api/v1/users`, który zwraca cudze dane. Zero narzędzi, maksymalna wartość.
**Kwota:** 9 000–20 000 zł.

### C. Upload plików — poz. 7
**Cel:** `zglos-dezinformacje.nask.pl` (formularz przyjmuje materiał dowodowy), `116sos.pl`
**Dlaczego:** jeśli formularz przyjmuje załączniki, to jest tam cała klasa: obejście MIME,
podwójne rozszerzenie, SVG z JS, ZIP bez walidacji, ścieżka zapisu.
**Uwaga:** znaleziskiem jest **obejście walidacji z realnym skutkiem**, nie „przyjął plik .exe".
Sam fakt przyjęcia pliku bez konsekwencji jest wykluczony (§8 poz. 7 — wymaga RCE/wpływu).
**Kwota:** 9 000–20 000 zł.

### D. SSRF z odczytem — poz. 5
**Cel:** `zglos-dezinformacje` i `oad` — serwisy, które naturalnie **pobierają treść z zewnątrz**
(np. „podaj link do zgłoszenia"). To najpłodniejszy typ podatności w aplikacjach przyjmujących URL-e.
**Wymóg:** musi być **odczyt**, nie tylko DNS. Blind SSRF jest wykluczony (§8 poz. 7).
**Kwota:** 9 000 zł (wysoka) za dostęp do usług wewnętrznych.

### E. Ominięcie middleware Next.js (CVE-2025-29927) — poz. 9/12
**Cel:** `oad`, `dyzurnet`, `science`, `116sos`, `zglos-dezinformacje` — wszystkie na Next.js.
**Status:** test jest w narzędziu (`naskrecon hypotheses --paths /panel,/admin`). Jeśli któraś wersja
jest podatna, to jedno żądanie zamienia 403 na 200 i mamy krytyczną.
**Uczciwie:** szansa na trafienie jest mała — to głośne CVE z 2025, łatane. Ale koszt sprawdzenia to 2 żądania.

### F. To, czego nie zgadnę — i dlaczego to jest najważniejsze
Największe nagrody w takich konkursach prawie nigdy nie pochodzą z listy „znane klasy".
Pochodzą z **jednej konkretnej funkcji, którą autor napisał w pośpiechu** — eksportu do CSV
z danymi osobowymi, funkcji „udostępnij raport linkiem", resetu hasła przez token w URL,
panelu moderatora z IDOR-em. Nie da się tego znaleźć skanerem. Trzeba wejść w aplikację i czytać
jej zachowanie jak człowiek. **To jest praca dla Ciebie, nie dla narzędzia.**

---

## 4. Narzędzie — co już działa

`naskrecon` (Rust, Rayon, 16 testów jednostkowych przechodzi):

```bash
cargo build --release
./target/release/naskrecon scope                      # 12 domen + stawki z regulaminu
./target/release/naskrecon check gitlab.snkom.nask.pl # POZA ZAKRESEM (kod 1)
./target/release/naskrecon sweep                      # 12 żądań, przegląd nagłówków i tech
./target/release/naskrecon hypotheses                 # ekspozycje + baseline catch-all
./target/release/naskrecon scan --files bundle1.js bundle2.js   # offline, pełny Rayon
```

Trzy rzeczy, które robi dobrze i których nie robią gotowe skanery:

1. **Twardy limiter 4,5 req/s wspólny dla wszystkich wątków** — nie da się przypadkiem przekroczyć
   regulaminowego sufitu, nawet na 16 rdzeniach. Program **odmawia startu** przy `--rps > 5`.
2. **Guard zakresu** — żądanie do hosta spoza §5 jest pomijane z komunikatem, nie wysyłane.
3. **Odejmowanie catch-all** — dla każdego hosta pobierany jest losowy nieistniejący URL jako
   wzorzec, a znaleziskiem jest tylko odpowiedź, która **nie jest HTML**. Bez tego każdy SPA
   zwraca 200 na `/.env` i generuje 200 fałszywych trafień. Sprawdzone: po włączeniu tej reguły
   wynik na 12 domenach to **zero trafień** — i to jest poprawny, uczciwy wynik.

### Korekta do założenia o wydajności
Rust z Rayonem **nie da 100–200× przyspieszenia tam, gdzie wąskim gardłem jest sieć z limitem 5 req/s**.
Przy 12 żądaniach na sekundę całe narzędzie spędza 99% czasu na `sleep`. Przyspieszenie 16× widać
dopiero w analizie offline (setki plików JS, regex na MB tekstu) — i tam Rayon jest włączony.
W tej konkurencji **moc obliczeniowa nie jest bottleneckiem. Bottleneckiem jest moja i Twoja głowa.**

---

## 5. Co zrobić w tej kolejności (konkretny plan)

**Dziś:**
1. Załóż konto na hack.cert.pl i zaakceptuj regulamin **obu** NASK i platformy — bez tego nie można zgłosić.
2. Sprawdź, które z 12 domen w ogóle odpowiadają (`naskrecon sweep`).
3. Zarejestruj **własne** konto na `dataannotation.pllum.org.pl` i `zglos-dezinformacje.nask.pl`.
   To Twoje dwa główne cele na cały miesiąc.

**Dni 2–5:** ręczne przejście obu aplikacji. Cel: mapa endpointów, mapa ról, mapa identyfikatorów.
Tu działa `naskrecon scan` na pobranych bundle'ach JS — wyciąga endpointy, parametry i wzorce sekretów.

**Dni 6–20:** polowanie na klasę A i B. Każdy znaleziony IDOR → natychmiastowy raport, nie czekaj.
Nagrody lecą sukcesywnie, a duplikaty przegrywają.

**Dni 21–30:** klasy C, D, E na tym, co zostało; ewentualnie drugi Tier-2 cel.

---

## 6. Realna kalibracja — żeby nie było rozczarowania

- **Nie obiecuję 20 000 zł.** Nie mam dostępu do aplikacji za logowaniem i nie mogę prowadzić sesji
  interaktywnej. Mogę dostarczyć narzędzie, plan i analizę — decydujące 20% to Twoja praca w przeglądarce.
- **Średnia nagroda na takim konkursie to niska/średnia półka (600–4 000 zł).** Jeden znaleziony IDOR
  z realnym wpływem = 9 000 zł. Dwa = ~18 000 zł. To realistyczny cel górny na miesiąc dla jednej osoby.
- **Pula 100 000 zł i 12 domen** oznacza, że NASK spodziewa się **kilkunastu–kilkudziesięciu** zgłoszeń,
  nie jednego zwycięzcy. To konkurs „kto więcej znajdzie", a nie „kto znajdzie jedyną lukę".
- **Najczęstszy powód porażki to nie brak umiejętności, tylko zły wybór celu** — tydzień na
  `bezpiecznymiesiac.pl` (strona statyczna) to tydzień stracony, bo nie ma tam czego znaleźć.

---

## 7. Zasady, których nie łamiemy

- Tylko domeny z §5. Żadnych `*.snkom`, `*.ebsi`, `*.sp`, `zakupy`, `zamowienia`, `taskmanagement`, `ksod`.
- Max 5 req/s. Nasze narzędzie ma sufit 4,5 i nie da się go podnieść argumentem CLI.
- Żadnych testów obciążeniowych i DoS (§8 poz. 10) — **natychmiastowa dyskwalifikacja**.
- Tylko własne konta. Żadnego dostępu do cudzych danych w celu „udowodnienia" poza minimum
  koniecznym do PoC (najlepiej: własne dwa konta).
- Żadnych niszczących operacji: nie usuwamy, nie modyfikujemy cudzych rekordów. PoC = odczyt.
- Dyskrecja do czasu poprawki (wymóg z komunikatu NASK).
