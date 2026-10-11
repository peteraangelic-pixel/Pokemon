# Bill + Mirror forensics (2026-10-11)

User ask: "worth tackling Bill (0.648, hardest non-mirror) and mirror (42% of
losses)?" — Answer after forensics + 2 rejected agent variants: **not at the
agent level.** Details below.

## 1. The actual loss mechanism (instrumented, not guessed)

Both pools lose the same way: **board collapse**. Terminal state in a loss:
our `active=None, bench=[], hand=0` — last Pokémon KO'd with empty bench AND
empty hand → loss even with 30-45 cards left in the deck (you can't put a
basic from the deck into play).

- Bill (150g): 61/61 losses = empty board at end; **59/61 wiped by Mega
  Lucario** (2 by Koraidon); median loss turn 9.
- Mirror (150g): same mechanism (88-90% of losses), plus the terminal dumps
  show the opponent holding a full 4-bench while ours is empty.
- At the moment of the final KO we **never** had a basic in hand (0/320
  losses across 3 pools) — the hand was already spent.

Structural cause: **our deck has only 10 Pokémon (6 basic)** in 60 cards
(30 {W} + 20 trainers). We absorb at most ~10 KOs; Bill's line
(Aura Jab 130 @1F + Mega Brave 270 @2F, once-every-2-turns, + Koraidon
Impact 200 + 20 {F} + Ultra Ball/Mega Signal/Urbain refill) sustains ~200
dmg/turn. It's a tempo race we structurally lose ~35-38% of.

## 2. The Lucario line is 4 decks, and 3 of them we already beat

top30_live Lucario decks (677/678/979 present):
| deck | v21 win rate (interleaved, 500-800g) |
|---|---|
| Bill_Vlasak | **0.62-0.65** (the hard one) |
| OceanMix | 0.84-0.85 |
| Raja_Biswas | 0.86-0.90 |
| yu_kuo14 | 0.71 |

Bill = pure speed line (Riolu 4 / Lucario 3 / Koraidon 1 / Drilbur, 20 {F}).
The others add Solrock/Lunatone/Hariyama + retrieve engines — we beat those.

## 3. What I tried (and rejected) — v23, 2 variants, ~15k interleaved games

**v23 = v21 + "Boss's defuse":** when opp active is a charged Lucario/Koraidon
(≥2 {F}), boost using Boss's Orders to force one of their bench Pokémon into
the active (defuse the 270/200, set up a KO on the fresh body). The v11 base
scores Boss's as a generic card and never values it as a tempo-defuse.

- **v23a (loose gate):** net −1.44pp (z=−0.95) on the 4 Lucario decks, with a
  **Raja hole: −6.75pp (z=−2.77)** — Raja's deck has 4× Lucario + Gong/Judge/
  Lillie's×4, so the defuse is undone in one turn and we just burned Boss's.
- **v23b (tight gate: only force a killable basic ≤110HP, and only if no
  other ≥1F Lucario waits on their bench):** Raja hole gone (−0.6pp), full
  field test (11,898 games: 4 Lucario + mirror10@5000 + yaruki + leo +
  Alakazam + Kanga_Slowpoke) = **net +0.14pp (z=+0.21) = NET ZERO**. Bill
  specifically: +1.0pp then −4.0pp across two runs (±4pp at 500g); pooled
  1300g = −2.0pp (z=−1.1). Not a win.

Verdict: **both variants rejected** (agents/main_heuristic_v23.py deleted).
The v11/v21 baseline already uses Boss's near-optimally; the residual Bill
gap is tempo + Pokémon count, not a single fixable decision.

## 4. Why mirror is not locally actionable

The gauntlet runs **the same agent on both seats** (deck-only delta). A true
mirror is therefore a coin flip + deck-order noise locally — it structurally
cannot measure the real edge vs *other players'* Kyogre agents (we only have
their decks, not their logic). Local mirror numbers (0.43-0.59 across
samples) are that noise, not a signal. The only locally-visible lever is a
small tempo edge, which the v11 base already has (T1 Snover +40 nudge, KO
scoring, retreat-when-lethal).

## 5. Where the levers actually are

1. **Deck level (Bill)**: the 10-Pokémon ceiling is the real constraint.
   Candidates: replace weak trainers (Cyrano 1x, Maximum Belt 1x) with a 7th
   basic or 5th Abomasnow; add Waitress (3x→4x) for ramp. But the deck is
   shared by the whole top30 — a deck change is a field-wide A/B, a separate
   decision (and the c87f7a48 branch owns deck/submission work).
2. **v22b (stall attach planner)** remains the verified ship-able agent win
   (see v22_assessment_2026_10_11.md): +5.71pp pure stall (z=+3.39),
   bit-identical elsewhere.
3. **Mirror**: needs opponent-agent data (replay mining of *decisions*, not
   just decks) — a bigger project, deferred.

## 6. Tooling note

`tools/ab_interleaved.py` had a `pa = pb = [0,0,0]` list-aliasing bug (A and
B compared to themselves); fixed 2026-10-11. All numbers in this doc are from
the fixed tool.
