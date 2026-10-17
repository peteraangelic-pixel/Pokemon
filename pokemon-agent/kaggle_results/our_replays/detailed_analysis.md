# Detailed Loss Analysis - Alakazam

Total losses: 71

## By detailed reason
- WIPE_0_EMPTY: 21 (29.6%)
- WIPE_1_SINGLE: 21 (29.6%)
- RISK_2_LOW: 9 (12.7%)
- OTHER_?: 8 (11.3%)
- OTHER_KYOGRE: 5 (7.0%)
- OTHER_FEZANDIP: 4 (5.6%)
- OTHER_MEOWTH+FEZANDIP: 2 (2.8%)
- BENCH_DISADV_3vs6_?: 1 (1.4%)

## By opponent arch
- KYOGRE: 24
- ?: 20
- MEOWTH+FEZANDIP: 11
- FEZANDIP: 9
- LUCARIO: 5
- LATIAS+CLEFAIRY: 1
- CLEFAIRY+FEZANDIP: 1

## By turn
- T5: 1
- T7: 3
- T8: 2
- T9: 5
- T10: 5
- T11: 10
- T12: 5
- T13: 6
- T14: 4
- T15: 9
- T16: 3
- T17: 5
- T18: 2
- T19: 3
- T21: 2
- T22: 1
- T23: 2
- T24: 1
- T37: 1
- T41: 1

## Wipe losses deep dive (first 20)
### 124677663 vs PeterSharps (KYOGRE) T14
- our_board: []
- opp_board: ['A:card723(100/350)', 'B:card721(150)']
- our_ko: [] opp_ko: []
- last_logs: [{'cardId': 3, 'fromArea': 1, 'playerIndex': 1, 'serial': 89, 'toArea': 3, 'type': 6}, {'cardId': 1227, 'fromArea': 1, 'playerIndex': 1, 'serial': 71, 'toArea': 3, 'type': 6}, {'cardId': 722, 'playerIndex': 0, 'putDamageCounter': False, 'serial': 10, 'type': 16, 'value': -200}, {'cardId': 722, 'fromArea': 4, 'playerIndex': 0, 'serial': 10, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 44, 'toArea': 3, 'type': 6}]
- moves_tail: [{'turn': 8, 'type': 0, 'opt': None}, {'turn': 8, 'type': 0, 'opt': None}, {'turn': 8, 'type': 0, 'opt': None}, {'turn': 8, 'type': 0, 'opt': None}, {'turn': 8, 'type': 0, 'opt': None}]

### 124678236 vs cocosu3434 (LATIAS+CLEFAIRY) T12
- our_board: []
- opp_board: ['A:card1380(140/140)', 'B:card184(210)', 'B:card272(190)', 'B:card44(260)', 'B:card305(70)', 'B:card1380(140)']
- our_ko: [] opp_ko: []
- last_logs: [{'cardId': 723, 'playerIndex': 0, 'putDamageCounter': False, 'serial': 3, 'type': 16, 'value': -170}, {'cardId': 723, 'fromArea': 4, 'playerIndex': 0, 'serial': 3, 'toArea': 3, 'type': 6}, {'cardId': 722, 'fromArea': 10, 'playerIndex': 0, 'serial': 7, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 48, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 35, 'toArea': 3, 'type': 6}]
- moves_tail: [{'turn': 8, 'type': 1, 'opt': None}, {'turn': 8, 'type': 1, 'opt': None}, {'turn': 8, 'type': 1, 'opt': None}, {'turn': 8, 'type': 1, 'opt': None}, {'turn': 8, 'type': 1, 'opt': None}]

### 124678985 vs pika28samson (FEZANDIP) T12
- our_board: []
- opp_board: ['A:card743(140/140)', 'B:card743(140)', 'B:card742(80)']
- our_ko: [] opp_ko: []
- last_logs: [{'cardId': 723, 'playerIndex': 0, 'putDamageCounter': True, 'serial': 5, 'type': 16, 'value': -360}, {'cardId': 723, 'fromArea': 4, 'playerIndex': 0, 'serial': 5, 'toArea': 3, 'type': 6}, {'cardId': 722, 'fromArea': 10, 'playerIndex': 0, 'serial': 7, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 43, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 47, 'toArea': 3, 'type': 6}]
- moves_tail: [{'turn': 5, 'type': 1, 'opt': None}, {'turn': 5, 'type': 1, 'opt': None}, {'turn': 5, 'type': 1, 'opt': None}, {'turn': 5, 'type': 1, 'opt': None}, {'turn': 5, 'type': 1, 'opt': None}]

