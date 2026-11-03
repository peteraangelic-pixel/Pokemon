# NASK — niezależny przegląd źródeł (3.11.2026)

## Zakres i wersje

- `peteraangelic-pixel/NASK`: `main` = `e0a562e19cf84c5c17bdda02527b54ba556ff92b`, wyłącznie README; `arena/a29ca234-nask` = `ed96a2f660f72854f2e3466436f698eec7fd01c8`, 12 commitów przed main. Przejrzano drzewo, workflowy, kod sieciowy i generator; kod pobrany do tymczasowego katalogu, bez uruchomienia przeciw usługom.
- Folder Drive `1tWcRm79xeYQslPACYOagZ0bmhuKnlBMo`: lista 13 plików, przeczytano 12 plików tekstowych, w tym strategię, plan, wyniki i przegląd narzędzia. ZIP `08-nask-bugbounty-komplet.zip` nie został przeze mnie pobrany ani rozpakowany, dlatego zawartość ani twierdzenie o 16 testach nie są niezależnie zweryfikowane.
- Ograniczenie: brak kompilatora cargo w tej sesji, nie odtwarzałem kompilacji ani testów zgłaszanych przez autora z Drive; sprawdziłem kod źródłowy i konfigurację CI. Nie przeprowadziłem nowych testów NASK.

## Wypłaty — co mówi regulamin

NASK: zgodnie z [§7 regulaminu](https://hack.cert.pl/api/v1/public/institutions/nask-pib/programs/nask/editions/1/terms/download), zwycięzcy mogą być wyłaniani i powiadamiani w trakcie konkursu, zgłoszenia mogą być oceniane sukcesywnie albo w turach, a wypłata następuje do 60 dni po ogłoszeniu wyników; zwycięzcy zasadniczo mają być wyłonieni nie później niż 30 dni po zakończeniu edycji, z zastrzeżeniem rozstrzygnięć wcześniejszych. Nie jest to gwarancja natychmiastowej wypłaty. CERT i Gov.pl również przewidują możliwość wcześniejszego przyznania i termin do 60 dni po wynikach; nie potwierdzono, że NASK jest od nich szybszy. Władysławowo w swoim regulaminie wskazuje 90 dni po końcu na wyłonienie zwycięzców i 60 dni od wyników na wypłatę. Wybieramy NASK jako punkt wyjścia, ale bez twierdzenia, że jest najszybszy ze wszystkich.

## Co wnosi Drive

- Użyteczne wskazówki o mapie usług, różnicowaniu własnych kont, fałszywych trafieniach wynikających z catch-all i rotujących wartości, oraz konieczności kontekstowej walidacji. To prowadzi do oszczędnych, precyzyjnych badań, nie do powtarzania starych skanów.
- Plik `07-recon-out-20261103.jsonl` zawiera 12 rekordów wstępnego pobrania `/`; **nie jest pełnym śladem 204 żądań**. Nie odtworzono danych dla 192 innych żądań. Raport o zero ekspozycji traktujemy jako relację autora w zakresie ich testów, nie dowód braku luk w aplikacjach; porównania tech/HTTP mogą być nieaktualne. Wiersze m.in. `dns.pl` wskazują status 0, a opis innego pomiaru wskazuje 200 — trzeba uwzględniać kontekst pomiaru i nie utożsamiać obu biegów.
- Identyfikacja frameworka z nagłówków nie dowodzi, gdzie działa autoryzacja ani że jest podatny na dane CVE. Kody 200/403 same w sobie nie wykazują obejścia. Brak danych o publicznej rejestracji w HIVE; tworzenie kont i analiza dostępu wyłącznie zgodnie z zasadami, bez zgadywania i przetwarzania cudzych danych. Nie uznawać automatycznie IDOR za 9000–20000 zł: przyznaną kategorię, tier i CVSS ocenia organizator.
- Wyciąg z Drive wskazuje `pllum.org.pl`, natomiast odczyt oryginalnego PDF wskazuje `plum.org.pl`, a strona programu `pllum.org.pl`. Prosić NASK o rozstrzygnięcie, wstrzymać oba warianty do wyjaśnienia. Osobno jawnie wskazana `dataannotation.pllum.org.pl` występuje w obu wersjach; to nie jest upoważnienie do innych subdomen. Strona CERT wskazuje `mwdb.cert.pl`, PDF `wmdb.cert.pl`; nie zgadywać.
- Przykładowy PoC na Drive jest ilustracją, a nie znaleziskiem. Przykład nie dowodzi IDOR: konto B jest odbiorcą wysłanej do niego wiadomości, więc sam odczyt B może być zgodny z oczekiwaniami. Adres w przykładzie ponadto nie jest wykazanym zakresem mSzyfr. Szablon wymaga korekty kwot na kategorię i redakcji danych; żadnych prawdziwych tokenów w publicznym repo.

## Audyt repo NASK

- Rust `probe`, `ffuzz`, `takeover`: kod równolegle odpytuje sieć przez Rayon, a mechanizmów wspólnego limitera ani wymuszanej listy dozwolonych hostów w tych plikach nie znaleziono. Deklaracja w komentarzu nie jest egzekwowanym bezpiecznikiem. Kod `subenum` wylicza nazwy pod dowolnym podanym hostem i rozwiązuje je DNS-owo bez sprawdzania zakresu, więc przykład `nask.pl` może obejmować nazwy niewymienione w programie. Nie uruchamiać tych narzędzi na celach konkursowych w tej postaci.
- `python/jsminer.py` pobiera dowolne URL-e przez wiele procesów, bez wymuszenia zakresu/centralnego limitu, może kopiować potencjalne sekrety w wyniku, a `urlopen` domyślnie obsługuje przekierowania. Nie używać w tej postaci w konkursie. Do analizy wyłącznie offline można zaprojektować odrębny tryb bez zapisywania wartości sekretów, po weryfikacji.
- CI: `cargo fmt` ma `continue-on-error`, `cargo clippy --all-targets || true`; workflow nie zapewnia poprawnej kompilacji ani testów. Repo dodaje `native` pod katalogiem workspace, lecz nie jako jego członka; źródło analizy z Drive zgłasza również błędy kompilacji trzech narzędzi HTTP. Sam nie odtwarzałem builda.
- Korekta względem audytu Drive: `scan.yml` nie musi mieć domyślnej ścieżki do nieistniejącego pliku: w przejrzanym commicie `wordlist` domyślnie jest puste i workflow tworzy fallback w `/tmp/subs.txt`. Nadal nie należy go uruchamiać: generuje nazwy subdomen bez sprawdzania dozwolonego zakresu.
- `gen_report.py` oraz szablon jako format mogą być przydatne, lecz generator automatycznie wstawia oświadczenia o zgodności, których nie weryfikuje, i może zapisać surowy PoC do zwykłego pliku. Nie traktować tego jako zatwierdzonego procesu ani wrzucać jego wyników do publicznego repo. Oświadczenia potwierdza człowiek.

## Ustalenie robocze

Priorytet: program NASK, ręczna analiza funkcji oraz ewentualna weryfikacja na własnych, nieszkodliwych zasobach z zachowaniem pełnych zasad programu. Offline analizator na danych syntetycznych może używać Rust/Rayon; jakikolwiek klient sieciowy wymaga osobnego audytu scope, przekierowań, wspólnego limitowania obejmującego wszystkie procesy oraz ochrony danych. Żadnych niejawnych wyników, logów, poświadczeń ani PoC w publicznych repozytoriach lub publicznych logach/artefaktach Actions.
