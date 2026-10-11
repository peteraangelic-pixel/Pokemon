# Diagnoza v14 (484.1, rank 222/317) i analiza liderów 1200+

Stan na 2026-10-11 ~14:30 UTC. Dane: 8 rozgrywek v14 (episode-121975059…88745), 30 rozgrywek
top10_live, 75 starszych replayów, gauntlety FFI (libcg.so) z 2026-10-11.

## 1. Wynik v14

- v14 = `main_heuristic_v11f.py` (= gen6, ten sam plik) + deck `v13_29_top30` (29W: 4×723, 4×722, 2×721, 29×3E). Zweryfikowane z bundla.
- Submissja 1: **484.1** (rank 222/317), submissja 2: 385.0. Poprzednie μ: 372.1 → wzrost o ~112 pkt.
- Pole: 317 zespołów, best 1230.8, mediana 653.5, top10% = 1002.9, top1% = 1196.9.

## 2. Przyczyny przegranych z „słabymi" (rank 155–246)

Próbka 8 meczów v14: **2W-6L**. Przeciwnicy i ich decki:

| Wynik | Rank | Przeciwnik | Deck rywala |
|---|---|---|---|
| L | 222 | PeterSharps (auto-mirror) | 29W mirror |
| L | 157 | (ノ◡ <) | **Lucario ex 14E** (Riolu/Solrock) |
| L | 246 | Tom Curry11 | 35W mirror |
| L | 198 | F.A.Nina | **Lucario ex 13E** |
| W | 226 | Kevin Hulin | Dragapult ex 10E |
| W | 155 | vrmichalski | 35E mirror |
| L | 214 | tanzaku | **Ogerpon Teal ex 14E** |
| L | 155 | vrmichalski | 35E mirror |

5 z 6 przegranych = 2 mirrory + 3 aggro 13–14E.

### Dowody

1. **Deck NIE jest problemem.** Gauntlet FFI (ten sam agent po obu stronach, 20g/matchup):
   - v11f+v13_29 vs meta top30: **0.867** (Ogerpon 0.600, Lucario 0.900, Alakazam 1.000, Dipplin #1 0.850, Dragapult 0.900, Sinistcha 0.950)
   - gen5 (v10_34) vs meta: 0.850 — oba agentu równoważne.
   - Oznacza: nasz mill bije każdy archetyp meta na poziomie decka.

2. **Policy jest problemem.** Ten sam pattern co na weak tierze:
   - symulacja (ten sam policy): weak 0.71–0.75, meta 0.85–0.87
   - live: ~0.33–0.40 na tym samym poolu graczy
   - luka ~35 pkt = polityka rywala bije naszą, nawet przy przewadze decka.

3. **Tempo (mierzalne, z obserwacji w replayach):**
   - Liderzy: 1. prize ~T6–7, **2.17 prize do T9** (w wygranych), mecze kończą się ~T10.
   - My: 1. prize ~T8–8.5, **1.00 prize do T9**. Mniej więcej 2 pół-tury wolniej na starcie.
   - Przykład (F.A.Nina 198, Lucario 13E vs nasz 29W, match L): atakująca Solrock→Lucario ex
     gotowa T4–T6, 3+ prize do T7 w obu grach; nasz mill: 0–1 prize, Snover KO'wany w T2–T4.

4. **Mirrory = rzut monetą, my poniżej 0.50** (2W-3L w 5 meczach z próbki; 1x stall do
   deckoutu po 24T — obie decki się skończyły, czyli rywal zmielł szybciej).

## 3. Co robią liderzy 1200+ (top ~5: ANMOL GARG 1230, YumeNeko 1216, leo_turing 1175,
YumeNeko 1172, Bill Vlasak 1188)

### Decki (top30_live, 23 decki)

