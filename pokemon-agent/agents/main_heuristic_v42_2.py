# v42.2 (a450, 2026-10-14): v41 reactive + per-archetype STATE-VALUE ML modulation.
# 6 numpy MLPs (SPREAD/GRASS/FIGHTING/WALL/DEFAULT + GLOBAL fallback; MIRROR model
# rejected: below base rate) trained on 84k states from 10k self-play games
# (tools/gen_ml_data2.py, split by game). win_prob<0.4 -> develop board,
# >0.6 -> press attacks. Knob: PTCG_V422_ML=1. Weights embedded (base64 f32).
# v41 REACTIVE (2026-10-14): v39 (=v38b wallgate) + sticky archetype detector
# + per-archetype plan modules: SPREAD (Alakazam/Dragapult/Dusknoir: hand-cap,
# lean bench), ENDGAME prize-race deny, stricter WALL gate option.
# Knobs: PTCG_V41_ARCH/SPREAD/ENDGAME=1, PTCG_V41_WALLGATE=v2|strict.
# Deck pair: decks/v39_33w_kyo4_eugen.csv (8 basics) or v41_34w_kyo3.csv.
# v39 = v38b (wallgate adaptive) pilot, UNCHANGED defaults.
# Built 2026-10-14 from the v38b (57159904, live 418.9) / v36 (57160199, live 399.9)
# loss analysis: both ~44% live WR, losses spread over the whole field
# (conqueror median mu ~474), end-state forensics dominated by NO_POKEMON
# bench-outs (83-89% of losses in-engine). Pilot micro-knobs tested and
# REJECTED (BENCH0 boost, bench-target=1); the shipped fix is the deck:
# decks/v39_33w_kyo4.csv -- 8 basics instead of 6 (2 Water -> 2 Kyogre),
# paired A/B local cost -0.33pp n.s. (10 286 games), bench-out losses down.
# v29 = v28 bench400 + 8560 mirror specialist (Hammer >=280 +250, Riptide >=100 +150, no early trades) + FAST_EX Zacian/Duraludon/Zangoose
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
os.environ.setdefault("PTCG_RETREAT_WALL", "350")
os.environ.setdefault("PTCG_GUST_BONUS", "70")
os.environ.setdefault("PTCG_WALL_PENALTY", "-650")
os.environ.setdefault("PTCG_WALL_ESCAPE", "230")
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
RETREAT_WALL = _env_int("PTCG_RETREAT_WALL", 360)
GUST_BONUS = _env_int("PTCG_GUST_BONUS", 80)
WALL_PENALTY = _env_int("PTCG_WALL_PENALTY", -500)
WALL_ESCAPE_BONUS = _env_int("PTCG_WALL_ESCAPE", 260)
ATTACH_WALL_BONUS = _env_int("PTCG_ATTACH_WALL_BONUS", 45)
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

    v11: boosted from 60 to 80 + extra 30 vs known walls (330 Sylveon Safeguard, 345 Crustle)
    Inspired by Kaggriculture TOP30 delayed-sale vs high-turnover – stronger gust urgency.
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
        bonus = 80
        # Extra vs known wall IDs (330 Sylveon Safeguard, 345 Crustle Rock Inn)
        try:
            opp_id = opp_active.get("id")
            if opp_id in (330, 345, 533):  # 533 Crustle Sturdy also walls in some builds
                bonus += 30
        except Exception:
            pass
        return bonus
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
    # v22c: LOW_E_AGGRO opening fix from v12b (via c87f7a48 v21b; FIXED: v21b
    # applied the adj before `score` existed => UnboundLocalError => silent no-op)
    _aggro_adj = 0
    try:
        opp_id = (opp_active or {}).get("id")
        if opp_id in LOW_E_AGGRO_IDS_V21:
            if cid == 721:
                _aggro_adj = -150
            elif cid == 722:
                _aggro_adj = 80
    except Exception:
        _aggro_adj = 0
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
    return score + _aggro_adj

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
    """Higher == more precious.  Used to decide what to throw away.
    
    v11: H1 logic for Night Stretcher (1097) and Powerglass (1163) + cow5 vs cow8
    """
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
        # v11: Night Stretcher (1097) recycles Water when low on deck (H1)
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
        return 66
    if ct == CardType.TOOL:
        # v11: Powerglass wanted when active Kyogre and discard Water (H1 + self-repairing valve)
        if cid == 1163:
            try:
                my_active = _active(obs, me_idx)
                if my_active and my_active.get("id") in (721, 722, 723):
                    p = obs["current"]["players"][me_idx]
                    water_in_discard = sum(1 for d in (p.get("discard") or []) if isinstance(d, dict) and card(d.get("id")).get("en") == Energy.WATER)
                    if water_in_discard >= 1:
                        return 85
            except Exception:
                pass
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
            # v33b: KO 80/40 for weak
                        # v33: extra boost vs low HP weak field – 80/40 for thin 410.9
            if opp_hp <= 100:
                score += 80
            elif opp_hp <= 150:
                score += 40

            # v34: Thick walls protocol (a450 idea #2) – auto-detect active >=300HP (Hydrapple 330, Starmie 420)
            # Switch kill sequence: Riptide-ramp / Frost-cycle instead of chipping 130
            try:
                if opp_hp >= 300:
                    # If opponent is thick wall, boost Riptide ramp and Frost Barrier cycle
                    atxt = (attack_data(aid).get("t") or "").lower() if aid else ""
                    if "riptide" in atxt or "discard" in atxt:
                        # Riptide does 20 per Water in discard – with thick wall we need ramp
                        disc = obs["current"]["players"][me_idx].get("discard") or []
                        water_in_disc = sum(1 for d in disc if isinstance(d, dict) and card(d.get("id")).get("en") == 8)
                        if water_in_disc >= 3:
                            score += 60  # ramp is ready vs thick wall
                    if "frost" in atxt or "barrier" in atxt:
                        score += 40  # Frost cycle to stall thick wall
                    # Penalize chipping 130 Swirling vs 300+ HP wall (needs 3 hits, too slow)
                    if "swirling" in atxt or est == 130:
                        score -= 30
            except Exception:
                pass
            # v11 endgame (Kaggriculture: stop planting near end): when prize race tight, boost KO
            try:
                opp_prize = obs["current"]["players"][opp_idx].get("prize") or []
                taken = sum(1 for p in opp_prize if p is None)
                if taken >= 4:  # opponent has 2 or fewer prizes left, we are close to winning
                    score += 30  # endgame KO boost
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
    """Higher == more precious.  Used to decide what to throw away.
    
    v11: H1 logic for Night Stretcher (1097) and Powerglass (1163) + cow5 vs cow8
    """
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
        # v11: Night Stretcher (1097) recycles Water when low on deck (H1)
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
        return 66
    if ct == CardType.TOOL:
        # v11: Powerglass wanted when active Kyogre and discard Water (H1 + self-repairing valve)
        if cid == 1163:
            try:
                my_active = _active(obs, me_idx)
                if my_active and my_active.get("id") in (721, 722, 723):
                    p = obs["current"]["players"][me_idx]
                    water_in_discard = sum(1 for d in (p.get("discard") or []) if isinstance(d, dict) and card(d.get("id")).get("en") == Energy.WATER)
                    if water_in_discard >= 1:
                        return 85
            except Exception:
                pass
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
            # v33b: KO 80/40 for weak
                        # v33: extra boost vs low HP weak field – 80/40 for thin 410.9
            if opp_hp <= 100:
                score += 80
            elif opp_hp <= 150:
                score += 40

            # v34: Thick walls protocol (a450 idea #2) – auto-detect active >=300HP (Hydrapple 330, Starmie 420)
            # Switch kill sequence: Riptide-ramp / Frost-cycle instead of chipping 130
            try:
                if opp_hp >= 300:
                    # If opponent is thick wall, boost Riptide ramp and Frost Barrier cycle
                    atxt = (attack_data(aid).get("t") or "").lower() if aid else ""
                    if "riptide" in atxt or "discard" in atxt:
                        # Riptide does 20 per Water in discard – with thick wall we need ramp
                        disc = obs["current"]["players"][me_idx].get("discard") or []
                        water_in_disc = sum(1 for d in disc if isinstance(d, dict) and card(d.get("id")).get("en") == 8)
                        if water_in_disc >= 3:
                            score += 60  # ramp is ready vs thick wall
                    if "frost" in atxt or "barrier" in atxt:
                        score += 40  # Frost cycle to stall thick wall
                    # Penalize chipping 130 Swirling vs 300+ HP wall (needs 3 hits, too slow)
                    if "swirling" in atxt or est == 130:
                        score -= 30
            except Exception:
                pass
            # v11 endgame (Kaggriculture: stop planting near end): when prize race tight, boost KO
            try:
                opp_prize = obs["current"]["players"][opp_idx].get("prize") or []
                taken = sum(1 for p in opp_prize if p is None)
                if taken >= 4:  # opponent has 2 or fewer prizes left, we are close to winning
                    score += 30  # endgame KO boost
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
        # v26: boost evolve when we have thin board - develop faster vs fast decks
        try:
            if len(my_bench) < 3:
                score += 20
            # vs Lucario, evolve faster to Mega Aboma with Belt?
            if _V21_SEEN & LUCARIO_IDS_V21:
                score += 15
        except Exception:
            pass
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
            # v11: Powerglass (1163) self-repairing valve (Kaggriculture carrot 1.15x)
            # Only attach when active Kyogre line and discard has Water – high margin limited resource (melon 4 cells)
            try:
                if src == 1163 and target_area == Area.ACTIVE:
                    tid = target.get("id") if target else None
                    if tid and tid in (721, 722, 723):  # Kyogre line
                        p = obs["current"]["players"][me_idx]
                        water_in_discard = sum(1 for d in (p.get("discard") or []) if isinstance(d, dict) and card(d.get("id")).get("en") == Energy.WATER)
                        if water_in_discard >= 1:
                            score += 55  # H1 + v11 boost
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
                return 400  # v28: stronger bench vs fast KO with empty bench
            score = 320
            if is_primary_line(cid):
                score += 10
            # v26: generic board development boost vs fast decks - bench when thin
            if len(my_bench) < 2:
                score += 60  # v28 bench <2 => 380-400
            elif len(my_bench) < 3:
                score += 40  # v28 bench <3 => 360-380
            # v11 tape opening (Kaggriculture B21 inspiration): T1 Snover boost when early and have Water
            # If deckCount >50 (early), bench empty, and Snover (722) in hand with Water in hand -> +40
            try:
                if cid == 722:  # Snover
                    p = obs["current"]["players"][me_idx]
                    deck_cnt = int(p.get("deckCount") or 0)
                    if deck_cnt > 50 and len(my_bench) <= 1:
                        # check Water in hand
                        hand = p.get("hand") or []
                        has_water = any(card(h.get("id")).get("en") == Energy.WATER for h in hand if isinstance(h, dict))
                        if has_water:
                            score += 40  # tape opening boost
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
        return 90
    if ct == CardType.STADIUM:
        return 45
    if ct == CardType.TOOL:
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
        # v30 SWARM fix from a450: Riptide AND Hammer carry d=0 in db, raw-d scoring was coin-toss
        # Score by real estimate + KO bonus, never self-mill into deckout
        _my_act = _active(obs, me_idx)
        _opp_act = _active(obs, opp_idx)
        _opp_hp = int((_opp_act or {}).get("hp") or 0) if _opp_act else 0
        _at_t = card((_my_act or {}).get("id")).get("pt") if _my_act else None
        _dfn_c = card((_opp_act or {}).get("id")) if _opp_act else {}
        for i, o in enumerate(opts):
            _aid = o.get("attackId")
            _ad = attack_data(_aid)
            _est = estimate_attack_damage(_aid, obs, me_idx, opp_idx)
            if _est > 0:
                try:
                    if _at_t is not None and _dfn_c.get("w") is not None and _at_t == _dfn_c.get("w"):
                        _est += 30
                    if _at_t is not None and _dfn_c.get("res") is not None and _at_t == _dfn_c.get("res"):
                        _est = max(0, _est - 30)
                except Exception:
                    pass
            _sc = max(_est, int(_ad.get("d") or 0)) * 4
            if _est > 0 and _opp_hp and _est >= _opp_hp:
                _sc += 300
            if _mill_would_deck_us_out(_aid, obs, me_idx):
                _sc = -500
            scores.append((_sc, i))

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
# --- v21: archetype-scan hybrid (2026-10-11) ----------------------------------
# Obs facts (verified with tools/gauntlet_ffi_dbg.py):
#   - opponent DECK is NOT visible (only deckCount); hand is None.
#   - VISIBLE: their active+bench pokemon ids and their discard pile -> we can
#     classify the archetype from the board as the game develops.
#
# DRAW DIAGNOSIS (100g vs Banette/utility team, all draws instrumented):
#   every draw is the step_limit at turn ~1240-1660 with our last Kyogre vs an
#   energy-less utility wall (Latias ex 210 / Clefairy ex 190 / Slowking 120 /
#   Meowth ex 170). Mechanism: Kyogre's Riptide SHUFFLES all discard Water back
#   into our deck -> W-in-discard drops to ~0 -> next Riptide does ~0 damage ->
#   v11's +45 recycle bonus keeps choosing it -> infinite 0-damage loop.
#   The winning line exists: stop flushing the ammo, attach up to 3W (shuffled W
#   are drawable) and kill the wall with Swirling Waves 130 x2-3.
#
# Modes (set from a scan of opp active+bench+discard ids, sticky per process):
#   STALL   (Slowpoke/Latias/Clefairy/Meowth/Fezandipiti/Kyurem/Smoochum/
#            Annihilape/Conkeldurr/Zeraora seen) -> penalize Riptide -120.
#   LUCARIO (677/678)  -> protect our 4-prize Mega Abomasnow (v20b rule B).
#   MIRROR  (721/722/723) -> Hammer -150 guard at real deckCount<=10 (v20c A').

