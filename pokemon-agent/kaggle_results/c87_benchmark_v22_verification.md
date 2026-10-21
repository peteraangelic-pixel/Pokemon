# Weryfikacja benchmark v2.2 REAL (c87 73475a9) — 2026-10-21

Postep wzgledem v2.1 jest prawdziwy: narracja sprostowana (z cytatem
naszej opinii), poprzednie wersje zachowane (benchmark_v2_v2/v2.1.py),
fazy 1/2/6 realnie graja. Ale haslo "wszystkie fazy mierzone" nadal
nieprawdziwe. Pomiary u nas (sandbox 2 rdzenie, agent kontrolny v67):

- Phase1 FFI: REAL, 77.8 gier/s (40g) — spojna z naszym 66.6. OK.
- Phase1b Rust: **ZEPSUTA** — wolany `gauntlet_rust --agent ...`,
  a binarka nie ma takiej flagi (stderr: unexpected argument) -> gps=0.0.
  Rust nadal niemierzony przez ten benchmark (150 gier/s to nasz pomiar).
- Phase2 liga: dziala, lecz 4 gry/pare (24 razem) = n-zabawka; u nas
  3 pilotow (v80_final istnieje tylko na c87). Bez wartosci decyzyjnej.
- Phase4 "transformer inference": czasy NumPy matmulow losowych macierzy
  (bez attention/softmax/modelu); ms/opcja = forward/32 umowne;
  "0.1 ms/opcja na 1070 GPU" dalej hardcoded w nocie.
- Phase6 lethal: REAL gry, ale projekt nie izoluje przyczyny: testowany
  agent zawsze na siedzeniu 0, brak zamiany siedzen, n=40; domyslny
  agent (v85) porownywalby dwa rozne agenty, nie ablacj lethal.
  Kontrola v67-vs-v67: delta -0.025, narzut -4.9% (szum/bias siedzenia).
- Phase3 (belief Judge) i Phase5 (PPO throughput): NADAL brak w kodzie.

Werdykt: v2.2 > v2.1 (uczciwosc + realne fazy 1/2/6), lecz do naprawy:
1b (flaga CLI), 3 i 5 (brak), 6 (ablacja tego samego agenta, swap
siedzen, n>=600), 2 (n>=100/par).
