# Katalog warunków wygranej: ARC-AGI-3, 15 gier treningowych

Stan na 2026-10-14. Źródło: kod gier (`environment_files`, pobrany przez gałąź `arena/7911f950`).
Każdy warunek wygranej sprawdziłem w kodzie (funkcja wywołująca `next_level()` / `win()`).
Klatki startowe wyrenderowałem lokalnie przez `play.py`.

## Zasada hold-out

Katalog powstał **tylko z 15 gier**: ar25, bp35, cd82, ft09, lf52, lp85, r11l, re86, sb26, sk48, sp80, tr87, tu93, vc33, wa30.

10 gier testowych (cn04, dc22, g50t, ka59, ls20, m0r0, s5i5, sc25, su15, tn36) **nie jest tu opisanych**.
Na nich mierzymy, więc ich zawartość nie może trafić do promptu.
Prywatne gry konkursowe mają nowe mechaniki. Dlatego katalog opisuje *klasy* celów i *obserwowalne sygnały*, a nie przepisy na konkretne gry.

## Gry (warunek wygranej zweryfikowany w kodzie)

| Gra | Akcje | Klasa | Warunek wygranej (kod) | Co widać na ekranie |
|---|---|---|---|---|
| ar25 | klaw.+klik | POKRYJ | każdy znacznik celu pokryty przez element **lub jego odbicie** w osiach-lustrach (odbicia wielokrotne) | kształty L, jasna pionowa linia (lustro), białe kropki-cele |
| bp35 | klik+3,4,7 | DOTRZYJ | awatar spadający grawitacyjnie **ląduje na klejnocie**; lądowanie na kolcach = przegrana | przewijany pionowo poziom, bloki do usuwania |
| cd82 | 1–6 | KOPIUJ | płótno == miniatura wzoru (piksele 10×10 bez przekątnych) | miniatura w lewym górnym rogu, płótno pośrodku |
| ft09 | klik | OGRANICZENIA LOKALNE | każdy kafel-klucz 3×3 mówi, które sąsiednie pola mają mieć **ten sam / inny** kolor niż jego środek; klik zmienia kolor pola cyklicznie | siatki 3×3 kolorowych pól z kaflem-kluczem w środku |
| lf52 | 1–4,6,7 | ZREDUKUJ | zostaje **dokładnie 1** pionek (ruch = przeskok o 2 pola, jak w samotniku) | plansza z zielonymi pionkami |
| lp85 | klik | UMIEŚĆ | każdy oznaczony element stoi na swoim znaczniku `goal` / `goal-o`; klik obraca pierścienie kafli | pierścień kolorowych kafli, strzałki po bokach |
| r11l | klik | DOTRZYJ | ciało (między dwoma uchwytami) **dotyka** swojego celu (kropkowany kontur); kolizje ze ścianami karane | dwa krzyżyki-uchwyty, fioletowe ciało, kropkowany romb |
| re86 | 1–5 | POKRYJ | każdy znacznik celu przykryty pikselem **tego samego koloru** z ruchomych krzyży | żółty i niebieski krzyż, małe kwadraciki w tych kolorach |
| sb26 | 5,6,7 | KOPIUJ (sekwencja) | sloty wypełnione w kolejności wzorcowej; sprawdzenie dopiero po **akcji zatwierdzenia** (5); błędy zabierają życia | rząd wzorcowy u góry, sloty pośrodku, paleta na dole |
| sk48 | 1–4,6,7 | KOPIUJ (sekwencja) | kolejność wagonów zebranych przez „węża" == sekwencja wzorcowa; **dopasowane pozycje zapalają wskaźnik** | wąż z różową głową, kolorowe bloki, wzorzec na dole |
| sp80 | 1–6 | PRZEPŁYW | po wypuszczeniu (akcja 5) strumień wypełnia **wszystkie** naczynia bez rozlania; liczba prób ograniczona | dozownik u góry, belki-odbijacze, naczynia u dole |
| tr87 | 1–4 | KOPIUJ (reguły) | dolny rząd == tłumaczenie górnego rzędu według pokazanych par reguł A→B; dalsze poziomy: tłumaczenie drzewiaste | pary symboli niebieski→różowy u góry |
| tu93 | 1–4 | DOTRZYJ (wszyscy) | **wszystkie** awatary jednocześnie stoją na wyjściach (ruch synchroniczny) | labirynt, niebieski start, zielone wyjście |
| vc33 | klik | WYRÓWNAJ | każdy znacznik koloru c jest na tej samej wysokości co cel koloru c i połączony tym samym segmentem (pewność średnia) | szare poziomy/ściany, kolorowe znaczniki na krawędzi |
| wa30 | 1–5 | UMIEŚĆ | wszystkie skrzynki w strefie celu **i puszczone** (nie trzymane) | gracz, niebieskie skrzynki, obrysowana strefa |

