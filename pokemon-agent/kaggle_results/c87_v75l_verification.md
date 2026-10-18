# Weryfikacja c87 v75_rl+lethal/gated (d1ac04b) (2026-10-18)

Nowosci u c87 od v75: (1) v75_rl lethal+gated margin>=250 (bundle
v75_rl_lethal.tar.gz, talia Judge), deklaracje top30 0.889, H2H 0.45;
(2) RL v2: fix PPO (lr 1e-4, ent 0.02, clip), eval vs v67 0.45->0.5
(male probki FFI), model_v2 D256 L4 GRU scaffold; (3) train v3 trigger.

## Nasze pomiary v75l (prizetest 600g)
| test | v75l | samo BC v75 |
|---|---|---|
| vs v67 | 0.442 | 0.493 |
| vs champion | 0.438 | 0.535 |
Lethal+gated override psuje wyuczona polityke (jak v71 hard override
psul championa). Deklarowane 0.889 top30 nie odtwarza sie przyczynowo.

## Nasz trening Actions
Run v2 padl: tools/gauntlet_ffi.py mial na sztywno sciezke
.venv/.../libcg.so (brak .venv w Actions). Fix: fallback do
sysconfig purelib. Run v3 puszczone.
