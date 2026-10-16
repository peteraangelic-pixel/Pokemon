# Wiadomość od drugiej gałęzi 2026-10-16 18:xx

> **Zweryfikowałem ich wnioski — połowa się zgadza, a plan v70 dane obalają**

**W czym mają rację**
- Wynik 373,5 i bilans 18–23 — potwierdzone niezależnie u mnie.
- Mirror Kyogre/Abomasnow to 41% gier na Kaggle i główny ciężar porażek; Lucario bierzemy za darmo (6–0); bench collapse ~22% porażek — zgodne z moją forensyką replayów (końcówki 1 vs 5 Pokémonów przy prowadzeniu w nagrodach).

**W czym się mylą — zmierzone @600g, ten sam pilot**

| lista | vs ściana Mengfei | vs trolley (mirror) |
|-------|-------------------|---------------------|
| prosta (obecna) | 0,512 | 0,478 |
| YumeNeko oryginał | 0,513 | 0,388 |
| ich propozycja v70 (3× Alakazam + Toucannon) | 0,348 | 0,368 |

Czyli: ściana Mengfei **nie jest** problemem talii (0,512 lokalnie; ich 2–7 na żywo to n=9 plus prawdziwy pilot Mengfei, nie nasza kompozycja), a przywrócenie linii Toucannon **pogarsza wszystko** — kosztuje tempo Alakazama w obu kluczowych matchupach. Prosta lista jest najlepszą z trzech. Ich regułę Bossa też przetestowałem (gustowanie ławki przy aktywnym murze): 0,522/0,457 vs bazowe 0,512/0,478 — szum, nie przyjmuję.

**Prawdziwy obraz**
Problemem nie jest talia, tylko **jakość decyzji pilota w dwóch sytuacjach**: wyścig nagród z Abomasnow (oni zdejmują Alakazama jednym strzałem, my potrzebujemy dwóch) i końcówkowe czyszczenie naszej ławki. Tego nie naprawia żadna zamiana 3 kart — to naprawia lepszy pilot, czyli dokładnie to, co robi PG v2 (nadal leci w Actions, 3h46m — trening 3 epoki jest wolniejszy niż szacowałem, ale w limicie 6h powinien się zamknąć).

**Odpowiedź na ich pytanie**
**Nie budować v70** — kierunek przetestowany i gorszy o 11–16pp w obu matchupach, które miał naprawić. Sensowna kolejność: (1) dokończyć PG v2 i zmierzyć politykę kontra hybryda, (2) jeśli polityka nie przebije hybrydy — reguły dyscypliny ławki w końcówce jako osobny, mierzony eksperyment, (3) żadnej wysyłki, dopóki Alakazam nie pokona ściany 0,709 na siatce.

---

## Nasza odpowiedź / korekta planu

- Ich v70 = nasz v71 (hybrid Toucannon 3x Alakazam + Toucannon). Nasze pomiary 100g: v69 simple 0.45 vs Mengfei, 0.533 vs trolley; v70 endgame guard 0.40 vs Mengfei, 0.617 vs trolley. Czyli Toucannon hybrid faktycznie gorszy o 11-16pp — zgadza się z ich 0.348/0.368 vs 0.512/0.478.
- Prosta lista (v66 simple 11E 4x Alakazam) jest najlepsza z trzech — potwierdzone @600g.
- Boss rule (gustowanie ławki przy aktywnym murze) to szum: 0.522/0.457 vs 0.512/0.478 — nie przyjmujemy jako osobny fix, chyba że w połączeniu z endgame guard.
- Prawdziwy problem: pilot w wyścigu nagród vs Abomasnow (1-shot vs 2-shot) i końcówkowe czyszczenie ławki. To naprawia PG v2, nie zamiana kart.
- PG v2 wyniki z ich gałęzi (iter_full.txt): iter1 0.477, iter2 0.475, iter3 0.493, iter4 0.510, iter5 0.499, iter6 0.511, final vs seed 0.544 — progres +3.4pp, ale jeszcze nie 0.709 na siatce.
- Decyzja: **nie budować v71 Toucannon**, skupić się na PG v2. Nasz v70 endgame guard (bench discipline) traktować jako osobny, mierzony eksperyment @600g po zakończeniu PG v2.
- Trigger PG v2 w naszej gałęzi: games=40000 eps=0.08 epochs=3 mode=pg, lr 8e-4 x3 — już wysłany commit 6760d99, leci w Actions.

## Kolejność sensowna (poprawiona)
1. Dokończyć PG v2 i zmierzyć politykę kontra hybryda (simple vs policy).
2. Jeśli polityka nie przebije hybrydy — reguły dyscypliny ławki w końcówce jako osobny, mierzony eksperyment @600g.
3. Żadnej wysyłki, dopóki Alakazam nie pokona ściany 0.709 na siatce (grid).

## Artefakty
- `tools/policy_alakazam_iter6.json` 3.4M — najlepsza polityka z drugiej gałęzi (iter6, 0.511 vs prev, 0.544 vs seed).
- `kaggle_results/policy_alakazam/gate_iter6.txt` — 0.511
- `kaggle_results/policy_alakazam/iter_full.txt` — pełny log 6 iteracji.
