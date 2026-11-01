# v0.2.0 — pierwsza korekta modelu po audycie

Data: 2026-11-01. Wersja bazowa: `88b0e101076591eca914359655424d9fb5ee186e`.
Uwzgledniono wczesniejsze poprawki drugiego AI z commitow `bcfc44f` i `88b0e10`.

**To poprawka poprawnosci obliczen i prezentacji wynikow, a nie zwalidowany nowy model baterii.**
Stalych materialowych i degradacyjnych nie dopasowano ponownie do danych laboratoryjnych.
Wzrost liczby cykli po zmianie wzoru SEI lub bilansu masy nie oznacza postepu materialowego.

## Co poprawiono

- SOC nie resetuje sie do zera miedzy cyklami. Zachowywany jest znormalizowany SOC konca
  poprzedniego rozladowania; nadal nie jest to pelny bilans stezen i stechiometrii elektrod.
- Krok czasowy konczy sie na granicy SOC=0/1, zamiast przekraczac zakres.
  Shutdown separatora i limity czasu zatrzymuja protokol, zamiast pozostawiac petle bez postepu.
- Prady CC sa odniesione do poczatkowego Ah. Program jawnie informuje, ze NIE ma fazy CV.
- Calkowana jest energia oddana, energia pobrana i przeplyw ladunku. EFC oznacza
  sume rozladowanych mAh podzielona przez poczatkowe mAh. Wyniki energii sa na mase
  modelowego ogniwa, nie pomiarem gotowego produktu.
- Oddzielono czas 0–80% od 10–80%; przejscia SOC sa interpolowane w kroku czasowym.
  Nowe pola czasu sa puste/NA, jesli cel nie zostal osiagniety. Historyczne pole `t80_min`
  w pierwszych kolumnach CSV pozostaje dla zgodnosci, z zerem dla braku wyniku.
- Cykl kwalifikowany wymaga oddania >=80% aktualnej pojemnosci oraz zmierzonego
  przejscia 10–80% w <=30 min. Kryterium szybkiego ladowania wymaga dodatkowo >=2C.
  EOL rate-limited ma teraz prog 80%, zamiast historycznych 30%.
- SEI korzysta z roznicy pierwiastkow czasu skumulowanego, zamiast sumy pierwiastkow
  czasow kolejnych cykli. Zaleznosci temperaturowe nadal wymagaja kalibracji.
- Strata dead-Li jest odnoszona do rzeczywiscie przepuszczonego ladunku, nie stalej kary
  za kazdy czesciowy cykl. Parametr nie jest eksperymentalnie wyznaczona sprawnoscia CE.
- Loading oznacza mase calej suchej powloki; udzial aktywny jest stosowany raz w
  pojemnosci. Ceny materialu aktywnego sa mnozone przez jego mase, a nie mase calej powloki.
- Kryterium energii i ranking korzystaja z energii rzeczywiscie oddanej w pierwszym cyklu,
  nie nominalnej calki OCV. Referencja: NMC811/grafit/LP57, L20, N/P1.1, 25C, CC 2C/1C.
  Jest to stala referencja projektu, nie twierdzenie o najlepszym ogniwie na rynku.
- Wyszukiwanie wybiera tempo wedlug liczby kwalifikowanych cykli, nie samego licznika petli.
- Rozdzielono `performance_pass` od pelnego `passed`. Obecny model nie opisuje chemii
  przeladowania poza 100% SOC: `abuse_model_complete=false` przy zadanym overcharge.
  W rezultacie brak zdarzen cieplnych nie daje pelnego PASS. To brak pokrycia modelu,
  nie dowod niebezpieczenstwa ani bezpieczenstwa fizycznej baterii.
- Raport, pitch i investor korzystaja z aktualnej tabeli diagnostycznej i jawnego statusu
  badan. Usunieto z generatora historyczne obietnice dokladnosci, kosztu fabryki i terminu wdrozenia.
- Dodano 14 testow regresji i skrypt odtwarzajacy przypadki oraz siatke 2880 konfiguracji.
  CI uruchamia testy w konfiguracji rayon i std oraz archiwizuje nowe dowody.

## Wyniki kontrolne

Warunki jak w pierwotnym audycie: ladowanie CC 2C, rozladowanie 1C. Prad w v0.2 odniesiony
do poczatkowej pojemnosci. Nie nalezy interpretowac porownania jako badania dwoch fizycznych baterii.

