# Detailed Loss Analysis - Alakazam

Total losses: 27

## By detailed reason
- WIPE_1_SINGLE: 11 (40.7%)
- WIPE_0_EMPTY: 6 (22.2%)
- OTHER_?: 4 (14.8%)
- RISK_2_LOW: 4 (14.8%)
- BENCH_DISADV_3vs5_MEOWTH+FEZANDIP: 1 (3.7%)
- EARLY_LOSS_T9_KYOGRE: 1 (3.7%)

## By opponent arch
- KYOGRE: 11
- ?: 10
- MEOWTH+FEZANDIP: 2
- FEZANDIP: 2
- LUCARIO: 1
- LATIAS+MEOWTH+FEZANDIP: 1

## By turn
- T8: 2
- T9: 4
- T10: 3
- T11: 3
- T12: 1
- T13: 1
- T14: 3
- T17: 2
- T19: 2
- T23: 2
- T27: 1
- T28: 1
- T30: 1
- T31: 1

## Wipe losses deep dive (first 20)
### 124858159 vs Sliver-Ze (KYOGRE) T10
- our_board: ['A:card722(90/90)']
- opp_board: ['A:card723(250/350)', 'B:card723(350)', 'B:card721(150)']
- our_ko: [] opp_ko: []
- last_logs: [{'cardId': 3, 'cardIdTarget': 722, 'playerIndex': 1, 'serial': 64, 'serialTarget': 99, 'type': 11}]
- moves_tail: [{'turn': 9, 'type': 0, 'opt': None}, {'turn': 9, 'type': 0, 'opt': None}, {'turn': 9, 'type': 0, 'opt': None}, {'turn': 9, 'type': 0, 'opt': None}, {'turn': 9, 'type': 0, 'opt': None}]

### 124859689 vs Morokoshi (MEOWTH+FEZANDIP) T13
- our_board: ['B:card721(150)']
- opp_board: ['A:card121(70/320)', 'B:card121(20)', 'B:card120(90)', 'B:card120(90)', 'B:card235(30)']
- our_ko: [] opp_ko: []
- last_logs: [{'cardId': 721, 'fromArea': 4, 'playerIndex': 0, 'serial': 37, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 62, 'toArea': 3, 'type': 6}, {'cardId': 133, 'fromArea': 5, 'playerIndex': 1, 'serial': 84, 'toArea': 3, 'type': 6}, {'cardId': 132, 'fromArea': 10, 'playerIndex': 1, 'serial': 83, 'toArea': 3, 'type': 6}, {'cardId': 131, 'fromArea': 10, 'playerIndex': 1, 'serial': 82, 'toArea': 3, 'type': 6}]
- moves_tail: [{'turn': 11, 'type': 0, 'opt': None}, {'turn': 11, 'type': 0, 'opt': None}, {'turn': 11, 'type': 0, 'opt': None}, {'turn': 12, 'type': 1, 'opt': None}, {'turn': 12, 'type': 1, 'opt': None}]

### 124860240 vs lswuwu (LUCARIO) T11
- our_board: []
- opp_board: ['A:card678(190/340)', 'B:card673(80)']
- our_ko: [] opp_ko: []
- last_logs: [{'attackId': 982, 'cardId': 678, 'playerIndex': 1, 'serial': 90, 'type': 15}, {'cardId': 721, 'playerIndex': 0, 'putDamageCounter': False, 'serial': 37, 'type': 16, 'value': -130}, {'cardId': 721, 'fromArea': 4, 'playerIndex': 0, 'serial': 37, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 12, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 10, 'toArea': 3, 'type': 6}]
- moves_tail: [{'turn': 10, 'type': 0, 'opt': None}, {'turn': 10, 'type': 0, 'opt': None}, {'turn': 10, 'type': 0, 'opt': None}, {'turn': 10, 'type': 0, 'opt': None}, {'turn': 10, 'type': 0, 'opt': None}]

