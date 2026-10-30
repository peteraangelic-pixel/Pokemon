#!/usr/bin/env python3
'''build_c87_v16f.py — MOJA NAJLEPSZA WERSJA: duck-v16 (Gemma `0ef24651`) + 6 poprawek.

DLACZEGO v16 JEST BAZĄ, A NIE COŚ WŁASNEGO
------------------------------------------
v16 to jedyny pakiet, którego reguła eskalacji jest ŻYWA w punktowanym rerunie:
  · `base_actions_per_level` jest `None` w trybie submisji (taaf/game.py L254-255, L439-440,
    L448, L471-472) ⇒ próg względny patcha 0008 degraduje do stałego flooru;
  · `actions_per_level` jest ŻYWE (taaf/game.py L569: `+= 1` po każdej akcji, w trakcie biegu)
    ⇒ self-pace patcha 0009 ma prawdziwe źródło danych.
Zmierzone (moja replikacja na r085 ORAZ na niezależnym r093):
    floor 20 + cap 2 (v13.4/v13.5/v15-a450 w rerunie) : 42 / 26 przedwczesnych / 4,33 % puli
    self-pace 1.5 x mediana (v16 w rerunie)            : 22 / 14 przedwczesnych / 2,27 % puli
                                                        (r093: 22 / 13 — ten sam kierunek)
Czyli v16 jest ~2x tańszy i ~2x mniej przedwczesny niż każdy inny pakiet w biegu, który się liczy.
Do tego v16 ma hint openerowy (jedyna dźwignia o skali >= celu: 7911 mierzy stosunek 24:1 wobec
całego sporu o eskalację) i sondę widoczności baseline + pokrycia.

CO TEN SKRYPT NAPRAWIA (6 rzeczy, wszystkie weryfikowalne STATYCZNIE — bez bundla, bez GPU)
------------------------------------------------------------------------------------------
 1 L7 `code_file` : 'arc3-duck-v13.ipynb' -> rzeczywisty plik. W pakiecie Gemmy ten plik NIE
                    ISTNIEJE, więc `kaggle kernels push` pada w ostatniej chwili.
 2 L7 `id`/`title`: 'petersharps/arc3-duck-v13-4-unified' -> własny slug. Obecny NALEŻY DO
                    v13.4-unified Smak, więc push NADPISAŁBY CUDZY KERNEL. (duck-v15 Gemmy ma
                    ten sam defekt ze slugiem arc3-duck-v13-3-arena.)
 3 L1 alarm       : `mean_actions_per_call < 1.5` -> `< 4.357` + druk BEZWARUNKOWY z drabinką
                    celów. Zmierzona baza to 4,357 (r019: 474 wywołania / 2065 akcji), więc próg
                    1,5 nie może być prawdziwy NIGDY — instrument, który miał powiedzieć, czy
                    batching zadziałał, jest martwy. Występuje w DWÓCH komórkach v16 (39 i 40).
 4 L6 bramka      : `NO-GO if mean_score <= 29.02` -> świadoma baseline. W submisji
                    `_compute_final_score` zwraca 0.0 (taaf/game.py L391-392), więc bramka
                    drukowałaby NO-GO w KAŻDYM submicie — głośno-mylący instrument.
 5 L6 wskaźnik    : `depth_budget_used_pct` -> None gdy `actions_need == 0`, zamiast
                    `100 x akcje` (log drukowałby "21200.0% of a full clear").
 6 docstring 0009 : "fires 27 times ... on 16 levels" -> **22 / 14**. Zweryfikowane przez
                    URUCHOMIENIE ich własnego testu: `tests/test_self_pace.py` drukuje
                    `self-pace=22/14`. Asercja `pace[0] < floor[0] and pace[1] < floor[1]`
                    przechodzi dla 14/9, 22/14 i 27/16 — czyli NIE DYSTRYMINUJE.

Każda poprawka jest ASERTOWANA: jeśli wzorzec nie pasuje, skrypt pada, nie produkuje
cichego pół-pakietu. To ta sama dyscyplina, którą zastosowałem do własnego weryfikatora.

UŻYCIE
------
    python3 build_c87_v16f.py <katalog_duck-v16> <katalog_wyjsciowy>
    python3 verify_config_liveness.py <wyjście>/arc3-duck-v16.ipynb --package <wyjście> --strict
'''
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

