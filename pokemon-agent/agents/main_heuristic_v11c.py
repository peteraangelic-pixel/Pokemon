# Gen5 best 0.8 (mutated around Gen4 0.782, strength 0.03)
"""Phase 1 rule-based agent for "The Pokemon Company - PTCG AI Battle Challenge".

Design goals
------------
1. **Never fail.**  Every decision is wrapped so that an unexpected observation
   can never raise out of ``agent()``.  A raise means the Kaggle submission is
   marked ``Error`` and burns one of the 5 daily slots.
2. **Legality first.**  We only ever return indices into
   ``obs["select"]["option"]``, never more than ``maxCount`` of them, never
   fewer than ``minCount`` (when the option list allows it).
3. **Explainable.**  Each candidate move gets an explicit score from a small
   set of PTCG concepts (damage, prizes, knock-out, board development, tempo).
   That makes the agent debuggable from logs and gives us something to write
   about later.

Move ordering (the single most important idea)
---------------------------------------------
The engine lets us act in *any* order within a turn, and **attacking ends the
turn**.  Therefore a per-option score is only correct if every "setup" action
scores strictly higher than every attack.  We use these bands::

    340  play a Supporter (draw / search)
    330  play an Item (search / utility)
    320  put a Basic Pokemon on the Bench
    310  evolve
    300  attach Energy / Tool
    290  play a Stadium
    270  use an Ability
    260  attack that takes a prize
    200  any other attack
    120  retreat (only when it is clearly right)
     20  discard / junk
      0  end turn

Everything is relative, so the exact numbers matter far less than the bands.

Observation contract (verified against the shipped cabt engine)
--------------------------------------------------------------
``obs["select"] is None`` -> return the 60 card ids of our deck.
Otherwise ``obs["select"]`` has ``type`` (SelectType), ``context``
(SelectContext), ``minCount``, ``maxCount`` and ``option`` (list of dicts with
``type`` == OptionType and type-specific fields).
"""
from __future__ import annotations

import json
import os
import random  # noqa: F401  (kept for future stochastic tie-breaking)
import re

# --------------------------------------------------------------------------
# Enums (mirrored from the cabt engine documentation / observed payloads)
# --------------------------------------------------------------------------


class SelectType:
    MAIN = 0
    CARD = 1
    ATTACHED_CARD = 2
    CARD_OR_ATTACHED_CARD = 3
    ENERGY = 4
    SKILL = 5
    ATTACK = 6
    EVOLVE = 7
    COUNT = 8
    YES_NO = 9
    SPECIAL_CONDITION = 10


class OptionType:
    NUMBER = 0
    YES = 1
    NO = 2
    CARD = 3
    TOOL_CARD = 4
    ENERGY_CARD = 5
    ENERGY = 6
    PLAY = 7
    ATTACH = 8
    EVOLVE = 9
    ABILITY = 10
    DISCARD = 11
    RETREAT = 12
    ATTACK = 13
    END = 14
    SKILL = 15


class Area:
    DECK = 1
    HAND = 2
    DISCARD = 3
    ACTIVE = 4
    BENCH = 5
    PRIZE = 6
    STADIUM = 7
    ENERGY = 8
    TOOL = 9
    PRE_EVOLUTION = 10
    PLAYER = 11
    LOOKING = 12


class CardType:
    POKEMON = 0
    ITEM = 1
    TOOL = 2
    SUPPORTER = 3
    STADIUM = 4
    BASIC_ENERGY = 5
    SPECIAL_ENERGY = 6


class Energy:
    COLORLESS = 0
    GRASS = 1
    FIRE = 2
    WATER = 3
    LIGHTNING = 4
    PSYCHIC = 5
    FIGHTING = 6
    DARKNESS = 7
    METAL = 8
    DRAGON = 9
    RAINBOW = 10
    TEAM_ROCKET = 11


class Cond:
    POISON = 0
    BURN = 1
    SLEEP = 2
    PARALYZE = 3
    CONFUSE = 4


class Ctx:
    MAIN = 0
    SETUP_ACTIVE_POKEMON = 1
    SETUP_BENCH_POKEMON = 2
    SWITCH = 3
    TO_ACTIVE = 4
    TO_BENCH = 5
    TO_FIELD = 6
    TO_HAND = 7
    DISCARD = 8
    TO_DECK = 9
    TO_DECK_BOTTOM = 10
    TO_PRIZE = 11
    NOT_MOVE = 12
    DAMAGE_COUNTER = 13
    DAMAGE_COUNTER_ANY = 14
    DAMAGE = 15
    REMOVE_DAMAGE_COUNTER = 16
    HEAL = 17
    EVOLVES_FROM = 18
    EVOLVES_TO = 19
    DEVOLVE = 20
    ATTACH_FROM = 21
    ATTACH_TO = 22
    DETACH_FROM = 23
    LOOK = 24
    EFFECT_TARGET = 25
    DISCARD_ENERGY_CARD = 26
    DISCARD_TOOL_CARD = 27
    SWITCH_ENERGY_CARD = 28
    DISCARD_CARD_OR_ATTACHED_CARD = 29
    DISCARD_ENERGY = 30
    TO_HAND_ENERGY = 31
    TO_DECK_ENERGY = 32
    SWITCH_ENERGY = 33
    SKILL_ORDER = 34
    ATTACK = 35
    DISABLE_ATTACK = 36
    EVOLVE = 37
    DRAW_COUNT = 38
    DAMAGE_COUNTER_COUNT = 39
    REMOVE_DAMAGE_COUNTER_COUNT = 40
    IS_FIRST = 41
    MULLIGAN = 42
    ACTIVATE = 43
    FIRST_EFFECT = 44
    MORE_DEVOLVE = 45
    COIN_HEAD = 46
    AFFECT_SPECIAL_CONDITION = 47
    RECOVER_SPECIAL_CONDITION = 48


# --------------------------------------------------------------------------
# Configuration knobs (tuned by local ladder experiments, see SUBMISSION_LOG)
# --------------------------------------------------------------------------

#: Do we choose to go first when the engine asks (SelectContext.IS_FIRST)?
os.environ.setdefault("PTCG_SUPPORTER", "346")
os.environ.setdefault("PTCG_ITEM", "325")
os.environ.setdefault("PTCG_BENCH", "304")
os.environ.setdefault("PTCG_EVOLVE", "292")
os.environ.setdefault("PTCG_ATTACH", "287")
os.environ.setdefault("PTCG_STADIUM", "270")
os.environ.setdefault("PTCG_ABILITY", "259")
os.environ.setdefault("PTCG_ATTACK_KO", "273")
os.environ.setdefault("PTCG_ATTACK", "195")
os.environ.setdefault("PTCG_RETREAT_BASE", "122")
os.environ.setdefault("PTCG_RETREAT_NO_ATK", "219")
os.environ.setdefault("PTCG_RETREAT_KO", "277")
os.environ.setdefault("PTCG_RETREAT_WALL", "344")
os.environ.setdefault("PTCG_GUST_BONUS", "59")
os.environ.setdefault("PTCG_WALL_PENALTY", "-650")
os.environ.setdefault("PTCG_WALL_ESCAPE", "211")
os.environ.setdefault("PTCG_ATTACH_WALL_BONUS", "30")
os.environ.setdefault("PTCG_ATTACH_WALL_PENALTY", "-35")
os.environ.setdefault("PTCG_BEACH_WALL", "335")
os.environ.setdefault("PTCG_FIGHTER_READY", "22")
os.environ.setdefault("PTCG_FIGHTER_NOT_READY", "-63")
os.environ.setdefault("PTCG_PRIZE_PENALTY", "16")
os.environ.setdefault("PTCG_ENABLE_BONUS", "14")
os.environ.setdefault("PTCG_PROGRESS_BONUS", "32")
os.environ.setdefault("PTCG_ACTIVE_BONUS", "6")
os.environ.setdefault("PTCG_PRIMARY_BONUS", "7")

