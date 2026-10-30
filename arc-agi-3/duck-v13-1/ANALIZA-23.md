# Dlaczego submisja dała tylko ~23? (analiza, 28.10)

Punkt odniesienia: best COMPLETE wcześniej = v3 **26,25**; smoke c45 na
10 grach publicznych = **26,78** (32 poziomy, przeliczone z surowego
`benchmark.json`). Wynik ~23 jest słaby, ale nie wymaga żadnej awarii —
wystarczą trzy znane mechanizmy, w kolejności prawdopodobieństwa:

## 1. Roster i rozcieńczenie tokenów (najsilniejszy kandydat)

Smoke to 10 gier × ~48 min każda. Pełny run musi zmieścić **cały roster**
w ~9 h przy 10 równoległych slotach generacji — czyli wielokrotnie mniej
tokenów i czasu na grę. RHAE jest wypukłe w głębokości (jeden poziom
więcej na grę wart jest nieproporcjonalnie dużo), więc cięcie budżetu
na grę o połowę kosztuje więcej niż połowę wyniku. Smoke 26,78 **nie
jest** estymatorem wyniku LB na pełnym rosterze — to pomiar innej,
łatwiejszej populacji przy innym budżecie.

## 2. Wysłany wariant prawdopodobnie nie był tym, za który się podawał

Jeżeli poszła v12-plan „jak leży", to w kodzie notebooka przypisanie to
`PLAN_COMMIT = "0"` (zmieniono tylko komentarze; zweryfikowane diffem
komórka-po-komórce z v11). Czyli zagrała **kontrola c45fix z capem 45k
włączonym**, a nie wariant plan. Oczekiwany wynik takiej konfiguracji:
~26,8 na populacji smoke, mniej na pełnym rosterze → ~23 jest spójne
bez żadnych dodatkowych hipotez.

## 3. Cap 45k sam w sobie kosztuje

Te same 10 gier, trzy buildy: v3 bez capa 29,02; r019 bez capa 27,21;
c45 z capem 45k **26,78** (najniższy). Cap strzela też do poziomów,
które właśnie miały zostać ukończone (su15: 56,4 → 13,3). Pomiar jest
między-buildowy (słaby), ale kierunek i mechanizm są zgodne.

## 4. Zero pamięci między wpisami benchmarku (KOREKTA 30.10)

Pierwotna wersja tego punktu mówiła o „20 passach" — to nieprawda dla
punktowanego biegu: komórka konfiguracyjna ustawia `bm.n_passes = 1`
przy `TRUE_SUBMISSION` (wykryły to niezależnie recenzje Gemma i c87;
potwierdzone w kodzie). Replay patcha 0006 działa więc przez: (a)
playbook offline, (b) powtórzone wpisy tej samej gry w rosterze
(magazyn kluczowany bazowym kodem gry, np. `ls20-9607627b` → `ls20`),
(c) powroty do ukończonego poziomu w obrębie wpisu, o ile wystąpią
(`ONLY_RESET_LEVELS=true` wymuszane przez taaf ogranicza ten kanał).
Wniosek o braku pamięci nadal prawdziwy — inny jest nośnik.

## 5. Wariancja

Średnia RHAE po grach ma dużą wariancję (pojedyncza gra potrafi ruszyć
średnią o kilka punktów). ±2–3 pkt między identycznymi runami to norma,
nie sygnał.

## Co by rozstrzygnęło diagnozę w 100%

Log z tego runu (Kaggle → kernel output). Trzy linie wystarczą:
`v13/v11 profile=... plan_commit=...` (który wariant naprawdę zagrał),
`ARC3 candidate-45: level_token_cap=...` (czy cap był włączony) oraz
metering (`v11_metrics.json`: liczba gier w rosterze i tokeny/gra —
to powie, jak silne było rozcieńczenie z pkt 1).
