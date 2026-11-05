# NASK Bug Bounty — jak coś wygrać? (konkretny plan)

Źródła: https://hack.cert.pl/ oraz https://android.com.pl/tech/1101723-nask-zaplaci-za-zhakowanie-systemow/

## 1. O co chodzi w konkursie

* **Organizator:** CERT Polska w strukturach NASK – PIB (państwowy instytut badawczy).
* **Platforma:** https://hack.cert.pl/ — pierwszy w Polsce państwowy program bug bounty.
* **Edycja 11/2026:** trwa od **03.11.2026 do 30.11.2026** — mamy około miesiąc (dziś jest 03.11.2026).
* **Pula nagród:** **1 000 000 PLN** na wszystkie programy razem.
* **Wysokość nagrody za pojedynczy błąd:** zależy od krytyczności, trudności exploitu i wpływu na usługi państwa. **Maksymalnie 20 000 PLN** za błąd.
* **Programy w scope:**
  1. **NASK** (Tier 1: Niski 600 / Średni 4000 / Wysoki 9000 / Krytyczny 20 000 PLN)
  2. **CERT Polska** (takie same stawki do 20 000 PLN)
  3. **Portal Gov.pl** (do 20 000 PLN)
  4. **mSzyfr** — rządowy komunikator (do 20 000 PLN)
  5. **Gmina Władysławowo** (do 4 000 PLN — łatwiejszy cel na rozgrzewkę)
* **Wymagane w zgłoszeniu:** pełny opis + **PoC (Proof of Concept)** i instrukcja odtworzenia krok po kroku.
* **Warunek:** dyskrecja — nie ujawniamy luki publicznie do momentu wdrożenia poprawki.

## 2. Co najbardziej się opłaca szukać (wg tabeli nagród)

| Klasa podatności | Przykład | Prawdopodobna stawka (NASK Tier 1) |
|---|---|---|
| **Zdalne wykonanie kodu (RCE)** | SSTI → RCE, File Upload → RCE, SSRF → RCE | **20 000 PLN (Krytyczny)** |
| **Nieautoryzowany dostęp do baz danych** | SQL Injection | **20 000 PLN** |
| **Omijanie kluczowych mechanizmów uwierzytelniania** | Reset hasła bez dostępu do maila/telefonu, logowanie bez hasła | **20 000 PLN** |
| **Pełne przejęcie konta** | Przejęcie sesji/tokenów, fałszowanie tożsamości | **20 000 PLN** |
| **SSRF (wewnętrzne zasoby)** | Odczyt z sieci wewnętrznej, dostęp do prywatnych usług | 4 000–9 000 PLN |
| **IDOR / Broken Access Control** | Odczyt/modyfikacja cudzych danych | 4 000–9 000 PLN |
| **XSS** | poza wyłączeniami | 600–4 000 PLN |
| **CORS błędna konfiguracja** | odczyt wrażliwych danych przez nieautoryzowane domeny | nisko–średnio |
| **Open Redirect (w OAuth/OIDC lub łańcuchu ataku)** | przechwycenie kodu uwierzytelniania | średnio |

**Cel Minimum Viable Prize:** znaleźć **jedno** potwierdzone IDOR/XSS/SSRF (bardzo realne do znalezienia w kilku dniach recon + fuzzingu) — to już 600–4000 PLN.
**Cel dużej wygranej:** łańcuch: subdomain takeover → przejęcie konta administratora → RCE lub SQLi — to 20 000 PLN.

## 3. Konkretne pomysły na Ataki (do przetestowania TYLKO w scope hack.cert.pl)

### A. Subdomain Takeover → przejęcie konta (najlepszy stosunek wysiłku do nagrody)
Rządowe portale (Gov.pl, NASK, mSzyfr) często używają zewnętrznych usług: AWS S3, GitHub Pages, Azure, Shopify, Mailchimp, Zendesk. Jeśli znajdziemy CNAME wskazujący na usługę, która nie istnieje lub nie jest przypisana — możemy przejąć subdomenę. Potem:
* reset hasła wysyłany na domenę, którą kontrolujemy → przejęcie konta użytkownika/admina,
* kradzież tokenów OAuth/OIDC przez Open Redirect na przejętej domenie.