NOWY_SLUG = "arc3-duck-v16-c87f"

# --- 3. alarm: próg 1,5 -> 4,357 + druk bezwarunkowy --------------------------
# Dwa warianty nazwy pola: `mean_actions_per_call` (sonda rosteru, kom. 40)
# i `mean_a_per_call` (sonda pokrycia, kom. 39).
ALARMY = [
    (
        '''        if _acpc and _summary["mean_actions_per_call"] < 1.5:
            print(f"v13.4 roster: a/call = {_summary['mean_actions_per_call']} < 1.5 -> commit(plan) "
                  f"praktycznie nie odpala; dzwignia 50+ lezy odlogiem", flush=True)''',
        '''        # c87f FIX 3 (L1): próg 1,5 był 3x PONIŻEJ zmierzonej bazy 4,357 (r019: 474 wywołania
        # / 2065 akcji), więc gałąź nie mogła się wykonać NIGDY. Druk bezwarunkowy + drabinka celów:
        # tok/akcję = tok/wywołanie / akcje/wywołanie = 3664,6 / a_per_call, a akcje/grę =
        # 2945 x 1000 / (17,2 ms/tok x tok/akcję). Cel 300 akcji/grę => a/call ~ 5,7; 400 => ~ 7,6.
        _ACPC_BAZA = 4.357
        if _acpc:
            _a = _summary["mean_actions_per_call"]
            print(f"v13.4 roster: a/call = {_a} (baza r019 = {_ACPC_BAZA}; "
                  f"cel 300 akcji/grę ~ 5.7, cel 400 ~ 7.6)", flush=True)
            if _a < _ACPC_BAZA:
                print(f"v13.4 roster: a/call {_a} < {_ACPC_BAZA} -> REGRESJA batchingu "
                      f"(hint openerowy nie zadziałał albo się cofnął)", flush=True)
            elif _a < 5.7:
                print(f"v13.4 roster: a/call {_a} w [{_ACPC_BAZA}, 5.7) -> batching zadziałał "
                      f"CZĘŚCIOWO; ~250-300 akcji/grę, czyli ~35 pkt po dyskoncie 25 %", flush=True)
            else:
                print(f"v13.4 roster: a/call {_a} >= 5.7 -> batching ZADZIAŁAŁ; "
                      f">= 300 akcji/grę, droga do 50 otwarta", flush=True)''',
    ),
    (
        '''        if _summary["mean_a_per_call"] < 1.5:
            print(f"v16 coverage: a/call={_summary['mean_a_per_call']} < 1.5 -> batch na openerze "
                  f"(hint) nie zadzialal; tok/akcje nie spadly", flush=True)''',
        '''        # c87f FIX 3 (L1): j.w. — próg 1,5 nieosiągalny przy bazie 4,357.
        if _summary["mean_a_per_call"] < 4.357:
            print(f"v16 coverage: a/call={_summary['mean_a_per_call']} < 4.357 (baza r019) -> batch "
                  f"na openerze (hint) NIE POPRAWIL tok/akcje", flush=True)''',
    ),
]

# --- 4. bramka NO-GO: świadoma baseline ---------------------------------------
BRAMKA_STARA = '''    _gate = "NO-GO (below v3 smoke 29.02)" if _summary["mean_score"] <= 29.02 else "GO (above v3 smoke)"
    print(f"v11 gate: {_gate}", flush=True)'''
