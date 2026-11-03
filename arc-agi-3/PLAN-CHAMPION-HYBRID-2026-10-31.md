# Plan Champion Hybrid — 31 października 2026

## Cel i uczciwe ograniczenie

Zaprojektować kandydata o możliwie większej szansie niż v13.7 i v15, bez twierdzenia, że przekroczy 50. v13.7 ma zapisane 13,28, v3 historycznie 26,25; nie jest to kontrolowane porównanie. Przed przypisaniem jakiegokolwiek wyniku v15 trzeba wskazać dokładną wersję i zapis zgłoszenia; tutaj jego wynik nie zweryfikowano. Najnowszy znaleziony w repo zapis progu piątego miejsca 51,51 to historyczna migawka, nie aktualny ani końcowy próg.

## Pomysł: trzy warstwy, jeden niezmieniony mistrz

1. **Nienaruszony odzyskany champion v3** (historyczny notebook `champion-recovery-20261031/champion-v3/arc3-duck.ipynb`, SHA256 `8d0195f92c5518a41d14edbfca596b72c27690f269f681bbaa9af0bc3d257bcc`) jako kontrola i domyślny solver. Nie pakować warstw v13.7 ani v15, nie менять serving, temperatury, world modelu i budżetu. Zabezpieczyć weryfikację SHA i punktów instalacji.
2. **Obserwacyjny portfolio-router** z bezpieczną abstencją: początkowo tylko przetestowany template z ft09. Nowe kompetencje wtykane i mierzone osobno. Każda dostaje wyłącznie bieżące publiczne obserwacje, legalne akcje i historię aktualnej gry. Przed aktywacją musi sprawdzić kilka niezależnych warunków strukturalnych i spójność hipotezy; nie wybierać specjalisty po ID gry. Jeden ruch na raz, obserwacja po każdym ruchu; sprzeczność = wyłączenie specjalisty na poziom i natychmiastowy fallback. Nie zapewnia to braku szkody po pierwszym kliknięciu.
3. **Zwięzła pamięć operacyjna między poziomami**, jeżeli A/B potwierdzi korzyść: wzór mechaniki, sprawdzone reguły, wyniki błędów i sprawdzona sekwencja wyłącznie po rzeczywistych sukcesach. Sekwencji nie odtwarzać ślepo: warunki obserwacji i akcje muszą pasować, inaczej oddać sterowanie. Nie dodawać równocześnie do pierwszego eksperymentu template; sprawdzić kompatybilność z istniejącą pamięcią v3 i ryzyko przepełnienia kontekstu.

Kluczowa zaleta to nie łączenie dużej liczby niezmierzonych patchy, lecz wyprowadzanie testowalnych i rozłącznych zdolności przy zachowaniu działającego fallbacku. Stworzyć kolejną zdolność tylko po obejrzeniu wystarczającego korpusu; np. nav-plan w klawiaturowych planszach jest hipotezą, nie gotowym rozwiązaniem. Planer może bazować jedynie na obserwowanych lokalnych przejściach i wstrzymywać się, jeśli stan nie odróżnia ukrytych mechanik; niedozwolone jest zakładanie dostępu do silnika w submisji. Szukać korzyści na ukończeniach, nie na liczbie ruchów.

## Bariery inżynieryjne przed kwalifikacją template

- Po przekazaniu sterowania aktualne `template_hook` musi obsłużyć błąd ekstrakcji/rozpoznawania przez kontrolowany fallback; błędu, który może nastąpić po wykonaniu akcji, nie wolno obsługiwać przez ślepe powtórzenie akcji. Jawnie logować kategorie i liczbę rezygnacji, bez danych prywatnych silnika.
- Izolować kontroler na rzeczywisty lifecycle gry, nie wyłącznie ścieżkę pliku; testować współbieżność, reset, powtórne użycie ścieżki i przejście poziomu. Sprawdzić realny kod cyklu życia zanim wybierze się klucz. Nie dopuszczać przeniesienia learned między grami.
- Sprawdzić niejednoznaczne panele, permutacje, obce mechaniki, zmianę poziomu po akcji, brak/niedozwoloną akcję myszy, wyjątki, rozmiary ramek i funkcję fallbacku; testy jednostkowe nie zastępują symulacji.
- Uzgodnić metadane GPU (`enable_gpu=true` w kernel-metadata vs `isGpuEnabled=false` w notebooku); zweryfikować przez preflight przed ewentualnym użyciem.

## Kolejność prób i decyzji

A. Niezmodyfikowane v3 vs v3+sam template, pary: ta sama gra, seed, budżet, model, konfiguracja. Rejestrować hashe i surowe ślady; sprawdzić pierwsze oraz późniejsze obserwacje. Obejmować znane ft09, inne publiczne gry i odłożone gry/odmiany. Development cases nie liczą się jako ślepa walidacja.

B. Osobno v3 vs v3+jedna nowa zdolność, na innych mechanikach; najpierw dowieść autonomicznych ukończeń w realnym harnessie oraz niskiej liczby fałszywych uruchomień. Test 25 początkowych ramek nie wystarcza. Rust/Rayon jedynie dla zmierzonego wąskiego kernela, nie jako dowód ogólnej poprawy.

C. Osobno v3 vs v3+pamięć. Do łączenia dopiero po indywidualnych testach, potem ponownie paired A/B całej hybrydy, bo interakcje mogą odwrócić korzyści.

D. Wybór najlepszego: per gra/liczba poziomów, oficjalna punktacja, różnice w parach, regresje w grupach i przedziały niepewności; rejestrować błędy API, narzędzi i akcje oddzielnie. Punktację obliczać z rzeczywistych baseline'ów zgodnie z oficjalnym SDK. Nie uznawać pozytywnego jednego seeda ani zwycięstwa 3:0 na development ft09 za przewagę globalną. Docelowy Flash-Next jest wymagany do oceny transferu z lokalnego Qwena; jeśli go brak, wniosek pozostaje wstępny.

E. Oddzielne świadome GO użytkownika przed jakąkolwiek wysyłką na Kaggle. Bez GO brak triggerów czy uploadu.

## Czego nie robimy

Nie uzbrajamy 20k, nie promujemy v13.7 ani v15 wyłącznie na podstawie smoke; nie zakładamy, że wzrost a/call do 6 oznacza 50; nie wykorzystujemy wytrenowanej na jednej grze sekwencji jako dowodu generalizacji. Nie zwiększamy dużej macierzy Qwena po jej zerowych wynikach bez zmiany hipotezy lub pomiaru. Cel 50 pozostaje ambitny, nie gwarantowany.

## Status

To projekt eksperymentalny, a nie zaimplementowany i sprawdzony nowy notebook. Wykorzystuje istniejące dane: template lokalnie 3 poziomy na znanej ft09, zero kontrolnie; izolacja i bezpieczeństwo w szerszej hybrydzie pozostają do sprawdzenia. Plik jest w repo Pokemon, nie został przesłany do Smak-Domu-Konkurs.
