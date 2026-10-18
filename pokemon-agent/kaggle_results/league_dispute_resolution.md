# Rozstrzygniecie spornych liczb ligi c87 (2026-10-18)

Ich league_eval_v71 (300g) dala wyniki odwrotne do naszych. Replikacje
na prizetest (te same pliki agentow, obie strony trolley, 1200g):

| para | c87 liga | nasza replikacja |
|---|---|---|
| v67 vs Judge | 0.683 dla v67 | **0.494** (remis; pilot Judge na trolley = v67 z definicji) |
| Judge vs horizon | 0.283 dla Judge | **0.517 dla Judge** |
| v71 vs v67 | 0.533 dla v71 | **0.462 + 0.491 replikacja (pooled 0.477)** |

Wniosek: tabela ligi c87 to artefakt ich harnessu/plikow (prawdopodobnie
inne kopie agentow lub mapowanie talii) - trzy niezalezne replikacje ja
obalaja. Zgodne pozostaja: liga jako metr (tak), 80% flip niemozliwe
regulami (tak), sufit 600-700 i kierunek RL (tak), Judge jako idea
kontyngentna (u nas +3.6pp vs Alakazam na prawdziwym pliku, 1200g).

v71_gated: mirror 0.500, siatka 0.693, vs v67 pooled 0.477 - nie lepsza
od v67; nie wysylac. Ich plan v72 (v71+J1) odziedziczy koszt mirroru v71.
