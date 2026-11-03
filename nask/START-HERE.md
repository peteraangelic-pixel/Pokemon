# NASK Bug Bounty — plan startowy

Stan researchu: 3 listopada 2026. To dokument planistyczny; nie zawiera znalezionych luk. Przed testem należy ponownie przeczytać aktualny regulamin platformy, edycji i aktualny zakres danego programu. Niczego nie testowano aktywnie i niczego nie zgłoszono.

Przegląd badań innych sesji i korekty: [PRZEGLAD-ZRODEL-2026-11-03.md](PRZEGLAD-ZRODEL-2026-11-03.md). W pierwszej kolejności pracujemy nad programem NASK; nie uruchamiamy bez audytu skanerów z repo NASK.

## Program i bezpieczeństwo

Źródła: [platforma](https://hack.cert.pl/), [regulamin platformy](https://hack.cert.pl/terms-of-service), [CERT Polska](https://hack.cert.pl/programs/cert-polska/bug-bounty-cert-polska/editions/1), [NASK](https://hack.cert.pl/programs/nask-pib/nask/editions/1), [Gov.pl](https://hack.cert.pl/programs/centralny-osrodek-informatyki/portal-gov-pl/editions/1), [mSzyfr](https://hack.cert.pl/programs/mszyfr/mszyfr/editions/1), [Władysławowo](https://hack.cert.pl/programs/cciod-wladyslawowo/gmina-wladyslawowo/editions/1).

- Programy aktualnie 03–30.11.2026; reguły mogą się zmienić i przyjmowanie może zostać zawieszone.
- Tylko wskazane systemy. Scope każdej edycji ma pierwszeństwo nad domysłami; żadnych innych subdomen czy przekierowań poza zakresem. W CERT `hack.cert.pl` jest objęte, jego subdomeny wykluczone poza jawnym wyjątkiem `ctf.hack.cert.pl`; `*.lab.cert.pl` jest wyłączone.
- Rozbieżności źródeł wymagają potwierdzenia przed testami: CERT strona `mwdb.cert.pl`, PDF `wmdb.cert.pl`; NASK strona `pllum.org.pl`, PDF `plum.org.pl`. Wstrzymać oba warianty do pisemnego wyjaśnienia organizatora. Nie przyjmować brzmienia strony za jedyne rozstrzygnięcie.
- Automatyczne narzędzia maksymalnie 5 req/s. Własna zasada operacyjna: wspólny limiter dla wszystkich uruchomień i źródeł, znacznie poniżej limitu, z zapasem, bez prób maksymalizacji przepustowości; jeśli nie można zagwarantować globalnego limitu, nie uruchamiać równolegle. Pełny zakres reguł może być ostrzejszy. Przerwać przy oznakach problemów z usługą.
- Nie DoS, obciążenia, spam, phishing. Tylko własne/dedykowane konta testowe; nie korzystać z kont innych użytkowników. Nie przetwarzać, kopiować ani usuwać cudzych danych osobowych lub poufnych; w razie nieoczekiwanego dostępu przerwać, nie eksplorować i odpowiedzialnie zgłosić.
- Przykładowo interesujące kategorie: kontrola dostępu/API, XSS, CSRF, SSRF i SQLi — w zakresie definicji, wykluczeń i bezpiecznego PoC. Surowy wynik automatu nie jest zgłoszeniem. Brak nagłówków, self-XSS, nieaktualne wersje bez wpływu i DNS-only blind SSRF są na liście wykluczeń.
- Zgłoszenie z odtwarzalnym, nieniszczącym PoC i wpływem przez zalogowane konto platformy. Szczegóły nie mogą być ujawniane do czasu usunięcia. 3 kolejne odrzucenia z określonych powodów mogą skutkować blokadą zgłoszeń. Nie obiecywać płatności ani terminu natychmiastowego dochodu.
- Programy NASK, CERT, Gov.pl, mSzyfr podają odpowiednio 600/4000/9000/20000 zł dla Tier 1 lub jednej tabeli; Tier 2 NASK/CERT połowa. Władysławowo ma niższe stawki. Kwalifikacja i CVSS 4.0 należą do organizatora. Sprawdzić odpowiednie regulaminy edycji.
- Konto platformy: rejestracja przez Węzeł Krajowy, PESEL, 18+, polski rezydent podatkowy, stosowne wyłączenia i akceptacja; sprawdzić szczegóły samodzielnie. Na potrzeby płatności regulamin NASK/Gov/mSzyfr podaje polski rachunek, termin do 60 dni od wyników i zgłoszenia mogą być odrzucane albo duplikatami.

## Plan poszukiwań — priorytety

1. **Dokładne sprawdzenie zakresu i zasad, a potem mapa funkcji** jednej wybranej aplikacji: publiczne powierzchnie, własne konto, formularze i sposób pracy użytkownika. To nie jest pozwolenie na skanowanie całej infrastruktury.
2. **Różnicowe porównanie dostępu** w zakresie i na własnych kontach, o ile organizator dopuszcza ich tworzenie: czy dwa uprawnienia lub sesja/wylogowanie są konsekwentnie traktowane? Używać wyłącznie samodzielnie utworzonych, nieszkodliwych danych. Wykazywać wpływ bez dotykania danych osób trzecich.
3. **Analiza przepływu zaufania**: bezpiecznie analizować interfejs i własne, wcześniej pozyskane odpowiedzi; wyszukiwać miejsca, gdzie aplikacja inaczej traktuje tę samą operację w UI i API. Istotne są dowody realnego wpływu, nie samo istnienie endpointu.
4. **Dobre zgłoszenie zamiast masy skanów**: zakres, stan początkowy, minimalne kroki, spodziewany i rzeczywisty wynik, ograniczony PoC, wpływ i redakcja danych; bez zgadywania CVSS i bez publicznego ujawniania. Przed zgłoszeniem ponownie sprawdzić stan programu i wymagania organizatora.

Nie ma dowodu, że te hipotezy występują na wskazanych systemach. Nie uruchamiać automatycznych testów do czasu przygotowania poprawnej listy zakresu, bezpiecznego limitera i przeglądu całości zasad.

## Narzędzia i infrastruktura

Preferencja: Rust + Rayon dla CPU-bound lokalnych prac (analiza offline, deduplikacja, normalizacja, testy dużych korpusów); porównywać z Pythonem, bo 100–200× nie jest gwarantowane. Sieciowe próby są ograniczone regulaminem i nie powinny wykorzystywać Rayon do intensyfikacji żądań. Python/FFI/multiprocessing tylko gdy dane i mierzalna korzyść to uzasadniają. Lokalny Ryzen 5950X/64 GB jest dobry do offline; nie zwiększa dozwolonej szybkości testów.

GitHub Actions nadaje się do kompilacji i testowania na lokalnych fikcyjnych danych, nie do obchodzenia limitów i nie do publikowania dowodów. `peteraangelic-pixel/NASK` jest PUBLICZNY: bez logów ruchu, odkryć przed naprawą, sekretów, PII, sesji czy surowych PoC. Nie wysyłać tam nawet z pozornie prywatnymi artefaktami Actions; nie zakładać ich poufności. Tutejsze outbound połączenia sandboxa są ograniczone do wybranych domen; bezpośrednie testy NASK stąd nie są dostępne. Nie używać Actions jako obejścia zasad ani limitów.