GO_FIRST = os.environ.get("PTCG_GO_FIRST", "1") not in ("0", "false", "False", "")

#: Score variable-damage attacks
VAR_DAMAGE = os.environ.get("PTCG_VAR_DMG", "1") not in ("0", "false", "False", "")

# Wall handling
WALL_SWITCH = os.environ.get("PTCG_WALL", "1") not in ("0", "false", "False", "")

# --- Tunable scoring bands (for evolutionary search, 40 parallel versions) ---
def _env_int(name, default):
    try:
        return int(os.environ.get(name, str(default)))
    except:
        return default

SUPPORTER_SCORE = _env_int("PTCG_SUPPORTER", 340)
ITEM_SCORE = _env_int("PTCG_ITEM", 330)
BENCH_SCORE = _env_int("PTCG_BENCH", 320)
EVOLVE_SCORE = _env_int("PTCG_EVOLVE", 310)
ATTACH_SCORE = _env_int("PTCG_ATTACH", 300)
STADIUM_SCORE = _env_int("PTCG_STADIUM", 290)
ABILITY_SCORE = _env_int("PTCG_ABILITY", 270)
ATTACK_KO_SCORE = _env_int("PTCG_ATTACK_KO", 260)
ATTACK_SCORE = _env_int("PTCG_ATTACK", 200)
RETREAT_BASE = _env_int("PTCG_RETREAT_BASE", 120)
RETREAT_NO_ATK = _env_int("PTCG_RETREAT_NO_ATK", 205)
RETREAT_KO = _env_int("PTCG_RETREAT_KO", 285)
RETREAT_WALL = _env_int("PTCG_RETREAT_WALL", 340)
GUST_BONUS = _env_int("PTCG_GUST_BONUS", 60)
WALL_PENALTY = _env_int("PTCG_WALL_PENALTY", -500)
WALL_ESCAPE_BONUS = _env_int("PTCG_WALL_ESCAPE", 200)
ATTACH_WALL_BONUS = _env_int("PTCG_ATTACH_WALL_BONUS", 40)
ATTACH_WALL_PENALTY = _env_int("PTCG_ATTACH_WALL_PENALTY", -20)
BEACH_WALL_SCORE = _env_int("PTCG_BEACH_WALL", 345)
FIGHTER_READY_BONUS = _env_int("PTCG_FIGHTER_READY", 60)
FIGHTER_NOT_READY = _env_int("PTCG_FIGHTER_NOT_READY", -40)
PRIZE_PENALTY = _env_int("PTCG_PRIZE_PENALTY", 25)
ENABLE_BONUS = _env_int("PTCG_ENABLE_BONUS", 30)
PROGRESS_BONUS = _env_int("PTCG_PROGRESS_BONUS", 18)
ACTIVE_BONUS = _env_int("PTCG_ACTIVE_BONUS", 12)
PRIMARY_BONUS = _env_int("PTCG_PRIMARY_BONUS", 10)


#: Special-condition preference when we inflict one (higher == better).
_COND_ATTACK_ORDER = {
    Cond.PARALYZE: 50,
    Cond.SLEEP: 45,
    Cond.CONFUSE: 35,
    Cond.BURN: 25,
    Cond.POISON: 20,
}
#: When *we* suffer one, this is how much we want to get rid of it.
_COND_RECOVER_ORDER = {
    Cond.PARALYZE: 50,
    Cond.SLEEP: 45,
    Cond.CONFUSE: 35,
    Cond.BURN: 25,
    Cond.POISON: 20,
}

# --------------------------------------------------------------------------
# Deck
# --------------------------------------------------------------------------

_FALLBACK_DECK = (
    [721, 721, 722, 722, 722, 722, 723, 723, 723, 723]
    + [1092]
    + [1121, 1121, 1145, 1145, 1163, 1163]
    + [1219, 1219, 1219, 1219]
    + [1227, 1227, 1227, 1227]
    + [1262, 1262]
    + [3] * 33
)


try:
    _HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    # Kaggle does not import our file -- it exec()s its source:
    #   kaggle_environments/agent.py -> get_last_callable -> exec(code_object, env)
    # In that namespace __file__ simply does not exist.  Both of our first two
    # uploads died at import on `NameError: name '__file__' is not defined`,
    # which costs a submission slot and surfaces only as a bare Error status.
    # Everything we ship is unpacked flat into /kaggle_simulations/agent, so we
    # do not need __file__ there at all.
    _HERE = ""


def _candidate_dirs() -> list[str]:
    """Where to look for deck.csv / card_index.json.

    The Kaggle paths come first because they are the only ones guaranteed to
    exist in the grading environment, and they do not depend on __file__.
    """
    dirs = [
        "/kaggle_simulations/agent",
        "/kaggle_simulations/agent/assets",
        os.getcwd(),
    ]
    if _HERE:
        parent = os.path.dirname(_HERE)
        dirs += [_HERE, os.path.join(_HERE, "assets"),
                 parent, os.path.join(parent, "assets")]
    return [d for d in dirs if d]


def _load_deck() -> list[int]:
    for d in _candidate_dirs():
        try:
            with open(os.path.join(d, "deck.csv"), encoding="utf-8") as fh:
                ids: list[int] = []
                for line in fh:
                    for tok in line.replace(",", " ").split():
                        if tok.strip():
                            ids.append(int(tok))
                if len(ids) == 60:
                    return ids
        except Exception:
            continue
    return list(_FALLBACK_DECK)


try:
    DECK = _load_deck()
except Exception:
    DECK = list(_FALLBACK_DECK)


# --------------------------------------------------------------------------
# Card database
# --------------------------------------------------------------------------


