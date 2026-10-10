# ARC-AGI-3 — stan i przekazanie (handoff)

> Ten plik istnieje po to, żeby **nowa sesja Arena.ai mogła podjąć pracę w 2 minuty**.
> Nowa sesja nie pamięta tej rozmowy — wszystko, co ma wiedzieć, musi być tutaj.

**Ostatnia aktualizacja:** 10 X 2026, ~20:30 CEST

---

## Stan: ETAP 1 — crate Rust działa, baseline Kaggle nie odpalony

| Pozycja | Wartość |
|---|---|
| Konkurs zaakceptowany na Kaggle | ✅ (użytkownik potwierdził) |
| Sklonowany baseline | ✅ `Tufalabs/duck-harness` (MIT) — **tylko w `.cache/duck`, NIE w repo** |
| Analiza architektury | ✅ `README.md` w tym katalogu |
| **Crate Rust: segmentacja** | ✅ port zgodny bajt-w-bajt z Pythonem |
| **Crate Rust: RHAE** | ✅ |
| **Crate Rust: replay** | ✅ |
| **CI zielone** | ✅ clippy `-D warnings` + 32 testy |
| Zmierzony zysk Rust vs Python | ✅ ~121× realistyczna klatka, ~276× patologiczna — `rust/BENCHMARK.md` |
| Uruchomiony baseline na Kaggle | ❌ **następny krok** |
| Starter kit + `make play-local` | ❌ **następny krok** (wymaga tokena Kaggle) |
| Wynik własny na leaderboardzie | ❌ |

### Sprzęt użytkownika (ustalone)

- **5950X (16 rdzeni) + 64 GB RAM**
- **GPU 8–16 GB VRAM** → lokalnie tylko modele 7–8B. Iteracja logiki agenta OK, testy 27B wymagają Kaggle.
- Wniosek: skoro nasze poprawki dotyczą **scaffoldingu, nie modelu**, można je walidować na małym modelu lokalnie. To oszczędza kwotę GPU na Kaggle.

### ⚠️ Ustalenia o CI (ważne przy dalszej pracy)

Sandbox sięga tylko `api.github.com`. W efekcie:
- `gh run view --log` **nie działa** (logi leżą na `results-receiver.actions.githubusercontent.com`)
- artefakty **nie działają** (`*.blob.core.windows.net`)
- `git push` z runnera **nie działa**

**Działający kanał:** CI komituje logi do `arc-agi-3/ci-logs/` przez GitHub Contents API (`gh api -X PUT`). Te pliki nie są w `paths:`, więc nie tworzą pętli. Czytaj je lokalnie po `git pull`.

**Pułapka, którą już naprawiliśmy:** `cmd 2>&1 | tee log` maskuje status wyjścia — build i testy raportowały sukces mimo błędu kompilacji. Każdy taki krok ma teraz `set -o pipefail`.

⚠️ **`.cache/` jest wyłączone ze snapshotów.** Po nowym uruchomieniu trzeba zrobić
`git clone --depth 1 https://github.com/Tufalabs/duck-harness.git` od nowa.

---

## Co już wiemy (nie odkrywaj tego od zera)

Kontekst rynkowy — patrz `../konkursy-ai-2026.md` (główny brief):
- 28 aktywnych teamów (nie 4 494 — to liczba kont), top to Tufa Labs 55,89 RHAE
- Leaderboard skoczył z 27,9% (30 IX) na 55,89% (4 X), bo Duck poszedł open-source
- Zostało **$75 000 dla top-5**; milestone'y (30 VI, 30 IX) przepadły; $700k bonusu poza zasięgiem
- **Zero wymogu angielskiego** — czysty wynik na leaderboardzie, bez writeupu (w przeciwieństwie do ARC-AGI-2, gdzie $275k jest *za opis*)

Technika — patrz `README.md` w tym katalogu:
- 7 słabych punktów zidentyfikowanych w kodzie, z numerami linii
- Największa luka: **brak pamięci między 20 passami** (`_ensure_session` zeruje wszystko)
- Druga: **wiedza kasowana przy przejściu poziomu** (6 z 7 slotów)
- Trzecia: parser etykiet gubi markdown (`**World model:**` nie zadziała) — najłatwiejszy pewny zysk
- **Binding constraint: 9 h na notebooku Kaggle.** Config z repo (25 gier × 20 passów × 45 min) się nie mieści

---

## ⚠️ Najpierw jedno pytanie do użytkownika

**Czy masz GPU i jakie?**

- **Brak GPU / ≤8 GB** → iteracja LLM lokalnie odpada. Zostaje: logika agenta lokalnie (`make play-local`, bez GPU) + Rust/precompute + pomiary na Kaggle.
- **24 GB (3090/4090)** → **Qwen3.6-27B w Q4 (~16 GB) chodzi lokalnie przez llama.cpp/ik_llama** → pełna iteracja na własnym sprzęcie, Kaggle tylko do finału. To zmienia wszystko.
- **≥48 GB** → mieści się nawet FP8 (~27 GB), czyli praktycznie ten sam model co na Kaggle.

Bez tej odpowiedzi nie da się zaplanować dni 3–17.

## Następny krok (dokładnie)

1. **Odpowiedzieć na pytanie o GPU wyżej** — reszta zależy od odpowiedzi.
2. `git clone https://github.com/arcprize/ARC-AGI-3-Kaggle-Starter.git` → `make setup` → `make play-local`
   - **Nie wymaga GPU.** Prawdziwy silnik gier (`arc-agi` z PyPI = to samo co bramka Kaggle), agent gra lokalnie w sekundach.
   - Wrzucić Kaggle API token do `.kaggle/access_token` w katalogu projektu (nie do home).