### 124679029 vs yyx673 (LUCARIO) T13
- our_board: ['A:card723(20/350)', 'B:card721(150)']
- opp_board: ['A:card678(340/340)', 'B:card675(110)', 'B:card675(70)', 'B:card676(110)', 'B:card673(80)']
- our_ko: [] opp_ko: []
- last_logs: [{'cardId': 3, 'fromArea': 12, 'playerIndex': 1, 'serial': 96, 'toArea': 1, 'type': 6}, {'cardId': 722, 'fromArea': 12, 'playerIndex': 1, 'serial': 70, 'toArea': 1, 'type': 6}, {'cardId': 1262, 'fromArea': 12, 'playerIndex': 1, 'serial': 117, 'toArea': 1, 'type': 6}, {'cardId': 3, 'fromArea': 12, 'playerIndex': 1, 'serial': 91, 'toArea': 1, 'type': 6}, {'playerIndex': 1, 'type': 0}]
- moves_tail: [{'turn': 12, 'type': 0, 'opt': None}, {'turn': 12, 'type': 0, 'opt': None}, {'turn': 12, 'type': 0, 'opt': None}, {'turn': 12, 'type': 0, 'opt': None}, {'turn': 12, 'type': 0, 'opt': None}]

### 124680392 vs the soul hunter (KYOGRE) T11
- our_board: ['A:card722(90/90)']
- opp_board: ['A:card722(90/90)']
- our_ko: [] opp_ko: []
- last_logs: [{'cardId': 3, 'cardIdTarget': 722, 'playerIndex': 1, 'serial': 86, 'serialTarget': 69, 'type': 11}]
- moves_tail: [{'turn': 2, 'type': 0, 'opt': None}, {'turn': 2, 'type': 0, 'opt': None}, {'turn': 2, 'type': 0, 'opt': None}, {'turn': 2, 'type': 0, 'opt': None}, {'turn': 2, 'type': 0, 'opt': None}]

### 124681089 vs DavideSanta (?) T11
- our_board: ['B:card723(350)']
- opp_board: ['A:card96(210/210)', 'B:card96(210)']
- our_ko: [] opp_ko: []
- last_logs: [{'attackId': 120, 'cardId': 96, 'playerIndex': 1, 'serial': 64, 'type': 15}, {'cardId': 723, 'playerIndex': 0, 'putDamageCounter': False, 'serial': 5, 'type': 16, 'value': -270}, {'cardId': 723, 'fromArea': 4, 'playerIndex': 0, 'serial': 5, 'toArea': 3, 'type': 6}, {'cardId': 722, 'fromArea': 10, 'playerIndex': 0, 'serial': 8, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 52, 'toArea': 3, 'type': 6}]
- moves_tail: [{'turn': 10, 'type': 0, 'opt': None}, {'turn': 10, 'type': 0, 'opt': None}, {'turn': 10, 'type': 0, 'opt': None}, {'turn': 10, 'type': 0, 'opt': None}, {'turn': 10, 'type': 0, 'opt': None}]

### 124682458 vs Utandra (MEOWTH+FEZANDIP) T7
- our_board: []
- opp_board: ['A:card96(120/210)', 'B:card92(40)', 'B:card710(160)', 'B:card140(210)', 'B:card96(210)']
- our_ko: [] opp_ko: []
- last_logs: [{'attackId': 120, 'cardId': 96, 'playerIndex': 1, 'serial': 63, 'type': 15}, {'cardId': 721, 'playerIndex': 0, 'putDamageCounter': False, 'serial': 16, 'type': 16, 'value': -240}, {'cardId': 721, 'fromArea': 4, 'playerIndex': 0, 'serial': 16, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 25, 'toArea': 3, 'type': 6}]
- moves_tail: [{'turn': 6, 'type': 0, 'opt': None}, {'turn': 6, 'type': 0, 'opt': None}, {'turn': 6, 'type': 0, 'opt': None}, {'turn': 6, 'type': 0, 'opt': None}, {'turn': 6, 'type': 0, 'opt': None}]

### 124683814 vs Prashant Rawat (?) T23
- our_board: ['A:card723(110/350)']
- opp_board: ['A:card345(110/150)', 'B:card345(170)', 'B:card345(150)', 'B:card344(70)']
- our_ko: [] opp_ko: []
- last_logs: [{'cardId': 3, 'cardIdTarget': 723, 'playerIndex': 1, 'serial': 83, 'serialTarget': 66, 'type': 11}]
- moves_tail: [{'turn': 19, 'type': 0, 'opt': None}, {'turn': 19, 'type': 0, 'opt': None}, {'turn': 19, 'type': 0, 'opt': None}, {'turn': 19, 'type': 0, 'opt': None}, {'turn': 19, 'type': 0, 'opt': None}]

