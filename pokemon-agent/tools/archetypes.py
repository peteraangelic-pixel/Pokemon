"""Archetype deck builder for the local gauntlet.

We cannot see the real Kaggle ladder meta, so we do not pretend to reproduce
"the meta".  What we build instead are **mechanic probes**: decks chosen because
they exercise a different kind of pressure on our agent.

  - anti-ex walls (Crustle / Safeguard Sylveon)
  - evolution denial (Bronzong)
  - big stage-2 tera attackers (Dragapult ex, Pikachu ex)
  - mega ex attackers (Gardevoir, Charizard)
  - a plain aggressive basic ex (Raging Bolt)
  - a mirror (our own deck)

The decks are auto-assembled: give a headline attacker, and this module resolves
its evolution chain, picks matching basic energy, and fills the rest with a
generic staple package.  Every deck is validated against the engine's deck
construction rules (tools/deck_rules.py) before it is returned.

Run directly to build and validate every archetype:

    .venv/bin/python tools/archetypes.py
"""

from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from deck_rules import deck_problems, load_library  # noqa: E402

DATA = os.path.join(ROOT, "data")

# ---------------------------------------------------------------------------
# card database
# ---------------------------------------------------------------------------

with open(os.path.join(DATA, "cards.json")) as fh:
    _CARDS = json.load(fh)
CARDS = {c["cardId"]: c for c in _CARDS}
BY_NAME: dict[str, list[int]] = {}
for _c in _CARDS:
    BY_NAME.setdefault(_c["name"], []).append(_c["cardId"])

# pokemonType uses the same codes as energyType, and the basic energy card id
# happens to equal that code (id 3 == "Basic {W} Energy", energyType 3).
TYPE_LETTER = {1: "G", 2: "R", 3: "W", 4: "L", 5: "P", 6: "F", 7: "D", 8: "M"}

with open(os.path.join(DATA, "attacks.json")) as fh:
    ATTACKS = json.load(fh)
ATTACKS = {a["attackId"]: a for a in (ATTACKS if isinstance(ATTACKS, list) else [])}


def skill_text(card_id: int) -> str:
    return " ".join(s.get("text", "") for s in CARDS[card_id].get("skills", [])).lower()


def find_supporter(keyword: str, limit: int = 3) -> list[int]:
    """Supporter ids whose text contains `keyword` (case-insensitive)."""
    out = []
    kw = keyword.lower()
    for c in _CARDS:
        if c["cardType"] == 3 and kw in skill_text(c["cardId"]):
            out.append(c["cardId"])
    return out[:limit]


# ---------------------------------------------------------------------------
# generic staples
# ---------------------------------------------------------------------------
#
# Chosen from what the (restricted) 1431-card pool actually offers.  Notably
# absent: Nest Ball, Professor's Research, Iono.  Present and good: Hilda
# (search an Evolution + an Energy), Boss's Orders, Buddy-Buddy Poffin.

ULTRA_BALL = 1121
BUDDY_BUDDY_POFFIN = 1086
RARE_CANDY = 1079
SWITCH = 1123
NIGHT_STRETCHER = 1097
ENERGY_RETRIEVAL = 1118
ENERGY_RECYCLER = 1139
BOSS_ORDERS = 1182
HILDA = 1225

# resolved lazily: the pool's draw supporters
_DRAW = find_supporter("draw 3 cards") or find_supporter("draw")[:2]

MASTER_BALL = 1125        # search any Pokemon, no discard cost
ENERGY_SEARCH = 1119
HYPER_AROMA = 1082        # search up to 3 Stage 1
SACRED_ASH = 1129         # shuffle 5 Pokemon back from the discard
MAX_ROD = 1110            # recover Pokemon + basic energy
POKE_PAD = 1152           # search a Pokemon without a Rule Box
PRECIOUS_TROLLEY = 1126   # any number of Basic Pokemon onto the Bench
BOXED_ORDER = 1084
MIRACLE_HEADSET = 1109    # recover 2 Supporters
POKE_VITAL_A = 1096       # heal 150
PRIME_CATCHER = 1088      # gust + switch
HEROS_CAPE = 1159         # +100 HP
RESCUE_BOARD = 1157
AIR_BALLOON = 1174        # -2 retreat
SACRED_CHARM = 1177
LUCKY_HELMET = 1156
LIVELY_STADIUM = 1251     # +30 HP to basics
GRAND_TREE = 1249         # search a Stage 1 each turn

