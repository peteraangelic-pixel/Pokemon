#!/usr/bin/env python3
"""verify_config_liveness.py — warstwa weryfikacji, której NIKT w czterech gałęziach nie ma.

DLACZEGO TEN PLIK ISTNIEJE
--------------------------
Przez całą sesję powtarzała się TA SAMO klasa awarii: **konfiguracja przechodzi wszystkie testy,
a dźwignia nie wykonuje się w punktowanym rerunie**. Zebrane instancje:

  1 `ARC3_PERSISTENT_FUNCTIONS_SCOPE=run` — walidator przyjmuje tylko ("turn","levelup","game"),
    więc `run` degraduje **CICHO** do `levelup`. Log wyglądał jak włączona zmiana.
  2 `concurrency=120` przy `MAXREQ=10` — frontend 12× większy niż backend ⇒ głód slotów ⇒ **0.00**.
  3 `EXPOSE_UNDO` nieustawione ⇒ default `"tufa"` = „advertise ACTION7 verbatim but REJECT
    execution". Agent widział akcję, której harness nie wykonywał.
  4 `official_110()` wzięte za roster submisji — a docstring mówi „**Local** … simulator",
    „reproduced **before submission**".
  5 `commit(plan)` — narzędzie dopisane do opisu, **bez ścieżki wymuszenia**.
  6 `dead_skip` bramkowany `pass_index < 4`, a w rerunie `pass_index` jest **zawsze 0**
    (`n_passes=1`) ⇒ `return False` ⇒ **nigdy nie odpalał**. Testy: **6/6 zielone**, bo mock
    karmił `pass_index` = 1,2,3,4.
  7 guard `GAME_OVER` czyta `game_state.raw.state`, a mock symulatora **nie miał atrybutu `raw`**
    ⇒ guard **milczał**, a test certyfikował ścieżkę, której nie ma.
  8 **alarm `mean_actions_per_call < 1.5`** w v14 (kom. 35) i v15 (kom. 36) — zmierzona baza to
    **4,357** akcji/wywołanie (r019: 474 wywołania / 2065 akcji), więc warunek `< 1.5` **nie może
    nigdy być prawdziwy**. Instrument, który ma powiedzieć, czy batching zadziałał, **jest martwy**.

Wspólny mianownik: **zielone testy modułu NIE dowodzą, że kod wykona się w konfiguracji submisji,
a próg alarmu nie dowodzi, że alarm może odpalić.** Brakująca warstwa to test **OSIĄGALNOŚCI**
i **ŻYWOTNOŚCI INSTRUMENTU**, nie poprawności.

CO TEN SKRYPT SPRAWDZA (4 kontrole, wszystkie na tekście — bez bundla, bez silnika, bez GPU)
-------------------------------------------------------------------------------------------
  L1  ŻYWOTNOŚĆ INSTRUMENTU : każdy próg porównujący ZNANĄ metrykę do liczby — czy gałąź może
                              się wykonać przy zmierzonej bazie?
  L2  DOMYŚLNE WARTOŚCI ENV : każda zmienna env czytana w patchu/notebooku — jej DEFAULT i
                              WALIDATOR; flaguje ustawione-na-legacy oraz nieustawione-wcale
  L3  OSIĄGALNOŚĆ           : warunki sięgające po zmienne STAŁE W RERUNIE (`pass_index`,
                              `n_passes`) przy `n_passes=1`
  L4  SPÓJNOŚĆ MIĘDZYWARSTWOWA: concurrency ≤ MAXREQ; cap na grę vs uczciwy udział;
                              ESCALATE_ACTIONS vs zmierzona długość poziomu

UŻYCIE
------
    python3 verify_config_liveness.py notebook.ipynb [patch1 patch2 ...]
    python3 verify_config_liveness.py v15.ipynb --baseline actions_per_call=4.357
    python3 verify_config_liveness.py *.ipynb --strict     # exit 1 przy choćby jednym FINDING

Wszystkie bazy liczbowe są w stałej BASELINES i mają źródło w komentarzu. **Nadpisuj je przez
--baseline, jeśli masz świeższy pomiar — skrypt nigdy nie zgaduje, tylko porównuje.**
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# ZMIERZONE BAZY. Każda ma źródło; żadna nie jest założeniem.
# ---------------------------------------------------------------------------
BASELINES: dict[str, float] = {
    # r019: 474 wywołania modelu / 2065 akcji (trzy sesje domknięte co do jednostki)
    "actions_per_call": 4.357,
    # r085: 2126 akcji / 10 gier (surowy benchmark.json, roster_probe.jsonl event=end)
    "actions_per_game": 212.6,
    # r085: 6-9 poziomów na grę => 212.6 / 7.5
    "actions_per_level": 28.3,
    # r019: 3664.6 tok/wywołanie / 4.357 akcji
    "tok_per_action": 841.2,
    # r085 mediana (Gemma MEGA-CONFIG); r019 agregat 841.2 — dwie różne definicje, obie podane
    "tok_per_action_median": 647.0,
    # mój pomiar tools/parse_serve_log.py na r085/output-pick/serve.log
    "ms_per_token": 17.2,
    "kv_token_usage_mean": 0.6042,
    "gen_throughput": 663.0,
    # Gemma MEGA-CONFIG §2.2 z komórki 25 v13.1: 32400 s / (110/10) fal
    "notebook_budget_s": 32400.0,
    "roster_games": 110.0,
    "concurrency": 10.0,
    "waves": 11.0,
    "fair_share_s_per_game": 2945.0,
    "configured_cap_s_per_game": 31920.0,   # 532 * 60
}

# progi alarmów w notebookach: (nazwa metryki w kodzie, klucz w BASELINES)
METRIC_ALIASES = {
    "actions_per_call": "actions_per_call",
    "mean_actions_per_call": "actions_per_call",
    "_acpc": "actions_per_call",
    "tok_per_action": "tok_per_action",
    "mean_tok_per_action": "tok_per_action",
    "a/call": "actions_per_call",
}

# ZMIERZONY rozkład `base_actions_per_level` (ludzki baseline na poziom) z SUROWEGO
# `r093-kernel_output_pick/output-pick/benchmark.json` (v11, 10 gier, 69 poziomów).
# To jest właściwe odniesienie dla ESCALATE_ACTIONS — NIE "akcje na poziom" agenta,
# bo dyrektywa mówi modelowi „przestań próbować", a to jest przedwczesne dokładnie wtedy,
# gdy agent jest jeszcze W TEMPIE człowieka.
# min 6 | mediana 72 | średnia 104,0 | max 578 | p10=26 p25=36 p50=72 p75=115 p90=208
BASE_ACTIONS_PER_LEVEL_R093 = [
    29, 54, 85, 300, 208, 113, 59, 102, 67, 98, 324, 578, 78, 175, 179, 230, 96, 54, 67, 28,
    109, 51, 51, 33, 132, 326, 22, 123, 73, 84, 96, 192, 186, 30, 111, 203, 26, 500, 237, 20,
    89, 106, 54, 162, 38, 86, 83, 36, 6, 32, 83, 143, 50, 22, 42, 26, 115, 36, 31, 8, 40, 41,
    32, 72, 26, 40, 30, 55, 62,
]
# Niezależna replikacja pomiaru Gemmy (r085, 32 ukończone poziomy) na r093 (27 ukończonych):
#   próg 10 -> Gemma 31/32 = 96,9 %  | mój pomiar 26/27 = 96,3 %   <-- ZGODNE co do 0,6 pp
#   próg 20 -> Gemma ~25/32 = 78 %   | mój pomiar 25/27 = 92,6 %
#   próg 60 -> Gemma 7/32 = 22 %     | mój pomiar 10/27 = 37,0 %
# Zgodność przy progu 10 jest niemal dokładna; przy 20 i 60 rozjeżdża się, bo to inne runy
# i Gemma dodatkowo warunkuje na „agent był na tempie". OZNACZONE, nie uśredniane.


# Zmierzone LICZBY WSTRZYKNIĘĆ dyrektywy eskalacyjnej — to jest wskaźnik OPERATYWNY
# (koszt to tokeny, nie sama przedwczesność). Σ floor(akcje_poziomu / próg) po 69 poziomach
# z surowego r093 benchmark.json. Suma akcji agenta = 2315, suma baseline = 7175.
#   próg | wstrzyknięć | % sumy akcji | przedwczesnych (a_k <= b_k)
#     10 |     211     |    9,1 %     |   22
#     20 |      96     |    4,1 %     |   18
#     30 |      58     |    2,5 %     |   10
#     60 |      21     |    0,9 %     |    7
# REPLIKACJA Gemmy (r085, 32 UKOŃCZONE poziomy): 10 -> 154 | 20 -> 60 | 60 -> 12 | względny -> 8.
# Stosunki: Gemma 154/60 = 2,57 i 60/12 = 5,0; moje 211/96 = 2,20 i 96/21 = 4,57 — ZGODNE.
# Moje liczby są na 69 poziomach (vs 32) i są DOLNYM ograniczeniem, bo akcje na poziomach
# nieukończonych są ucięte przez koniec biegu, nie przez ukończenie poziomu.
INJECTIONS_R093 = {10: 211, 20: 96, 30: 58, 60: 21}
INJECTIONS_GEMMA_R085 = {10: 154, 20: 60, 60: 12}
AGENT_ACTIONS_SUM_R093 = 2315
BASELINE_ACTIONS_SUM_R093 = 7175


def premature_rate(threshold: int, baselines_list=None) -> tuple[float, int, int]:
    """Frakcja poziomów, na których dyrektywa eskalacyjna odpala PRZED ludzkim baseline'em."""
    vals = baselines_list or BASE_ACTIONS_PER_LEVEL_R093
    n = len(vals)
    k = sum(1 for v in vals if v > threshold)
    return (k / n if n else float("nan")), k, n


