# NASK bug bounty — weryfikacja pakietu, moje pomysły i zasady (3.11.2026)

**Źródła.** (1) Strona programu `hack.cert.pl/programs/nask-pib/nask/editions/1` — pobrana
i przeczytana w całości 3.11.2026 (2 chunki). (2) Pakiet z Google Drive
(`00-README`…`12-gen_report.py` + `08-nask-bugbounty-komplet.zip`, 53 842 B) — przeczytany
i rozpakowany; jego zawartość leży teraz w tym katalogu (`nask/`), bo **przed tym commitem
nie była w żadnym repozytorium git** (repo `peteraangelic-pixel/NASK` miało wyłącznie
`README.md` + workflow CI). (3) Repo `peteraangelic-pixel/NASK` (gałąź `arena/a29ca234-nask`
istnieje, **nie dotknięta**). (4) Stan ARC na `arena/a450b00f-pokemon`: domknięty
(peer-review v3-slim/v3-control, bez nowego agenta).

---

## 1. Fakty programu zweryfikowane u źródła (nie z artykułu)

| fakt | wartość |
|---|---|
| okres edycji 11/2026 | **03-11-2026 → 30-11-2026** |
| nagrody Tier 1 (niski/średni/wysoki/krytyczny) | **600 / 4 000 / 9 000 / 20 000 PLN** |
| nagrody Tier 2 | 300 / 2 000 / 4 500 / 10 000 PLN |
| **Tier 1 (zakres)** | `nask.pl`, `dyzurnet.pl`, `dns.pl`, `oad.nask.pl`, `zglos-dezinformacje.nask.pl` |
| **Tier 2 (zakres)** | `bezpiecznymiesiac.pl`, `secure.edu.pl`, `bezpiecznewybory.pl`, `116sos.pl`, `pllum.org.pl`, `science.nask.pl`, `dataannotation.pllum.org.pl` |
| zasady testowania | **bez uwierzytelnienia albo wyłącznie własne/kont testowe**; automaty **max 5 req/s** |
| klasy objęte | RCE, przejęcie konta, dostęp do danych wrażliwych, SQLi, SSRF z odczytem, SSTI, file-upload ze skutkiem, XSS (z wyłączeniami), IDOR/BAC, eskalacja, sesje/authn, API authz, mass assignment, CORS ze skutkiem, path traversal/LFI, CSRF ze skutkiem, open redirect (warunkowo), cache poisoning, request smuggling, XXE |
| **wyłączenia (klasztory)** | wycieki bez danych wrażliwych (stack trace, wersje, IP, ścieżki, listingi, user enumeration, metadane, publiczne debug); brak nagłówków/HSTS/captchy/flag cookie; SPF/DKIM/DMARC bez spoofingu; TLS bez scenariusza; **CVE bez działającego PoC**; MITM/fizyczny/DevTools/stare przeglądarki; self-XSS, tabnabbing, clickjacking bez krytycznej akcji, czysty HTML injection; CSRF bez wpływu; **blind SSRF tylko z dowodem DNS**; open redirect bez scenariusza; **DoS i testy obciążeniowe ZABRONIONE**; brak rate-limitu bez scenariusza; subdomain takeover bez PoC; **zgłoszenia bez PoC i z samych skanerów = odrzucone** |