### 124860792 vs diujin217 (KYOGRE) T8
- our_board: ['A:card723(350/350)']
- opp_board: ['A:card723(350/350)', 'B:card722(90)', 'B:card722(90)']
- our_ko: [] opp_ko: []
- last_logs: [{'playerIndex': 0, 'type': 5}, {'cardId': 3, 'cardIdTarget': 723, 'playerIndex': 0, 'serial': 62, 'serialTarget': 11, 'type': 11}, {'playerIndex': 0, 'type': 3}, {'playerIndex': 1, 'type': 2}, {'cardId': 3, 'playerIndex': 1, 'serial': 89, 'type': 4}]
- moves_tail: [{'turn': 7, 'type': 0, 'opt': None}, {'turn': 7, 'type': 0, 'opt': None}, {'turn': 7, 'type': 0, 'opt': None}, {'turn': 7, 'type': 0, 'opt': None}, {'turn': 7, 'type': 0, 'opt': None}]

### 124860840 vs Dnyanesh (KYOGRE) T11
- our_board: ['B:card722(90)']
- opp_board: ['A:card721(150/150)', 'B:card723(350)']
- our_ko: [] opp_ko: []
- last_logs: [{'playerIndex': 1, 'type': 0}, {'cardId': 723, 'fromArea': 4, 'playerIndex': 0, 'serial': 42, 'toArea': 3, 'type': 6}, {'cardId': 722, 'fromArea': 10, 'playerIndex': 0, 'serial': 39, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 30, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 19, 'toArea': 3, 'type': 6}]
- moves_tail: [{'turn': 9, 'type': 1, 'opt': None}, {'turn': 9, 'type': 1, 'opt': None}, {'turn': 9, 'type': 1, 'opt': None}, {'turn': 9, 'type': 1, 'opt': None}, {'turn': 9, 'type': 1, 'opt': None}]

### 124861365 vs Ricardo Paizinho (?) T11
- our_board: ['A:card721(150/150)']
- opp_board: ['B:card305(70)', 'B:card742(80)']
- our_ko: [] opp_ko: []
- last_logs: [{'cardId': 3, 'fromArea': 3, 'playerIndex': 1, 'serial': 77, 'toArea': 1, 'type': 6}, {'playerIndex': 1, 'type': 0}, {'cardId': 743, 'fromArea': 4, 'playerIndex': 0, 'serial': 26, 'toArea': 3, 'type': 6}, {'cardId': 741, 'fromArea': 10, 'playerIndex': 0, 'serial': 19, 'toArea': 3, 'type': 6}, {'cardId': 19, 'fromArea': 8, 'playerIndex': 0, 'serial': 8, 'toArea': 3, 'type': 6}]
- moves_tail: [{'turn': 7, 'type': 1, 'opt': None}, {'turn': 7, 'type': 1, 'opt': None}, {'turn': 7, 'type': 1, 'opt': None}, {'turn': 7, 'type': 1, 'opt': None}, {'turn': 7, 'type': 1, 'opt': None}]

### 124863037 vs tategami (?) T23
- our_board: ['A:card722(90/90)']
- opp_board: ['A:card103(60/60)', 'B:card103(60)']
- our_ko: [] opp_ko: []
- last_logs: [{'cardId': 3, 'cardIdTarget': 722, 'playerIndex': 1, 'serial': 80, 'serialTarget': 101, 'type': 11}]
- moves_tail: [{'turn': 1, 'type': 0, 'opt': None}, {'turn': 1, 'type': 0, 'opt': None}, {'turn': 1, 'type': 0, 'opt': None}, {'turn': 1, 'type': 0, 'opt': None}, {'turn': 1, 'type': 0, 'opt': None}]

