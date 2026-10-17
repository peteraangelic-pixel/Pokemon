# Weryfikacja c87 v68_resistant / v69_resistant_v2 (2026-10-17 noc)

## Ich deklaracje (harness FFI 20g)
v68: top30 0.909 vs v67 0.894, new_losses 0.700 vs 0.691. v69: test w toku.

## Nasze pomiary (prizetest/grid, artefakty z paczek)
| test | wynik |
|---|---|
| ich v68 (pilot+talia) vs nasze v67+trolley, 1200g | **0.443** |
| ich v69 vs nasze v67+trolley, 1200g | **0.462** |
| ich pilot v68 na ICH talii vs champion | 0.482 |
| NASZ v67 na ich talii vs champion | 0.522 |
| ich talia + nasz pilot, siatka 4800g | 0.690 (trolley: 0.714) |
| ich v68 siatka | 0.694 |

## Ustalenia
1. Talia legalna (60 kart, 1 ACE SPEC Maximum Belt) - ale INNA niz trolley:
   31E, Mega Signal x4, zero Petrel/Trolley, +Poke Pad/Belt/Amarys/Waitress.
2. Blok anty-FEZANDIP celuje w karty SPOZA talii: Poffin 1086, Judge 1213,
   Prime Catcher 1088, Sacred Ash 1129 - martwy kod (jest tylko 1x Stretcher).
   Poffin i tak nie lapie Snovera (90HP > 70HP).
3. Na tej samej talii nasz pilot bije ich pilota o 4pp (0.522 vs 0.482) -
   ich blok regul szkodzi; ich talia z naszym pilotem tez slabsza na siatce.
4. Zgodne z nami: mirror naprawiony (live vs KYOGRE 0.57), nowy problem =
   Fezandipiti/Alakazam (Cruel Arrow 100 > Snover 90HP; Powerful Hand vs reka).
   Ich probki live male (0-5, 1-5), kierunek prawdziwy, skala niepewna.

## Werdykt
v68/v69 NIE do wysylki (regres na metryce przyczynowej i siatce).
v67+trolley zostaje. c87 w faf6677 zgadza sie: (a) pilot z horyzontem >
(b) przebudowa talii; v67 zostaje 24h na stabilizacje.
