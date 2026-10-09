# NOTES_STRATEGY — why this agent is built the way it is

> Working design journal for **The Pokémon Company – PTCG AI Battle Challenge
> Playground**. This is the raw material for a future writeup on the paid Strategy
> edition, so it records *reasoning and evidence*, not just conclusions. Every
> claim below is either marked **[verified]** (we ran it), **[reported]** (public
> source), or **[assumed]** (untested — flagged so we can kill it later).

---

## 1. The setup, and what we are actually optimising

The leaderboard is a **Gaussian skill estimate N(μ, σ²)** seeded at μ₀ = 600, not a
win rate. Three consequences that shape the whole project:

* **σ matters as much as μ early on.** New submissions get a higher episode rate to
  shrink σ fast, so the first day of a new submission is the cheapest information we
  will ever get. Day-1 noise must not be over-interpreted.
* **Margin of victory is irrelevant** — only win/draw/loss updates μ. So there is no
  reason to play for style or speed, and every reason to play for *stability*: one
  crash costs a whole submission slot (5/day).
* **Only the latest 2 submissions are live.** A new submission does not just add an
  agent, it *retires* an older one. So we should never "just try something" with both
  slots occupied by something known-good — the cost of a bad experiment is losing a
  working agent.

**Therefore the prime directive is: never Error.** An agent that is mediocre but
never crashes accumulates μ. An agent that is brilliant but crashes on one rare
observation shape loses the entire run.

---

## 2. What we learned from the summer 2026 (paid) edition

The playground is a continuation of `pokemon-tcg-ai-battle` (simulation, 6,807 teams)
and `pokemon-tcg-ai-battle-challenge-strategy` ($240k, judged on writeup quality).
Public writeups — this is the highest-value research we have:

### 2.1 The proven lever is the *deck*, not the policy  **[reported]**

One team's project notes are blunt: *"The ONE proven lever: meta-counter
(rock–paper–scissors). Dragapult > Trevenant > Alakazam > Dragapult. Read replays →
find the rising archetype → ship its counter, do NOT mirror it."* Their own attempt
to mirror the meta *flopped at 460*, while shipping the counter hit ~900–978.

Another team reported that **53 % of their losses were structural** — decided by the
matchup, before any play decision. And the 1st-place simulation solution spent a large
part of its effort on **deck archetype clustering and card-by-card mutation** rather
than only on the network.

**Implication for us:** policy quality has a ceiling set by the deck. Our Phase 1
should therefore not be judged only by "does the heuristic play well", but by
"is this deck worth playing well with". Deck work is Phase 2's first item.

### 2.2 Rule-based agents ceiling at ~600–700  **[reported]**

A team that deliberately went rule-based (and chose the *same* Mega Abomasnow ex deck
we start on) reported: *"climbed to a stable rating of around 600, winning roughly
50–60 % of its matches… around 600–700 the bot stops improving because it cannot look
ahead."* This independently validates the user's Phase 1 target of ~600+ and tells us
the Phase 2 trigger: **when μ stalls near 650, stop tuning rules.**

### 2.3 Hand-written rules *hurt* the top RL agents  **[reported]**

7th place: *"hand-written rules and mechanical teachers — every one we tested cost win
rate, by up to 36 points. Our reading: a rule covers only the cases we thought of, and
training writes the rest into the weights as error."*

This is **not** an argument against our Phase 1. It is an argument about *where rules
belong*: they cost a top-tier learned policy because the policy can already learn the
case; they *help* a Phase 1 agent that has no policy at all. The same team kept exactly
one class of hand-written logic at inference — **a lethal check** — because *"lethal
detection is computation, not strategy"*. That distinction is the design line we should
copy: **hand-code computation (rules of arithmetic), learn judgement.**

### 2.4 Feature exposure beat feature engineering  **[reported]**

7th place again: *"When the policy played badly, we looked for a quantity it could not
see rather than a rule to impose… The line that added the knockout distance gained 4.3
points of win rate (z=2.5 over 1,500 games per arm)."* The features were: energy still
missing after an attach, damage counters left to a knockout and the prize it pays,
which energy unlocks which attack, damage after weakness and resistance.

