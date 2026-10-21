# Weryfikacja benchmark v2.3 REAL (c87 1ef6e5a) — 2026-10-21

Pierwsza wersja, w ktorej kazda faza wykonuje kod (odpowiedz na audyt
f5cc7c3). Pomiary u nas (sandbox 2 rdzenie, agent kontrolny v67):

- Phase1 FFI: REAL, 74.8 gier/s (20g) — OK, spojna (66.6 / 77.8).
- Phase1b Rust: CLI naprawiona (--agent usunieta, gauntlet biegnie:
  44 gry w 0.6s), ale **parser zwraca total=0 -> gps=0.0**. Format
  "Overall: 0.818 (36-8 d0)" nie pasuje do regexa (\d+)W-(\d+)L,
  a fallback wymaga \d+-\d+-\d+ na koncu linii. Rust nadal niemierzony
  przez ten benchmark (jedna poprawka regexa od celu).
- Phase2 liga: dziala (120 gier, 76 gier/s; przy --games>=100 bedzie
  100/pare). U nas 3 pilotow (v80_final tylko na c87).
- Phase3 belief Judge: **wykonuje sie, lecz prozna** — mirror talii
  trolley: zadna strona nie ma Fezandipiti ex -> fez_detections=0
  z konstrukcji. Wymaga przeciwnika z deckiem Fez.
- Phase4 transformer: attention prawdziwa, ale **n_layers ignorowane**
  — obie konfiguracje wykonuja JEDNA warstwe (2.19/5.55 ms to forward
  1-warstwowy); etykiety L4/L8 falszywe. FF=1024 stale dla obu.
- Phase5 "PPO throughput": REAL pomiar, lecz samego rollout (71.3
  gier/s, ekstrap. 2800 gier=39 s) — bez kroku uczenia. Nasz BENCH_PC
  mierzy rollout + epoke JAX; etykieta zawyzona.
- Phase6 lethal: seat swap naprawiony; ale dalej mierzy agent-vs-v67
  minus parzystosc mirror, NIE ablacj lethal tego samego agenta.
  Kontrola: klon v67 jako "agent" dal 0.35 vs 0.45 kontroli (n=40)
  -> szum +-10-15pp; dopiero n=600 (domyslne) ma sens.

Werdykt: v2.3 = uczciwy, dzialajacy benchmark z 5 bledami mniejszej
wagi: parser 1b, proznia fazy 3 w mirrorze, warstwy w fazie 4,
rollout-only w fazie 5, brak ablacj w fazie 6. Postep v2.1->v2.3
realny: z dokumentu narracyjnego zrobilo sie narzedzie.