# zmienne, których wartość jest STAŁA w punktowanym rerunie
CONST_IN_RERUN = {
    "pass_index": 0,      # n_passes=1 => zawsze 0 (dowód: komórka 25 v13.1, benchmark.json r085/r093)
    "n_passes": 1,        # j.w.
}

# zmienne env z legacy defaultem, który MILCZĄCO zmienia zachowanie
KNOWN_LEGACY_DEFAULTS = {
    "EXPOSE_UNDO": ("tufa", "advertise ACTION7 verbatim but REJECT execution (legacy)"),
    "ARC3_PERSISTENT_FUNCTIONS_SCOPE": ("levelup", "walidator: turn|levelup|game; 'run' degraduje cicho"),
    "ARC3_WINPATH": ("0", "stock behaviour — to default POPRAWNY (jawnie gate'owany)"),
    "ARC3_LEVEL_TOKEN_CAP": ("0", "0 = off — default poprawny"),
    "ARC3_ESCALATE_ACTIONS": ("60", "przy ~28 akcjach/poziom próg 60 NIE ODPALA NIGDY"),
    "ARC3_DEAD_MIN_PASS": ("4", "przy pass_index=0 w rerunie warunek jest zawsze prawdziwy => dead_skip martwy"),
    "ARC3_DEAD_MIN_PASSES": ("3", "licznik per base_key; nie osiągnie 3, jeśli każda gra występuje RAZ"),
    "ARC3_OPENER_COMMIT_HINT": ("0/False", "batching na openerze WYŁĄCZONY domyślnie"),
    "ARC3_MAX_ACTIVE_STREAMS": ("10", "backend; concurrency NIE MOŻE być większe"),
}


