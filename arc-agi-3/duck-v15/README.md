# duck-v15 = duck-v14 (Gemma) + patch 0007 (relative escalation)

Built 2026-10-30 by session `a450b00f` on top of this package's duck-v14
(mirrored unchanged from `Gemma-konkurs`, branch `arena/c4eeb067-gemma-konkurs`).
Two changes, nothing else touched (verified cell-by-cell: only the
ARC3_VARIANT cell, the switch banner, and one inserted writer cell differ):

1. **Patch 0007 implements PROPOZYCJA-0007** (the sketch below in this
   package), which the Gemma session did not ship because it could not
   verify `git apply` against r033. This session has the bundle, so:
   `patches/0007-escalate-relative.patch` - `pc_escalate_at()` pure
   threshold logic in `inference/utils/plan_commit.py`; `ToolAgent`
   takes `base_actions_per_level` (handed over by
   `Solver._make_analyzer` from `taaf.game.Game`); the directive fires
   at `max(ESCALATE_ACTIONS, 1.2 x baseline[level])`, at most
   `ARC3_ESCALATE_MAX_PER_LEVEL` (default 2) times per level.
   Env: `ARC3_ESCALATE_RATE` (1.2), `ARC3_ESCALATE_MAX_PER_LEVEL` (2,
   0 = unlimited). Verified: applies as patch 7/7 on r033, tree
   compiles, plumbing checked by AST, 7 new unit tests.
   **Submission-mode behaviour:** the engine hides baselines
   (`base_actions_per_level is None`), so the relative rule degrades
   to v14's absolute 20 + the per-level cap of 2 - the measurable win
   is local/smoke; the cap is the part that also applies on the rerun.
2. **Kernel slug** is `petersharps/arc3-duck-v15` (note: the inherited
   v14 metadata still pointed at `arc3-duck-v13-2`; fixed here, and
   `code_file` is `arc3-duck-v15.ipynb`).

Verification (offline, this session):
`tools/verify_v15.py --bundle <r033> --tests` ->
**ALL CHECKS PASSED** (7/7 patches, 12 plan-commit + 8 winpath +
7 escalate tests). Rebuild: `tools/build_v15.py` from
`arc3-duck-v14.ipynb`; regenerate patch: `tools/make_patch_0007.py`.

Everything below is the original duck-v14 README.

---

# ARC3 Duck v14

**Baza:** `duck-v13-2` (`6b10853`) z `arena/a450b00f-pokemon`.
**Ten pakiet nie zmienia ani jednego patcha.** Łańcuch `0001/0002/0004/0005/0006`,
`src/base-v11.ipynb` i `playbook.json` są **bajt w bajt** te same co w v13.2, więc ich
`tools/verify_v13.py` (6/6 na czystym r033) stosuje się bez zmian, a playbook dalej daje
14/14 poziomów i 184/184 hashy na prawdziwych grach.

Zmienione są **cztery rzeczy**, każda uzasadniona pomiarem albo usuwająca ryzyko wywalenia
notebooka:

| # | zmiana | dlaczego |
|---|---|---|
| 1 | `ESCALATE_ACTIONS` **10 → 20** | 10 było zgadnięte; na 32 ukończonych poziomach r085 odpala 154× (15,3% puli tokenów gry) i na **31/32** poziomach każe modelowi przestać próbować, gdy ten jest na tempie albo lepszy od ludzkiego baseline'u. Przy 20: 60× (6,0%) |
| 2 | hook sondy rosteru z c45 **owinięty w try/except** | `_orig_play = _S._HarnessGameSession.play` stało **poza** jakimkolwiek try w komórce, która ustawia `bm.solver.*`. Brak atrybutu w innym revision bundla = wyjątek = martwy notebook przed startem |
| 3 | **nowa sonda rosteru** (po biegu, z `bm.game_runs`) | odpowiada na jedyne pytanie, od którego zależy, czy pamięć win-path jest warta 0 czy +5…15: czy roster powtarza bazowe kody gier |
| 4 | **nowa sonda budżetu** (przed biegiem) | cap na grę jest 11× powyżej uczciwego udziału (532 min vs ~48 min przy 110 grach); nikt tego nigdzie nie loguje |

