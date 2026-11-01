# Audyt projektu baterii — 1 listopada 2026

**Ocena:** projekt zawiera sensowne kierunki materiałowe i działający symulator, ale nie dowód opracowania baterii przewyższającej rynek. Najbardziej obiecujący do eksperymentu jest kierunek NMC + anoda zawierająca krzem. Najbardziej efektowne wyniki DRX i anode-free są silnie zależne od uproszczeń modelu. Nie ma obecnie podstaw, aby obiecać jednocześnie wyższą energię, niższy koszt, wysokie bezpieczeństwo i łatwe wdrożenie.

## Zakres i dowody

Sprawdzono trzy lokalne wersje: `battery-sim`, `battery-sim2` oraz `Pokemon-arena-d1882c0f-pokemon/battery-sim`. Wspólne pliki `cell.rs`, `sim.rs`, `sweep.rs` są identyczne we wszystkich trzech. Pozostałe moduły i dokumenty różnią się wersjami. Wszystkie 26 plików z drzewa `battery-sim` pobranego przez konektor GitHub dla wskazanej gałęzi odpowiada plikom w ostatnim katalogu — porównanie Git blob SHA-1, nie tylko nazw. W audycie nie zmieniano modelu ani oryginalnych wyników.

Zbudowano aktualny lokalny kod: `cargo build --release --no-default-features`. Wykonano sześć przypadków, przeliczono zestawienia CSV i osobny eksperyment wrażliwości korzystający bezpośrednio z oryginalnych modułów Rust. Pliki dowodowe: `evidence.json`, `runtime.txt`, sześć `*-trace.csv`, `sensitivity.rs`, `sensitivity.txt`. `reproduce.py` odtwarza analizę CSV i sześć przebiegów po uprzednim zbudowaniu programu.

## 1. Co rzeczywiście odtworzono

| Konfiguracja | Warunki | Nominalne Wh/kg modelu | Cykle | Oddana pojemność w pierwszym cyklu | 80% SOC osiągnięte? |
|---|---|---:|---:|---:|---|
| NMC811/Si-C/GEL, L30, N/P1,10 | 25°C, ładowanie 2C | 278,8 | 670 | 81% | tak |
| DRX/Si-C/GEL, L40, N/P1,02 | −10°C, 2C | 361,0 | 641 | 32% | nie |
| identyczny DRX | 25°C, 2C | 361,0 | 443 | 67% | nie |
| LFP/LIFREE/LP57, L35, N/P1,02 | 25°C, 2C | 270,2 | 512 | 97% | tak |
| NMC811/LIFREE/GEL, L35, N/P1,02 | −10°C, 2C | 358,7 | 542 | 32% | nie |
| NMC811/grafit/LP57, L20, N/P1,10 | 25°C, 2C | 236,9 | 735 | 92% | tak |

Wszystkie rozładowania w tej tabeli: 1C. Nominalne Wh/kg są bilansem OCV/masy, a nie pomiarem energii oddanej podczas danego przebiegu. Nie można przemnożyć bezrefleksyjnie Wh/kg przez udział pojemności: napięcie i straty również się zmieniają.

Zliczenia plików:

- `grid.csv`: 14 640 wierszy, 321 PASS, w tym **159 z nieosiągniętym 80% SOC**.
- `optim_winners.csv`: 2880 wierszy, 420 PASS, w tym **234 z nieosiągniętym 80% SOC**.
- `mega.csv`: 99 840 wierszy, 5788 PASS; najlepsze C to 1C dla 4410, 2C dla 1253 i 3C dla 125. **2402 PASS nie osiągają 80% SOC**. Liczby dotyczą wybranego najlepszego tempa, nie wszystkich temp, które mogły przekroczyć 500 cykli.
- `marathon.csv`: 312 wierszy danych, 13 PASS; przed nagłówkiem CSV jest 94 wierszy tekstu konsoli.

Liczba kombinacji jest poprawna. Nie zastępuje ona liczby niezależnych doświadczeń ani walidacji predykcyjnej.

## 2. Krytyczny problem testu bezpieczeństwa

`cell.rs:228` ustawia shutdown przy 130°C dla wszystkich elektrolitów poza SOLID. `sim.rs:315` zeruje wtedy prąd. Test rozpoczyna się od temperatury pieca 150°C oraz SOC=0 (`sim.rs:468`). Prąd od początku wynosi więc zero, a ogniwo pozostaje na SOC=0. Pozostające w modelu reakcje cieplne nie są przy tym konsekwentnie zależne od SOC.

