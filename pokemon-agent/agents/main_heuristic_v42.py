# v42 ML-EXPERIMENT (2026-10-14): v41 reactive + tiny MLP option-value blend.
# Weights trained on self-play (tools/gen_ml_data.py + tools/train_ml.py),
# embedded below as base64 float32. score += V42_ML_W * (p - 0.5) on MAIN options.
# Knobs: PTCG_V42_ML=1, PTCG_V42_ML_W=60. Falls back to pure v41 if numpy/model absent.
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

        # DEFAULT mode keeps v34 logic (thick walls already handled in base)

    except Exception:
        pass
    if V42_ML:
        try:
            score += V42_ML_W * (_ml_predict(ml_features(obs, me_idx, opp_idx, opt)) - 0.5)
        except Exception:
            pass
    return score




# ================= v42 ML option-value (experimental) =================
V42_ML = os.environ.get("PTCG_V42_ML", "0") not in ("0", "false", "False", "")  # default OFF: A/B 32g/deck = -0.6pp (neutral-neg); experimental scaffold
V42_ML_W = float(os.environ.get("PTCG_V42_ML_W", "25"))
_ML_W_B64 = "AADwQQAAwEIAAIBCAAAAAPT4ibz+suo+CZQVPbYWlj6+f+A+fdrSvHN4xD7R9m++fWpOPl/dYT6n+n8+ZKB5vquIor47dIQ+OEvYPeKb3D4Zz7W+RBOvPkNm2D0bnQE/ZDltu5Kozj6eDSY+kVD7PkSgmD6/uAk/QzgcvwXRqD7Qsh49odmxPdKx4r6yLiO/bC4qvkFqk77Qpjy9zhc1v2X7qD6vWmc+jsPgPdP2KL7kwKa9ngSavnN7Kb6mnB0+2kH0PXX+5r7MywU+QY/gvnV91DxSJNc+n1XoPi3wAT7Fkdy+OdC4vpvNCb8gc0Q+JTE7vlS7mTtuByO+xvL9Pd0j2z5au9a+eyvTvhW74b2crcg+loeWvkzlwb7m0Nm+idWuvhlEpj3tFXM/UEK0vj73rD4C4FY+ffyevio1OT28Ci2+SVg2vtM9KD9Onju/qFoLP6Fi7j1rpKm956cSPkq/2j492NY9W1hoPkq8mT58lr++87WlPlCXRD/HbyE+o3IUP2c3RL51Tp28boWPvjDB4L6VdVw/SOrnvlwqazzEbgq/DI1pvpQVSL3/pZS+LJUOvF/yTD/1D1K+nx5rvhyj1j2iYoG+VAVIP+ALHz5f03e+q9mkvotDoz497xW/qGY3P64BtT5hpXA9y1DyPrqTqj3MB0g/phafvryniz+lmnG+CC2Uvr+7MT6SWyG+yixKvZzwg7+H9Ji+XXX7PoH/ZT5Q77w+NMXXPdBLYr4NQ3G+zMUFPWv1g70TGwG/opFWvrTFXL6NqfK+rQ53Pii6U77eAgo/DoSwvQMnBb1IUoa9zmqFvpVquzwkoj4+z0CwPt/exD6ok4g+ByHCvkrBiL4LEau+1RMVvuHJ/r2kUxa+IU0pPthezL62AlK+LxmiPiy40D6xOpm9F0dIPkn7S74c/+k+Oz6SvfSuJb4kDou+1V7IvsZpuD3TajW+WQSDvh2eDr9l16W/UHhhPkb/Ob9IV7+8JUPoPd+OOjx+TPI9XtuXvWlbjL0dLny+Y/gruxHs8L3RUw0/abXAPpbmpD5S66G9PKQ8Pj5/HL4PVHM9jkAKP1dawz3LO8y+/ZBkvlRrIz/aYfs8rKcCPo3EUT8ACxg/n8VSPksCvj61aaY+Y/cNPzEydj4LQ+s9BGYOvhU6sL6t16w8x1XTPikGBL6HqbG+2L+Ovoyxv72EpvO+pDsOvYmarz4MFaQ/0KB6PpF/472A0VC+0+Fmv9bJlD2z4Ly8sT8GP/E2HL6QJ8o98rV3voEOpD1dx5Y+rF7DvmdB4ryXOhS/aelWP8CIUT/uVk0/g5rjvtGtKz7wfAk++WQhPIr5szuv7Jk+PzaUvqgNrz4NrdE9nw/vPCo0G7x25Ra+Hsm1PvjvA76udSc8FTT8PYlwj76fAQw/3zthvtRSmD6z7gA+qLIXv5sFzL1ESIG+mpO1vcjyz75Qz0E97bv5veTWHj4OdoO+2GsbvBcxVr6vVha8qmeaPnsvkD7kw6e+OXSkvhqcSz5FM8G9Av8VPc2P2b6oMEg+vMAdP74H6r0m6f0+r0pKPoFyWL9zz609fJuBvTVK3D7rK+K9WbU7vl/d/j2Nj6C+eMIjvIX+gjyLxau+3XURvigcyz4ijBY/HJKavgybvboHiuY+bvKDPuBvlD/PXZ8+YgGAvqYAjT69oeU9zUAZvs/pg7zokqi+lCkzv9BI0L5FiMO+zqnxvQ9L/jxRRQy/XGVZPrl0drpDtSI+EXq1Pjcc+T668KK+mImHPobpMD5W22E+zILDPhIs0r6vilK+pYOjvgTcib4fm0M9hV0Tv5IW675o0tQ8HlPhvS0DHT6xBMa+3CQUvbNHAj6DixK+0O6MvmoX9z0mM1Q+WiTkvclKWj0ONes+Lnbpu7Fhuz7SzaI+Y2UUvgXJlT5/8bw+7V6yPmKM2D5qzwI+CDUePmvLIT5VYA8/iJ6IPjRQP78uVbI+rj9JPv/Yxb3PV2C+SLXzvozC5z5nOeo9y8OuvnJxYj6NCFI9qT0DP/rMCr5ORnS/BijZPTpsMD4A5y++mQsVvwWiQ77qnt8+YXlBv7gv3j5thBO/oAVvP6C0JT7X7By+iz7JPv3UID57Ypo9d4IPPmZU4rnBItG+clUlP8qv3D12JYq+ziMcvuEnL7+1YZa+eeunvoYwsb2DBU69gBEeP7MAvr0Y0IO9ym68O3+2DL8puhy+4DO4vt4fVD8SBxM+MkK+u51Vyb5TPwG9hvdUvsmKlj7M7g2+ZKEWvj9P5z7Ehga+1YkAvpttuz7B7vi9INILvXPpwb0MmbG9CmNNvjx+GTx2qTA/8DDNPvRsJb7FDxY/fQfnvN47lz4ZkVM+So/rPTcnRz8BO4M+gB6wvrKnKD+oLBi+8cPdO6HThr9GG+I+ePHiPXaddz2Ijos+DWUFPyb9gj2QOuQ+owoAv3HhN74Suzk/ylG7PoHXir42nLI9n80XPotTHb6skeA6HiSOvrD4Gb9nUoK+b2H6PuRi8r5ZHkg85ZdpPqGkdD5qdrS+7gNgvUx9jr2YQAg+IDVIvpeRwb7nJSE+PnhEP35is712djy+wLgWPhKXLr6oj3g+IOK2vq2cgz0XLhK+9zSWvcNcJDwoCke9Qy2vvfsODL0lRKe+7f2CPUkwGz7TSqs9XdJ5PlZrpb5g9iO/DTv9PVu7jzyN0ig/Bd80Ptxp1L6f1V886verO1DhyL4y+D0/O+wuPqSUzD2mqmY+s6sLP7w1Nr3TyRw+vDEjvoD6o72hJSo+biW+PqEOoD5uJ4Y+Hnj4vWWu1r2wuDc97vS9vKdXPz62JAw+Xs5IPpIn9j3NtXs+2kuGviRvQT7CijI/bkLnOwj9V76DOAk+Z1WLPqknLT6Nawi/LxcJvkxKE76Xrpi+DOnhPPRrj705Hg8+SNQrPzW6sT7GTM49b7GtvtgUpD3lko++46zCvKNEMr4MSTu+dqPUukMtg76M/se+eIsQv/+zATpi3YS+jDyyPYk/nj4mBBC+MGUKPlebcb6I+xU/nwywPmF5kD5Pq6e+qwY3PofDv7797yu+GVRNPkCTYz4Pnjq9pQpFPxFmiL68KD6+blUovXvXlr6KWes+4ADvvWP3dj9wsEM8om/CPoAoO76NgnU+Ij8Gv7paBL64RTu+LDQtPqdtBb9xEJs+Kr/ivZh7vL2fWju+zA9KvSQ2nb7L+gQ/D5QPPMz5UL7Vzoi+Q4mrvsxlsL6JvxE/UMcJPEmhQL5871S+V9sWPwOUK76BuxK+3QPiPopEWD5+VRc+BVxMvc4fAr67ora9oFNhvhTiVDxN5dG7pX/lPoupDr7ff0Y+6/gnvcilCL/kG8M8yjkyvC7Azb7cB2Q+7pTLvqsCzr53ET+9F9bdPPW2k76pag0+irbmPYFL/L0Niuu8NdcVP2V4Y74m3oo+IRCyPW9tKz7Va3S+mKr2Phd80DytWQa+w3hVvg3jqrw9Uum9wkkkvoG94D4cqaG+T1uEvg454z5RfUg+ONLAPVSu8L3m60I98saZvG1f7z4BTEW+2X6fPb3I/T1JEz6/T/EcvkTMsj4q1nm+x9+Ovmd4WzzFPdo+rxlFPoXZw7x9VCc+0whWPiwJnb7LSc+9cJI6PhEOnD46q2u+GcUMv2Fe174yOS6/IAmEvo4sXr0nfc895lmTvju0NT7o8Qq/hH4WPkRWYL5iwyg/MGRcPveGFL5ubae+g9GOvkMcKL8U/ri+40imvs2Dxj7eQxc+S8grvtswlL4e81++lSv5PVcIZz5mbi4+Rr4iPUbvgj4xERG8phduPvz2kL6zEyC//GmtPl5AOT5/Xce94rZBPn/UBb390he+YwhHvsiPjj4LNp8+ixFQvoNrm77UhaI9X29xPEWEWr70y7M+l/cMvfF5AD4aC9I+hNEuP34Oqr4Wxyc+ncfKvoDtIT4TGxS/xiQUP4rpaL4nHjs+RkCMvvxE7r05XkE+kSYJPp4T0z1cOWQ+9U97Pp61oT1is/s6sNNpPkEBNz1Mn/C9E/cEvQtrnr7mv2W8nybQPQzZ57y9Ido9uqN8Pov37L7f/xS9jbflPs/HN78haOC96d+yPqkV2b5Z5+A+pw7OvoZqoD7sIvY++HfTPuzNsz0s8EU+pg8uvid/Yz6JYOW9LmofvpcoNT5vHWs9GOVFvpTFNr08ZuS+x4sxPwQYXj4McR6/MBLNvvAt8L3g+kO9Q5rQvS9Xgb5nn20+KIG/vVRjtj6RtNa8XqKePiTGq77ipNQ91nRovtVqqbxgRmc+9zI2P8Ti2j5LIF4+OPWMvkkkoT7QIhY9c1CXPgoGvz4bfSO+7B6YvmYJcj546e0+Wh/3vfAi5j4IoZ6+XaTAPegheT38Hyq/cmvfPg96rb2l4GW+xCIRv/9viz4tNdm9op3VvIYTTr/EWzg9pUzGvgnv0j5kr1E9WIYOPQBThD9bkiu9kUMpP9rSFT58N7+9GFWhPvRr2D53aMK+jmICPzHrTD6tnAw/Vc/FPmSD0L7hsqq+DwoxP71j3j1nh3u+lfDIPfj8cL00uQK/iBUnv8iNHL9ufoY+BscmvbHUFL2DTlq+xGVwPpboLr9ffd6+lwdhvttbi7753hI+R3OQvuSdjL06cte+3pVjvvAEFT9thMK+36wMvy0WXr3rSq69YzsMPksCUbx5Fls+VSsnvk92Ur4AIYW+Iku1vsoPYz5nyeE+oecpPn8rSD4aGYw+norgPpYm5L499oW+rLqhPTOeHr9AoRE9tM1LPUbaB74Yl6G+P2bvPkEzK79ZcaA8jxV0P7NpETuxe9290KqsPhnbtT4Jhf++Z/d7vbBSIL2HVpg+KiWePv5FwT2IytC9+A5NPoUNSL4uMoK9mkIuPipVE743lKm+/UfGPtSu/Dtfwyu/Q4SePnSxB76fmXU+lYYEvK/lD73/Evm811Dxvj58JT3LPTw/gIlPv31C1j3ulRY9/PdCvxdT5r4I5xI/kXwMvMs7GT8Iz6g+ciVHPN7YWj4u7GY+Fh+1PsUH0j0f6Iu9iXc/PToBdz5pdgM+CSqLvTZLGb7AJ5y+YmLQvdOIlb7sCtC7XrAOPhcGGT0w3529KOVyPr97Gj99364+nXkmP0JcDD+LE44+uNaKvVIYDr+PI2e+UfqgvOck/j5gZra+PPT7PhrbhL0AcD8+j+Envz8JEz01w7W9b240PuH0wDxpAJe+ImF6PiaoNz5uyB0+XWCFPqaLkT6Iiri7uHqzvskWt74nb7I+19Y7PhbP1zyW1uW9OX8FPIHG0Ts5E7K9tNE4vhoPDz+VuHE9DywgvjYhrL7J3j++5Uo+PmyDSD5L7Wa92sBaPCFPob0cdJK+gRSsPtwLxT01ryM/m+1HvvJzEb0YdGk+npqBvUVzt76E4Hq+YRrVPNaRtT0dG8i8l6iEPtA9gz7Nrqo994XjOy66hb1MsBE+JSVzPnAwgDyG9O09d36rvZKaur7xUoS+GHdKPg9f7D0JOdI+nVBtPHakZD5k5q4+03aDPq3lIL6RMUO90j4JPWdUgr62zPo9e16HPptF/r06YgI/eLuZvRSlVr3k/3u930M7vrT13D2kbqk7OKHbPvORID6rKQ4+aktqvWD1ur6CUL28QtBgvsqpez6SyAC8JTXcPrFpQj5+6Vw+YvBzPQpezD2vAxa99C+ZPpLZxL6UHCI9b5psP/MMcT0WKAQ9PGJoPecwir4Ap+Q+luIAPeShnj3iy50+adMqP1zLK73WlKE+51WSvbM80z3ST0W+1EHePaAs4j4+m8Q+sAEEvTmhFj64kPA9cm5wPq9tnbz1uAE/HAoQPnNacT2/1r2+tSgpPqXneb4cL6u+4AyWvOzzKL+bkSo+46fLPbmkoz0gLru+WPMkP4/aTr2/MEC+7rmRvvIyTL2QV50+25+pPmpwAL6pQUS+Kd7HPWPa1L3eRA2+AafSvgxD2b25Tce9bPCCvXsYNj4uUFC+Vrgjv7KSLL6Omag+0To9Pp9cpr6iFnI+OIaYvmW2CT/azq29YKjKPQjoET/Wdhe89H+7vtkmCb8oMUI+2u8TPgxmrj6CcMy+xFsoP1SFvb7bLLq8lhxMPg01CD9NKcw976Ebv8fjWb66g4o9Nur2PaRZZj6l/36+5srxPvEQa74vCt8+LKCQvYHowD4HYy2+2gXwvdXST79UDKW9d3LfvuXjqT6tuc0+d4q4PcO0h74DLfG9Ix/1vIAhLj8OMho+ONNiPlcqnLvtUTm/vfzMvhBqSL/DOK69cajdPULRqr7kSQS+Hi7qPkYUmL3g+gO+NA7VvC6YZD3CDs88inB7PU779D4okOW+geOMvu5CCT1xbuQ9qqykvbRl0L10KAs/3cmFvhsNWr0Gb1S9Tvt6Pf8z2L3pZyg/ntmMvuFFuL37iT2+4y6mvhsTar0LCzq/SOyKPkQ05b7Fh6u9nlehPQOdIj7ULry+HFGOPtX05T4bmuu97ei0Pqj1lr2Pv+q8K9woPz9yrr68ICK+g4IkPrB6+L1DQWe+/paoPfsnPz9ndQa/byDdPfrXlj4/FWa+PVe7vgqVAT9M1pM88EumPqRZSj6db18+Yzb5PRJFZz6dps6+keDpvY4/DD4J1YK+XQq4vaGl1r57TsE+4+v9PrLgpr3DlAs+AIkZvjt4vT5/ySY+s9udPknTZz0tlBi9OIfIvp2bMj70xjy+o2sNPpEZCT3Fv5A+Q8WPu24/hz623XO+cSIhPicAbb3IZk09GsOXPCONdz6EfgW/w9eqPcmRxb7giZ8+bGUCv6GyhL6ASN2+FrTYPh9nqr6x8vA8SKkNvrjs7b7fWrK9bTkvPgXhQr1G0Xg+92G/vcMb6Dpuesu9Cq21PTMI+z64jL89QaNNPZOBI77pvke++ovBPhcJk75FbnG+FCDOvORt4b1OTQE/xmccv80Vvz0DcDw+dyCUvmRsKr6pwuQ9CGvXPjdhc74PxdC+8Y6APoFvyT5sKbG9M1QSv+/uvz5Z9lG9sZOUPlPxN7x+o8a9r/fuvUfJwj6gob0+Pk8Nv7GKd74M7eo+ujjCvQXas77iIZc6tDblvJ7mzby1lv29TfejvX8U8b0jkbA9ieJWvlEpmb28Xhi9up2sPuJ0xT3DCOi8CsQNPnjA1j01z48+fusFPq8m7T5mwbE+E3MtvGkw270LWGk+MJgIPmwHyLzyP8O+YTzyvk20Bb7HkDs+A3CPPguQYr7BmRY/czy0PbYx+D1lnVc9OKGsvlAsHr7BQB6/cYGSvjKOVr/27Yo+Bj9JPHpKAj+xEU4+d8YIv/tvbj5Qpj8+OwiNPiRNnjzaMgS/AsRBOgGztz7QZIw9ofyRPgmsPT9rwjc+NxYQvpgtAL9gPNK9KKI2vvzE8L5Yqpw+5+7oPBGdarwZKfi+81vPvneP5T7lmzq/lJgZPEH/Kz8Vob87Q72UPrxhhj0qc76+sB62PD7XvD4eR8w8yg7APgDciz4tLuQ+Xu/Wvpw+qb3uU4q+NYxQPQsRZzp+ZNA9VVLPvety6753yQm85eBXvhFdd75Q1sU95aOWPohfij68Qiy8VNw9v7FfFb5EXn0+pvwwPp5JNj4SecO+G4b0PqrdnL5LLC89Gv3BvsWTir4lCi89n4blvpGUDL+YJXq+aVzIPth0yL1Spgs/6bx7vRBhtj1nniS/x8q6vtEXBD+PV84+uBK3Pp0t3D1w3NY+NT+TvtYHxT0UI969umuUvS2utz00Lq49S5vFvqFIvr6+lq2+QZy3Poov4b5Z1PW+epsnPyewTzvmTCq/48TOvob3Az+uvQ6+rgfcPoQdqz3VFlE87nV4P93cAD45XUO9jqOPOwgw0T426bQ9YYE6PtHJZz2AMZ2+WjEdvDyAVb2Rd/A8z80Mvzrj/b5/7dy+ld/FPUz9Gb86IiA9Csm2PRkmC7/Sp8C9DbGtveWGRD7QBjm/b/JHvj62HL+3FEm+/dP3Pf7ZJr48ZoG+aKljvre6Hz9i9Ak9ltMGPzVYBr/r9kC+dMxvPlQPK75GY+i9bYm3PR65f760H8k+zRJgvqHhjD6HGgq+NHwIvQsuDr/bu9I94DxcPgnqlj7ivUs85XLDvHVQer+5E+U98hBMPrBRvLwym3g+UnfsvtiNhL4ekiU9ftt1PkxGA7/paFW+VG0IP8wyfb5Vbj0/H629vlZWw761ba0+2d86P4mfqr4KKYI+IAK6viMhKT/eWwu/HDXFvrPGRT1e4jA/4lnhPr2yPj/14/g+hQCMvaYN5L4JfAm/co8Lv4hCh7tVrUi/guXCPUVu7D6fpiE/qw1yPl7pub0l8e0964m0vpfAkb46VLi+SuArP2NYDj3R3NC+mGaMPl7SVD4kUpg+cHNmPTYSmDsRPzy+JoMzPvxUrz7xksG+0sxVvTWF5z6DBnm+lsU8PmOqNj64v4k9x4JOP4w2ED5lVL0+UkZhvo22WL7YnRM+jjwDP2KgoD4E0j4/CekiPk705r1oNxg+Cv5fvQs1Bb7g5ca+HOycPoGZlb7W3Dg+d8aFvqrNCD+Yo7y9DT+EPoPcpr7NU8C+ttnUPVmskTtA1I4+xhVVvryBkr4K5LM9urtJPhWgYb79U+Q+a0MavkAWc75o4HE9o7DAvjxHEj9gc/y+XArGPr9PrD46YCK/L22HvuIICD/Gr0w+XSp1vWZ99z61wKC+6U8Rvp6lHL8r5am9TbkSvv2fAD4uutM6l/tQvljcNT8EhYQ+3TZTPpYBi74D/Pq9lFcZvex8lr1VtEO++rQ2Pj/LuL3+IGO9aabfvfwDwD5Z4gy+9VoTvyBXPb4rUAA+JuUXPg1PSz5p8Ka9HJOzvgUgMT3qPA2+wYu3vgiKaT3nDF+9lnLovg9Ocb6TNmo+961fvrmciT0l1DU+29RNvk43yz4eIra9xbWAvWvSer4D7AA/cEuLPtJm6z5UZYy+O2dAv87TtT4nFim+m5vVvUn87D1VTds9vcvPPqW3ub6ys2w+QITlPdHrV712yAg/kYeOPqg/+j3ECwy/P/dcvZynWz1ueFk+N+GkviPHdb6gaZO+85rcOzeaTL3rncI+g+7pvZxdZ7t1DlA+sjphvSAww7yJ4zA/Gl61vtQVSj3+UFu+ORviPbw8Br+eVJs9rwXUPmwDEz/KROA+EQubPi96qj2W9q68fyI+vuJ1PD4tBlo+y3mZPolq5r74QqC+i9nUvlo1Br8gvIm+jSc2P2QWJr43Qt09oym7PqJF3D4niI2+T30YP0Cas73p8KU95uRcPtyY/L5EPEG+WmKyvh6Lkz5PuLu8KRuVvlYQqz7QouY+nM6ZPdjAoD4UjQ2/dfIbPpZsdD09s6e9tOsuPfqp7D7nUDm+AfjlvtBdDrz1WQA/KIwpPaP3uz7oYcY6/B+ZvuHapL61uOI9h73ePvwl9r5lBKA+T2Ahvvi4b7wQt4g+rltIPv6VED6BeQ+/whlVPo9ysztzoyc/Ws8vPZ9Uur3q/gy/HXWWvSFur75l23M9Ws5zPI5iAz2KAIc9GwfHvC9MJj6us8W+HuUvv+wkHL6BQ7u+Nt5xvYpvRz5lUoe+qmiuPh2BPb3qDv+7uIoFP13I7T37/1I9Vp69PEz9qLsIYbU+wnAVv0d/bT6REm2+G39UvpXw6b4dTvw+YPegvIkeZr0U9rK+XxgNPuqLKr8g/uo9+BIyP1FEhL082389+bgbPa684L2JTIu+bCM3PP7fDz5MJcE+MlHcvZwFkD5qah898GsIPwhTBD6qXiO8+Vczv1lv7T66fwE/AVQqviP0Nb9rUum+Tzi8PnTg8b06gDa+Ft8CvY6hrT5typm9Gc/WPAxHSL7Vj+0+qj0JP1i/jb4hiJe+dQbSu5UrGz/XNIG+nMUVP04XTT4Sss+82oNTPsr7xz4ta7W+hQgwvlZl4D5AmVm9Y4iyvjMkij5vUrO9TEWSvmT6h770Dxs8WzDePuwk6j4Klou9Oh39PsV/9r46Rwa+GGHtvdZywL6DYdQ+vtp7Prq3Kr5cZDM/OQsWPQiPgL4Gunm+NTygvt0Lxj4b0YQ+BIG5PXjzMD4tRaW+uGWLPg8/JL/hxN08Z9eqvsevrr2CBTQ+SXRnPm0cwb7SNZS9YsQyvpEcm72qxu09xOnYPkX7hz4OPMM+62GjvW1PYr1fQY2+6pmfvt/uRb4UVj0+auSUPYX46DxEhIm8+0FZPqJsyj1Ckkw+VpnHvryXgr7uweI97OdsPZrOkL0ubV++Tf8WP5cW472Rpnc9yMMZPmGLFb9nDqU9bbAdPtFdAD7px3I9JcDZvJ6xpz3V+Fw+kskpvTXHLT1YpMG9DjCTPvzOLj0mR1k+cUPWvrKCaj6rEp0+vNezPkKXmT1N4oO9IPDGPTPXYb0C7dM9V6YPvvnK7T7tbJE+x6PUvi9plD1d1Su+jV4nvr0hPr3tRqW9qbwXPgLekb4v6ls+sVrNPtC5Ej6mvLc9qmkLPQidOb4PFJo94l99PpV2pD5+U8k+B3e1PvxdKz1r3ls+DloxvUkEo7743IA9EKM0vl0T/T0Jc1y+wLB4Pldfmj5vuCI+7/rUvQH1DT5lsxY+mZIFvtnn0zz7gSM+U7cjvVuakj55kvc+MjmwvsLoLz5uaTa+0Uo3PaTeLb4dKL09B0DMPY+niD4v/TU+bQM/vna1sj4jJxK8vaJhPl2ZoL2jBIG8xX6UPmk0BT7FmYI+q4ZWvkamcT6dZJw9nSKrPYZYCb7u2r295Ra9PkFtzL4WAwC9oCCwvYlxlz41V9c9sa6KPtg6nT1id9k7dORaPlSu1r2fHQw+tr+Hvpnqn73wsjo+/aR2vnBGkD4Nys2+O575vtxxO77TO7u9FcdePeB/Mzw+95Y9E6hYPiORLrtUP/08IxWEvtHghT6SxCq/732mOwoP9T0wTBc+eyDovP8Quj3pRkM+P7Z2PhwyBb0dbsI9ONmxPWOhbD5o/og+DuALPM5DF76BiJE9s2JUPrObCT43Eug9gpjEPu4Hi766rog+V1QUvsKDVD1Ca4U9OmuXPj/Zmb1i1Vi9SGhkviyIMj5t2fS9VIH8PX05OL5fqXi9lg7oPftxQr1PNqc+ObaNvbAwID2b35q+gqqFPuCxqzybXCE+beddvg8V0r5Orxa/cVdgvlxZlz6TlE49FVMkvZ7f4jxuNgQ+QbjxvbD6oz2YH6m9vWG1vg3UG70i/KM+vHXwvV079j2zkr69eRiSvT13mz1r6Sk9yJ5zvsdNHr+D3RS+UwaIvvUKqb4Lt+k9a+5vPV46xb6HBrQ+nzD+Pa09wL3yIxM+5+F8vE8tFr47+Ju+GNMwvYfizj2zCNO+0wObvj77jL5X2/U7CqILvtp12T4a3PC+SF0tvsVx7rxWKCs+xWXzvtNnmrz3ZGc+USt7PH+te75B+G0+NhWAvUgOLr4M7JK+L2qEPUig9D356cS9z9znPcS3dD30RI4+x1sbPXaLEr6sYw69RZ8uPvfj0z1ESyy+SlDDPeTcb74qO+I9776GvXOeHT6rKo29wLmevnqt4b7z/Ke+5PrhPYJJ6b6QdlM+9nKVvv1pkD6Di5i+h4SWvVtzwr1wGGI9Ab3MPAMS0Lwkx+Q9oP0Cvm/olj7lAIw9S9QMPjwtmTzR0go8siLXvM6dxD3bXM8+1QqPPpmjEb4iaGS+xck2Ptl2EjzjT0Y+FZeCvNu+Jr07hpa9O9Q7vg6WfL0hGI8+WDrPPppWhj0Syw2+GlukvSY3+z2MxI+8IUunPVWBZr2Y7bW9uTN8PZUgq70f/sU+xypjPU0Y3751HD695szNvUYxur4RlbY9vSDuPYXrm7ysoB09qYcMvqHYLL1s+Ua+M3eJvgO/Zj44Wla+DjBPPgFQ8T3psqm91jQOvk4GhryDHxc+efKhPoj3hDxO30g9iGhxPlCvyTwL8rs9lJyWvUk2ir3OIAG+qwNBvUhyNz1PKJC+EGToPkVmZL6XMyq+by8bPgPTv748YB+9AO2Evp69FL4pM6m99U/ZPZtv+zyvZiU+HnqZPm6dBT4rlMW95vJkPm5mw73v8Zu9deV9PlBYAj4UpPa8e46PvSctID5eLom+gjbFPTqhcDxNsT4+utbPvaA0XT4XbFI+itQnvpewNL0mCse9ORqPPQxsRT4ViYU8NqnVvhw9Ob6IweW8yC3oPbItZT5Kn8u9b/52PAaIZr2lp/I9/7oMPXhJvD75cuO9HeglPOfRpL5Naxi+9Gb9PV++1T3GPoa+T7IovsD+ozxJgw0+pwyDPvnxBT2G+5i+hSvNvYPAlLxL0gQ+ubv7PNfs1r1tfBI+7PpDPo87sD3pr+O8VJurPnmOhr7T+Ok9JnQ2PqcXh740ixM9Op+gvdZC7D0phm89UqjzPrmqCD7UCt691h+RPQ/Hqbyimc29lzGcPgEfpL7GPO+99SYhPSRNSL4i/gm/0uBGPuFMnL6tjZW94l3gvZJpGr62xcW+j5YMvngmjT4m7c49MfIvPmmGwL6YID29dX4PvuQGxD3RpYE9dVkNPl/iA766FQS+cVflvg3b1D2gPku+AUmovrFG+r2q056+DoxbPRFAnj3AWgc9nBCxvZbBsL00j1A+bVWZvkPdAT5x7a++ETqFviwe870skvO9jRctPjvl3T1sf/K+lMoUPnNqvD5ukWQ+LVl+PuRQgj2ejJy+9Yspvtmi1j1KWj8+U0oKvnzzF76rhVk8AgD+vg1oFb6loL4+UaZ4PpbPXb3CYZM+16QlvtsZK779aAi/5TMYPtMwsr3are0+jWWSPYGIWD1jkd6+NFuLPtBahD0QBrW8DGwlvxIWhj3H/7Y9Ntf1vGdYor1Iiok9tVlLPtFytrqYm6I+86ggPtq58b1v2la+QRELv6zXmL4Y5As+GoJyvSBvn76Mnti7AICgvpGO2T3o2AU7c9ZpPiHAjL7C1P49br3dPn8pn7zZotY9LFVivm31yL6M38o922JUvY/jcD6VJYK+mh6ZveY4gz6vmNI+W71MvjHoD78YBqI+idFnPtozfz7W5cu8v8IQPybSCT6tVgw+gTfQvhwe0jx17Es9XTs9PWenMz4c5yi+Hq0FP4kACr83DQA9E9h3PTDx2r6XSI4+xNlHPp6zo72nFgY/IW2RvasnkD1fC3+9gAe+vnuyPD6PnRm+cyWZvZCUCD2Vtx+/t9S2viGaFb+dmsM+fbwhvtusBL5Qhyq+97r7PNpFsL2g7oO9+k/3viiGCz61GFu+rzCRPqXKtz50age9B4icPNKIAD7cUGA+76gCu5WNKD4DGgg964tqPmm09D2hLyq9PpdlPltd5L5EKxG7SgHoPmZX3b6gHBK/QHMzPiRXWT7Bs7S+hZ6RPnVvrL7ji8a+CPTOPISGBL7EFGq+v+H/PKx5C77bxeC9dJ6ZvSOSpD3AZXW9np8bvmHwz77WngK+IrCYPk3V6j2+5nS+vHbZPadYg74uXIc+drUhPu31Zj4Nwgc+/ZR4vFCVuT3Vfru+S7EcPV8YrD6HLGk/MhIuPtsTgLvbmr6+lcK1PkousL5RDQ2+02SdPKXEu74pu6U++hWUPk8kH778m6s75yKEvkrVYb65KP89LqZrPvR5Hr4sqlk9yGVUvgGaCD32w429cWnKPTQ/ET4XWL4+xLY7vgY+DD3oAcY+EeDwPqLSSr74PAm+YAuIPswLNj5RgZu+lbajPdyXxbyK5Ak/yYpYPXxTkL1ecNs8jZkSPlT0OT4hfRS+EwhQvNSJjb48qq++pofXvqs6yb6LkSW+6gddvr9IGz2v04U+npGOPUIujb0bSEM+S7jPvp4P5b6VDMQ9utdQPlSEjz4Tg7W9TauuvnlqK76r6Cs+jx+Gvm5xKb5W8cy+NW6Gvhia3bzxRWE7zPrjvQ8jgb7NeC+9ossnuRw7zL5nWQW+Ru4Mv/nYkb4chre8bwm5vD4BMr2anmC9icIAPi5xnD1lH429cMWcPqxzA74HOqQ+jNSoPRJvbb5AsnA9apxpu7Zhfb63iTO++gP3OyIyZ75XEEI+hduEPTuaIj0rw4M9KBOSPoZZij4P+as9gGoRPdYF7L0xX88+AVw2PbbZ+73lSLC8PdmavqSW0Dr5Wc48AJEAPz4sZ77Sp3U+8ghMPbNhkb79hSw+6TyYvSHhALuTcas93/ySvk8+lT4xsQq+fFu2PmMT/Tykfns+8vQSPkGGnD6DvR6+XFllvamBDz50eT+91AqLPq4bq75FlGO9khv3PbMMur42AOI6HKarPkddZz5wcEq9z4lqPiD7ST5iFqs9Hoa9PapDKz6bUZK+TmC1vb6nbLwfZRU9SvDFPuOqjj4u4D6+/PdUOwCdljzbagc9DvSpPbEFyjt4rmk+yHz+PNaVJD4yoN89eFqkvjhYoj5DBSK+tCqbvqGOrj2aCUS9GPQrPqHM+b3BN7i9le20PnuuLT35yNQ9Y8ulvlFHUz1RjJo9PTQ/PqL13roJpfI9ywqJPjC9lb6WnKm9xybAvd21wb7SNe88jLX6vUF5F7zSmrI+FAAwPuEF+DwI4dM9+Ab8PbmALT46yDw+E7q7PsN+iLxj88291ggRvLTIhb8w1Tu9SVOuPQzwkT7WNg6+CJ5qPrc3eD4i4SY8VUKIPj6tuj71HIQ9F6uLPHpYgz6FEay9RkfzvShYdT1TxSK+2VYbPl3P+D0HoUU+6V8bPmesD75CtKo9YBvpPTA+Fb0GA+s+z+ctPRzFlL2Irqw+p3qPPn5YNT2lLDq+SpwLPr07ez54N449IExqvVARPT2jfws9egEwPs4w+r65kJq+W3SJvUtKJr0OaTS+DG+jPcgoBz2g/1Y9wrBOvd5v4D6KU5G972yAPbh2zz4UgLa8JGPFvik1Kz368iK9cuvrvOKKcz4Rhhs96ySWPezXaz7eK+Y9/WPePJ8rnz1L2IU9lYmzvaPE8r3G4dQ7TEx8vvRrpr5F+qs+qH59vRgTy7v60Q69HAfGO1AmwDv9v4k8/dJUvkJsdj6i/Da+7s+IPsGp/b7RVIy+GCiDPk6uHL1AajG+eWPGPVo3ir7UmKI8UWsSv10077300Cu+EqwOPtWMZz5O8GG+0LHUPvKHHL7z5Ae/0Usdv4Jyyz6DJ7m8nSYrvrW9Rb5/Y5C+K8OyPjBtsbxhqew+OHZSvQ9aG7/CQ18+1rLCvbC6er2tMM8++0aLve2cmT6A7qi6EtJGvr8hBj5d0R6+wGCiPjLKfT5NsYQ8D0EhPkRHFT52vpG9P6xsPjBhcL0P7CI+aUR7vorO1zysBtw9tXZQvqwX273mZwy+QS5BPhCHPb7Tlek9yhnKPhn3vj1/bdS+io4KPbVbij5DGJS9Un+TPmY3JT69b+I96ECGvYdqBb7gJoO9bSSXPHSiDD4PPuM9Jg6avadmnzzyhdI9wl/Vvq6v1z1NhsW97hClvA13rDv3ati8+X1ivqIKvbzIrb29sPmQO5I3mL0cm2m9DmdJvoeBk73Rg+K9lpGCPLGAvz0vJ428yWfmvcQwvb2Zuqi8M4mCPSFPsz32Wxy+Rm3UvdE0Rb4GJsA9qHAXvpUMQL4ocOi9CvcKvXwj5LzDQ8g9TfA4vm353b3N3JC83ujuvRgHYj2NkeG9WoIjPbf2Gb5oAzK+EjQNPCLo9jysxuY9BThmvs4TFL0q4/C9cwJEPQb5jz2LjsO9pv1EvuELSL4CQrM9QEGWvUHz7r08qHG96Yq/vjNYpr3KgxG+hL6yvs05zb2yVyM9tVGlvf/CHL5e/6O9k38Pvs6ULL6IYtI8Km6NvXXdqL306SS9cHrtPFYnJT2VTze9d1Novm6aUL5aghu9+z80POrJar2Iz3a9k8GyveyRwrybWDQ9+2iVPd08Bb4Xdz+9jFvdPR0oRL7qfeM8IuZ7PU7SFD1qGma+x24bvmTczj2LJUc9/e71vcdWq75g2dW+rDTbPa5a5b3xQEe+OsS9vrwmUj5Nmsu8IfzXvuD30D14j1G+kZPePqsAZzzWFJm+DowPPUw3ez6WP5a73AeMPgCpnT3a+YE9r1CJPmTbE77W1TQ+DbJrPJ2hej4PJJS9uNoQPcf7JbyWELa9kWbxPll5HL0pQsc9kicFPrT4XT5pDaQ+yrASP8eiib7AoQQ+7EZJPhJmIL2IOCi+WhjuvWCsej495z0+sXPGvTNUG76tn5s9o5C6vXBfFL4X7KE9AgJQvronOT4uwiU+LPSgPuXW0r0/2y89weFGvkcS5z35YGI9woEnPpmd2T5jYSs++cvjvlqs5z0iEOE+VMkrPZPpvj51Srw9tQ6Jvn1uQ76gFBU+UoyQvKn0Oj2jA6G8FCbDPZBjprzB/R6+jWCNvilmcL6Simc+ij3xvt2uNb9S0Ms9x8M3vhN4ij73tKM+eHFWPUnXHr6FsMi+0tbBPcMfMD7TwtA9prKiPtj3jrygh5c+bMkxPlCt6z2xDek9sHyiPY/iLD0LieQ+L5DBPbEPIz5QGA68AJqvvSCAe71OlFO8mQarPdZ9ur6xDI8+vX6TvglIar5jI6C+420wvh+y6j3RCWy9bZgAvngzuj3TfoE+geDOPbtx7T6libK9yJcGPtyko72J+ma7n1fDPtENob2Nl6W+0x1TviCoo72aARq+KGhMvH/XOr57hfG7HRbYvVsaMr5/mhg+9PsePQ740b0aCAK9HdgwPpwyDT65+0g+4+jpu7GApD5BM6w+ESRavWASCLy6piE9pq5nvn2/sL3B6pu9JTOLvj0XeL6Sh6G+PrWWvjiSP76ZcJA+3u4tPnvUoD79IYC9IASnPSaP5T74km4+YnDVPJvzh76ZrwM9Tqa1vcFwU75l52S+0T4IPt9P8T2ABUC+OqxnPv0xIT6NHgG+xywnvlikj7zeL0a+fWHLPVaXqD0kH3M+bFLYvoyn5L2rkAg/r6IOPXQ/Ez4Lwgw+vN35PaZXgr5kCgW8wyiVvczYdr2BQUE+uqTLPrC1OD2ntlQ9YVPXPBaz5z0FoFo+ZOE3PkMMiDzNtM69wyyLPpCIYD028r28qH23vVLukT7dhIu9GbFXPnvHoj3EBlW+9IHZPc6fCb51eem98npcvNzTpb08FGc8a4SMvF3JKz61Bas9lSYXvybF7jxmtEC+Tgq0vh5+7r1wlyQ9PBSZvRAD7r13o8M9tukmvXb6er4xUGE9N8gcu3z87j1p7HK+PJ+zPlFdBjwHQL++1yOyvTTxZzrBgsY9HCTdvZlVhr7/xCM+nolcvmorcr4f8FU+yjefvUtxVT5EHlw+P369vYtOLr7cBKA8ZggBP8qCJr7o6Fy+YIqdPkc+rb3AtNg8lUqJvv7Qkr7ptLE+aeVTPnoiGT7nVoE9YCRxvKgz/j48oIa+HrYcPeShgLwLkjM+4WIHPo0Qf7x6Kw0+H81OPluRBT2mVwc9woFDPkf8GT2ceoY90/LjvjHoDD5Buqk+ZrtrPqiofz4pp/y88kLWPQQtID0gFMk87SynPkyCE74prgE+imomvSNcS7uHaBa+skJ1PCMDEL77Y24+91r1PTi1cL4xCUm9HkbtvScIYr5VXO29ijOpPSdA8D1kIsi+i1qDvN6bOTw7gxy+gkBCPbZRBz+wkCo+gJJcvgw9Jb6n1lS9t2crvte5CT6wDPW97ufAvS0E074Gtau+t4NCvpEOj71lg72+4YbPvof7n71usng+lAxxvfEjlr33rje+AUEzPWSbCr5aY4q9Pdq9vWQzwL3UHK29ke79PLnUM70bxBQ9zJHaPBhw8jlEnus9t5Favp4t1z3vcN28kQGBvSDN+73E4i0+cWTOPY+W875dCIO+JzGYPRBlUr7H94W7FVgAv2SgrL6Jrj29/8H/PJGLDD1uxlw9tf/APhVfBL4dGfK9dXyevp3h0724DEI+RILJvUhAJT5CFSI9CbY6PtRUKT6Zvwq/gsKnvblg1r5GQIS+I0KAPB0uIz5JK4M+UE4DOxGRx72h7q++bvIMPrjGv70jaQW9EgQCvGVljT1Xw029oC1gPCxIfb0zJSS+MwXmOo3RmD5oVow+/pSIPnV74ryDY/S84MqFPfOOu76IMAK93tqbO9aEqD7nYGg+DJVIvgmKq7yCd5g9tKmlvIeekT70Rju+GfwBPvBtX72bCNy9+CuaPlvAXD33/LG9eKIsvlT9uL7f4yO9p+ImvzrrOD4KomW+cmrPvoamJj1McgM9wq3BvJhT0L0Hfcs9iIdEvoSqLL48OJ69j+Ryva62pT3GLwc9yjcuPQaPDz6F0IK+NwGlvoelMb1jbRq8laAwvqeypL66pBc+rFMWPv7mDrzP8ZC+gZsqPR+ynL3BX5++vYsTPspmoz28KGi+Z+WsPpbVir4dX3O+CmZdPv/vhb7qiRM+aUYLvgoOQDwyAkS+xu6Pvc7ZcDxugi6+vCcqPTc4uT6t0Cs9Crq4vdp9+D2nDQ6+O20DPilrlD6Rbxa+yNc+Pi6oJj5ARwq++V+JPbXKur4axJE9YQyTPlQfrL6hsCK+GR24vfAGEj2CI1o99Qu2vnRTdL1XdhU+n/JQvioKj71RnWk+Rz6APgpFwT35mNK+hBgKvnMSJz6zpIS9p/YbPonzFz8f/Rs9n7B2vnXrIr0nHqu9uf+gvdZfSL3dAQ89LlLPvZbKBb5++Ps9gjNbPQq5/bxObzA+rv9AvMaxO75VaYs9kD14PobGgT4RyQW9v2cHvtwVVr04gZm+9C6iPeuJmj0daVc8ZouEvGR4CD66tjO+prQuPfqSxT2c0Ky93jKxPXcFlr6K2ZO+Xou6vlULkz5kqiW9U+uWvSOBob73RYQ9E6QbPaxylr6ktQo9nIKtPQp0qj1vBj68T7n+Pf63Jr7dAfc8AA5LvnxjPb5G4Hk9zbNuPuPS/b0iLp8+juxovtojqj0tFiw+rMrpvmn0PD5Cut88nsxmPFdL8r2+iKW8dbXmvd18nb4xk8K9i6iHvroKTD7vgSi+DDoCvpHrpr5cXT+9HhTsPUFEBz5sc2a+62XrvVPnQr4B1ko+Upc9PY74Kz2u/ke/5YW8PtiKbz4k5JA9eT+nPX0iCzxLcVO+auFuO3CSiTzLWHu+9S4Iv5UwL70Eb7892ui1vV5dAr3p/tO9HObgPWhip7z2h/a968INvmD5zrz6Tk89ls6kvJmK37xOYT8+KkPUPfHRrb0fE5G+Zwv8vIbxpj11iDi+ZMVLvgjgnj7/xw0+SppVPtsdZjxBgw098GziPessS778Ork8bAfyvHaalju2v5Q+r/xFvqikKL2Ev4695U5CvduBtj3VDKK8qYEivyxLM75O7rS+dKt0vZbTcb2Z7AY+S5d3Pr4Fgj5X94W9JuhlvtSeLb4hT4A9Y9YOv93Hvj3GYkO+H0SBPuA1jL6+0na+yGTxPOJ1h76ztrO+kO8CPkBVoj06L1g+mWTTPZ+CPL4RWFE+FWREvioB/rxxHhm7UtYCvuXvrL1NlDE+9rwxvOaCGj3C/TM89PkpPf4owT3OU4u9bX2svQA/gL5kfGq+1E+ePGMo5b5VMPW9m4SXPmN0bb4wQ7y9vzjQvsoBjb6Gy369gpyyvsJJib4YL089EffSPb4UZ709+/O9EMzKPvYVkDxistu9lxs5PvyoTz4s/Yw9INOdPlfPSr4ug6y8cPJGvp/wEbwvNFg+12U0PpXDr70lJwq+iHCbPeTRvr5ddZe9h1FUPhHRJz2Seq2+V1vSPUPwRz5a7dW9c8O9vDH2M7z8ycA9idh6PgqGgL21t6Y+/IGBPn2jtT3KKJg+ZzmXPJxrBL5VO1o+xieCOmFCGj7R9EC9GWAbPfkljT1ps0a+7QkqPnMV+bw0NtG9Vz6LvUWvNL2eHTC+0Cj/PVwqCj1BVqs+sHFkPuwHZzxZQ/c96zUEPhyux73NhZM+QB+bPK4YS70BZAu+RY9iPjtR0buhORq+sKqGvYt4IT1hnF693TcQPkcpvD0ZsXS91en1vbgNt77SB5u+Arm7vo94hD7mU4a+HvYAvVSqST0qGIq92IVwPn7ddT7o2IY+jn/hPq+GqD5FexG+td2mPU6D8LzBaaG+pGkLvaBAez7U4nS6duYkviQKHL5MKdA9y8q8PeCO0T0jlb2+sV+vvp5dTr4odCQ+LxgFPyQgNj6TTTA+KjfqPDklw718dxy+ze7EPaifpL7EmFu+HWJgPm7TBj7xLAM+LtzsvXkAdr5SPxm/MXhiPTLLdz70yVy8L5hBv1WI4b1pW8a9OfrdvpUggr6T3zG8qdO9POJe7z2gVHq+grsCO3Cq2b7loqo+ZvYBv3zHjL74YgO9FD0uPNp8fL7bY26+K+73vRuKYL0bKZc+04poPn4xJ75c6II7oCwJPcHzbz6Arac919OMPhGx1j34OAu+Z5CPPm7PAr8VPFG+Mr6uvo4Twb2gBLG+WM26Pm1Xzb6Mtzs96ALHu+QdJr/XtdO9M/7tvq4AZb4ed8e+ZEu3PanRhD0S/QG9cMqUPgoajT3rddk9TAPSvXJNgr3uaAO+n8oYPhijyL0NssY+s0KTPZq7hD00sCg9i5+lvmHHjj7l3BQ+KfZjPlFYcb+gb4e8TPiCPpHqWT6AV0Q9MNKFvgJxgjz2uRG+JTTVvo1lk7yF0W4+rUwuO1ijgT59lvy+EpvZPq3AcL2Lzpi+lPbcvjVZSr1Q0aY+FG0DP16xVj35C/69yKhGvCcmZL6jD0E+6gq2PVAulj3ddzI9gagGvZYtrT7t2kc9W2wGvimgyL7Cmbm9wUpmvLF5bD5mtj6+gKKsPcPBRj7jB9m8281kPO6S1brXnQe+CeQlvrwKpj0NQuK+BAyIPgbWQ752ul0+sT5uPox0hj0GmCU85It9vliTXT6pGZY96CKBPiJm173lfYs9polqPpzi0T2bVd+9ysM3vVOEdbwx1Dk+SzrfPXCKUT3NzMw9emUfPECtGjhaMVk93wuXvdV3Tj5nRC89yh66vUI+mb4FiLg9PkW4PbFLlb2W9au9jauKvdqGsL7EbQu/7QvxPTDWRjxA9UK+CaoxvmDhND7LuXQ9bn8RvvyYkL53wCk+LAoCPkGrhb3Y+yQ+JixCv93pR76OvPQ8ELcePpSwl759WAc/DBQiPoSpdL2UXVA+WkhPvgY+B7/uh909VjDcOoISTb4VHtO90jQwvdr/Rr6s/JM+EJcPvrN3tD6hSIg+F7HBvVe0Bj06ir8+RrNcvfduAr5vvCc90f++Pokwh73mzV49zsOAPAOFZT1M0LC9njpNvtyjkD3tUzg+cA7OvqD4rz61kVq+zKUGPqUM972u+5s+/aMBPn9nIz5/jay9T087Pn7kYT0Dr8A+eexWPTp8Zj0NpYs+8KsbPnMdgz0s6wQ+CeBcvt8M971maMk9ooKrvkCxvz7KNNa93kHdPb0aCL5Yyic9dHtovAX2M77MFOQ9ErimPug7JD6rg8s9U+ylPcOfvT2YcHu+I5mPPTv3Ub3NS2Q8QRozPg2NrD4WgRu7SS06PkqxAj48EVy+wKwivV6xgL5fkAE/U9CUvsKpOj1y9Se7gfq7PZyhXb1dsWQ+mFb1PbrICz2Kbk69U264vE/6yz0CQ/893RepvsZDub14K7s9lA+PPnP0Kr4SJ4q8ZtjUPdltl7umQwu+iPmtvUIYJ756egw+bjhtvREUQj6aLg89pBr2vfOM1Trk3o2+6as5PjwFfT4001o9fYktvvjn4Dwltic9+gfnPjcxCr4raNw9MFGuvKIHX74V8qa+IK2hvnM0jT7PY8a8HPo9vZJPLj6Ow5k+sZefvkR/37zNtHk+5SQSvpWLVD70v2++Bv3vvXScPj7Yc7W7e3Mrv8t98D1y+cU9lvX7vDfMhT7ZIoe+W6UNvtNYCTtTk5E+6d8fvUkYuL47dDK+6eAKvrKHpTxJkPC8juo/Pssd8r0ZZCU+MLoJPmeJl7yf8yW/obgUvkPIsD0CsUW+vy+TvrAf4r3WTok905wRvySq8LwgMxI+cOVlvbmBiL0TSWg+vLqfPqStIDxD+YI+yCUCPoLkRb6D7ZU++D4RvqqHwT1UM/S+7259vV6SDb9up1U966/ePgTaFz2oR0c9CcsCP5MLgT2Gt4M+Hzm2vWH0pD226bg8CnVcPePHjrwArg2/+KQBvfJXSj2lF+a8l5yKvvPAer2GCJW8TKTRvQZEqz2fgmS8AKsTPmjhPbwleEe+jqhMv0wK4ztM5WO+H3qnvvoV/71Fux09qAgqvq4ujz3fGs+78CJqvsieL77XmgQ+k7nNvfYxRT64qMk+1BVsPeT55L1+lM+9GBetvqYZQL20BRu+OJZbPth2BL8j6749rG8UPdGTIz27Zoi++J6EvZDuBr37e3S+U045vuRAyb0WTjK+JPYzPYaBr74AQoA9gnCovnwFij2eDZa8Bv5aPdmPvr2Q1p6+Izr7vSDPoT2dJhs+ExKfPlHS0bx5hiC9ZgSDvuxm9r5oZAa+kbCSvmlB7TyKsEG+xE6pPc9ttr47zMO+7XqYPpPYwr3gz9a9J8aqPQWXBT37vDg+fr66vfcDFr8vC/K9vDYqvi/8WD57wzC+M0fXvX07VD0MhJQ9vHQ1Pu4p9j0AHq8+oGwZvrt60z04ROs9MbNqvv5GhrqKppG+Yb4ivl9r0r5vsEy9vs6BvhjnhT2cdMq9Rqe7PkymNz7NsUk9BXB5vutjyD3Cgzc+ULk6PhGd6jxSEx2+YNsbPvqk0r74rI+9ha4SvvK1RL7yHQQ9+3PCvYSYIL61zug9xIfzPAOCmT6D0qq+3adbvd4SzT1h3bC+iOZvvlpHVD4cIHy+tVOZvpDNlD7OBm69THPiPZV8yr17D12+nT67Pqgv9Dx8MYi+oYx+vreOyzz2PSC+4cUdPhaRwr2dtwA/r7PEvvD5kz7R8Eg9PjqEPAHfab1nLsU9GD8HvRrfdD7WKcu9GfUgPrZniTzk0XI+Xbx3vTzpmr7WgGy96hCHPtuKR75L+06+oug8PsCpjL7MKA68yk+pvokK7L7ehKk9ZKvZPbwhxT4Mq50+LBJNPdN0MT65iaI+N+5LvmxZD75oF0U+rJpUPS6CQz4tKxg+p7VCvkt5gb7yhxk9MgS1PatPlbyJy6S+oBctvpRgw71Bz5q9WCnCPtwdxj6ACQQ+nnZgviK/Jz73tJi+GByDvXgD0z3TVG4+6D3QvgbPw76eZS0++0CIvS6wIr6VXLK9IN+Tvi6N4b7BeqU+2ZC1vumByr5qXIO+elcivXrrUL7bbO493D2gPS+AdD4ZWIg920EHvrQuFL55Rrm9HHKePq3JAD/+J3a+LsMmvookWz5QZfM9LQxrvkwVyj1pFYq+3n8mPTxCRT3VyX0+qv1IvddZyjt0lzY9oBZXPibRrz2IHA2+rY36vERxvDymaYu+uBoVvy3nW70X15s9YYqfPQNwmj2EyoS8fbhavqRKNL4HdiG+YpwHPqjhV76885c+Kx/Wvck3iz0C5/e8XrORPpDubr6ED4e+1StnvXMsVL5x8dG9BX+VPvranT4fb6A+WUkIPtISkTyO3Ie+O8hUvgdx2D3ME1e9/+jRvCMKRL5vZ6a9FXsSvpLOkz1yTwE+RhBovtqN7T3LIFg+UwUqvvYEqL2ryjK+mlyOPuZ9Jr6eEKm9XP4gvhBuU780BFQ+IcOxvfCdwL5l7Yc9WVwyvut0HL0B7I891wfAveNBGL6ds7U9M5nDPRpDmL1rKhk+/cGpO4nLdb733d693kHLvRKujr62gI89pYEgu7wyPj0mHjY+J2zfPKlD4z22EIU9lh5fPn8n/L3EIPo8vHUePT0BMD5nCgW97k3jPRW2or6wgYE8E38vPHuTYL5cwow+AyK8u7sTCD6PjIe8gmChPpB+gb3p2A++BOOpPXl+9b1EK3k9tjTlvfsACj5mWbI+9d7/PWGQPbzk+TM92uzqPcz0Kj3dzR490RETPqb9oj5AQzy+mQZtvEKBC77PbuU+U/wNvVBImjpdpH885hbWPae4dj4JMQW/QkMYvXLFir4FYAE+H8e5PHXo7Lywtzw+W+y9PLWs2r3f3zC+faqfvlOjCr0Ik3Y+/3oLPlZwkj7QhXm+Ti13vabJnD6qHIQ9wyCbvsb1Ub0LDjk+GWtNvXP8zD1gGY6+Ijinvouzlj15iwS+CowJvprzljxbW46+9c8TvmkrrTyMdne7jCSivm3Atr3C6Iy9bitWvocDUL1i+xy+5ggWvQGxqj6hLt+96LydviZ0HL6hu00+AC6avqFXzDxPiAW+KgGwPchB9D3OnCM+Wm3dvex2hbzAyw++XuihvTfjAb9kpZI+N5SGvl0RbT4f/KY+LJbPPmffgD3izOY9J5sPPpf2Qj2yvTA9qgQXvrfA/Lx6uu49WJl8PuTChbxMY5k+czKpPu9enb5e9b69ysaHvgyFkTxc49K9bffiPUgY8T0vfbG9+wsoPjxdIT4OTFs+bmskPjpauT2phpW9qErjvL35uL6UtF09HlvBPp2tDT4E9Rm+TlQSPvK6rj250oy+nIpHPHpmFz4WtB4+pU1APhoTHz7Lb9a9Q28Gv8ipqr5iqGc9aJurO0UAiL5Fggy+8W5CPjlXA78VvR+/xWAwPmmnhbxZEpm+pBT3vmu0oT0HOfq+rwqkPfJbAz2h8h8+h2+PPXgrOb2PN3A+GsJKPt0RKz346xA/ej9evgTCDD5/wyw9umJIvlWJw71TjD++zwRBvuqkALvb7SA+XKKNvfoYDj404zO+gI9lPd4tLD7sHDw+byRhPRgIgr718SC+jLxvPrCBQr5TiDi+iR6jPQd5AL4DCi4+pcmHvvm6sD4CAV++XSk4vtS6Hr6gNVo95x3CvOEYpr6r4Lm9PbJ3Prp1Tr1kPpI90cNqvBcnTrxjnXg+p/sXvw31hr7MDj6+F6W9Pchn5jx6hAw/ZHQIPd/axj6MQi8+K7xovm0LLz5tb4M+uX+QPc7NfLyUcaE7PGnIvvJlA76piOM9i57DPG0Ht76Y31k9KnUCvqzNH7y05Tg+tYvPvY56PL7hhwc9xhUWvkRIqjzag46+cGnEPGW9tr2EgIm96VcGPTqUab2B2gi+ETc8vjTSMr3Raws/hQk6vuRzAb675Ng98miKOwGn7TxfMBO/0JuLPYAxpL7kbkQ8QuwKvhxJDL5dWn69AVFVPiVzaj7yI6Y8MxKWPbeX2L3nKEw9qRkAvtsnezwF83M+YqmyPWY4/D3W6QO+gC4Wv3SRvT4DPBO9HRnePUsTlr5XUBE+th78vtLEuj7/ei0+adbFPR9Y77640LM+BR7ZPM/Oo76Nm8W8dsgOPtjMoL6SUgo+ea71Pb2fwz4gUoe+rVRMPugvHb2fc8e+KgPIPelqtj73PcW+dXqJPUDDET2SuNK9JxA6vcw8y77P7ae8Hg+YvQ3FJL0KVHg6ysxnvlYahr1qKF6+7Q2QPjDfrz04SQO+pOWtPYWHiz5eVTQ+BCL6vhxuiDzumgm+hqtSPYM4F72QKH++zGU5PgEpKLy62yS+NGW5PCApTD14xFE+lZ9uPi0pz75/C868QZFhvjkOAb50xfU9X0ziPc3z4r0DvAS9PXjZPWyU2Twz96O7C9uCvfhbZ77osss9kXtkvqDdOb72v8e8JANbPYrRFL7FNyA+f/jPPBwXAb4Hgb+9NuIGPR1BHz3ejQM+0USFvrAZnr6XPrg9fQu9PYYXdzwvKAw+bjy8PeehYb6u6xg+3cvcvbDYyD3b0Ig+wbJLvnpzdj0LpoG8aB9OvVtylj1Il6a+grWAvQrdlz218+s9CF7HvUCXMb4NLWc+yK2nPVkPBL4lGh6+RcrMvZkZUT1yuBK+KQUgPkXuOzxNW489lhCEvmMUN77Sq4O+UY8OvYyE3j1dSZO+6k99vgyxfrzCHt8+iEDSvHCsAT5iZNk9qJ+nPf+4BL7+iqI927ScvhDPc7wXyZ483riuvSFlzb4/ri8+kiGsPnmCEz76YNM9kyK8vfbqjbzyTC8+KzgIvuVaxrzjM9m+vHFyPehM+LxSv42+aWeIPeqNIb5hnIC+CKQIvplpMr7qCIA9MH3QPUMXR7sADX6+NVNZvkVJH702kZO8pYjkvZAzir0rwbY+es9Vvbl/X71xFHo8LB+OPuJuez7W4oY+AUOzvAEZhL4262q+ly1VPT3kJz6+JiW+tEUovsC3gD2Nsbs+Vczwvsfahj7MNZk9L1lIvmq9HD1L5rW9ekgAPbyOg77Xw9W+oUbTvTtEsj67on6+in2nvr4RA74I2nu+FWMTPk/Eeb3bZ4y+onXAvWPMlL0Cnwi+drShPgGoib67Kvy+cgGHvQtoTj5yvqg8A29uPZlLM76jSU28qqkVvDilpT7pqqS9CshJPtfySbvN2qK9p6SCPLFTc75odQ2+BCVKvdfbBjp1o9O9C1JBPZU4mzwZrgo94psYPhi9HD4lMAS9KhmTPUReDb6XopM9VIijvmQB8D1y57s+fd0PPqz7ULyxsG++uSy8PKEm+DxWmem9w0NFvSbXkr5vMdS82TpYvgFR3j2MeoU+GhHcvZIMGz6cNTU9qtVTvlnd3b4692K+bpvKvFRQy72pztw8kYZCvujE9b2UeNA8NnvRvsp2g74NO50+ks7wPWYOij3ZdGs9TwMWPfwAXD4saBK9vUAZPvdciD7uLVi+cGO0PjjM8b7Cloc+fYEzvWLIeL4ZRjs9UMwDvY769z1kSSQ+wWsrvf1dej7BloI7G8CovZ+G9T18fhS+J4tQvU4UzT1sM3I94Ob2PqVKjT4DkbK+zU8zvs+Urr4AV4m+IhYZPhZxob2Yi0A9gKxUvv9zUT2yRZS8pJeOvfLGzr3NSNM86khPvdabAz6o3Fa99VUQvgleB75wjWg+pWMFviBdAb2nfQM+8U7JvlUH5j1J5Qi+93tyvqQX/rxleDe9ojI5vKXKQL4EjcI8M7PgvmoRprzkF4295M6uvkO6wz0xFYq+mDicvrqMBz0k/y++JBSCPtLUy70qQ00+5WjVPQg86T2Pihk+wgPhOzD6Jb16bpM9ztgePphEJzytqW+9W1qHvlxEBz6WgGK+oH6XvnCW67ztuvM8ISbcvbhKmj3Dz+o91ylwvkjjnb2Uxr48OA0vPjx2Rz4zeJu++PKqvRi3ET7f8Xc+2Bx0PvM93r0MIfm9NyknvljsjT25xfe+SiIGPsACjDxIz909OcSIvqdMNL5DTHi9HUcavmVl0jw211q9D7tQPVX22Tyi4xW+sUSFvUkwnr0SqJ49KM6EvMOmdL2HRsU9Z8RJviy3WD3wYm461UYdPmZkAr1s5/8953qEPh+wI76a78s8+qtZvrxI8z0NtrS+MUOGvLsnhL0kPQg+2DccvogJYb6UUiE+LO/0vd6+Vz5x5Zy+20QYvl6/vDwdRs2+040hvupl/b3EN8e9rgUBvvqT3bxpjms+mIglPurmOb2x41o9pt1bvtfXQz23qs296MAhvuGrxT4IZuu9wNPMu5yim76bhSe+y1+iPtwNOb4zshK+DCU2PS3plr4mZ1s97H2FPhZnnL1ZJ2s96SCqPQTzP74zG56+4F4OvaM7dT4Nn4Q8G5rFPZlzSb1yd7w+YnEWv/ORwz31HLq9O8oAOuUc570f5ga+maoJva/Ukr1m9/u7PPG8PSARCr4YI5O8dApNvrDG7zwS1Ys+WJDvvRs1g74i5l0+ccagPujiD7xOcOY9nO3Ivdmlnj7hGMK8p9Otvg1PVr5NlxO/bUAqPloSbL7EITC+8PYUPvixaD02y768J+8UvQ9oVb2Ow4e+6w3pvUa6Pr7unhw8f+jUvr1fCr3Up+M9jHgxvQtaxr3yQwM+2+LjvWUTab5o7Lm93MCNvfoaCr7kvhU9fLcWvvrPNr7961G+dc1Jv6DXpb050j87BIilPf4+fL5ShYk9VWJTvrlr/DtzJac+XQV9Pk4fzL4eN+e+MdgmPVCGOz4wN1O+wvI1vktTIj7eyog+6C+UPN2h1T2Ejk++GhJWvUr6Wb0qdq+9gT7+PfkFsT37vx4+mduOPcANqT6tpBK++fZSvUoW7r7ZyW6+tCsuPn0ZZ749UCe9M8bwvect5D2VgRk9aLOTPec64z0Vof27neNNPgfFvrwByTO+veAFvmsgxzxy7d49LsRYPTdRST4snxs9J2g6PSsIy75SV748Yesyvmv42rxfooq9Vtg6Pm7CJb5kA0I+dbyovU+XEb4woL28dSi4viCLrb6ZPig+5CYrvorlQL0+OXw9bXygvClLvz3PoMg+I8mQvKFopj6tRAy+l8MovTAmpD75NpY99GW/PqzNZ77DKQY+J5MTPm6Plb02Wua8EUvAPQ4BnTzVjIS+AEwRPTW7hz3ToKo87AYavtTSSr164IY+ZkXnvccEzzygT6w8D3aTPtKr+rxEPh6/SNd/PWg6o7s3DBu+1t/zvuCouD2DTcQ96FcPvSa6fr6G+NI8XhJiPdma7jyO9aS9NpEivi89kr38ngW+xPBvPQmXlL7yqUG9lkYNvP3ivr3FXgc5BI6Ivo15jb5QzEK7HvsMvu27Mb79exa/NprVPJCidD7jTTo+HFLrvcKNXD1QIWq+LiVrvvAicD5gSq29a3+6vbPyHT6KEgQ+PXU2PrgbX77jWym9StXbPKKQT71e9x08UKycOvbmcr5uyeO9R0AfvTSQA78LR2A+kRStvhBK0j1qhAm/Ii5CvlMf/b0VpLM8rZCQvm7e4z2uwdw9cSY6vqYTjL4RbZm+PvOOvcX8Vr4yMfe8ijvTPnr5SD5pB6+9d+eiPaRcaD6UQIq9xISoO7uFJT60En68cmI7PcEKSb4GJPO9Y9kMOzaI5z28+Ti9et72PQBNYT7++Qi+pIljPaCULb458/c9RX7KPpVZ5b7/4Bg9LP18vrJVJ70910W+gffPvZTqSL5/mIW+c5UfPgR2K76TasU93D0ePjB/ID5jHdw9SgOJPtch9D2QaKe5yb4dvspOhj4gnAq+qvSPPufcm765+0G+lNkavl8L/jzjXoi9TaMbvoUKyT04FQo9/xKrPDlxkL7R4qa+qeQFPhpvWz0240S9PtyIPiF8djwNNIe+jMKJvYBktz5dlfc9P0LOPY+Oy77TxY6+tyN6vnU5rD65b2a+NDtXvTnwHD6ciUU9zpv9PTsj+L1KKZM+xaCTvuwVhD0XEwC+ghDJvarXrT4Lh4w9KWaZu7A2mL1vEd49xtaju59V+j007F8+Qm1wPDfScD5sF4U+EXfHPcO3s7zOZgS/FdYfPuUKbL1sgVM9n1k6vpUOOj4UCBw+hze7PdT8Hb23dxC8EiO5uu/6IL6d2ge+9SvkPN6Qf7040zk+NzR6PE6CrLzhxhE+bjG7PWd7yLwH+Te9LvLwvVSeTz3XK/s95juBPpIuFb6B1q89g33WvRwrq76d4Bc+KbKMPlU+w71GV+2+qkRxvusKib2mx/m97dJIvlDuWr3D9R++UcM3vj5z8Twuh508ipIpvvC5vD1N2zu+HozgPbp0RT7Xa+c8+x8evQFYGL7OQF29L99HPlLSlTx9nn2+aSJnvh0zaTyR9oC+LtQAvS+aqb0UQyi+fgo5Pt7hcD0piGq+o3uTPR116D2rEg+8nNgMvmsZhTwZVEm9RhcrPiGlmrwnEQC9Z1KJvuxWrD3Vdfy9kZfPPZOolj5o5Xm9y9K+vZZyGb5R80e9KM1evYIBNT6KCaQ8AH+aPsChFz4tGoM9IDyZvjJvvj3xiOg974qbutvkV72k5gQ+fLIdPQxraL5vYku+tokOv/h/UbyxF1U+X1cBvuLPz74PkOW+mWiXvo9vrD4xybO9hhlGvtm6iTw2H5a9ijWRPea+9LyAWHa+FG5qPuhQ/r7Z1Xw+GXDHvRw9vL6ir6K+PcSOPjP9ejxS07O+m7NxPiYaGT3gcuu9PO1WPWjCtD2giZI+CMKSu0Mjs77QSbE+uiffPXPKKr6TU5I9JvVfvgc4Cr7G1mK9Eo60vWRq7L5b4zu+rg0EPnmEID3Sycw+KLqrvvxCAL6ZwRm+NMqevmLASj52ss472zSavY9ahL1f32Q9G8qNPK5rTD6p1Xa8Jew7vurj2j2UdIE+MBqSPSsHyL0b/l8++GVJPiD4O7/Eyt29mTLSOxJ0GL5vhDu/L/w8PdLRYb5nMsu+MP1aPvWtsb0JL+O9qMD/O88fOL2zztK92rcLPbdCJL3L6E4+cP2gvgrfgj1NRGW+jY0bvtbXAr3NfKa+6gfwPNL9kj0C1gg+DMQePgGMQD4Rut29D4RSvrJ1BL4rGfe91/h9vTptcT26bT2+AB1oPTodhL4bR1295NsCvk606L1X45o+TOwyPlJ2cz1OeAq8dhhXvZ38xL6lP609hnd5Pj+/wb1Y9By8tRL+PT8OXT6kozq+FpgwvmWm0L2YPFY+1KOSPSUgzT7USJM+T0zbvZ7ucb7fPqY9DLqfvd7gyD15axe+/m3EPOrqPL7RfLw9EQGGPm0gob3JSkq9dbuUPqaVIr587Km9ug6uvtc6wLtnjgc8SKktvS1LnzyoZFm+BVgyvmmuEr4baSI+P+bAPj50KL6Y06Q9GlFvPfAimL22IBC/vVY0PmsDsbz1GXK9IVu2PZ4yp70ksew9vhqAPukFzz0kyrw8NhvKvTxAFjvYZB0+N4TIvkLxED6OCWS+jVYgPsg9Pz02tEg+mAToPaodRL0ST+a9FrsQvlm9LLzgOUA+wb+hPSPka74lja69OuQSPWuwRT5TDv892T9cveSY1b2MU5M9LfuiPk/U3L70Eos+/vXZPSXUAT6mpBU+DmZPvVfasr2FPHw+mzkgPrPulb4HqD4+ZAJHveBL6LzJc+09HtO8vUBpir4PkhO9L02NvkLXiT4ZaQQ+pfPWvY9sCz7hmcY+gG6APv+CUT1usBO+NJvBPYU1mL6JnIY9i8LJPsvPLbx1sou9Fol8vr1P8T11cns+d04evn0nUL65DqQ+hWvGvVSdkj4kRO890HytPpfJGr7TZkC+u2zAPteWT71QD8k8E1xjPvsmcr00J4i+M9sCvoEAX7zPxQg+FqwyvjvDHT4xoko7F7NxvX3d1L7RWpM9xzKLPnLh5D2TXWm+FoLQva9yEz4Ec9Y9n0DZvR7cjbmDC30+XkjIvdq73b1i8qI8A/EqPQFx/725mTo+ryTAPcTGRb7zj6Y+jqhiviZeejxSDAM+Kf1gPqPks765zX8+4+GHPm+7QT47Vka+FZebvg8ZDj2WO9W9yQrxPYEJQ74te6Q+qD8pPdEVG769TzI+PG6TvV8+Wzznd9A9DzaDPCXghD5aaA6+2IzMvnihoz0arpA9sh7nOiKvhb5tPO08/rxOPtkJiz0MW+C8O2uNvoafiD6H3y29uCK0O0bFiD6pd00+br1RvsfAdT5ExTI+xPLFPQrf1D0u6x28CX2yPcaS3r2KfQs9bVzEvVfFP7xF/ue9HbKhvc6+wbvQI3u9mMhvPdCzWr3d1Mi9FU0Qv32p1z0fu969lzAUvsKzSDzboYo+dFwbvjEL6r2eBw0+kYTBPmzg4z1Wli4+EWU0vm0o6T2YuSs+xqS0PKOwfz7/YwY9yZ+qPU4Tfj4MtKE+9iOBvvc+Kj7l/iQ9lqq+PVDgETxW90g931g/Pqinkz1/hFG+zv9xPWnXuTyuuY++7c3sPt921z36jew9jHDAPpPnzT39WKM+eTeTPtGrUD72Ih4+927UvUyelj7Ysyu9P+UePvt8Hj7P5ZE+DMw2PleECj4UqrQ907VzPt+lPD071Qe97AXQvhWeHj1gr3c+3cyXvc39F72rDyq+0LblvIKHtT583+E+aIvGPuA2lr5YN3e9mIEKPjjXJT+VKm49K3npvtb+bj4kO0C9Tl3nvfL9PL42yMs9BkBfPt4Hjj4TWpq+2tgwvgf1Ob5GO0i+sBHkPu7tjb79ufw9SwU+v0NoVD6Derk+LMb1vmqFcz5a4S0+1AqsPBlBSD3Xl2M895Hovu/pjz2Dyws/xaMZvlRcNb1+uCM+uNyuPl5GP7604gC8CERWvrX8g74Jaxi+LSvhveAGlb7bkgW/hRJavUApNL4y6JM+RDtTPZ/bVrn5heA9JmRaPg4Qy71Xnjk+dnONPsTLjr2u5QC+PvWNvpGcHz0SWkm9bzJKPn6/Lr0QaxE+e+UkPXASRD2uswS+OLeZPlKqjr581c8+fQw0vpmBHb7ORN0+OCCzvq8McD18D548sSfWPbJLsT0Hdos+iIuGPRgex73U6x8+bdELvlVcfr1oJSW+I2N+PT13szzNDmY+5FQgPQt3pr1i5C4+2qOEvZ+RpzxKsTK+qGrwvQiyHr34D6a+snU7PezzNr3sUOS7JdYwPYB9hL5/VJC+Q97AvQSSVT7favs8RPjXPRerWj4P8da7rB92Ps58Az7hCtO9BwaVvAtcOT+FBng+BbVJPvz7FD3nLZo9KxzPPi+ygL7e3oY+CJonPiY7CD3GSm4+c3tMvWE2Aj5+GQG9ETMDP4fAnj3+Bi+9P5EpPfzQFb44KFg+0NBXPr2BlD1iLbq7Sl/CPp981b0+FNi9xLozvAsiRL7179s9tIAAPhI3/j1lRaa9FR2JvmgV1b2Zs9i9L4k2PqfmXj66SC89nmxHPG5taD6k5A0/tM0BvsONo72hDGo9fqyjPYs9Bj57DcW+smkVvj5xBz+2Uf2+LDtZPdkNK77eqh4+SDi8vgAUZz74POc9NB+GProINz6kZ2e7UEMnvpGL/b5U9IM+zwymvsoeZb6Pa6M+nBG2vKekHj7R8ga8/I3SPYMgXb6Dq4C+UUnHPn75AL600Fe+FPc/vm6NsTscjZO+FkwhPos58j2A0q8+gsvqO5TrSLxcc9a+2juPvcW1Jr40wIc+FfOLPRXUyb3E/jS+E77GvQ0i87un1Hw9EzOfvU1Z2j2afWE9Jkyvvvpo073flRq+a8Q8veUh8j3U1T49wLfAPUtCFr3XoNA9/r4KPK5Bor5tzps9r0rLvRwDiD7+4p891rSsPLw4lTzpiIO9mOF2OS8mwL5TqhQ+TI9mPgiUAL5o4ye9E5BTPpfqXz4XuHo8xQekPstYND7UrMo+IXxTPispUT2LQSe9WT42PrB/Jj49DF++XIW5vdFUxD2sN0O+2T2vvl++xLzNaeE9A6F1PuOiIz4EVN89WGNQvuX8OT2yjvg9PximPqMoWr7qJR2+8DGMvr8jbD3fmw8+oxuzPUZFjD0xr9W8cXehvWud0jzH0jk+z+VwPRlUWrzvQt29oaBkPl/hEz3qpSG92GzfvW/bML7/KMm9bfgqPsY97b16H3A9+CtePu9zMLxQQLo9yNd6Pi+Lqz4aI4S+pLUiv7WKEz7gjDs6l7L9vdco2bz6OxC+EMO6vjTKN7042AM+DoOVPegjpj3OHxs85a/KvMiOQr5c3b+98f0EPu+bZT7uEuY94aa4PkR1OT12IZW+7v2aPj6QlT082qK9K2m9vgVfA74HNo09r+pNvpEIAr4hjua64OgCvl13Yb5ngBU9FeS8vQKx6L0imSW/t6DEPhDfZL303tG8jQaVvu8VCr31gNK9bemTvYoDUD0FW7o92b4zvvWfgr7p5KS8m8OZPvH5Pb4G/7U7bqjquk0x5D37Rm09XVmHvREfGjyxST6+UvXevfQ8FL5cQOy9SUeDOq0aZL06nBU9Yoa9PePtIz06N7w8fp0/PnOnpb41Fae9/HeyPcvmkD2mWvK+/ZY2PobmY71Viww+h2p2vW1ZxL1I0j4+pzVJPuHD9j3n9KQ+cZwGvao6dj0lm+m9Kjp6vPrVVj51PkE8YJxkvkvWizsiMu86YqpKvRRRn74+LPc9XsgCPcPdvL0Kloe9jsOYvBnPJ74TALA+LVnEvo67kD2DxIE+IOPivFnL4j3buam+UkBXPm8qO73iam+++XIOPjNPoDxGbo6+TQErPsAQnj0fTrY+dtslPjoTA73EMDa+mhx8vfBvAj4BPyY9HphvPvQq8T2mlG++lwCGviPQg7xbl5I9/kb7vNWEaT1wtgw8tYPSPEKmG75T6hg+3b7GvoYtsLyMd66+ynppvRzgpD6huSc9vFU7PlUyNj5FHAG7jEcTvqA2IT5qZQ6+PeSZPYxM0jzEx1G7WaniPQK/Kb3tw4E+EjKOvnGECb4PrRk9OxFqvqAWUr42yhS+S7SOPvwhRr0Io3o+4duZPjt/Frusi1g+WKZQvvv6Er7zchE+yeP9vZ78Vr7flbe+E2DRvgEcxz1VIo08cJ86vdu5pL2nQ5U95BKnvfVpLb3I+Ye+qEeJPM87Jj5Cx3w9TVidPbqT7D1bN0I+tYMGPeRpjb6KwC++jl4OPgcfhT6IFLy98PWyPCrnJL67xFO+MDJuvgtfkL5YZTc+LocPvov0Kb916jA9itcmv0+7MD7mg2W+wChzvqibDL51+4g+rRtmvS+3GT7dSdS9A6g3vfi4Sj4GFBO+Y+cfvszBWb75axc+o63xujhz0rwGTy+9ujyYvslz0D0TQ7E880sOPjEyUz2LHPy8O9MDPq+6Nz4AMp29yazTPfC2fbxUbMM9vUCWvcOnIL5lz0a/0l1hv9bvTL6nuZU+nCqLvmROBDzT1pq9dy1vPCz+IL5JrRy+JfUSvIT0nL6ZNos9RzuNvTnyy76p3xw9SJCxPQOsKbyhV/E9c7ElvnDw7b0Qdr++uS+avmnaUD6fNGE9PWFgPIO5J7x3xgo+6gJKPsdIk71W+Zy+1YrJPo+UZj7OSXG9vqXRvgJBUb5HMTI9mLxLPoU0l73uBIS+a9jbvbhk2bpRmEK99SVEvtaIPrzoEKo9aj0kvhymqz2OA7++c2clPvBGDr6nu4+8KCVJvqUNFT6B2/G+dCObvW5UFT6MwZ2+6MK2PKoWcr4/CEC8vxc/vrHkj75NCYS+pOCNPXjoAz4/d7I+K8HkPWY6hD2mUMG7GoMzvucn0DwKwc0+vKi4PgqRFz51doc+ZGXWPbnOBb4pnSo+z0vsvZiieTxBQHc+dsCOvkAsJj1yQ0e+xQ4MvtDA4jzIdYG8J9CgO8HHe70TVCs9YZyyvg+weryYldW93C+YPhT4db7lrPc9GbtQvn71Gr7K1FY+sgkdPm9xkL5RPBy+zMjhvrZJcL3tBna+2L4LvQgcgT33uWC+uUPuPhfzwL1XWRc+GqAXPvn2WL5V2Gi+kvqbvaX7h72fSxs93XCSvVJa0b7JyIU7bgfvvZVAvL67i0c5gX9DPnp80j4C93K+tvS8vXZehT42BQg+vr0qPfcyGLwsHvy9w7YdPmqOpD4MwA++3KQGv+Z2mbyrvJa9JR7lvClYbT633NU8aRlKvlE6377wrTU9uaJqvmVud72kcum8t2Jgvo7Ma76cVPy+tAWwvJBDS70H6I8+leADvuXNXb69Lm8+tBMOvg6nDD5Leig+EfB5PkF4Ej7qPQQ+UFqXPdgUJr2TkPm8CCAGvar76Txm6oy91kOJPhStxjx2Siy+qhC0vggUsD2gZ409cTiGvtyXYD2payU+C4zhvRDQJb+45wi+pb4cvgMz4r2yXgq/sVRTvYSNqb6vlu692r37PSHBsr57fkq/XdDivnF1WbzTdEm+ATDRvQ/vmD5Nnuy+Wh2HvFsaAT2IGQm+pb9NveTBjz5AFCa+msuovuy3s71R0H++PkcMvkwh775xe4c+55STvmCrOj3HQTu+t5ItvjVfhD0t7WE+mwedPm9YAL1x9RQ9/4NPu3c/1T1p+ua9vCHKPXbUqTvuXxE+iLaIPtcz0b228VO9GyuoO31FVr7jQXM8ZisvvEEr8D0xnS6+bcfVPiwS672L54w+2cspPqYio76W18+9xu5lPvvum766bO496/4xvnGnlj1wMXg9F0+BvpPCdjyBq1++IUKxvDRDszzro6o+rgkqPmRwBT4kcXo9fN2lvTbqRDwcepY+pbWuOyyAjj4q6Cu9tv6lPgzc176qUaQ96rIePTUD2bwUPY2+C/d+vqzkIz0TowY9RoMwvtsTsL0Sxl28Rbo1PnMSXL3ID3O+VdKevTIKBz+6QEO8+rcDvqQylDwd8qA+8cl/PiBbfb4BHh49sIw/PXo8L75ZzHm+No6mvn4Wxb0U61U9r+rGvaRWvL5IB+++pfcCvhKKLD6fkSM+3tUnvaULJr/DBi++KVsbPYlf570eRIy+E43WPdQhmbzpagQ/0wswPbi1YT0ZXOA9lmg+PiaBG74tVwG+jY+lvJjunj5QsbQ9fvEPPWM7jT6Coag9ej2GvuX/vb5nkRu+8afLvJ01Tj47ExU9M0CFvk9+kL6lvF0+XesEPlo4071nFN08oxyLPtgnXL0zKqG9M9Lrvn7URT5rdFE8GIIEPi50LL7WWoK+z5cHPseiBr4kGZw99m+kviGEeD5otFg+6D0dPg5hor5Htg4+TlEiPr3ga77Q046+yMFvPQU8Cz4ysim+MHXqvr5rLj4bX5G+/kaKPQXY4L5M4S2+Y2iKveTVcj5iuNu9l87avu2FI70oiTS+Otx+Pf4WDb5+d/48q21Ovs5amb7Pd/u+bxhHvfIMdT1Xouk92+9lPornkDtQROC9aVxEPTfyVj7sPEm+lpd3PdQ7Yz3qMzw8k66jPum81b3hPXC+NM4FPuW1jL4k0Gi95sCWvS4suj0oFsC9+EF0PSAKfj5oPWs+9upfPkaeLT730u69OcuYPa7sqb3rIAE/3Dy/vbd57LtwAc4+zak9vN0DOb401pm9vAQzvt1SbL6d42G+S/MGPkTLCT5464U8O0t2PQ+5kL4DGte9EsESPeyi0r0mjnK9XLS6vNBwuL2p0xW+vIuivjgwY7609488eCPjPWMgzT2lKMm85TQUvCyXTz58zbK+3NOpPfbPzT1Lr7i9NGEEvU27Mr7lIoW+dfmivg1b772zpeW+kqbsPEfGWj7Jg9a+PEaYvp706byfojm9Yvw0u8bkzD0xXeg95SKrPQCl1LyoOIu+X9/XPdYO9r7ZU8o9hYdDvs2BAD4hLIY+FGmfPSkZi76HaiS+uhkcvsu/Fj4zaGc+V7RPPav9+74eglI+mjxXvvPDVL5mhAQ+SvxMO/ojT75JNyu+eOofvRySST26riQ+9PDdubmnVbyZMIE+o9MpPnVudz47eMS8zBeEvIvqi74BM1w+MmnrPF5Plr47LRI9WkgMvYNONT2uzQs+WHb7uzwNGr6FZDe+0TK+PqLe9L0F+VC+6D/Su/uzqTyo+wK+AZrhOz81S76nIt69SjOKvgU7Cz4ScTK+4O4TPT+p9L52ABi+Q1Q+PpMAmj6dAB2+KJsnPq/Zsb2pDp09qoyOvu7Emb3mH7m99DNLPIMqOT66N6i9j61tPlJ+xz0e5I++nrL5vseyuL6EkZa+C0civu4Sp71Dusa9sPgivjdr5btXCqy9RiLyvUtE3L5yYQc9usONPZoCML4DY4K+Ln2VPI5zlb4aAM68myi6Pc4SZbwJvQc997IOPmfLTLruFpS9BkqKPkrCJT66e8+7x4sXPsM2hb2O/VU9Oo+Mux9eKb4ZL5M9rcswvq1sXj5d4Hm+vilpPARuNr5+G98+ejT8vd8Kg75y8c09I9ofPga6Xb6A32K9rh+qPTLjlr2kMAM+jXe4vYPwV77s5jU+aQmLvizBe774aZ4+hyYlvjNTAr/kSsM9O6TdOz8dZT6rO4+9guvuuz+V0DyIwvg95NIcvixzj74NoUU+QCSKvamsZL3tX7m8zTTPvQiM6jwsKQQ+2kCivEqRz73B6sg9sxuivuRgXDx1L/W+wJHxve1NAjtSmC2+rVkVPmH8iD5AiKO+e99QPpLQXrw2niq+P9Ehvpnfpr31cpw+DKXJPcKNv73sLEw+hN4+veQ2Fz690GE+qzETvghBhr5Ymwo+crl2vsFgujxFLOG9FVGXPK7Bt70kPIs9i0TCvsYQkjyTKl082AfRvd9ig72DF8w9yvmEvR0p+rvxx0G8SGlCvRSNoL0Y0K8+zhOBPqdWSb1zKY89emQCvg1nBz5evie+TyDhvflKDz696KQ9aNJXPo6lP75hlnw96/vZvaNu6bzMX7K+K7IMPveANLwVJkC+eLefvt1NC75TP1I+PaSbvM3Pnr6Z63g9+knyPHGHkj1wi1S9ol1NvcKqYD6NCpO9b03du3be+j3sbAg9eOSovAsC5L3Z4XO+ziyJPalnX7yXkJG+PbfePW3F/jquWP++YsqiPRTeDr6FIcy9YL3BPQqVbD3PHLS9tXu6vV/aU71na469TJ2Vvl9zMTwHcng+ApQOvhQy7jyqvBu+l3ZTvCKMVj7t+oQ+nKBPPey0z70geoE+Fc6RvRNMOb7FrhE+m44lvtcWo75c3Yo+PARwOlLddT3D+zw9NqNFvgaZFj2Eqa09ZQaAPXPdXL79nym+Y3UyPYOChT61GkC+hHO6PgoDuT1b7kG+O5fuvXXwMr9vCUM+Axa7vORsrj30TYq9PdMUPl3YCT12gLS9N5nYPdgsuz3kIcO9cBw2Pk8zKj2tq4i9Dw1zPs90yb7IJ8y+w840PjsJr721wee9PrRNPlwsdD5E9B2+xHJovZRREz1I91s+rXlcvt0IGz2L/5C+/SjLvY5wob3DuJ++xbrsvcrKnD6V3go+/VMSPgnYZ71FTxE+FQasPRaNgL5XIs698bAbPQw0Lr5ovje+U2uGPmF/gT10cj6+CQFBvsPnOD6PkiI9IvLAvaVxUD4/u+09tXVGvU0kuz5Zv2E+rDkwPnzjWD5bg9M+5JOMPqw8Nj6lG3q8ZEuMvj9eUr4svbQ9l74dPsYSwr3RD4c9cR6sPUYT5L5C1Ds+1aCvPXX4N74p+1O/fVWFPrAzX74z7IQ8zM5aPudy/z2c4We+MqLUvsl09Dyy6Jo85CwnPpfrjr1Xn2g95UYwPiKCH77CMO89Q96mPuOnEbyDUyw+ThXzvfhAjz2DumS8E/tlvRd+c7xDpLw9fbdcPr3HEr78YMS9ClIFvhL8Aj7bxAg9Og+Fvnhq577goa69Sz2BvjFL1j3EFvY8BhshvoR4Qr4BoC09oYfbPeOSa777Kg6+Bj6vvXAnbr1Gsyk+eMtZvvXz/z2Db3++qWZuvrXKn70U5ba+3hwbv0ZeET6rn9C8O2b5vpbBDDxWZUk+hbC/PFWFmT5bYo27dLXsPbTtoL6DGDg9HbUhPzYkLb4F9Ae+AbGwvnOp9T39Dky+X6CJPmZIB79og1Y9nkTivdfeCD5eLei+4WYbvtU64D67KUU9ZNx+vU6hgzw/dJ49uV6aPVY8y77BfIY+pkfwvmyuhT1RYeu9tOiXO5K5BT5hEko+351cvo9ko7zXkkW+qF98vpWMLT+Xrtc+CSGjPiSksD0sCsu9Tbtavs16hj5d8KU9UKTBPohxCb5riOg9IWJKPqn4hL7RSZ6+ydTBvc2RGT3LJVQ+5eMWvljD7r2/adS+hnxrviNVdD526GE9Aw9jvka/cbwwLlu9cWMIPkDmFL6xfUk+TbiDvulYqb4iE3K+wQPfvd6PRj2O3uq7sQ6ZvkpfC70p9T09sMP4OycfLL6bdtU9qJ52vaxPur5ZOZS9h7rBvgeyrL5GOvw9by6tPW0Ubr7ZhjO+Z7FZPatWI74l1DU+XV0Kvj9czT49ENu+bFrVPa4KUr7+8O49MfUBvrqQPD5lR4e904qQvsiIAL3iwEA9EounPg91qz62t3w9+iDRvUJ4172pylG+V9xhvfmlNT2AQGa+b9SAvhCXnL0HgkK8PBOUPl04rz2d8nA93YovPihd27zsohG+mS9KvhSprz2hb608KQDRPSdYXb14AiO72IALvvRyg77GEl49zGuEPiYHwb5erfC+W24bPgDjtr0zqKg91qfxPAcPAL1lV7w+Vv0Pvb+/A77RYyS+bYxPPUHAGT/aO8I+jE6SvjbvkL6gZmA+SNVAvnduAL3+bYC+9Jb+PaQ53D2KsnA+ZHqlPeoaFz5Jt5w+NxLTPYJEXT34nIw+U51lPegXejxzP0G815P2Pd97ND4xbmO+p6UjPv8ynj6vekA9Q27IPv1u271lksg9mgWWPkVl7T0LxNs9BuFSvpqkZL5d+t8+YduCvGsG3D6cegI9hvPNPXcmjb1t42e+rYZhPqJvHr5yhbA9mUjVPUmOMD5fGWC93Vtzvr77xj5gmMW6QiGIvvU+Rz0YgxC+MBHHPlgLj76T5Uw+AMWiPNM0Kj7+6Kc9rw68vWFeyz4qGLM+4p9CPt2zsL3XZ489aBVhPgIn2z3fpSC+HBsdPBl1Rj6asZA+9RprvsLlVDvqjkS+GXPvPV/NTj7QPzu+ljfVPTRddD58/568tc/KvblT3T57FsQ97hKSvbGIvj0lr9o9oEYhvhSNfb1vMJ2+X2pJPks1U75YAoi9rP3HvM8jdj5dpsC+GVQMPaP9g71u/Zo+PxzUPu96qr4VufS9omdqvo5pgL01aAq9VrxOPZx6QT5qrs29Mqcev3ipGb170sE+Z4WDPgEjZr5GBde+E2yPPWJ3nz58tiE9/88aPczEZz4ck1U9UpHvvOZDiz0zFDC9VIqIvnhavb14yjC+q2MdPUmXjLxAqcQ93vdqPu9zkj5W4YO8qZeWvpiSWr+dwvW790egviLQoL6aMB49ZosovYhL/j0gBzA9l1F2Plxjjj7Caxo+AsN/vWARjz5PrMa8ctRfPpq/Uj5DPLW9pTAUPG8irD7zYRs/xMCRvvRTnDwUR369D++avkUhZbwNxxi9JW6SvqiUuj0iVB2+0XJuPhbb2b2CccM9doQCPm+kGT664iI+MYptPghhWj4QbBM971POPfX5F77zjp49MjY+vrkCpz28iBm+sxeDPnBQ1b3ZuK49DGi7Pf92mj7EzLa8sv+AvgoPor6jOIa+sWGQvrSLED5mITk+8S5sO6PDO7t8qu88/INDPrM3GL6EtHu9zycSPpENxD6mEi8+0x2KPm2jCb7rmt09FtOtvShADb5HEJi9f7kIvghelb5n5pw9UAUevgrYOb5mU1S+qHvZvQvdqT4ZGhc+NF1CPjz5qL0MTcq+EnTbParm9r5rBEa+SSusu4ofXT5Kham+NiazPLUVSD6OtKg9eaCFvsqExrzpVo+9GiOGvb0Mlz1n5QO+tXvYPYp8UT5ESSO+Ch1ivhYIir2pVEy+dwBvvsPv272MIsE9fFPLvRp+f73egoU+m3fRPEwkD73/jiE9r8QcPjeJEr/vbBQ+Z+TfPeQfQz6+BLG+eg4dPsGCFT868iA+XLlLvnufxDzgWPu9hhxLOzpGIj4PaJE9thQVvj25MT5ql+U9zJXXvGFQKD7fDAs9nXu7PZP9A76hz/G9d0ubPa5h0T1erL+918MkPqMMBT1XVzu8QOolPmx5JT7K7xi9HevavS9jir1OWLW9K+MQPbPYg77yBS68XmS1PvaVXD5cOz8+firJvb9f/jzyt3k95ygGPlotkD6HCKm+4r4lPog047yc1m49hzJuPs3sIb4oPY69BFulPbhwAb88f5C+b/3qvbWpyD1VPTI+mEuiPR+kJT5GGsa+kx66veQWSb6TmqM+xgqUPRkZhT7OrGU+hg5IPqnCrb0Jnbq+n8eIvk0Vdz5jGZy+3mu/POF9dr2vA8e9UBrfPHeKsb7APke9sDZ4vpCtnz5Pdca9bvV3Pt/AnD4z1Pm9x8UEvu7aDb6896M+5NC0vC7Ioj2pzSq+ZGOmPfLTer5viTU+8c+fvre0RL79cxQ+dIgPvfS/A76rGJI+jCfHPmMZmD6F7oK+gGAfPhIBqz1x6Iy+6yuJPf4zmr0UtyE+/ChfPq5gZb1C5BC+U6sdPE97rr2OX9u8EUM7vdJrMD4udI09cC8lPqkaS73UaEY7YQ6WvqITmz2g6Ae+MvFBPaJ3oD0+Xv6+wBF8PjGzFb6p5gM9DEDiO3fEHT5BBsI9FnJLPTZCTT4ErVI9Mp7xO1IPujwVmWO964SyPnGwGL78nI++gIyEPmjQmz4f6Ne+yUkEP2q+Gj26wiY+MSFVPaK+/j1suNq+Ve2Nvhd/i74SmIE+aExjvlkI3j00TYc8a9D+vHggYT0ox+Q8BrPrvXeIqL0rdD49OlbOvqo1cb57eay+cdOBuxwGdz0Z5n0+PvHWPG//Kz6xPN69NeEgPkyoiLy6iCI9mPkMvo/JrT1hiKY+AeJHvhAvib22Ev08YuDYPdiJJD1pDuW8BXKzvsrVXD5meAg7lw6/vsDUHr3YBD07WD0tvkgYMj5NCeY9HnNtPdcPdb6FonC9SVNivgtj9L24Qoe+KjjlPmmKGr7HpEK+Pe21Pl7JrTwCykk9Kvg7vgG9yL6m8Xe95tyqvhX1br4+MWo9Gd5HPj/qmDxqO0a++D4uPqWEmL1kb6s9E5S5PgetaT2Msi4+aY6+vttpjT4FioS+6+SpvbpUlL5dQJK+4sA6PiDllbwJ92k+ZVFwvRxMoL2NYr++H27cvoERv77JSYa9//jNPW+ic72tILq9x47avUDvV75rLby+bAztvm2zJz53Ag4+AWSmvkddCT6IA6I92cLJPQG8bL4dIh09t69qPjiVnr26IO69hUjxvQnzoL5rOmw+tgLfPJb8hz0YISS+Uh2cPlzVRD6cFE6+OOL1valKu72K33Q9LXdIPpxSGT4PgQY+ElWjPhirxDxQH9O9s0Y8PdwbCz5cLm++KxJlPZpU5zyhmvg8+BeOPpHfmb4swPI9CS5CPh9ZBLrEW+u+JJZmPVsPoL63t+k9XwMGvQRyNj63CFC9DCkwPugAuz49d5w8Sm3qPZ0S+j3D+Qe+VC10PTkUHr661V09i48gPaeg677eEa09AAwxPYiDQz6w1NO9t78AvolUGT5ru0S9CVG7vXTWXD6QmYg+886BPVpaeb4PV+w+VcpsPe9NS73zkH0+x6GsPa7jMr7izjm+fqnLvZC8NL7buo6+XrGDPRoHkjxCidO9fOGaPa7tJz6Ah++9YKwMvr2aJL3pl4C9vWYUPulmk77Hznq+8jU2vSSJjT4dyMG+TAtZPT1gjL2avk4+RVMOvRcINr6H25G+qkyuverymT1gNBY+KnAzvew4jj5wZMK9NrGAvqbjsL08Llm9xMLxvmzXEL540J+9cRmTPasON78lsBW++KrmvXN5B71hyiQ+OIVkPeXetLu0m4U8SlQTvImiGL6V3Ac+btwKv85zhz2xjfw9fCSDvVGkRT54C6I9Kv15PcCa7b1RJZA9lO3WvfXd3L3TOQI+zHsivT8GoT6Iq5u9iCKsvo7chj3Gfjo+rGadPGbXBj4Pd24+vm08vbdep7x7GuO+PcyYvmFsGD63VBs+dzHgvdjoEL48egK+gzCgvliiXL4gOpm+b4xRvsBBtz3HPiE9HEPaPXEtDr7sBGa+9KuhPm6p5bueN2o7ZOGaPQGVlb7uRz29Kc+2vn8RjD6Ud3O+c1bBPZVvhL4FIom9MyTkPV7JO73Fuqi98PoNvA8Kbr4nBtS9EHqsPhwmcb467949LSApvYumwj0sP1w+LW5kPsxmUz4f/iC+cA4+PkK/PTsj0oY+b4JbvgzYez5rhOO9MPQUvg+n2L7naoU7XF2/Pjgeaz6g/8e97lxPPWZzWr6Xxye+BoFRPqNOMb0gCio+YCYAvuXP3L4AMjC+bM2Svad1OT0YOl8+PU8DPyu6Fr0FR5k9mvDLvGhmrr6yVSO+jsWEu9EKwL0ueRY9vVQqvkFouTxkONy9wGsSv3eJub7eZ36+2MowPuCpDz+I1wQ+S0eCPuGR5Tzz/VU+YNLBvnikiLwUHaI+gXtrvkbnDz6/yni+/s7WvaX8Jr60k4890ouwvmx0vLuWTYy9VRN5vQFbpr0h08G+lQtnPSSr2b2kiV0+OZJevaALtr3C8kW+TEjTPZ9HaL4ELtA+u12vuxeRJT5H9Cu+HhO/Pu85Yz4GyWi9CipVPsjMA760Boq+ZdvoPVBEAr6rzkQ+MoLaPLz+B72l9aw8JsFFv8hprz0z3aa+yrDtPrluyT5VLaI9GSdovsiAjj0TWA482CIOPgXmtL6ikHa+WUYevAZCyL1Rqm8+nlcEPo0kk73z+8i+li58vp/vYz0pqUE+mqCDvoTVmL1iFZ09mlUnPromhr6XVUA9iFktvUpnDr3prro9+A87vjsPbL3EZAi+3NoZvoFHJL7G+Zw8AAoxvsJ/qT4ULWk+9vpbOwc7MD4e8bI98f9XvUoTY701kAu7tP2pPcMpED7Gh3U9M73DvSw7zruNxdc8n9bxPTdFxD4FqY2+VcN3vqHICj2rIJS9COEvvFXI2r1EEC4+hAeyPD/2R77g/nY+ZA1APloyvj65PGa+qK0KPSTBMj31UzQ+5vUTPvWFgL7IpuY9GZwMPme7/z2FE8U9mwaRve+j3zxKogm+t/sEvhn5ML72+Ii9xcW2PaLAtb2V6MM+Y4FDOxnbyT7rVZ6+0+AUv2Yiu728AgI+7IbUPhSaFb729pS+WVD+Pf13lj5Yb8S9C5NdPmKVQz6+FZK8WA8cvsHYc73elAQ93/invqvXjb723g893jfUviI+vD7KpXy9xGQvPv1WwD5DAh6+TR10vk0PhT6fDWQ96nu+O+W6qL1Gwcw9cUmKPrB+47ydz1O9eEvSPNfifz4bb4o+JK+GPe0ZijzjTvW8/CJUPk9QBz45e5I76tE3Pc19kL7YTqE8Nbt+PUrMN7yyHJU9emMNPRb0qL6e44+7xI3ZvHwDl7496Lw7+CyOvp+4xL0K6Ro/DUqovjlCAzyjxEC96dBdvrQGa76pZ3W9PemcvU4j4T5vp1m+CU78PftLFj4Vk3G/OfNPPvJuAL4WyYc9CJWKvcHF/73HsY0+GCsbvewvfT0W1A8+icVnPWwJqzx70wU+U9uDPchAvr6oMHW9l5UAvo8bVT6aSOs9qVv6PRC7rj4k0qm+uiS+vE9RMz222a0+ogCKPrvFJb0Tnru+PcovvRySvr1UHJg+uribPgfcLz4BNYi8k72SvsDxS76r11W+ITODPe5+iD68/my9qf05PmBYZr6HZqG+uLPIPF3sn753xw6/CWFtPUX8hT1NTno9wk88PuXaAD5DuhK9RAZrPm4GRDyQzIW+QR13Pm+uEj5s2T68p8HUvaPFEz/qgXI+d2AOPqu0nD4J3Wk+fYI7PH3OHz4Z/iW+Gg+6PXG/x77i4QA9Et48PhQt4b6VKrQ+OYhMvoxROj6pYay9J962PXbvp71Ho8Y+0wEPPlcToD4WHK49aUvHPe1UZj0+k3a9+LTtuz1zRL0Ojz69vl2KvkxaIbwPWUA9DQnNPFWuk7t3+KG96+1WvlwOhb4pmmG+hKehvCTwgr6sipE99jtXvvD8tL7Jqis+Sx9kvTjmNL0DaMM+/Al1Ppv2yz13RrY+hI6uPd8s7z0PC9K95eT3uvfB872wzmw+qnWNPnsBpb7cb5M+bboEPgl/uD31Any8XGNHPqGgiz1ZaL2974igvbepQj3NAyy+K/MSvpSBcj5BVM29lwZavkAFdL4uKAS/vfcWvo21YT5Nlmu+trCJvcJSk75UldI9V+c4PaupnD3Co10+qoOGPvT+Yj4LVc291xNEvo7mu735bWe+sXQ6PgbuwTytBSu96GM4vSk2hj58oUW+9lT+PWCHcD4XPdQ8D4z3vqLrnT30BIC+XxCAvt14Ob6XapS9esQkPowBkr4XHQO80ox7PcDop7rbQfQ8rPO1vI0l/j1f0Si+IQMavsh1dTvsEgE+UfNVvqf4wb1MTde96RgFvjczrDw9FOY95aRavQqeJz6Q2As+P94ivqGLUj3iX6M9zyODPjwDTL79d3k+NzMvvZuAlr7E08U9AOjtvgvfQ76oSd28ZeqvvpDfdL7lEcC9TmIdvjrjcD40WjQ8co/jvQWYY77vd1e9l1WtPWdBkb1oD4q+LRRJPnzQqry9yKG7fYq8PnbuB76+Muo9/OeTvo8dSzw+OOO9NP7HvUBo8b23U4I96huuPTg18Tz1G9Y+6oY8vhyWSb7E4MO9S7zovkoFez4xucU972F6vo76yT3w4iK8iovrPujyr74YUq2+NC7UvqnfODyae/++BcHUvVpAlj1NGcM9yw88vjpUAz6h7YW9nhcDPlhGqTwMt6O+cADFO49J3D4kiUe9AozFvhZUob3Iuju+3yqlvtLwaL1eeE69CYAVvvTICb/ll6K+Dg8xvp4LJD67mJG+7xZ3vFGKLz67j5m+gkEcPSGjXb5eLJa7ZWcxPugetT46CMa9BmqbPsk2/r0IwJU+xdMHv7TlkrwPI7A+xmPsPQ+ikr2r7oU9tQOMPtc1Hr6YsAi9KfIwvp1sEz2S44I+aqUsPoCRer5HwO29/hocvyKxTj7JUIS9EvtcPvz8iby34tU9V69Vvh+qHjyS7A++ehFhPc3PjD2rBre8Rj/evt8nSD5kP7a+OPWPvaRplz0yEgQ98WD7vZkAMj11NKK9DIBGPrkoQ70Wd488896CPqDvb77SfKg9qG+XPbefi76obwI+ot7EPWeTbz6b/gY+IVsdPumonz6VcMy9HVggvjFW7T2t6hC9w8ptPhBfvD3B8fo94IJWPQsykr2LUqc93IedvSVHTL0VHFc8nuXWPeGiuDwcPm49dWUKPXeTA75jW6S9tvCuPmxHID4udrc90tStPMNQ0b0JUx89oW0pPDfaT75aFhw+dkoZP9jLZr4WoIs+Sn8IvEdxlT6lEYw9x4QQPKNxjT4Sp1G+PpUJPgq4H74ACF++oIAhPS750b5vNGU9NZgnPoRdCD5Oo4Q9VIPgPAt1Nbskm9u9jTN5PubdRL7fXMy8F7uHvUwAEz64k5O+sYpqPh0NPr5G/6s+ZdShPUhdzz3kQAA+gSS7PcqyA72PdYw+hvktPp+clr0Rmxa+FEGdPgd7MT6smUE932exvvshdj6oVMW9otiMPTiP7D2O5wO+RQvoPRerOD5DlCs+gZEVvgnhlL2dlp69X9OtvQl/oj0Tkx89d/R0vcH6WDzAb127r9AovySESD36jpY+lNyEvqdRMr7e35y9RDcCvbvF372ljo69gwkYPTFlj75u62m9QPifPMgNib1nDOe87uw4vuEWhz4t60q+ssZyve3BXz2XU2Q+AQfmPNvx/j2UqlG+cvewvY7mX73MKZs8q8EyvqwtIT4t0tK9JN6Lvmo+VLwcmD894fU9PaNRx72uKis9L8PVvchiND78hS0+fuvJvdtiqz4yWkE9n9kUvTHFcD3eDYa9JViZviSfUj6VHiC+eEtZvY9+FD7zB6o9RY2cPlX2PT6Hf7Y9IEr/PDNm3T1BJ5e+GyX8PHtFoj3+g5O+lNozPDkhcb5CaaQ9XTFAPu7i6L3OHko77zNePhqGIT5JZJq+uppDv1aohT4/BAs+p0PhvfWC6TxK0q6+xl+bvhOZ27071Qw/xQ9yvFHhyT4gfZy+2Ihku1d6DD6w62K857PIvjIMhD5aim4+M0qQPr1Unz5H9lI9B0NLPjnyvz2zv3++nLDzPRGWcT1uuPk9phrpPE/5cD1noZ09a1SoPfsuwj3n6Wo+lByQO3xqkr5pBk69LJQQuwgmMz15iNm+y+i8va0ZRL52pIC8Sa6rvfamwD12UQY+7mSrvlbZOT1fgRo+p3BGvrJKhj7+LhC+eAoQvvQA/j3in6M8Zd4LvkYigr/QvXc8nS83PdxO9j7/AYs+mcAbPmJ6I75JWw0+0YYevuLZPj5H/189b1havM0Ttb0gBFe9J+wNPo4esD6hEKs9kdyqPOmHN74WjFI8bnBvPoHF0D7Rd0Y+Xr+vPRKM/j2+WbE+a86mPW1WhTzrDyA+n+8jv0e7y76kPJW9hu1JPjcx/L2s/Ey+vmtKPqAysb5A2ga9WA0SPuvzlL6hIyE+bWylvnOOzTuR0ao9/NJjvmW6cD2aDIu+YskCPsh2Ib7fRp498xK2vTPolr657sK9Zi9SPhGOhb7yDpo7px4LvnKXV77m2xu+LmGNPXGQyL6QrtU90llWPougNL5j3nK8AckDPb1Fzr0gnLe+KXC1PjWGeT0FGQ+/xK7EPtCrO75F/jc9gjcmPvJnpbwAdRA2TCqfvuwdar6q6oq91/BfvZd7YL44xl8+20aFviinyL3oEQc+Q4cRvXuVub7AB0m9/vXmveapnb6hEGq7K1PPvds07j23J5K9LuU6vfiSAb529kO/sqg/vpz2ND73wi0+QL/8PBCNHj55LB09iNg/Pmk8NL+74TK+ioDBPW7GoLyF99w+3/puvWDOlr3ANiy+zqQuvivWf75QtRK+mGmbvq3un72Vhqk+4KPTPJcqW74jMLA9zC9SvjmUhz4yKSE8WdC9voDl3D2UMG4+x3SLvkJKcb5KH6Q+FiFOvCxvgj5007e9ktchPUAe6b1DzTc9PSmOvklUzb3i0JM+Soe1PYr+8b7TwSa8F7L1PdVHLr6pI7K+zw6LPBr0Tb57I1++8aZ1vkv2cb5elYC93w0NvgJ/jj3dGB8+8yQOvvVMgDypgY69nRMpPtXQeL3Pwtw8A+1MPb65t72ycvW6YUfMvuLsHr43Yr29XHOQPgpFOT4gyVq+FHbIvn5lFT7vvsg+nClfPgLR374oOuk9+VgAvcEYHj6KdEW9NxKIvt2TzT3YaBY+Df4VvWMadL1iU4G+3VdqPPhSAD2O3kq+mEvJPqs6Jb75PxE+Ay1LvaqLtbzT+aq+YKw9vkufvL6ntgY+5LdBPTym4b6obza+zHSyPSz55Tx6Aog99RhIPENxhb1Srty8Gs/XPIoTm70AL+E8qaxyPUV9Pz09Z4W8N9c6vZMDk70r/YG9SP6YvZ1t2b3WPAk9meBoPLTJAj1uu7q8qA5lPaPT7DxdYwY9jDcBuvafgzxmUjG9NkoIOhS5dbxvk4q8ifCQPTQjuz0g3Ti+8CnUvbOXgT2MVYK9Rab4vTJJWL2s72C8KzzMvZr7ybwLLBC98jc+vd/b9jw7JPk8RTZiu15Yt7rZ0WS7S5eMvIAWcjzcXZc8SSCUPYPykL02Gpe834oAvs9wUb23yIw9lWk3vdIfWb3CwTa9rY46PS9qRDysVWC9mFagPYYYHTy4Ljo+QqWRPjL03r4rTDs+pH/CvraiJr7XxDm+LKQKP0jT0j7K1AI+wQfYvYpaub4LEw+//DldvmrbPr5xwqu+uMroPUi6/T2BSLk9gemRPaXGPj+oBo2+oGOKPmH4hT0GV48+FbJjvh3uMb6b78u+ks3MPoQiFj4LUss981K9vulHD7+nAAw/p3XMvrW4tr6x7vU9a4+kvjWjBL8c9Oi9DbevvBr6k71yE8M+SC2cvtK7nT0Ut7Q+sEqbPnk8Z76u70W/OKBbPnTjTz55RDW+huMlP/GNbr6P5CQ9aZ75vmKz0D46cEO9HQKFvjM1Pz6zKN09IZMNv2vlAD+t3Hg+azM0PVcHfz6qZ1U/8uNxP7OAFz/OIAI/1LJoP2v5az+yy6E+XWQjP+trhD4AAAAAwSjxPoIl1T4AAAAAl+/HPj134z6gq6Y+5vM7PvGd7T3cNvA+9DiWPqeYiD6Bx3Q9w8KYPibctzpJS2A+W6QVPnOlpz3sCrQ9AAAAAHYYVD6J0YM+RhQZPkuwID6eEmE+RzthPrxITz5u9oo+RgGzPvJKQz69N4Y1wJIzPvKDdz69N4Y1bb35PgIkez7tZp8+SDLGPrb+oz79g/8+ERnpPqp44j6DxnI+tDbqPgxUGT3Hngs/tty0PrBTjD6PAZE+vTeGNQ=="  # filled by tools/train_ml.py
_ML_MODEL = None


