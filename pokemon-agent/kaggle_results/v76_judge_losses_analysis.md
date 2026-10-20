# Analiza porażek 2 ostatnich submisji + status Actions (2026-10-20)

## Live (poll)
- v76 RL (57409358): **378.0** — najslabsza aktywna. Duzo porazek.
- v70 Judge (57370290): **415.9**. v70_horizon 450.8 (team best), v67 443.2.
- Ich v78_rl: 436.2 / 383.3 (dwie kopie) — tez nie przebija heurystyki.

## Actions rl-train v4 (39332947847): CANCELLED po 5h30m
Limit czasu workflow (330 min) ubil trening w polowie PPO; parametry
meta-ligi PRZEPADLY (commit dopiero na koncu). Naprawa: krotszy run,
timeout 355, train.py sam commit/push params_best co 5 iteracji.

## Porazki (probe 120g/deck, pula zywych talii opp_decks_v59, pilot champion)
v76: WR 0.709 sumarycznie, ale **Crustle wall (opp_15): 0.100** (108/120
porazek, glod tylko 22% — model nie umie przebic sciany, a w treningu
v3 sciany nie bylo). Mirrory 0.45-0.50. Na zywo piloci graja swoimi
deckami lepiej niz symulowany champion -> stad 378 mimo 0.517 lok.
v70 Judge: WR 0.710; najslabsze: **Crustle 0.275** (87 porazek), mirrory
0.48-0.55, Dragapult lok. 0.983 (artefakt slabego pilota champion).

Wniosek: wspolny zrodlowy problem obu submisji = sciana Crustle +
coin-flip mirror. Liga treningowa v4 (z opp_15/opp_02/opp_04/opp_10)
adresuje dokladnie to — pod warunkiem, ze run dojedzie do konca.
