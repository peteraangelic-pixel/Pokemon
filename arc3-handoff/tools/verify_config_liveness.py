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

  9 **próg względny `max(20, 1.2 x base_actions_per_level[level])`** — patch 0007 (a450 `8d96c68f`)
    i 0008 (Smak `f04c3e73`, Gemma). `taaf/game.py` L254-255, L439-440, L448 i L471-472: w trybie
    submisji silnik **UKRYWA** baseline (`None`). Wtedy `if b > 0` nie zachodzi ⇒ **cała dźwignia
    wraca do stałego flooru 20**. Pomiar „8 wstrzyknięć, 0 przedwczesnych" dotyczy **SMOKE'A**.
    To TA SAMA FORMA co #6: mock/smoke karmi wartości, których rerun **nigdy nie wyprodukuje**.
 10 **bramka `NO-GO if mean_score <= 29.02`** + `depth_budget_used_pct` (kom. 35/37/38 w v15-a450,
    v13.4, v13.5, v16). `_compute_final_score` zwraca **0.0** gdy baseline jest `None`
    (`taaf/game.py` L391-392), a `actions_need = sum(base_actions_per_level or []) = 0`.
    ⇒ w KAŻDYM prawdziwym submicie log drukuje `score=0.00`, `21200.0% of a full clear`
    i pewne siebie **`NO-GO`**. To **NOWA PODKLASA**: instrument nie milczy (jak #8) — **KŁAMIE**.

Wspólny mianownik: **zielone testy modułu NIE dowodzą, że kod wykona się w konfiguracji submisji,
a próg alarmu nie dowodzi, że alarm może odpalić.** Brakująca warstwa to test **OSIĄGALNOŚCI**
i **ŻYWOTNOŚCI INSTRUMENTU**, nie poprawności.

DWIE PODKLASY MARTWEGO INSTRUMENTU (rozróżnienie z 30.10):
  CICHO-MARTWY (#8)  — próg poniżej bazy ⇒ gałąź nigdy się nie wykona ⇒ log MILCZY.
                       Skutek: nie dowiesz się, czy dźwignia zadziałała.
  GŁOŚNO-MYLĄCY (#10)— wejście jest zerem z konstrukcji w submisji ⇒ gałąź wykonuje się ZAWSZE
                       i drukuje fałszywy werdykt. Skutek: dowiesz się czegoś, co NIE JEST PRAWDĄ.
                       **Groźniejszy**, bo produce zaufanie: `score=0.00` + `NO-GO` wygląda jak
                       prawdziwa porażka, a prawdziwą porażkę 0.00 już raz mieliśmy (57629847).

CO TEN SKRYPT SPRAWDZA (7 kontroli, wszystkie na tekście — bez bundla, bez silnika, bez GPU)
-------------------------------------------------------------------------------------------
  L1  ŻYWOTNOŚĆ INSTRUMENTU : każdy próg porównujący ZNANĄ metrykę do liczby — czy gałąź może
                              się wykonać przy zmierzonej bazie?                     → łapie #8
  L2  DOMYŚLNE WARTOŚCI ENV : każda zmienna env czytana w patchu/notebooku — jej DEFAULT i
                              WALIDATOR; flaguje ustawione-na-legacy oraz nieustawione-wcale
  L3  OSIĄGALNOŚĆ           : warunki sięgające po zmienne STAŁE W RERUNIE (`pass_index`,
                              `n_passes`) przy `n_passes=1`                           → łapie #6
  L4  SPÓJNOŚĆ MIĘDZYWARSTWOWA: concurrency ≤ MAXREQ; cap na grę vs uczciwy udział;
                              ESCALATE_ACTIONS vs zmierzona długość poziomu
  L5  WEJŚCIE UKRYTE W SUBMISJI: czy pakiet zależy od `base_actions_per_level` (ukrytej
                              w rerunie) i czy ma ŻYWY zamiennik kalibrujący na
                              `actions_per_level` (taaf/game.py L569: inkrement po każdej akcji)
                              + czy ma sondę, która to ROZSTRZYGNIE w biegu          → łapie #9
  L6  INSTRUMENT GŁOŚNO-MYLĄCY: bramka/wskaźnik, którego wejście jest ZEREM Z KONSTRUKCJI
                              w submisji ⇒ zawsze odpala z fałszywym werdyktem       → łapie #10
  L7  WDROŻENIOWOŚĆ PAKIETU : `code_file` z kernel-metadata.json istnieje? slug należy
                              do TEGO pakietu, czy do cudzego? (wymaga --package DIR)

UŻYCIE
------
    python3 verify_config_liveness.py notebook.ipynb [patch1 patch2 ...]
    python3 verify_config_liveness.py v16.ipynb --package ARC3/duck-v16 --strict
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
                "naprawa": "próg WZGLĘDNY `max(20, 1.2 × baseline[poziom])` daje 8 wstrzyknięć / 0,8 % puli / "
                      "0 przedwczesnych — ALE JEST MARTWY W RERUNIE, bo silnik ukrywa baseline "
                      "(taaf/game.py L254-255, L439-440, L448, L471-472; patrz L5). ŻYWY zamiennik: "
                      "SELF-PACE `clamp(1.5 × mediana(actions_per_level[:ukończone]), 20, 120)` + cap 2 "
                      "→ 22 nudge / 14 przedwczesnych / 2,27 % puli na r085 i 22 / 13 na r093 (moja "
                      "replikacja; r085 odtwarza tabelę Gemmy co do jednej, docstring 0009 mówiący 27/16 "
                      "NIE odtwarza się w 192 kombinacjach). Bez self-pace: 20 + cap 2 = 42 / 26 / 4,33 %"
        })
    return f


# ---------------------------------------------------------------------------
# L5 — WEJŚCIE UKRYTE W SUBMISJI
# ---------------------------------------------------------------------------
# ŹRÓDŁO PIERWOTNE: taaf/game.py z r033-recon-bundle (688 linii), CZTERY miejsca:
#   L254-255 docstring GameRun : "base_actions_per_level is None when the engine
#                                 hides baselines (e.g. submission mode)"
#   L439-440 docstring Game    : "base_actions_per_level is None when the engine
#                                 hides baselines (submission mode)"
#   L448     pole              : base_actions_per_level: list[int] | None =
#                                 field(default=None, init=False)
#   L471-472 komentarz asercji : "may legitimately be None (R11.02: engine hides
#                                 baselines in submission mode)"
#   L391-392 _compute_final_score: "if self.base_actions_per_level is None ... return 0.0"
# CO JEST ŻYWE W SUBMISJI (też taaf/game.py):
#   L569 execute_action : self.game_run.actions_per_level[level_before] += 1
#                         -> licznik ROSNIE PO KAŻDEJ AKCJI, w trakcie biegu
#   L571-572            : levels_completed aktualizowane zaraz po tym
#   L258-259 docstring  : "Invariant: sum(actions_per_level) == len(history)"
# STAN EMPIRYCZNY (sprawdzone przeze mnie 30.10): 0 z 5 dostępnych benchmark.json
#   (r050, r085, r093 == r108 ten sam blob 90173adb, r110, r118) pokazuje null.
#   Wszystkie mają baseline PRESENT 10/10, bo wszystkie to SMOKE.
#   => warunek "hidden" jest UDOKUMENTOWANY W ŹRÓDLE, ale NIGDY NIE ZAOBSERWOWANY.
#      Rozstrzygnie go dopiero pierwszy submit z sondą widoczności baseline.
HIDDEN_IN_SUBMISSION = ("base_actions_per_level",)
ALIVE_IN_SUBMISSION = ("actions_per_level", "levels_completed", "history")


def check_hidden_inputs(cells, patch_texts, baselines):
    '''Czy pakiet zależy od wejścia, którego w submisji NIE MA — i czy ma żywy zamiennik?'''
    f = []
    nb = "\n".join(s for _, s in cells)
    joined = nb + "\n" + "\n".join(patch_texts)
    if not any(re.search(rf"\b{v}\b", joined) for v in HIDDEN_IN_SUBMISSION):
        return f

    # Reguła względna występuje w DWÓCH instalacjach: Smak/Gemma bramkują ją env
    # (ARC3_ESCALATE_RELATIVE), a450 `8d96c68f` ma ją ZAWSZE włączoną i czyta
    # self._arc3_base_actions przez czystą funkcję pc_escalate_at w plan_commit.py.
    # Kluczowanie tylko po nazwie env PRZEGAPIA tę drugą — więc szukam wzorca, nie nazwy.
    relative_on = bool(re.search(
        r"ARC3_ESCALATE_RELATIVE|_arc3_base_actions|pc_escalate_at|_escalate_threshold"
        r"|base_actions\[idx\]|base_actions_per_level\[", joined))
    # Żywy zamiennik = kalibracja na actions_per_level (taaf/game.py L569: rośnie po każdej akcji)
    substitute = bool(re.search(r"ARC3_ESCALATE_SELF_PACE|_escalate_self_pace", joined))

    if relative_on and not substitute:
        f.append({
            "kontrola": "L5 WEJŚCIE UKRYTE W SUBMISJI",
            "ważność": "KRYTYCZNA", "komórka": "-", "linia": "-",
            "kod": "ARC3_ESCALATE_RELATIVE=1 bez ARC3_ESCALATE_SELF_PACE=1",
            "problem": "próg względny czyta base_actions_per_level[level], a taaf/game.py L254-255, "
                       "L439-440, L448 i L471-472 mówią, że w trybie submisji silnik ją UKRYWA (None). "
                       "Wtedy `if b > 0` nie zachodzi i funkcja zwraca stały floor.",
            "skutek": "dźwignia MARTWA w jedynym biegu, który się liczy, BEZ żywego zamiennika: "
                      "rerun wykona floor 20 + cap 2 = 42 nudge / 26 przedwczesnych / 4,33 % puli "
                      "(r085; mój niezależny r093: 39 / 23 / 4,02 %). Cały pomiar '8 wstrzyknięć, "
                      "0 przedwczesnych' dotyczy SMOKE'A, nie submisji.",
            "naprawa": "dodać patch self-pace kalibrujący na actions_per_level (ŻYWE: taaf/game.py "
                       "L569 inkrementuje go po każdej akcji) — zmierzone 22 nudge / 14 przedwczesnych "
                       "na r085 i 22 / 13 na r093, czyli ~2× taniej i ~2× mniej przedwczesnych niż 20+cap2",
        })
    elif relative_on and substitute:
        f.append({
            "kontrola": "L5 WEJŚCIE UKRYTE W SUBMISJI",
            "ważność": "INFO", "komórka": "-", "linia": "-",
            "kod": "ARC3_ESCALATE_RELATIVE=1 + ARC3_ESCALATE_SELF_PACE=1",
            "problem": "—",
            "skutek": "poprawnie: gałąź względna jest bezwładna w rerunie, a `return paced or floor` "
                      "przekazuje sterowanie self-pace. UWAGA na odwrotność: w SMOKE baseline jest "
                      "widoczny, więc smoke ĆWICZY GAŁĄŹ WZGLĘDNĄ, A NIE TĘ, KTÓRA PÓJDZIE DO RERUNU.",
            "naprawa": "—",
        })

    probe = re.search(r"baselines_hidden|baseline_available|baseline[\"']?\s*[:=]\s*[\"']?(hidden|yes|no)",
                      nb)
    if not probe:
        f.append({
            "kontrola": "L5 WEJŚCIE UKRYTE W SUBMISJI",
            "ważność": "WYSOKA", "komórka": "-", "linia": "-",
            "kod": "brak sondy widoczności baseline (baselines_hidden / baseline_available)",
            "problem": "żaden z 5 dostępnych benchmark.json (r050, r085, r093, r110, r118) nie pokazuje "
                       "base_actions_per_level = null — wszystkie to smoke'i. Nikt więc NIGDY nie "
                       "zaobserwował warunku, na którym opiera się cała argumentacja.",
            "skutek": "po submisji nie dowiesz się, czy próg względny był żywy, czy martwy — "
                      "a od tego zależy, czy self-pace w ogóle był potrzebny",
            "naprawa": "logować per grę `\"baseline\": \"hidden\" if run.base_actions_per_level is None "
                       "else len(...)` i wydrukować werdykt zbiorczy",
        })
    return f


# ---------------------------------------------------------------------------
# L6 — INSTRUMENT GŁOŚNO-MYLĄCY (nowa podklasa: nie milczy, tylko KŁAMIE)
# ---------------------------------------------------------------------------
# Różnica wobec L1: L1 łapie próg, który NIGDY się nie wykona (cicho-martwy).
# L6 łapie miernik, który WYKONA SIĘ ZAWSZE i wydrukuje pewny siebie fałsz,
# bo jego wejście jest w submisji zerem z konstrukcji.
ZERO_BY_CONSTRUCTION_IN_SUBMISSION = {
    "mean_score": "final_score pochodzi z _compute_final_score, które zwraca 0.0 gdy "
                  "base_actions_per_level is None (taaf/game.py L391-392)",
    "score": "j.w.",
    "mean_actions_need": "need = sum(base_actions_per_level or []) = 0 gdy baseline ukryty",
    "actions_need": "j.w.",
}


def check_loud_wrong_instruments(cells, patch_texts, baselines):
    '''Bramka/wskaźnik, który w submisji zawsze odpala z fałszywym werdyktem.

    Rozpoznaje ZABEZPIECZENIE: jeśli komórka sama sprawdza widoczność baseline
    (`actions_need == 0` / `base_actions_per_level is None` / `baselines_hidden`),
    to bramka jest świadoma i dostaje INFO, nie KRYTYCZNE. Bez tego mój weryfikator
    oflagowałby MOJĄ WŁASNĄ poprawkę jako defekt — a narzędzie dające fałszywe
    pozytywy jest gorsze niż brak narzędzia, bo uczy ignorować raport.
    '''
    f = []
    GUARD_RX = re.compile(r"actions_need[\"\']?\]?\s*==\s*0|base_actions_per_level\s+is\s+None"
                          r"|baselines_hidden|baseline_available|baseline\s*[=:][^\n]{0,12}(hidden|ukryt)")
    for idx, src in cells:
        uses_hidden = any(re.search(rf"\b{k}\b", src) for k in ZERO_BY_CONSTRUCTION_IN_SUBMISSION)
        if not (uses_hidden and "game_runs" in src):
            continue
        guarded = bool(GUARD_RX.search(src))
        # 6a — bramka GO/NO-GO na score
        for ln_no, line in enumerate(src.splitlines(), 1):
            if re.search(r"(?:_gate|NO-GO|GO \()[^\n]*?([<>]=?)\s*\d+(?:\.\d+)?", line) and \
               re.search(r"mean_score|\bscore\b", src):
                if guarded:
                    f.append({
                        "kontrola": "L6 INSTRUMENT GŁOŚNO-MYLĄCY",
                        "ważność": "INFO", "komórka": idx, "linia": ln_no,
                        "kod": line.strip()[:150],
                        "problem": "—",
                        "skutek": "bramka JEST świadoma baseline (komórka zawiera strażnika "
                                  "widoczności) — w submisji wydrukuje N/A zamiast fałszywego NO-GO",
                        "naprawa": "—",
                    })
                else:
                    f.append({
                        "kontrola": "L6 INSTRUMENT GŁOŚNO-MYLĄCY",
                        "ważność": "KRYTYCZNA", "komórka": idx, "linia": ln_no,
                        "kod": line.strip()[:150],
                        "problem": "bramka porównuje score z stałą, ale w submisji score = 0.00 "
                                   "Z KONSTRUKCJI (taaf/game.py L391-392: _compute_final_score "
                                   "zwraca 0.0 gdy baseline None)",
                        "skutek": "w KAŻDYM prawdziwym submicie log wydrukuje 'NO-GO (below v3 smoke "
                                  "29.02)' niezależnie od wyniku. To groźniejsze niż martwy alarm z L1: "
                                  "martwy alarm MILCZY, ten KRZYCZY fałszywym werdyktem. Dodatkowo "
                                  "score=0.00 w logu jest nieodróżnialne od PRAWDZIWEJ porażki 0.00, "
                                  "którą już raz mieliśmy (submisja 57629847, c45 concurrency=120 vs "
                                  "MAXREQ=10).",
                        "naprawa": "uzależnić bramkę od widoczności baseline: "
                                   "if _summary['mean_actions_need'] == 0: drukuj 'N/A (baseline "
                                   "ukryty w submisji) - score lokalny nie ma sensu, patrz "
                                   "weight_pct/coverage'",
                    })
                break
        # 6b — wskaźnik z mianownikiem, który w submisji jest zerem
        buggy = re.search(r"max\(\s*1\.0?\s*,\s*_mean\([\"\']actions_need", src)
        if buggy:
            for ln_no, line in enumerate(src.splitlines(), 1):
                if "depth_budget_used_pct" in line:
                    f.append({
                        "kontrola": "L6 INSTRUMENT GŁOŚNO-MYLĄCY",
                        "ważność": "WYSOKA", "komórka": idx, "linia": ln_no,
                        "kod": line.strip()[:150],
                        "problem": "mianownik actions_need = 0 w submisji, a max(1.0, ...) zamienia "
                                   "dzielenie przez zero w dzielenie przez 1 — czyli w 100 x "
                                   "liczba_akcji",
                        "skutek": "log wydrukuje np. '212/0 (21200.0% of a full clear)' — liczba bez "
                                  "sensu wyglądająca na pomiar",
                        "naprawa": "zwracać None gdy actions_need == 0 i zabezpieczyć druk",
                    })
                    break
    return f


# ---------------------------------------------------------------------------
# L7 — WDROŻENIOWOŚĆ PAKIETU (kernel-metadata.json)
# ---------------------------------------------------------------------------
def check_deployability(pkg_dir: str):
    '''code_file musi istnieć; slug nie może należeć do cudzego pakietu.'''
    f = []
    meta_p = Path(pkg_dir) / "kernel-metadata.json"
    if not meta_p.is_file():
        return f
    try:
        meta = json.loads(re.sub(r"//.*$", "", meta_p.read_text(encoding="utf-8"), flags=re.M))
    except (OSError, ValueError) as exc:
        f.append({"kontrola": "L7 WDROŻENIOWOŚĆ", "ważność": "WYSOKA", "komórka": "-", "linia": "-",
                  "kod": str(meta_p), "problem": f"nie dało się przeczytać metadata: {exc!r}",
                  "skutek": "kaggle kernels push zachowa się nieprzewidywalnie", "naprawa": "naprawić JSON"})
        return f
    code_file = meta.get("code_file", "")
    if code_file and not (Path(pkg_dir) / code_file).is_file():
        obecne = sorted(p.name for p in Path(pkg_dir).glob("*.ipynb"))
        f.append({
            "kontrola": "L7 WDROŻENIOWOŚĆ",
            "ważność": "KRYTYCZNA", "komórka": "-", "linia": "-",
            "kod": f'code_file = {code_file!r}',
            "problem": f"plik {code_file!r} NIE ISTNIEJE w katalogu pakietu; są tam: {obecne}",
            "skutek": "`kaggle kernels push` albo się wywali, albo — jeśli w katalogu został stary plik "
                      "o tej nazwie — wypchnie ZŁY notebook. To defekt głośny (push pada), więc mniej "
                      "groźny niż kolizja sluga, ale blokuje submisję w ostatniej chwili.",
            "naprawa": f'ustawić code_file na rzeczywisty plik: {obecne[0] if obecne else "?"}',
        })
    kid = str(meta.get("id", ""))
    slug = kid.split("/")[-1] if kid else ""
    # ODNIESIENIEM JEST NAZWA NOTEBOOKA (prawdziwy artefakt), NIE nazwa katalogu:
    # katalog bywa scratchem audytora (np. duck-v15-a450) i wtedy porównanie daje
    # FAŁSZYWY POZYTYW. Wersja notebooka jest tym, co pakiet naprawdę zawiera.
    nbs = sorted(Path(pkg_dir).glob("*.ipynb"))
    name = (code_file if (Path(pkg_dir) / code_file).is_file() else
            (nbs[0].name if nbs else Path(pkg_dir).resolve().name))
    tokens = set(re.findall(r"v\d+(?:[\.-]\d+)?", name.lower()))
    slug_n = slug.replace(".", "").replace("-", "")
    if slug and tokens and not any(t.replace(".", "").replace("-", "") in slug_n for t in tokens):
        f.append({
            "kontrola": "L7 WDROŻENIOWOŚĆ",
            "ważność": "KRYTYCZNA", "komórka": "-", "linia": "-",
            "kod": f"id = {kid!r}  (katalog: {name})",
            "problem": f"slug kernela {slug!r} nie zawiera wersji pakietu {sorted(tokens)} — wygląda na "
                       f"slug ODZIEDZICZONY po innym pakiecie",
            "skutek": "push NADPISZE CUDZY KERNEL o tym slugu. Zmierzone 30.10: duck-v16 Gemmy ma slug "
                      "arc3-duck-v13-4-unified (= kernel v13.4 Smak), a duck-v15 Gemmy ma "
                      "arc3-duck-v13-3-arena (= kernel v13.3-arena Smak). To ta sama klasa błędu, za "
                      "którą użytkownik zganił nas 2026-10-16 ('wrzuciles ten sam plik co w nocy!!!').",
            "naprawa": f"dać własny slug, np. petersharps/{name.replace('_', '-')}",
        })
    return f


KONTROLE = [
    ("L1 ŻYWOTNOŚĆ INSTRUMENTU", check_instrument_liveness),
    ("L2 DOMYŚLNA WARTOŚĆ ENV", check_env_defaults),
    ("L3 OSIĄGALNOŚĆ", check_reachability),
    ("L4 SPÓJNOŚĆ MIĘDZYWARSTWOWA", check_cross_layer),
    ("L5 WEJŚCIE UKRYTE W SUBMISJI", check_hidden_inputs),
    ("L6 INSTRUMENT GŁOŚNO-MYLĄCY", check_loud_wrong_instruments),
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
    # deduplikacja: ten sam problem zgloszony z kilku linii (np. definicja + druk) to JEDNO ustalenie
    seen, ded = set(), []
    for f in out:
        k = (f["kontrola"], f["komórka"], f["problem"][:80])
        if k in seen:
            continue
        seen.add(k)
        ded.append(f)
    return ded


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("notebook", help="plik .ipynb do sprawdzenia")
    ap.add_argument("patches", nargs="*", help="pliki .patch (opcjonalnie; notebookowe są brane automatycznie)")
    ap.add_argument("--baseline", action="append", default=[], metavar="NAZWA=WARTOŚĆ",
                    help="nadpisz zmierzoną bazę, np. --baseline actions_per_call=5.1")
    ap.add_argument("--strict", action="store_true", help="exit 1 przy choćby jednym KRYTYCZNYM")
    ap.add_argument("--package", metavar="KATALOG", default=None,
                    help="katalog pakietu z kernel-metadata.json — włącza kontrolę L7 WDROŻENIOWOŚĆ")
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
    if args.package:
        findings.extend(check_deployability(args.package))
    if not findings:
        print("\n✅ BRAK USTALEŃ — wszystkie kontrole czyste.")
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
