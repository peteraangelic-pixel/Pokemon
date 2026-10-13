# Win Condition Hypotheses Registry

Based on analysis of 25 demo games. Agent should systematically test these hypotheses.

## Type 1: Pattern Clearing (remove specific colors)
**Example:** cn04 - remove all pixels of colors 8 and 13 from sprites
**How to test:** Check if game has sprites with specific colors that need to be removed
**Signature:** Function checks sprite pixels for specific color values (8, 13 = orange/red in ARC)

## Type 2: Timer-Based (countdown to zero)
**Example:** ft09, ls20 - countdown timer, win when time expires
**How to test:** Check if game has decreasing counter (self.dzy, self.current_steps)
**Signature:** Boolean function returns `counter > 0` or `counter >= 0`

## Type 3: Pattern Matching (match colors between sprites)
**Example:** sk48 - match pixel colors between sprite pairs
**How to test:** Check if game compares pixel colors across multiple sprites
**Signature:** Function iterates over sprite pairs, compares `sprite.pixels[x,y]`

## Type 4: Position-Based (reach target location)
**Example:** TBD - move sprite to specific coordinates
**How to test:** Check if game has target coordinates and checks sprite position
**Signature:** Function compares `sprite.x, sprite.y` to target values

## Type 5: Collection-Based (collect all items)
**Example:** TBD - collect/eliminate all sprites of certain type
**How to test:** Check if game tracks visible sprites and checks if all are gone
**Signature:** Function iterates over `level.get_sprites()`, checks `is_visible`

## Type 6: State-Based (achieve specific game state)
**Example:** TBD - arrange sprites in specific configuration
**How to test:** Check if game validates sprite positions/rotations/states
**Signature:** Function checks multiple sprite properties (position, rotation, visibility)

---

## Hypothesis Testing Protocol

When agent encounters new game:
1. **Observe first 10 actions** - what changes on screen?
2. **Identify sprite types** - which sprites are interactive?
3. **Test Type 1-6** - which hypothesis matches observed behavior?
4. **Record result** - save which hypothesis was confirmed/refuted
5. **Execute strategy** - once hypothesis confirmed, optimize for speed

## Priority Order (based on frequency in demo games)
1. Pattern Clearing (most common)
2. Timer-Based
3. Pattern Matching
4. Collection-Based
5. Position-Based
6. State-Based

---

*Registry built from 25 demo games. Agent should test systematically, not guess.*
