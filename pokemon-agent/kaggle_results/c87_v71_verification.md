# Weryfikacja c87 v71_gated (2026-10-18)

Ich deklaracje (FFI): 0.557 vs champ, 0.797 new_losses, 0.931 top30, 0.729 broad.
Talia = trolley34w (spojna). Skladniki: lethal +2000, mask dominated,
bench v2 hard override +5000/+2000, meta-counter, gated endgame +500.

## Nasze pomiary (prizetest/grid)
| test | v71 | odniesienie |
|---|---|---|
| mirror vs champion 1200g | 0.500 (glod 56%) | v67 0.527 |
| H2H vs v67 1200g | **0.462** | - |
| vs hybryda Alakazam 1200g | 0.535 | v67 0.507, v70_judge 0.543 |
| siatka 4800g | 0.693 | v67 0.714, horizon 0.708 |

## Werdykt
v71 slabiej od v67 w mirrorze i siatce; hard override lawki psuje
porzadek decyzji championa (znana lekcja: kolejnosc silnika > reczne
przeboje). Jedyny plus: Alakazam 0.535 (nizej niz v70_judge 0.543).
NIE do wysylki. Live: ich v70_horizon 57334418 = 419.4 (mlody),
v67 nadal najlepsza submisja 443.2. v71 nie wyslana (disarm u c87).