## Ustalenia przekrojowe (ważniejsze niż sama lista)

1. **Licznik, który maleje co akcję, to zawsze limit kroków lub żyć.**
   Jego wyzerowanie oznacza przegraną, nigdy wygraną (`self.lose()` w cd82, r11l, re86, tu93, vc33, wa30, ls20, cn04…).
   Rejestr drugiej gałęzi ma tu błąd („Timer: wygrana, gdy czas się skończy").
2. **Warunek wygranej to zawsze „wszystkie".** Wszystkie cele pokryte, wszystkie awatary na wyjściach, wszystkie naczynia pełne.
   Częściowy postęp zwykle nie daje sygnału. Wyjątkiem są wskaźniki dopasowania, np. w sk48.
3. **6/15 gier pokazuje wzorzec do skopiowania lub przetłumaczenia** (cd82, sb26, sk48, tr87, ft09 w formie kluczy).
   Obszar, na który żadna akcja nie wpływa, a który wygląda jak coś, co da się zmienić, to prawie na pewno wzorzec.
4. **Kontury, kropkowane obrysy i małe znaczniki w kolorze ruchomego obiektu to cele** (ar25, r11l, re86, lp85, wa30).
5. **Akcja zatwierdzenia:** w sb26 i sp80 wynik sprawdza się dopiero po akcji 5, a prób jest mało.
   Najpierw trzeba ustawić konfigurację, dopiero potem zatwierdzać. Nie wolno klikać 5 „na próbę".
6. **Jedna gra = jedna funkcja wygranej dla wszystkich poziomów.** Kolejne poziomy dokładają mechaniki, ale klasa celu się nie zmienia (tr87: wariant drzewiasty tej samej reguły).
   Po pierwszym rozwiązanym poziomie cel jest więc w zasadzie znany i trzeba go zapisać w notatkach.

## Ile punktów może dać katalog? (dane Franzena, 4×25 przebiegów, `loss_split.py`)

| | |
|---|---|
| przebiegi z 0 rozwiązanych poziomów | 7 / 100 (sk48 4×, g50t, m0r0, sc25) |
| strata: nierozwiązany poziom 1 | **7,0 pkt/grę** |
| strata: utknięcie po ≥1 rozwiązanym poziomie | **43,9 pkt/grę** |
| tokeny na poziom 1 (mediana) | 15k, średnio 14% budżetu |
| tokeny spalone na ostatnim, nierozwiązanym poziomie | 34% budżetu |

**Wniosek:** samo rozpoznanie celu może odzyskać najwyżej ok. 7 pkt na demo, plus trochę tokenów zaoszczędzonych na poziomie 1. To nie jest mnożnik 1,5×.
86% straty powstaje *po* tym, jak agent już rozwiązał co najmniej jeden poziom tej gry, czyli zwykle zna cel.
Następny krok to klasyfikacja tych utknięć: (a) nowa mechanika niezrozumiana, (b) zły cel mimo rozwiązanego poziomu 1, (c) dobry model, ale nie znalazł rozwiązania, (d) pętla.
Udział (c) rozstrzyga, czy szybkie przeszukiwanie (Rust + rayon) ma sens.

## Narzędzia

- `play.py`: uruchamia grę lokalnie na CPU, bez API, i renderuje klatkę do PNG.
  arcengine z PyPI wymaga Pythona 3.12, ale działa na 3.11:
  `pip install --no-deps --ignore-requires-python arcengine && pip install pydantic numpy pillow`.
- `loss_split.py`: podział straty punktów i tokenów według poziomów, z `benchmark.json`.

- `replay.py`: odtwarza historie akcji z `benchmark.json` na lokalnych grach. **Zgodność: 100/100 przebiegów Franzena daje dokładnie ten sam `levels_completed`.**

Możliwość lokalnego uruchamiania gier pozwala **odtworzyć historie akcji z `benchmark.json`** (każdy przebieg zapisuje akcje) i dokładnie zobaczyć stan, w którym agent utknął.
To metoda do klasyfikacji (a)–(d) bez GPU.
