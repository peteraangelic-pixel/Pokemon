# Audyt baterii — przekazanie ustaleń kolejnemu AI

Data: 2026-11-01. Repo: `peteraangelic-pixel/Pokemon`, gałąź `arena/d1882c0f-pokemon`.
Commit bazowy sprawdzony przed publikacją audytu: `697a0150204047c6a59f2ede0b7156cf3db27735`.

**Zacznij od [AUDYT_BATERII_PL.md](AUDYT_BATERII_PL.md).** Zawiera pełną ocenę projektu,
błędy w kodzie, ograniczenia wnioskowania, porównanie sześciu kandydatów, źródła naukowe,
alternatywne kierunki rozwoju i plan walidacji. Historyczne portfolio i pitch w pozostałych
katalogach należy czytać razem z tym audytem, bo zawierają twierdzenia, których model nie uzasadnia.

## Najważniejsze ustalenia do sprawdzenia w kodzie

1. Test w piecu 150°C zeruje prąd od początku przez shutdown przy 130°C; zadanie 0C/1C/10C daje identyczny wynik cieplny.
2. PASS nie wymaga osiągnięcia 80% SOC. 234 z 420 zwycięzców `optim_winners.csv` go nie osiągają.
3. Rekord DRX/Si-C/GEL: 361 Wh/kg nominalnie, 641 częściowych cykli przy −10°C, ale tylko 32% oddanej pojemności w pierwszym cyklu; 443 cykle przy 25°C.
4. SOC resetuje się do zera przed każdym cyklem, nawet jeśli poprzednie rozładowanie skończyło się powyżej zera.
5. Trwałość LFP/LIFREE zależy silnie od założonego `dead_li`: 512/126/44 cykle w trzech scenariuszach.
6. Rozszerzalność Si nie wpływa na wynik; bilans masy i geometrii nie różnicuje LP57/GEL/SOLID.
7. Podane USD/kWh obejmują część materiałów, nie pełny koszt produkcji. NMC811 zawiera kobalt.

To są ustalenia audytu kodu i symulacji. Nie wykonano fizycznych ogniw, pomiarów laboratoryjnych,
certyfikacji ani wyceny przez fabrykę. Analiza wrażliwości nie wyznacza rzeczywistych parametrów materiału.

## Pliki dowodowe

- `runtime.txt` — komendy i pełne wyniki sześciu odtworzonych konfiguracji.
- `*-trace.csv` — ich przebiegi cykl po cyklu.
- `evidence.json` — zliczenia CSV, przykłady PASS bez 80% SOC, EFC z trace i zgodność plików z GitHubem.
- `github-tree.json` — manifest 26 plików wejściowego drzewa `battery-sim` z Git blob SHA-1.
- `inputs/optim_winners.csv` — oryginalny wynik 2880 kombinacji z lokalnego `battery-sim2`, którego brakowało we wskazanej gałęzi.
- `reproduce.py` — analiza oryginalnych CSV i odtworzenie sześciu przypadków.
- `sensitivity.rs`, `sensitivity.txt` — eksperyment wrażliwości i jego wynik, bez modyfikowania modelu.

Zapisane logi zawierają lokalne ścieżki z komputera, na którym wykonano audyt.
`evidence.json` obejmuje również lokalne duplikaty `battery-sim2` i katalog pobrany z GitHuba;
po uruchomieniu w samym repozytorium lista ścieżek będzie krótsza. Porównuj metryki, nie nazwy lokalnych katalogów.

## Odtworzenie po pobraniu gałęzi

**Uwaga po wydaniu v0.2:** ponizsze dowody dotycza historycznego modelu v0.1.
W osobnym checkoutcie aktualnej galezi najpierw wykonaj:

```powershell
git restore --source=697a0150204047c6a59f2ede0b7156cf3db27735 -- battery-sim
```

Nastepnie buduj i uruchamiaj polecenia ponizej. Skrypt odmawia nadpisania historycznych
dowodow, jesli manifest zrodel nie odpowiada wersji audytowanej.
Do aktualnego modelu sluzy `battery-sim/tools/validate_v02.py --sweep`;
szczegoly: [zmiany v0.2](../battery-sim/ZMIANY_V02.md).

Wymagane: Rust/Cargo i Python 3; brak dodatkowych pakietów Python.
Z głównego katalogu repozytorium:

```powershell
cargo build --release --no-default-features --manifest-path battery-sim/Cargo.toml
python audyt-2026-11-01/reproduce.py
rustc -O audyt-2026-11-01/sensitivity.rs -o audyt-2026-11-01/sensitivity.exe
./audyt-2026-11-01/sensitivity.exe
```

Na Linux/macOS można nadać programowi nazwę `sensitivity` zamiast `sensitivity.exe`.
Skrypt Python rozpoznaje oba warianty nazwy programu `battery-sim`.
Uruchomienie `reproduce.py` nadpisuje dowody `evidence.json`, `runtime.txt` i sześć trace CSV
w katalogu audytu, dlatego do zachowania opublikowanych wyników użyj osobnego checkoutu.

W pierwotnym lokalnym folderze `NewBattery` źródła najnowszej wersji są w
`Pokemon-arena-d1882c0f-pokemon/battery-sim`; skrypt Python rozpoznaje ten układ.
Kompilując tam harness Rust, dodaj `--cfg local_snapshot`, aby wskazać tę samą wersję źródeł:

```powershell
rustc -O --cfg local_snapshot audyt-2026-11-01/sensitivity.rs -o audyt-2026-11-01/sensitivity.exe
```

## Co robić dalej

Najpierw poprawić model i oddzielić energię nominalną od oddanej, częściowe cykle od EFC
oraz regułę bezpieczeństwa od walidacji fizycznej. Zachować dotychczasowe CSV jako historyczne.
Przed zmianami przeczytać cały audyt, zwłaszcza opis bilansu litu w anode-free: lit pochodzi
z katody, więc nie należy dodawać jego masy ponownie, lecz trzeba modelować jego objętość i reakcje.
Potem porównać kontrolowane warianty pełnych ogniw i dopiero aktualizować portfolio/pitch.

Ta publikacja dodaje dokumentację i dowody. Nie naprawia jeszcze symulatora ani nie zatwierdza jego prognoz.