### 124685933 vs Elbachir Salik (KYOGRE) T7
- our_board: []
- opp_board: ['A:card723(300/350)', 'B:card722(90)']
- our_ko: [] opp_ko: []
- last_logs: [{'cardId': 3, 'fromArea': 1, 'playerIndex': 1, 'serial': 112, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 1, 'playerIndex': 1, 'serial': 106, 'toArea': 3, 'type': 6}, {'cardId': 722, 'playerIndex': 0, 'putDamageCounter': False, 'serial': 7, 'type': 16, 'value': -400}, {'cardId': 722, 'fromArea': 4, 'playerIndex': 0, 'serial': 7, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 32, 'toArea': 3, 'type': 6}]
- moves_tail: [{'turn': 6, 'type': 0, 'opt': None}, {'turn': 6, 'type': 0, 'opt': None}, {'turn': 6, 'type': 0, 'opt': None}, {'turn': 6, 'type': 0, 'opt': None}, {'turn': 6, 'type': 0, 'opt': None}]

### 124687298 vs mo (LUCARIO) T17
- our_board: []
- opp_board: ['A:card678(340/340)', 'B:card675(110)', 'B:card677(80)', 'B:card676(110)', 'B:card675(110)']
- our_ko: [] opp_ko: []
- last_logs: [{'attackId': 983, 'cardId': 678, 'playerIndex': 1, 'serial': 67, 'type': 15}, {'cardId': 721, 'playerIndex': 0, 'putDamageCounter': False, 'serial': 15, 'type': 16, 'value': -270}, {'cardId': 721, 'fromArea': 4, 'playerIndex': 0, 'serial': 15, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 36, 'toArea': 3, 'type': 6}]
- moves_tail: [{'turn': 15, 'type': 1, 'opt': None}, {'turn': 15, 'type': 1, 'opt': None}, {'turn': 15, 'type': 1, 'opt': None}, {'turn': 15, 'type': 1, 'opt': None}, {'turn': 15, 'type': 1, 'opt': None}]

### 124689955 vs Hitisha Goyal (KYOGRE) T8
- our_board: []
- opp_board: ['A:card723(280/350)', 'B:card723(350)', 'B:card723(350)', 'B:card722(90)']
- our_ko: [] opp_ko: []
- last_logs: [{'cardId': 3, 'fromArea': 1, 'playerIndex': 1, 'serial': 108, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 1, 'playerIndex': 1, 'serial': 97, 'toArea': 3, 'type': 6}, {'cardId': 721, 'playerIndex': 0, 'putDamageCounter': False, 'serial': 16, 'type': 16, 'value': -600}, {'cardId': 721, 'fromArea': 4, 'playerIndex': 0, 'serial': 16, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 24, 'toArea': 3, 'type': 6}]
- moves_tail: [{'turn': 4, 'type': 0, 'opt': None}, {'turn': 4, 'type': 0, 'opt': None}, {'turn': 4, 'type': 0, 'opt': None}, {'turn': 4, 'type': 0, 'opt': None}, {'turn': 4, 'type': 0, 'opt': None}]

### 124690629 vs Rashid Khazeiynasab (LUCARIO) T13
- our_board: ['B:card721(150)', 'B:card721(150)']
- opp_board: ['A:card678(310/340)', 'B:card676(110)', 'B:card678(340)', 'B:card675(110)', 'B:card44(260)', 'B:card678(340)']
- our_ko: [] opp_ko: []
- last_logs: [{'attackId': 983, 'cardId': 678, 'playerIndex': 1, 'serial': 69, 'type': 15}, {'cardId': 722, 'playerIndex': 0, 'putDamageCounter': False, 'serial': 8, 'type': 16, 'value': -270}, {'cardId': 722, 'fromArea': 4, 'playerIndex': 0, 'serial': 8, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 28, 'toArea': 3, 'type': 6}]
- moves_tail: [{'turn': 12, 'type': 0, 'opt': None}, {'turn': 12, 'type': 0, 'opt': None}, {'turn': 12, 'type': 0, 'opt': None}, {'turn': 12, 'type': 0, 'opt': None}, {'turn': 12, 'type': 0, 'opt': None}]