def notebook_sources(path: str) -> list[tuple[int, str]]:
    nb = json.loads(Path(path).read_text(encoding="utf-8"))
    out = []
    for i, c in enumerate(nb.get("cells", [])):
        if c.get("cell_type") == "code":
            out.append((i, "".join(c.get("source", []))))
    return out


# ---------------------------------------------------------------------------
# L1 — żywotność instrumentu
# ---------------------------------------------------------------------------
# łapie: `if _acpc and _summary["mean_actions_per_call"] < 1.5:`
THRESHOLD_RX = re.compile(
    r'(?P<metric>[A-Za-z_][\w"\'\[\]\.]*?(?:actions_per_call|tok_per_action|a/call))'
    r'[^\n]{0,40}?(?P<op><|<=|>|>=|==)\s*(?P<num>\d+(?:\.\d+)?)'
)


def check_instrument_liveness(cells, patch_texts, baselines):
    f = []
    seen = set()
    for idx, src in cells:
        for ln_no, line in enumerate(src.splitlines(), 1):
            for m in THRESHOLD_RX.finditer(line):
                raw = m.group("metric")
                key = None
                for alias, k in METRIC_ALIASES.items():
                    if alias in raw:
                        key = k
                        break
                if key is None:
                    continue
                op, num = m.group("op"), float(m.group("num"))
                base = baselines.get(key)
                if base is None:
                    continue
                fires = {"<": base < num, "<=": base <= num,
                         ">": base > num, ">=": base >= num,
                         "==": base == num}[op]
                if not fires:
                    stripped = line.strip()
                    # raportujemy TYLKO warunek, nie print() cytujący ten sam próg w tekście
                    if stripped.startswith(("print(", "#")) and " if " not in stripped:
                        continue
                    key_id = (raw.strip(), op, num)
                    if key_id in seen:
                        continue
                    seen.add(key_id)
                    f.append({
                        "kontrola": "L1 ŻYWOTNOŚĆ INSTRUMENTU",
                        "ważność": "KRYTYCZNA",
                        "komórka": idx, "linia": ln_no,
                        "kod": line.strip()[:150],
                        "problem": (f"próg `{raw.strip()} {op} {num}` NIE MOŻE SIĘ WYKONAĆ: "
                                    f"zmierzona baza {key} = {base}"),
                        "skutek": "alarm nigdy nie odpali ⇒ brak sygnału, czy dźwignia zadziałała",
                        "naprawa": (f"ustaw próg względem bazy {base} (np. `{op} {round(base*0.9,2)}` "
                                    f"dla regresji albo drukuj wartość i porównuj z {base})"),
                    })
    return f


