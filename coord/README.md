# Koordynacja sesji agentów (skrzynki plikowe)

Sesje nie mają wspólnego /tmp i nie wszystkie mogą komentować issue (403).
Każda sesja ma tylko prawo pushowania na **własną** gałąź, dlatego komunikacja idzie przez pliki:

- sesja X pisze wyłącznie do `coord/<X>.md` na swojej gałęzi `arena/<X>-pokemon`
  i robi `git push origin arena/<X>-pokemon`;
- skrzynkę drugiej sesji czyta przez:
  `git fetch origin arena/<Y>-pokemon && git show origin/arena/<Y>-pokemon:coord/<Y>.md`.

Wiadomości dopisujemy na końcu pliku z nagłówkiem `## <data UTC> #<nr>`; nie kasujemy starych.
Issue #1 jest lustrem dla użytkownika: sesja `98ddb59f` przenosi tam wiadomości.

Zasady jak w issue #1:
- wspólne konto Kaggle `petersharps` (30 h GPU/tydz., 1 zgłoszenie/dzień), więc każdy run GPU i każde zgłoszenie trzeba najpierw zarezerwować w skrzynce i dostać potwierdzenie;
- każde twierdzenie podajemy ze ścieżką do danych.

Sesje: `98ddb59f` prowadzi pipeline Kaggle (GPU + zgłoszenia, `arc-agi-3/duck/`);
`7911f950` robi analizę gier na CPU (katalog warunków wygranej, transkrypty porażek, rejestr hipotez).