### 124692630 vs Angel Francisco Aguayo Salazar (?) T11
- our_board: []
- opp_board: ['A:card781(150/280)', 'B:card337(180)', 'B:card781(280)', 'B:card781(280)', 'B:card781(280)']
- our_ko: [] opp_ko: []
- last_logs: [{'attackId': 1130, 'cardId': 781, 'playerIndex': 1, 'serial': 65, 'type': 15}, {'cardId': 721, 'playerIndex': 0, 'putDamageCounter': False, 'serial': 15, 'type': 16, 'value': -230}, {'cardId': 721, 'fromArea': 4, 'playerIndex': 0, 'serial': 15, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 36, 'toArea': 3, 'type': 6}]
- moves_tail: [{'turn': 9, 'type': 4, 'opt': None}, {'turn': 9, 'type': 4, 'opt': None}, {'turn': 9, 'type': 4, 'opt': None}, {'turn': 9, 'type': 4, 'opt': None}, {'turn': 9, 'type': 4, 'opt': None}]

### 124693323 vs SC (MEOWTH+FEZANDIP) T15
- our_board: []
- opp_board: ['A:card121(250/320)', 'B:card121(320)', 'B:card121(320)', 'B:card112(110)']
- our_ko: [] opp_ko: []
- last_logs: [{'attackId': 154, 'cardId': 121, 'playerIndex': 1, 'serial': 83, 'type': 15}, {'cardId': 721, 'playerIndex': 0, 'putDamageCounter': False, 'serial': 15, 'type': 16, 'value': -200}, {'cardId': 721, 'fromArea': 4, 'playerIndex': 0, 'serial': 15, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 48, 'toArea': 3, 'type': 6}]
- moves_tail: [{'turn': 14, 'type': 0, 'opt': None}, {'turn': 14, 'type': 0, 'opt': None}, {'turn': 14, 'type': 0, 'opt': None}, {'turn': 14, 'type': 0, 'opt': None}, {'turn': 14, 'type': 0, 'opt': None}]

### 124694000 vs Mibbles (FEZANDIP) T11
- our_board: []
- opp_board: ['A:card743(70/140)', 'B:card743(140)', 'B:card742(80)', 'B:card743(140)', 'B:card305(70)']
- our_ko: [] opp_ko: []
- last_logs: [{'attackId': 1072, 'cardId': 743, 'playerIndex': 1, 'serial': 87, 'type': 15}, {'cardId': 722, 'playerIndex': 0, 'putDamageCounter': True, 'serial': 8, 'type': 16, 'value': -500}, {'cardId': 722, 'fromArea': 4, 'playerIndex': 0, 'serial': 8, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 33, 'toArea': 3, 'type': 6}]
- moves_tail: [{'turn': 10, 'type': 0, 'opt': None}, {'turn': 10, 'type': 0, 'opt': None}, {'turn': 10, 'type': 0, 'opt': None}, {'turn': 10, 'type': 0, 'opt': None}, {'turn': 10, 'type': 0, 'opt': None}]

### 124695345 vs LivMaAn (MEOWTH+FEZANDIP) T10
- our_board: []
- opp_board: ['A:card150(330/330)', 'B:card140(210)', 'B:card710(160)', 'B:card93(80)', 'B:card1071(170)', 'B:card96(210)']
- our_ko: [] opp_ko: []
- last_logs: [{'attackId': 195, 'cardId': 150, 'playerIndex': 1, 'serial': 91, 'type': 15}, {'cardId': 723, 'playerIndex': 0, 'putDamageCounter': False, 'serial': 4, 'type': 16, 'value': -450}, {'cardId': 723, 'fromArea': 4, 'playerIndex': 0, 'serial': 4, 'toArea': 3, 'type': 6}, {'cardId': 722, 'fromArea': 10, 'playerIndex': 0, 'serial': 9, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 34, 'toArea': 3, 'type': 6}]
- moves_tail: [{'turn': 6, 'type': 0, 'opt': None}, {'turn': 6, 'type': 0, 'opt': None}, {'turn': 6, 'type': 0, 'opt': None}, {'turn': 6, 'type': 0, 'opt': None}, {'turn': 6, 'type': 0, 'opt': None}]

### 124696068 vs Sayuru Rehan Bopitiya (FEZANDIP) T15
- our_board: ['B:card722(90)', 'B:card722(90)']
- opp_board: ['A:card743(130/140)', 'B:card305(70)', 'B:card742(80)', 'B:card343(80)', 'B:card305(70)']
- our_ko: [] opp_ko: []
- last_logs: [{'attackId': 1072, 'cardId': 743, 'playerIndex': 1, 'serial': 87, 'type': 15}, {'cardId': 722, 'playerIndex': 0, 'putDamageCounter': True, 'serial': 7, 'type': 16, 'value': -620}, {'cardId': 722, 'fromArea': 4, 'playerIndex': 0, 'serial': 7, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 34, 'toArea': 3, 'type': 6}]
- moves_tail: [{'turn': 14, 'type': 0, 'opt': None}, {'turn': 14, 'type': 0, 'opt': None}, {'turn': 14, 'type': 0, 'opt': None}, {'turn': 14, 'type': 0, 'opt': None}, {'turn': 14, 'type': 0, 'opt': None}]