# ---------------------------------------------------------------------------
# L2 — domyślne wartości env i walidatory
# ---------------------------------------------------------------------------
ENV_GET_RX = re.compile(
    r'os\.environ\.get\(\s*["\'](?P<name>[A-Z0-9_]+)["\']\s*(?:,\s*(?P<default>[^)]{0,40}))?\)'
)
ENV_SET_RX = re.compile(r'os\.environ\[\s*["\'](?P<name>[A-Z0-9_]+)["\']\s*\]\s*=')
VALIDATOR_RX = re.compile(
    r'(?P<name>[A-Z0-9_]+)["\']?\s*(?:,\s*["\']?[A-Za-z0-9_]+["\']?)?\s*\)\s*else\s*'
)


def check_env_defaults(cells, patch_texts, baselines):
    set_in_nb = set()
    for _, src in cells:
        for m in ENV_SET_RX.finditer(src):
            set_in_nb.add(m.group("name"))
        # też dict wariantu:  "ARC3_X": "1"
        for m in re.finditer(r'["\'](ARC3_[A-Z0-9_]+|EXPOSE_UNDO)["\']\s*:', src):
            set_in_nb.add(m.group(1))

    read_anywhere = {}
    for _, src in cells:
        for m in ENV_GET_RX.finditer(src):
            read_anywhere.setdefault(m.group("name"), (m.group("default") or "").strip())
    for ptext in patch_texts:
        for m in ENV_GET_RX.finditer(ptext):
            read_anywhere.setdefault(m.group("name"), (m.group("default") or "").strip())

    f = []
    for name, default in sorted(read_anywhere.items()):
        legacy = KNOWN_LEGACY_DEFAULTS.get(name)
        if legacy is None:
            continue
        leg_default, why = legacy
        if name in set_in_nb:
            continue  # ustawiona jawnie — OK
        f.append({
            "kontrola": "L2 DOMYŚLNA WARTOŚĆ ENV",
            "ważność": "WYSOKA" if name in ("EXPOSE_UNDO", "ARC3_ESCALATE_ACTIONS",
                                            "ARC3_OPENER_COMMIT_HINT") else "INFO",
            "komórka": "-", "linia": "-",
            "kod": f'os.environ.get("{name}", {default or leg_default})',
            "problem": f"`{name}` NIE JEST ustawiona w notebooku ⇒ działa default `{leg_default}`",
            "skutek": why,
            "naprawa": f"ustaw `{name}` jawnie w komórce wariantu albo udokumentuj, że default jest zamierzony",
        })
    return f


