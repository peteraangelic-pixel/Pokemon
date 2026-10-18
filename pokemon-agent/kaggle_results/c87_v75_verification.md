# Weryfikacja c87 v75_rl (BC 2000g) + status RL (2026-10-18)

Ich deklaracje: top30_live 0.833, H2H vs v67 0.425 (40g).
Bundle v75_rl.tar.gz NIE istnieje na galezi (jest agents/v75_rl.py 2.79M
+ rl/params_*.npz). Testowany plik agenta z repo.

## Nasze pomiary
| test | v75_rl | odniesienie |
|---|---|---|
| vs v67 600g | 0.493 | remis (ich 0.425@40g = mala probka) |
| vs champion 600g | 0.535 | klon nauczyciela |
| siatka 100/deck | 0.700 | v67 0.714 |

BC dziala jak teoria: 89% match -> gra na poziomie championa, sufit =
nauczyciel. Ich PPO skolapsowalo (WR 0.60->0.275) - przyczyna zgodna
z nasza diagnoza: wspolny optimizer LR 1e-3 / brak delegacji nie-MAIN;
u nas smoke PPO stabilny (LR 3e-4, delegacja, eval 0.53-0.65).

## Nasz trening Actions
Run v1 (39117574385) umarl po cichu w 1m38s (brak pipefail maskowal
blad pythona; brak commitu parametrow). Fix: pipefail + realny budzet
PPO; run v2 wystartowal (commit 7ca4938). Docelowo: BC 6000g/2500 krokow
+ 12 iter PPO x200g vs liga, ewaluacja co iteracje.
