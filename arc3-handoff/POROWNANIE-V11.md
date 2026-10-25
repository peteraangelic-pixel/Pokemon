# v11 (`arc3-duck-v11-plan-safe`) kontra moja wersja agenta

**Data:** 2026-10-25 · **Autor:** sesja `arena/c87f7a48-pokemon`
**Źródła (read-only przez `gh api`):** `arc-agi-3/duck-v11/README.md`, `OCENA-V11-ARENA.md`,
`arc3-duck-v11.ipynb` (874 384 B), `kernel-metadata-v11.json`, `arc3-duck-v11.zip` (226 131 B),
oraz `duck-c45/arc3-duck-c45.ipynb` do weryfikacji pierwotnej przyczyny.

Werdykt w jednym zdaniu: **v11 naprawia bug, który kosztował slot i który był w MOIM własnym
notebooku — przepisałem wszystkie trzy liczby do `FAKTY-I-POMIARY.md` w trzech sąsiednich
liniach i nigdy ich nie porównałem.** Architektonicznie v11 jest przede mną; analitycznie jestem
przed v11. Szczegóły i tabela poniżej.

---

## 1. Zweryfikowana przyczyna 0.00 — potwierdzam w źródle, nie na słowo

Ich diagnoza (commit `6dc0aa7c`, 15:04 UTC): „`TRUE_SUBMISSION concurrency=120` vs serwer
`MAXREQ=10` → głód slotów (0 poziomów); parquet=stub". **Sprawdziłem to w notebooku c45
i jest dokładnie tak.** Trzy komórki, trzy liczby:

```
cell  9 | 'ARC3_MAX_ACTIVE_STREAMS': 10,
cell 17 | MAXREQ=10,
cell 17 | "--max-running-requests", str(CFG["MAXREQ"]), ...
cell 17 | assert CFG["CUDAGRAPH_MAXBS"] >= CFG["MAXREQ"]
cell 21 | bm.solver.concurrency = 10          <- ścieżka SMOKE
cell 21 | bm.solver.concurrency = 120  # game count should be 110   <- ścieżka TRUE_SUBMISSION
cell 21 | bm.solver.max_runtime_s_per_game = 532*60
```

| ścieżka | concurrency | backend (`MAXREQ` / `MAX_ACTIVE_STREAMS`) | wynik |
|---|---|---|---|
| **smoke** | **10** | 10 / 10 | ✅ zgodne → r019 = 27.21, r076 = 10 gier z logami |
| **TRUE_SUBMISSION** | **120** | 10 / 10 | ❌ **120-way fanout na 10 slotów** → ref 57629847 = **0.00** |

### Dlaczego nikt tego nie złapał przez dziewięć dni

> **Bramka `ARC3_SMOKE_OK` jest strukturalnie ślepa na tę klasę buga.** Smoke ustawia
> `concurrency = 10`, czyli **dokładnie tyle, ile backend**. Ścieżka submisji ustawia 120.
> Więc smoke **z konstrukcji nie może** zwalidować ścieżki submisji — przechodzi zawsze,
> niezależnie od tego, czy rerun przejdzie.

To jest ważniejsze niż sam bug: **ich proces walidacji ma dziurę, przez którą przejdzie każda
rozbieżność między smoke a rerunem.** Konkretne zabezpieczenie, które by to złapało (3 linie,
zero GPU, zero tokenów):

```python
# preflight ścieżki SUBMISJI, w komórce 21 przed uruchomieniem
if TRUE_SUBMISSION:
    _be = int(os.environ.get("ARC3_MAX_ACTIVE_STREAMS", CFG["MAXREQ"]))
    assert bm.solver.concurrency <= _be, (
        f"concurrency={bm.solver.concurrency} > backend slots={_be} "
        f"-> fanout zagłodzi gry (to dało 0.00 na ref 57629847)")
```

Warto to włożyć **do notebooka**, nie do dokumentu — dokumenty tej klasy ustaleń już były
i nie pomogły.

---

## 2. Mój własny błąd — udokumentowany przeze mnie, niewykryty przeze mnie

`FAKTY-I-POMIARY.md`, trzy sąsiednie wpisy:

```
L629: ARC3_MAX_ACTIVE_STREAMS       = 10
L636: `TRUE_SUBMISSION` = `n_passes=1`, `concurrency=120`, `max_runtime_s_per_game=532*60`
L638: Cell 17 (SGLang): `CTX=(116+12+8)*1024`, `MEMFRAC=0.96`, `MAXREQ=10`, `CUDAGRAPH_MAXBS=10`
```

