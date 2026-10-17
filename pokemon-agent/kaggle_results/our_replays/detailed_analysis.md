# Detailed Loss Analysis - Alakazam

Total losses: 78

## By detailed reason
- WIPE_1_SINGLE: 30 (38.5%)
- WIPE_0_EMPTY: 11 (14.1%)
- OTHER_?: 10 (12.8%)
- RISK_2_LOW: 9 (11.5%)
- OTHER_KYOGRE: 8 (10.3%)
- OTHER_LUCARIO: 3 (3.8%)
- EARLY_LOSS_T9_?: 1 (1.3%)
- OTHER_FEZANDIP: 1 (1.3%)
- OTHER_LUCARIO+FEZANDIP: 1 (1.3%)
- BENCH_DISADV_3vs5_FEZANDIP: 1 (1.3%)
- BENCH_DISADV_3vs5_MEOWTH+FEZANDIP: 1 (1.3%)
- OTHER_MEOWTH: 1 (1.3%)
- BENCH_DISADV_3vs6_?: 1 (1.3%)

## By opponent arch
- ?: 28
- KYOGRE: 27
- MEOWTH+FEZANDIP: 7
- FEZANDIP: 7
- LUCARIO: 4
- LATIAS+FEZANDIP: 1
- LUCARIO+FEZANDIP: 1
- LATIAS+MEOWTH+FEZANDIP: 1
- LUCARIO+KOROIDON: 1
- MEOWTH: 1

## By turn
- T4: 1
- T5: 1
- T6: 1
- T7: 3
- T8: 4
- T9: 4
- T10: 5
- T11: 5
- T12: 8
- T13: 5
- T14: 10
- T15: 2
- T16: 3
- T17: 5
- T18: 3
- T19: 4
- T20: 2
- T21: 1
- T22: 3
- T23: 3
- T24: 1
- T27: 1
- T28: 1
- T30: 1
- T31: 1

## Wipe losses deep dive (first 20)
### 124844896 vs WolfeyVGC (MEOWTH+FEZANDIP) T14
- our_board: ['B:card723(350)', 'B:card723(270)']
- opp_board: ['A:card121(320/320)', 'B:card121(280)', 'B:card121(320)', 'B:card65(60)', 'B:card120(90)']
- our_ko: [] opp_ko: []
- last_logs: [{'cardId': 723, 'playerIndex': 0, 'putDamageCounter': True, 'serial': 44, 'type': 16, 'value': -10}, {'cardId': 723, 'fromArea': 4, 'playerIndex': 0, 'serial': 43, 'toArea': 3, 'type': 6}, {'cardId': 722, 'fromArea': 10, 'playerIndex': 0, 'serial': 41, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 12, 'toArea': 3, 'type': 6}]
- moves_tail: [{'turn': 13, 'type': 0, 'opt': None}, {'turn': 13, 'type': 0, 'opt': None}, {'turn': 13, 'type': 0, 'opt': None}, {'turn': 13, 'type': 0, 'opt': None}, {'turn': 13, 'type': 0, 'opt': None}]

### 124845423 vs Kentaro Totsuka (?) T7
- our_board: ['A:card305(70/70)']
- opp_board: ['A:card93(80/80)', 'B:card90(100)', 'B:card89(70)', 'B:card89(70)', 'B:card149(40)', 'B:card149(40)']
- our_ko: [] opp_ko: []
- last_logs: [{'cardId': 305, 'fromArea': 5, 'playerIndex': 1, 'serial': 80, 'toArea': 4, 'type': 6}]
- moves_tail: [{'turn': 5, 'type': 1, 'opt': None}, {'turn': 5, 'type': 0, 'opt': None}, {'turn': 5, 'type': 0, 'opt': None}, {'turn': 5, 'type': 0, 'opt': None}, {'turn': 5, 'type': 0, 'opt': None}]