import json as _v21_json

RIPTIDE_ID_V21 = 1042
HAMMER_ID_V21 = 1046
FROST_BARRIER_ID_V21 = 1047
MEGA_ABOMASNOW_V21 = 723
LUCARIO_IDS_V21 = {677, 678}
MIRROR_IDS_V21 = {721, 722, 723}
# v30 SWARM bench-as-resource (a450)
# --- v31 (a450): S1/S2 WIRED. In v30 the constants below existed but were
# DEAD (defined, never referenced). v31 makes them live. S3 (attack-est) was
# already live in v30 (copied from a450 v29_swarm) and stays untouched.
SWARM_AUTO_FAST_EX = True
SWARM_BENCH = True

_FAST_EX_AUTO_CACHE = None

def _swarm_fast_ex() -> frozenset:
    """Seed 13 ids UNION auto-detected fast-ex threats (a450 v29_swarm S2).

    Auto rule: pokemon flagged ex (or mega-ex - but NOT our own mirror Mega
    Abomasnow ex, which would only add mirror noise; Mega Starmie 1031 stays
    in via the seed set) with hp >= 200, or hp >= 150 with retreat cost <= 2.
    Covers future/unknown ex cards that a hardcoded set will always miss.
    """
    global _FAST_EX_AUTO_CACHE
    if _FAST_EX_AUTO_CACHE is not None:
        return _FAST_EX_AUTO_CACHE
    ids = {63, 547, 1031, 861, 24, 171, 361, 336, 299, 169, 839, 992, 1002, 90, 93, 240, 347, 921, 1356, 100, 1355}
    if SWARM_AUTO_FAST_EX:
        try:
            for _cid_s, _c in CARDS.items():
                try:
                    if _c.get("ct") != CardType.POKEMON:
                        continue
                    is_ex = _c.get("ex") == 1
                    is_mex = _c.get("mex") == 1
                    if not is_ex and not is_mex:
                        continue
                    if is_mex and not is_ex:
                        continue  # mirror safety: our own Mega Abomasnow stays out
                    hp = int(_c.get("hp") or 0)
                    rc = int(_c.get("rc") or 9)
                    if hp >= 200 or (hp >= 150 and rc <= 2):
                        try:
                            ids.add(int(_cid_s))
                        except Exception:
                            pass
                except Exception:
                    continue
        except Exception:
            pass
    _FAST_EX_AUTO_CACHE = frozenset(ids)
    return _FAST_EX_AUTO_CACHE