**Mam wszystkie trzy liczby, zapisane wiernie, osiem linii od siebie — i nigdy ich nie
porównałem.** Mało tego, poszedłem w złą stronę:

- `FAKTY` L975: „**10 slotów dopasowane do `MAXREQ`**” — zauważyłem dopasowanie po stronie
  `MAX_ACTIVE_STREAMS`, ale nie zauważyłem, że `concurrency` je łamie 12-krotnie.
- `FAKTY` L677-679: zapisałem **ekstrapolację**, że podniesienie `MAXREQ` 10→16-20 dałoby
  ~+45% puli KV, i oznaczyłem to jako „lever #3”. **Dźwignia była odwrotna**: problem nie polegał
  na tym, że backend ma za mało slotów, tylko że frontend prosi o 12× za dużo.

I mój własny `notebook/arc3-duck-fixed.ipynb` (30 komórek) **ma w cell 21 dokładnie to samo
`concurrency = 120`**. Czyli gdyby mój notebook poszedł na slot, też dałby **0.00**. Mój
„naprawiony notebook” naprawiał **łańcuch patchy** (0004 w slocie `duck-extra-02`, co było
realnym problemem — łańcuch C padał na `solver.py:35`), ale nie dotknął ścieżki submisji.

**Lekcja, którą zapisuję jako zasadę:** przepisanie konfiguracji do dokumentu to nie jest jej
zrozumienie. Przy każdej konfiguracji wielowarstwowej trzeba sprawdzić **spójność między
warstwami** (frontend ↔ backend ↔ budżet), nie tylko wierność każdej warstwy z osobna.

---

## 3. Porównanie: v11 kontra moja wersja agenta

### Co v11 ma, a ja nie

| element | stan u mnie | komentarz |
|---|---|---|
| **fix concurrency 120 → 10 na ścieżce submisji** | ❌ **mam ten sam bug** | jedyna zmiana, która decyduje, czy slot daje cokolwiek innego niż 0.00 |
| **`commit(plan)`** z `expect` per krok (`level`, `board_changed`, `step`, `digest`, `cells`), stop na pierwszym rozjeździe, `max_actions=40` | ❌ | odpowiedź na odwrotną korelację `a/call`↔score, którą sam wykryłem (§3 `OCENA-DEEPSEEK-V9.md`); weryfikacja jest darmowa punktowo, bo „tool calls, reasoning steps, retries are NOT counted as actions" |
| **`ARC3_ESCALATE_ACTIONS=60`** → retrodykcja → `model_state`/`model_step` → `check_model()` → `plan()` → `commit()` | ⚠️ mam słabszy `RESET_LEVEL` | mój tylko czyści klatkę; ten każe modelowi **napisać symulator i sprawdzić go** na zarejestrowanych przejściach |
| **model świata pisany przez model** (`model_state`/`model_step`/`model_goal`, `check_model()`, `plan()` BFS) — patch 0002 | ❌ | to jest tor T3 z `LEPSZA-DROGA.md`, jedyny z opublikowanym dowodem na 45+ |
| **pełny patch Franzena**: 24 pliki / 659 896 B z `da-fr/arc-agi-3-solution`, w 2 chunkach (380 000 + 279 896), sha256 sklejki `54768e2f…` zgodny 1:1, `git apply --check` PASS na bundlu r033 | ⚠️ mam 16 plików / 498 799 znaków z ekstrakcji notebooka | mój działa (patrz `OCENA-V10.md` §1 — `%%writefile` dopisuje nową linię), ale jest **częściowy** względem upstream |
| **chunkowanie patcha + sha256 w runtime** | ❌ | dobra inżynieria niezależnie od tego, że diagnoza v10 była błędna |
| **`PROFILE`** (5 wartości: `c45`\|`deep`\|`wide`\|`plan`\|`plan-esc`) | ❌ | mechanizm „jedna zmienna na slot" |
| **naprawa transportu CRLF→LF** w JSON-ie + kanoniczny re-dump (strict parse PASS) | ❌ | bez tego notebook się nie parsuje |

### Co ja mam, a v11 nie