### 124845953 vs Praneeth Yeddu (LATIAS+FEZANDIP) T13
- our_board: ['A:card66(140/140)']
- opp_board: ['A:card756(300/300)', 'B:card756(300)', 'B:card96(210)']
- our_ko: [] opp_ko: []
- last_logs: [{'cardId': 19, 'fromArea': 1, 'playerIndex': 1, 'serial': 71, 'toArea': 2, 'type': 6}, {'playerIndex': 1, 'type': 0}]
- moves_tail: [{'turn': 5, 'type': 0, 'opt': None}, {'turn': 5, 'type': 1, 'opt': None}, {'turn': 5, 'type': 1, 'opt': None}, {'turn': 5, 'type': 0, 'opt': None}, {'turn': 5, 'type': 0, 'opt': None}]

### 124845954 vs Faaiz Hussain (MEOWTH+FEZANDIP) T12
- our_board: ['A:card723(140/350)']
- opp_board: ['B:card150(330)', 'B:card1071(170)', 'B:card709(110)']
- our_ko: [] opp_ko: []
- last_logs: [{'cardId': 96, 'fromArea': 4, 'playerIndex': 0, 'serial': 3, 'toArea': 3, 'type': 6}, {'cardId': 1, 'fromArea': 8, 'playerIndex': 0, 'serial': 49, 'toArea': 3, 'type': 6}, {'cardId': 1, 'fromArea': 8, 'playerIndex': 0, 'serial': 57, 'toArea': 3, 'type': 6}, {'cardId': 1, 'fromArea': 8, 'playerIndex': 0, 'serial': 55, 'toArea': 3, 'type': 6}, {'cardId': 1, 'fromArea': 8, 'playerIndex': 0, 'serial': 52, 'toArea': 3, 'type': 6}]
- moves_tail: [{'turn': 5, 'type': 1, 'opt': None}, {'turn': 5, 'type': 1, 'opt': None}, {'turn': 5, 'type': 1, 'opt': None}, {'turn': 5, 'type': 1, 'opt': None}, {'turn': 5, 'type': 1, 'opt': None}]

### 124845967 vs Festival (?) T13
- our_board: ['B:card721(150)']
- opp_board: ['A:card93(80/80)', 'B:card240(110)', 'B:card90(100)', 'B:card90(100)', 'B:card90(100)']
- our_ko: [] opp_ko: []
- last_logs: [{'cardId': 723, 'playerIndex': 0, 'putDamageCounter': False, 'serial': 43, 'type': 16, 'value': -120}, {'cardId': 723, 'fromArea': 4, 'playerIndex': 0, 'serial': 43, 'toArea': 3, 'type': 6}, {'cardId': 722, 'fromArea': 10, 'playerIndex': 0, 'serial': 41, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 23, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 15, 'toArea': 3, 'type': 6}]
- moves_tail: [{'turn': 12, 'type': 1, 'opt': None}, {'turn': 12, 'type': 1, 'opt': None}, {'turn': 12, 'type': 1, 'opt': None}, {'turn': 12, 'type': 1, 'opt': None}, {'turn': 12, 'type': 1, 'opt': None}]

### 124846514 vs Steveneg13 (KYOGRE) T8
- our_board: []
- opp_board: ['A:card723(350/350)', 'B:card722(90)', 'B:card721(150)']
- our_ko: [] opp_ko: []
- last_logs: [{'cardId': 3, 'fromArea': 1, 'playerIndex': 1, 'serial': 95, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 1, 'playerIndex': 1, 'serial': 88, 'toArea': 3, 'type': 6}, {'cardId': 742, 'playerIndex': 0, 'putDamageCounter': False, 'serial': 26, 'type': 16, 'value': -600}, {'cardId': 742, 'fromArea': 4, 'playerIndex': 0, 'serial': 26, 'toArea': 3, 'type': 6}, {'cardId': 741, 'fromArea': 10, 'playerIndex': 0, 'serial': 22, 'toArea': 3, 'type': 6}]
- moves_tail: [{'turn': 7, 'type': 1, 'opt': None}, {'turn': 7, 'type': 0, 'opt': None}, {'turn': 7, 'type': 0, 'opt': None}, {'turn': 7, 'type': 0, 'opt': None}, {'turn': 7, 'type': 0, 'opt': None}]