B39_BENCH0 = int(os.environ.get("PTCG_B39_BENCH0", "35"))  # v39 knob; 35 == v38b (120 tested: mirror 902-898/1800, hard-suite worse -> rejected)
SWARM_BENCH_TARGET = int(os.environ.get("PTCG_B39_BENCH_TARGET", "3"))  # v39 knob
SWARM_BENCH_HOT = 35
SWARM_BENCH_WARM = 15
SWARM_BENCH_THREAT = 35
# v29 mirror specialist from 8560: Hammer one-shot >=280, Riptide >=100, no early trades
MILL_HAMMER_MIN_V29 = 280
MILL_RIPTIDE_MIN_V29 = 100
MIRROR_NO_TRADE_TURNS_V29 = 4
LOW_E_AGGRO_IDS_V21 = {676, 677, 678, 119, 120, 121, 96, 92, 93, 150, 89, 330, 345, 533, 710, 1349}
STALL_IDS_V21 = {115, 140, 144, 162, 163, 183, 184, 224, 272, 377, 1071}

# --- v36 adaptive opponent modeling (Kaggriculture v13 reactive) ---
# Inspired by Kaggriculture V13 TOP12 reactive: scan opponent board for animal/crop counts and switch strategy
# Here we scan opponent active+bench+discard for WALL / FAST_AGGRO / MIRROR archetypes and adapt