## 1. Skąd liczba 20 (a nie 10 i nie 60)

Dyrektywa eskalacyjna (540 znaków ≈ 146 tokenów) mówi: „stop probing by hand → napisz
`model_state`/`model_step` → `check_model()` → `plan()` → `commit()`". To **przypomnienie,
nie wymuszenie** — `commit()` zostaje opcją modelu. Liczby z r085 (`tools/escalation_audit.py`
w `ARC3/local-lab`, 32 ukończone poziomy):

| próg | wstrzyknięć | tokenów dyrektyw | % puli gry | odpala **przed** ludzkim baseline'em |
|---|---|---|---|---|
| 10 (v13.2) | 154 | 22 330 | **15,3%** | **31/32 poziomów** |
| **20 (v14)** | **60** | 8 760 | 6,0% | ~25/32 |
| 60 (v13.1) | 12 | 1 740 | 1,2% | 7/32 |
| `max(20, 1,2 × baseline[poziom])` | 8 | 1 160 | 0,8% | 0/32 |

Przykłady z v13.2: `cn04/4` dostaje „przestań próbować" po 41 akcjach, gdy człowiek potrzebuje
300; `cn04/5` po 52 przy 208; `m0r0/3` po 94 przy 203.

Dwa powody, dla których to nie jest kosmetyka:
- **kosztowna jest posłuszność, nie tekst.** Każda z 154 zachęt prosi o turę modelarską
  (tysiące tokenów). Jeśli model posłucha co czwartej — ~12 tys. tokenów (8% puli) plus akcje
  na weryfikację modelu.
- **możliwy efekt drugiego rzędu:** w scaffoldzie działa priority gate z referencją tempa
  w tokenach na poziom (`priority_pace_reference.json`, poziom 1 = 27 tys. tokenów, fallback
  45,9 tys.). Gra, która napompuje tokeny, wpada do gorszej bandy kolejki. Hipoteza (nie
  zmierzona): eskalacja @10 sama wypycha grę z kolejki. Sonda nr 4 i tak to pokaże w liczbach.

Wariant docelowy, którego tu **nie ma** (bo wymaga patcha scaffoldu, a ja nie mam r033, żeby
go zweryfikować): próg względny
`on_level > max(20, 1.2 × game_run.base_actions_per_level[level])` → 8 wstrzyknięć na r085,
wszystkie na poziomach, na których run realnie traci punkty. Szkic kodu i instrukcja
weryfikacji: `PROPOZYCJA-0007.md`. **Nie jest** dołączony jako patch, bo nieumnieszczony
`git apply` w submisji jest gorszy niż brak patcha.

## 2. Co mierzą sondy

**Sonda budżetu** (komórka 29, przed `bm.run`): liczba gier, `n_passes`, concurrency, budżet
notebooka, uczciwy udział na grę, skonfigurowany cap i iloraz. Zapisuje
`/kaggle/working/budget_probe.json`, a przy ilorazie > 1,3 drukuje ostrzeżenie. Nic nie zmienia.

Fakt, na którym to stoi: we **wszystkich trzech** zapisanych runach każda gra kończy się
dokładnie na capie — `max(final_wallclock_seconds) == min(...) == 48 / 48 / 90 min`. Gra nie
zatrzymuje się wcześniej, więc cap jest przydziałem akcji (akcje = cap / sekundy na akcję).
Czy priority gate sam pilnuje sprawiedliwego podziału — tego nie wiadomo, bo nikt tego nie
loguje. Sonda to rozstrzyga po jednym przebiegu.

