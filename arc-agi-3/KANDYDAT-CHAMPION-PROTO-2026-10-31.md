# Kandydat Champion Proto — odpowiedź na peer audit, 31.10.2026

## Decyzja i status

Kandydat do opracowania: odzyskane v3 jako nienaruszona baza + osobno sprawdzane poprawki alokacji i portfolio specjalistów. To nie jest gotowy notebook ani gwarancja TOP5. Nie zakładamy wyniku v15 bez identyfikacji jego submisji. Peer audit: Smak `codex/arc-local-lab-v18-20261030` `c0b47ca11794ed684a5ec5fadf57f3461b24d7de`; gałęzie źródłowe wskazane w załączniku PEER-AUDIT-RESPONSE-20261031.md.

Ponownie uruchomione: 37 testów template i guard (37 passed), dwie syntetyczne sondy 300 przypadków na rodzinę; wyniki oryginał copy 149/149, rotate 299/18, invert 300/0, random 297/23; single-mismatch odpowiednio 149/149, 17/3, 0/0, 8/1 (rozpoznane/trafne). Sonda ma narzuconą sztuczną dystrybucję; liczby nie są odsetkiem błędów na Kaggle. Nie odtwarzano 25 gier ani Duck/Flash-Next.

## Korekta poprzedniego projektu

Oryginalny template **nie jest bezpieczny do aktywacji w notebooku**: zgodny przewidywany kolor nie dowodzi słusznego celu i może nastąpić oscylacja. Guard 32 ogranicza tę pętlę, ale może przerwać dobrą partię; single-mismatch nie eliminuje fałszywych rozpoznań ani nie obejmuje wszystkich gałęzi inferencji. Syntetyczne random po bramce nadal 8 rozpoznań, z czego tylko 1 trafne. Dlatego oba mechanizmy są materiałem badawczym, nie gotowym kandydatem.

## Konstrukcja

A. Kontrola = dokładne v3, notebook SHA256 8d0195f92c5518a41d14edbfca596b72c27690f269f681bbaa9af0bc3d257bcc; nie zmieniać służącego modelu, kontekstu, temperatury, world modelu ani budżetu w grupie kontrolnej. Historyczne 26,25 nie jest gwarancją obecnego wyniku.

B. Eksperyment harmonogramowania (jedna zmienna): porównać v3 z umiarkowanym limitem czasu na grę i ewentualnym bezpiecznym miękkim zatrzymaniem. Próg dobrać offline, nie przyjmować magicznych 45 lub 49 minut. Weryfikować działanie w rzeczywistym solverze i sprawiedliwy dostęp każdej gry: jak wyliczany jest cap, kolejka, status zadań w toku, koszty modelu i koszt dokończenia. Samo porównanie smoke 48 min z capem rerun 532 min nie dowodzi głodzenia kolejki. Replay nie odtworzy zmienionych decyzji po capie ani współzależności inference. Hipoteza: ograniczenie gier z małym przyrostem może zwiększyć pokrycie, ale może też uciąć trudne rozwiązania i obniżyć wynik.

C. Eksperyment specjalisty (osobny od B): v3 + kompetencja z wyłącznikiem domyślnym podczas developmentu. Wybierać mechanikę z danych, nie ID. W celu sprawdzenia template naprawić oscylację, błędy/fallback, lifecycle izolacji, ruchy kończące poziom, reguły potwierdzania celu i sygnały fałszywego rozpoznania. Zachować zarówno abstencję jak i jawny limit; żadna z tych ochron nie daje gwarancji braku szkody. Sprawdzić późniejsze stany i gry niewykorzystane w projektowaniu. Nie rozłączać oryginalnej v3, gdy reguła niepewna. Bezpieczna obsługa wyjątków po wykonanym kroku nie może duplikować kroku.

D. Dopiero jeżeli B i C osobno wygrywają, połączyć i porównać z A w nowym teście, ponieważ interakcje kosztu i solvera są możliwe. Pamięć między poziomami, replay i następna rodzina mechanik stanowią dalsze oddzielne eksperymenty; nie deklarować ich skuteczności.

## Kwalifikacja

Wspólny korpus różnych mechanik i seedów, te same gry/budżety, osobny holdout; raport per gra, poziomy, oficjalna punktacja, błędy narzędzi/API, czas i działania, liczba aktywacji i negatywne efekty. Wystandaryzować współbieżność i kolejność. Zobaczyć także faktyczne czasy oczekiwania i liczbę gier rozpoczętych przed końcem budżetu. Lokalny Qwen27B to wstępny sygnał, nie substytut paired A/B z Flash-Next. Pozytywny wynik na development ft09 nie jest walidacją globalną; unit testy ani GPU speedup nie są poprawą score.

Submisje Kaggle tylko na osobne, wyraźne GO użytkownika. Repozytorium Smak nie zostało zmodyfikowane; ten plik leży w gałęzi `arena/a450b00f-pokemon`, lokalnie, nie opublikowany na Smak.
