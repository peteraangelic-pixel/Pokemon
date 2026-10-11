# Droga zgłoszeniowa na Kaggle — zwalidowana 11 X 2026

## Co działa

Notebook: **https://www.kaggle.com/code/petersharps/arc-agi-3-novelty-explorer**
Konto: **petersharps** (potwierdzone przez API)

Przebieg: `KernelWorkerStatus.COMPLETE`, zero błędów. W logu:
- `arc-agi-0.9.8` i `arcengine-0.9.3` instalują się z
  `/kaggle/input/competitions/arc-prize-2026-arc-agi-3/arc_agi_3_wheels`
  → **nie trzeba internetu**, co potwierdza założenie o braku sieci
- `Prepared tracked novelty-explorer source in /tmp/arc_novelty_agent`

## ⚠️ Save & Run All NIE daje wyniku

W logu: `Wrote save-phase placeholder submission.parquet`

To celowe (`build_notebook.py`): w zwykłym trybie notebook zapisuje **atrapę**,
żeby walidacja przeszła bez łączenia się z bramką konkursu.

**Prawdziwa ewaluacja dzieje się dopiero po kliknięciu „Submit to Competition"
na Kaggle** — wtedy notebook odpala się w trybie konkursowym i faktycznie gra.

Konsekwencja: **nie mamy jeszcze żadnego wyniku na prywatnym zbiorze.** Mamy
tylko potwierdzenie, że cała droga techniczna działa.

## Kwestia modelu

`kernel-metadata.json` ma `model_sources: []` — agent jest deterministyczny,
bez modelu. Żeby wejść z modelem, trzeba dodać model hostowany na Kaggle
(np. Qwen 2.5 7B) do `model_sources`, bo notebook nie ma internetu i nie
pobierze wag w trakcie biegu.

To nie zostało zrobione — to następny krok, nie drobiazg.

## Jak sprawdzać status bez ponownego pusha

```bash
touch arc-agi-3/.kaggle-poll.trigger && git add -A && git commit -m poll && git push
```

Workflow `arc-agi-3-kaggle.yml` pobiera `kaggle kernels status` oraz log i
`submission.parquet` do `arc-agi-3/kaggle/results/`. Każdy `make submit`
tworzy nową wersję kernela i restartuje bieg — dlatego sprawdzamy status
osobno, bez pusha.

## Ograniczenie

**Kaggle pozwala na jedno oficjalne zgłoszenie dziennie.** Kliknięcie
„Submit to Competition" należy do właściciela konta — nigdy nie zrobię tego
sam z siebie.

---

## ZGLOSZENIE DO KONKURSU PRZEZ API — DZIALA (11 X 2026)

Wcześniej sądziliśmy, że zgłoszenie wymaga ręcznego kliknięcia
„Submit to Competition". **To nieprawda.** Kaggle CLI 2.2.4 ma:

```
kaggle competitions submit -c <competition> -k <notebook> \
                           -f <plik wyjsciowy> -v <wersja> -m "<opis>"
  -k KERNEL   Name of kernel (notebook) to submit to a code competition
```

W riemann używaliśmy `-f tarball`, bo kaggriculture była konkurencją
**plikową**. ARC-AGI-3 jest konkurencją **kodową** — tu idzie `-k`.

### Dokładna sekwencja (zaimplementowana w `arc-agi-3-submit-competition.yml`)

1. `make setup` → venv z kaggle
2. zapisz token do `.kaggle/access_token`
3. `kaggle competitions submission-limits -c COMP` → **przerwij, jeśli
   `Remaining today: 0`** (zabezpieczenie przed spaleniem limitu)
4. `make notebook` → generuje `notebooks/submission.ipynb`
5. `kaggle kernels push -p notebooks` → zwraca
   **`Kernel version N successfully pushed.`** ← stąd bierzemy N
6. czekaj, aż `kaggle kernels status <ref>` pokaże `KernelWorkerStatus.COMPLETE`
7. `kaggle competitions submit -c COMP -k <ref> -f submission.parquet -v N -m "..."`

### Pułapki, na które weszliśmy

| błąd | przyczyna | naprawa |
|---|---|---|
| `require both the output file name and the version number` | brak `-f` i `-v` | podać oba |
| parsowanie wersji zwracało pustkę | regex miał `\\D` zamiast `\D` po przejściu przez YAML | czytać `Kernel version N successfully pushed` z logu pusha |
| krok kończył się błędem mimo `true` na końcu | Actions używa `bash -e`; `kaggle kernels submit --help` zwraca 2 | `|| true` przy samej komendzie |

### Ważne: błędy nie zużywają limitu

`exit_code=1` zostawiał `Remaining today: 1`. Można bezpiecznie próbować
kolejnych wersji, aż jedna zostanie przyjęta.

### Po zgłoszeniu — diagnostyka, której dotąd nie mieliśmy

```
kaggle competitions submissions -c COMP --csv     # id i status
kaggle competitions episodes <submission_id>      # w co agent faktycznie grał
kaggle competitions replay <episode_id>           # nagranie
kaggle competitions logs <episode_id> <idx>       # logi agenta
```

### Nasze pierwsze prawdziwe zgłoszenie

- **id 57075036**, wysłane 2026-10-11 13:15 UTC, status `PENDING`
- notebook `petersharps/arc-agi-3-novelty-explorer` wersja 5
- `Submissions today: 1`, `Remaining today: 0` (limit dzienny wykorzystany)
- bieg konkursowy trwa do **9 godzin** — wynik sprawdzamy przez
  `arc-agi-3/.kaggle-poll.trigger`