### 124846518 vs jazivxt (?) T12
- our_board: ['A:card721(150/150)', 'B:card723(350)']
- opp_board: ['A:card190(300/300)', 'B:card74(70)', 'B:card343(80)', 'B:card666(160)', 'B:card190(300)', 'B:card117(210)']
- our_ko: [] opp_ko: []
- last_logs: [{'cardId': 3, 'cardIdTarget': 723, 'playerIndex': 1, 'serial': 68, 'serialTarget': 102, 'type': 11}]
- moves_tail: [{'turn': 11, 'type': 0, 'opt': None}, {'turn': 11, 'type': 0, 'opt': None}, {'turn': 11, 'type': 0, 'opt': None}, {'turn': 11, 'type': 0, 'opt': None}, {'turn': 11, 'type': 0, 'opt': None}]

### 124847612 vs Majiro_ns (FEZANDIP) T22
- our_board: ['B:card723(350)']
- opp_board: ['A:card743(140/140)', 'B:card305(70)']
- our_ko: [] opp_ko: ['card959', 'card959']
- last_logs: [{'cardId': 723, 'playerIndex': 0, 'putDamageCounter': True, 'serial': 45, 'type': 16, 'value': -400}, {'cardId': 723, 'fromArea': 4, 'playerIndex': 0, 'serial': 45, 'toArea': 3, 'type': 6}, {'cardId': 722, 'fromArea': 10, 'playerIndex': 0, 'serial': 38, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 7, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 11, 'toArea': 3, 'type': 6}]
- moves_tail: [{'turn': 12, 'type': 1, 'opt': None}, {'turn': 12, 'type': 1, 'opt': None}, {'turn': 12, 'type': 1, 'opt': None}, {'turn': 12, 'type': 1, 'opt': None}, {'turn': 12, 'type': 1, 'opt': None}]

### 124848177 vs Igor Zharov (?) T8
- our_board: ['B:card723(350)', 'B:card722(90)']
- opp_board: ['A:card190(400/400)', 'B:card666(160)', 'B:card169(130)', 'B:card57(100)']
- our_ko: [] opp_ko: []
- last_logs: [{'attackId': 253, 'cardId': 190, 'playerIndex': 1, 'serial': 79, 'type': 15}, {'cardId': 723, 'playerIndex': 0, 'putDamageCounter': False, 'serial': 45, 'type': 16, 'value': -440}, {'cardId': 723, 'fromArea': 4, 'playerIndex': 0, 'serial': 45, 'toArea': 3, 'type': 6}, {'cardId': 722, 'fromArea': 10, 'playerIndex': 0, 'serial': 41, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 27, 'toArea': 3, 'type': 6}]
- moves_tail: [{'turn': 7, 'type': 0, 'opt': None}, {'turn': 7, 'type': 0, 'opt': None}, {'turn': 7, 'type': 0, 'opt': None}, {'turn': 7, 'type': 0, 'opt': None}, {'turn': 7, 'type': 0, 'opt': None}]

### 124848716 vs Noel Bobby (?) T6
- our_board: ['A:card721(150/150)']
- opp_board: ['A:card96(180/210)', 'B:card96(210)', 'B:card96(210)', 'B:card96(210)']
- our_ko: [] opp_ko: []
- last_logs: [{'cardId': 3, 'cardIdTarget': 721, 'playerIndex': 1, 'serial': 73, 'serialTarget': 97, 'type': 11}]
- moves_tail: [{'turn': 5, 'type': 0, 'opt': None}, {'turn': 5, 'type': 0, 'opt': None}, {'turn': 5, 'type': 0, 'opt': None}, {'turn': 5, 'type': 0, 'opt': None}, {'turn': 5, 'type': 0, 'opt': None}]

### 124849823 vs kutty1119 (MEOWTH+FEZANDIP) T19
- our_board: ['B:card721(90)']
- opp_board: ['A:card121(320/320)', 'B:card140(210)', 'B:card235(30)', 'B:card112(110)', 'B:card120(90)', 'B:card1071(170)']
- our_ko: [] opp_ko: []
- last_logs: [{'cardId': 721, 'playerIndex': 0, 'putDamageCounter': True, 'serial': 36, 'type': 16, 'value': -10}, {'cardId': 723, 'fromArea': 4, 'playerIndex': 0, 'serial': 45, 'toArea': 3, 'type': 6}, {'cardId': 722, 'fromArea': 10, 'playerIndex': 0, 'serial': 41, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 7, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 28, 'toArea': 3, 'type': 6}]
- moves_tail: [{'turn': 11, 'type': 1, 'opt': None}, {'turn': 11, 'type': 1, 'opt': None}, {'turn': 11, 'type': 1, 'opt': None}, {'turn': 11, 'type': 1, 'opt': None}, {'turn': 11, 'type': 1, 'opt': None}]

