# Transfer wiedzy z wcześniejszych prac

## Metoda: najcenniejsze

- Przyznane deklaracje, certyfikaty testów i wyniki z różnych gałęzi nie są dowodem; odtwarzaj na przypiętym kodzie i danych, zapisuj wersje, komendy, hash, warunki, surowe wyniki i ograniczenia. Najpierw testy bezpieczeństwa własnego narzędzia, potem minimalna walidacja hipotezy.
- Sprawdzaj faktyczny kod, kolejność inicjalizacji oraz stan środowiska; komentarz/probe uruchomiony przed stworzeniem prawdziwej listy gier mylił się co do badanego rosteru. Przekłada się to na filtrowanie dozwolonych hostów przed każdą operacją, łącznie z przekierowaniami.
- Oddzielaj korelację od przyczyny. Jedna różnica wyniku, pojedynczy seed, symulacja w cieniu i statystyka z innego korpusu nie identyfikują przyczyny. Porównuj sparowane warianty i kontrolę, raportuj negatywne wyniki i przypadki, których nie sprawdzono.
- Weryfikuj aktywację i połączenia rzeczywistego kodu. W jednym laboratorium wynik 40,06 był błędnie przypisany niepodłączonej warstwie; dodatkowo brakowało capa wyniku. Test, który przechodzi na izolowanej funkcji, nie dowodzi efektu w całej aplikacji.
- Minimalne uprawnienia, identyczna kontrola i powtarzalność: w security różnice testuj na własnych sztucznych danych/kontach; wynik podobny lub większy ruch nie oznacza znalezienia podatności. Niebezpieczne domysły kończą się na hipotezie, a nie raporcie.
- Systemy eksperckie z abstencją: pozytywny test jednej mechaniki nie gwarantuje generalizacji. ARC template wykonał 3 poziomy znanej gry, lecz sonda odkryła fałszywe dopasowania oraz cykl 60 działań bez zgłoszonej sprzeczności. Muszą istnieć limity, jawny stan i negatywne testy. Kontrola pojedynczego efektu nie dowodzi właściwego celu.
- Uważaj na przecieki stanu pomiędzy grami/sesjami, testy równoległości, reuse ścieżek, wylogowanie/reset i partial failure. Nigdy nie duplikuj działania po wyjątku, jeśli nie wiadomo, czy operacja już zaszła.
- Bezpieczna pamięć agenta: odróżniać dowód, hipotezę i jej odrzucenie; poprzednie v3-slim miało gorszy publiczny smoke (17,35/24 poziomy vs kontrola 27,50/33; pojedyncze przebiegi, nie wynik konkursowy). Nie traktować LLM jako autorytetu.
- Wartość bezpieczeństwa i stop conditions są ważniejsze od szybkości. Utrzymuj pełną izolację sandboxa, brak sekretów w kontenerach i zewnętrznych logach, minimalny dowód, ochronę danych i weryfikację przed zgłoszeniem.

## Algorytmy i technologie warte rozważenia

- Python: szybkie prototypowanie, czytelne testy i orkiestracja. Rust/Rayon: lokalne CPU-bound przetwarzanie, parsery, haszowanie, porównania zbiorów, agregacja. Mierz end-to-end, nie ekstrapoluj pomiaru kernela. Przykład: wcześniejsze ~33× dotyczyło tylko batchowego wykrywania prostokątów, nie całego agenta.
- FFI/multiprocessing: koszt przekazania danych i liczba workerów; unikać 16 procesów × 16 wątków. 5950X Zen 3 nie posiada AVX-512. Windows ma inne ścieżki i ABI; testować docelową platformę, nie zakładać WSL.
- Przetwarzanie wsadowe, deduplikacja po stabilnym identyfikatorze, hasze artefaktów i wersji, event logs oraz analiza różnic są użyteczne offline. Zachować prywatność, minimalizację i politykę retencji; nie trzymać nieujawnionych materiałów na publicznym GitHubie.
- Modelowanie hipotez: dobieranie następnego nieniszczącego testu, który rozróżnia kilka wyjaśnień, zamiast bezcelowego powtarzania prób. Wymagany zakres i zgodność regulaminowa; nie wykraczać poza własne dane.
- Hash-chain/replay i warunkowe wznowienie są pomocne w odtwarzalności, ale tylko jeśli operacje są bezpieczne i nie są powtarzane po niepewnym rezultacie. Żadnych niekontrolowanych działań na produkcji.

## Punkty odniesienia

- Audyty poprzednich gałęzi: `arc-agi-3/AUDYT-START-HERE-2026-10-31.md`, `arc-agi-3/RECENZJA-HIPOTEZY-CAP-2026-10-31.md` w tym workspace, o ile zachowane.
- Repo z wcześniejszymi wynikami Codexa: `peteraangelic-pixel/Smak-Domu-Konkurs`, `codex/arc-local-lab-v18-20261030` (wcześniej sprawdzany tip `0f95b205`). Wnioski w tym dokumencie są skrótem, nie równoważnym archiwum danych.
- Historyczne konkursowe wyniki ARC i Pokémon nie są prognozą powodzenia w bug bounty. Nowe narzędzia muszą zostać niezależnie zweryfikowane na bezpiecznych danych.
