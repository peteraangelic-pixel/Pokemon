# CERT — moje.cert.pl: publiczna mapa funkcji

Data: 3.11.2026. Uwzględniono program CERT jako jeden z czterech programów wskazanych przez użytkownika; bez Władysławowa. Nie znaleziono luki ani nie utworzono kont. Dane poniżej pochodzą z publicznych stron i publicznej, zewnętrznej kolekcji API; nie są dowodem obecnej implementacji ani zgłoszeniem.

## Co sprawdzono

- Jednorazowo odczytano publiczne strony [rejestracji](https://moje.cert.pl/accounts/signup/), [regulaminu](https://moje.cert.pl/terms/) i [poradnika zespołów](https://moje.cert.pl/guides/users-in-organization/) — pojedyncze, zwykłe pobrania stron, bez wysłania formularzy i bez użycia kont. Wcześniejszy URL instrukcji incydentów z indeksu wyszukiwarki aktualnie zwrócił 404; indeks nie musi być aktualny.
- Poradnik opisuje pełny dostęp, domyślny dostęp tylko do odczytu, zaproszenia do organizacji oraz możliwość nadawania uprawnień. Dokumentuje oczekiwane zachowanie, a nie stwierdza, że jest wadliwe.
- [Regulamin serwisu](https://moje.cert.pl/terms/) wskazuje, że dostęp do informacji o wyciekach jest dla administratorów domen i tylko w zakresie ich własnych domen, zaś niektóre funkcje wymagają dodatkowej akceptacji. Nie należy wykonywać prób na cudzych domenach, sieciach, organizacjach ani wyciekach.
- Publiczna, nieoficjalna [kolekcja API](https://github.com/Ysiakowy/moje.cert.pl-API) w commicie `04af130a8422dd748e52e61160f3b249affdea67` zawiera 15 zapisanych operacji: 9 GET, 2 POST, 1 PATCH, 1 PUT, 2 DELETE. Grupuje je wokół kontekstu użytkownika, organizacji oraz domen. Jej autor nie jest organizatorem; kolekcja pochodzi z 2025 r. i może być nieaktualna. Przeanalizowano strukturę lokalnie; nie wykonano żadnej operacji API ani nie kopiowano kolekcji do repo.

## Istotna niejednoznaczność zasad

Program [CERT Bug Bounty](https://hack.cert.pl/programs/cert-polska/bug-bounty-cert-polska/editions/1) obejmuje `moje.cert.pl` i dopuszcza testy z własnymi lub testowymi kontami. Jednocześnie regulamin samej usługi `moje.cert.pl`, część IV pkt 4.2, nakazuje powstrzymać się od działań mających na celu testowanie możliwości przełamania lub ominięcia zabezpieczeń. Dokumenty dotyczą różnych kontekstów, ale nie rozstrzygnięto ich wzajemnej relacji ani zakresu zgody konkursowej. **Poprosić organizatora o pisemne wyjaśnienie przed aktywnymi próbami uwierzytelnionymi lub badaniem obchodzenia zabezpieczeń.** Nie zakładać, że sam formularz rejestracji jest zgodą na dowolne operacje.

## Hipoteza badawcza, nie ustalenie

Po wyjaśnieniu zasad: czy operacje na organizacji i zasobach przestrzegają przypisania ról i własności także po zmianie uprawnień? Testować wyłącznie własne konta i nieszkodliwe własne zasoby, nie korzystać z usług wykrywania wycieków innych osób, nie skanować cudzej infrastruktury i nie wykonywać masowych operacji. Publiczny poradnik dostarcza oczekiwań dla ról; kolekcja jest tylko wskazówką do sposobu działania, nie gwarancją aktualnego API.

Porównanie statusów samo nie dowodzi podatności: 200 dla użytkownika z dostępem do udostępnionego mu zasobu może być poprawne, a odpowiedź odmowna nie dowodzi bezpieczeństwa systemu. Znalezisko wymagałoby ograniczonego, zgodnego z regulaminem i odtwarzalnego dowodu realnego wpływu oraz prywatnego zgłoszenia.

W pobliskich równoległych pracach [repo NASK](https://github.com/peteraangelic-pixel/NASK/tree/codex/multi-program-lab-20261103) raportuje przebieg z częściowym pokryciem i zero kandydatów/potwierdzonych luk. Jest to relacja autora; surowych prywatnych dowodów nie analizowano. Nie ingerowano w żadne sesje ani workflowy.
