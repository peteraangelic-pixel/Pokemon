# Analiza rewolucji Alakazam — druga gałąź vs nasza gałąź

## TL;DR
- Trolley (Abomasnow) ma sufit 420-450 na Kaggle mimo 0.907 vs top30 i 0.791 vs broad_field
- Alakazam YumeNeko (1352.9 #1) ma sufit 1352, ale nasz v44 daje 0.278 vs top30
- Druga gałąź zbudowała dedykowanego pilota v65: 0.556 vs top30 (2x lepiej niż v44), 0.725 vs ściany (vs 0.4 trolley), 9-17% bench collapse (vs 48% trolley)
- v65 to właściwy fundament pod skok 1000+, ale wymaga strojenia per-archetyp (mirror + fast aggro 0.40-0.44)

## Pomiary lokalne (gauntlet_ffi, libcg.so direct, multiprocessing)

### vs top30_live (27 decków)
- c87_v61 (trolley, v44): 49W-5L-1D = 0.907 (5g: 121W-14L=0.896)
- dragapult (_arch, v44): 40W-14L=0.741 (2g), 28W-39L=0.418 vs broad
- YumeNeko + v44: 15W-38L=0.278 (nasz search)
- YumeNeko + v65: 30W-24L=0.556 (2g), 73W-62L=0.541 (5g)
- YumeNeko + v66: 27W-27L=0.5 (2g)
- YumeNeko + v67: 41W-40L=0.506 (3g) — trade wall za broad
- YumeNeko + v68: 75W-60L=0.556 (5g) — remis z v65

**Wniosek:** trolley nadal najlepszy vs top30 lokalnie, ale nie przekłada się na Kaggle.

### vs broad_field (67 decków, 1g)
- trolley v61 v44: 53W-14L=0.791
- dragapult v44: 28W-39L=0.418
- YumeNeko v65: 34W-33L=0.507
- YumeNeko v67: 42W-25L=0.627 (best Alakazam vs broad)
- YumeNeko v68: 31W-36L=0.463

### vs ściany (4 decki: crustle_wall, shaun2024_wall, 2 live wall killers, 10g)
- trolley v44: 16W-24L=0.4 (shaun2024 1-9=0.1!)
- dragapult v44: 10W-30L=0.25
- YumeNeko v65: 29W-11L=0.725 (shaun2024 10-0=1.0, crustle 9-1=0.9)
- YumeNeko v66: 38W-22L=0.633
- YumeNeko v67: 24W-16L=0.6
- YumeNeko v68: 26W-14L=0.65

**Potwierdzenie tezy drugiej gałęzi:** Alakazam jako 1-prize non-ex przechodzi przez ścianę Crustle (0.725 vs 0.4), trolley nie.

### vs live_killers (18 decków które nas biły na Kaggle, 2g)
- trolley: 25W-11L=0.694
- YumeNeko v65: 19W-17L=0.528

### vs hard6_c87 (6 najtrudniejszych: Eugen, GiovanniCR, Riccardo, YumeNeko, alakazam, ogerpon, 5g)
- trolley: 24W-6L=0.8
- YumeNeko v65: 17W-13L=0.567

## Dekod YumeNeko (1352.9)

```
4x Telepath Psychic Energy (19) special
4x Abra (741) 50HP Basic, Teleportation 10 + switch
4x Kadabra (742) 80HP Stage1, Super Psy Bolt 30
4x Rare Candy (1079)
4x Buddy-Buddy Poffin (1086)
4x Poke Pad (1152)
3x Dudunsparce (66) 140HP Stage1, Land Crush 90, ability Run Away Draw
3x Dunsparce (305) 70HP Basic, Trading Places 0 + switch, Ram 20
3x Alakazam (743) 140HP Stage2, Powerful Hand 20 * hand
3x Hilda (1225) draw/search
3x Dawn (1231) draw/search
2x Basic P Energy (5)
2x Enhanced Hammer (1081)
2x Boss's Orders (1182) Gust
2x Battle Cage (1264) Stadium
2x Pikipek (1407) 70HP Basic, Double Stab 40
2x Toucannon (1409) 150HP Stage1, Feather Rondo 60
1x Enriching Energy (13) special
1x Fezandipiti ex (140) 210HP Basic ex, Cruel Arrow 30 anywhere
1x Togekiss (214) 140HP Stage1, Speed Wing 140
1x Togepi (959) 50HP Basic
1x Night Stretcher (1097)
1x Sacred Ash (1129)
1x Handheld Fan (1161) Tool
1x Lana's Aid (1184)
1x Special Red Card (1413)
```
- 11 basiców (vs 6-8 trolley) → 9-17% bench collapse vs 48%
- 7 energii (4 Telepath +2 Basic +1 Enriching) → meta 2-15E, 2-3 Gust (Boss x2)
- Silnik: Poffin szuka Abra/Dunsparce, Rare Candy skip Kadabra, Dudunsparce/Toucannon/Togekiss dobierają, Dawn/Hilda = obrażenia (Powerful Hand 20 * hand)

## Dlaczego v44 nie umie grać Alakazamem (0.278 vs 0.556)

v44 liczy obrażenia z `card_index.json`:
- Hammer-lanche (Abomasnow) 0 → parsuje "100 per Water discarded" → ~330 dmg
- Powerful Hand (Alakazam) 0 → v44 nie parsuje "20 per card in hand" → 0 dmg
- Więc v44 nigdy nie atakuje Alakazamem, tylko Dudunsparce 90 dmg → przegrywa.

v65 fix: `_atk_damage` zwraca 20*hand_n dla Powerful Hand, 30 dla Cruel Arrow.

## Co dalej — plan drugiej gałęzi (słuszny)

1. **Tempo:** Rare Candy agresywniej (110 vs 95), Boss KO liczone z ręki (20*hand+30 Fezandipiti), rotacje Abra Teleportation zamiast retreat za energię
2. **Silnik ręki:** Dudunsparce/Fezandipiti/Toucannon per plan YumeNeko (draw = dmg), ability Run Away Draw boost gdy hand<=5
3. **Strojenie per-archetyp:** ściana już wygrywamy (0.725), teraz mirror i szybkie aggro (Dragapult, Lucario, Ogerpon, Dhelmise/Banette) — 600g + replikacje
4. **Polityka:** BC z decyzji pilota + self-play na tej talii (ręczny scorer ma sufit, ale najpierw pilot musi grać poprawnie)

## Nasze próby v66-v68 — wnioski

- v66: bench guard +1000/+500, Rare Candy 110, Poffin 85, KO bonus +80 → top30 0.5 (gorszy niż v65 0.556), walls 0.633 (gorszy niż 0.725), broad 0.55 (lepszy niż 0.507) — over-benching szkodzi vs top30
- v67: Boss exact KO + hand boost + switch attack → top30 0.506, walls 0.6, broad 0.627 (best broad) — trade wall za broad
- v68: v65 + tylko Boss exact + Hilda boost → top30 0.556 (remis), walls 0.65, broad 0.463 — Boss sam nie wystarcza

**Lekcja:** manualne strojenie 1-2 bonusów nie przebija progu 0.55-0.56 vs top30. Potrzebne CEM per-archetyp jak w trolley (40-parallel, 600g, per-deck best).

## Propozycja rewolucji do 1000+

### Opcja A: Dokończyć Alakazam (rekomendacja drugiej gałęzi)
- Zostawić v65 jako bazę (0.556 top30, 0.725 walls, 9-17% bench)
- Zrobić tunable wrapper v65_tunable.py z env vars: RARE_CANDY, POFFIN, BOSS_KO, HAND_LOW, ABILITY, RETREAT, ATTACK_KO
- CEM 20-30 configs x 5 worst matchups (Mengfei Crustle+Kanga, Darren Dhelmise/Banette, Jerry Ogerpon, Kentaro mirror, OceanMix Lucario) — 600g per config, 4 workers, ~10 min
- Cel: >0.65 vs top30 i >0.75 vs walls jednocześnie — wtedy Kaggle 800-1000+
- Docelowo polityka BC na tej talii (dane z pilota, nie z proxy)

### Opcja B: Hybrid trolley + Alakazam (nasz pomysł)
- Deck: 4 Snover +3 Dunsparce +4 Abra +2 Fezandipiti = 13 basics (no collapse), 20 Water +7 Psychic = 27E? Za dużo.
- Lepszy: YumeNeko deck + 2 Kyogre jako secondary attacker vs Dragapult (Riptide 20 per Water in discard — z 7E nie działa, potrzeba 10E)
- Test: YumeNeko 7E vs YumeNeko 10E (dodaj 3 Basic P) — czy Powerful Hand nadal działa? Hand size nie zależy od E, więc 10E może pomóc vs Dragapult (więcej energii do attach) kosztem 3 trainerów.

### Opcja C: Dragapult rewolucja (nasz wcześniejszy pomysł)
- Dragapult v44: 0.741 top30, 0.418 broad, 0.25 walls — gorszy niż trolley i Alakazam vs walls, więc nie celuje w 1000+ (ściany zabijają)

**Rekomendacja:** Opcja A — kontynuować v65 Alakazam, bo ma najwyższy sufit (1352) i strukturalne zalety (1-prize, 11 basics, przechodzi ściany). Trolley ma sufit 420-450 potwierdzony Kaggle (v61 421.4). Dragapult sufit nieznany, ale lokalnie słabszy vs walls.

## Następne kroki (bez auto-submit)

1. Skopiować v65 do `agents/v65_alakazam.py` (już jest) + `decks/top30_live/YumeNeko.csv` jako deck referencyjny
2. Zbudować `v69_tunable` z env vars i uruchomić CEM na 5 worst matchups (600g) — workflow `deck_archetype_search` już działa, można rozszerzyć na `alakazam_tune`
3. Przetestować vs broad_field + top30 + walls — cel >0.65 top30 i >0.70 walls
4. Dopiero wtedy bundle `v69_alakazam_revolution` z distinct nazwą (nie reuse!) i manual submit za zgodą usera

## Załączniki
- `agents/v65_alakazam.py` — dedykowany pilot YumeNeko, 0.556 top30, 0.725 walls
- `agents/v66_alakazam.py`, `v67`, `v68` — próby poprawy, wyniki w tabeli
- `kaggle_results/search_*.txt` — deck archetype search vs top30 (trolley 0.907 best, dragapult 0.815, YumeNeko 0.278 z v44)
- Workflow `.github/workflows/deck_archetype_search.yml` — multiprocessing gauntlet_ffi, 27 decków x2 gry, 90s