BRAMKA_NOWA = '''    # c87f FIX 4 (L6): w submisji silnik UKRYWA baseline (taaf/game.py L254-255, L439-440, L448,
    # L471-472), a _compute_final_score zwraca wtedy 0.0 (L391-392). Stara bramka drukowałaby
    # "NO-GO (below v3 smoke 29.02)" w KAŻDYM prawdziwym submicie — głośno-mylący instrument,
    # a score=0.00 w logu jest nieodróżnialne od prawdziwej porażki 0.00 (submisja 57629847).
    if _summary["mean_actions_need"] == 0:
        _gate = ("N/A — baseline UKRYTY w tym biegu, więc score lokalny jest 0.00 z konstrukcji, "
                 "nie z wyniku. Patrz na weight_pct / coverage (nie zależą od baseline) "
                 "i na a/call.")
    else:
        _gate = "NO-GO (below v3 smoke 29.02)" if _summary["mean_score"] <= 29.02 else "GO (above v3 smoke)"
    print(f"v11 gate: {_gate}", flush=True)'''

# --- 5. depth_budget_used_pct: None zamiast 100 x akcje -----------------------
DBUP_STARA = '''        "depth_budget_used_pct": round(100.0 * _mean("actions") / max(1.0, _mean("actions_need")), 1),'''
DBUP_NOWA = '''        # c87f FIX 5 (L6): actions_need = sum(base_actions_per_level or []) = 0 gdy baseline ukryty,
        # a max(1.0, ...) zamieniało dzielenie przez zero w dzielenie przez 1 => "21200.0% of a full
        # clear". None jest uczciwe; druk poniżej też jest zabezpieczony.
        "depth_budget_used_pct": (round(100.0 * _mean("actions") / _mean("actions_need"), 1)
                                  if _mean("actions_need") else None),'''
DRUK_STARA = '''          f"({_summary['depth_budget_used_pct']}% of a full clear) "'''
DRUK_NOWA = '''          f"({(_summary['depth_budget_used_pct'] if _summary['depth_budget_used_pct'] is not None else 'n/a — baseline ukryty')}% of a full clear) "'''
# DRUK_NOWA nie niesie komentarza-znacznika (to fragment f-stringa), więc idempotencja
# potrzebuje osobnego podciągu rozpoznawczego — ASCII, bez myślników.
DRUK_ZNACZNIK = "_summary['depth_budget_used_pct'] if _summary['depth_budget_used_pct'] is not None"

# --- 6. docstring patcha 0009 i fixture: 27/16 -> 22/14 -----------------------
# ⚠️ WZORCE MUSZĄ BYĆ JEDNOLINIOWE: w pliku .patch każda linia ma prefiks "+", więc wzorzec
# obejmujący "\n    16 levels" pasuje do fixture (.py), ale NIE do patcha. Pierwsza wersja
# zastosowała się POŁOWICZNIE: patch dostał "22 times" i został przy "16 levels", czyli mówił
# 22/16 — LICZBĘ, KTÓRA NIE ZGADZA SIĘ Z ŻADNĄ Z TRZECH. Poniżej: dwa niezależne podciągi
# jedoliniowe + asercja, że OBA weszły (inaczej skrypt pada, nie wypuszcza pół-poprawki).
# Detektor "już zastosowane" dla FIX 3 MUSI być kluczowany na WZORCU KODU, nie na gołym
# podciągu "< 1.5": v13.7 ma w komórce 2 KOMENTARZ dokumentujący stary martwy alarm
# ("a/call alarm `< 1.5` was dead ..."), więc test `"< 1.5" not in s` odrzucał komórkę
# z już wstawioną poprawką. Feedback Smaka (SYNC §25D, 3945d727) — mieli rację.
ALARM_KOD = 'if _acpc and _summary["mean_actions_per_call"] < 1.5'

DOCSTRING = [
    ("fires 27 times instead of 42", "fires 22 times instead of 42"),
    ("16 levels instead of 26", "14 levels instead of 26"),
]


# Znaczniki już zastosowanych poprawek — build jest IDEMPOTENTNY: pakiet, który część z nich
# już ma (np. v13.6-final ma FIX 3 wzięty z mojej warstwy-8), dostaje "już zastosowane", nie błąd.
ZNACZNIKI = {"c87f FIX 3": "FIX 3", "c87f FIX 4": "FIX 4", "c87f FIX 5": "FIX 5",
             "4.357": "FIX 3", "mean_actions_need\'] == 0": "FIX 4"}