Our Phase 1 heuristic already computes exactly these quantities for its own ranking
(§4). The natural Phase 2 step is to *expose them as inputs* to a learned policy instead
of consuming them inside rules.

### 2.5 Sample-size discipline  **[reported]**

* *"Around 100 games per opponent are too few for a reliable win-rate estimate. At
  least 500 games per opponent are needed."*
* 7th place reported four blocks of 250 games reading 58.0 / 56.8 / 56.4 / 58.4 and
  called 1,500 games per arm the bar for a feature decision.

Our local arena runs a full BO1 game in ~0.15 s, so 2,000 games ≈ 5 minutes. **We can
and should buy the sample size that the ladder cannot give us** — this is the single
biggest structural advantage of the local engine.

### 2.6 Going first is worth ~6–8 points of win rate  **[verified, ours]**

We A/B'd our own agent against itself with only the `IS_FIRST` answer flipped:
**76–44 over 120 games = 63.3 % for the player who chooses to go first** (z ≈ +2.9).
7th place independently reported 57.9 % as the seat that chooses. So `GO_FIRST = True`
is a measured decision, not a guess — and it is worth ~1 energy attachment of tempo
with a deck that needs three.

### 2.7 A trap worth remembering  **[reported]**

The rule-based writeup lost games (and possibly crashed) by playing cards whose
*cost* it could not pay: Buddy-Buddy Poffin with fewer than 2 Basic Pokémon in hand,
or a search card whose target was already in hand. **Our legality is guaranteed by the
engine** (it only offers legal options), but the *pre-condition* checks are on us —
the engine will offer a search card and then ask us to pick a card we cannot use.
This is why our search/utility scoring is precondition-aware (§4.4).

---

## 3. Architecture decisions

### 3.1 Single-file, stdlib-only agent  **[decision]**

`main.py` imports nothing but `json`, `os`, `random`, `re`. Reasons:

1. The harness imports `main.py` from an unpacked directory we do not fully control;
   any import-time failure is an instant `Error`.
2. Every extra module is a packaging failure mode.
3. No numpy means no version skew against the Kaggle Docker image.

The card database is a separate `card_index.json` (443 KiB, 1,431 cards + 1,755
attacks) loaded from a list of candidate paths. **If it fails to load, the agent still
plays legally** — all lookups degrade to neutral defaults rather than raising. We
prefer a dumber agent to a dead one.

### 3.2 Bands, not weights  **[decision]**

The engine lets us act in **any order within a turn, and attacking ends the turn**.
That single fact makes naive "score each option" dangerous: if a knock-out attack
scores highest, the agent will attack *before* attaching its energy and silently lose
a turn of development.

So scores are not free parameters — they are **bands with a hard ordering**:

```
340  play a Supporter (draw / search)
330  play an Item (search / utility)
320  put a Basic on the Bench
310  evolve
300  attach Energy / Tool
290  play a Stadium
270  use an Ability
260  attack that takes a prize
200  any other attack
120  retreat (raised to ~285 only when we are escaping a knockout)
 20  discard / junk
  0  end turn
```

Every setup band is strictly above every attack band. That is the invariant to
preserve when editing; the exact numbers inside a band barely matter. We verified the
consequence empirically: the diagnostic counts **0 turns ended with an attack
available** while a real attack was on offer.

### 3.3 Estimate damage, never model it  **[decision]**

We do not try to reproduce the engine's damage calculation. We estimate:

* printed damage when present;
* **variable-damage attacks parsed from effect text** (see §4.2) — this matters more
  than it sounds;
* weakness/resistance as ±30 **[assumed]** — the modern flat-weakness rule, not
  verified card-by-card against the engine.

Estimates are only used to *rank our own options*. The engine decides outcomes, so a
wrong estimate costs a suboptimal move, never an illegal one. This keeps the blast
radius of a modelling error small.

---

## 4. What the Phase 1 heuristic actually does

### 4.1 Deck plan inference

The deck is fixed and known, so at import we compute the deck's **plan**: the
highest-value evolved Pokémon (HP + 120/ex + 200/Mega ex + stage bonuses), then walk
`evolvesFrom` by card name to get the pre-evolution chain.