### 124696704 vs Rajveer Vora (?) T21
- our_board: ['A:card721(10/150)']
- opp_board: ['A:card1074(80/150)', 'B:card344(40)', 'B:card1073(40)']
- our_ko: [] opp_ko: []
- last_logs: [{'cardId': 3, 'cardIdTarget': 721, 'playerIndex': 1, 'serial': 108, 'serialTarget': 75, 'type': 11}]
- moves_tail: [{'turn': 6, 'type': 0, 'opt': None}, {'turn': 6, 'type': 0, 'opt': None}, {'turn': 6, 'type': 0, 'opt': None}, {'turn': 6, 'type': 0, 'opt': None}, {'turn': 6, 'type': 0, 'opt': None}]

### 124697372 vs Don't foget me (?) T10
- our_board: ['A:card722(90/90)', 'B:card721(150)']
- opp_board: ['A:card1406(310/340)', 'B:card547(220)', 'B:card85(70)', 'B:card85(70)', 'B:card547(220)', 'B:card547(220)']
- our_ko: [] opp_ko: []
- last_logs: [{'cardIdActive': 721, 'cardIdBench': 722, 'playerIndex': 1, 'serialActive': 76, 'serialBench': 68, 'type': 8}]
- moves_tail: [{'turn': 9, 'type': 1, 'opt': None}, {'turn': 9, 'type': 0, 'opt': None}, {'turn': 9, 'type': 0, 'opt': None}, {'turn': 9, 'type': 0, 'opt': None}, {'turn': 9, 'type': 0, 'opt': None}]

### 124699418 vs Richard Guo (MEOWTH+FEZANDIP) T9
- our_board: ['A:card721(130/150)']
- opp_board: ['B:card120(90)', 'B:card120(90)']
- our_ko: [] opp_ko: []
- last_logs: [{'cardId': 3, 'fromArea': 8, 'playerIndex': 1, 'serial': 106, 'toArea': 3, 'type': 6}, {'cardId': 235, 'fromArea': 4, 'playerIndex': 0, 'serial': 15, 'toArea': 3, 'type': 6}, {'cardId': 5, 'fromArea': 8, 'playerIndex': 0, 'serial': 55, 'toArea': 3, 'type': 6}]
- moves_tail: [{'turn': 5, 'type': 1, 'opt': None}, {'turn': 5, 'type': 1, 'opt': None}, {'turn': 5, 'type': 1, 'opt': None}, {'turn': 5, 'type': 1, 'opt': None}, {'turn': 5, 'type': 1, 'opt': None}]

## Recommendations for resistant version

### Observed dominant failure: bench wipe 59% (21 empty +21 single)
- Fix v70 had guard board<=2 prizes<=3, but losses still show board 0/1 at T14 avg
- Need stricter: board<=3 and prizes<=4, always bench basic if available
- Boost Poffin (1086) and Nest Ball (1152) search when board<=3
- Boost recovery Night Stretcher (1097) Sacred Ash (1129) when board<=3
- Never promote Abra (741) when board<=3, prefer Alakazam > Dudunsparce > Dunsparce
- In main phase, if board<=3, prioritize benching over Boss KO unless Boss gives immediate prize win
- Also need to handle early losses T<10:  maybe mulligan / basic count 6 is low? Check deck has 6 basics (Dunsparce 4 + Abra 4? actually 4+4=8) — should be ok, but maybe need more search
- Vs KYOGRE (24 losses): Kyogre 350 HP, our max 20*hand. Need hand refill Dawns/Hilda more aggressively when vs Kyogre arch
- Vs ? (20 losses): unknown arch, likely Crustle/Kangaskhan wall — need Boss cheap prize race logic

### Proposed v72 knobs
- PTCG_BENCH_GUARD_BOARD=3 (was 2)
- PTCG_BENCH_GUARD_PRIZE=4 (was 3)
- PTCG_POFFIN_BOOST when board<=3
- PTCG_RECOVERY_BOOST when board<=3
- PTCG_NO_ABRA_PROMO when board<=3
- PTCG_HAND_REFILL_THRESH=5 (was 4) vs Kyogre
