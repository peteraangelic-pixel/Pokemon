# Weryfikacja benchmark v2.5 REAL (c87 492dfcc) — 2026-10-21

Odpowiedz na audyt v2.4 (2011b56). Pomiary u nas (sandbox 2 rdzenie):

- Phase1b parser: **NAPRAWIONA** — regex lapie "Overall: ... (36-8 d0)":
  total=43 gry sparsowane, gps=33.2 przy mikro-probie 2 gry/matchup
  (narzut startu procesu; pelny pomiar 600 gier wczesniej = 150 g/s).
- Phase3: flaga our_deck_has_judge=false + uczciwy caveat — OK.
  fez_detections 1457/20 gier (metodologia decyzje-nie-gry zostaje).
- Phase6 strażnik: OK (brak v85 -> print + 0, nie crash)... ale:
- Phase6 ENTRYPOINT: `main()` woła `phase6_lethal_real_ablation`,
  funkcja nazywa sie `phase6_lethal_true_ablation` -> **NameError,
  committowana v2.5 crashuje na --phase 6 / all**. Obejrzane importem.
- Ablacja (bezposrednie wolanie, 80 gier/porownanie): kontrola 0.4625,
  lethal-on 0.275 -> delta **-18.8pp**. Mechanizm dziala i potwierdza
  serie: twarde override'y szkodza (v75l 0.442<0.493). ZASTRZEZENIE:
  wrapper = "atakuj pierwsza opcja gdy opp HP<=150" bez estymacji
  obrazen i bez bramki nagrod — to NIE jest produkcyjny soft lethal
  +200 z v81, wiec pomiar dotyczy wrappera, nie wyslanej reguly.
- winrate_our_v85=0 przy braku pliku (powinno byc null, nie 0) —
  delta_our -46pp to artefakt raportu.

Werdykt: 3/3 fixow z audytu adresowanych; parser i straznik realnie
dzialaja, ablacja strukturalnie prawdziwa. Do poprawy: NameError
w main (faza 6 martwa z CLI), semantyka wrappera != soft lethal z v81.