**Konsekwencje strategiczne (potwierdzam ustalenia STRATEGII):** kto pierwszy ten lepszy
(duplikat = zero); nagrody sukcesywnie (wysyłaj od razu); **ta sama przyczyna w dwóch
serwisach = JEDNA podatność**; 5 req/s oznacza konkurs na myślenie, nie fuzzing; CVSS 4.0
decyduje o kwocie; zakres = dokładnie lista (subdomeny niewypisane, np. `gitlab.snkom.nask.pl`,
**są poza zakresem** — testowanie ich to problem prawny, nie „brak nagrody").

---

## 2. Weryfikacja narzędzia `naskrecon` — czytanie kodu, nie uruchomienie

**Uwaga o metodzie:** w moim sandboxzie **nie ma `cargo`/`rustc`**, więc 16 testów
jednostkowych **nie uruchomiłem**; poniżej weryfikacja przez czytanie źródła z zipa.

1. **Limiter jest twardy i globalny.** `recon/src/ratelimit.rs`: `min_gap = 1/rps`,
   `acquire()` blokuje wątek na condvarze do chwili `next_ok`; stan w `Mutex` współdzielony
   przez wszystkie wątki Rayon. `main.rs`: `if cli.rps > scope::MAX_REQ_PER_SEC { eprintln!("ODMOWA…"); exit(2) }`
   — **program odmawia startu powyżej regulaminowego sufitu**, niezależnie od `--threads`.
   Komentarz wprost: „domyślnie 4.5 req/s… Nie należy go podnosić". ✓
2. **Guard zakresu.** `scope.rs::in_scope(host)` dopasowuje **dokładnie** domeny z §5
   (testy: `exact_domains_are_in_scope`, `www_of_apex_is_the_same_asset`,
   `unlisted_subdomains_are_not`, `oad_beats_parent_match`); `payout(tier, cvss)`
   odtwarza tabelę z regulaminu (test `payouts_follow_regulation`). ✓
3. **Odejmowanie catch-all.** `baseline.rs::is_real_file` zwraca fałsz, gdy `content-type`
   zawiera `html` albo ciało zaczyna się od `<`/`<html`; `strip_dynamic` zwija ścieżkę
   echo i ciągi ≥16 znaków hex (rotujący token CSRF); test `catchall_with_echoed_path_is_detected`.
   To ta reguła zbiła 200 fałszywych trafień do zera — **bez niej każdy SPA „ma /.env"**. ✓
4. **Workflow nie strzela siecią przy push.** `recon/workflow-recon.yml`: przy `push` tylko
   `cargo build --release --locked` (bramka — „bez tego CI kłamie"), `cargo test`, oraz check
   guarda zakresu, który **MUSI zwrócić kod 1** dla `gitlab.snkom.nask.pl`; kroki sieciowe
   (`sweep`, `hypotheses`) wyłącznie przy `workflow_dispatch` z jawnym `rps`. ✓
   **Nie podpinam tego workflow do `.github/` tego repozytorium bez Twojej zgody** — leży
   jako `nask/recon/workflow-recon.yml` do świadomego włączenia.

**Werdykt:** pakiet jest **zgodny z regulaminem przez konstrukcję**, a nie przez deklarację.
To rzadkość i to jest jego głównza wartość obok planu.

---

## 3. Moje pomysły — dodatek do planu, każdy z kryterium akceptacji

**P0. Offline'owa ekstrakcja powierzchni z publicznych assetów (Rust+Rayon, ZERO żądań
poza pobraniem assetów).** Rozszerzyć `naskrecon scan` o: (a) parsowanie build-manifestu
Next.js i payloadów RSC/fligth do enumeracji tras i route-groups; (b) **klasyfikator formatu
identyfikatorów per endpoint** (int sekwencyjny / UUID / ULID / hash) — sekwencyjny int w
`/task/{id}` to natychmiastowy kandydat IDOR i priorytet ręcznego testu dwóch kont;
(c) score sekretów z filtrem entropii i allow-listą fałszywych (klucze map, ID buildów).
*Kryterium:* na bundle'ach HIVE i zglos-dezinformacje lista endpointów ≥ tej z DevTools,
zero ręcznej roboty; czas < 5 s na 16 rdzeniach. **Tu Rayon realnie płaci** (CPU-bound),
zgodnie z kalibracją pakietu, że sieć z limitem 5 req/s nigdy nie jest bottleneckiem.

**P1. Pre-scorer CVSS 4.0 → kwota + deduplikator „ta sama przyczyna".** W `gen_report.py`:
wektor CVSS 4.0 → półka z tabeli programu (Tier × severity) oraz reguła §7 pkt 9: jeśli
ten sam root cause dotyka dwóch hostów w zakresie, generator **scala do jednego zgłoszenia**
i oznacza drugi host jako instancję. *Kryterium:* raport bez wektora i bez sekcji „instancje"
nie przechodzi walidacji; oczekiwana kwota drukowana przed wysyłką.

**P2. Test middleware Next.js jako para żądań z baseline'em.** Hipoteza CVE-2025-29927-podobna
już jest w pakiecie; dodaję wymóg: najpierw baseline catch-all dla tej ścieżki (`baseline.rs`),
potem warianty nagłówka (`x-middleware-subrequest` itd.), a 403→200 jest znaleziskiem **tylko
gdy ciało 200 NIE jest catch-allem**. *Kryterium:* zero trafień na hostach kontrolnych
z catch-allem; każde trafienie ma diff ciała vs baseline w raporcie.

**P3. Polowanie na source-mapy i assety buildu (pasywne, publiczne, ≤4.5 req/s).**
`*.js.map`, `_next/static/chunks/*`, `stats.json`, `build-manifest.json` na 5 celach
aplikacyjnych. Source-mapy odsłaniają klienty API z pełną listą endpointów → wejście do P0.
*Kryterium:* inwentarz assetów w `recon-out.jsonl` ze stemplem limitera; brak żądań poza §5.

**P4. Macierz uploadu jako checklista + szablony PoC, wykonywana RĘCZNIE.** MIME vs
rozszerzenie vs magic bytes, podwójne rozszerzenie, SVG z JS, archive-in-archive, ścieżka
zapisu — jako tabela do odhaczania w przeglądarce (regulamin wymaga PoC z realnym skutkiem;
zautomatyzowany fuzz uploadu generowałby szum i ryzyko przekroczenia limitu). *Kryterium:*
każdy wiersz ma status „wykluczony / potwierdzony PoC / do dalszego testu" w REJESTRZE.

**P5. Dyscyplina zgłoszeń wymuszona narzędziem.** `gen_report.py` odmawia wygenerowania
raportu bez: wektora CVSS, kroki PoC odtwarzalne na **własnych dwóch kontach**, host w §5,
brak operacji niszczących (tylko odczyt), stemple czasowe żądań z `recon-out.jsonl`.
*Kryterium:* §8 pkt 14 (skanery bez ręcznego potwierdzenia = odrzucone) niespełnialny
konstrukcyjnie.

---

## 4. Czego NIE zrobię (granice prawne i regulaminowe)

- **Żadnego hosta spoza §5** — w tym kuszących `gitlab.snkom`, `nextcloud.snkom`,
  `secret.eadministracja`, `*.ebsi`, `*.sp`, `zakupy`, `zamowienia`, `taskmanagement`, `ksod`.
- **Żadnego DoS/testów obciążeniowych**, żadnego przekroczenia 5 req/s (narzędzie ma sufit 4.5
  i odmawia startu wyżej).
- **Żadnych cudzych kont ani cudzych danych**; PoC wyłącznie na własnych dwóch kontach,
  tylko odczyt, bez modyfikacji i usuwania rekordów.
- **Żadnych zgłoszeń z samych skanerów** i żadnych „potencjalnych" łańcuchów bez PoC.
- **Dyskrecja do czasu poprawki** (wymóg komunikatu NASK).
- Z mojego sandboxa **nie wykonuję żadnych żądań do domen w zakresie** (nie mam tam zasięgu
  sieciowego, a aktywna faza i tak należy do Ciebie po rejestracji i akceptacji regulaminu).

---

## 5. Moc obliczeniowa — gdzie naprawdę pomaga

- **GitHub Actions:** kompilacja Rusta + `cargo test` + analiza offline setek plików JS
  (Rayon, CPU-bound) — dokładnie jak zaprojektowano w `workflow-recon.yml`. Sieć tylko
  przy `workflow_dispatch` z `rps ≤ 4.5`. **Nie dispatchuję niczego bez Twojego GO.**
- **Twój Ryzen 9 5950X / 64 GB:** korpus offline (bundle + source-mapy + regex na MB tekstu)
  — jedyny etap, gdzie 16 rdzeni skraca czas z minut do sekund.
- **Rust+Rayon „100–200×" nie dotyczy części sieciowej** — przy suficie 5 req/s narzędzie
  spędza ~99 % czasu na czekaniu; pakiet mówi to wprost i ma rację. Bottleneckiem jest
  czytanie zachowania aplikacji jak człowiek, nie CPU.

---

## 6. Record sprzątania workspace (wykonane w tym commicie)

Usunięte z drzewa roboczego przez `git rm` — **wszystko odzyskiwalne z historii**
(`git checkout dc15143 -- <ścieżka>`):

| usunięte | rozmiar | powód |
|---|---:|---|
| `benchmark*.zip` w korzeniu (6 plików) | ~31,5 MB | moje stare bundla PTCG, nadpisane przez v2.9.1 FINAL FIX |
| `pokemon-agent/kaggle_results/**` (133 pliki) | ~192 MB | surowe logi/replaye PTCG; wnioski żyją w `SUBMISSION_LOG.md` i `NOTES_STRATEGY.md` |
| `pokemon-agent/rust/bin-win/*.exe` (10 plików) | ~23 MB | binaria Windows; źródła Rust zostają |
| `google_drive/` (nieśledzone) | ~56 KB | redundantna kopia zipa z Drive; komplet jest teraz w `nask/` |

**Zachowane:** `arc3-handoff/` (25 dokumentów + narzędzia + patche + testy — dorobek audytów
ARC), `arc-agi-3/peer-review/` (1,8 MB dowodów v3-slim/v3-control), źródła `pokemon-agent/`
(benchmark, agenty, decki, `SUBMISSION_LOG.md`, `NOTES_STRATEGY.md`), cały `nask/`.

---

## 7. Czego potrzebuję od Ciebie (bez tego stoję)

1. **Konto na hack.cert.pl + akceptacja regulaminu platformy i konkursu** — bez tego zgłoszenie
   nie istnieje (§1 pkt 3). To musi zrobić człowiek.
2. **Dwa własne konta** na `dataannotation.pllum.org.pl` (HIVE) i przejście formularza
   `zglos-dezinformacje.nask.pl` z własnymi danymi testowymi — warunek całej ścieżki IDOR.
3. **GO na każdy `workflow_dispatch`** i na każdzą kosztowną próbę (zasada z pakietu).
4. Decyzja, czy `nask/` zmirorować do `peteraangelic-pixel/NASK` (sesja pracuje na gałęzi
   `arena/c87f7a48-pokemon` i nie pushuje nigdzie indziej — mirror to jedna komenda u Ciebie).

---

## 8. Kalibracja oczekiwań (podpisuję się pod nią)

Typowa nagroda w takim programie to **niska/średnia półka (600–4 000 PLN)**; jeden IDOR
z realnym wpływem = **9 000 PLN**, dwa ≈ **18 000 PLN** — to realistyczny sufit miesiąca
dla jednej osoby. **Nie obiecuję 20 000 PLN**: decydujące ~20 % to praca w przeglądarce
na własnych kontach, której agent nie wykona. Pula 100 000 PLN i 12 domen oznacza konkurs
„kto więcej znajdzie", a najczęstszym powodem porażki jest **zły wybór celu** (tydzień na
stronie statycznej = tydzień stracony, bo wykluczenia zjadają jedyne możliwe tam znaleziska).