# Filled in priority order after the Pokemon and the energy are placed.  The
# list is deliberately longer than the gap it has to fill, so the energy count
# we ask for is the energy count we get instead of the padding absorbing the
# slack and quietly turning every deck into a 25-energy pile.
STAPLE_PRIORITY = (
    [HILDA] * 4
    + [MASTER_BALL] * 4
    + [ULTRA_BALL] * 4
    + [BUDDY_BUDDY_POFFIN] * 3
    + list(_DRAW[:3]) * 3
    + [NIGHT_STRETCHER] * 3
    + [HYPER_AROMA] * 2
    + [PRECIOUS_TROLLEY] * 2
    + [POKE_PAD] * 2
    + [ENERGY_SEARCH] * 2
    + [ENERGY_RETRIEVAL] * 2
    + [ENERGY_RECYCLER] * 2
    + [SACRED_ASH] * 2
    + [MAX_ROD] * 2
    + [BOSS_ORDERS] * 3
    + [PRIME_CATCHER] * 2
    + [SWITCH] * 2
    + [HEROS_CAPE] * 2
    + [RESCUE_BOARD] * 2
    + [AIR_BALLOON] * 2
    + [LIVELY_STADIUM] * 2
    + [GRAND_TREE] * 2
    + [POKE_VITAL_A] * 2
    + [MIRACLE_HEADSET] * 2
    + [BOXED_ORDER] * 2
    + [SACRED_CHARM] * 2
    + [LUCKY_HELMET] * 2
)


# Several strong searchers in this pool are ACE SPEC (Master Ball, Hyper Aroma,
# Precious Trolley, Max Rod) and the engine allows exactly one ACE SPEC per deck.
# deck_rules.py caught all four of them the first time we tried to run 4x.
# We keep a single Master Ball and drop the rest rather than let the deck fail.
ACE_SPEC_KEEP = 1125


def staples_priority(chain_len: int) -> list[int]:
    """Staples in the order we want to add them, one copy at a time."""
    base = [RARE_CANDY] * 4 + list(STAPLE_PRIORITY) if chain_len >= 3 else list(STAPLE_PRIORITY)
    out: list[int] = []
    ace_used = 0
    for cid in base:
        if CARDS[cid].get("aceSpec"):
            if cid != ACE_SPEC_KEEP or ace_used:
                continue
            ace_used += 1
        out.append(cid)
    return out


def resolve_chain(target_id: int) -> list[int]:
    """Walk `evolvesFrom` back to a Basic, returning [basic, ..., target].

    When several printings share a name we prefer the one whose card id is
    closest to the target's -- the engine stores a family adjacent to itself,
    so this keeps us inside one consistent printing set.
    """
    chain = [target_id]
    cur = CARDS[target_id]
    seen = {cur["name"]}
    while cur.get("evolvesFrom"):
        pre_name = cur["evolvesFrom"]
        if pre_name in seen:
            break
        seen.add(pre_name)
        cands = BY_NAME.get(pre_name, [])
        if not cands:
            break
        best = min(cands, key=lambda cid: abs(cid - target_id))
        chain.insert(0, best)
        cur = CARDS[best]
    return chain


def is_basic(card_id: int) -> bool:
    return bool(CARDS[card_id].get("basic"))


def attack_energy_types(card_id: int) -> list[int]:
    """Energy types the card's attacks actually require (0 == colorless).

    `pokemonType` is NOT the energy the card needs -- our Mega Abomasnow ex has
    pokemonType 4 yet every attack costs Water (3).  Always read the costs.
    """
    weights: dict[int, int] = {}
    for aid in CARDS[card_id]["attacks"]:
        for t in ATTACKS[aid]["energies"]:
            if t:  # 0 == colorless, payable with anything
                weights[t] = weights.get(t, 0) + 1
    if not weights:
        pt = CARDS[card_id].get("pokemonType")
        return [pt] if pt else []
    # most-needed type first
    return sorted(weights, key=lambda t: (-weights[t], t))