| element | stan w v11 | komentarz |
|---|---|---|
| **`tools/token_economy_model.py`** — wynik LB jako funkcja tok/akcję, z kalibracją sufitu wobec zmierzonego 26.25 | ❌ mają pomiary, nie model | pozwala odpowiedzieć „ile tok/akcję trzeba na 49.85" bez wydawania slotu |
| **`results/budget_triage.tsv`** — `sum_baseline` / budżet dla 25 gier (`fits_all` 2, `marginal` 2, `infeasible` 21) | ❌ | mówi, **w których grach** opłaca się kupować głębokość; przy 394 akcjach dochodzą sb26, r11l, tn36, sc25, su15, lp85 |
| **`tools/calib_probe.py`** — kalibracja ruchów **po hashu efektu**, wszystkie 25 gier w 0.5–8 s | ❌ | odblokowała ft09 (288/4096 responsywnych, wszystkie dokładnie 38 px) i obaliła kalibrację po centroidach |
| **`arc3_search.py`** — search na **prawdziwym silniku** (BFS/beam, `deepcopy` 16.9 ms, `level_reset()` 1.82 ms) | ⚠️ mają `plan()` BFS, ale **w modelu napisanym przez LLM** | różnica zasadnicza: mój search nie wymaga, żeby model umiał napisać symulator; ich wymaga — i to jest jedyna nieusunięta niewiadoma |
| **twierdzenie o capie + warunek `a ≤ 0.9325·b`** zweryfikowany z oficjalną metodologią RHAE | ⚠️ mają formułę odtworzoną co do 0.0000 | zbieżne; moja korekta warunku (z 1.0724 na 0.9325) jest w `FAKTY` |
| **`tests/test_arc3_level_budget.py`** — 16 testów (14 passed + 2 skipped) | ✅ mają 12/12 dla `commit()` | różne mechanizmy, oba przetestowane |

### Co moje, a jest **w** v11

| element | jak wszedł |
|---|---|
| **`arc3_level_budget.py`** — cap tokenów na poziom 45k + limit resetów + `KEEP_GOING`/`RESET_LEVEL`/`ABANDON` | jako `duck-extra-02.patch` (`0004-standalone`), **zastępując** ich 0003 — dokładnie tak, jak rekomendowałem w `PATCH-0004-I-SEARCH.md` §3 po padzie łańcucha C na `solver.py:35`. W opisie submisji 57629847 widnieje `level-token-cap 45k` |
| **roster probe** (sygnatury pierwszej ramki per run) | `OCENA-V11-ARENA.md`: „`ARC3_SMOKE_OK` gate i **sonda rosteru zachowane z v10**". Rekomendacja z `DIAGNOZA-45plus.md` pkt 8 — to jest pomiar, który rozstrzygnie, czy playbook i triage są cokolwiek warte |
| bramka `ARC3_SMOKE_OK` przed submisją | ich własna, ale zgodna z moją rekomendacją |

### Czego słusznie nie ma w v11 (zbieżność z moją korektą)

**Playbooka.** v10 §6 i mój `OCENA-DEEPSEEK-V9.md` §4 doszły niezależnie do tego samego: prywatny
scorecard ma „no repeated game IDs" i „hidden baselines", `official_110()` to **lokalny
symulator**, a eval to 110 gier nieznanych. v10 formułuje to ostrzej i wprost wymienia moje
artefakty: „cała wiedza o konkretnych grach (**playbook, triage budżetu**) jest warta zero".
W v11 playbooka nie ma i słusznie. Triage zostaje jako **rozkład a priori**, nie jako lista celów.

---

## 4. Decyzja slotu: `PROFILE=plan` czy `PROFILE=c45`

Arena odnotowała problem (`OCENA-V11-ARENA.md` pkt 1): `PROFILE=plan` to **fix concurrency +
PIERWSZY pomiar `commit(plan)` w jednym runie** — dwie zmienne, wbrew ich własnej zasadzie.
Ich kontrargument: „Po 0.00 każdy niezerowy wynik i tak jest postępem".

**Rekomenduję `PROFILE="c45"` na najbliższy slot.** Cztery powody:

