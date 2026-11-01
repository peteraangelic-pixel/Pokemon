# Aktualne zlecenie: rozwijaj zmierzoną kontrolę v3

Na polecenie użytkownika: NIE poświęcać kolejnych testów na odrzucony v3-slim. Nie analizować go jako obiecującego kandydata. Zachowany raport służy tylko uniknięciu powtarzania eksperymentu.

## Dostarczona baza
arc3-duck.ipynb jest dokładnym odzyskanym v3. SHA256: 8d0195f92c5518a41d14edbfca596b72c27690f269f681bbaa9af0bc3d257bcc.
Potwierdzony zakończony test docelowego Flash-Next:33 ukończenia,27.49667,10/10 gier z co najmniej jednym ukończeniem,crashed=[],ARC3_SMOKE_OK. benchmark.json zawiera rzeczywiste przebiegi. Historyczna punktowana submisja tego kodu miała26.25;to inny pomiar. Nie ma gwarancji identycznego rerunu ani wyniku60+. Ta baza działa w pełnej pętli na modelu docelowym,ale nie rozwiązuje wszystkich poziomów.

## Zadanie badawcze z celem60+
Zaproponować i wdrożyć mechanizm dający NOWE ukończenia w wielu grach. Punktem wyjścia mają być nieukończone poziomy w benchmarku i rzeczywiste logi. Najpierw wskazać konkretny błąd/ograniczenie,które zmiana naprawia. Nie zastępować tego prognozą wyniku z liczby akcji,smoke infrastruktury lub symulacją kolejki.

Przydatne kierunki do rozdzielenia między sesjami: wykonywalny model świata z kontrolą trafności przed planowaniem; dobór eksperymentów rozróżniających hipotezy mechaniki; bezpieczne przenoszenie parserów i reguł między poziomami; zatrzymywanie powtarzanych nieskutecznych planów na podstawie obserwacji; przydział budżetu według mierzonego postępu. To hipotezy,nie gotowe przewagi. Wybierz kierunek pasujący do własnych wyników gałęzi i zweryfikuj aktywację.

Każda propozycja powinna dostarczyć kod,hash,krótki opis przyczyny i zmiany oraz pomiar przy identycznym modelu,rosterze i budżecie. Raportować ukończenia per gra,nowe zera,regresje i score. Obiecującą przewagę potwierdzić świeżą kontrolą. Nie kopiować do polityki gameID ani informacji z kodu silnika.

Nie nadpisywać sluga kontroli z kernel-metadata.json. Przed własnym prywatnym testem nadać unikalne id/title. Koordynować kosztowne próby z użytkownikiem;ten pakiet sam nie uruchamia żadnego testu ani sesji AI. Nie zgłaszać do konkursu bez osobnej zgody.

## Co już wiemy
slim:17.35047/24 — odrzucony;solved-level memory28.40/32 — odrzucona;recovery17.11/25 — odrzucone,hook recovery nie aktywował się. Nie scalać tych zmian w nadziei na sumę zysków.
Codex właśnie testuje osobno scope retained functions game→levelup na tej bazie,sekcje pamięci OFF. Nie dublować tej próby. Brak jej wyniku;nie jest nowym championem.

Pełne surowe logi kontroli i dalsze wyniki: https://github.com/peteraangelic-pixel/Smak-Domu-Konkurs/tree/codex/arc-local-lab-v18-20261030/arc-agi-3/analysis/v3-target-result-20261031/v3-output
Aktywny eksperyment: https://github.com/peteraangelic-pixel/Smak-Domu-Konkurs/tree/codex/arc-local-lab-v18-20261030/arc-agi-3/analysis/v3-levelscope-20261101
