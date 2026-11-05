# Strategia na 5 programów — i dlaczego „więcej skanerów" nie da pieniędzy

Odpowiedź na pytanie: *czy zrobić narzędzie Python FFI + Rust, które sprawdza wiele podatności
w kilku miejscach konkursu jednocześnie, sterowane przez Actions?*

**Krótka odpowiedź: tak dla koordynatora, nie dla fuzzera.** Poniżej dowód z pomiaru,
a nie z opinii.

---

## 1. Fakty, które zmieniają plan (przeczytane z 5 regulaminów, nie z artykułu)

| program | pula | Tier 1 | Tier 2 | uwaga |
|---|---:|---|---|---|
| NASK | 100 000 zł | 600/4 000/9 000/**20 000** | 300/2 000/4 500/10 000 | największa pula |
| CERT Polska | — | 600/4 000/9 000/**20 000** | 300/2 000/4 500/10 000 | `*.cert.pl` = wildcard |
| Portal Gov.pl | — | 600/4 000/9 000/**20 000** | — | **tylko `www.gov.pl`**, jeden host |
| mSzyfr | — | 600/4 000/9 000/**20 000** | — | `*.komunikator.narodowy.gov.pl` = wildcard |
| Gmina Władysławowo | — | **100**/1 000/2 500/4 000 | 100/600/1 500/2 500 | stawki 5× niższe |

Razem **26 hostów dokładnych + 2 strefy wildcard**. Wszystkie pięć programów ma
**identyczny limit 5 req/s** i identyczne zasady (§6 pkt 1–2 w każdym). Więc owszem —
ograniczenie dotyczy wszystkich, nie tylko NASK.

**Najważniejsze przeoczenie w moim poprzednim planie:** `*.cert.pl` w Tier 2 to **wildcard**,
a nie lista. CERT Polska ma całą strefę, do której należy `mwdb.cert.pl` — czyli
**platforma malware-sharing** (najciekawszy cel w całym konkursie pod kątem danych wrażliwych).
Do tego `ctf.hack.cert.pl` (Tier 2) i `hack.cert.pl` (Tier 1) — czyli **sam portal konkursu**
jest w zakresie.

---

## 2. Pomiar, który przesądza sprawę

Zbudowałem koordynatora i puściłem go na **wszystkich 26 hostach pięciu programów**:

```
hostów: 26   żądań: 208   czas: 156 s   (efektywnie 1,33 req/s, sufit 5,0)

=== DO ZGŁOSZENIA: 0 ===
=== ODRZUCONE PRZEZ REGULAMIN: 19 ===
   braki X-Frame-Options / CSP frame-ancestors  → §8 poz. 3.1 WYKLUCZA
   brak security.txt                             → informacja operacyjna, nie podatność
```

**Zero findingów do zgłoszenia na 26 hostach.** I to jest odpowiedź: to nie jest problem
z narzędziem, to jest własność konkursu.

### Dlaczego tak wychodzi — arytmetyka regulaminu

§8 to lista rzeczy, za które **nie płacą**. I pokrywa ona praktycznie całą powierzchnię,
jaką skaner jest w stanie zobaczyć bez logowania:

| co skaner widzi bez konta | czy płaci |
|---|---|
| brak nagłówków bezpieczeństwa, HSTS, captcha, flagi cookies | **nie** (3.1–3.4) |
| stack trace, wersje, listingi katalogów, user enumeration | **nie** (2.1–2.2) |
| nieaktualne biblioteki, znane CVE bez PoC | **nie** (3.9–3.10) |
| open port bez znaczenia | **nie** (3.8) |
| blind SSRF z samym DNS | **nie** (7) |
| open redirect bez OAuth/łańcucha | **nie** (8) |
| brak rate limitingu bez scenariusza przejęcia konta | **nie** (10.3) |
| klucze API bez możliwości nadużycia | **nie** (12.1) |
| **raport ze skanera bez ręcznego potwierdzenia** | **nie** (14.4) |

Co **płaci**: IDOR, mass assignment, przejęcie konta, SSRF z odczytem, upload→RCE,
RCE, dane wrażliwe, SQLi. **Wszystkie te rzeczy wymagają sesji, konta i zrozumienia logiki
aplikacji.** Żadna nie jest widoczna w odpowiedzi HTTP na anonimowe żądanie.

**Wniosek: fuzzer nie jest tu wąskim gardłem — jest bezużyteczny.** Przy 5 req/s słownik
1000 ścieżek to 3,5 minuty i szum, a nie wynik.

---

## 3. Lepszy plan: rozdziel role inaczej, niż proponujesz

Twoja intuicja „nie skupiajmy się na jednej rzeczy" jest **słuszna co do celu**, ale
mechanizm musi być inny. Nie „więcej automatów równolegle", a **podział na to, co robi
maszyna, i to, co robisz Ty**.

