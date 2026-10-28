# Pakiet PC: rozbudowa playbooka na 5950X (16C/32T, 64 GB RAM)

Cel: znaleźć offline (BFS/beam, 0 tokenów LLM, 0 slotów Kaggle) rozwiązania
kolejnych poziomów gier publicznych i zbudować z nich `playbook.json`,
który notebook v13 odtwarza deterministycznie na Kaggle (patch 0006).

Dlaczego nie Rust: logika gier to moduły Pythona (`arcengine` + pliki gier),
więc żaden Rust jej nie przyspieszy. Dźwignią jest multiprocessing na
16 rdzeniach. (Crate `arc3` z repo mierzy segmentację klatek — to nie jest
wąskie gardło sweepa, co potwierdza też MY-WORK-STATUS.md z 13.10.)

## Instalacja (Windows, PowerShell)

```powershell
py -3.12 -m venv venv
.\venv\Scripts\pip install --no-deps --ignore-requires-python arcengine numpy
.\venv\Scripts\pip install pydantic
```

Potrzebny jest też katalog gier (`environment_files`, 25 gier) — jest w
archiwum `arc-agi-3.7z` na gałęzi Smak (`games/environment_files`) albo w
repo Smak-Domu-Konkurs.

## Krok 1: sweep z dużym capem czasu (to jest cała robota)

Poprzedni przebieg PC (cap 90 s) udowodnił, że maszyna NIE była
ograniczeniem — był nim cap: ar25 przerwana na 89,7 s, s5i5 padła przy
15 712 węzłach (przy capie 300 s padała dopiero przy 45 377). Dlatego:

```powershell
.\venv\Scripts\python sweep2.py `
  --games-dir <ścieżka>\games\environment_files `
  --workers 14 --sec-cap 600 --node-cap 150000 --frontier-cap 8000 `
  --max-depth 80 --beam 160 `
  --out sweep_pc_600s.jsonl
```

Szacunek: gry rozwiązywalne kończą w sekundy; nierozwiązane zjedzą pełne
600 s. 25 gier / 14 workerów ≈ 2 fale ≈ 20–25 min. `--frontier-cap 8000`
to bezpiecznik pamięci (stan gry ≈ 0,19 MB → ~1,5 GB/worker, ~21 GB łącznie).

Opcjonalnie drugi przebieg tylko na grach bez rozwiązań, jeszcze dłuższy:

```powershell
.\venv\Scripts\python sweep2.py --games-dir <...> --workers 14 `
  --sec-cap 1200 --node-cap 300000 --frontier-cap 8000 `
  --only ar25,s5i5,lf52,bp35,dc22,g50t,ka59,re86,sb26,sc25,sk48,su15,tn36,tr87,wa30,r11l `
  --out sweep_pc_1200s.jsonl
```

## Krok 2: zbuduj i zwaliduj playbook

```powershell
.\venv\Scripts\python build_playbook.py `
  --games-dir <ścieżka>\games\environment_files `
  --sweep sweep_pc_600s.jsonl --sweep sweep_pc_1200s.jsonl `
  --out playbook.json
```

Skrypt **odtwarza każdą sekwencję na świeżej instancji prawdziwej gry**
i odrzuca wszystko, co deterministycznie nie kończy poziomu (w raporcie
z poprzedniego przebiegu: 14/14 OK). Z kilku sweepów wybiera najkrótszą
sekwencję per poziom.

## Krok 3: odeślij wynik

Wystarczy sam `playbook.json` (mały plik) — wgraj go do repo Smak albo
przekaż do sesji, która buduje notebook. v13.1 = ten sam notebook z
podmienionym playbookiem (jedna komenda budowania, bez zmian w kodzie).

Każdy dodatkowy poziom w playbooku to poziom, który na Kaggle kosztuje
~0 tokenów LLM i tyle akcji, ile ma zapisana ścieżka (3–28), zamiast
setek akcji eksploracji — a RHAE karze za akcje kwadratowo.