WALL_IDS_V36 = {150, 283, 756, 153, 648, 1031, 802, 472}  # Hydrapple ex 330, Mamoswine ex 340, Mega Kang 300, Cinderace ex 320, Grimmsnarl ex 320, Mega Starmie 330, Mamoswine 180, Kang 120
FAST_IDS_V36 = {336, 299, 816, 169, 839, 992, 90, 93, 347, 921, 240, 1356, 100, 1355, 142, 785, 547, 1002, 96, 99, 108, 117, 24, 95, 361, 666}  # Zacian, Duraludon, Thwackey, Dipplin, Seaking, Goldeen, Genesect, Zangoose, Ogerpon, Kang, Starmie, Cinderace
# MIRROR_IDS already defined as MIRROR_IDS_V21 = {721,722,723}

ADAPT_WALL_THRESHOLD = 2
ADAPT_FAST_THRESHOLD = 3

_V38 = {"dc": [], "obench": -1, "turn": -1}

def _v38_observe(obs, me_idx, opp_idx):
    try:
        cur = obs.get("current") or {}
        turn = int(cur.get("turn") or 0)
        if turn <= 1 and _V38["turn"] > 1:
            _V38["dc"] = []
        _V38["turn"] = turn
        p = (cur.get("players") or [])[opp_idx]
        _V38["obench"] = len(p.get("bench") or [])
        dc = int(p.get("deckCount") or 60)
        if not _V38["dc"] or dc < _V38["dc"][-1]:
            _V38["dc"].append(dc)
    except Exception:
        pass

def _v38_dc_drop() -> int:
    dc = _V38.get("dc") or []
    return (60 - min(dc)) if dc else 0

def _v38_wall_live_v2(wall_cnt, opp_ahp) -> bool:
    # v38b: more permissive - 1 evidence enough (was 2)
    ev = 0
    if wall_cnt >= 1:
        ev += 1
    if _V38.get("turn", 0) >= 4:
        ev += 1
    if _V38.get("obench", 9) <= 2:
        ev += 1
    return ev >= 1

def _v38_mirror_radar(mirror_cnt) -> bool:
    return mirror_cnt >= ADAPT_MIRROR_THRESHOLD or _v38_dc_drop() >= 8

ADAPT_MIRROR_THRESHOLD = 2

V41_ARCH = os.environ.get("PTCG_V41_ARCH", "1") not in ("0", "false", "False", "")
V41_SPREAD = os.environ.get("PTCG_V41_SPREAD", "1") not in ("0", "false", "False", "")
V41_ENDGAME = os.environ.get("PTCG_V41_ENDGAME", "1") not in ("0", "false", "False", "")
V41_WALLGATE = os.environ.get("PTCG_V41_WALLGATE", "v2")
V41_SPREAD_HANDCAP = int(os.environ.get("PTCG_V41_HANDCAP", "6"))

SPREAD_IDS_V41 = {741, 742, 743, 245, 119, 120, 121, 131, 132, 133, 112}
ALAKAZAM_IDS_V41 = {741, 742, 743, 245}
BENCHSPREAD_IDS_V41 = {119, 120, 121, 131, 132, 133, 112}  # Dragapult/Dusknoir/Munkidori
_V41 = {"arch": None, "turn": 0}


def _v41_archetype(seen, opp_active_id):
    """Sticky archetype call: once SPREAD/WALL/FAST/MIRROR is seen, keep it."""
    try:
        turn = int(_V38.get("turn", 0))
        if turn <= 1 and _V41["turn"] > 1:
            _V41["arch"] = None
        _V41["turn"] = turn
        if _V41["arch"]:
            return _V41["arch"]
        arch = None
        ids = set(seen or ())
        if opp_active_id is not None:
            ids.add(opp_active_id)
        if ids & SPREAD_IDS_V41:
            arch = "SPREAD"
        elif ids & MIRROR_IDS_V21:
            arch = "MIRROR"
        if arch:
            _V41["arch"] = arch
        return arch
    except Exception:
        return None


def _v41_wall_live(wall_cnt, opp_ahp) -> bool:
    if V41_WALLGATE == "strict":
        ev = 0
        if wall_cnt >= 2:
            ev += 1
        if _V38.get("turn", 0) >= 6:
            ev += 1
        if _V38.get("obench", 9) <= 1:
            ev += 1
        if opp_ahp and opp_ahp >= 300:
            ev += 1
        return ev >= 2
    return _v38_wall_live_v2(wall_cnt, opp_ahp)


def _v36_detect_mode(seen, opp_active_id, opp_active_hp):
    # Count how many distinct WALL / FAST ids seen
    wall_cnt = len(seen & WALL_IDS_V36)
    fast_cnt = len(seen & FAST_IDS_V36)
    mirror_cnt = len(seen & MIRROR_IDS_V21)
    # Active HP >=300 is strong wall signal even if id not in set (future walls)
    if opp_active_hp and opp_active_hp >= 300:
        wall_cnt += 2
    if opp_active_id in WALL_IDS_V36:
        wall_cnt += 1
    if opp_active_id in FAST_IDS_V36:
        fast_cnt += 1

    # Priority: WALL > FAST > MIRROR > DEFAULT (wall is most dangerous, needs ramp)
    if wall_cnt >= ADAPT_WALL_THRESHOLD:
        return "WALL", wall_cnt, fast_cnt, mirror_cnt
    if fast_cnt >= ADAPT_FAST_THRESHOLD:
        return "FAST", wall_cnt, fast_cnt, mirror_cnt
    if mirror_cnt >= ADAPT_MIRROR_THRESHOLD:
        return "MIRROR", wall_cnt, fast_cnt, mirror_cnt
    return "DEFAULT", wall_cnt, fast_cnt, mirror_cnt

