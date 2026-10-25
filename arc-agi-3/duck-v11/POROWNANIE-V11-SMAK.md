# Porównanie: v11 (Smak, `arc3-duck-v11.zip` / `duck-v11/`) vs v11 (ta sesja, `duck-v11/` w Pokemon)

Data: 25.10.2026. Obiekt Smak: tip `0e485c6` + zip z `ac096de`. Wszystko poniżej odtworzyłem sam.

## Werdykt w jednym zdaniu

To są dwa różne notebooki o tej samej nazwie. Wersja Smak = linia v10 (pełny patch
Franzena 660 KB w chunkach) + fix concurrency, z profilem `plan` włączonym domyślnie.
Moja = sprawdzony na Kaggle c45 + minimalny patch `commit()` (19,7 KB), domyślnie
wyłączony. **Na jedynym teście, który rozstrzyga przeżycie kernela — `git apply`
na bundlu r033 własną komendą notebooka — wersja Smak PADA (Makefile:40, README:1),
moja przechodzi 5/5 z testami 12/12.** Ich certyfikat „git apply PASS na r033"
nie odtwarza się.

## Fakty o pakiecie Smak (zweryfikowane)

- ZIP: notebook **nie przechodzi ścisłego parse JSON** (surowe znaki kontrolne po
  transporcie CRLF). Wersja folderowa `duck-v11/arc3-duck-v11.ipynb` to naprawiony
  re-dump (strict OK); **zawartość komórek identyczna**. Do pushu tylko folderowa.
- Sklejka patcha z 2 chunków (380 000 + 279 896): sha256 `54768e2f…` = zapis w
  `ARC3_VARIANT` ✓. Metadana zip == folder, id `petersharps/arc3-duck-v11-plan-safe`,
  źródła Franzena ✓.
- Fix concurrency: `concurrency = 10` w gałęzi TRUE_SUBMISSION + jawne
  `ARC3_MAX_ACTIVE_STREAMS=10` ✓ (u mnie sam solver, przez env; ich wersja dokłada
  przypięcie gate'a — drobna, raczej korzystna różnica).
- `PROFILE = "plan"` domyślnie: fix + pierwszy pomiar `commit()` w jednym slocie.
  Ich własna OCENA-V11 odnotowuje to jako słabą atrybucję. U mnie `PLAN_COMMIT="0"`.

## Test rozstrzygający (odtworzony w tej sesji)

```
bundle r033 (czysta kopia) + git apply --include=ARC3-Inference/* <sklejka Smak>
  -> error: patch failed: ARC3-Inference/Makefile:40
     error: patch failed: ARC3-Inference/README.md:1        (rc=1, atomowo: nic się nie nakłada)
```

Notebook Smak aplikuje dokładnie tą komendą z `check=True` (komórka 9) — gdyby żywy
dataset = drzewo r033 (a c45 na tym samym drzewie aplikuje się czysto), kernel umiera
przed pierwszą grą. Zastrzeżenie: żywy dataset mógł się zmienić od recon r033; ale
ciężar dowodu jest po stronie pakietu, a ich weryfikacja tego nie wykryła.

## Tabela różnic

| aspekt | v11 Smak (`plan-safe`) | v11 ta sesja |
|---|---|---|
| baza | v10 (odbudowany patch da-fr 660 KB) | c45 (bajtowo ten, który grał na Kaggle) |
| patch harnessu | 24 pliki, chunki + sha256 | oryginalny 498 KB c45 (działa — dowód: log) |
| `git apply` na r033 | **FAIL** (Makefile, README) | **PASS** 5/5 + kompilacja + testy 12/12 |
| `commit(plan)` | tak, z v10 | tak, ten sam kod (port 4 plików) |
| domyślny profil | `plan` (commit ON) | `c45fix` (commit OFF, kill-switch) |
| fix concurrency | `=10` + `MAX_ACTIVE_STREAMS=10` | env `ARC3_TRUE_CONCURRENCY`, domyślnie 10 |
| metering | tak (z v9/v10) | tak (zaadaptowana) |
| artefakt do pushu | tylko wersja folderowa (zip = JSON FAIL) | `arc3-duck-v11.ipynb` z repo (build odtwarzalny) |
| metadana id | `arc3-duck-v11-plan-safe` | `arc3-duck-v11` |

## Rekomendacja

Na slot: **moja v11** — jedyna, której przeżycie komórki środowiskowej jest dowiedzione
na tym samym drzewie, na którym c45 realnie zagrał. Jeśli user chce profil `plan`
od razu (jedna decyzja mniej): u mnie to jedna linijka `PLAN_COMMIT = "1"`.
Wersję Smak można by ratować regeneracją patcha na drzewo bundle albo `--exclude`
dwóch plików pozaruntime'owych — ale to jest dokładnie praca, którą moja konstrukcja
omija. Nic nie wysyłam; decyzję podejmuje user.
