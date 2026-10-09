# Replay Analysis — 7 replays

Our team (inferred): **Lauresowe 3D**

Total replays: 7

## Win/Loss vs opponents

| Opponent | Games | Wins | Losses | Win rate |
|---|---|---|---|---|
| Lauresowe 3D | 1 | 0 | 0 | 0.00 |
| Dnyanesh | 1 | 1 | 0 | 1.00 |
| Jonathan Axl | 1 | 0 | 1 | 0.00 |
| Pawit Sahare | 1 | 0 | 1 | 0.00 |
| The Prad K | 1 | 0 | 1 | 0.00 |
| Jarno Rantala | 1 | 1 | 0 | 1.00 |
| 彭文龙 | 1 | 1 | 0 | 1.00 |

## Deck meta (all decks seen)

- Energy distribution: {33: 7, 36: 1, 26: 1, 35: 2, 15: 1}
- Gust (Boss/Catcher) distribution: {0: 11, 2: 1}

### Example decks that beat us

- **episode-120516202-replay.json** vs Jonathan Axl (winner Jonathan Axl, 151 steps)
  - Energy: 26, Gust: 2
  - Pokemon: Snover x4, Mega Abomasnow ex x4, Kyogre x2
  - Trainers: Basic {W} Energy x26, Mega Signal x4, Lillie's Determination x4, Poké Pad x3, Waitress x3, Night Stretcher x2

- **episode-120517988-replay.json** vs Pawit Sahare (winner Pawit Sahare, 75 steps)
  - Energy: 35, Gust: 0
  - Pokemon: Snover x4, Mega Abomasnow ex x4, Kyogre x2
  - Trainers: Basic {W} Energy x35, Mega Signal x4, Lillie's Determination x4, Waitress x4, Cyrano x2, Maximum Belt x1

- **episode-120519812-replay.json** vs The Prad K (winner The Prad K, 110 steps)
  - Energy: 33, Gust: 0
  - Pokemon: Snover x4, Mega Abomasnow ex x4, Kyogre x2
  - Trainers: Basic {W} Energy x33, Team Rocket's Petrel x4, Lillie's Determination x4, Ultra Ball x2, Mega Signal x2, Powerglass x2

### Example decks we beat

- **episode-120516144-replay.json** vs Dnyanesh (107 steps)
  - Energy: 36, Gust: 0
  - Pokemon: Snover x4, Mega Abomasnow ex x4, Kyogre x2

- **episode-120521637-replay.json** vs Jarno Rantala (171 steps)
  - Energy: 35, Gust: 0
  - Pokemon: Snover x4, Mega Abomasnow ex x4, Kyogre x2

- **episode-120523473-replay.json** vs 彭文龙 (171 steps)
  - Energy: 15, Gust: 0
  - Pokemon: Riolu x4, Mega Lucario ex x4

## Recommendations

- More than half of decks have 0 gust. Adding 2x Boss's Orders (id 1182) could give us free wins vs walls (Crustle, Sylveon) — we saw 0.30→0.61 vs Sylveon with just play improvement, gust would push it further.

- Average energy in meta: 31.5. Our current 33 is high; top players use 26-30. Cutting 3-7 energy for trainers (Boss, Cyrano, Night Stretcher) trades ~20-40 damage per Hammer-lanche for consistency.

- Mirror losses (identical deck) suggest play, not deck, is the bottleneck. Lethal DFS and better energy attachment prioritization are next.