Bezpośredni test NMC811/Si-C/GEL dał **identyczne Tmax=154,890253803132°C** dla zadanego przeładowania **0C, 1C i 10C**. To rozstrzyga, że test nie bada tego, co opisuje dokumentacja. Wynik „survives” nie uzasadnia twierdzenia o odporności na przeładowanie.

Pozostałe ograniczenia: progi „wybuchu” i runaway są regułami modelu, nie modelem gazowania/ciśnienia/odpowietrzania; wspólny próg 200°C nie dowodzi samopodtrzymującej reakcji. Oddawanie ciepła przez obie powierzchnie każdej warstwy elektrody nie odwzorowuje automatycznie wnętrza wielowarstwowego ogniwa. Ceramiczny separator i wyższy próg zwarcia pojawiają się jako własność kategorii GEL, bez osobnego bilansu konstrukcyjnego.

**Wniosek:** dla wszystkich sześciu kandydatów status bezpieczeństwa fizycznego brzmi „niezweryfikowane”. Stabilność katody LFP nie przenosi się automatycznie na bezpieczeństwo całego ogniwa z osadzającym się metalicznym litem.

## 3. Cykl, szybkie ładowanie i użyteczna energia

`sweep.rs:104–111` nie wymaga osiągnięcia 80% SOC. W `sim.rs:73` wystarcza oddawanie 30% pojemności, żeby nie zakończyć próby jako rate-limited. Daje to możliwość zdobycia PASS przy częściowych cyklach. Zerowe t80 w CSV oznacza brak osiągnięcia celu, nie błyskawiczne ładowanie.

DRX z tabeli wykonał 641 częściowych cykli, odpowiadających około **205 ekwiwalentom pełnego rozładowania** względem początkowej pojemności. To obliczenie z zapisanego trace, nie korekta prognozy trwałości. Co więcej, `sim.rs:483` resetuje SOC do zera przed każdym ładowaniem, nawet jeżeli poprzednie rozładowanie zakończyło się powyżej zera. Tym samym stan nie jest ciągły między cyklami. Największy problem dotyczy właśnie zimnych, silnie spolaryzowanych konfiguracji.

Prąd wynosi `C × aktualna pojemność` (`sim.rs:485`), więc maleje wraz ze starzeniem. Trzeba to ujawnić przy porównaniu z protokołem utrzymującym stały prąd odniesiony do początkowego Ah. Model nie ma pełnego etapu CV. Sam wynik „2C” nie jest porównywalny z dowolną kartą katalogową.

**Naprawa:** zachować SOC między cyklami, całkować rzeczywiście oddaną energię, raportować Wh/kg przy zadanym protokole, przepływ Ah/Wh i EFC, rozróżniać CC/CC-CV oraz stały prąd/stałe C względem aktualnej pojemności. Kryterium szybkiego ładowania powinno zawierać np. rzeczywisty czas 10–80% oraz wymaganą pojemność użytkową, nie sam zadany prąd.

## 4. Anode-free: wynik silnie zadany parametrami

LIFREE otrzymuje fikcyjną pojemność materiałową 38 600 mAh/g, czyli 10 razy większą niż lit, aby przy zwykłym wzorze N/P reprezentować bardzo małą masę anody. **To zabieg numeryczny, a nie nowy materiał.** W prawdziwym anode-free trzeba osobno opisać brak początkowego materiału anodowego oraz masę i objętość litu przenoszonego z katody podczas ładowania. Lit pochodzi z katody: nie należy dodawać jego masy po raz drugi, ale nie wolno pomijać jego objętości i chemii powierzchniowej.

LIFREE ma `k_an=0`, `plat=0`, a dodatkowe zdarzenie cieplne dla litu w `check_safety` dotyczy nazwy LIMETAL. Nie jest więc wiernie modelowana reaktywność warstwy litu, która powstaje na kolektorze w ogniwie anode-free. Zakładane `dead_li=0,0002` ustala dużą część trwałości.

Eksperyment wrażliwości LFP/LIFREE/LP57, 25°C, 2C, bez innych zmian:

| Założone dead_li | Cykle modelu |
|---:|---:|
| 0,0002 | 512 |
| 0,001 | 126 |
| 0,003 | 44 |

To scenariusze niepewności parametru, nie trzy pomiary materiałów. W prostym bilansie bez rezerwy litu zachowanie 80% po 500 cyklach wymaga średniej efektywności zachowania litu ok. `0,8^(1/500)=99,9554%`, zanim doliczymy inne przyczyny utraty pojemności. Dla 1000 cykli jest to ok. 99,9777%. Rzeczywisty model musi wiązać utratę z przepływem ładunku, morfologią i elektrolitem.

Kierunek anode-free ma podstawy naukowe: [Columbia/Joule, 2026](https://www.engineering.columbia.edu/about/news/new-electrolyte-points-stronger-safer-batteries) opisuje określony żel i wielowarstwowe pouch cells o poprawionej trwałości i odporności na uszkodzenie. To potwierdza sens kierunku, ale nie parametry generycznego GEL z Waszej bazy ani niski koszt produkcji Waszego projektu.

## 5. Krzem, DRX, elektrolity i koszty

**Krzem:** expansion jest tylko przechowywane i wypisywane. Zmiana z 0% przez 60% do 300% nie zmienia 670 cykli ani 993,7 Wh/L głównego kandydata. Brakuje m.in. utraty kontaktu, pękania, zmian porowatości oraz straty litu podczas formacji. Żywotność anody nie wynika z mechaniki, lecz z kilku wpisanych współczynników. [Badanie pełnych ogniw Si/grafit](https://www.nature.com/articles/s41467-021-22662-7) pokazuje znaczenie bilansu litu i sprzężenia elektrochemii z mechaniką.

**SEI:** cykliczny model sumuje `sqrt(czas pojedynczego cyklu)` (`sim.rs:568`), co przy równych cyklach daje wzrost liniowy z liczbą cykli, a nie deklarowane sqrt(czasu całkowitego). Wersja storage używa różnicy pierwiastków; te dwa modele nie są spójnie połączone.

**DRX:** nazwa rodziny nie określa składu ani receptury syntezy. Wpis 250 mAh/g, prosta krzywa o wysokim napięciu i 95% aktywnego materiału nie dowodzą, że wszystkie te parametry można uzyskać razem w grubej elektrodzie przy 2C. Nie ma osobnych krzywych ładowania/rozładowania, histerezy i utraty napięcia. [Eksperyment Nature Communications 2025](https://www.nature.com/articles/s41467-025-60946-4) pokazuje zarówno postęp, jak i zależność wyników od syntezy oraz zanikanie napięcia. Nie oznacza to, że każdy DRX jest słaby; oznacza, że jeden generyczny zestaw parametrów jest niewystarczający.

**Elektrolity:** LP57, GEL i SOLID dają przy tej samej parze elektrod identyczną masę, grubość, Wh/kg i Wh/L. W audycie głównego kandydata wszystkie trzy miały masę 71,199849 mg/cm² i grubość 0,019975 cm. Brakuje odrębnej gęstości, objętości, udziału polimeru/ceramiki oraz konstrukcji stałego separatora i kompozytu katodowego. Nie ma też mapy zgodności soli, rozpuszczalników i elektrod. [LP57 jest elektrolitem LiPF6](https://pmc.ncbi.nlm.nih.gov/articles/PMC7493211/), więc dosłowny przepis „Na-PW/HC/LP57” nie jest kompletną recepturą ogniwa sodowego. Gdyby etykieta oznaczała analog sodowy, trzeba jawnie podać inny skład i parametry. NA_NFPP dodatkowo opisano w README wzorem NVP, czyli Na3V2(PO4)3; NFPP to Na4Fe3(PO4)2P2O7 — różne materiały i koszty.

**Bilans masy:** loading opisano jako masę powłoki; pojemność mnożona jest przez act, ale masę powłoki ponownie dzieli się przez act. Trzeba przyjąć jedną konwencję: masa aktywna albo masa całej powłoki. Nie jest to powód do uznania wszystkich wartości za zawyżone — kierunek części poprawek może być przeciwny.

**Koszty:** 27/41/67 USD/kWh to założony koszt części materiałów podzielony przez nominalną energię. Nie uwzględnia pełnego BOM, produkcji, formacji, braków, uzysku, kontroli, oprzyrządowania i kapitału. Koszty DRX, specjalnych elektrolitów i Si-C nie są poparte ofertami dostawców dla określonych gatunków i skali. Użycie masy całej powłoki z ceną materiału aktywnego dodatkowo miesza podstawy kosztowe. Nie można porównywać tych liczb bezpośrednio z ceną gotowego ogniwa. Do dalszego etapu nadaje się np. [BatPaC Argonne](https://publications.anl.gov/anlpubs/2019/03/150624.pdf), uzupełniony własnymi ofertami i realistycznym uzyskiem.

## 6. Ocena portfolio i rynku

| Kandydat | Moja ocena dalszego kierunku |
|---|---|
| NMC811 + Si-C + GEL | Najlepszy punkt wyjścia do eksperymentu; rodzina sensowna, konkretne parametry niepotwierdzone. Wyższy udział Si i żel dodają ryzyka procesu. |
| NMC811 + anode-free | Uzasadnione badania długoterminowe, słabe podstawy tezy o łatwym/tanim uruchomieniu. |
| LFP/LMFP + anode-free | Niska cena katody nie rozwiązuje utraty litu i bezpieczeństwa anody. Nie traktowałbym jako najtańszego produktu startowego. |
| DRX + Si-C | Dwa trudne układy materiałowe jednocześnie. Interesujące dla laboratorium, zbyt spekulacyjne dla pierwszego wdrożenia. |
| LFP + anode-free + SOLID | Trzy obszary do walidacji; model nie dowodzi 20 lat życia ani odporności kompletnego produktu na 60°C. |
| Na-PW + HC | Warto badać dla konkretnego zastosowania kosztowego; najpierw prawidłowy elektrolit, bilans sodu i realny benchmark. |

NMC811 zawiera kobalt: LiNi0,8Mn0,1Co0,1O2. Stary `battery-sim/pitch.md` nazywający głównego kandydata cobalt-free jest błędny. Portfolio mówi, że modelowe 201 Wh/kg pakietu pokonuje 255–260 Wh/kg pakietów porównawczych — arytmetyka temu przeczy.

Próg 236,9 Wh/kg to Wasza własna referencja, a nie najlepsza bateria rynkowa. Producent [Molicel podaje dla P50B](https://www.molicel.com/newsroom/ocsial-and-molicel-announce-long-term-partnership-to-enhance-ultrahigh-power-cells-with-single-wall-carbon-nanotubes/) ok. 260 Wh/kg i zdolność ładowania 5C; osobna deklaracja 1400 cykli dotyczy rozładowania 100 W — nie zakładam, że uzyskano ją jednocześnie z ładowaniem 5C. [CATL podał w 2024](https://www.catl.com/en/news/6239.html) 205 Wh/kg na poziomie systemu Shenxing PLUS oraz ładowanie 4C. To komunikaty producentów, nie nasz niezależny pomiar, ale już pokazują, że Wasze 279 Wh/kg ogniwa / 201 pakietu nie dowodzi przewagi.

Twierdzenia o dokładności ±15% i cyklach w granicach 2× nie mają w sprawdzonych plikach zestawu niezależnych danych walidacyjnych, dopasowania i testu poza próbą. Identyczny wynik Python/Rust lub na dwóch PC weryfikuje implementację/powtarzalność, nie prawdziwość modelu fizycznego. Prototyp Python dodatkowo zawiera starszy katalog materiałów niż obecny Rust.

## 7. Co proponuję zamiast pogoni za rekordem symulacji

**Priorytet energii zbliżonej do głównego kandydata:** pozostać przy komercyjnej katodzie NMC, ale porównać grafit i grafit z umiarkowanym dodatkiem Si/SiOx. Zacząć od około 3–5% aktywnego krzemu w masie aktywnej anody, uwzględniając rzeczywistą specyfikację dostawcy, ICE, binder i porowatość. Nie mylić procentu aktywnego Si z procentem kupionego kompozytu Si-C. Pierwszy wariant z przemysłowym elektrolitem ciekłym dobranym do obu elektrod i separatorem powlekanym ceramicznie; określony żel dopiero jako kontrolowany wariant. Podobieństwo do istniejących procesów zwiększa szansę wdrożenia, ale nie zapewnia przewagi kosztowej.

Jeżeli potrzebny jest punkt odniesienia liczbowego, **280–300 Wh/kg oraz ≥800 cykli w określonym protokole 2C można przyjąć jako cel projektu**, nie jako wynik tej analizy ani gwarancję, że umiarkowany dodatek Si go zapewni. W pierwszej serii celem powinno być wykazanie poprawy względem własnego pełnego ogniwa kontrolnego.

**Priorytet kosztu i bezpieczeństwa:** LFP lub LMFP z grafitem, a umiarkowany Si jako opcja po uzyskaniu dobrej referencji. LMFP może zwiększyć napięcie bez Ni/Co, lecz trzeba sprawdzić rozpuszczanie Mn, gazowanie i reakcje z anodą — [badanie Nature Chemistry 2026](https://www.nature.com/articles/s41557-025-02016-2) pokazuje te sprzężenia w pełnych ogniwach LMFP/grafit. Taki produkt ma większą szansę być ekonomiczny niż anode-free/SOLID/DRX, ale nie obiecuję, że wyrówna 279 Wh/kg. Dla magazynu ważniejszy może być koszt oddanej energii przez całe życie niż masa.

**Jeżeli priorytetem pozostaje anode-free:** wybrać konkretną opublikowaną chemię interfejsu i zlecić próbę jej niezależnego odtworzenia. Generyczny parametr GEL nie zastępuje receptury. Jest to osobna ścieżka badawcza.

Praktyczny punkt odniesienia dla krzemu: [Argonne CAMP, materiały komercyjnie dostępne](https://arxiv.org/abs/2509.15144). Autorzy opisują pouch cells z wysokim udziałem SiOx, 600–1000 cykli przy C/3 i **projektowane** cele 350 Wh/kg / 700 Wh/L. To nie dowód 600–1000 cykli przy 2C ani potwierdzenie naszego proponowanego wariantu; to dobry przykład poziomu szczegółowości materiałów i protokołów potrzebnego do oceny wdrożenia.

## 8. Najkrótsza droga do rozstrzygnięcia

1. Zamrozić wyniki jako historyczne; usunąć z komunikacji nieudowodnione „bezpieczne”, „lepsze od rynku”, „produkowalne dziś” oraz zakresy dokładności.
2. Naprawić ciągłość SOC, CC-CV, bilanse litu/sodu, ekspansję, geometrię, energię użytkową oraz protokół cieplny. Powiązać parametry z konkretnymi próbkami materiałów i źródłami. Wprowadzić przedziały niepewności.
3. Skalibrować na kilku pełnych ogniwach referencyjnych; osobne przypadki pozostawić do oceny poza próbą. Kalibracja jednego NMC nie waliduje DRX, Na-ion ani anode-free.
4. Zlecić laboratorium porównanie 2×2: grafit vs grafit z umiarkowanym Si, elektrolit ciekły vs określony żel, ta sama katoda NMC i separator. Najpierw pomiary formacji/ICE, potem kilka replik pełnych pouch cells każdej wersji. Utrzymać zbliżone rzeczywiste obciążenie powierzchniowe i jawny N/P, E/C oraz docisk. Jako start do rozmowy z laboratorium: 3–4 mAh/cm²; nie jest to zoptymalizowana receptura.
5. Porównać energię oddaną na kompletną masę i objętość ogniwa, czas 10–80%, retencję, EFC, sprawność, gazowanie/pęcznienie i przechowywanie. Proponowany wspólny punkt: 25°C i 45°C, ładowanie 2C według jawnego protokołu, rozładowanie 1C, z kontrolami przy wolnym ładowaniu. Testy bezpieczeństwa zlecić specjalistycznemu laboratorium; symulowany piec nie jest kwalifikacją produktu.
6. Dopiero na tej podstawie wycenić BOM, proces, uzysk i wdrożenie u producenta kontraktowego. Nie da się teraz uczciwie wyliczyć kosztu fabryki ani obiecać terminu 1–2 lat z samej nazwy chemii.

**Decyzja, którą podjąłbym dziś:** kontynuować NMC/grafit–Si jako pierwszy eksperyment energetyczny; LFP/LMFP/grafit jako ścieżkę kosztową. Zachować DRX i anode-free jako badania o wyższym ryzyku. Wartość obecnej pracy to kod, uporządkowane hipotezy i baza do projektowania doświadczeń. Potwierdzony wynalazek i przewaga produkcyjna wymagają dopiero wykazania.