FIGHTING_ENERGY_V21 = 6

def _v24_board_ids(me_idx: int, obs: dict) -> list:
    out = []
    a = _active(obs, me_idx)
    if a and a.get("id") is not None:
        out.append(a.get("id"))
    for p in _bench(obs, me_idx):
        if p and p.get("id") is not None:
            out.append(p.get("id"))
    return out


def _v24_board_n(me_idx: int, obs: dict) -> int:
    return len(_v24_board_ids(me_idx, obs))


def _v24_evo_has_pre_on_board(cid, obs: dict, me_idx: int) -> bool:
    """Can `cid` actually be put on the board right now (as an evolution)?"""
    c = card(cid)
    ef = c.get("ef")
    if not ef:
        return True  # basic: always playable
    pre_ids = set(BY_NAME.get(ef) or [])
    pre_ids &= set(PLAN.get("counts") or {})  # only pre-evos in our deck
    if not pre_ids:
        return False
    return any(i in pre_ids for i in _v24_board_ids(me_idx, obs))


def _v24_hand_count(cid, obs: dict, me_idx: int) -> int:
    try:
        hand = obs["current"]["players"][me_idx].get("hand") or []
        return sum(1 for h in hand if isinstance(h, dict) and h.get("id") == cid)
    except Exception:
        return 0


def _v24_discard_ids(obs: dict, me_idx: int) -> list:
    try:
        d = obs["current"]["players"][me_idx].get("discard") or []
        return [x.get("id") for x in d if isinstance(x, dict) and x.get("id") is not None]
    except Exception:
        return []


def _v24_search_gate(cid, obs: dict, me_idx: int) -> int:
    """Score delta for playing a search/recycle trainer whose result we
    cannot use this turn (unknown ids pass through unmodified)."""
    try:
        if cid in _V24_EX_SEARCH:
            exs = [c for c in PLAN.get("pokemon", [])
                   if card(c).get("mex") or card(c).get("ex")]
            if not any(_v24_evo_has_pre_on_board(c, obs, me_idx) for c in exs):
                return -150  # would fetch an ex we cannot evolve onto
            return 0
        if cid in _V24_EX_RECYCLE:
            disc = set(_v24_discard_ids(obs, me_idx))
            exs = [c for c in PLAN.get("pokemon", [])
                   if (card(c).get("mex") or card(c).get("ex")) and c in disc]
            if not any(_v24_evo_has_pre_on_board(c, obs, me_idx) for c in exs):
                return -150
            return 0
        if cid in _V24_RECYCLE:
            disc = set(_v24_discard_ids(obs, me_idx))
            usable = [c for c in disc if is_pokemon(c)
                      and (card(c).get("b") or _v24_evo_has_pre_on_board(c, obs, me_idx))]
            if not usable:
                return -80
            return 0
        return 0
    except Exception:
        return 0



_V21_SEEN = set()


def _v21_poke_energy_count(poke, energy_type):
    n = 0
    for e in (poke.get("energies") or []):
        eid = e.get("id") if isinstance(e, dict) else e
        try:
            if int(card(eid).get("en") or 0) == energy_type:
                n += 1
        except Exception:
            pass
    return n


def _v21_scan(obs, opp_idx):
    try:
        p = obs["current"]["players"][opp_idx]
        for poke in ([p.get("active")] if p.get("active") else []) + (p.get("bench") or []):
            if isinstance(poke, dict) and poke.get("id"):
                _V21_SEEN.add(int(poke["id"]))
        for dcard in (p.get("discard") or []):
            cid = dcard.get("id") if isinstance(dcard, dict) else dcard
            if cid:
                try:
                    _V21_SEEN.add(int(cid))
                except Exception:
                    pass
    except Exception:
        pass


_v21_original_score_main = _score_main_option


def _score_main_option_v21(opt, obs, me_idx, opp_idx):
    score = _v21_original_score_main(opt, obs, me_idx, opp_idx)
    try:
        _v21_scan(obs, opp_idx)
        my_active = _active(obs, me_idx)
        opp_active = _active(obs, opp_idx)
        if not my_active or not opp_active:
            return score
        mid, oid = my_active.get("id"), opp_active.get("id")
        otype = opt.get("type")
        seen = _V21_SEEN

        # --- STALL mode: keep our deck alive (Hammer self-mill is what burns it),
        # stop the 0-damage Riptide loop while the deck can still feed attacks,
        # and bias toward pressing damage. Wins vs stall come from prize damage
