# FAZA 2: jak dogonic top10 (1000+) - plan i fundament

## Diagnoza (writeupy Simulation + nasze dane)
- Sufit heurystyki: 600-700 (opublikowane). My: ~440. Zostalo troche
  miejsca w regulach, ale nie na 1000.
- Top10 = polityki uczone: Transformer 1-10M, PPO/IMPALA self-play vs
  liga 20-70+ zamrozonych przeciwnikow, belief z historii, meta talie
  (Dragapult ex ~36% top laddera), dysrupcja reki (Judge/Unfair Stamp).
- Lever meta-counter (18. miejsce): Dragapult > Trevenant > Alakazam >
  Dragapult; wysylaja countera na biezaca mete, nie mirrora.

## Co juz mamy (ten commit)
- tools/league_eval.py: round-robin pilotow + rating Bradley-Terry
  (jak 24. miejsce). Pierwsza tabela @300g/par (szum!): champion 1055,
  v63 1032, v67 1024, v70_judge 1000, v70_horizon 989, v69r 958,
  alakazam_hybrid 942. Wniosek: wrapery daja w H2H tyle co nic;
  v69r potwierdzona najslabsza. Liga = metr dla kazdego pilota Fazy 2.

## Plan (kolejnosc)
1. LIGA JAKO SRODOWISKO: zamrozic 8-12 pilotow (champion, v63, v67,
   obie v70, hybryda Alakazam, piloci puli top30 od c87) x talie mety
   (trolley, Alakazam, Dragapult z puli, Crustle, Lucario).
2. RL: PPO na opcjach (akcja = wybor z listy legalnych, cechy stanu
   jak w championie + historia) - trening na Actions (Rust 180 g/s,
   linia c87) lub PC usera (bench_pc v2 czeka). Start: Dragapult albo
   trolley; nagroda = wygrana; ewaluacja co iteracje LIGA (nie mirror!).
3. SEARCH DETERMINISTYCZNY (tani, rownolegle): lethal-check juz jest;
   dolozyc 1-ply ocene ataku/ucieczki tylko w waskich bramkach
   (margin>=prog), mierzone w lidze.
4. META-COUNTER: co tydzien z replayow top (fetch c87) klasyfikowac
   mete i wybierac talie/pilota z ligi pod nia, zamiast jednej talii.

## Czego NIE robic (udowodnione martwe konice)
- BC/PG od slabszego nauczyciela; CEM na malym harnesse; kolejne
  regulki wrappera (+-3pp); talia 31E; martwy kod (reguly bez kart).
- Decyzje na <1200g i na pulach ze slabymi pilotami (new_losses FFI
  zawyza: wszyscy ~0.79, live flip ~55%).
