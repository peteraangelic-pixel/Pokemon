# v51 LEAGUE (a450, 2026-10-14): v42.2 modulator with LEAGUE-trained
# per-arch state-value models (24k games, 5 pilots x pool decks, 454k
# states, split po grach) + CEM2-best knobs (jak v48). Zrodlo modeli:
# tools/gen_league_data.py + train_league.py -> league_models.json
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
os.environ.setdefault("PTCG_SUPPORTER", "325")
os.environ.setdefault("PTCG_ITEM", "292")
os.environ.setdefault("PTCG_BENCH", "285")
os.environ.setdefault("PTCG_EVOLVE", "330")
os.environ.setdefault("PTCG_ATTACH", "255")
os.environ.setdefault("PTCG_STADIUM", "278")
os.environ.setdefault("PTCG_ABILITY", "216")
os.environ.setdefault("PTCG_ATTACK_KO", "345")
os.environ.setdefault("PTCG_ATTACK", "221")
os.environ.setdefault("PTCG_RETREAT_BASE", "109")
os.environ.setdefault("PTCG_RETREAT_NO_ATK", "225")
os.environ.setdefault("PTCG_RETREAT_KO", "259")
os.environ.setdefault("PTCG_RETREAT_WALL", "348")
os.environ.setdefault("PTCG_GUST_BONUS", "101")
os.environ.setdefault("PTCG_WALL_PENALTY", "-581")
os.environ.setdefault("PTCG_WALL_ESCAPE", "245")
os.environ.setdefault("PTCG_ATTACH_WALL_BONUS", "40")
os.environ.setdefault("PTCG_ATTACH_WALL_PENALTY", "5")
os.environ.setdefault("PTCG_BEACH_WALL", "346")
os.environ.setdefault("PTCG_FIGHTER_READY", "6")
os.environ.setdefault("PTCG_FIGHTER_NOT_READY", "-40")
os.environ.setdefault("PTCG_PRIZE_PENALTY", "12")
os.environ.setdefault("PTCG_ENABLE_BONUS", "9")
os.environ.setdefault("PTCG_PROGRESS_BONUS", "39")
os.environ.setdefault("PTCG_ACTIVE_BONUS", "12")
os.environ.setdefault("PTCG_PRIMARY_BONUS", "11")

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