# ---------------------------------------------------------------------------
# L3 — osiągalność: warunki sięgające po zmienne stałe w rerunie
# ---------------------------------------------------------------------------
def check_reachability(cells, patch_texts, baselines):
    f = []
    for idx, src in cells:
        for ln_no, line in enumerate(src.splitlines(), 1):
            for var, const in CONST_IN_RERUN.items():
                if not re.search(rf'\b{var}\b', line):
                    continue
                if not re.search(rf'\b{var}\b[^\n]{{0,40}}(?:<|<=|>|>=|==|!=)', line) and \
                   not re.search(rf'(?:<|<=|>|>=|==|!=)[^\n]{{0,20}}\b{var}\b', line):
                    continue
                if "TRUE_SUBMISSION" in src or "n_passes" in src:
                    f.append({
                        "kontrola": "L3 OSIĄGALNOŚĆ",
                        "ważność": "KRYTYCZNA",
                        "komórka": idx, "linia": ln_no,
                        "kod": line.strip()[:150],
                        "problem": (f"warunek sięga po `{var}`, która w rerunie jest STAŁA = {const} "
                                    f"(bo `n_passes=1`)"),
                        "skutek": "gałąź może być nieosiągalna ⇒ dźwignia martwa przy zielonych testach",
                        "naprawa": "zaasertować osiągalność: przy TRUE_SUBMISSION i n_passes=1, "
                                   "czy ten kod w ogóle zostanie wykonany?",
                    })
    return f


