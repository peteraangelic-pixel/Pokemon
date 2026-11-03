# Wstępna mapa publiczna — NASK, CERT, Gov.pl, mSzyfr

Data: 2026-11-03. Zakres użytkownika: bez Władysławowa. W tym etapie użyto wyłącznie wyników wyszukiwarki i dostępnych publicznie opisów. Wpisy nie są wynikami testów bezpieczeństwa ani potwierdzonymi podatnościami. Indeks może być nieaktualny. Nie utworzono kont ani nie wysłano formularzy.

| Priorytet | Powierzchnia | Publiczna obserwacja | Dalszy krok / ograniczenie |
|---|---|---|---|
| CERT | [moje.cert.pl](https://moje.cert.pl/) | Indeks pokazuje [rejestrację](https://moje.cert.pl/accounts/signup/) oraz konta i uprawnienia organizacji. | Potencjalnie użyteczny scenariusz kontroli dostępu, ale test tylko na własnych kontach i własnych zasobach; sprawdzić zasady usługi i faktyczną dostępność. Żadnych cudzych wycieków, kont ani domen. |
| CERT | [incydent.cert.pl](https://incydent.cert.pl/) | Publiczna [instrukcja](https://incydent.cert.pl/instrukcje-email/gmail) opisuje zgłoszenie i załączniki. | Mapa funkcji, nie dowód luki; nie wysyłać fikcyjnych zgłoszeń ani załączników do systemu obsługi incydentów. |
| NASK | [oad.nask.pl](https://oad.nask.pl/) | Indeks opisuje publiczny serwis Ośrodka Analizy Dezinformacji. | Sprawdzić wyłącznie funkcje i jawne linki w zakresie; treść strony nie wskazuje luki. |
| NASK | `dns.pl` | Wyniki wyszukiwarki wskazują też `www.dns.pl`, `panel.dns.pl` i `partner.dns.pl`. | Nie testować wymienionych subdomen tylko dlatego, że istnieją: regulamin NASK wymienia `dns.pl`, zakres poddomen wymaga osobnego potwierdzenia. Żadnych prób kont rejestratorów. |
| Gov.pl | [www.gov.pl](https://www.gov.pl/) | Indeks prowadzi także do usług pod innymi domenami państwowymi. | W tym programie wymieniono `www.gov.pl`; nie śledzić automatycznie linków do innych hostów. |
| mSzyfr | [mas.komunikator.narodowy.gov.pl](https://mas.komunikator.narodowy.gov.pl/) | Wynik indeksu opisuje usługę uwierzytelniania Matrix i dokument discovery. Nazwa hosta pasuje do wildcard domeny wskazanej w programie. | Kandydat do ręcznej weryfikacji zakresu i aktualności, nie podatność. Brak dowodu dostępności kont badawczych; przed testami sprawdzić bieżący regulamin i warunki dostępu. Nie korzystać z cudzych kont ani tokenów. |

## Ograniczenia i tempo

Każdy z rozpatrywanych czterech programów dopuszcza automaty do 5 req/s. Ponieważ sposób sumowania limitu między celami nie jest jednoznaczny, bezpieczna polityka robocza to pojedynczy skoordynowany proces i 1 req/s łącznie, bez niezależnych równoległych kampanii. Nie robić testów obciążeniowych, spamu, przejmowania infrastruktury, ani kopiowania czy przetwarzania cudzych danych osobowych lub poufnych. Natychmiast przerwać w przypadku przypadkowego dostępu do takich danych lub oznak zakłóceń. Nie zgłaszać różnicy czy heurystyki jako luki bez nieniszczącego dowodu realnego wpływu.

Środowisko sesji ma ograniczone wyjście do sieci, a wcześniejszy kolektor wymaga poprawek wskazanych w `POSTEP-I-AUDYT-2026-11-03.md`. Nie wykonano nowej kampanii, nie wykryto ani nie zgłoszono podatności. Nie konfigurowano samoczynnego zadania nocnego.
