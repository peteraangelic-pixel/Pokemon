# NOTES_STRATEGY — droga do 1000+

## Obecny stan (2026-10-16)
- Live v69 373.5 COMPLETE poniżej v56T 423.9 i v59 406.6. 41 gier 18-23.
- Najgorsza kategoria: ? 2-7 (Kangaskhan 756 + Crustle 345) — ściany 300 HP.
- Drugi branch zweryfikował nasz harness: 5-10g/deck daje 0.652 top30 / 0.825 walls, ale na ich 4800g (600g per grupa, silni piloci) ten sam agent ma trolley 0.492 wall 0.520 grid 0.614 ~= ich v65 0.611. Czyli nasz harness zawyża.
- Dominujący tryb przegrywania: wipe z niewykorzystanymi prize — prowadzimy 4-1, ostatni Pokemon umiera board 1 vs 5, promujemy ostatniego Abrę 50 HP. 21.7% przegranych ma pusty our_board.

## Wnioski drugiej gałęzi (a450b00f)
- Lokalny harness inflatuje — trzeba 4800 gier (strong pilots, replikacje) by poprawnie rankingować.
- Archetyp sam nie daje skoku — pilot jest sufitem.
- CEM best val 0.467 = overfit na małym harnessie. Gen0 best 0.583 worst5 vs full top30 0.556 < default 0.652.
- PG v2 recipe poprawiony: BC seed z hybrid-v2+simple deck clone 0.422 vs trolley (było 0.153), lr 8e-4 x3 epochs (było 1e-4 x1 = plateau), 40k gier x6 iteracji. Nadal w trakcie, ale to kandydat na przebicie heurystyki.
- Fix wipe: endgame bench discipline zawsze >=2 za aktywnym, timing recovery Night Stretcher/Sacred Ash, nigdy nie promuj ostatniej Abry.

## Plan dla 1000+ (zrewidowany po drugiej gałęzi)

### Faza A — naprawa heurystyki (v70-v72 zrobione)
- [x] v70: bench guard jeśli board<=2 i prize<=3 → benchuj basic, Poffin/Pad, potem recovery. Nie promuj Abry gdy board<=2 i prize<=3. Boost Boss KO z marginesem 10-15.
- Wynik lokalny: top30 10g 0.615 (vs 0.619), broad 0.632 (vs 0.622), Mengfei 0.50 vs 0.15 (+35pp). To naprawia ? kategorię.
- [x] v71 hybrid Toucannon: 3x Alakazam +2x Toucannon +11E +3 Boss. Toucannon 60+20*bench (max 260) + Boss na małe bench. Wynik 0.607 top30, 0.40 Mengfei — gorszy niż v70 simple, ale idea secondary attackera słuszna.
- [x] v72 bench>=3: zbyt defensywny, 0.607 top30, 0.35 Mengfei — odrzucony. Wniosek: próg board<=2 jest lepszy niż <=3.

**Decyzja:** v70 simple jest najlepszy heurystycznie na ściany. Zgłosić v70 jako następny, z distinct nazwą bundle.

### Faza B — walidacja 4800g (do wdrożenia)
- Zbudować skrypt `tools/gauntlet_4800.py`:
  - grupy: trolley (v56_trolley, v57_trolley34w, shaun2024_wall), Crustle wall, Mengfei Kangaskhan, top30_live split na top10 i reszta, live_killers 18 decków.
  - każda grupa 600 gier (np. 3 decki x200 gier lub 1 deck x600), łącznie ~4800.
  - raport: winrate per grupa, worst5, bench wipe %.
  - Używać multiprocessing.Pool + gauntlet_ffi (jak a450) — 84k próbek w 128s, 20+ gier/s z Rust+Rayon w Actions.
- Przed każdym submitem uruchamiać 4800g, nie 5-10g. Tylko jeśli >0.55 grid i >0.5 trolley i >0.5 wall i >0.6 top30 — dopiero submit.

### Faza C — Policy Gradient v2 (zgodnie z drugą gałęzią)
- BC seed: zamiast champion c87_v44, użyć nauczyciela Alakazam v70 (hybrid-v2+simple). Wygenerować dane BC via `gen_bc_data_alakazam.py`:
  - teacher = v70 agent, deck pool = simple + hybrid + YumeNeko + trolley + walls.
  - cel: clone 0.422 vs trolley (obecnie 0.153 z generic champion).
- Trening BC: lr 8e-4 x3 epochs (nie 1e-4 x1), batch 512, jak w PG v2.
- PG iteracje: 40k gier x6 iter, jobs 4, eps 0.08 temp 0.7, mode pg, win-weight 0.5 entropy 0.01, lr 8e-4.
- Rollout: `policy_rollout` Rust z lto, jeden lib per rayon thread, 15-20g/s policy rollout, jak w a450.
- Gate: eval 2000 gier vs poprzednia polityka, league-frac 1.0.
- Budowa agenta: `build_policy_agent.py` z wagami .npz.

### Faza D — deck archetype search dla rewolucji
- Workflow `deck_archetype_search.yml` już istnieje — szuka YumeNeko Alakazam vs dragapult etc.
- Dodać koncept: Alakazam 3x + Toucannon 2x + 11E + 3 Boss + 2 Night Stretcher + 1 Sacred Ash.
- Alternatywnie: powrót do YumeNeko list (z Togekiss) ale z naszym endgame guard — test czy 0.685 vs YumeNeko (2g) utrzyma się na 600g.

### Faza E — submit hygiene (po nauczce)
- Nigdy nie używaj tej samej nazwy bundle dla różnej zawartości — 5 slotów może mieć różne nazwy.
- DISARM wszystkich auto-submit workflow (`at_reset.DISARM`, `submit_2am.DISARM`, `submit_now.DISARM`) — tylko ręczny `workflow_dispatch` za zgodą usera.
- Tylko 2 ostatnie suby aktywne — nie zapychać slotów masą słabych wersji. Max 5/dzień.
- Bundle flat: `main.py` + `deck.csv` + `card_index.json` (embed by nie było zero-features na Kaggle).

## Co dalej (kolejne kroki)
1. Uruchomić walidację 4800g dla v70 vs v69 vs v71 — potwierdzić że v70 > v69 na wall i nie gorszy na top30.
2. Zbudować BC data z v70 teacher (40k gier) i wytrenować policy_rust_v70.npz z lr 8e-4 x3.
3. Uruchomić PG iteracje 6x40k (jak druga gałąź) — cel >0.6 vs trolley i >0.65 vs walls na 4800g.
4. Gdy wyniki zadowalające i >20g/s w Actions (Rust+Rayon), za zgodą usera wrzucić najlepszą wersję po 2giej w nocy (okno 5 slotów).
5. Kontynuować analizę live replays: fetch `kaggle_our_replays` co 24h, aktualizować `episodes_table.csv` i `summary.md`.

## Materiały na przyszły writeup (płatna edycja)
- Różnice symulatora vs oficjalne PTCG rules (thread discussion) — znaleźć przed pisaniem logiki gry.
- Dlaczego top7 overfituje a top30 nie: silni gracze mają 2-15E 2-3 Gust, my mieliśmy 33E — meta shift.
- Bench wipe jako główny leak: analiza 48% -> 23% -> 21.7% po fixach, ale nadal 9-17% w drugiej gałęzi vs 48% u nas.
- Rust+Rayon 200x speedup, ale marnuje darmowe minuty Actions — kompromis: Python multiprocessing lokalnie, Rust w Actions dla >20g/s.