# (Swirling 130x2 kills every utility wall) or their self-mill deckout.
        if seen & STALL_IDS_V21:
            try:
                my_deck_n = int(obs["current"]["players"][me_idx].get("deckCount") or 20)
            except Exception:
                my_deck_n = 20
            if otype == OptionType.ATTACK:
                aid = opt.get("attackId")
                if aid == RIPTIDE_ID_V21 and my_deck_n > 12:
                    score -= 120          # 0-damage loop move while deck healthy
                if aid == HAMMER_ID_V21:
                    if my_deck_n <= 20:
                        score -= 200      # hard stop: their deck empties ~T35-50,
                    elif my_deck_n <= 30: # surviving it wins by their deckout
                        score -= 40
                if my_deck_n > 12 and aid not in (None, RIPTIDE_ID_V21):
                    score += 30           # press damage: walls never heal

        # --- MIRROR mode: deckout guard with the REAL deck counter (v26 improved).
        if seen & MIRROR_IDS_V21 and otype == OptionType.ATTACK \
                and opt.get("attackId") == HAMMER_ID_V21:
            try:
                deck_n = int(obs["current"]["players"][me_idx].get("deckCount") or 20)
            except Exception:
                deck_n = 20
            if deck_n <= 15:
                score -= 200  # v28 earlier guard
            elif deck_n <= 20:
                score -= 150
            elif deck_n <= 25:
                score -= 80

        # --- LUCARIO mode: 4-prize Mega Abomasnow protection (v26 improved).
        if seen & LUCARIO_IDS_V21:
            my_dmg = (int(my_active.get("maxHp") or 0) - int(my_active.get("hp") or 0))
            opp_f = _v21_poke_energy_count(opp_active, FIGHTING_ENERGY_V21)
            # v26: earlier protection - >=2 Fighting and >=50 dmg (was >=3 and >=80)
            if mid == MEGA_ABOMASNOW_V21 and opp_f >= 2 and my_dmg >= 50:
                if otype in (OptionType.RETREAT, OptionType.SWITCH, OptionType.TO_ACTIVE):
                    score += 160  # v26 +20
                elif otype == OptionType.ATTACK and opt.get("attackId") == FROST_BARRIER_ID_V21:
                    score += 110  # v26 +20
            # v26: vs Lucario, bench Snover as sacrifice (1 prize) and keep Mega on bench
            if opp_f >= 2 and len(my_bench) < 3:
                if otype == OptionType.PLAY and is_basic_pokemon(_hand_id(obs, me_idx, opt.get("index"))):
                    # boost benching basics vs Lucario
                    score += 20

        # --- v31 FAST_EX (S2 WIRED): auto-detected set, seen-based threat.
        try:
            _fast = _swarm_fast_ex()
            opp_id = opp_active.get("id") if opp_active else None
            threat_seen = bool(seen & _fast)
            if opp_id in _fast or threat_seen:
                # S1 WIRED: warm the bench BEFORE the first KO (root cause #1)
                if otype == OptionType.PLAY and len(my_bench) < SWARM_BENCH_TARGET:
                    score += SWARM_BENCH_THREAT
                # Snover (90 HP) retreats urgently only vs fast-ex ACTIVE
                if opp_id in _fast and my_active and my_active.get("id") == 722 \
                        and my_active.get("hp", 0) <= 90:
                    if otype in (OptionType.RETREAT, OptionType.SWITCH):
                        score += 100
        except Exception:
            pass

        # --- v31 S1 WIRED: bench-as-resource in EVERY matchup.
        # Root cause #1 (c87f forensics + our FFI): 50% of losses end with an
        # empty board T3-11. Plant basics while they are still in hand.
        if SWARM_BENCH and otype == OptionType.PLAY:
            try:
                _bid = _hand_id(obs, me_idx, opt.get("index"))
                if _bid and is_basic_pokemon(_bid) and len(my_bench) < SWARM_BENCH_TARGET:
                    if len(my_bench) == 0:
                        score += B39_BENCH0  # v39: never end a turn on an empty bench
                    else:
                        score += SWARM_BENCH_HOT if len(my_bench) <= 1 else SWARM_BENCH_WARM
            except Exception:
                pass

    except Exception:
        pass
    return score


_score_main_option = _score_main_option_v21


# --- v22b: stall attach planner (DISCOVERIES.md open problem #2) ---
# In STALL mode, walls never heal. A Kyogre with 3W does Swirling 130/turn:
# 120HP wall dies in 1, 190-210-260HP walls in 2. The frozen-draw endgame
# is Kyogre stuck at 1-2W chipping 0-dmg Riptides. So: build the 3W and
# force the kill.
_score_main_option_v21_inner = _score_main_option