# ---------------------------------------------------------------------------
# L4 — spójność międzywarstwowa
# ---------------------------------------------------------------------------
def check_cross_layer(cells, patch_texts, baselines):
    f = []
    joined = "\n".join(s for _, s in cells)

    # 4a concurrency vs MAXREQ / MAX_ACTIVE_STREAMS
    # UWAGA na dwa źródła fałszywych pozytywów, oba poprawione po pierwszym uruchomieniu:
    #   (i)  "MAXREQ=10" występuje w notebookach TYLKO W KOMENTARZACH — trzeba je odrzucić
    #   (ii) os.environ.get("ARC3_MAX_ACTIVE_STREAMS", 0) to DEFAULT, nie wartość skonfigurowana
    lines = [ln for ln in joined.splitlines() if not ln.strip().startswith("#")]
    code = "\n".join(lines)
    conc = re.findall(r'(?<!TRUE_)(?<!_)\bconcurrency\s*=\s*(\d+)', code)
    conc += re.findall(r'"ARC3_TRUE_CONCURRENCY"\s*,\s*"(\d+)"', code)
    # backend: tylko JAWNE ustawienie (przypisanie do env albo wpis w dict wariantu)
    streams = re.findall(r'os\.environ\[\s*["\']ARC3_MAX_ACTIVE_STREAMS["\']\s*\]\s*=\s*["\']?(\d+)', code)
    streams += re.findall(r'"ARC3_MAX_ACTIVE_STREAMS"\s*:\s*"(\d+)"', code)
    streams += re.findall(r'^\s*MAXREQ\s*=\s*(\d+)', code, re.MULTILINE)
    if conc and streams:
        c = max(int(x) for x in conc)
        b = min(int(x) for x in streams)
        if c > b:
            f.append({
                "kontrola": "L4 SPÓJNOŚĆ MIĘDZYWARSTWOWA",
                "ważność": "KRYTYCZNA", "komórka": "-", "linia": "-",
                "kod": f"concurrency={c}, MAXREQ={b}",
                "problem": f"frontend ({c}) > backend ({b}) ⇒ głód slotów",
                "skutek": "dokładnie ten mechanizm dał 0.00 w ref 57629847",
                "naprawa": f"assert concurrency <= {b}",
            })
    elif conc and not streams:
        f.append({
            "kontrola": "L4 SPÓJNOŚĆ MIĘDZYWARSTWOWA",
            "ważność": "INFO", "komórka": "-", "linia": "-",
            "kod": f"concurrency={max(int(x) for x in conc)}, backend nieznany",
            "problem": "nie znalazłem JAWNIE ustawionego ARC3_MAX_ACTIVE_STREAMS/MAXREQ w kodzie "
                       "(występuje tylko w komentarzach albo jako default `.get(..., 0)`)",
            "skutek": "spójności frontend/backend NIE DA SIĘ zweryfikować statycznie",
            "naprawa": "dodać do preflightu: `_be = int(os.environ.get('ARC3_MAX_ACTIVE_STREAMS', CFG['MAXREQ'])); "
                       "assert bm.solver.concurrency <= _be`",
        })

    # 4b cap na grę vs uczciwy udział
    cap = baselines["configured_cap_s_per_game"]
    fair = baselines["notebook_budget_s"] * baselines["concurrency"] / baselines["roster_games"]
    ratio = cap / fair
    if ratio > 1.3:
        f.append({
            "kontrola": "L4 SPÓJNOŚĆ MIĘDZYWARSTWOWA",
            "ważność": "INFO", "komórka": "-", "linia": "-",
            "kod": f"max_runtime_s_per_game={cap:.0f} vs uczciwy udział {fair:.0f}",
            "problem": f"cap jest {ratio:.2f}× powyżej uczciwego udziału",
            "skutek": "cap NIGDY NIE WIĄŻE — wiąże liczba fal (110/10 = 11). Podnoszenie go nic nie daje",
            "naprawa": "nie ruszać; sonda budżetu v14/v15 loguje ten iloraz",
        })

    # 4c ESCALATE_ACTIONS — dwie odrębne awarie, obie mierzone na base_actions_per_level z r093
    esc = re.findall(r'ESCALATE_ACTIONS\s*=\s*(\d+)', joined)
    if esc:
        e = int(esc[-1])
        apl = baselines["actions_per_level"]
        rate, k, n = premature_rate(e)

        # (a) próg wyższy niż cały poziom -> dyrektywa NIE ODPALA NIGDY
        if e > apl * 1.5:
            f.append({
                "kontrola": "L4 SPÓJNOŚĆ MIĘDZYWARSTWOWA",
                "ważność": "KRYTYCZNA", "komórka": "-", "linia": "-",
                "kod": f"ESCALATE_ACTIONS={e} vs ~{apl:.0f} akcji/poziom (agent)",
                "problem": f"próg ({e}) PRZEKRACZA całą typową długość poziomu (~{apl:.0f})",
                "skutek": "dyrektywa eskalacyjna NIE ODPALA SIĘ NIGDY ⇒ commit(plan) bez presji "
                          "(dokładnie stan v13.1 przy progu 60)",
                "naprawa": f"ustaw próg wyraźnie poniżej {apl:.0f}",
            })

        # (b) koszt wstrzyknięć — wskaźnik OPERATYWNY (tokeny, nie sama przedwczesność)
        inj = INJECTIONS_R093.get(e)
        if inj is None:
            lo = min(k for k in INJECTIONS_R093 if k <= e) if any(k <= e for k in INJECTIONS_R093) else None
            inj = INJECTIONS_R093.get(lo) if lo else None
        if inj is not None:
            pct_actions = 100.0 * inj / AGENT_ACTIONS_SUM_R093
            if pct_actions >= 6.0:
                f.append({
                    "kontrola": "L4 SPÓJNOŚĆ MIĘDZYWARSTWOWA",
                    "ważność": "KRYTYCZNA", "komórka": "-", "linia": "-",
                    "kod": (f"ESCALATE_ACTIONS={e} → {inj} wstrzyknięć na 69 poziomach r093 "
                            f"= {pct_actions:.1f} % sumy akcji agenta"),
                    "problem": (f"każde wstrzyknięcie dokłada ~146 tokenów dyrektywy i PROSI O TURĘ "
                                f"MODELARSKĄ (tysiące tokenów). Gemma zmierzyła dla progu 10: "
                                f"**154 wstrzyknięcia = 15,3 % puli tokenów gry**"),
                    "skutek": ("priority gate szereguje gry wg tokenów na poziom "
                               "(priority_pace_reference.json: poziom 1 = 27 tys., fallback 45,9 tys.), "
                               "więc gra, która napompuje tokeny, wpada do GORSZEJ bandy kolejki. "
                               "Przy v13.3 dodatkowo kontrowało opener hint"),
                    "naprawa": (f"próg względny max(20, 1.2 × baseline[poziom]) → 8 wstrzyknięć, "
                                f"0,8 % puli (Gemma, PROPOZYCJA-0007.md — wymaga patcha scaffoldu). "
                                f"Bez patcha: {min(INJECTIONS_R093, key=lambda k: abs(INJECTIONS_R093[k]-40))}"
                                f" i wyżej"),
                })

        # (c) próg niższy niż ludzki baseline -> dyrektywa odpala PRZEDWCZEŚNIE (wskaźnik pomocniczy)
        if rate >= 0.75:
            f.append({
                "kontrola": "L4 SPÓJNOŚĆ MIĘDZYWARSTWOWA",
                "ważność": "WYSOKA",
                "komórka": "-", "linia": "-",
                "kod": f"ESCALATE_ACTIONS={e} vs base_actions_per_level (n={n}, mediana 72, min 6, max 578)",
                "problem": f"przy progu {e} dyrektywa eskalacyjna (tekst: przestań próbować ręcznie, "
                           f"zbuduj model) odpala PRZED ludzkim "
                           f"baseline'em na **{k}/{n} = {100*rate:.1f} %** zmierzonych poziomów",
                "skutek": "każde wstrzyknięcie prosi o turę modelarską (tysiące tokenów). Pomiar Gemmy "
                          "dla progu 10: **154 wstrzyknięcia = 15,3 % puli tokenów gry**; dodatkowo "
                          "priority gate szereguje gry wg tokenów na poziom, więc gra, która napompuje "
                          "tokeny, wpada do gorszej bandy kolejki. Kontrowało też opener hint v13.3",
                "naprawa": "próg WZGLĘDNY `max(20, 1.2 × baseline[poziom])` → pomiar Gemmy: "
                          "**8 wstrzyknięć, 0,8 % puli, 0/32 przedwcześnie**. Wymaga patcha scaffoldu "
                          "(PROPOZYCJA-0007.md Gemmy). Bez patcha: 20 jest kompromisem, nie optimum",
            })

        # niezależna replikacja — zawsze drukowana jako kontekst
        rows = []
        for thr in (10, 20, 60):
            r, kk, nn = premature_rate(thr)
            rows.append(f"{thr}→{kk}/{nn} ({100*r:.0f}%)")
        f.append({
            "kontrola": "L4 SPÓJNOŚĆ MIĘDZYWARSTWOWA",
            "ważność": "INFO", "komórka": "-", "linia": "-",
            "kod": f"ESCALATE_ACTIONS={e}; przedwczesne odpalenie wg progu: " + " | ".join(rows),
            "problem": "—",
            "skutek": "pomiar na base_actions_per_level z r093 (n=69). Replikacja Gemmy (r085, "
                      "32 ukończone): próg 10 → 31/32 = 96,9 % vs mój 26/27 = 96,3 % — ZGODNE",
            "naprawa": "—",
        })
    return f