### 124850357 vs Noel Bobby (?) T12
- our_board: ['A:card721(150/150)', 'B:card722(90)']
- opp_board: ['A:card96(210/210)', 'B:card96(210)', 'B:card96(210)']
- our_ko: [] opp_ko: []
- last_logs: [{'cardId': 3, 'cardIdTarget': 721, 'playerIndex': 1, 'serial': 65, 'serialTarget': 97, 'type': 11}]
- moves_tail: [{'turn': 10, 'type': 0, 'opt': None}, {'turn': 10, 'type': 0, 'opt': None}, {'turn': 10, 'type': 0, 'opt': None}, {'turn': 10, 'type': 0, 'opt': None}, {'turn': 10, 'type': 0, 'opt': None}]

### 124850930 vs saravana Kishore (KYOGRE) T5
- our_board: ['A:card722(80/90)']
- opp_board: ['A:card722(90/90)', 'B:card722(90)', 'B:card721(150)', 'B:card722(90)']
- our_ko: [] opp_ko: []
- last_logs: [{'cardId': 3, 'cardIdTarget': 722, 'playerIndex': 1, 'serial': 78, 'serialTarget': 98, 'type': 11}]
- moves_tail: [{'turn': 3, 'type': 0, 'opt': None}, {'turn': 3, 'type': 0, 'opt': None}, {'turn': 3, 'type': 0, 'opt': None}, {'turn': 3, 'type': 0, 'opt': None}, {'turn': 3, 'type': 0, 'opt': None}]

### 124851464 vs Brian Bonti (MEOWTH+FEZANDIP) T11
- our_board: []
- opp_board: ['A:card96(160/210)', 'B:card96(210)', 'B:card710(160)']
- our_ko: [] opp_ko: []
- last_logs: [{'attackId': 120, 'cardId': 96, 'playerIndex': 1, 'serial': 81, 'type': 15}, {'cardId': 721, 'playerIndex': 0, 'putDamageCounter': False, 'serial': 36, 'type': 16, 'value': -420}, {'cardId': 721, 'fromArea': 4, 'playerIndex': 0, 'serial': 36, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 27, 'toArea': 3, 'type': 6}]
- moves_tail: [{'turn': 10, 'type': 0, 'opt': None}, {'turn': 10, 'type': 0, 'opt': None}, {'turn': 10, 'type': 0, 'opt': None}, {'turn': 10, 'type': 0, 'opt': None}, {'turn': 10, 'type': 0, 'opt': None}]

### 124852030 vs Aayush Jansari (MEOWTH+FEZANDIP) T7
- our_board: ['A:card305(70/70)']
- opp_board: ['A:card120(90/90)', 'B:card120(90)', 'B:card235(30)', 'B:card119(70)']
- our_ko: [] opp_ko: []
- last_logs: [{'cardId': 5, 'cardIdTarget': 305, 'playerIndex': 1, 'serial': 65, 'serialTarget': 80, 'type': 11}]
- moves_tail: [{'turn': 5, 'type': 0, 'opt': None}, {'turn': 5, 'type': 0, 'opt': None}, {'turn': 5, 'type': 0, 'opt': None}, {'turn': 5, 'type': 0, 'opt': None}, {'turn': 5, 'type': 0, 'opt': None}]