| warstwa | kto | co | dlaczego tak |
|---|---|---|---|
| **1. Guard i inwentarz** | maszyna | 26 hostów, 5 programów, zakres, stawki, deduplikacja | deterministyczne, tanie, bezbłędne |
| **2. Weryfikacja „czy to w ogóle płaci"** | maszyna | każdy finding dostaje `accepted: true/false` wg §8 | **największa oszczędność czasu** — nie piszemy raportów za 0 zł |
| **3. Rekonesans offline** | maszyna, Rayon | endpointy i parametry z bundle'ów JS, mapy API | 16 rdzeni naprawdę pomaga, sieci nie rusza |
| **4. Sesja i logika** | **Ty** | rejestracja, dwa konta, IDOR, mass assign, upload, SSRF | tylko to płaci |
| **5. Koordynacja i raport** | ja | priorytetyzacja, generator raportu, rejestr zgłoszeń | nie tracimy czasu na duplikaty |

### Gdzie realnie leży kasa — w tej kolejności

1. **`mwdb.cert.pl`** (CERT, Tier 1) — platforma wymiany malware. Najbogatsze dane wrażliwe
   w całym konkursie. Wymaga konta — i to jest jedyny sposób, żeby coś tam znaleźć.
2. **`moje.cert.pl`** / **`n6portal.cert.pl`** (CERT, Tier 1) — panele użytkownika = IDOR, sesje.
3. **`hack.cert.pl`** (CERT, Tier 1) — **portal konkursu jest w zakresie**. Rejestracja, zgłoszenia,
   role, punktacja. Na tym można było pracować od pierwszej minuty.
4. **`komunikator.narodowy.gov.pl`** (mSzyfr, wildcard) — komunikator = cudze wiadomości = poz. 3.2 „dostęp do prywatnych treści". Wysoka/krytyczna.
5. **`www.gov.pl`** — jeden host, ogromny ruch, najwyższa konkurencja. Nisko priorytetowo.
6. **Władysławowo** — najniższe stawki (100–4 000 zł). Bierzemy tylko, jeśli coś wpadnie samo.

### Czego Actions NIE rozwiąże

Actions da 16 rdzeni na kompilację i analizę offline — i to jest realna wartość.
Ale **nie da sesji w aplikacji**: nie zaloguje się na dwa konta, nie przejdzie flow
rejestracji, nie zauważy, że `?id=123` pokazuje cudze dane. A właśnie to płaci.
Poza tym GitHub może blokować skanowanie ruchu do domen rządowych z runnerów — tego nie weryfikowałem.

---

## 4. Co już działa

```
coordinator/
├── programs.json   5 programów, 26 hostów, 2 strefy wildcard, stawki, wykluczenia
├── scope.py        guard: allow > exclude > exact > wildcard; 26/26 testów przechodzi
├── checks.py       4 checks pasywne, każdy zwraca accepted:true/false wg §8
└── coord.py        koordynator: ThreadPool + JEDEN globalny limiter 4,5 req/s
```

Testy guardu (najważniejsze, bo dotyczą granicy zakresu) — przechodzą wszystkie:

```
hack.cert.pl          → cert Tier1   (apex jest w zakresie)
panel.hack.cert.pl    → None         (subdomeny hack.cert.pl NIE są)
ctf.hack.cert.pl      → cert Tier2   (allow-lista, wyjątek z regulaminu)
gitlab.snkom.nask.pl  → None         (poza §5)
*.komunikator.narodowy.gov.pl.evil.com → None  (nie dajemy się oszukać)
```

Uruchomienie:
```bash
python3 coord.py table        # 26 hostów, 5 programów, stawki
python3 coord.py scope cert.pl
python3 coord.py run --limit 26
```

---

## 5. Odpowiedź na „a może uniwersalne inteligentne narzędzie"

Byłoby warte tyle, ile warte są jego reguły. Problem nie leży w wykrywaniu — leży w tym,
że **konkurs płaci tylko za podatności wymagające stanu zalogowanego użytkownika**,
a to nie jest problem, który da się rozwiązać szybkością. Da się go rozwiązać **mapą
aplikacji** — wiedzą, gdzie są identyfikatory, gdzie są role, gdzie jest upload.

Dlatego następny krok to nie kolejny skaner, ale **jedna rzecz na jeden dzień**:
wejść na `hack.cert.pl` i `mwdb.cert.pl`, założyć własne konta, spisać endpointy
i identyfikatory, i dopiero potem puszczać cokolwiek automatycznie.

**Uczciwa kalibracja:** przy 26 hostach i pięciu programach, z których jeden ma pulę
100 000 zł, a reszta prawdopodobnie po kilka–kilkanaście tysięcy, realistyczny wynik
dla jednej osoby w miesiąc to **jedno–dwa trafienia w klasie 4 000–9 000 zł**.
Nie 20 000 zł, bo te wymagają łańcucha (SSRF→odczyt, upload→RCE), który trudno
znaleźć w cudzej aplikacji bez jej kodu.

---

## Zastrzeżenia

* Wszystkie stawki, zakresy i wykluczenia: z sekcji „Zakres systemów" pięciu programów
  na hack.cert.pl, stan 2026-11-03.
* Pule nagród dla CERT/Gov/mSzyfr/Władysławowo **nie są podane** na stronach programów —
  podałem tylko znane stawki za pojedynczy błąd.
* „19 findingów odrzuconych" to wynik jednego przebiegu na 26 hostach, nie dowód,
  że w tych systemach nie ma podatności. Dowodzi tylko, że **bez sesji nic nie widać**.
* Nie weryfikowałem, czy GitHub Actions pozwala na ruch do domen `*.gov.pl` z runnerów.