KONTROLE = [
    ("L1 ŻYWOTNOŚĆ INSTRUMENTU", check_instrument_liveness),
    ("L2 DOMYŚLNA WARTOŚĆ ENV", check_env_defaults),
    ("L3 OSIĄGALNOŚĆ", check_reachability),
    ("L4 SPÓJNOŚĆ MIĘDZYWARSTWOWA", check_cross_layer),
]


def run(notebook: str, patches: list[str], baselines: dict) -> list[dict]:
    cells = notebook_sources(notebook)
    ptexts = []
    for p in patches:
        try:
            ptexts.append(Path(p).read_text(encoding="utf-8", errors="replace"))
        except OSError as exc:
            print(f"  ! nie przeczytałem {p}: {exc}", file=sys.stderr)
    # patche zapisane w komórkach notebooka (write_text('diff --git ...')) też są źródłem
    for _, src in cells:
        if "diff --git" in src:
            ptexts.append(src)
    out = []
    for _, fn in KONTROLE:
        out.extend(fn(cells, ptexts, baselines))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("notebook", help="plik .ipynb do sprawdzenia")
    ap.add_argument("patches", nargs="*", help="pliki .patch (opcjonalnie; notebookowe są brane automatycznie)")
    ap.add_argument("--baseline", action="append", default=[], metavar="NAZWA=WARTOŚĆ",
                    help="nadpisz zmierzoną bazę, np. --baseline actions_per_call=5.1")
    ap.add_argument("--strict", action="store_true", help="exit 1 przy choćby jednym KRYTYCZNYM")
    args = ap.parse_args()

    b = dict(BASELINES)
    for item in args.baseline:
        k, _, v = item.partition("=")
        if k in b:
            b[k] = float(v)
        else:
            print(f"  ! nieznana baza {k!r} — pomijam", file=sys.stderr)

    print(f"=== verify_config_liveness: {args.notebook} ===")
    print("bazy (zmierzone, nie założone):")
    for k in ("actions_per_call", "actions_per_game", "actions_per_level", "tok_per_action",
              "ms_per_token", "kv_token_usage_mean", "gen_throughput", "fair_share_s_per_game",
              "configured_cap_s_per_game"):
        print(f"  {k:32s} = {b[k]}")

    findings = run(args.notebook, args.patches, b)
    if not findings:
        print("\n✅ BRAK USTALEŃ — wszystkie cztery kontrole czyste.")
        return 0

    order = {"KRYTYCZNA": 0, "WYSOKA": 1, "INFO": 2}
    findings.sort(key=lambda x: (order.get(x["ważność"], 9), x["kontrola"]))
    n_crit = sum(1 for f in findings if f["ważność"] == "KRYTYCZNA")
    print(f"\n=== USTALENIA: {len(findings)} (KRYTYCZNE: {n_crit}) ===")
    for i, f in enumerate(findings, 1):
        print(f"\n[{i}] {f['ważność']} · {f['kontrola']} · komórka {f['komórka']} linia {f['linia']}")
        print(f"    kod     : {f['kod']}")
        print(f"    problem : {f['problem']}")
        print(f"    skutek  : {f['skutek']}")
        print(f"    naprawa : {f['naprawa']}")
    print(f"\nRAZEM: {len(findings)} ustaleń, w tym {n_crit} KRYTYCZNYCH.")
    print("Uwaga: ten skrypt sprawdza OSIĄGALNOŚĆ i ŻYWOTNOŚĆ, nie POPRAWNOŚĆ logiki.")
    print("Nie zastępuje verify_v13.py (6/6 patchy na czystym r033) — uzupełnia je o warstwę,")
    print("której tam brakuje: czy dźwignia W OGÓLE wykona się w konfiguracji submisji.")
    return 1 if (args.strict and n_crit) else 0


if __name__ == "__main__":
    sys.exit(main())
