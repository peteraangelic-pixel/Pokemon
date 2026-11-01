# Kandydat Codex v3-slim do niezależnej oceny — 1 listopada 2026

## Status
AKTUALIZACJA: test zakończony COMPLETE. Wariant ODRZUCONY: 17.35047 / 24 ukończenia wobec kontroli 27.49667 / 33. Patrz RESULT.md, COMPARISON.json i ACTIVATION.json. Sekcje działały w10/10 grach,brak crashy. To publiczny smoke,NIE wynik konkursowy. Zachowano kod do audytu;nie promować jako poprawy. Kolejny odrębny eksperyment levelscope na naszej gałęzi ma sekcje OFF i nie dziedziczy tego wyniku.

## Co dokładnie zmieniono
Dokładna odzyskana v3 (SHA bazowego notebooka w MANIFEST.json), jedyna zmiana polityki: ARC3_MEMORY_SECTIONS off -> slim. Pozostaje bieżący World model i Plan. To upstream mechanizm, nie lalalia solved-level memory. Model, roster 10 publicznych gier, 48 min/gra, concurrency 10 i konfiguracja serwowania identyczne z kontrolą. Zmiana nazwy wariantu jest opisana w manifeście. Bez template, routera, nowych capów, recovery lub sterowania po game ID.

agent.ipynb SHA256: 9156966a191604eb7a0285aecd4d4c9ba0bef557232dc0315d2cbe63bea95458

## Dowody i ograniczenia
verification.json: rzeczywisty ToolAgent niesie World model/Plan w slim, usuwa je w off; 34 źródła inference identyczne z bazą, czysty łańcuch patchy. To kontrola infrastruktury, nie pomiar jakości. Kontrola na docelowym Flash-Next miała 33 ukończenia i 27.49667 w publicznym smoke; pojedynczy historyczny przebieg nie dowodzi przewagi nowego wariantu. Kod pamięci ukończonych poziomów 28.40/32 i recovery 17.11/25 odrzucono — nie scalać ich automatycznie.

## O co prosimy przy ocenie
Sprawdzić faktyczną aktywację sekcji w promptach, ukończenia per gra, nowe zera, błędy, tokeny i regresje. Obiecujący wynik wymaga świeżej kontroli lub sparowanej replikacji. W NEXT-HYPOTHESIS.md są tropy z logów oraz jawna korekta: action zwraca dict, executed to bool, executed_actions to lista. Nie wyłączać zabezpieczeń stale-state w celu zmniejszenia liczby błędów.

## Własne eksperymenty
Nie nadpisywać oryginalnego sluga petersharps/arc3-duck-codex-v3-slim-1101 ani jego wersji 1. kernel-metadata.json zachowuje oryginalną konfigurację wyłącznie do odtworzenia; przed własnym push zmienić id i title na odrębny slug. Nie wysyłać do konkursu bez zgody użytkownika. Zachować ten pakiet jako kontrolę i ulepszenia zapisać obok, z nowym hashem, opisem zmiany i własnym pomiarem. Sam commit pakietu nie uruchamia sesji innych AI.

## Aktualne wyniki i surowe dane
Kolektor GitHub Actions: https://github.com/peteraangelic-pixel/Smak-Domu-Konkurs/actions/runs/41288053823
Notebook prywatny: https://www.kaggle.com/code/petersharps/arc3-duck-codex-v3-slim-1101
Nasza gałąź z aktualizowanym dziennikiem i surowymi wynikami: https://github.com/peteraangelic-pixel/Smak-Domu-Konkurs/tree/codex/arc-local-lab-v18-20261030/arc-agi-3/analysis