**Klasa:** przejęcie konta / omijanie uwierzytelniania → do 20 000 PLN.

### B. SQL Injection na publicznych endpointach
Formularze kontaktowe, wyszukiwarki, filtry w portalach. Wiekowe systemy administracyjne często mają starsze PHP/Java — SQLi wciąż się zdarza. Odczyt bazy = dostęp do danych wrażliwych.

**Klasa:** SQL injection / dostęp do danych wrażliwych → 9 000–20 000 PLN.

### C. IDOR / Broken Access Control w API mSzyfr / Gov.pl
Komunikator i portale mają API. Jeśli endpoint `/api/messages/{id}` nie sprawdza, czy zalogowany użytkownik jest właścicielem wiadomości — odczyt cudzych rozmów/danych osobowych.

**Klasa:** IDOR, autoryzacja i dostęp → 4 000–9 000 PLN.

### D. Mass Assignment
Przy rejestracji lub edycji profilu przesyłamy `role=admin` lub `is_verified=true`. Brak walutacji pól po stronie serwera.

**Klasa:** Mass Assignment → Wysoki, do 9 000 PLN.

### E. SSRF → zasoby sieci wewnętrznej
Endpoint pobiera URL podany przez użytkownika (np. generowanie podglądu strony, import awatara). Wskazujemy na `http://169.254.169.254` (IMDS) lub wewnętrzne porty administration.

**Klasa:** SSRF → 4 000–20 000 PLN (jeśli prowadzi do RCE — krytyczny).

### F. File Upload → RCE / omijanie filtrów
Formularze awatarów, załączników, dokumentów. Przesłanie pliku `.php` / `.jsp` pod zmienionym MIME, lub pliku z podwójnym rozszerzeniem `image.jpg.php`.

**Klasa:** File Upload → RCE → do 20 000 PLN.

### G. SSTI → RCE
Silniki szablonów (Jinja2, Twig, Freemarker, Thymeleaf) w polach wpisywanych przez użytkownika (kontakt, opinie, szablony wiadomości w mSzyfr).

**Klasa:** SSTI → RCE → do 20 000 PLN.

### H. Open Redirect w przepływie OAuth/OIDC (Gov.pl)
Portal Gov.pl jako punkt zaufania w logowaniu Państwowej e-usługi. Open Redirect pozwalający przekierować kod uwierzytelnienia na zewnętrzną domenę.

**Klasa:** Open Redirect (warunek spełniony) → Wysoki.

### I. HTTP Request Smuggling / Web Cache Poisoning
Na serwerach za 역 proxy/WAF. CL.TE / TE.CL może doprowadzić do przechwycenia cudzych żądań lub bypassu WAF.

**Klasa:** HTTP Request Smuggling / Cache Poisoning → Wysoki–Krytyczny.

## 4. Metodyka pracy z narzędziami z tego repo (Rust + Rayon)

### Faza 1 — Recon (dni 1–3)
1. **Subdomain enumeration** — narzędzie `rust/subenum` z Rayon: równoległe zapytania DNS do tysięcy słowników subdomen (pod rządowe domeny: `nask.pl`, `cert.pl`, `gov.pl`, `mszyfr.gov.pl`, `wladyslawowo.pl` i poddomeny).
2. **HTTP probe** — sprawdzenie, które subdomena odpowiadają (równoległe żądania HTTP, Rayon).
3. **Fingerprinting** — wykrycie technologii (serwer, CMS, framework, wersje) — łatwiej potem dobrać exploity.

