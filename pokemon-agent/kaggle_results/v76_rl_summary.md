# v76 RL (BC+PPO) - podsumowanie 2026-10-19

Nocne wyniki: v67 nadal best 443.2; nasza v70 Judge (57370290) 427.0
(mloda); v70_horizon 422.2; v69r 427-428; ich v75_rl_lethal = ERROR
na Kaggle (paczka crashuje w produkcji - lekcja: clean-room test!).

## Nasz model (Actions run 39138976359, commit 9ba09e1)
BC 6000g: match 0.977, eval 0.57/0.46 (100g). PPO 12 iter: eval
0.29-0.67 (szum 100g), zapisany final (brak best-checkpoint - do poprawy).

## v76 = model + lethal-win override + fallback champion (1 plik)
Clean-room (sam main.py+deck+card_index, jak Kaggle):
- vs v67 0.517 @600 | vs champion 0.552 @600 | siatka 200/deck (nizej)
Wczesniej rl/agent.py: 0.509/0.507 @1200. Model = poziom nauczyciela,
PPO jeszcze nie przebija wyraznie. Paczka ptcg_v76_rl_a450.tar.gz
przechodzi bramki; NIE wyslana (brak rozkazu).

Nastepne kroki RL: best-checkpoint w train.py, dluzsze PPO z snapshotami
ligi, GRU belief, ewaluacja ligowa kandydatow przed paczka.
