# v72 - decyzja po pelnym przesiewie (2026-10-18)

Przetestowane i ODRZUCONE na 1200-2400g (prizetest/siatka/liga):
- v72 stack (horizon c87 + Judge a450): Alakazam 0.518, vs v67 0.477
- ES strojenie 6 wag championa (3 generacje): fitness plaski 0.51-0.54,
  walidacja BENCH0=1170: mirror 0.492 / Alakazam 0.537 = szum
- Dragapult pilotem championa: 0.028 vs sciana (champion nie gra
  obcych archetypow; nowy pilot = projekt RL, nie reguly)
- v68 druga fala, 5 wymian talii, v71 hard override (c87) - wczesniej

Zostaje jedyny artefakt z dodatnim bilansem: v70 Judge (meta-kontra):
Alakazam +3.6pp (0.543 vs 0.507), glod 40->37%, mirror -2.2pp,
siatka neutralna. To jest nasza v72 do slotu: ptcg_v70_meta_a450.tar.gz
(spojna, bramki OK, niewyslana). Meta live rosnie w Alakazam/Fezandipiti
(v67 live: FEZ 0-5), wiec bilans powinien rosnac z czasem.

Dogonienie liderow (1350) = program RL z liga (FAZA2_roadmap.md):
PPO vs liga 8-12 pilotow, Transformer+belief, tygodnie + compute.
Narzedzia gotowe: tools/league_eval.py, tools/es_tune.py (seed ES
na Actions w wiekszej skali), tools/prizetest.py (metr przyczynowy).