def _ml_load():
    global _ML_MODEL
    if _ML_MODEL is not None:
        return _ML_MODEL
    try:
        import base64

        import numpy as np

        raw = np.frombuffer(base64.b64decode(_ML_W_B64), dtype=np.float32)
        # layout: dims(4 int32 as float) then W1,b1,W2,b2,W3,b3,mean,std
        dims = raw[:4].astype(int)
        d_in, d_h1, d_h2 = int(dims[0]), int(dims[1]), int(dims[2])
        i = 4
        def take(n):
            nonlocal i
            a = raw[i:i + n].copy()
            i += n
            return a
        W1 = take(d_in * d_h1).reshape(d_in, d_h1); b1 = take(d_h1)
        W2 = take(d_h1 * d_h2).reshape(d_h1, d_h2); b2 = take(d_h2)
        W3 = take(d_h2).reshape(d_h2, 1); b3 = take(1)
        mean = take(d_in); std = take(d_in)
        _ML_MODEL = (W1, b1, W2, b2, W3, b3, mean, std)
    except Exception:
        _ML_MODEL = False
    return _ML_MODEL


def ml_features(obs, me_idx, opp_idx, opt):
    """(state, option) features for the ML value model. ~30 dims, all from obs."""
    cur = obs.get("current") or {}
    players = cur.get("players") or [{}, {}]
    me_p = players[me_idx] if len(players) > me_idx else {}
    op_p = players[opp_idx] if len(players) > opp_idx else {}
    my_act = _active(obs, me_idx) or {}
    op_act = _active(obs, opp_idx) or {}
    my_bench = _bench(obs, me_idx) or []
    op_bench = _bench(obs, opp_idx) or []
    def hp_frac(poke):
        hp = float(poke.get("hp") or 0); mx = float(poke.get("maxHp") or 1)
        return hp / mx if mx else 0.0
    disc = me_p.get("discard") or []
    water_disc = sum(1 for d in disc if isinstance(d, dict) and (card(d.get("id")) or {}).get("en") == 8)
    op_ids = set()
    for poke in [op_act] + list(op_bench):
        if poke and poke.get("id") is not None:
            op_ids.add(poke.get("id"))
    otype = opt.get("type")
    est = 0.0; ko = 0.0
    if otype == OptionType.ATTACK:
        try:
            est = float(estimate_attack_damage(opt.get("attackId"), obs, me_idx, opp_idx) or 0)
            if op_act and est >= float(op_act.get("hp") or 0) > 0:
                ko = 1.0
        except Exception:
            est = 0.0
    hid = None
    if otype == OptionType.PLAY:
        try:
            hid = _hand_id(obs, me_idx, opt.get("index"))
        except Exception:
            hid = None
    my_act_c = card(my_act.get("id")) or {}
    op_act_c = card(op_act.get("id")) or {}
    return [
        min(float(cur.get("turn") or 0), 40) / 40.0,
        len(me_p.get("prize") or []) / 6.0,
        len(op_p.get("prize") or []) / 6.0,
        float(me_p.get("deckCount") or 0) / 60.0,
        float(op_p.get("deckCount") or 0) / 60.0,
        hp_frac(my_act), hp_frac(op_act),
        len(my_bench) / 5.0, len(op_bench) / 5.0,
        min(len(my_act.get("energies") or []), 6) / 6.0,
        min(water_disc, 20) / 20.0,
        min(float(me_p.get("handCount") or 0), 12) / 12.0,
        min(float(op_p.get("handCount") or 0), 12) / 12.0,
        1.0 if my_act_c.get("megaEx") else 0.0,
        1.0 if (op_act_c.get("ex") or op_act_c.get("megaEx")) else 0.0,
        min(float(op_act.get("hp") or 0), 350) / 350.0,
        min(sum(float(b.get("hp") or 0) for b in my_bench if b), 900) / 900.0,
        1.0 if op_ids & SPREAD_IDS_V41 else 0.0,
        1.0 if op_ids & WALL_IDS_V36 else 0.0,
        1.0 if op_ids & FAST_IDS_V36 else 0.0,
        1.0 if otype == OptionType.ATTACK else 0.0,
        1.0 if otype == OptionType.PLAY else 0.0,
        1.0 if otype == OptionType.EVOLVE else 0.0,
        1.0 if otype == OptionType.ATTACH else 0.0,
        1.0 if otype == OptionType.RETREAT else 0.0,
        est / 300.0, ko,
        1.0 if (hid and is_basic_pokemon(hid)) else 0.0,
        1.0 if hid in (1227, 1235) else 0.0,
        1.0 if (hid and (card(hid) or {}).get("megaEx")) else 0.0,
    ]


def _ml_predict(feats):
    m = _ml_load()
    if not m:
        return 0.5
    try:
        import numpy as np

        W1, b1, W2, b2, W3, b3, mean, std = m
        x = (np.asarray(feats, dtype=np.float32) - mean) / std
        h = np.maximum(x @ W1 + b1, 0)
        h = np.maximum(h @ W2 + b2, 0)
        z = float(h @ W3 + b3)
        return 1.0 / (1.0 + pow(2.718281828, -z))
    except Exception:
        return 0.5


def agent(obs: dict) -> list[int]:
    try:
        return _decide(obs)
    except Exception:
        return _fallback(obs)