| przypadek | v0.1 licznik cykli | v0.2 licznik / kwalifikowane cykle | v0.2 nominalne Wh/kg | v0.2 oddane Wh/kg, cykl 1 |
|---|---:|---:|---:|---:|
| NMC811/Si-C/GEL, L30, N/P1.10, 25C | 670 | 824 / 824 | 286.6 | 213.2 |
| DRX/Si-C/GEL, L40, N/P1.02, −10C | 641 | 1 / 0 | 373.0 | 100.4 |
| ten sam DRX, 25C | 443 | 1 / 0 | 373.0 | 222.2 |
| LFP/LIFREE/LP57, L35, N/P1.02, 25C | 512 | 616 / 616 | 278.2 | 256.8 |
| NMC811/LIFREE/GEL, L35, N/P1.02, −10C | 542 | 1 / 0 | 366.7 | 107.1 |
| referencja NMC811/grafit/LP57, L20, N/P1.10, 25C | 735 | 544 / 544 | 242.7 | 214.0 |

Flagship ma w tym protokole praktycznie taka sama energie oddana jak referencja
(213.2 wobec 214.0 Wh/kg). Ten model nie pokazuje jego przewagi energetycznej.
DRX przy −10C oddaje tylko ~33% aktualnej pojemnosci, wiec proba jest konczona jako rate-limited.
Wieksza liczba cykli LIFREE nadal bazuje na umownych parametrach litu i nie dowodzi wykonalnosci.

Pelna siatka 2880 projektow: **248 performance_pass**, w tym NMC811:93, LFP:152, DRX:3.
Zaden performance_pass nie ma brakujacego czasu 10–80%.
**Pelny passed: 0**, bo model nie pokrywa wymaganej chemii przeładowania.
Nie sa to 248 zwalidowanych baterii ani mapa rzeczywistego uzysku produkcyjnego.

## Odtworzenie

Z katalogu `battery-sim`:

```powershell
cargo test
cargo test --no-default-features
cargo fmt --check
cargo clippy --all-targets -- -D warnings
cargo clippy --all-targets --no-default-features -- -D warnings
cargo build --release
python tools/validate_v02.py --sweep
```

Wyniki: `results/v0.2.0/summary.json`, `runtime.txt`, szesc `*-trace.csv`,
`optim_winners_v02.csv`, `report-en.md` i `report-pl.md`. Skrypt nadpisuje tylko
dowody w tym katalogu wersji. Oryginalne `grid.csv`, `mega.csv`, `marathon.csv`
i `audyt-2026-11-01` sa historyczne; nie zostaly przeliczone ani podmienione.

## Co pozostaje do zrobienia

1. Kalibracja i ocena poza proba na niezaleznych pelnych ogniwach; nie nadawac zakresow
   dokladnosci bez danych. Oryginalny prototyp Python jest historyczny, nie portem 1:1 v0.2.
2. Pelny CC-CV, poprawne okna stechiometrii i potencjaly elektrod, formacja oraz sprzezenie
   degradacji z oknem uzytkowym i starzeniem kalendarzowym. Teraz jest jawny model CC.
3. Mechanika Si, zmiany porowatosci, gazowanie, realna objętość i bilans litu w anode-free.
   Fikcyjne 38600 mAh/g LIFREE nadal oznacza skrot modelowy, nie material.
4. Oddzielne masy, gestosci i geometrie elektrolitow/ceramiki; dzisiejsze Wh/L sa
   przyblizeniem suchego stosu, bez pelnego bilansu objętości i opakowania.
5. Mapa zgodnosci soli i elektrod. LP57 jest elektrolitem litowym: wynik Na/HC/LP57
   nie jest kompletna receptura sodowa. NVP i NFPP trzeba rozdzielic materialowo.
6. Testy termiczne na skalibrowanej geometrii i chemia nadmiernego naladowania; obecne
   dwa etapy cieplne sa diagnostyka, nie testem normatywnym. Przeplyw pradu w ich logu
   nie dowodzi poprawnej reakcji chemicznej poza pelnym SOC.
7. Pelny BOM, ceny konkretnych gatunkow materialow, proces, formacja, uzysk i wycena
   przez producenta kontraktowego. Czesciowy koszt materialow nie jest cena gotowego ogniwa.

Do czasu wykonania tych krokow nie rekomenduje wyboru inwestycyjnego ani produkcyjnego
na podstawie rankingu tego symulatora. Najblizszy praktyczny krok pozostaje taki jak w audycie:
kontrolowane pelne ogniwa NMC/grafit–Si oraz osobna sciezka kosztowa LFP/LMFP/grafit.