def energy_plan(card_id: int, n_energy: int) -> list[int]:
    """Split `n_energy` basic energy cards across the types the attacks need."""
    types = attack_energy_types(card_id)
    if not types:
        raise ValueError(f"cannot infer an energy type for {CARDS[card_id]['name']}")
    weights = {t: 1 for t in types}
    # weight by how often the type appears across this card's attacks
    counts: dict[int, int] = {}
    for aid in CARDS[card_id]["attacks"]:
        for t in ATTACKS[aid]["energies"]:
            if t in weights:
                counts[t] = counts.get(t, 0) + 1
    total = sum(counts[t] for t in types) or len(types)
    out: list[int] = []
    for t in types:
        out += [t] * max(1, round(n_energy * counts.get(t, 1) / total))
    # trim/extend to exactly n_energy, keeping at least one of each type
    while len(out) > n_energy:
        for t in reversed(types):
            if len(out) <= n_energy:
                break
            while len(out) > n_energy and out.count(t) > 1:
                out.remove(t)
    while len(out) < n_energy:
        out.append(types[0])
    return out


def build(attacker: int, n_energy: int = 14, copies: tuple[int, ...] = (4, 4, 4),
          extra: tuple[int, ...] = (), energy_id: int | None = None) -> list[int]:
    """Assemble a legal 60-card deck around `attacker`.

    `copies` gives the number of copies per link of the evolution chain, from
    the basic up.  Energy is held to exactly `n_energy`; the remaining slots are
    filled with staples in priority order, which keeps the energy count honest
    instead of letting the padding absorb the slack.
    """
    chain = resolve_chain(attacker)
    if len(copies) < len(chain):
        copies = copies + (copies[-1],) * (len(chain) - len(copies))

    deck: list[int] = []
    for link, n in zip(chain, copies):
        deck += [link] * n
    deck += list(extra)

    if energy_id is not None:
        deck += [energy_id] * n_energy
    else:
        deck += energy_plan(attacker, n_energy)

    deck = _fill_staples(deck, chain_len=len(chain))

    probs = deck_problems(deck, load_library())
    if probs:
        raise ValueError(f"assembled deck is illegal: {probs}")
    return deck


def _fill_staples(deck: list[int], chain_len: int, target: int = 60) -> list[int]:
    """Top up to `target` cards with staples, respecting the 4-copy rule."""
    lib = load_library()
    deck = list(deck)
    for cid in staples_priority(chain_len):
        if len(deck) >= target:
            break
        if lib[cid].get("basicEnergy"):
            continue
        name = CARDS[cid]["name"]
        if sum(1 for d in deck if CARDS[d]["name"] == name) >= 4:
            continue
        deck.append(cid)
    # anything still missing (a priority list shorter than the gap) -> energy of
    # the type already in the deck, which is exempt from the 4-copy rule
    if len(deck) < target:
        eids = [d for d in deck if CARDS[d]["cardType"] == 5]
        filler = eids[0] if eids else 3
        deck += [filler] * (target - len(deck))
    return deck


# ---------------------------------------------------------------------------
# the archetypes
# ---------------------------------------------------------------------------
#
# (name, headline attacker, note)

MEGA_ABOMASNOW_EX = 723     # us: mill + recycle, 350 HP, stage 1
CRUSTLE_WALL = 345          # "Prevent all damage ... from your opponent's {ex}"
SYLVEON_SAFEGUARD = 330     # Safeguard: same anti-ex clause
BRONZONG_JAMMER = 55        # 30 dmg + "can't evolve" next turn
DRAGAPULT_EX = 121          # stage 2 tera, 320 HP
TREVENANT = 1311            # stage 1
ALAKAZAM = 245              # stage 2
MEGA_GARDEVOIR_EX = 747     # mega ex, 360 HP
MEGA_CHARIZARD_X_EX = 790   # mega ex, 360 HP
RAGING_BOLT_EX = 63         # basic ex, 240 HP
PIKACHU_EX_TERA = 210       # basic tera ex, 200 HP