def _podmien(text: str, stary: str, nowy: str, etykieta: str) -> tuple[str, int]:
    n = text.count(stary)
    if n == 0:
        raise SystemExit(f"✗ {etykieta}: wzorzec nie pasuje — pakiet się zmienił, NIE zgaduję.\n"
                         f"  szukam: {stary[:110]!r}")
    return text.replace(stary, nowy), n


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    if not src.is_dir():
        raise SystemExit(f"✗ {src} nie jest katalogiem")

    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    print(f"=== build_c87_v16f: {src} -> {dst} ===")
    raport = []

    # ---- FIX 1 + 2: kernel-metadata.json ------------------------------------
    meta_p = dst / "kernel-metadata.json"
    raw = meta_p.read_text(encoding="utf-8")
    meta = json.loads(re.sub(r"//.*$", "", raw, flags=re.M))
    nbs = sorted(p.name for p in dst.glob("*.ipynb"))
    if not nbs:
        raise SystemExit(f"✗ brak .ipynb w {dst}")
    stary_cf = meta.get("code_file")
    if stary_cf not in nbs:
        meta["code_file"] = nbs[0]
        raport.append(f"FIX 1 (L7 code_file) : {stary_cf!r} -> {nbs[0]!r}  [poprzedni NIE ISTNIAŁ]")
    else:
        raport.append(f"FIX 1 (L7 code_file) : {stary_cf!r} — już poprawny, bez zmian")
    stary_id = meta.get("id", "")
    slug = stary_id.split("/")[-1] if stary_id else ""
    slug_n = slug.replace(".", "").replace("-", "")
    wersje = set(re.findall(r"v\d+(?:[\.-]\d+)?", meta["code_file"].lower()))
    if slug and wersje and any(v.replace(".", "").replace("-", "") in slug_n for v in wersje):
        raport.append(f"FIX 2 (L7 slug)      : {stary_id!r} — JUŻ WŁASNY (zgadza się z {meta['code_file']}), bez zmian")
    else:
        meta["id"] = f"{stary_id.split('/')[0]}/{NOWY_SLUG}" if "/" in stary_id else NOWY_SLUG
        meta["title"] = NOWY_SLUG
        raport.append(f"FIX 2 (L7 slug)      : {stary_id!r} -> {meta['id']!r}  [poprzedni był CUDZY]")
    meta_p.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    # ---- FIX 3 + 4 + 5: notebook --------------------------------------------
    nb_p = dst / meta["code_file"]
    nb = json.loads(nb_p.read_text(encoding="utf-8"))
    liczniki = {"alarm": 0, "bramka": 0, "dbup": 0, "druk": 0,
                "alarm_juz": 0, "bramka_juz": 0, "dbup_juz": 0, "druk_juz": 0}
    for c in nb["cells"]:
        if c.get("cell_type") != "code":
            continue
        s = "".join(c["source"])
        o = s
        for stary, nowy in ALARMY:
            if stary in s:
                s, _ = _podmien(s, stary, nowy, "FIX 3 alarm")
                liczniki["alarm"] += 1
            elif "4.357" in s and ALARM_KOD not in s:
                # pakiet już zaadoptował poprawkę (v13.6-final wziął ją z mojej warstwy-8,
                # własnym sformułowaniem: bezwarunkowy druk z bazą 4.357 i celami 5,7/7,6)
                liczniki["alarm_juz"] = liczniki.get("alarm_juz", 0) + 1
        # ZNACZNIK-NJPIERW, nie wzorzec-najpierw: BRAMKA_STARA jest PODCIAGIEM BRAMKA_NOWA
        # (stara linia zostaje w galezi else:), wiec test wzorca nigdy nie odróżni
        # "jeszcze nie" od "juz tak" — przy wzorzec-najpierw poprawka ZAGNIEŻDŻAŁA się
        # przy każdym kolejnym biegu. Znacznik w komentarzu jest jednoznaczny.
        if "c87f FIX 4" in s:
            liczniki["bramka_juz"] += 1
        elif BRAMKA_STARA in s:
            s, _ = _podmien(s, BRAMKA_STARA, BRAMKA_NOWA, "FIX 4 bramka")
            liczniki["bramka"] += 1
        if "c87f FIX 5" in s:
            liczniki["dbup_juz"] += 1
        elif DBUP_STARA in s:
            s, _ = _podmien(s, DBUP_STARA, DBUP_NOWA, "FIX 5 dbup")
            liczniki["dbup"] += 1
        if DRUK_STARA in s:
            s, _ = _podmien(s, DRUK_STARA, DRUK_NOWA, "FIX 5 druk")
            liczniki["druk"] += 1
        elif DRUK_ZNACZNIK in s:
            liczniki["druk_juz"] += 1
        if s != o:
            c["source"] = s.splitlines(keepends=True)
    raport.append(f"FIX 3 (L1 alarm)     : poprawiono w {liczniki['alarm']} komórkach "
                  f"(v16: oczekiwane 2 — sonda pokrycia + sonda rosteru)")
    raport.append(f"FIX 4 (L6 bramka)    : poprawiono w {liczniki['bramka']} komórkach (oczekiwane 1)")
    raport.append(f"FIX 5 (L6 wskaźnik)  : definicja {liczniki['dbup']}x + druk {liczniki['druk']}x "
                  f"(oczekiwane 1 i 1; już zastosowane: {liczniki['dbup_juz']} i {liczniki['druk_juz']})")
    if (liczniki["alarm"] + liczniki["alarm_juz"] < 1 or
            liczniki["bramka"] + liczniki["bramka_juz"] < 1 or
            liczniki["dbup"] + liczniki["dbup_juz"] < 1 or
            liczniki["druk"] + liczniki["druk_juz"] < 1):
        raise SystemExit("✗ nie wszystkie wzorce pasują — patrz liczniki wyżej. NIE wypuszczam pół-pakietu.")
    for k in ("alarm", "bramka", "dbup", "druk"):
        if liczniki.get(k + "_juz"):
            raport.append(f"       ({k}: {liczniki[k+'_juz']}x JUŻ ZASTOSOWANE w tym pakiecie — idempotentnie pomijam)")
    nb_p.write_text(json.dumps(nb, indent=1) + "\n", encoding="utf-8")

    # ---- FIX 6: docstring patcha 0009 + fixture -----------------------------
    ile = 0
    for kandydat in sorted(dst.rglob("*.patch")) + sorted(dst.rglob("*.py")):
        txt = kandydat.read_text(encoding="utf-8", errors="replace")
        if "fires 27 times" not in txt and "16 levels instead of 26" not in txt:
            continue
        o = txt
        trafione = []
        for stary, nowy in DOCSTRING:
            if stary in txt:
                txt = txt.replace(stary, nowy)
                trafione.append(stary[:22])
        # ASERCJA: jeśli plik miał którąkolwiek z liczb, musi mieć OBIE poprawione.
        if "fires 22 times" in txt and "14 levels instead of 26" not in txt:
            raise SystemExit(f"✗ FIX 6 w {kandydat.name}: '22 times' weszło, ale '14 levels' NIE "
                             f"— wzorce nie są jednoliniowe? NIE wypuszczam pół-poprawki.")
        if "fires 27 times" in txt or "16 levels instead of 26" in txt:
            raise SystemExit(f"✗ FIX 6 w {kandydat.name}: została stara liczba (27 lub 16).")
        if txt != o:
            kandydat.write_text(txt, encoding="utf-8")
            ile += 1
            raport.append(f"FIX 6 (docstring)    : {kandydat.name} — 27/16 -> 22/14 "
                          f"(oba podciągi: {len(trafione)}/2)")
    if ile == 0:
        raport.append("FIX 6 (docstring)    : 'fires 27 times' nie występuje w *.patch/*.py "
                      "(JUŻ POPRAWIONE albo patch/fixture poza pakietem)")

    # ---- FIX 6b: ten sam docstring w patchu OSADZONYM W NOTEBOOKU --------------
    # Znalezione na v13.7 (2026-10-30): FIX 6 iteruje *.patch i *.py, więc poprawia
    # TYLKO kopię referencyjną. Kaggle aplikuje tekst z komórki notebooka
    # (`_P("/kaggle/duck-extra-07.patch").write_text(...)`), a verify_v13.py
    # ekstrahuje patche WŁAŚNIE z notebooka (`extract_patches(cells)`). Bez 6b pakiet
    # jest niespójny: shipped 27/16 vs patches/+fixture 22/14 — i certyfikat tego NIE
    # widzi, bo kontrola "extra-07 registered (byte-for-byte from Gemma duck-v16)"
    # asertuje tylko obecność dwóch podciągów, nie porównuje ani jednego bajtu.
    # Podmiana per-element listy `source` (nie resplit) — struktura JSON zostaje 1:1.
    nb2 = json.loads(nb_p.read_text(encoding="utf-8"))
    kom_6b = []
    for idx, cell in enumerate(nb2["cells"]):
        joined = "".join(cell.get("source", []))
        if "duck-extra-07.patch" not in joined or "fires 27 times" not in joined:
            continue
        newsrc, ruszone = [], 0
        for part in cell.get("source", []):
            p2 = part
            for stary, nowy_s in DOCSTRING:
                p2 = p2.replace(stary, nowy_s)
            ruszone += (p2 != part)
            newsrc.append(p2)
        po = "".join(newsrc)
        if "fires 27 times" in po or "16 levels instead of 26" in po:
            raise SystemExit(f"✗ FIX 6b w komórce {idx}: została stara liczba (27 lub 16).")
        if "fires 22 times" not in po or "14 levels instead of 26" not in po:
            raise SystemExit(f"✗ FIX 6b w komórce {idx}: nowy docstring nie wszedł w całości.")
        if ruszone != 1:
            raise SystemExit(f"✗ FIX 6b w komórce {idx}: docstring leży w {ruszone} elementach "
                             f"source, oczekiwałem dokładnie 1 — nie zgaduję.")
        cell["source"] = newsrc
        kom_6b.append(idx)
    if kom_6b:
        nb_p.write_text(json.dumps(nb2, indent=1) + "\n", encoding="utf-8")
        raport.append(f"FIX 6b (OSADZONY 0009): komórki {kom_6b} — 27/16 -> 22/14. To jest "
                      f"artefakt, który Kaggle NAPRAWDĘ aplikuje; bez tego FIX 6 był dekoracyjny.")
    else:
        raport.append("FIX 6b (OSADZONY 0009): 'fires 27 times' nie występuje w notebooku "
                      "(już poprawione albo pakiet osadza 0009 inaczej) — bez zmian.")

    print()
    for r in raport:
        print("  " + r)
    print(f"\n✅ gotowe: {dst}/{meta['code_file']}")
    print("   następny krok (BRAMKA, musi dać 0 KRYTYCZNYCH):")
    print(f"   python3 verify_config_liveness.py {dst}/{meta['code_file']} --package {dst} --strict")
    print("   UWAGA: bramka to NIE certyfikacja. Certyfikacja = verify_v13.py --bundle r033 --tests.")
    print("   STAN NA 2026-10-30: bundel r033 JEST w repo Smak-Domu-Konkurs")
    print("   (arc-agi-3/kaggle/ops/results/r033-recon-bundle/, 74 pliki) — certyfikację DA SIĘ")
    print("   uruchomić offline. Wymaga: requests, numpy, pillow (pip --break-system-packages).")
    print("   Testy winpath (11) wymagają arcengine, który potrzebuje Pythona >= 3.12 —")
    print("   na 3.11 to JEDYNA kontrola nie do odtworzenia (8 błędów = ModuleNotFoundError).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
