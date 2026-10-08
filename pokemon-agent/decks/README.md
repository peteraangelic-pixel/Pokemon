# Deck variants — measured, rejected, kept on purpose

These are **failed experiments**, not alternatives worth trying. They live here
so the negative result survives; the shipped deck is still `../deck.csv`.

| file | change vs `deck.csv` | gauntlet overall | crustle_wall | sylveon_safeguard | vs baseline deck |
|---|---|---|---|---|---|
| `deck.csv` (shipped) | — | **0.780** | **0.325** | **0.500** | 0.483 |
| `gust.csv` | +2 Boss's Orders (1182), −2 energy | 0.444 | 0.217 | 0.358 | 0.383 |
| `attacker.csv` | +2 Kyogre, +2 Boss's Orders, +2 Ultra Ball, −6 energy | 0.469 | 0.292 | 0.400 | 0.425 |

(120 games per archetype per seat; the "vs baseline deck" column is our variant
against our own shipped list, which is the cleanest head-to-head deck test we
have — it should read ~0.500 for an equally strong deck.)

## Why they lost

Both variants pay for their new cards with **basic Water energy**, and in a mill
deck that is not a free currency. Hammer-lanche discards the top 6 cards and
deals 100 per Basic `{W}` Energy among them, so its expected damage is directly
proportional to the energy density of the deck:

| energy in deck | water rate | Hammer-lanche |
|---|---|---|
| 33 (shipped) | 0.550 | ~330 |
| 31 (gust) | 0.517 | ~310 |
| 27 (attacker) | 0.450 | ~270 |

Trading 60 damage per attack for a gust effect we could not reliably find (2
copies, and Petrel is our only tutor) left us worse in **every** matchup, not
just the walls the change was aimed at.

## What this tells us

The 33-energy count in the engine's sample list looks sloppy — real decks run
8-14 — but for *this* archetype it is load-bearing. The obvious "fix the sample
deck" advice does not transfer. If we ever want those trainer slots, they have
to come from somewhere other than energy.

## Still untested

- Cutting **trainers** instead of energy to make room (we have 4x Petrel, 4x
  Lillie's Determination — both look cuttable).
- A third attacker that is not an `ex`, so the wall matchup has an out without
  needing to be drawn at the right moment.
- Whether Crustle is even common enough on the ladder to be worth a slot.
