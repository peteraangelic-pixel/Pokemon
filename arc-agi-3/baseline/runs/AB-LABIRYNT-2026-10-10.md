# Hipoteza: cd82 jest źle klasyfikowane jako labirynt — OBALONA

## Pytanie

cd82 utknęło na **5 stanach przez 400 akcji**, a tryb decyzji brzmiał
`tile-maze-navigation`. Hipoteza: `tile_maze_view()` bierze za labirynt planszę,
która nim nie jest (na nagraniu widać duże jednorodne pola i trójkąt), przez co
zły moduł prowadzi grę i wpada w cykl.

Dodano `tile_fill_permille` — część niejednorodnych kafelków 5×5 na planszy
— oraz strojony próg `ARC3_MAZE_MIN_FILL`.

## Wynik (20 gier, 400 akcji każda)

| gra | poziomy | tile_fill | tryb |
|---|---|---|---|
| ls20 | **2** | **111** | tile-maze-navigation |
| cd82 | 0 | **180** | tile-maze-navigation |
| m0r0 | 0 | **611** | tile-maze-navigation |
| ka59 | 0 | 138 | graph-click-frontier |
| sp80 | 0 | 173 | graph-click-frontier |
| sk48 | 0 | 354 | graph-click-frontier |
| dc22 | 0 | 395 | graph-click-frontier |
| g50t | 0 | 465 | graph-simple-frontier |
| tr87 | 0 | 611 | graph-simple-frontier |

## Wniosek

**cd82 JEST bardziej labiryntem niż ls20** (180 vs 111). Zaostrzenie progu
odrzuciłoby najpierw ls20 — jedyną grę, która zdobywa 2 poziomy. Hipoteza
„zła klasyfikacja planszy" jest więc **obalona**: cd82 ma poprawny moduł,
problem leży głębiej w nawigacji.

Warto zauważyć, że sześć gier ma `tile_fill` 138–611, a i tak gra w trybie
`graph-click-frontier` lub `graph-simple-frontier` — bo nie mają akcji
kierunkowych, więc `tile_maze_view` zwraca `None` niezależnie od wyglądu.

## Co zostaje

- `tile_fill_permille` w diagnostyce — przydatne, zostaje.
- `ARC3_MAZE_MIN_FILL` domyślnie **0** (bez zmiany zachowania). Nie ma
  wartości progowej, która poprawiłaby wynik.