| Archetyp | E | Zespoły w top30 |
|---|---|---|
| **Ogerpon Teal Mask ex** | 14E | **12** (YumeNeko #2, leo_turing #5, Stephen Schott #8, Mengfei Li #9, Chonghao Peng #10, Xinyu Li #11, Colton Martin #12, JerryChen #14, Mathieu W #19, KyryloBakumenko #26, Zedan Soorya #27, +1) |
| Lucario ex | 13–20E | Bill Vlasak #4 (20E), Raja Biswas #22 (14E), OceanMix #28 (13E) |
| Dipplin/Grookey aggro | 6E | **ANMOL GARG #1**, バーベナ #13, Cristobal Tudela #21 |
| Alakazam | 2E | Kentaro Totsuka #7, Majiro_ns #17 |
| Dragapult ex | 10E | Leon Liu #24 |
| Sinistcha | 3E | Darren Sheehan #18 |

Wnioski: (a) **zero mill w top30**, (b) meta = low-E aggro 2–20E vs nasze 29–34E,
(c) Ogerpon 14E to dominujący archetyp.

### Styl gry (30 rozgrywek top10_live)

- Pierwszy search/gust: T0–T1 (my: T0.8–1), 8–16 searchy na grę (Alakazam #7: 14/grę od T1;
  ANMOL GARG #1: 16/grę).
- 1. prize ~T6–7, 2.2 prize do T9, koniec meczu ~T10–13 (krótkie, szybkie mecze).
- Ich przegrane to **straty tempo**: gdy wypadową, mają 0.4 prize do T13 (umierają wcześnie).
- Konsystencja: nie przedłużają meczów, wygrywają speed race.

## 4. Co NIE działa (wykluczone testami)

- **Zmiana decka na Ogerpon 14E przy obecnej polityce**: weak_field 0.605, broad_field 0.395
  (vs mill 0.58–0.755). Polityka gen6 jest dostrojona pod engine mill (wall/stall/attach) —
  na Ogerpon traci przewagę.
- **gen5 (v10_34) vs gen6 (v11f)**: równoważne na meta (0.850/0.867); gen7 (0.778) nie
  pokonał gen6 (0.787) w ewolucji.
- **Deck 29W vs 34W**: oba OK na meta (0.867/0.850); na weak tier 34W + gen6 = 0.755
  (najlepszy combo) vs 29W = 0.580.

## 5. Rekomendacja na v15 (w kolejności)

1. **Runda ewolucji gen8 z fitness tempowym na poolu meta**:
   - pool: 6 decków meta (Ogerpon/Lucario/Alakazam/Dipplin/Dragapult/Sinistcha) + mirrory
   - fitness = winrate + premia za prize-pace (prize do T9) − kara za wolne 1. prize
   - silnik FFI: 120 gier/3s → stać nas na populację 1000+ kandydatów × 60+ gier
2. **Matchup-specific openingi**: nie leadzić Kyogre pod Solrock/Lucario; stall Snoverem
   vs aggro; w mirrorze przyspieszyć mielenie (wygrywać wyścig deckoutów).
3. **Deck na v15**: `v10_34_sig4` (34E) — lepsza synergia z polityką (weak 0.755), albo
   29W jeśli gen8 będzie ewoluowany pod 29W.
4. Cel: zamknąć lukę policy (live 0.33–0.40 → 0.55+ vs aggro mid). Dopóki luka istnieje,
   żaden deck nie przebije ściany mid tieru (rank ~90–250 = aggro wall).

## Aneks: narzędzia

- `tools/gauntlet_ffi.py` — gauntlet bez kaggle_environments (FFI do libcg.so), 20–40x szybszy.
- `tools/analyze_playstyle.py` / `_rust` — gust/retrieval/energy per team.
- `/home/user/scratch/h2h.py` — 2-agent H2H z FFI (bez auto-init kaggle_environments).
- Uwaga format replaya: epizod = **BO3** (`bo:3` w configuration); obserwacje rzadkie
  (stan tylko w części kroków); lista `prize` = pozostające prize (6→0).