### 124864153 vs Revue (?) T30
- our_board: []
- opp_board: ['A:card345(230/270)', 'B:card756(130)', 'B:card344(70)']
- our_ko: [] opp_ko: []
- last_logs: [{'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 16, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 34, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 26, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 23, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 13, 'toArea': 3, 'type': 6}]
- moves_tail: [{'turn': 20, 'type': 0, 'opt': None}, {'turn': 20, 'type': 0, 'opt': None}, {'turn': 20, 'type': 0, 'opt': None}, {'turn': 20, 'type': 0, 'opt': None}, {'turn': 20, 'type': 0, 'opt': None}]

### 124864690 vs Raihan Ramadistra (MEOWTH+FEZANDIP) T14
- our_board: ['A:card723(30/350)', 'B:card721(70)', 'B:card723(270)']
- opp_board: ['B:card120(90)', 'B:card1071(170)', 'B:card140(210)', 'B:card112(100)', 'B:card120(70)']
- our_ko: ['card722', 'card722', 'card722', 'card722', 'card722', 'card722'] opp_ko: []
- last_logs: [{'cardId': 121, 'fromArea': 4, 'playerIndex': 0, 'serial': 25, 'toArea': 3, 'type': 6}, {'cardId': 120, 'fromArea': 10, 'playerIndex': 0, 'serial': 22, 'toArea': 3, 'type': 6}, {'cardId': 119, 'fromArea': 10, 'playerIndex': 0, 'serial': 19, 'toArea': 3, 'type': 6}, {'cardId': 5, 'fromArea': 8, 'playerIndex': 0, 'serial': 7, 'toArea': 3, 'type': 6}, {'cardId': 2, 'fromArea': 8, 'playerIndex': 0, 'serial': 3, 'toArea': 3, 'type': 6}]
- moves_tail: [{'turn': 13, 'type': 1, 'opt': None}, {'turn': 13, 'type': 1, 'opt': None}, {'turn': 13, 'type': 1, 'opt': None}, {'turn': 13, 'type': 1, 'opt': None}, {'turn': 13, 'type': 1, 'opt': None}]

### 124865226 vs Elbachir Salik (KYOGRE) T9
- our_board: ['A:card721(150/150)']
- opp_board: ['A:card723(240/350)']
- our_ko: [] opp_ko: []
- last_logs: [{'cardId': 3, 'cardIdTarget': 721, 'playerIndex': 1, 'serial': 95, 'serialTarget': 97, 'type': 11}]
- moves_tail: [{'turn': 6, 'type': 0, 'opt': None}, {'turn': 6, 'type': 0, 'opt': None}, {'turn': 6, 'type': 0, 'opt': None}, {'turn': 6, 'type': 0, 'opt': None}, {'turn': 6, 'type': 0, 'opt': None}]

### 124866711 vs RAHUL REDDY PULICHARLA (KYOGRE) T8
- our_board: []
- opp_board: ['A:card721(60/150)']
- our_ko: [] opp_ko: []
- last_logs: [{'cardId': 722, 'fromArea': 4, 'playerIndex': 0, 'serial': 41, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 13, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 8, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 10, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 16, 'toArea': 3, 'type': 6}]
- moves_tail: [{'turn': 7, 'type': 0, 'opt': None}, {'turn': 7, 'type': 0, 'opt': None}, {'turn': 7, 'type': 0, 'opt': None}, {'turn': 7, 'type': 0, 'opt': None}, {'turn': 7, 'type': 0, 'opt': None}]

### 124868214 vs 加油华为 (LATIAS+MEOWTH+FEZANDIP) T17
- our_board: ['A:card723(90/350)', 'B:card721(150)']
- opp_board: ['A:card121(320/320)', 'B:card121(320)', 'B:card120(90)', 'B:card1071(170)']
- our_ko: ['card721', 'card721', 'card721', 'card721', 'card721', 'card721'] opp_ko: []
- last_logs: [{'cardId': 723, 'playerIndex': 0, 'putDamageCounter': True, 'serial': 45, 'type': 16, 'value': -10}, {'cardId': 723, 'fromArea': 5, 'playerIndex': 0, 'serial': 45, 'toArea': 3, 'type': 6}, {'cardId': 722, 'fromArea': 10, 'playerIndex': 0, 'serial': 39, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 19, 'toArea': 3, 'type': 6}]
- moves_tail: [{'turn': 13, 'type': 0, 'opt': None}, {'turn': 13, 'type': 0, 'opt': None}, {'turn': 13, 'type': 0, 'opt': None}, {'turn': 13, 'type': 0, 'opt': None}, {'turn': 13, 'type': 0, 'opt': None}]

### 124869201 vs Leo (?) T31
- our_board: ['B:card723(110)', 'B:card721(150)']
- opp_board: ['A:card345(60/150)', 'B:card1074(150)', 'B:card1074(150)', 'B:card1074(150)', 'B:card345(150)', 'B:card1074(150)']
- our_ko: [] opp_ko: []
- last_logs: [{'attackId': 479, 'cardId': 345, 'playerIndex': 1, 'serial': 96, 'type': 15}, {'cardId': 723, 'playerIndex': 0, 'putDamageCounter': False, 'serial': 44, 'type': 16, 'value': -120}, {'cardId': 723, 'fromArea': 4, 'playerIndex': 0, 'serial': 44, 'toArea': 3, 'type': 6}, {'cardId': 722, 'fromArea': 10, 'playerIndex': 0, 'serial': 39, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 11, 'toArea': 3, 'type': 6}]
- moves_tail: [{'turn': 30, 'type': 0, 'opt': None}, {'turn': 30, 'type': 0, 'opt': None}, {'turn': 30, 'type': 0, 'opt': None}, {'turn': 30, 'type': 0, 'opt': None}, {'turn': 30, 'type': 0, 'opt': None}]

### 124870192 vs Mahog (?) T12
- our_board: []
- opp_board: ['A:card648(320/320)', 'B:card860(70)', 'B:card112(110)', 'B:card112(110)', 'B:card646(70)', 'B:card112(110)']
- our_ko: [] opp_ko: []
- last_logs: [{'cardId': 1097, 'fromArea': 6, 'playerIndex': 1, 'serial': 99, 'toArea': 2, 'type': 6}]
- moves_tail: [{'turn': 6, 'type': 0, 'opt': None}, {'turn': 6, 'type': 0, 'opt': None}, {'turn': 6, 'type': 0, 'opt': None}, {'turn': 6, 'type': 0, 'opt': None}, {'turn': 6, 'type': 0, 'opt': None}]

### 124870683 vs zengbo1 (KYOGRE) T9
- our_board: ['A:card721(150/150)']
- opp_board: ['A:card723(290/350)', 'B:card721(150)']
- our_ko: [] opp_ko: []
- last_logs: [{'cardId': 3, 'cardIdTarget': 721, 'playerIndex': 1, 'serial': 75, 'serialTarget': 97, 'type': 11}]
- moves_tail: [{'turn': 7, 'type': 0, 'opt': None}, {'turn': 7, 'type': 0, 'opt': None}, {'turn': 7, 'type': 0, 'opt': None}, {'turn': 7, 'type': 0, 'opt': None}, {'turn': 7, 'type': 0, 'opt': None}]

### 124872330 vs Elbachir Salik (KYOGRE) T14
- our_board: ['A:card722(90/90)']
- opp_board: ['A:card723(260/350)', 'B:card723(350)']
- our_ko: [] opp_ko: []
- last_logs: [{'cardId': 3, 'cardIdTarget': 722, 'playerIndex': 1, 'serial': 69, 'serialTarget': 99, 'type': 11}]
- moves_tail: [{'turn': 10, 'type': 0, 'opt': None}, {'turn': 10, 'type': 0, 'opt': None}, {'turn': 10, 'type': 0, 'opt': None}, {'turn': 10, 'type': 0, 'opt': None}, {'turn': 10, 'type': 0, 'opt': None}]

### 124874118 vs Mitsuaki Inoue (FEZANDIP) T19
- our_board: ['B:card723(350)']
- opp_board: ['A:card743(140/140)', 'B:card742(80)', 'B:card140(210)', 'B:card66(140)', 'B:card959(50)']
- our_ko: [] opp_ko: ['card743', 'card743', 'card743', 'card743']
- last_logs: [{'attackId': 1072, 'cardId': 743, 'playerIndex': 1, 'serial': 86, 'type': 15}, {'cardId': 723, 'playerIndex': 0, 'putDamageCounter': True, 'serial': 44, 'type': 16, 'value': -500}, {'cardId': 723, 'fromArea': 4, 'playerIndex': 0, 'serial': 44, 'toArea': 3, 'type': 6}, {'cardId': 722, 'fromArea': 10, 'playerIndex': 0, 'serial': 41, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 13, 'toArea': 3, 'type': 6}]
- moves_tail: [{'turn': 18, 'type': 1, 'opt': None}, {'turn': 18, 'type': 1, 'opt': None}, {'turn': 18, 'type': 1, 'opt': None}, {'turn': 18, 'type': 1, 'opt': None}, {'turn': 18, 'type': 1, 'opt': None}]

### 124874562 vs Riccardo Lo Bianco (?) T10
- our_board: []
- opp_board: ['A:card861(280/310)', 'B:card103(60)', 'B:card103(60)']
- our_ko: [] opp_ko: []
- last_logs: [{'attackId': 1240, 'cardId': 861, 'playerIndex': 1, 'serial': 104, 'type': 15}, {'cardId': 722, 'playerIndex': 0, 'putDamageCounter': False, 'serial': 39, 'type': 16, 'value': -300}, {'cardId': 722, 'fromArea': 4, 'playerIndex': 0, 'serial': 39, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 25, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 35, 'toArea': 3, 'type': 6}]
- moves_tail: [{'turn': 3, 'type': 0, 'opt': None}, {'turn': 3, 'type': 0, 'opt': None}, {'turn': 3, 'type': 0, 'opt': None}, {'turn': 3, 'type': 0, 'opt': None}, {'turn': 3, 'type': 0, 'opt': None}]

### 124874969 vs wdzlyq (KYOGRE) T17
- our_board: ['A:card723(350/350)', 'B:card723(350)']
- opp_board: ['A:card723(350/350)', 'B:card721(150)', 'B:card721(150)', 'B:card159(130)', 'B:card722(90)']
- our_ko: [] opp_ko: []
- last_logs: [{'cardIdActive': 723, 'cardIdBench': 723, 'playerIndex': 1, 'serialActive': 103, 'serialBench': 105, 'type': 8}]
- moves_tail: [{'turn': 11, 'type': 0, 'opt': None}, {'turn': 11, 'type': 0, 'opt': None}, {'turn': 11, 'type': 0, 'opt': None}, {'turn': 11, 'type': 0, 'opt': None}, {'turn': 11, 'type': 0, 'opt': None}]

### 124876227 vs IAMNAMNAM (FEZANDIP) T14
- our_board: ['A:card723(50/350)', 'B:card722(90)']
- opp_board: ['A:card1406(340/340)', 'B:card1331(150)', 'B:card343(80)', 'B:card140(210)', 'B:card86(100)']
- our_ko: [] opp_ko: []
- last_logs: [{'cardId': 722, 'playerIndex': 1, 'serial': 99, 'type': 10}]
- moves_tail: [{'turn': 13, 'type': 0, 'opt': None}, {'turn': 13, 'type': 0, 'opt': None}, {'turn': 13, 'type': 0, 'opt': None}, {'turn': 13, 'type': 0, 'opt': None}, {'turn': 13, 'type': 0, 'opt': None}]

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