**Sonda rosteru** (komórka 35, po biegu): czyta `bm.game_runs`, zapisuje
`/kaggle/working/roster_probe.jsonl` (jedna linia na run: `game_id`, `base`, poziomy, akcje,
tokeny, `actions_per_call`, `tok_per_action`, wall, score, state) i drukuje werdykt:

```
v14 roster: {"duplicate_bases": 3, "max_repeats": 4, ...}
v14 roster: POWTARZA SIE 3 bazowych gier (do 4x) -> pamiec miedzy wpisami PLACI
```

albo

```
v14 roster: ZADNY bazowy kod sie nie powtarza -> pamiec win-path = 0 pkt
```

Dodatkowo alarm na martwą dźwignię: `actions_per_call < 1,5` → `commit(plan)` praktycznie
nie odpala, czyli jedyna droga do 50+ leży odłogiem.

## 3. Bramka GO/NO-GO na smoke (ten sam slot, ~1 h GPU)

Po przebiegu czytamy **trzy liczby** z komórki 34 (metering v11) i dwóch sond:

| liczba | wartość progowa | co znaczy |
|---|---|---|
| `actions_per_call` | **≥ 1,8** | `commit(plan)` naprawdę wykonuje wiele akcji na turę modelu — to jest mechanizm 226 → ~450 akcji i jedyna droga do 50+ |
| `cap_over_fair` + `runs_with_zero_actions` | cap ≈ udział, zero akcji brak | żaden kawałek rosteru nie jest głodzony |
| `duplicate_bases` | cokolwiek | rozstrzyga, czy pamięć win-path liczy się w prawdziwym scorecardzie |

Jeśli po smoke'u `actions_per_call` stoi na ~1,0 — eskalujemy inaczej (próg względny z
`PROPOZYCJA-0007.md`), a nie podkręcaniem liczby 20 → 10 → 5.

## 4. Uczciwa prognoza

- **v14 nie jest skokiem na 50.** To v13.2 z mierzonym spustem (mniej „przestań próbować"),
  bez ryzyka wywalenia komórki konfiguracyjnej i z przyrządami, które po jednym przebiegu
  rozstrzygają dwie rzeczy blokujące każdą dalszą decyzję.
- Podłoga bez zmian: playbook 2,90 na 25 grach publicznych. Pamięć: 0 albo +5…15 — zależnie
  od sondy. Prognoza rerunu: **26–31**, z @20 raczej górna połowa niż dolna.
- Cap-off +0,4…2,2 i `plan_commit` (niezmierzony) zostają jak w v13.2.

## 5. Budowa i testy

```bash
cd ARC3/duck-v14
python3 tools/build_v14.py                  # -> arc3-duck-v14.ipynb (36 komórek)
python3 tools/test_probes.py                # sondy na stubach: budżet, roster, wyjątki
PYTHONPATH=<arcengine> python3 -m pytest -q tests/test_winpath.py   # 8/8
```

Build jest deterministyczny: `tools/build_v14.py` najpierw odtwarza v13.2 **ich własnym**
`tools/build_v13.py` (co do bajtu, sprawdzone: md5 `2886fde0ecc3…`) i dopiero potem nanosi
cztery zmiany. Diff v14 vs v13.2 to **dokładnie** komórki 2, 25, 29 i nowa 35 — nic więcej.

`tests/test_plan_commit.py` nie uruchamia się w tym pakiecie (importuje
`inference.utils.plan_commit` ze scaffoldu, nie z pakietu) — ich `verify_v13.py` robi to na
czystym r033.

## 6. Czego tu nie ma (świadomie)

- Bez nowych patchy w łańcuchu (zero ryzyka przy `git apply`).
- Bez zmiany `playbook.json` (md5 `e2d86b1e07fe`).
- Bez zmiany `bm.n_passes` / `max_runtime_s_per_game` — sonda najpierw, decyzja potem.
- Bez `soft_end_time` w trybie TRUE (ich kod ustawia go tylko offline). To zostaje jako
  osobna, ryzykowna zmiana do rozważenia, gdy sonda pokaże głodzenie rosteru.