### Faza 2 — Odkrywanie powierzchni ataku (dni 4–8)
1. **Directory/parameter fuzzing** — `rust/ffuzz`: równoległe testy tysięcy ścieżek (`/admin`, `/api/v1/`, `/debug`, `/swagger`, `/actuator`, `/.git`, `/config`).
2. **JS analysis** — moduł `python/jsminer` (Python FFI + multiprocessing): pobiera pliki JS, wyciąga klucze API, ukryte endpointy, tokeny, komentarze deweloperskie.
3. **Subdomain takeover scan** — sprawdzamy CNAME i czy usługa źródłowa jest nieprzypisana.

### Faza 3 — Weryfikacja podatności i PoC (dni 9–20)
Na odkrytych endpointach testujemy ręcznie (nie automatycznie exploitujemy na siłę, żeby nie położyć usług):
* SQLi (wyłącznie weryfikacja, bez wyciągania cudzych danych),
* SSRF na własny colaborator/interactsh,
* XSS z prostym alertem (tylko tam, gdzie w scope),
* IDOR na własnych dwóch kontach (jeśli aplikacja pozwala na rejestrację),
* Mass Assignment z polami `role`, `admin`.

Każdy potencjalny błąd udokumentowujemy: kroki, żądania HTTP, zrzuty ekranu, wpływ.

### Faza 4 — Zgłoszenia (dni 21–30)
Wypełniamy formularze na hack.cert.pl z pełnym PoC i instrukcją odtworzenia. Zgłaszamy najpierw błędy o najwyższym wpływie. Czekamy na werdyfikację, nie ujawniamy publicznie.

## 5. Dlaczego Rust + Rayon + GitHub Actions?

* **Ryzen 9 5950X** (16 rdzeni / 32 wątki) + **64 GB RAM** — Rayon rozdziela pracę na wszystkie rdzenie. Skanowanie tysięcy subdomen/endpointów, które w Pythonie single-thread zajęłoby godziny, w Rust + Rayon zajmuje minuty. Użytkownik deklarował, że Rust jest 100–200x szybszy — w recon/fuzzingu to realna przewaga czasowa (konkurs trwa tylko miesiąc).
* **GitHub Actions** — większa moc obliczeniowa niż lokalny sandbox. Workflow buduje narzędzia i może uruchamiać skany (tylko na celach w scope, na własną odpowiedzialność).
* **Python FFI + multiprocessing** — tam, gdzie Rust nie ma dojrzałej biblioteki (np. analiza plików JS, niektóre operacje kryptograficzne), używamy Pythona z wieloma procesami, a krytyczne odcinki wywołujemy przez FFI z Rustu.

## 6. Zasady bezpieczeństwa i prawne (nie do omijania)

1. **Testujemy tylko w scope** programów na hack.cert.pl. Poza scope = nielegalne.
2. **Żadnych DoS** — nie testujemy wydajnościowe, nie wysyłamy tysięcy zapytań na sekundę przeciwko produkcji.
3. **Zgłoszenia tylko przez formularz na hack.cert.pl**, z pełnym PoC.
4. **Dyskrecja** do momentu wdrożenia poprawki.
5. Nie atakujemy kont pracowników NASK ani nie używamy poświadczeń, których nie mamy.

## 7. Harmonogram (do 30.11.2026)

| Tydzień | Cel |
|---|---|
| 1 (3–9.11) | Zbudowanie narzędzi Rust/Rayon, recon wszystkich 5 domen, subdomain takeover scan |
| 2 (10–16.11) | Fuzzing katalogów/parametrów, analiza JS, odkrycie ukrytych endpointów API |
| 3 (17–24.11) | Weryfikacja SQLi/SSRF/IDOR/XSS, przygotowanie PoC |
| 4 (25–30.11) | Zgłoszenia przez hack.cert.pl, ewentualne uzupełnienia po weryfikacji |

**Kto co robi:** Agent dostarcza kod, narzędzia, strategię i workflow GitHub Actions. Użytkownik wykonuje rzeczywiste testy intruzycyjne i wysyła zgłoszenia — agent nie prowadzi aktywnych ataków na systemy państwa.