def _score_main_option_v22b(opt, obs, me_idx, opp_idx):
    score = _score_main_option_v21_inner(opt, obs, me_idx, opp_idx)
    try:
        # Always scan opponent
        _v21_scan(obs, opp_idx)
        _v38_observe(obs, me_idx, opp_idx)
        my_active = _active(obs, me_idx)
        opp_active = _active(obs, opp_idx)
        if not my_active or not opp_active:
            return score
        # v36 adaptive detection (Kaggriculture v13 style)
        try:
            opp_aid = opp_active.get("id")
            opp_ahp = int(opp_active.get("hp") or 0)
        except Exception:
            opp_aid = None
            opp_ahp = 0
        mode, wall_cnt, fast_cnt, mirror_cnt = _v36_detect_mode(_V21_SEEN, opp_aid, opp_ahp)

        # Existing stall logic
        if (_V21_SEEN & STALL_IDS_V21):
            my_deck_n = 20
            try:
                my_deck_n = int(obs["current"]["players"][me_idx].get("deckCount") or 20)
            except Exception:
                pass
            if my_active.get("id") == 721:  # Kyogre only
                w = len(my_active.get("energies") or [])
                wall_hp = opp_active.get("hp") or 0
                if wall_hp > 0 and wall_hp <= 260:
                    if opt.get("type") == OptionType.ATTACH and w < 3 and opt.get("inPlayArea") == Area.ACTIVE:
                        score += 40
                    elif opt.get("type") == OptionType.ATTACK and opt.get("attackId") == 1043 and w >= 3:
                        score += 120

        # --- v36 adaptive modes ---
        otype = opt.get("type")
        if mode == "WALL" and _v41_wall_live(wall_cnt, opp_ahp):
            # v37 wallgate: keep v34 thick walls (proven 0.900 exotic) not aggressive v36
            # v34 logic: Riptide ramp +60 if water>=3, Frost +40, Swirling -30 if hp>=300
            if otype == OptionType.ATTACK:
                aid = opt.get("attackId")
                atxt = (attack_data(aid).get("t") or "").lower() if aid else ""
                est = estimate_attack_damage(aid, obs, me_idx, opp_idx) if aid else 0
                if "riptide" in atxt or "discard" in atxt:
                    try:
                        disc = obs["current"]["players"][me_idx].get("discard") or []
                        water_in_disc = sum(1 for d in disc if isinstance(d, dict) and card(d.get("id")).get("en") == 8)
                        if water_in_disc >= 3:
                            score += 60
                    except Exception:
                        pass
                if "frost" in atxt or "barrier" in atxt:
                    score += 40
                if "swirling" in atxt or est == 130:
                    try:
                        opp_hp = int(opp_active.get("hp") or 0)
                        if opp_hp >= 300 and est < opp_hp:
                            score -= 30
                    except Exception:
                        pass
            if otype == OptionType.PLAY and is_basic_pokemon(_hand_id(obs, me_idx, opt.get("index"))):
                if len(_bench(obs, me_idx)) < 3:
                    score += 15
            if otype == OptionType.ATTACK and opt.get("attackId") == HAMMER_ID_V21:
                try:
                    deck_n = int(obs["current"]["players"][me_idx].get("deckCount") or 20)
                    if deck_n > 20:
                        score -= 20
                except Exception:
                    pass

        elif mode == "FAST":
            # Fast aggro opponent: they rush us with low HP ex/non-ex
            # Priority: bench-as-resource HOT 50, KO, evolve fast
            if otype == OptionType.PLAY and is_basic_pokemon(_hand_id(obs, me_idx, opt.get("index"))):
                bl = len(_bench(obs, me_idx))
                if bl <= 1:
                    score += 50  # HOT 50 vs fast
                elif bl == 2:
                    score += 30
            if otype == OptionType.ATTACK:
                # KO boost already in base, but extra vs fast low HP
                try:
                    opp_hp = int(opp_active.get("hp") or 0)
                    if opp_hp <= 130:
                        score += 30
                except Exception:
                    pass
            if otype == OptionType.EVOLVE:
                score += 30  # evolve faster vs fast
            if otype == OptionType.ATTACH:
                # Attach to active that can KO fast threat
                try:
                    if opt.get("inPlayArea") == Area.ACTIVE:
                        score += 15
                except Exception:
                    pass

        elif mode == "MIRROR":
            # Mirror Kyogre: conserve deck, earlier Hammer guard, don't waste Riptide
            if otype == OptionType.ATTACK and opt.get("attackId") == HAMMER_ID_V21:
                try:
                    deck_n = int(obs["current"]["players"][me_idx].get("deckCount") or 20)
                    if deck_n <= 15:
                        score -= 220  # hard stop earlier than v34
                    elif deck_n <= 20:
                        score -= 160
                    elif deck_n <= 25:
                        score -= 90
                except Exception:
                    pass
            if otype == OptionType.ATTACK:
                aid = opt.get("attackId")
                if aid == RIPTIDE_ID_V21:
                    try:
                        opp_hp = int(opp_active.get("hp") or 0)
                        est = estimate_attack_damage(aid, obs, me_idx, opp_idx)
                        if est < opp_hp and est > 0:
                            # vs mirror, don't chip with Riptide if not KO, save Water
                            score -= 20
                    except Exception:
                        pass

        # --- v41 reactive layer: SPREAD plan + endgame prize-race deny ---
        if V41_ARCH:
            try:
                arch41 = _v41_archetype(_V21_SEEN, opp_aid)
                _me_p = obs["current"]["players"][me_idx]
                _opp_p = obs["current"]["players"][opp_idx]
                if V41_SPREAD and arch41 == "SPREAD":
                    _bench_n = len(_bench(obs, me_idx))
                    _hid = _hand_id(obs, me_idx, opt.get("index")) if otype == OptionType.PLAY else None
                    if _V21_SEEN & BENCHSPREAD_IDS_V41 and _hid and is_basic_pokemon(_hid):
                        # Dragapult/Dusknoir put counters on the bench: stay lean.
                        if _bench_n >= 2:
                            score -= 60
                        elif _bench_n == 1:
                            score -= 25
                    if opp_aid in ALAKAZAM_IDS_V41:
                        # Powerful Hand: 2 counters x THEIR hand on our ACTIVE;
                        # bypasses Frost Barrier. Only answer: KO it now.
                        if otype == OptionType.ATTACK:
                            try:
                                _est = estimate_attack_damage(opt.get("attackId"), obs, me_idx, opp_idx)
                                if _est >= opp_ahp > 0:
                                    score += 120  # secure the KO before it fires again
                                else:
                                    score += 40   # pressure: chip is still progress
                            except Exception:
                                pass
                        if otype == OptionType.EVOLVE:
                            score += 40  # get the 350 HP body online fast
                if V41_ENDGAME:
                    _opp_prizes = len(_opp_p.get("prize") or [])
                    if 1 <= _opp_prizes <= 3 and my_active and (card(my_active.get("id")) or {}).get("megaEx"):
                        _ahp = int(my_active.get("hp") or 0)
                        if _ahp <= 120 and len(_bench(obs, me_idx)) >= 1 and otype in (OptionType.RETREAT, OptionType.SWITCH, OptionType.TO_ACTIVE):
                            score += 80  # deny the 3-prize KO that ends the game
            except Exception:
                pass

        # --- v42.2 ML modulation: losing -> develop, winning -> press ---
        if V422_ML:
            try:
                _p = _ml2_predict(obs, me_idx, opp_idx)
                if _p is not None:
                    if _p < 0.4:
                        _hid2 = _hand_id(obs, me_idx, opt.get("index")) if otype == OptionType.PLAY else None
                        if _hid2 and is_basic_pokemon(_hid2):
                            score += int((0.4 - _p) * 120)
                        elif otype == OptionType.EVOLVE:
                            score += int((0.4 - _p) * 80)
                        elif otype == OptionType.ATTACH:
                            score += int((0.4 - _p) * 60)
                    elif _p > 0.6 and otype == OptionType.ATTACK:
                        score += int((_p - 0.6) * 100)
            except Exception:
                pass

        # DEFAULT mode keeps v34 logic (thick walls already handled in base)

    except Exception:
        pass
    return score




