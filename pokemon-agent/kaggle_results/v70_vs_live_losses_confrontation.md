# Wyniki po ~4h + konfrontacja v70 z przegranymi meczami (2026-10-18)

## Submisje (poll 194c457 + fetch c87 1befaa8)
- 57318827 v67: 443.2, rekord 29W-35L (64 ep)
- 57327179 v69r (ich, reczna wysylka usera): 417.5, 26W-42L (68 ep)
  (duplikat 57327167: 421.9; wczesny odczyt 535.0 = spike kalibracyjny)
- 57290311 v63: 436.7 | zespol #324 / 421.9
Kolejnosc po 4h: v67 > v63 > v69r. Nasz pomiar lokalny (v69r slabsza) sie zgadza.

## Porażki v69r (30/42 replayow czytelnych)
GLOD WRÓCIL: 50% porazek z 0 nagrod (v67: 29%). Mirror 10, inne 6,
Alakazam 5, Lucario 4, Fezandipiti 3, Crustle 2. Ich talia 31E + martwe
reguly pogorszyly to, co v67 naprawila.

## Konfrontacja v70 (Judge) z przegranymi meczami
Metoda: dla kazdego archetypu z list porazek - lokalny reprezentant,
WR v70 zmierzony na 300-2400g (mirror 0.505, Alakazam 0.543,
Fezandipiti140 0.683, Lucario 0.903, Crustle 0.277, Dragapult ~0.95).
Oczekiwany odsetek "odwroconych" porazek:
- porazki v67 (31): v70 ~55% (v67 samo ~54%)
- porazki v69r (30): v70 ~59% (v67 ~57%)
KRYTERIUM 80%: NIESPELNIONE. Zaden wariant regułowy go nie spelni -
80% flip oznacza agenta klasy 1000+ (RL), nie tech-karte (+3pp odwraca
~5-10% porazek, reszta to wariancja i sila zywych pilotow).

## Top 10 > 1000 (YumeNeko 1358.7 #1, submit 2026-10-17 14:35)
Z writeupow Simulation (7. miejsce, 15., 24., "Aim to Be a Pokemon Master"):
- Wylacznie polityki UCZONE: Transformer 1-10M param, PPO/IMPALA self-play
  vs liga 20-70+ zamrozonych przeciwnikow, progressive deck specialization,
  belief o rece/talii przeciwnika z historii gry.
- Meta talie: Dragapult ex (~36% laddera top), Alakazam; dysrupcja reki
  (Judge/Unfair Stamp) = najsilniejsza bron vs Alakazam (79% WR, 70 gier)
  - niezaleznie potwierdza kierunek naszej v70.
- Czyste reguly: sufit 600-700 (opublikowany writeup regułowy).
Wniosek: 1000+ = program RL (tygodnie, GPU/Actions), nie kolejne regulki.
Nasze reguly asymptote ~440-550.