def _load_card_index() -> dict:
    for d in _candidate_dirs():
        try:
            with open(os.path.join(d, "card_index.json"), encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            continue
    return {"cards": {}, "attacks": {}, "by_name": {}}


try:
    _INDEX = _load_card_index()
except Exception:
    _INDEX = {"cards": {}, "attacks": {}, "by_name": {}}
CARDS: dict = _INDEX.get("cards") or {}
ATTACKS: dict = _INDEX.get("attacks") or {}
BY_NAME: dict = _INDEX.get("by_name") or {}


def card(cid) -> dict:
    """Card metadata, or an empty dict when the id is unknown."""
    if cid is None:
        return {}
    return CARDS.get(str(cid)) or {}


def cname(cid) -> str:
    return card(cid).get("n", "?")


def ctype(cid):
    return card(cid).get("ct")


def is_pokemon(cid) -> bool:
    return ctype(cid) == CardType.POKEMON


def is_basic_pokemon(cid) -> bool:
    c = card(cid)
    return c.get("ct") == CardType.POKEMON and bool(c.get("b"))


def attack_data(aid) -> dict:
    return ATTACKS.get(str(aid)) or {}


def prize_value(cid) -> int:
    """How many prize cards the opponent takes for knocking this out."""
    c = card(cid)
    if c.get("mex"):
        return 3
    if c.get("ex"):
        return 2
    return 1


# --------------------------------------------------------------------------
# Deck plan: which Pokemon line are we actually trying to build?
# --------------------------------------------------------------------------


def _build_plan(deck: list[int]) -> dict:
    """Infer, from our own 60 cards, what the deck is trying to do.

    The deck is fixed and known, so we can precompute the "win condition":
    the highest-value evolved Pokemon in the list, plus its pre-evolution
    chain.  The heuristic then prefers to develop that line.
    """
    counts: dict[int, int] = {}
    for cid in deck:
        counts[cid] = counts.get(cid, 0) + 1

    pokemon = [cid for cid in counts if is_pokemon(cid)]

    def power(cid: int) -> int:
        c = card(cid)
        return (
            int(c.get("hp") or 0)
            + 200 * int(c.get("mex") or 0)
            + 120 * int(c.get("ex") or 0)
            + 30 * int(c.get("s2") or 0)
            + 15 * int(c.get("s1") or 0)
        )

    primary = max(pokemon, key=power) if pokemon else None

    # Walk the pre-evolution chain by card-name matching.
    line: set[int] = set()
    if primary is not None:
        line.add(primary)
        cur = card(primary)
        for _ in range(4):
            ef = cur.get("ef")
            if not ef:
                break
            prev_ids = BY_NAME.get(ef) or []
            if not prev_ids:
                break
            nxt = prev_ids[0]
            line.add(nxt)
            cur = card(nxt)

    return {
        "counts": counts,
        "pokemon": pokemon,
        "primary": primary,
        "line": line,
    }


PLAN = _build_plan(DECK)

_PRIMARY_ATK_POWER = 0
if PLAN.get("primary") is not None:
    for _aid in card(PLAN["primary"]).get("atk") or []:
        _PRIMARY_ATK_POWER = max(_PRIMARY_ATK_POWER, int(attack_data(_aid).get("d") or 0))


def is_primary_line(cid) -> bool:
    return cid in PLAN["line"]


def plan_power(cid) -> int:
    """How much do we care about this Pokemon (for search / discard / setup)."""
    if cid is None:
        return 0
    c = card(cid)
    if c.get("ct") != CardType.POKEMON:
        return 0
    score = int(c.get("hp") or 0)
    if cid in PLAN["line"]:
        score += 150
    if cid == PLAN.get("primary"):
        score += 150
    if c.get("mex"):
        score += 60
    if c.get("ex"):
        score += 40
    return score


# --------------------------------------------------------------------------
# Board views
# --------------------------------------------------------------------------


def _sel_card_id(opt: dict, obs: dict, me_idx: int):
    """Resolve an option that refers to a card into a card id, if we can."""
    # SKILL options carry the card directly.
    if opt.get("cardId") is not None and opt.get("area") is None:
        return opt.get("cardId")
    area = opt.get("area")
    idx = opt.get("index")
    owner = opt.get("playerIndex", me_idx)
    if idx is None:
        return None

    if area == Area.HAND and owner == me_idx:
        return _hand_id(obs, me_idx, idx)
    if area == Area.DECK and owner == me_idx:
        # Searches legitimately reveal our own deck via select["deck"].
        deck = (obs.get("select") or {}).get("deck")
        if isinstance(deck, list) and 0 <= idx < len(deck):
            entry = deck[idx]
            if isinstance(entry, dict):
                return entry.get("id")
            if isinstance(entry, int):
                return entry
        return None
    return _board_card_id(obs, owner, area, idx)


def _hand_id(obs: dict, owner: int, idx: int):
    try:
        hand = obs["current"]["players"][owner].get("hand") or []
        return hand[idx].get("id")
    except Exception:
        return None


def _board_card_id(obs: dict, owner: int, area, idx: int):
    try:
        p = obs["current"]["players"][owner]
        if area == Area.ACTIVE:
            slot = (p.get("active") or [None])[idx]
        elif area == Area.BENCH:
            slot = (p.get("bench") or [None])[idx]
        elif area == Area.STADIUM:
            stadium = obs["current"].get("stadium") or []
            slot = stadium[idx] if idx < len(stadium) else None
        elif area == Area.DISCARD:
            discard = p.get("discard") or []
            slot = discard[idx] if idx < len(discard) else None
        elif area == Area.PRIZE:
            prize = p.get("prize") or []
            slot = prize[idx] if idx < len(prize) else None
        else:
            slot = None
        if isinstance(slot, dict):
            return slot.get("id")
        return None
    except Exception:
        return None


def _pokemon_at(obs: dict, owner: int, area, idx: int):
    """Return the raw Pokemon dict at a board slot (or None)."""
    try:
        p = obs["current"]["players"][owner]
        if area == Area.ACTIVE:
            lst = p.get("active") or []
        elif area == Area.BENCH:
            lst = p.get("bench") or []
        else:
            return None
        if 0 <= idx < len(lst):
            return lst[idx]
        return None
    except Exception:
        return None


def _active(obs: dict, owner: int):
    try:
        act = obs["current"]["players"][owner].get("active") or []
        return act[0] if act else None
    except Exception:
        return None


def _bench(obs: dict, owner: int) -> list:
    try:
        return [p for p in (obs["current"]["players"][owner].get("bench") or []) if p]
    except Exception:
        return []


_RE_PER_EACH = re.compile(r"does (\d+) damage for each", re.IGNORECASE)
_RE_MILL = re.compile(r"discard the top (\d+) cards? of your deck", re.IGNORECASE)
_RE_DECK_COUNT = re.compile(r"(\d+) cards? from your deck", re.IGNORECASE)


def _energy_id_of(cid):
    """Basic/special Energy cards report the energy type they provide."""
    return card(cid).get("en")


def _deck_energy_remaining(obs: dict, me_idx: int, energy_type) -> float:
    """Estimate how many cards of a given energy type are left in our deck.

    The deck list is known and every card we can see (hand, discard, attached,
    prizes we took) is observable, so this is a good approximation rather than a
    guess -- and it is what makes "mill" attacks scoreable.
    """
    try:
        total_in_deck = sum(1 for cid in DECK if _energy_id_of(cid) == energy_type)
    except Exception:
        return 0.0
    seen = 0
    try:
        p = obs["current"]["players"][me_idx]
        for h in p.get("hand") or []:
            if _energy_id_of(h.get("id")) == energy_type:
                seen += 1
        for d in p.get("discard") or []:
            if isinstance(d, dict) and _energy_id_of(d.get("id")) == energy_type:
                seen += 1
        for slot in (p.get("active") or []) + (p.get("bench") or []):
            if not slot:
                continue
            for e in slot.get("energyCards") or []:
                if _energy_id_of(e.get("id")) == energy_type:
                    seen += 1
    except Exception:
        pass
    return max(0.0, float(total_in_deck - seen))


def _deck_energy_rate(obs: dict, me_idx: int, energy_type) -> float:
    """P(card drawn from deck is this energy type) -- uniform-deck assumption."""
    try:
        remaining = float(obs["current"]["players"][me_idx].get("deckCount") or 0)
        if remaining <= 1:
            return 0.0
        return min(1.0, _deck_energy_remaining(obs, me_idx, energy_type) / remaining)
    except Exception:
        return 0.0


def _count_for_each(subject: str, obs: dict, me_idx: int, opp_idx: int) -> float:
    """Approximate the multiplier of a "does N damage for each <subject>" clause."""
    s = subject.lower()
    try:
        me = obs["current"]["players"][me_idx]
        opp = obs["current"]["players"][opp_idx]
    except Exception:
        return 0.0

    # --- energy living in a discard pile ---------------------------------
    if "discard pile" in s or "discarded" in s:
        pile = []
        for p in (me, opp):
            pile += [d for d in (p.get("discard") or []) if isinstance(d, dict)]
        if "{w}" in s or "water" in s:
            return float(sum(1 for d in pile if _energy_id_of(d.get("id")) == Energy.WATER))
        if "basic" in s and "energy" in s:
            return float(sum(1 for d in pile if _energy_id_of(d.get("id")) is not None
                             and card(d.get("id")).get("ct") == CardType.BASIC_ENERGY))
        if "energy" in s:
            return float(sum(1 for d in pile if _energy_id_of(d.get("id")) is not None))
        return float(len(pile))

    # --- energy revealed from the top of our deck ("mill") ---------------
    if "in this way" in s or "discarded in this way" in s:
        return 0.0  # handled by the mill-specific branch

    # --- hand / bench / board counts -------------------------------------
    if "in your hand" in s:
        return float(len(me.get("hand") or []))
    if "in your opponent" in s and "hand" in s:
        return float(opp.get("handCount") or 0)
    if "bench" in s:
        return float(len([b for b in (me.get("bench") or []) if b]))
    if "damage counter" in s and "this" in s:
        poke = _active(obs, me_idx) or {}
        return float(max(0, (int(poke.get("maxHp") or 0) - int(poke.get("hp") or 0)) // 10))
    if "prize" in s:
        return float(len([p for p in (opp.get("prize") or []) if p is None]))
    if "stadium" in s:
        return 1.0 if (obs["current"].get("stadium") or []) else 0.0
    if "tool" in s:
        return float(sum(len(b.get("tools") or []) for b in (me.get("bench") or []) if b))
    return 0.0


def _estimate_damage_raw(aid, obs: dict, me_idx: int, opp_idx: int) -> int:
    """Best-effort damage of an attack, including variable-damage effects.

    About a quarter of the engine's attacks carry ``damage == 0`` and put the
    real number in the effect text (e.g. Mega Abomasnow ex's Hammer-lanche:
    "100 damage for each Basic {W} Energy discarded this way").  Ignoring those
    makes the agent blind to an entire deck's win condition, so we parse the
    common "does N damage for each <subject>" shape and estimate the subject
    count from the visible board.
    """
    ad = attack_data(aid)
    base = int(ad.get("d") or 0)
    if base > 0:
        return base
    if not VAR_DAMAGE:
        return 0
    text = ad.get("t") or ""
    if not text:
        return 0

    m = _RE_PER_EACH.search(text)
    if m:
        per = int(m.group(1))
        # "for each Basic {W} Energy card that you discarded in this way"
        if "in this way" in text.lower():
            mill = _RE_MILL.search(text)
            n_cards = int(mill.group(1)) if mill else 6
            low = text.lower()
            if "{w}" in low or "water" in low:
                rate = _deck_energy_rate(obs, me_idx, Energy.WATER)
            elif "basic" in low and "energy" in low:
                rate = sum(
                    _deck_energy_rate(obs, me_idx, et)
                    for et in (Energy.GRASS, Energy.FIRE, Energy.WATER,
                               Energy.LIGHTNING, Energy.PSYCHIC, Energy.FIGHTING,
                               Energy.DARKNESS, Energy.METAL)
                )
            elif "energy" in low:
                rate = sum(
                    _deck_energy_rate(obs, me_idx, et)
                    for et in (Energy.GRASS, Energy.FIRE, Energy.WATER,
                               Energy.LIGHTNING, Energy.PSYCHIC, Energy.FIGHTING,
                               Energy.DARKNESS, Energy.METAL)
                )
            else:
                # "for each card you discarded this way"
                rate = 1.0
                return int(per * n_cards)
            # A mill attack also has to leave us a deck to draw from.
            return int(per * n_cards * min(rate, 1.0))

        m2 = _RE_DECK_COUNT.search(text)
        if m2 and "deck" in text.lower() and ("discard" in text.lower()):
            return int(per)

        subject = text[m.end():m.end() + 120]
        count = _count_for_each(subject, obs, me_idx, opp_idx)
        return int(per * count)

    # Attacks that only multiply ("does 30 more damage for each...") or plain
    # effect attacks are left at zero: we would rather under-rate than invent.
    return 0


def damage_prevented(attacker_cid, defender_cid, damage: int = 0) -> bool:
    """True if the defender's ability blanks this attacker's damage entirely.

    Measured, not assumed: our Mega Abomasnow ex scored 0.195 against Crustle
    and 0.285 against Sylveon while beating nine other archetypes at 0.83+.
    A 181-step game ended with the opposing Crustle on hp=150/150 -- it had
    taken literally zero damage -- while we had milled 32 cards for nothing.

    Note the trap: the engine reports our Mega Abomasnow ex with ``ex == 0``
    and ``megaEx == 1``.  The anti-ex abilities say "Pokemon {ex}" and the
    engine applies them to us anyway, so a Mega counts as an {ex} attacker
    here.  Reading the flag alone would have missed this completely.

    The per-card ``pv`` flag is precomputed at index build time, where the full
    ability text is available -- at runtime we only ship skill *names*.
    """
    if attacker_cid is None or defender_cid is None:
        return False
    dfn = card(defender_cid)
    blocked = dfn.get("pv")
    if not blocked:
        return False
    # bench-only protection is irrelevant when we are hitting the Active
    if dfn.get("pvs") == "bench":
        return False
    atk = card(attacker_cid)
    is_ex = bool(atk.get("ex") or atk.get("mex"))  # a Mega ex counts as {ex}
    for cls in blocked:
        if cls == "ex" and is_ex:
            return True
        if cls == "basicEx" and is_ex and atk.get("b"):
            return True
        if cls == "tera" and atk.get("tr"):
            return True
        if cls == "ability" and atk.get("sk"):
            return True
        if cls == "dmg200" and damage >= 200:
            return True
        if cls == "specialEnergy":
            return True  # conservative: we cannot see attached card classes here
        if cls == "all":
            return True
    return False


def _wall_gust_bonus(cid, obs: dict, me_idx: int, opp_idx: int) -> int:
    """Extra urgency for a gust card when our Active is walled out.

    An anti-ex wall protects only *itself*, so forcing it to the Bench and
    hitting whatever replaces it is a clean way back into the game.  Without
    this the agent treats Boss's Orders as just another Supporter and plays it
    for card draw while the wall sits there soaking up everything.
    """
    if not WALL_SWITCH:
        return 0
    if not card(cid).get("gu"):
        return 0
    try:
        my_active = _active(obs, me_idx)
        opp_active = _active(obs, opp_idx)
    except Exception:
        return 0
    if not my_active or not opp_active:
        return 0
    if damage_prevented(my_active.get("id"), opp_active.get("id"), 10 ** 6):
        return 60
    return 0


def estimate_attack_damage(aid, obs: dict, me_idx: int, opp_idx: int) -> int:
    """Damage an attack would do, after the defender's protection abilities.

    Splitting this out from the raw estimator means every call site -- attack
    scoring and opponent threat assessment alike -- sees the wall for free.
    """
    dmg = _estimate_damage_raw(aid, obs, me_idx, opp_idx)
    if dmg <= 0:
        return 0
    try:
        atk = _active(obs, me_idx)
        dfn = _active(obs, opp_idx)
    except Exception:
        return dmg
    if atk and dfn and damage_prevented(atk.get("id"), dfn.get("id"), dmg):
        return 0
    return dmg


def _mill_would_deck_us_out(aid, obs: dict, me_idx: int) -> bool:
    ad = attack_data(aid)
    m = _RE_MILL.search(ad.get("t") or "")
    if not m:
        return False
    try:
        remaining = int(obs["current"]["players"][me_idx].get("deckCount") or 0)
    except Exception:
        return False
    return remaining <= int(m.group(1)) + 1


def _best_attack_damage(poke, attacker_cid, defender_cid, obs=None, me_idx=0, opp_idx=1) -> int:
    """Rough best-case damage this Pokemon could do to a given defender.

    Used only for threat assessment -- the engine decides real numbers.  We
    model the common modern weakness rule (+X when the attacker's type matches
    the defender's weakness) as a flat +30 and resistance as -30.
    """
    if not poke:
        return 0
    best = 0
    for aid in card(attacker_cid).get("atk") or []:
        if obs is not None:
            dmg = estimate_attack_damage(aid, obs, me_idx, opp_idx)
        else:
            dmg = int(attack_data(aid).get("d") or 0)
        best = max(best, dmg)
    if best == 0:
        return 0
    atk_type = card(attacker_cid).get("pt")
    dfn = card(defender_cid)
    if atk_type is not None and dfn.get("w") is not None and atk_type == dfn.get("w"):
        best += 30
    if atk_type is not None and dfn.get("res") is not None and atk_type == dfn.get("res"):
        best -= 30
    return max(best, 0)


def _cheapest_attack_cost(poke) -> int | None:
    """Energy cost of the cheapest usable attack of this Pokemon (None if none)."""
    if not poke:
        return None
    best = None
    for aid in card(poke.get("id")).get("atk") or []:
        cost = len(attack_data(aid).get("e") or [])
        if cost > 0 and (best is None or cost < best):
            best = cost
    return best


def _energies_needed(poke, attacker_cid=None) -> int:
    """How many more energy attachments the cheapest attack still needs."""
    cost = _cheapest_attack_cost(poke)
    if cost is None:
        return 99
    have = len(poke.get("energies") or [])
    return max(0, cost - have)


def _attack_ready(poke) -> bool:
    """True when the Pokemon can already pay for at least one attack."""
    if not poke:
        return False
    have = len(poke.get("energies") or [])
    for aid in card(poke.get("id")).get("atk") or []:
        cost = len(attack_data(aid).get("e") or [])
        if 0 < cost <= have:
            return True
    return False


def _fighter_score(poke, obs=None, opp_active=None) -> int:
    """How good is this Pokemon *as the current Active*?

    Combines: can it attack right now, how hard does it hit, how much HP does it
    have before it dies, and what do we give up if it is knocked out.
    Wall-aware: a Pokemon that cannot damage the opponent's Active because of
    an anti-ex wall is heavily penalised, so retreat brings in Kyogre instead
    of another Mega.
    """
    if not poke:
        return -1000
    cid = poke.get("id")
    have = len(poke.get("energies") or [])
    best_dmg = 0
    for aid in card(cid).get("atk") or []:
        ad = attack_data(aid)
        cost = len(ad.get("e") or [])
        if cost <= have:
            best_dmg = max(best_dmg, int(ad.get("d") or 0))
    hp = int(poke.get("hp") or 0)
    score = hp + 2 * best_dmg
    if _attack_ready(poke):
        score += FIGHTER_READY_BONUS            # it can actually do something this turn
    else:
        score += FIGHTER_NOT_READY            # sitting there taking hits
    score -= PRIZE_PENALTY * prize_value(cid)  # expensive Pokemon are liabilities in front
    # --- wall awareness ---
    if WALL_SWITCH and obs is not None and opp_active is not None:
        try:
            if damage_prevented(cid, opp_active.get("id"), 10 ** 6):
                score += WALL_PENALTY   # this Pokemon is blanked by the wall
            else:
                # non-walled attacker is precious when we are walled
                my_active = _active(obs, _me_idx_from_obs(obs))
                if my_active and damage_prevented(my_active.get("id"), opp_active.get("id"), 10 ** 6):
                    score += WALL_ESCAPE_BONUS
        except Exception:
            pass
    return score

def _me_idx_from_obs(obs):
    try:
        # current player is usually me_idx; fallback to 0
        return int(obs.get("current", {}).get("playerIndex", 0))
    except Exception:
        return 0


# --------------------------------------------------------------------------
# Card value (for discards, searches, and prize choices)
# --------------------------------------------------------------------------


def card_value(cid, obs: dict, me_idx: int) -> int:
    """Higher == more precious.  Used to decide what to throw away."""
    c = card(cid)
    if not c:
        return 50
    ct = c.get("ct")
    if ct == CardType.POKEMON:
        v = plan_power(cid)
        return 60 + v // 4
    if ct == CardType.BASIC_ENERGY:
        return 12
    if ct == CardType.SPECIAL_ENERGY:
        return 38
    if ct == CardType.SUPPORTER:
        return 72
    if ct == CardType.ITEM:
        return 66
    if ct == CardType.TOOL:
        return 44
    if ct == CardType.STADIUM:
        return 40
    return 50


def _copies_in_hand(obs: dict, me_idx: int, cid) -> int:
    try:
        hand = obs["current"]["players"][me_idx].get("hand") or []
        return sum(1 for h in hand if h.get("id") == cid)
    except Exception:
        return 1


def _discard_rank(cid, obs: dict, me_idx: int) -> int:
    """Lower == better to discard."""
    val = card_value(cid, obs, me_idx)
    val -= 6 * max(0, _copies_in_hand(obs, me_idx, cid) - 1)
    return val


# --------------------------------------------------------------------------
# MAIN decision scoring
# --------------------------------------------------------------------------


def _score_main_option(opt: dict, obs: dict, me_idx: int, opp_idx: int) -> int:
    otype = opt.get("type")
    cur = obs["current"]
    my_active = _active(obs, me_idx)
    opp_active = _active(obs, opp_idx)
    my_bench = _bench(obs, me_idx)

    if otype == OptionType.END:
        return 0

    if otype == OptionType.ATTACK:
        aid = opt.get("attackId")
        if my_active is None or opp_active is None:
            return 200 if aid else 150

        est = estimate_attack_damage(aid, obs, me_idx, opp_idx)
        atk_type = card(my_active.get("id")).get("pt")
        dfn = card(opp_active.get("id"))
        if atk_type is not None and dfn.get("w") is not None and atk_type == dfn.get("w"):
            est += 30
        if atk_type is not None and dfn.get("res") is not None and atk_type == dfn.get("res"):
            est -= 30
        est = max(est, 0)

        # Never mill ourselves to death: if this attack eats more cards than we
        # have left, it hands the opponent the game.
        if _mill_would_deck_us_out(aid, obs, me_idx):
            return 5

        opp_hp = int(opp_active.get("hp") or 0)
        ko = est > 0 and est >= opp_hp
        score = ATTACK_KO_SCORE if ko else ATTACK_SCORE
        score += min(est, 240) // 4
        if ko:
            score += 25 * prize_value(opp_active.get("id"))
            # H2 lethal: when 1 prize left, extra boost
            try:
                rem = _remaining_prizes(obs, me_idx)
                if rem == 1:
                    score += 50
            except Exception:
                pass
        if est == 0:
            # A pure-effect attack (heal, recycle, disruption) still has value,
            # but we should not skip real development for it.
            score -= 40
            text = (attack_data(aid).get("t") or "").lower()
            if "shuffle those cards into your deck" in text or "into your deck" in text:
                score += 45  # recycling fuel is how a mill deck keeps going
        return score

    if otype == OptionType.RETREAT:
        score = RETREAT_BASE
        if my_active is None:
            return score
        opp_power = _best_attack_damage(opp_active, (opp_active or {}).get("id"), my_active.get("id"), obs, opp_idx, me_idx)
        my_hp = int(my_active.get("hp") or 0)
        can_attack = _can_my_active_attack(obs, me_idx)
        backup_ok = any(
            plan_power(p.get("id")) >= plan_power(my_active.get("id")) - 40 for p in my_bench
        )
        if not can_attack and my_bench:
            score = RETREAT_NO_ATK  # get a live attacker in front instead of idling
        if opp_power >= my_hp and my_bench and backup_ok and my_hp <= 80:
            score = RETREAT_KO  # escape a knockout, then develop

        if WALL_SWITCH and opp_active is not None and my_bench:
            # Our Active is walled: every attack it has is blanked by the
            # defender's ability.  Attacking anyway is worse than doing nothing
            # -- a mill attack would chew through our own deck for zero damage.
            # If anyone on the bench can actually hit, go get them.  Score 340
            # puts retreat above Supporter (340) so we escape before drawing.
            if damage_prevented(my_active.get("id"), opp_active.get("id"), 10 ** 6):
                for p in my_bench:
                    if not damage_prevented(p.get("id"), opp_active.get("id"), 10 ** 6):
                        score = max(score, RETREAT_WALL)
                        break
        return score

    if otype == OptionType.EVOLVE:
        src = _hand_id(obs, me_idx, opt.get("index"))
        score = EVOLVE_SCORE
        if is_primary_line(src):
            score += 25
        if opt.get("inPlayArea") == Area.ACTIVE:
            score += 15
        return score

    if otype == OptionType.ATTACH:
        src = _hand_id(obs, me_idx, opt.get("index"))
        c = card(src)
        target_area = opt.get("inPlayArea")
        target_idx = opt.get("inPlayIndex", 0)
        target = _pokemon_at(obs, me_idx, target_area, target_idx)
        score = ATTACH_SCORE
        if c.get("ct") == CardType.TOOL:
            score = ATTACH_SCORE - 12
            if target_area == Area.ACTIVE:
                score += 8
            # H1: Powerglass (1163) recycles Water when Active Kyogre
            try:
                if src == 1163 and target_area == Area.ACTIVE:
                    tid = target.get("id") if target else None
                    if tid and tid in (721,722,723):
                        p = obs["current"]["players"][me_idx]
                        water_in_discard = sum(1 for d in (p.get("discard") or []) if isinstance(d, dict) and card(d.get("id")).get("en") == Energy.WATER)
                        if water_in_discard >= 1:
                            score += 55
            except Exception:
                pass
            return score
        # Energy attachment: only one per turn, so make it count.  The single
        # most valuable thing an attachment can do is *turn on* an attack.
        if target is not None:
            cost = _cheapest_attack_cost(target)
            have = len(target.get("energies") or [])
            if cost is None:
                score += 5
            elif have + 1 >= cost and have < cost:
                score += ENABLE_BONUS   # this attachment enables the attack
            elif have < cost:
                score += PROGRESS_BONUS   # progress toward it
            else:
                score += 4    # already online; extra energy is low value
            if target_area == Area.ACTIVE:
                score += ACTIVE_BONUS
            if is_primary_line(target.get("id")):
                score += 10
            # --- wall v2: when walled, feed the bench attacker that can hit ---
            if WALL_SWITCH and opp_active is not None and target is not None:
                try:
                    my_active = _active(obs, me_idx)
                    if my_active and damage_prevented(my_active.get("id"), opp_active.get("id"), 10 ** 6):
                        if not damage_prevented(target.get("id"), opp_active.get("id"), 10 ** 6):
                            score += ATTACH_WALL_BONUS  # this energy builds our escape plan
                        else:
                            score += ATTACH_WALL_PENALTY  # don't feed another walled attacker
                except Exception:
                    pass
        return score

    if otype == OptionType.ABILITY:
        return ABILITY_SCORE

    if otype == OptionType.PLAY:
        cid = _hand_id(obs, me_idx, opt.get("index"))
        if cid is None:
            return 40
        c = card(cid)
        ct = c.get("ct")
        if ct == CardType.POKEMON:
            if len(my_bench) >= 5:
                return 30
            if not my_bench and (my_active is None or int(my_active.get("hp") or 0) <= 80):
                return 335  # we are about to lose to a KO with an empty bench
            score = 320
            if is_primary_line(cid):
                score += 10
            # v11c tape opening (Kaggriculture B21) + H1 base
            try:
                if cid == 722:  # Snover
                    p = obs["current"]["players"][me_idx]
                    deck_cnt = int(p.get("deckCount") or 0)
                    if deck_cnt > 50 and len(my_bench) <= 1:
                        hand = p.get("hand") or []
                        has_water = any(card(h.get("id")).get("en") == Energy.WATER for h in hand if isinstance(h, dict))
                        if has_water:
                            score += 40
            except Exception:
                pass
            return score
        if ct == CardType.SUPPORTER:
            if cur.get("supporterPlayed"):
                return 25
            return SUPPORTER_SCORE + _wall_gust_bonus(cid, obs, me_idx, opp_idx)
        if ct == CardType.ITEM:
            return ITEM_SCORE + _wall_gust_bonus(cid, obs, me_idx, opp_idx)
        if ct == CardType.STADIUM:
            if cur.get("stadiumPlayed"):
                return 25
            stadium = cur.get("stadium") or []
            if stadium:
                return 150  # replacing a stadium is usually low value for us
            return 290
        if ct in (CardType.BASIC_ENERGY, CardType.SPECIAL_ENERGY):
            return 40  # energy should be attached, not "played"
        return 200

    if otype == OptionType.DISCARD:
        return 20

    return 60


def _can_my_active_attack(obs: dict, me_idx: int) -> bool:
    """True if the engine is currently offering us any attack."""
    opts = (obs.get("select") or {}).get("option") or []
    for o in opts:
        if o.get("type") == OptionType.ATTACK:
            return True
    # Also allow for the ATTACK select-type being pending.
    return False


# --------------------------------------------------------------------------
# Non-MAIN decision scoring
# --------------------------------------------------------------------------


def _score_generic_card(opt: dict, obs: dict, me_idx: int, opp_idx: int) -> int:
    """Score a CARD/ENERGY-style option by what the context is asking for."""
    ctx = (obs.get("select") or {}).get("context", Ctx.MAIN)
    cid = _sel_card_id(opt, obs, me_idx)
    owner = opt.get("playerIndex", me_idx)
    area = opt.get("area")
    poke = _pokemon_at(obs, owner, area, opt.get("index", -1))

    if ctx in (Ctx.SETUP_ACTIVE_POKEMON,):
        # Opening Active: prefer our evolution line, but a 90 HP Snover is a
        # real risk in front.  plan_power already rewards the line, so blend in
        # raw HP so a fat Basic can win when the line is thin.
        return 100 + plan_power(cid) // 2 + int(card(cid).get("hp") or 0) // 4

    if ctx in (Ctx.SETUP_BENCH_POKEMON,):
        return 100 + plan_power(cid) // 3

    if ctx in (Ctx.TO_BENCH, Ctx.TO_FIELD):
        return 100 + plan_power(cid) // 2

    if ctx in (Ctx.TO_ACTIVE, Ctx.SWITCH):
        # Bring forward whoever can actually fight right now.
        # Wall-aware: never bring a walled ex in front of a wall.
        if poke is not None:
            opp_active = _active(obs, 1 - me_idx) if me_idx in (0,1) else None
            # try both opponent indices if me_idx unknown
            if opp_active is None:
                try:
                    opp_active = _active(obs, 0) or _active(obs, 1)
                except Exception:
                    opp_active = None
            return 400 + _fighter_score(poke, obs, opp_active) // 2
        return 100 + plan_power(cid) // 2

    if ctx == Ctx.TO_HAND:
        return _score_wanted_card(cid, obs, me_idx)

    if ctx in (Ctx.DISCARD, Ctx.TO_DECK_BOTTOM, Ctx.TO_DECK, Ctx.TO_PRIZE, Ctx.DEVOLVE):
        return 1000 - _discard_rank(cid, obs, me_idx)

    if ctx in (Ctx.DISCARD_ENERGY, Ctx.DISCARD_ENERGY_CARD, Ctx.SWITCH_ENERGY_CARD):
        # Discarding our own energy: hurt the Pokemon we care about least.
        return 1000 - plan_power((poke or {}).get("id")) // 4

    if ctx == Ctx.DISCARD_TOOL_CARD:
        return 1000 - plan_power((poke or {}).get("id")) // 4

    if ctx in (Ctx.DAMAGE_COUNTER, Ctx.DAMAGE_COUNTER_ANY, Ctx.DAMAGE, Ctx.EFFECT_TARGET):
        return _score_damage_target(opt, obs, me_idx, opp_idx)

    if ctx in (Ctx.REMOVE_DAMAGE_COUNTER, Ctx.HEAL):
        return 100 + plan_power((poke or {}).get("id")) // 2

    if ctx == Ctx.EVOLVES_FROM:
        return 100 + plan_power(cid) // 2

    if ctx == Ctx.EVOLVES_TO:
        return 100 + plan_power(cid) // 2

    if ctx in (Ctx.ATTACH_FROM, Ctx.ATTACH_TO):
        return 100 + plan_power(cid) // 3

    if ctx == Ctx.LOOK:
        return _score_wanted_card(cid, obs, me_idx)

    if ctx == Ctx.NOT_MOVE:
        return 50

    return _score_wanted_card(cid, obs, me_idx)


def _score_wanted_card(cid, obs: dict, me_idx: int) -> int:
    """How much do we want this card in hand / in play right now?"""
    c = card(cid)
    if not c:
        return 50
    ct = c.get("ct")
    if ct == CardType.POKEMON:
        score = 100 + plan_power(cid) // 3
        if not _bench(obs, me_idx) and is_basic_pokemon(cid):
            score += 60  # we need a body on the bench
        return score
    if ct == CardType.SUPPORTER:
        return 95
    if ct == CardType.ITEM:
        # H1: Night Stretcher (1097) recycles Water when low on deck
        if cid == 1097:
            try:
                p = obs["current"]["players"][me_idx]
                water_in_discard = 0
                for d in p.get("discard") or []:
                    if isinstance(d, dict):
                        en = card(d.get("id")).get("en")
                        if en == Energy.WATER:
                            water_in_discard += 1
                remaining = _deck_energy_remaining(obs, me_idx, Energy.WATER)
                if water_in_discard >= 2 and remaining < 8:
                    return 130  # high priority recycle
                if water_in_discard >= 1 and remaining < 5:
                    return 120
            except Exception:
                pass
        return 90
    if ct == CardType.STADIUM:
        return 45
    if ct == CardType.TOOL:
        # H1: Powerglass wanted when active Kyogre and discard Water
        if cid == 1163:
            try:
                my_active = _active(obs, me_idx)
                if my_active and my_active.get("id") in (721,722,723):
                    p = obs["current"]["players"][me_idx]
                    water_in_discard = sum(1 for d in (p.get("discard") or []) if isinstance(d, dict) and card(d.get("id")).get("en") == Energy.WATER)
                    if water_in_discard >= 1:
                        return 85
            except Exception:
                pass
        return 55
    if ct == CardType.BASIC_ENERGY:
        return 40
    if ct == CardType.SPECIAL_ENERGY:
        return 60
    return 60


def _score_damage_target(opt: dict, obs: dict, me_idx: int, opp_idx: int) -> int:
    """Place damage on the opponent -- prefer knockouts and big threats."""
    owner = opt.get("playerIndex", me_idx)
    area = opt.get("area")
    idx = opt.get("index", -1)
    poke = _pokemon_at(obs, owner, area, idx)
    if poke is None:
        return 50
    hp = int(poke.get("hp") or 0)
    cid = poke.get("id")
    score = 0
    if owner == opp_idx:
        # Cheap prize targets first: an active that is nearly dead is great.
        score = 200 - min(hp, 200) // 2
        if area == Area.ACTIVE:
            score += 30
        score += 20 * prize_value(cid)
        if int(poke.get("hp") or 0) <= 60:
            score += 40
    else:
        # Damaging ourselves is almost never right, but heal-style effects exist.
        score = 20
    return score



def _fallback(obs: dict) -> list[int]:
    try:
        select = obs.get("select")
        if select is None:
            return list(DECK)
        opts = select.get("option") or []
        if not opts:
            return []
        k = min(int(select.get("maxCount") or 1), len(opts))
        return list(range(max(k, 1)))
    except Exception:
        return []


def _decide(obs: dict) -> list[int]:
    select = obs.get("select")
    if select is None:
        return list(DECK)

    opts = select.get("option") or []
    if not opts:
        return []

    max_count = int(select.get("maxCount") or 0)
    min_count = int(select.get("minCount") or 0)
    if max_count <= 0:
        return []

    stype = select.get("type")
    me_idx = int((obs.get("current") or {}).get("yourIndex") or 0)
    opp_idx = 1 - me_idx

    scores: list[tuple[int, int]] = []

    if stype == SelectType.MAIN:
        for i, o in enumerate(opts):
            scores.append((_score_main_option(o, obs, me_idx, opp_idx), i))

    elif stype in (
        SelectType.CARD,
        SelectType.ATTACHED_CARD,
        SelectType.CARD_OR_ATTACHED_CARD,
        SelectType.ENERGY,
        SelectType.SKILL,
        SelectType.EVOLVE,
        SelectType.SPECIAL_CONDITION,
    ):
        ctx = select.get("context", Ctx.MAIN)
        for i, o in enumerate(opts):
            scores.append((_score_generic_context(o, obs, me_idx, opp_idx, ctx), i))

    elif stype == SelectType.ATTACK:
        for i, o in enumerate(opts):
            ad = attack_data(o.get("attackId"))
            scores.append((int(ad.get("d") or 0), i))

    elif stype == SelectType.COUNT:
        ctx = select.get("context", Ctx.MAIN)
        for i, o in enumerate(opts):
            num = int(o.get("number") or 0)
            if ctx in (
                Ctx.DRAW_COUNT,
                Ctx.DAMAGE_COUNTER_COUNT,
                Ctx.REMOVE_DAMAGE_COUNTER_COUNT,
            ):
                scores.append((num, i))
            else:
                scores.append((-abs(num), i))

    elif stype == SelectType.YES_NO:
        ctx = select.get("context", Ctx.MAIN)
        for i, o in enumerate(opts):
            scores.append((_score_yes_no(o, obs, me_idx, ctx, select), i))

    else:
        for i in range(len(opts)):
            scores.append((0, i))

    # Stable sort: highest score first, ties keep engine order.
    scores.sort(key=lambda t: (-t[0], t[1]))
    k = min(max_count, len(opts))
    k = max(k, 0)
    if k == 0:
        return [] if min_count <= 0 else [scores[0][1]]
    chosen = [idx for _, idx in scores[:k]]
    return chosen


def _score_generic_context(o: dict, obs: dict, me_idx: int, opp_idx: int, ctx: int) -> int:
    if ctx in (Ctx.DISCARD_ENERGY, Ctx.TO_HAND_ENERGY, Ctx.TO_DECK_ENERGY, Ctx.SWITCH_ENERGY):
        # ENERGY options carry a "count" of attached energies; keeping the
        # Pokemon that matters most powered is the priority.
        poke = _pokemon_at(obs, o.get("playerIndex", me_idx), o.get("area"), o.get("index", -1))
        base = plan_power((poke or {}).get("id")) // 4
        if ctx in (Ctx.TO_HAND_ENERGY, Ctx.TO_DECK_ENERGY, Ctx.SWITCH_ENERGY):
            return base
        return 1000 - base
    return _score_generic_card(o, obs, me_idx, opp_idx)


def _score_yes_no(o: dict, obs: dict, me_idx: int, ctx: int, select: dict) -> int:
    otype = o.get("type")
    yes = otype == OptionType.YES

    if ctx == Ctx.IS_FIRST:
        # Option[0] is YES == "I go first".  See GO_FIRST knob.
        return (10 if yes else 0) if GO_FIRST else (0 if yes else 10)

    if ctx == Ctx.MULLIGAN:
        # Redraw only when the engine says we may AND we hold no Basic Pokemon.
        try:
            hand = obs["current"]["players"][me_idx].get("hand") or []
            has_basic = any(is_basic_pokemon(h.get("id")) for h in hand)
        except Exception:
            has_basic = False
        if has_basic:
            return 0 if yes else 10
        return 10 if yes else 0

    if ctx in (Ctx.ACTIVATE, Ctx.FIRST_EFFECT, Ctx.MORE_DEVOLVE, Ctx.COIN_HEAD):
        return 10 if yes else 0

    return 10 if yes else 0


# --------------------------------------------------------------------------
# Debug hook (enabled with PTCG_DEBUG=1; output lands in the Kaggle agent log)
# --------------------------------------------------------------------------

_DEBUG = os.environ.get("PTCG_DEBUG", "") not in ("", "0", "false", "False")

if _DEBUG:
    _orig_decide = _decide

    def _decide(obs):  # type: ignore[misc]
        import sys

        out = _orig_decide(obs)
        try:
            sel = obs.get("select") or {}
            opts = sel.get("option") or []
            print(
                f"[ptcg] turn={((obs.get('current') or {}).get('turn'))} "
                f"stype={sel.get('type')} ctx={sel.get('context')} "
                f"n_opt={len(opts)} -> {out}",
                file=sys.stderr,
            )
        except Exception:
            pass
        return out


# ---------------------------------------------------------------------------
# Kaggle entry point -- MUST stay the last callable in this file.
#
# kaggle_environments.agent.get_last_callable() ends with:
#     return [v for v in env.values() if callable(v)][-1]
# It does NOT look for a function named `agent`; it takes whatever callable was
# defined last. Our helpers used to live below this function, so Kaggle called
# _score_yes_no() as if it were the agent and every episode died with
#     TypeError: _score_yes_no() missing 3 required positional arguments
# (main_random.py happened to define `agent` last, which is why the random
# submission passed while the heuristic one failed on the very same day.)
# tools/test_kaggle_import.py asserts this ordering using get_last_callable
# itself, so moving it again will fail the build rather than the upload.
# ---------------------------------------------------------------------------
def agent(obs: dict) -> list[int]:
    try:
        return _decide(obs)
    except Exception:
        return _fallback(obs)
