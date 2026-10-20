# FINAL - Ostatnia szansa - v79/v80/v81

**Data:** 2026-10-20 22:50 UTC
**Branch:** arena/c87f7a48-pokemon
**Status:** active - ostatnia szansa przed kasacją projektu

## Wyniki Kaggle (poll 2026-10-20T22:45:25Z)

| Submission | Score | Date | Status | vs v67 local |
|------------|-------|------|--------|--------------|
| v79_final.tar.gz | **522.3 peak / 486.5 current** | 2026-10-20 21:19 | COMPLETE | 7-3 0.700 |
| v80_final.tar.gz | 499.8 -> 491.5 | 2026-10-20 21:50 | COMPLETE | 8-2 0.800 |
| v81_final.tar.gz | 350.8 | 2026-10-20 22:25 | COMPLETE | 4-6 0.400 |
| v78_rl.tar.gz BC6000+PPO | 438.4 | 2026-10-19 22:22 | COMPLETE | 14-6 0.700 |
| v78_rl.tar.gz BC2000 | 390.8 | 2026-10-19 22:33 | COMPLETE | 7-13 0.350 |
| v70_horizon | 450.8 | 2026-10-18 | COMPLETE | - |
| v67_wall | 443.2 | 2026-10-17 | COMPLETE | - |

**NEW BEST: v79_final 522.3 peak (486.5 current) - +71.5 vs v70_horizon 450.8, +79.1 vs v67_wall 443.2**

Field: 459 teams, best 1357.2, median 674.0, top25% 880.4, top50% 674.0
Our 522.3 ~ place ~350/459 top 76% - nadal daleko od 880 top25%, ale progres +71.5

## Analiza przegranych (83 lossy z v78)

- KYOGRE mirror: 33 straty (39.8%) - 15W-12L 0.56 i 17W-21L 0.45
- ? (Crustle/Kangaskhan/Froslass/Dragapult): 21 strat (25.3%) - 7W-11L 0.39 i 5W-10L 0.33
- MEOWTH+FEZANDIP: 9 strat (10.8%) - 5W-6L 0.45
- FEZANDIP (pure): 9 strat (10.8%) - **2W-7L 0.22 - NAJGORSZY**
- LUCARIO: 6 strat - 9W-2L 0.82 (dobrze)

Top przeciwnicy: Don't foget me 0-3, SadLiT 0-3, Julian M 0-3, mo 0-3, Mitsuaki Inoue 0-3

## Co zrobiono w v79/v80/v81

### v79_final (BEST 522.3)
- Baza: v70_judge.py 2931 linii (450.8) - najlepsza heurystyka
- Dodano: anti-FEZANDIP Judge board<=4 (było tylko hand>=5, teraz zawsze gdy board<=4 vs FEZANDIP)
- Deck: v70_judge.csv 34 Water, 2 Kyogre, 4 Snover, 4 Aboma, 4 Ultra Ball, 1 Trolley (ACE), 2 Mega Signal, 3 Petrel, 4 Lillie, 1 Beach, 1 Judge + 1 Boss (34W 3UB 2Petrel Judge Boss) = 60 legal, 1 ACE
- Local vs v67: 7-3 0.700
- Gauntlet FFI vs top7_live: 36W-8L 0.818 (worst Darren_Sheehan 0-2, Eugen_LNCanti 0-2)
- Kaggle: 522.3 peak -> 486.5 current (variance)

### v80_final (491.5)
- Deck: 33W 3UB 2Petrel Judge Boss Amarys NightStretcher = 60 legal, 1 ACE
- Local vs v67: 8-2 0.800 - najlepszy vs v67!
- Kaggle: 499.8 -> 491.5 - gorszy niż v79 mimo lepszego vs v67, bo mniej Water = mniej consistency w mirror

### v81_final (350.8)
- Dodano soft lethal +200 gated + mask dominated (bench guard)
- Local vs v67: 4-6 0.400 - pogorszenie
- Kaggle: 350.8 - najgorszy, soft lethal nie działa w tym meta

## Wnioski i next steps (jeśli projekt przetrwa)

1. **FEZANDIP 22%** - v79 poprawia Judge board<=4, ale nadal słabo. Potrzeba Boss +180 (mamy w decku) + Kyogre pref vs snipe 100. v69 resistant miał board<=4 Judge+250 Boss+180 - my mamy tylko Judge, Boss nie zawsze w hand.
2. **? archetypy 33-39%** - Crustle/Kangaskhan/Froslass - potrzeba taniego searchu w wąskich bramkach + meta-counter rotacja
3. **KYOGRE mirror 45-56%** - powinno być 50%, tracimy przez flood guard. v70 miał 0.918 top30, więc jego heurystyka lepsza w mirror niż RL.
4. **Deck**: 34 Water + Judge + Boss = najlepszy kompromis (7-3 vs v67, 522.3 Kaggle). 33 Water + więcej tech = 8-2 vs v67 ale 415-491 Kaggle - mniej Water = mniej consistency w mirror który jest 40% gier Kaggle.
5. **RL vs Heurystyka**: RL BC6000+PPO 438.4 < Heurystyka v70 450.8 < Heurystyka v79 522.3. Heurystyka wciąż lepsza od RL w tym meta. Potrzeba Transformer 1-10M + GRU belief + pointer head (YumeNeko 1357) żeby przebić 1000.
6. **Gauntlet Rust**: nadal fails na `_build_plan` dla RL agentów - do naprawy: gauntlet_live.py rebind deck logika nie działa dla RL

## Pliki finalne

- `agents/v79_final.py` 2970 linii - BEST 522.3 peak
- `decks/v79_final.csv` 60 kart - 34W Judge Boss
- `bundles/v79_final.tar.gz` 152K flat (main.py+deck.csv+card_index.json) - no ERROR
- `agents/v80_final.py` 3004 linii - 8-2 vs v67
- `agents/v81_final.py` 3024 linii - soft lethal test
- `kaggle_results/our_replays/` - 83 lossy, 67 replays, episodes_table.csv

## Ostatnia submisja

v79_final resubmitted 2026-10-20 22:50 UTC as final attempt - oczekiwanie na wynik, 2 submissions remaining today.
