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
