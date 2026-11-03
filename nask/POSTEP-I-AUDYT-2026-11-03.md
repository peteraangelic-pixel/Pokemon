# Stan badań i kodu — 3.11.2026

## Nowsze źródła

- Repo `peteraangelic-pixel/Pokemon`, `arena/a450b00f-pokemon`: przed naszą publikacją `b7e9ef3bc564319ef2ae072f968d66d9b0137588`. Zawiera poprzednie materiały Pokémon i ARC, w tym wyniki Codex v3; nie jest to gałąź nowego projektu NASK. Niezapisane zmiany w starszym checkoutcie są osobne i należy je chronić.
- Repo `peteraangelic-pixel/NASK`: `main` `e0a562e`; `arena/a29ca234-nask` `3f3bc29` zawiera kopie materiałów Drive, wybrane materiały Pokémon oraz dokumenty innego projektu. Osobna gałąź `codex/multi-program-lab-20261103` `8b3228a` ma nowszy Python + Rust/Rayon FFI oraz własny manifest i workflow.
- We wskazanym folderze Drive jest 13 widocznych plików; archiwum ZIP ma nowy identyfikator `1f5i5WhTyrPsYpQf0rVaZdj9y1OQAg4vC`, rozmiar 53842 B i czas modyfikacji 18:35 UTC. Pozostałych 12 plików nie wykazuje nowej daty modyfikacji. W repo NASK `3f3bc29` jest kopia ZIP o tym samym rozmiarze; odczytałem tę kopię, **nie potwierdzono identyczności bajtowej z plikiem Drive**. Zawiera 28 wpisów, kontrola CRC przeszła, a w środku jest też projekt Rust `recon`. Nie uruchomiono go.

## Rzeczywisty postęp Codex, niezależna kontrola

- [Run 41699930075](https://github.com/peteraangelic-pixel/NASK/actions/runs/41699930075) ma status `success`, commit `8f02d32`; raport Codex opisuje 48 żądań, 24 hosty, 46 odpowiedzi, zero potwierdzonych luk. Te liczby pochodzą z raportu autora; surowych prywatnych dowodów nie odczytałem i nie weryfikowałem samodzielnie.
- [Run 41701587605](https://github.com/peteraangelic-pixel/NASK/actions/runs/41701587605) ma status `success`, commit `f453cac`; raport podaje testy Linux/Windows, Rust i rzeczywiste FFI. Potwierdzono status przebiegu przez GitHub, nie powtórzono tutaj całej kompilacji tej gałęzi. Następny commit `8b3228a` dotyczy dokumentacji. Opis pilota zawiera poprawkę fałszywego trafienia Modernizr. Dodatnia punktacja skanera nie jest podatnością.
- mSzyfr w pilocie odroczono: brak zweryfikowanego konkretnego hosta dla wildcard. Odłożono także CTF. Wniosków o braku luk nie ma.

## Ważne zastrzeżenia przed kolejnym ruchem

1. `programs/2026-11.json` w `8b3228a` zawiera `pllum.org.pl` i `mwdb.cert.pl` jako aktywne hosty, mimo rozbieżności z odczytanymi regulaminami PDF (`plum.org.pl`, `wmdb.cert.pl`). Nasza zasada robocza: wstrzymać obie pary do pisemnego wyjaśnienia. Wcześniejszy pilot deklaruje wykonanie listy hostów, więc nie zakładać, że omijał te pozycje.
2. `Governor.acquire()` w `tools/recon/python/nasklab.py` sprawdza flagę stop przed uśpieniem, ale nie po nim. Drugi worker może obudzić się i otrzymać zezwolenie po sygnale 429. Przy współbieżności żądanie już rozpoczęte nie zostanie cofnięte. Potrzebny test wyścigu, bezpieczny wspólny stan i jasna semantyka przerwania; nie uruchamiano na tej podstawie ponownie sieci.
3. Kod ustawia stop dla 429, ale nie dla 503. Proponujemy stop także dla oznak niedostępności. Lokalny lock działa tylko w jednym checkoutcie: nie synchronizuje niezależnych maszyn ani runnerów. GitHub concurrency ogranicza tylko wskazaną grupę w danym repo, nie cały świat. Jedna zatwierdzona instancja, bez innych badań sieciowych w tym samym czasie.
4. Kolektor zapisuje pełne treści HTML/JS do katalogu `private/` przed zaszyfrowaniem. Regulamin platformy §7.3 zabrania przetwarzania, kopiowania i usuwania cudzych danych osobowych i poufnych. Samo szyfrowanie nie gwarantuje zgodności, jeżeli treść nieoczekiwanie zawiera takie dane. Potrzebna procedura minimalizacji i bezpiecznego zatrzymania, a nie założenie, że wszystkie publicznie dostępne odpowiedzi są nieproblematyczne.
5. Workflow z ZIP nazywa sieciowy sweep „pasywnym”; nie jest pasywny. Guard `www.` automatycznie uznaje subdomenę za równoważną hostowi nadrzędnemu, co nie wynika automatycznie z zakresu, a limiter jest wspólny tylko dla procesu. Nie używać tego pakietu na celach konkursowych bez poprawy i audytu. Domyślne 4,5 req/s nie jest przyjętym przez nas zapasem 1–3 req/s.
6. Nie kopiować prywatnych wyników, surowych odpowiedzi, kluczy ani nieujawnionych PoC do publicznego repo i logów Actions. Nie deklarować odnalezienia podatności na podstawie skanera.

## Następny etap

Wykorzystać doświadczenia bardziej rozwiniętego projektu Codex, zamiast ponownie budować wszystko od zera. Uzupełnić audyt zakresu, testy zachowania stop i politykę danych; ustalić pisemnie sporne hosty. Na razie nasze `nask/lab` to wyłącznie syntetyczny, nienetworkowy prototyp. Dopiero po poprawkach i niezależnych testach bezpieczeństwa rozważyć pojedynczy kontrolowany proces, z limitem łącznym i bez równoległego pilotażu w innym repo. Żadnego nowego rekonesansu ani zgłoszenia w tej sesji nie wykonano.