1. **Nigdy nie mieli czystego pomiaru szybkiej linii.** Wszystkie cztery COMPLETE wyniki
   (0.01, 24.66, 23.94, 26.25) pochodzą z innych konfiguracji. Bez baseline'u szybkiej linii
   **żaden późniejszy delta nie jest interpretowalny** — a to jest dokładnie ta luka, którą
   od dziewięciu dni opisują wszystkie sesje („linia z najszybszym silnikiem nigdy nie została
   zmierzona").
2. **Kalibracja smoke→LB (−2.8 … −6.7 pp) była mierzona na innej konfiguracji.** Musi być
   wyprowadzona od nowa dla szybkiej linii, a do tego potrzebny jest jeden czysty punkt.
3. **Nowa warstwa potrafi KOSZTOWAĆ — mają na to własny dowód:** v6 (world model) **23.94** <
   v2 **24.66**. Jeśli `plan` da np. 22, nie dowiedzą się, czy `commit(plan)` zaszkodził, czy
   fix concurrency dał mniej, niż powinien.
4. **Fixa concurrency nie da się przetestować w smoke** (smoke już ma 10), więc submisja jest
   jedynym testem — a `PROFILE=c45` testuje **dokładnie to**, bez żadnej innej zmiany.

Przy kwocie GPU (30 h/tyg.; dwa runy po 9 h + smoke 2.5 h = **20.5 h**, „trzeci slot może nie
wejść") i przy **bezpieczniku** (commit `cce4b32c`: zero push/submit bez jawnego GO,
auto-decyzja 26.10 zawieszona) realnie dostępne są **~2 sloty**. Więc: `c45` teraz → baseline
i walidacja fixa; `plan` potem → czysty delta `commit(plan)`.

**Jeśli użytkownik uzna, że slot jest tylko JEDEN**, wtedy `plan` jest obronnym hazardem — ale
to hazard, nie pomiar, i trzeba to nazwać po imieniu przed wydaniem GO.

---

## 5. Co v11 uczciwie mówi o sobie (i z czym się zgadzam)

Z ich `README.md`, bez skrótów:

> „This is a candidate, not a demonstrated 50+ solver. The supplied notes report a best prior
> leaderboard result of 26.25, a c45 rerun of **0.00**, and an **unmeasured** v10 `commit(plan)`
> score. Those results do not support a promise of 50+. A live Kaggle run, per-game diagnostics,
> and a score comparison are required before claiming improvement. Public leaderboard score also
> does not guarantee a top-five private leaderboard finish."

oraz o własnej zmianie:

> „It **does not prove** that concurrency alone caused the 0.00 score; the scoring rerun log is
> still needed to establish that."

**Zgadzam się z oboma zdaniami i to jest dobrze postawiona sprawa.** Diagnoza concurrency jest
spójna ze źródłem (§1) i wyjaśnia, dlaczego smoke przechodził a rerun dał 0.00 — ale dopóki log
reruna nie jest dostępny (ich `r085`: „log reruna niedostępny przez API, tylko przeglądarka
usera"), jest to **najlepiej uzasadniona hipoteza**, nie dowód.

**Uwaga transportowa, którą warto pilnować:** notebook v11 przyszedł z **CRLF wewnątrz stringów
JSON**, co wykłada strict-parse. Arena naprawiła to przez `strict=False` → kanoniczny re-dump →
strict PASS, „ZAWARTOŚĆ bez zmian semantycznych". Jeśli zip będzie wgrywany ponownie, **naprawa
musi zostać zachowana**, inaczej notebook się nie sparsuje. To jest ta sama klasa pułapki co
brak końcowej nowej linii w patchu 498 KB — obie są artefaktami transportu, nie logiki.

---

## 6. Podsumowanie różnicy

| | moja wersja | v11 |
|---|---|---|
| **czy w ogóle zapunktuje na rerunie** | ❌ **nie** — `concurrency=120` w cell 21, ten sam bug | ✅ fix na obu dźwigniach (10 + 10) |
| architektura agenta | pętla LLM + mój `RESET_LEVEL` + search na prawdziwym silniku | pętla LLM + **model świata** + `commit(plan)` z weryfikacją + eskalacja 60 |
| kompletność patcha harnessu | 16 plików (działa, częściowy względem upstream) | **24 pliki / 659 896 B**, chunkowany, sha256 1:1, `git apply --check` PASS |
| analiza offline przed slotem | ✅ model ekonomii tokenów, triage budżetu, `calib_probe`, twierdzenie o capie | ⚠️ `v9_metrics` + `verify_offline` (43 sprawdzenia) — mocna weryfikacja, brak modelu |
| testy | 16 (`arc3_level_budget`) | 12 (`commit`) + 43 sprawdzenia offline |
| uczciwość co do niewiadomych | ✅ | ✅ |

**v11 wygrywa w tym, co decyduje o wyniku slotu. Ja wygrywam w tym, co decyduje o tym, który
slot w ogóle warto wydać.** To są komplementarne, nie konkurencyjne warstwy — i dlatego
najlepszy następny ruch to nie „wybrać jedną wersję", tylko wziąć z v11 fix concurrency +
`commit(plan)` + eskalację, a z mojej strony preflight spójności warstw (§1), triage i model
ekonomii do wyboru slotu.