3. Zmierzyć **realny czas jednego passu** na Kaggle (najpierw T4, potem RTX 6000) — bez tej liczby nie da się nic zaplanować.
4. Dopiero potem ruszać punkty E → B → A z `README.md`.

## Ustalenia techniczne (zatwierdzone przez użytkownika)

- **Zostajemy na branchu `arena/7cc8a7e0-pokemon`** — projekt ARC prowadzony w katalogu `arc-agi-3/`
- **Rust + rayon zamiast Pythona** do wszystkiego poza drobiazgami (nawet ~200× przyspieszenia)
- **GitHub Actions** do obliczeń, których nie da się wykonać lokalnie
- ⚠️ Actions **nie ma GPU** — nie da się tam odpalać inferencji 27B. Tylko: budowanie/testy crate'a Rust, CI, analiza artefaktów
- ⚠️ Finałowa submision **musi** wykonać się w notebooku Kaggle (9 h) — komputer lokalny jej nie zastąpi

---

## Deadline'y

| Data | Co |
|---|---|
| 26 X 2026 | entry deadline — **już zaakceptowane** |
| **2 XI 2026** | **finałowa submision** |
| 4 XII 2026 | ogłoszenie wyników |

Dni do submision: **22** (od 10 X)

---

## Podział na sesje (ustalony z użytkownikiem)

| Sesja | Branch | Cel |
|---|---|---|
| `arena/7cc8a7e0-pokemon` | **ta sesja** | Pokémon TCG AI Battle Challenge (Kaggle) |
| osobna (do założenia) | przydzieli Arena | **ARC-AGI-3** ← to |
| osobna | — | Gemma 4 Developer Agent (już działa) |
| osobna | — | hackathony Devpost |

⚠️ **Zasada:** jeden konkurs = jedna sesja. Nie puszczać tego samego konkursu w dwóch sesjach — Kaggle to jedno konto = jedna osoba, dwa teamy grożą dyskwalifikacją.

---

## Jak zacząć nową sesję

Wklej na początku:

```
Przeczytaj arc-agi-3/README.md i arc-agi-3/STATUS.md w tym repo.
Pracujemy nad ARC-AGI-3 na Kaggle (deadline 2 XI 2026).
Kontynuuj od kroku „Następny krok" w STATUS.md.
Nie rób zmian w kodzie poza katalogiem arc-agi-3/.
```

---

## ETAP 2 (2026-10-10): most na Kaggle działa, leaderboard zmierzony

### Jak czytać wyniki z CI — ostateczne ustalenie

Trzy próby i wszystkie potwierdzają to samo, co zapisały poprzednie sesje
w tym repo (`kaggle_poll.yml` na gałęzi `arena/c87f7a48-pokemon`):

| Kanał | Działa? |
|---|---|
| Logi Actions (`gh run view --log`, `--log-failed`) | ❌ host poza allowlistą |
| Artefakty (`upload-artifact`) | ❌ `*.blob.core.windows.net` poza allowlistą |
| `gh workflow run` / API dispatch | ❌ **403** — token aplikacji nie może dispatchować |
| Listowanie sekretów | ❌ 403 |
| **Workflow commituje wyniki na branch** | ✅ jedyny czytelny kanał |
| **`gh api .../jobs`** (status per krok) | ✅ |

**Wzorzec:** `touch <trigger>.trigger && git push` → workflow robi robotę →
commituje wyniki do `arc-agi-3/kaggle/results/` → agent czyta po `git pull`.
Workflow: `.github/workflows/arc-agi-3-kaggle.yml`.

### Sekret Kaggle: działa

`KAGGLE_API_TOKEN` jest w sekretach tego repo (konto **petersharps**).
Zweryfikowane: `kaggle competitions files -c arc-prize-2026-arc-agi-3`
zwróciło prawdziwe dane → **jesteśmy zapisani do konkursu**, **0 zgłoszeń**.
W danych konkursu jest m.in. pełne repo `ARC-AGI-3-Agents`.

### Publiczny leaderboard — stan na 2026-10-10

| Pozycja | Drużyna | Wynik |
|---|---|---|
| 1 | Yi-Chia Chen | **62.96** |
| 2 | Tufa Labs | **56.52** |
| 3 | mtg | 45.00 |
| 4 | Majkel1337 | 42.66 |
| 5 | NVARC3 | **40.97** ← próg nagrody |
| 10 | fshindo | 38.20 |
| 20 | Son & Mark & Ronen | 35.45 |

**Rozkład jest dwugarbny:** 15 drużyn stłoczonych w 35–40, potem luka,
i dwaj liderzy (56.52, 62.96). Mediana 38.17.

**Luka z mediany do progu nagrody: +2.80 pkt.** To zupełnie inna sytuacja niż
~7.5% lidera notowane we wrześniu przez poprzednią sesję — pole się przesunęło.

### ⚠️ Nierozstrzygnięte: ARC-AGI-3 było już raz zamknięte

W `riemann` wątek zamknięto 2026-09-04, głównie przez **eligibility**
(open-source, angielskie write-upy, rozmowy z organizatorami, KYC).
Szczegóły i twarde wyniki negatywne: **`arc-agi-3/PRIOR_WORK.md`**.

Nagrody ARC Prize Foundation (Grand Prize $700K) tych wymogów mają — ale
**konkurs Kaggle ($75 000 / top 5) ocenia wyłącznie wynikiem: bez write-upu
i bez rozmowy**. Pytanie do właściciela: czy KYC przy wypłacie też dyskwalifikuje?