For our sample deck this correctly yields `Snover → Mega Abomasnow ex` and marks
Kyogre as off-plan. `plan_power(cid)` then feeds setup, search, and discard choices, so
the agent protects and develops the cards that actually win.

*Known weakness:* `evolvesFrom` matching is **by name**, so alternate printings of the
same name collapse together, and a deck with two co-equal lines would pick one. Both
are acceptable for a single-plan deck.

### 4.2 Variable-damage estimation — the highest-value Phase 1 fix  **[verified]**

**429 of 1,755 attacks (24 %) carry `damage = 0` and put the real number in the effect
text.** Our first heuristic scored them all as zero damage. The concrete consequence:

| Attack | printed damage | reality |
|---|---|---|
| Hammer-lanche (Mega Abomasnow ex) | `0` | *"100 damage for each Basic {W} Energy card you discarded"* from the top 6 |
| Riptide (Kyogre) | `0` | *"20 damage for each Basic {W} Energy card in your discard pile"* |

With 33 Water Energy in a 60-card deck, Hammer-lanche averages **~330 damage for two
energy** — the deck's actual win condition — and the agent was rating it *below* the
printed 200-damage Frost Barrier.

The fix parses `does (\d+) damage for each <subject>` and estimates the subject count
from the board:

* *mill* ("…you discarded in this way") → `n_cards × P(drawn card is that energy)`,
  where the probability comes from a **deck census**: we know our own 60 cards and can
  see hand + discard + attached energy, so "energy left in deck / deckCount" is a good
  estimate rather than a guess. On a real mid-game state this produced `deckCount=19`,
  water rate `0.842`, Hammer-lanche estimate **505** (vs 200 printed for Frost Barrier).
* *discard pile* → counted directly from both discard piles.
* *hand / bench / stadium / damage counters on self* → counted directly.
* Unrecognised patterns stay at **0**. We would rather under-rate an attack we do not
  understand than invent a number and have the agent commit to a fantasy.

We also added a guard the naive version lacked: **never use a mill attack that eats
more cards than we have left in the deck** — otherwise our own win condition decks us
out and hands the opponent the game.

**Result: 56.65 % win rate over 2,000 games (1113-887, z = +5.05)** — the single largest
improvement in Phase 1. An earlier 300-game run of the same change read z = +1.15 and looked
like noise; the effect was real and 300 games simply could not see it (§5).

### 4.3 Energy attachment is the scarcest resource

One attachment per turn, so the question is never "which Pokémon is biggest" but
**"which attachment turns on an attack?"** The scorer compares the target's cheapest
usable attack cost against its current energy:

* `have + 1 >= cost` and `have < cost` → **+30** (this attachment enables the attack)
* `have < cost` → **+18** (progress)
* already online → **+4** (extra energy is nearly worthless)

Plus +12 for the Active slot (energy on the bench does nothing this turn) and +10 for
the deck's primary line.

> An earlier version had this **backwards** — it rewarded attaching to already-powered
> Pokémon. Worth remembering as a case where the code looked reasonable and was
> exactly inverted.

### 4.4 Precondition-aware utility scoring

The engine only offers *legal* options, but legality ≠ usefulness. A search card is
legal while its target sits in hand; Ultra Ball is legal with 3 cards in hand that we
would rather keep. So:

* **Discards** rank by `card_value − 6 × (copies already in hand)`, so we shed surplus
  basic energy (value 12) long before a deck-critical evolution (value 90+).
* **Searches** (`TO_HAND`, `LOOK`) score by what we *want* now: plan cards high, extra
  energy low, and +60 for a Basic when our bench is empty.
* **Tools/Stadiums** are deliberately low (44/40) — they are the best things to throw
  away and the least urgent to deploy.

### 4.5 Retreat is conditional, not reflexive

The rule-based writeup used "HP < 50 → retreat (score 250)". We use two triggers
instead, because retreating costs energy and a turn:

1. **We cannot attack and we have a bench** → ~205. Retreating converts a wasted turn
   into a developed board.
