# Werdykt: czy RESET po śmierci cofa do poziomu 1? (2026-10-24, sesja Pokemon)

## Pytanie
Sesja ARC potwierdziła na prawdziwym silniku (lokalnie, 0 GPU): RESET po śmierci
NIE zachowuje ukończonych poziomów (Q2 0/4), replay odtwarza poziom hash-w-hash (Q3 4/4).
Wniosek sesji ARC: "każda śmierć kosztuje całą ścieżkę w akcjach".

## Werdykt: test jest prawdziwy, ale mierzy konfigurację BEZ pinu. W zgłoszeniu pin jest.

Dowody z bundle r033 (Smak repo: arc-agi-3/kaggle/ops/results/r033-recon-bundle):

1. Harness po GAME_OVER wysyła `GameAction.RESET`
   (`inference/framework/solver.py:663-666` `_execute_auto_reset`, wywoływane :281).
2. Semantyka RESET w arcengine zależy od `level_reset_only` (env `ONLY_RESET_LEVELS`).
   Własny komentarz Tufy (`taaf/game_api.py:214-220`): BEZ pinu "handle_reset full-resets
   to level 0 whenever _action_count == 0 ... a mid-play RESET on level N > 0 with no
   actions taken on the new level snaps the player back to level 1".
3. Z pinem RESET resetuje tylko bieżący poziom. Pin jest ustawiany DWA razy:
   - komórka 2 notebooka duck-original: `os.environ["ONLY_RESET_LEVELS"]="true"`
     ("Pin arc_agi's cached level_reset_only before its client is built (RESET keeps
     the level)") — to ustawienie PRZED budową klienta, czyli to, które łapie cache;
   - `game_api.py:221` po `arcade.make` (procesowo, idempotentnie).

Wniosek sesji ARC (Q2 0/4) jest więc zgodny z silnikiem BEZ pinu — ich test lokalny
prawie na pewno zbudował klienta bez ustawionego env. Dla prawdziwego zgłoszenia
zaprojektowane zachowanie jest odwrotne: śmierć = restart bieżącego poziomu.

## Konsekwencje dla wartości replaya (0004)
- Przy działającym pinie ukończone poziomy NIE są odwiedzane ponownie po śmierci,
  więc replay w obrębie runu zarabia głównie na: (a) `n_passes > 1` (kolejne passy
  przechodzą znane poziomy za darmo — tu jest duża wartość, por. Franzena 4 passy),
  (b) ubezpieczeniu, gdyby gateway ignorował pin po stronie klienta.
- Ocena sesji ARC ("nie dźwignia +18; skaluje się ze śmierciami i n_passes;
  kolejność: najpierw Franzen, potem replay") pozostaje SŁUSZNA — ale z innego
  powodu niż "śmierć kasuje całą ścieżkę".

## Jak rozstrzygnąć empirycznie (1 grep, 0 GPU)
W dowolnym transkrypcie prawdziwego runu, gdzie agent ukończył >=1 poziom i potem
zginął: pole `level` w pierwszym `Last action result` PO `game_over: True`.
- level == poziom śmierci -> pin działa na gatewayu.
- level == 1 -> pin nie działa i wniosek sesji ARC obowiązuje w pełni.
r050 ma tylko sk48 na poziomie 1 (nie rozstrzyga). Kandydat: output v7 z r063.

## Wymóg dla testu integracyjnego patcha
Przesłankę trzeba powtórzyć z `ONLY_RESET_LEVELS=true` ustawionym PRZED budową
klienta arc_agi; test ma pokrywać OBIE konfiguracje. Inaczej testujemy silnik,
którego zgłoszenie nie używa.