# ================= v42.2 per-arch state-value ML =================
V422_ML = os.environ.get("PTCG_V422_ML", "1") not in ("0", "false", "False", "")
_ML2_B64 = {
    "GLOBAL": "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",
    "SPREAD": "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",
    "GRASS": "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",
    "FIGHTING": "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",
    "WALL": "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",
    "DEFAULT": "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"
}  # arch -> base64 float32 blob (filled at build time)
_ML2_MODELS = None
_ML2_CACHE = {"key": None, "p": None}

ML2_SPREAD = {741, 742, 743, 245, 119, 120, 121, 131, 132, 133, 112}
ML2_GRASS = {150, 348, 93, 347, 921, 89, 90, 42, 92, 149, 346}
ML2_FIGHT = {678, 333, 677, 974, 676}
ML2_WALL = {345, 533, 344, 532, 117, 386, 283, 756, 1031}


def _ml2_load():
    global _ML2_MODELS
    if _ML2_MODELS is not None:
        return _ML2_MODELS
    try:
        import base64

        import numpy as np

        out = {}
        for arch, b64 in _ML2_B64.items():
            raw = np.frombuffer(base64.b64decode(b64), dtype=np.float32)
            d_in, h1n, h2n = int(raw[0]), int(raw[1]), int(raw[2])
            i = 4
            def take(n):
                nonlocal i
                a = raw[i:i + n].copy(); i += n
                return a
            out[arch] = (
                take(d_in * h1n).reshape(d_in, h1n), take(h1n),
                take(h1n * h2n).reshape(h1n, h2n), take(h2n),
                take(h2n), take(1), take(d_in), take(d_in),
            )
        _ML2_MODELS = out
    except Exception:
        _ML2_MODELS = {}
    return _ML2_MODELS


def _ml2_state(obs, me_idx, opp_idx):
    cur = obs.get("current") or {}
    players = cur.get("players") or [{}, {}]
    me = players[me_idx] if len(players) > me_idx else {}
    op = players[opp_idx] if len(players) > opp_idx else {}
    def act(pl):
        a = pl.get("active") or []
        return a[0] if a else {}
    my_a, op_a = act(me), act(op)
    def hpr(poke):
        hp = float(poke.get("hp") or 0); mx = float(poke.get("maxHp") or 0)
        return (hp / mx if mx else 0.0), hp, mx
    my_hr, my_hp, my_mx = hpr(my_a)
    op_hr, op_hp, op_mx = hpr(op_a)
    def bratio(pl):
        b = pl.get("bench") or []
        tot = sum(float(x.get("hp") or 0) for x in b if isinstance(x, dict))
        mxt = sum(float(x.get("maxHp") or 0) for x in b if isinstance(x, dict))
        return (tot / mxt if mxt else 0.0), len(b)
    my_br, my_bn = bratio(me)
    op_br, op_bn = bratio(op)
    def wdisc(pl):
        return sum(1 for d in (pl.get("discard") or []) if isinstance(d, dict) and d.get("id") == 3)
    return [
        min(float(cur.get("turn") or 0), 50) / 50.0,
        float(me.get("deckCount") or 0) / 60.0,
        float(op.get("deckCount") or 0) / 60.0,
        min(float(me.get("handCount") or 0), 12) / 12.0,
        min(float(op.get("handCount") or 0), 12) / 12.0,
        my_bn / 5.0, op_bn / 5.0, my_hr, op_hr,
        min(len(my_a.get("energies") or []), 5) / 5.0,
        min(len(op_a.get("energies") or []), 5) / 5.0,
        my_br, op_br,
        min(wdisc(me), 15) / 15.0, min(wdisc(op), 15) / 15.0,
        (6 - len(me.get("prize") or [])) / 6.0,
        (6 - len(op.get("prize") or [])) / 6.0,
        my_mx / 400.0, op_mx / 400.0, (my_hp - op_hp) / 400.0,
    ]


def _ml2_arch(seen_ids):
    s = set(seen_ids or ())
    if s & ML2_SPREAD:
        return "SPREAD"
    if s & MIRROR_IDS_V21:
        return "GLOBAL"
    if s & ML2_FIGHT:
        return "FIGHTING"
    if (s & ML2_WALL) and not (s & ML2_GRASS):
        return "WALL"
    if s & ML2_GRASS:
        return "GRASS"
    return "DEFAULT"


def _ml2_predict(obs, me_idx, opp_idx):
    try:
        cur = obs.get("current") or {}
        players = cur.get("players") or [{}, {}]
        me_p = players[me_idx]
        key = (
            int(cur.get("turn") or 0), int(me_p.get("deckCount") or 0),
            int(me_p.get("handCount") or 0), len(me_p.get("prize") or []),
            len(players[opp_idx].get("prize") or []),
        )
        if _ML2_CACHE["key"] == key:
            return _ML2_CACHE["p"]
        models = _ml2_load()
        if not models:
            return None
        import numpy as np

        arch = _ml2_arch(_V21_SEEN)
        mdl = models.get(arch) or models.get("GLOBAL")
        if mdl is None:
            return None
        W1, b1, W2, b2, W3, b3, mean, std = mdl
        x = (np.asarray(_ml2_state(obs, me_idx, opp_idx), dtype=np.float32) - mean) / std
        h = np.maximum(x @ W1 + b1, 0)
        h = np.maximum(h @ W2 + b2, 0)
        z = float(np.dot(h, W3) + float(b3[0]))
        p = 1.0 / (1.0 + pow(2.718281828, -z)) if -20 < z < 20 else (1.0 if z > 0 else 0.0)
        _ML2_CACHE["key"] = key
        _ML2_CACHE["p"] = p
        return p
    except Exception:
        return None


def agent(obs: dict) -> list[int]:
    try:
        return _decide(obs)
    except Exception:
        return _fallback(obs)