### 124852094 vs DavideSanta (?) T12
- our_board: []
- opp_board: ['A:card96(260/310)', 'B:card96(210)', 'B:card96(210)']
- our_ko: [] opp_ko: []
- last_logs: [{'attackId': 120, 'cardId': 96, 'playerIndex': 1, 'serial': 65, 'type': 15}, {'cardId': 723, 'playerIndex': 0, 'putDamageCounter': False, 'serial': 44, 'type': 16, 'value': -390}, {'cardId': 723, 'fromArea': 4, 'playerIndex': 0, 'serial': 44, 'toArea': 3, 'type': 6}, {'cardId': 722, 'fromArea': 10, 'playerIndex': 0, 'serial': 38, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 24, 'toArea': 3, 'type': 6}]
- moves_tail: [{'turn': 8, 'type': 0, 'opt': None}, {'turn': 8, 'type': 0, 'opt': None}, {'turn': 8, 'type': 0, 'opt': None}, {'turn': 8, 'type': 0, 'opt': None}, {'turn': 8, 'type': 0, 'opt': None}]

### 124852575 vs Pawit Sahare (KYOGRE) T9
- our_board: ['A:card722(90/90)']
- opp_board: ['A:card723(70/350)', 'B:card721(150)']
- our_ko: [] opp_ko: []
- last_logs: [{'cardId': 3, 'cardIdTarget': 722, 'playerIndex': 1, 'serial': 89, 'serialTarget': 100, 'type': 11}]
- moves_tail: [{'turn': 7, 'type': 0, 'opt': None}, {'turn': 7, 'type': 0, 'opt': None}, {'turn': 7, 'type': 0, 'opt': None}, {'turn': 7, 'type': 0, 'opt': None}, {'turn': 7, 'type': 0, 'opt': None}]

### 124853683 vs RAHUL REDDY PULICHARLA (KYOGRE) T12
- our_board: []
- opp_board: ['A:card721(150/150)']
- our_ko: [] opp_ko: []
- last_logs: [{'cardId': 3, 'fromArea': 3, 'playerIndex': 1, 'serial': 97, 'toArea': 1, 'type': 6}, {'cardId': 3, 'fromArea': 3, 'playerIndex': 1, 'serial': 110, 'toArea': 1, 'type': 6}, {'playerIndex': 1, 'type': 0}, {'cardId': 305, 'fromArea': 4, 'playerIndex': 0, 'serial': 18, 'toArea': 3, 'type': 6}, {'cardId': 19, 'fromArea': 8, 'playerIndex': 0, 'serial': 10, 'toArea': 3, 'type': 6}]
- moves_tail: [{'turn': 11, 'type': 1, 'opt': None}, {'turn': 11, 'type': 0, 'opt': None}, {'turn': 11, 'type': 0, 'opt': None}, {'turn': 11, 'type': 0, 'opt': None}, {'turn': 11, 'type': 0, 'opt': None}]

### 124853685 vs diujin217 (KYOGRE) T10
- our_board: ['A:card721(150/150)']
- opp_board: ['A:card723(150/350)']
- our_ko: [] opp_ko: []
- last_logs: [{'cardId': 3, 'cardIdTarget': 721, 'playerIndex': 1, 'serial': 73, 'serialTarget': 97, 'type': 11}]
- moves_tail: [{'turn': 8, 'type': 0, 'opt': None}, {'turn': 8, 'type': 0, 'opt': None}, {'turn': 8, 'type': 0, 'opt': None}, {'turn': 8, 'type': 0, 'opt': None}, {'turn': 8, 'type': 0, 'opt': None}]

### 124854784 vs Sliver-Ze (KYOGRE) T17
- our_board: ['A:card723(250/350)', 'B:card722(90)']
- opp_board: ['B:card721(150)']
- our_ko: [] opp_ko: []
- last_logs: [{'cardId': 723, 'playerIndex': 0, 'putDamageCounter': False, 'serial': 10, 'type': 16, 'value': -600}, {'cardId': 723, 'fromArea': 4, 'playerIndex': 0, 'serial': 10, 'toArea': 3, 'type': 6}, {'cardId': 722, 'fromArea': 10, 'playerIndex': 0, 'serial': 3, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 20, 'toArea': 3, 'type': 6}, {'cardId': 3, 'fromArea': 8, 'playerIndex': 0, 'serial': 36, 'toArea': 3, 'type': 6}]
- moves_tail: [{'turn': 16, 'type': 1, 'opt': None}, {'turn': 16, 'type': 1, 'opt': None}, {'turn': 16, 'type': 1, 'opt': None}, {'turn': 16, 'type': 1, 'opt': None}, {'turn': 16, 'type': 1, 'opt': None}]

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