def our_deck() -> list[int]:
    """The deck we actually ship, read from deck.csv."""
    with open(os.path.join(ROOT, "deck.csv")) as fh:
        return [int(x) for x in fh.read().replace(",", " ").split() if x.strip()]


ARCHETYPES: dict[str, dict] = {
    "ours": {
        "deck": our_deck,
        "note": "baseline - the sample Mega Abomasnow ex mill/recycle list",
    },
    "dragapult": {
        "deck": lambda: build(DRAGAPULT_EX, n_energy=12),
        "note": "stage-2 tera 320 HP, the summer meta's headline attacker",
    },
    "crustle_wall": {
        "deck": lambda: build(CRUSTLE_WALL, n_energy=12),
        "note": "anti-ex wall - does our mega ex even register as 'ex'?",
    },
    "sylveon_safeguard": {
        "deck": lambda: build(SYLVEON_SAFEGUARD, n_energy=12),
        "note": "second anti-ex wall (Safeguard), independent printing",
    },
    "bronzong_lock": {
        "deck": lambda: build(BRONZONG_JAMMER, n_energy=12),
        "note": "evolution jammer - we are a stage-1 evolution deck",
    },
    "trevenant": {
        "deck": lambda: build(TREVENANT, n_energy=12),
        "note": "stage-1 attacker, item/ability pressure",
    },
    "alakazam": {
        "deck": lambda: build(ALAKAZAM, n_energy=12),
        "note": "stage-2, damage-moving archetype",
    },
    "gardevoir_mega": {
        "deck": lambda: build(MEGA_GARDEVOIR_EX, n_energy=14),
        "note": "mega ex 360 HP - same card class as ours",
    },
    "charizard_mega": {
        "deck": lambda: build(MEGA_CHARIZARD_X_EX, n_energy=14),
        "note": "mega ex 360 HP, fire",
    },
    "raging_bolt": {
        "deck": lambda: build(RAGING_BOLT_EX, n_energy=16, copies=(4,)),
        "note": "basic ex 240 HP, no evolution needed - pure tempo",
    },
    "pikachu_tera": {
        "deck": lambda: build(PIKACHU_EX_TERA, n_energy=12, copies=(4,)),
        "note": "basic tera ex 200 HP",
    },
}


def decks() -> dict[str, list[int]]:
    return {name: spec["deck"]() for name, spec in ARCHETYPES.items()}


def main() -> int:
    lib = load_library()
    print(f"draw supporters chosen: {[CARDS[i]['name'] for i in _DRAW]}")
    print(f"{'archetype':<20} {'n':>3}  {'energy':<22} legal  note")
    print("-" * 110)
    bad = 0
    for name, spec in ARCHETYPES.items():
        try:
            d = spec["deck"]()
        except Exception as exc:  # noqa: BLE001
            print(f"{name:<20} {'-':>3}  ERROR: {exc}")
            bad += 1
            continue
        probs = deck_problems(d, lib)
        atk = _headline(d)
        ec: dict[int, int] = {}
        for c in d:
            if CARDS[c]["cardType"] == 5:
                ec[c] = ec.get(c, 0) + 1
        energy = " ".join(f"{TYPE_LETTER.get(k, str(k))}{v}" for k, v in sorted(ec.items()))
        ok = "yes" if not probs else "NO"
        if probs:
            bad += 1
        print(f"{name:<20} {len(d):>3}  {energy:<22} {ok:<5}  {spec['note']}")
        if probs:
            for p in probs:
                print(f"      - {p}")
    print("-" * 110)
    print(f"{len(ARCHETYPES)} archetypes, {bad} problem(s)")
    return 1 if bad else 0


def _headline(deck: list[int]) -> int:
    """The Pokemon in the deck with the highest HP (our designated attacker)."""
    best, best_hp = deck[0], -1
    for cid in deck:
        c = CARDS[cid]
        if c["cardType"] == 0 and c["hp"] > best_hp:
            best, best_hp = cid, c["hp"]
    return best


if __name__ == "__main__":
    raise SystemExit(main())