2. **We are about to be knocked out** (opponent's best estimated damage ≥ our HP),
   our HP ≤ 80, and the bench has an equal-or-better body → ~285.

Deliberately *not* implemented: retreating to dodge a knockout when the bench is
worse, and "tanking" logic. Those need board evaluation we do not trust yet.

---

## 5. Measurement: how we decide what ships

**The ladder gives ~100 games per opponent — not enough.** 7th place needed 1,500
games per arm. So every design question is settled **locally first**:

```bash
python tools/ab_test.py --agent agents/main_heuristic.py \
    --env-a "PTCG_VAR_DMG=1" --env-b "PTCG_VAR_DMG=0" --games 2000
```

Design decisions that make this trustworthy:

* **Mirror match, single knob.** Identical deck, identical code, one env var.
* **Sides alternate every game** so first-player advantage cancels (important — we
  measured it at 63.3 %).
* **z-score reported**, and the tool prints the sample size the observed effect would
  actually need.

**The lesson we learned the hard way:** a mirror match between two near-identical
agents has *enormous* variance, because the deck's draw luck dominates. A 300-game
run of a genuinely-good change returned z = +1.15 — indistinguishable from noise. The
effect was real; 300 games simply could not see it. **Budget thousands of games, not
hundreds**, and treat any single-day ladder move under ~15 μ as uninformative.

The corollary for the daily submission budget: with 5 submissions/day and only 2 live,
we should spend **at most one slot per hypothesis**, and ideally pair each experiment
with a known-good agent in the other slot so a bad experiment cannot leave us with
nothing.

---

## 6. Open questions / next hypotheses

Ordered by expected value:

1. **Deck optimisation.** §2.1 says this is the proven lever, and our list is the
   engine's untuned *sample* deck: 33 basic energy, only 10 Pokémon, 17 trainers. The
   rule-based writeup's version of this deck added **Energy Retrieval / Energy
   Recycler** to loop Hammer-lanche — our sample list has neither. Concrete next step:
   swap in recycling cards, then measure old-vs-new deck in the local arena with the
   *same* policy. Because both agents are ours and the deck is a build artifact, this
   is a clean, high-signal experiment.
2. **Lethal search.** The one hand-coded thing the 7th-place team kept. A depth-first
   check over our turn's move combinations that proves a knockout, overriding the
   scorer. "Computation, not strategy" — so it cannot be penalised by the
   rules-hurt-RL finding.
3. **Phase 2 policy.** Either (a) behavioural cloning from our own heuristic's games as
   a warm start, then PPO self-play — the route the top teams took — or (b) determinized
   MCTS using the engine's own `search_begin` API, which the SDK exposes
   (`search_begin/search_step/search_end`) and which we have not touched yet.
   Reportedly *"search in training gave nothing over greedy"* **[reported]**, which
   argues for (a) and for using search only as a scoring overlay at inference.
4. **Opponent modelling.** No turn has been spent on it. Inferred archetype →
   counter-move selection is where the 1st-place team's later gains came from.
5. **Kill the ±30 weakness assumption.** Parse real weakness/resistance per card from
   the engine rather than assuming the modern flat rule.

## 6b. Deck construction rules, discovered the hard way  **[verified]**

Our robustness fuzzer kept reporting games that ended with both seats `INVALID` and a
nonsense `TypeError: 'Struct' object is not callable` from inside the harness. The
cause was **our test generator**, not the agent, and chasing it down produced four
findings worth keeping:

1. **The engine validates decks** and rejects illegal ones at battle start with
   `errorPlayer >= 0`, `errorType 4` — the episode then never runs a single turn.
2. **The 4-copy limit is by card *name*, not card id.** One `Espurr` printing plus
   four of a different `Espurr` printing is five Espurr and is illegal. Counting by
   id (the obvious implementation) silently passes illegal decks.
3. **Basic Energy is exempt** from the 4-copy limit — which is what makes a
   33-energy deck legal at all.
4. **ACE SPEC is capped at 1 per deck, and ACE SPEC includes energies**, not just
   trainers: Legacy Energy, Neo Upper Energy and Enriching Energy are all ACE SPEC,
   so "4 copies of a special energy" can break the rule without any trainer involved.

All four are encoded in `tools/deck_rules.py`, which any Phase 2 deck candidate must
pass before it is worth measuring.

**And the harness lesson, which is the one that could actually cost a submission:**
`kaggle_environments` inspects the agent callable's **arity**. A callable accepting two
parameters is invoked the legacy way as `(observation, configuration)` — so a helper
wrapper written as `def wrapped(obs, agent=agent)` silently receives the *environment
configuration* as its observation. Our submitted `agent(obs)` takes exactly one
argument and is safe, but this is the kind of bug that produces a confusing
`Error` status on the ladder with no obvious cause.

---

## 6c. The local gauntlet: we beat nine archetypes and get crushed by two  **[verified]**

`tools/gauntlet.py` plays our agent and our deck against eleven auto-assembled
archetype decks, from both seats, 200 games per seat. Both sides run the same
policy, so the deck and the matchup are the only variables.

| archetype | our win rate | z |
|---|---|---|
| **crustle_wall** | **0.195** | −8.70 |
| **sylveon_safeguard** | **0.285** | −6.15 |
| ours (mirror) | 0.465 | −1.06 |
| dragapult | 0.830 | +9.26 |
| bronzong_lock | 0.845 | +9.69 |
| trevenant | 0.860 | +10.11 |
| charizard_mega | 0.880 | +10.68 |
| pikachu_tera | 0.935 | +12.23 |
| gardevoir_mega | 0.960 | +12.94 |
| raging_bolt | 0.970 | +13.22 |
| alakazam | 1.000 | +14.07 |

Nine archetypes we crush. Two we lose badly — and they are the two decks built
around *"prevent all damage done to this Pokémon by attacks from your opponent's
Pokémon {ex}"*. That coherence is the evidence: it is one mechanism, not noise.

We confirmed it rather than inferring it. A 181-step game against Crustle ended
with the opposing Crustle at **hp 150/150 — it had taken literally zero damage**
— while we had 11 cards left in deck and 32 in the discard, having milled our
own deck for nothing. Wall games also run 4-5x longer than any other matchup,
which is what a game looks like when neither side can finish.

**The trap worth writing down.** The engine reports our Mega Abomasnow ex with
`ex == 0` and `megaEx == 1`. The anti-ex abilities say "Pokémon {ex}", and the
engine applies them to us anyway — a Mega *is* an `{ex}` attacker here. Any
implementation that read the `ex` flag alone would have concluded we were immune
and shipped a 0.195 matchup. We only found it because we measured.

**The fix.** Damage-prevention abilities are parsed once, at index build time
(where the full card text exists), and shipped as a compact `pv` flag — at
runtime the agent only sees skill *names*, so text parsing has to happen
offline. Every damage estimate then passes through `damage_prevented()`, and
when our Active is walled we switch in an attacker that can actually hit.

| archetype | before | after |
|---|---|---|
| crustle_wall | 0.195 | **0.325** |
| sylveon_safeguard | 0.285 | **0.500** |
| overall | 0.748 | **0.780** |

No other matchup moved outside noise. Sylveon went from a lost cause to even.

## 6d. A negative result: the 33-energy "sloppy" deck is load-bearing  **[verified]**

The sample list ships 33 basic Water energy, where real decks run 8-14. It looks
like the obvious thing to fix, and the summer writeups did fix it in their build.

We tried. Two variants, both measured worse in **every** matchup, including
straight up against our own shipped list:

- `+2 Boss's Orders, −2 energy` → 0.383 vs baseline
- `+2 Kyogre, +2 Boss's Orders, +2 Ultra Ball, −6 energy` → 0.425 vs baseline

The reason is that Hammer-lanche discards 6 cards and deals 100 per Basic
`{W}` Energy among them, so its expected damage is proportional to the energy
density of the deck: 33 energy → ~330 damage, 27 energy → ~270. We were trading
60 damage per attack for a gust effect we could rarely find.

**So the deck stays as it is.** Full write-up in `decks/README.md`, kept
precisely so we do not re-run this experiment in three months. The lesson is
narrower than "the deck is good": it is that generic deckbuilding intuition does
not transfer to a mill archetype, and that any future card we want has to be
paid for out of the 17 trainer slots, not the energy.

---

## 6e. The bug that cost two submissions, and why our tests could not see it  **[verified]**

Both first uploads failed at import:

```
File "/kaggle_simulations/agent/main.py", line 240, in _candidate_dirs
    here = os.path.dirname(os.path.abspath(__file__))
NameError: name '__file__' is not defined
```

Kaggle does not import our module; it compiles the source and `exec`s it
(`kaggle_environments/agent.py` → `get_last_callable` → `exec(code_object, env)`).
In that namespace there is no `__file__`. Anything running at import time that
touches it raises, the submission is marked Error, and the only feedback is a
downloadable log.

**The part worth remembering is not the bug, it is the blind spot.** We had a
smoke test, it ran self-play through the real engine, and it passed. But it
loaded the agent with `importlib.util.spec_from_file_location`, and **importing
defines `__file__`**. The test reproduced the game and not the loader, so it was
structurally incapable of catching this class of failure.

The general lesson: a submission is not "the agent", it is "the agent **as loaded
by a specific harness**". Those differ in ways that matter — here the namespace,
earlier the callable's arity (§6b). The gate has to replay the harness's loading
procedure, not merely exercise the logic.

`tools/test_kaggle_import.py` does that, and `build_submission.py` runs it on
every build and refuses to ship if it fails.

---

## 6f. Kaggle picks the *last callable in the file*, not the one named `agent`  **[verified]**

Second upload attempt: the random agent passed, the heuristic failed, same day,
same packaging. The log:

```
agent.py:154, in callable_agent
    return agent(*args) if callable(agent) else agent
TypeError: _score_yes_no() missing 3 required positional arguments
```

`self.agent` is `_score_yes_no`. Because `get_last_callable()` ends with:

```python
return [v for v in env.values() if callable(v)][-1]
```

There is no lookup by name. **Kaggle takes whichever callable was defined last
in the file.** Our helpers sat below `agent`, so one of them became the agent.
`main_random.py` happened to define `agent` last, which is the entire reason one
submission worked and the other did not.

This is the third harness difference that no amount of local game-playing could
have found — after the namespace (`__file__`, §6e) and the callable's arity
(§6b). The pattern: **the unit of deployment is not the agent, it is the agent
as loaded by a specific loader.** We now test with Kaggle's own
`get_last_callable()` so the ordering is enforced by the build, not by memory.

---


## 6g. Wall v2: from 0.30 to 0.61 vs Sylveon, 0.36 to 0.45 vs Crustle  **[verified]**

v1 added damage_prevented() and a 300 retreat + 60 gust bonus. It moved Sylveon
from 0.285 to 0.500 but left Crustle at 0.367 — still losing.

v2 observation from a live replay mental model: when walled, we were
1. retreating but picking another Mega as Active (fighter_score didn't know about walls)
2. attaching energy to the walled Active or another walled bench
3. ignoring Surfing Beach (free {W} switch) which is exactly the out

Fix:
- _fighter_score(poke, obs, opp_active) penalises walled attackers -500 and
  boosts the non-walled escape attacker +200 when we are walled
- TO_ACTIVE/SWITCH scoring uses wall-aware fighter_score
- RETREAT when walled scores 340 (above Supporter 340 band, so we escape before drawing)
- ATTACH when walled: +40 to non-walled bench, -20 to walled bench
- PLAY Surfing Beach when walled: 345 (immediate)

Result 60 games/seat:
  crustle_wall 0.367→0.450, sylveon 0.300→0.617, mirror 0.617→0.533 (noise),
  overall 0.776→0.809, 0 engine errors.

The deck still has 0 gust cards, so we cannot force the wall to bench. Our only
out is Kyogre (non-ex, 2 copies). v2 makes the agent actually find it.

---

## 7. Things we deliberately did *not* do yet


* **No RL.** With 5 submissions/day, 2 live slots, and a 3-month runway, a Phase 1
  agent that never crashes is worth more than an untrained network. Learning starts
  once the arena and packaging are proven.
* **No opponent-hand tracking.** Possible from the logs, but every hidden-information
  belief is a new crash surface. Deferred until a supervisor-style wrapper exists.
* **No time-consuming search.** `remainingOverageTime` is 600 s and `actTimeout` is 0;
  Phase 1 decisions are ~0.1 ms, leaving the whole budget for Phase 2.
