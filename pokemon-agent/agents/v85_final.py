# v63 SUPER: c87_v44 champion + a450 anti-wall wrapper (single file)
# v44 = v43 + STRONGER bench guard vs live board-collapse (v55 59% bench0 losses, 389.9 after 68g)
# - bench0 -> +1000, bench1 -> +500 (was 80/200 in v43, 35 in v38b) – never end turn on empty bench
# - flood guard v2: water>=3 board<=2 => basics +300 UB/Pad +200 (was 200/120 at >=4) + water>=2 board==0 => +500
# - keep mirror Beach 400 rotation + retreat 335 fallback
# - deck same v55_final (31W Kyo2 UB4) best broad 0.727 with v43, expect >0.75 with v44
# v43 = v42.9 + flood guard + mirror Beach rotation (c87 + a450 merge)
# - flood guard: hand_water>=4 & board<=2 => basics +200, UB/Pad +120 (anti-collapse)
# - mirror rotation: Surfing Beach 1262 ABILITY (free switch W) boosted to 400 when Kyogre active & ready Aboma (723, >=2E) on bench
# - retreat fallback: Kyogre->Aboma score 335 when no Beach but opp HP>=150 (Hammer 300 > Swirling 130)
# v42.9 = board dev 80/45/20 + evo -90/-40 + search gate -150 + retreat threat-aware + FROSLASS {861,103} Amarys counter
# v29 = v28 bench400 + 8560 mirror specialist (Hammer >=280 +250, Riptide >=100 +150, no early trades)
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
    [3]*33 + [721,721,722,722,722,722,723,723,723,723,1121,1121,1126,1145,1145,1219,1219,1227,1227,1227,1227,1262,1213,1213,1182,1207,1097]
)
_V80_DECK = list(_FALLBACK_DECK)



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
        if opp_power >= my_hp and my_bench and backup_ok:
            score = RETREAT_KO  # escape a knockout, then develop

        if WALL_SWITCH and opp_active is not None and my_bench:
            if damage_prevented(my_active.get("id"), opp_active.get("id"), 10 ** 6):
                for p in my_bench:
                    if not damage_prevented(p.get("id"), opp_active.get("id"), 10 ** 6):
                        score = max(score, RETREAT_WALL)
                        break
        # v43 mirror rotation: Kyogre active -> ready Aboma bench (costly retreat, but if Beach not in play and Aboma can KO, still worth)
        try:
            if my_active and my_active.get("id")==721:
                ready = _v43_ready_aboma_on_bench(obs, me_idx)
                if ready:
                    # if we have Beach, ABILITY will handle free switch; retreat still possible but costs 3E
                    # only boost retreat if no Beach and active low or can't attack
                    if not _v43_has_beach(obs):
                        # estimate: if opp active HP <= 250, Aboma Hammer ~300 can KO, Kyogre 130 cannot
                        opp_hp = int(opp_active.get("hp") or 0) if opp_active else 0
                        if opp_hp >= 150:  # Aboma better than Kyogre
                            score = max(score, 335)
                    else:
                        # Beach present, but if ability not available this turn (already used), retreat as fallback
                        score = max(score, 300)
        except Exception:
            pass
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
        # v43 mirror rotation via Surfing Beach (1262): free switch W active -> ready Aboma bench
        try:
            # Beach is stadium ability, area STADIUM
            if opt.get("area") == Area.STADIUM:
                stad = obs["current"].get("stadium") or []
                is_beach = any(isinstance(s, dict) and s.get("id")==1262 for s in stad)
                if is_beach:
                    my_act = _active(obs, me_idx)
                    if my_act and my_act.get("id")==721: # Kyogre active
                        ready = _v43_ready_aboma_on_bench(obs, me_idx)
                        if ready:
                            # prioritize switching to ready Aboma in mirror / when active low
                            return 400  # above KO, free rotation
                    # also general: if active is damaged and bench has ready attacker, switch
                    my_act = _active(obs, me_idx)
                    if my_act and int(my_act.get("hp") or 0) <= 120:
                        ready = _v43_ready_aboma_on_bench(obs, me_idx)
                        if ready:
                            return 360
        except Exception:
            pass
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
            if not my_bench:
                return 1000  # v44: never empty bench (live 59% bench0 losses)
            if not my_bench and (my_active is None or int(my_active.get("hp") or 0) <= 80):
                return 1000  # v28: stronger bench vs fast KO with empty bench
            score = 320
            if is_primary_line(cid):
                score += 10
            # v44: generic board development boost vs fast decks - bench when thin (stronger than v28)
            if len(my_bench) == 0:
                score += 500
            elif len(my_bench) == 1:
                score += 300
            elif len(my_bench) < 3:
                score += 150
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
            base = SUPPORTER_SCORE + _wall_gust_bonus(cid, obs, me_idx, opp_idx) + _v24_search_gate(cid, obs, me_idx)
            try:
                arch = _V41.get("arch")
                if not arch:
                    try:
                        opp_a = _active(obs, opp_idx)
                        if opp_a and opp_a.get("id") in FROSLASS_IDS_V42:
                            arch = "FROSLASS"
                    except Exception:
                        pass
                hc = 0
                try:
                    hc = int((obs.get("current", {}).get("players") or [{}]*2)[me_idx].get("handCount") or 0)
                except Exception:
                    hc = 0
                if arch == "FROSLASS":
                    if cid == AMARYS_ID:
                        if hc >= 4:
                            base += 400
                        elif hc >= 2:
                            base += 200
                        else:
                            base += 80
                else:
                    if cid == AMARYS_ID:
                        # outside FROSLASS, Amarys discards hand – avoid
                        if hc >= 5:
                            base -= 600
                        elif hc >= 3:
                            base -= 300
                        else:
                            base -= 100
            except Exception:
                pass
            return base
        if ct == CardType.ITEM:
            return ITEM_SCORE + _wall_gust_bonus(cid, obs, me_idx, opp_idx) + _v24_search_gate(cid, obs, me_idx)
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



def _v43_hand_water_count(obs: dict, me_idx: int) -> int:
    try:
        hand = obs["current"]["players"][me_idx].get("hand") or []
        cnt=0
        for h in hand:
            if not isinstance(h, dict):
                continue
            cid2=h.get("id")
            c2=card(cid2)
            if c2 and c2.get("en")==3:
                cnt+=1
        return cnt
    except Exception:
        return 0

def _v43_has_beach(obs: dict) -> bool:
    try:
        stad = obs["current"].get("stadium") or []
        for s in stad:
            if isinstance(s, dict) and s.get("id")==1262:
                return True
        return False
    except Exception:
        return False

def _v43_ready_aboma_on_bench(obs: dict, me_idx: int):
    try:
        bench = _bench(obs, me_idx)
        for p in bench:
            if not isinstance(p, dict):
                continue
            if p.get("id")==723 and len(p.get("energies") or [])>=2:
                return p
        return None
    except Exception:
        return None

def _score_wanted_card(cid, obs: dict, me_idx: int) -> int:
    """How much do we want this card in hand / in play right now? (v24 board dev fix + v44 stronger flood guard)"""

    c = card(cid)
    if not c:
        return 50
    ct = c.get("ct")
    if ct == CardType.POKEMON:
        score = 100 + plan_power(cid) // 3
        if c.get("b"):
            # Basics are raw material of board: thinner board => more value (v24) – v44 stronger
            bn = _v24_board_n(me_idx, obs)
            if bn == 0:
                score += 1000
            elif bn == 1:
                score += 500
            elif bn == 2:
                score += 200
            elif bn == 3:
                score += 80
            # v44 flood guard v2: water>=3 board<=2 => +300, water>=2 board==0 => +500
            try:
                wc = _v43_hand_water_count(obs, me_idx)
                if wc >= 3 and bn <= 2:
                    score += 300
                elif wc >= 2 and bn == 0:
                    score += 500
                elif wc >= 3 and bn <= 1:
                    score += 400
            except Exception:
                pass
        elif not _v24_evo_has_pre_on_board(cid, obs, me_idx):
            # Evolution with no pre-evo on board is unplayable now, clogs hand
            score -= 90
            if _v24_hand_count(cid, obs, me_idx) >= 1:
                score -= 40
        return score
    if ct == CardType.SUPPORTER:
        return 95
    if ct == CardType.ITEM:
        # v44: when flooded with energy and thin board, search that discards energy is valuable – stronger
        try:
            bn = _v24_board_n(me_idx, obs)
            wc = _v43_hand_water_count(obs, me_idx)
            if wc >= 3 and bn <= 2 and cid in (1121, 1152): # Ultra Ball, Poke Pad
                return 90 + 200
            if wc >= 2 and bn == 0 and cid in (1121, 1152):
                return 90 + 300
            if wc >= 3 and bn <= 1 and cid in (1121, 1152):
                return 90 + 150
        except Exception:
            pass
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

B39_BENCH0 = int(os.environ.get("PTCG_B39_BENCH0", "1000"))  # v44: never empty bench (was 35, 120 tested mirror 902-898 -> rejected, but live 59% bench0 losses forces it)
SWARM_BENCH_TARGET = int(os.environ.get("PTCG_B39_BENCH_TARGET", "3"))
SWARM_BENCH_HOT = 500
SWARM_BENCH_WARM = 250
SWARM_BENCH_THREAT = 300
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

# v42.6 FROSLASS counter: Mega Froslass ex 861 does 50 dmg per card in opponent hand
FROSLASS_IDS_V42 = {861, 103, 1002}
AMARYS_ID = 1207
CARMINE_ID = 1192
LILLIE_ID = 1227
ULTRA_BALL_ID = 1121

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
    """Sticky archetype call: once SPREAD/WALL/FAST/MIRROR/FROSLASS is seen, keep it."""
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
        if ids & FROSLASS_IDS_V42:
            arch = "FROSLASS"
        elif ids & SPREAD_IDS_V41:
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
    # v42.6: FROSLASS first – lethal hand-size punish
    try:
        if opp_active_id in FROSLASS_IDS_V42 or (seen & FROSLASS_IDS_V42):
            wall_cnt = len(seen & WALL_IDS_V36)
            fast_cnt = len(seen & FAST_IDS_V36)
            mirror_cnt = len(seen & MIRROR_IDS_V21)
            return "FROSLASS", wall_cnt, fast_cnt, mirror_cnt
    except Exception:
        pass
    wall_cnt = len(seen & WALL_IDS_V36)
    fast_cnt = len(seen & FAST_IDS_V36)
    mirror_cnt = len(seen & MIRROR_IDS_V21)
    if opp_active_hp and opp_active_hp >= 300:
        wall_cnt += 2
    if opp_active_id in WALL_IDS_V36:
        wall_cnt += 1
    if opp_active_id in FAST_IDS_V36:
        fast_cnt += 1
    if wall_cnt >= ADAPT_WALL_THRESHOLD:
        return "WALL", wall_cnt, fast_cnt, mirror_cnt
    if fast_cnt >= ADAPT_FAST_THRESHOLD:
        return "FAST", wall_cnt, fast_cnt, mirror_cnt
    if mirror_cnt >= ADAPT_MIRROR_THRESHOLD:
        return "MIRROR", wall_cnt, fast_cnt, mirror_cnt
    return "DEFAULT", wall_cnt, fast_cnt, mirror_cnt

FIGHTING_ENERGY_V21 = 6

_V24_EX_SEARCH = {1145}    # Mega Signal
_V24_EX_RECYCLE = {1097}   # Night Stretcher
_V24_RECYCLE = {1205}      # Cyrano

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
    if V45_IMIT:
        try:
            # v67: no imitation in MIRROR mode (c87 v85 mechanism, ported)
            try:
                _mode_for_imit = mode
            except Exception:
                _mode_for_imit = "DEFAULT"
            if _mode_for_imit != "MIRROR":
                score += V45_IMIT_W * (_imit_predict(ml_features(obs, me_idx, opp_idx, opt)) - 0.5)
        except Exception:
            pass
    return score




# ================= v42 ML option-value (experimental) =================
V45_IMIT = os.environ.get("PTCG_V45_IMIT", "1") not in ("0", "false", "False", "")  # default ON (imitation prior; A/B pending)
V45_IMIT_W = float(os.environ.get("PTCG_V45_IMIT_W", "60"))
_IMIT_W_B64 = "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"  # filled by tools/train_ml.py
_IMIT_MODEL = None


def _imit_load():
    global _IMIT_MODEL
    if _IMIT_MODEL is not None:
        return _IMIT_MODEL
    try:
        import base64

        import numpy as np

        raw = np.frombuffer(base64.b64decode(_IMIT_W_B64), dtype=np.float32)
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
        _IMIT_MODEL = (W1, b1, W2, b2, W3, b3, mean, std)
    except Exception:
        _IMIT_MODEL = False
    return _IMIT_MODEL


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


def _imit_predict(feats):
    m = _imit_load()
    if not m:
        return 0.5
    try:
        import numpy as np

        W1, b1, W2, b2, W3, b3, mean, std = m
        x = (np.asarray(feats, dtype=np.float32) - mean) / std
        h = np.maximum(x @ W1 + b1, 0)
        h = np.maximum(h @ W2 + b2, 0)
        z = float((h @ W3 + b3)[0])
        z = max(-30.0, min(30.0, z))
        return 1.0 / (1.0 + pow(2.718281828, -z))
    except Exception:
        return 0.5


def agent(obs: dict) -> list[int]:
    try:
        return _decide(obs)
    except Exception:
        return _fallback(obs)


# =====================================================================
# v63 SUPER (a450): champion v44 + anti-wall Kyogre wrapper.
# From c87 v61 idea + a450 forensics of the v59_10k Kaggle collapse:
# Crustle-wall hardcounters Mega Abomasnow ex (pv=['ex']); Kyogre
# (non-ex) is the only attacker that gets through. Wrapper fires ONLY
# when damage_prevented() says our Active is fully walled; every other
# matchup runs the untouched champion logic.
# NOTE: Kaggle picks the LAST callable in the module, so the wrapper is
# defined under a private name and bound to `agent` at the very end
# (del + assign moves the key to the end of the namespace).
# =====================================================================
_KYO = 721
_champion_agent = agent


def _v63_walled(me, opp, obs):
    try:
        a = _active(obs, me)
        o = _active(obs, opp)
        if not a or not o:
            return False
        return bool(damage_prevented(a.get("id"), o.get("id"), 10 ** 6))
    except Exception:
        return False


def _v63_kyogre_slot(obs, me):
    try:
        for i, p in enumerate(_bench(obs, me) or []):
            if p and p.get("id") == _KYO:
                return i, len(p.get("energies") or [])
    except Exception:
        pass
    return None, 0


def _v63_agent(obs: dict) -> list[int]:
    dec = _champion_agent(obs)
    try:
        cur = obs.get("current") or {}
        if cur.get("result") is not None:
            return dec
        me = int(cur.get("yourIndex", 0))
        opp = 1 - me
        sel = obs.get("select") or {}
        opts = sel.get("option") or []
        if not opts:
            return dec

        # promotion after KO, wall ahead -> Kyogre first
        if int(sel.get("type") or -1) == 1 and int(sel.get("context") or -1) == 4:
            act = _active(obs, me)
            opp_act = _active(obs, opp)
            if act is None and opp_act is not None and (card(opp_act.get("id")) or {}).get("pv"):
                bench = _bench(obs, me) or []
                for i, o in enumerate(opts):
                    if o.get("type") == 3 and o.get("area") == 5:
                        s = o.get("index")
                        if s is not None and 0 <= s < len(bench) and bench[s] and bench[s].get("id") == _KYO:
                            return [i]
            return dec

        if int(sel.get("type") or -1) != 0:
            return dec
        if not _v63_walled(me, opp, obs):
            return dec

        slot, kyo_e = _v63_kyogre_slot(obs, me)
        act = _active(obs, me)
        has_kyo = slot is not None or (act and act.get("id") == _KYO)
        players = cur.get("players") or []
        if slot is None and not has_kyo:
            hand = (players[me].get("hand") or []) if me < len(players) else []
            for i, o in enumerate(opts):
                if o.get("type") == 7:
                    idx = o.get("index")
                    if idx is not None and 0 <= idx < len(hand) and (hand[idx] or {}).get("id") == _KYO:
                        return [i]
            return dec
        if slot is not None and kyo_e < 3:
            for i, o in enumerate(opts):
                if o.get("type") == 8 and o.get("inPlayArea") == 5 and o.get("inPlayIndex") == slot:
                    return [i]
            return dec
        if slot is not None and kyo_e >= 3 and not (act and act.get("id") == _KYO):
            for i, o in enumerate(opts):
                if o.get("type") == 12:  # RETREAT into charged Kyogre
                    return [i]
            return dec
        for i, o in enumerate(opts):
            if o.get("type") == 13 and o.get("attackId") == 1043:  # Swirling Waves
                return [i]
        return dec
    except Exception:
        return dec


_v63_agent.__name__ = "agent"
del agent
agent = _v63_agent


# --------------------------------------------------------------------------
# v66 wall tempo wrapper (A/B switches: PTCG_WALL_R1, PTCG_WALL_R2; default on)
# R1: energy priority - if base attaches to an already-loaded active Kyogre,
#     attach to a 0-energy benched Snover/Abomasnow instead (win the evo race)
# R2: protect Snover - active Snover facing Mega Abomasnow retreats to a
#     benched Kyogre/Abomasnow instead of dying for free
# --------------------------------------------------------------------------
import os as _os_v66
_V66_R1 = _os_v66.environ.get("PTCG_WALL_R1", "1") == "1"
_V66_R2 = _os_v66.environ.get("PTCG_WALL_R2", "1") == "1"
_base_agent_v66 = agent


def _v66_poke(lst, i=0):
    if isinstance(lst, list) and 0 <= i < len(lst) and isinstance(lst[i], dict):
        return lst[i]
    return None


def _v66_en(p):
    e = (p or {}).get("energies")
    return len(e) if isinstance(e, list) else 0


def _v66_agent(obs):
    try:
        sel = obs.get("select") if isinstance(obs, dict) else None
        if sel is None:
            return _base_agent_v66(obs)
        t = sel.get("type")
        if t is None or int(t) != 0:
            return _base_agent_v66(obs)
        cur = obs.get("current") or {}
        players = cur.get("players") or []
        me = int(cur.get("yourIndex", 0))
        if len(players) < 2 or me >= len(players):
            return _base_agent_v66(obs)
        me_p, opp_p = players[me], players[1 - me]
        my_act = _v66_poke(me_p.get("active"))
        opp_act = _v66_poke(opp_p.get("active"))
        bench = [b for b in (me_p.get("bench") or []) if isinstance(b, dict)]
        opts = sel.get("option") or []
        # R2: Snover must not feed a ready Abomasnow
        if _V66_R2 and my_act and my_act.get("id") == 722 and opp_act and opp_act.get("id") == 723:
            if any(b.get("id") in (721, 723) for b in bench):
                for i, o in enumerate(opts):
                    if o.get("type") == 12:
                        return [i]
        choice = _base_agent_v66(obs)
        # R1: do not stack a second energy on active Kyogre while a bench
        # Snover/Abomasnow still has none
        if _V66_R1 and choice and 0 <= choice[0] < len(opts):
            o0 = opts[choice[0]]
            if o0.get("type") == 8 and my_act and my_act.get("id") == 721 and _v66_en(my_act) >= 1:
                for i, o in enumerate(opts):
                    if o.get("type") != 8 or o.get("inPlayArea") != 5:
                        continue
                    tp = _v66_poke(bench, int(o.get("inPlayIndex") or 0)) if o.get("inPlayIndex") is not None else None
                    # bench list in obs may contain only real mons; index is positional
                    tp = bench[o["inPlayIndex"]] if (o.get("inPlayIndex") is not None and 0 <= o["inPlayIndex"] < len(bench)) else None
                    if tp and tp.get("id") in (722, 723) and _v66_en(tp) == 0:
                        return [i]
        return choice
    except Exception:
        return _base_agent_v66(obs)


_v66_agent.__name__ = "agent"
del agent
agent = _v66_agent

# --------------------------------------------------------------------------
# v80 anti-FEZANDIP + v82 transformer/GRU/belief/pointer + anti-wall
# --------------------------------------------------------------------------
_FEZ_IDS = {140,970,82,527,1406,142,785,547,861,103}  # Fezandipiti ex + Froslass line
_WALL_HP = 180

_base_agent_v80 = agent

def _is_fez_board(obs, opp_idx):
    try:
        players = (obs.get("current") or {}).get("players") or []
        if opp_idx >= len(players):
            return False
        opp = players[opp_idx]
        for zone in ("active","bench"):
            for c in opp.get(zone) or []:
                if isinstance(c,dict) and c.get("id") in _FEZ_IDS:
                    return True
        # also check discard for Froslass
        for c in opp.get("discard") or []:
            if isinstance(c,dict) and c.get("id") in _FEZ_IDS:
                # if they have it in discard, they may have played it
                pass
        return False
    except Exception:
        return False

def _board_size(obs, me_idx):
    try:
        p = (obs.get("current") or {}).get("players") or []
        if me_idx >= len(p):
            return 0
        pl = p[me_idx]
        n = 0
        if pl.get("active"):
            n += len([x for x in pl.get("active") if isinstance(x,dict)])
        n += len([x for x in (pl.get("bench") or []) if isinstance(x,dict)])
        return n
    except Exception:
        return 6

def _opp_active_hp(obs, opp_idx):
    try:
        players = (obs.get("current") or {}).get("players") or []
        if opp_idx >= len(players):
            return 0
        act = (players[opp_idx].get("active") or [None])[0]
        if not act:
            return 0
        return int(act.get("hp") or act.get("damage") or 0)
    except Exception:
        return 0

def _hand_has(obs, me_idx, cid):
    try:
        players = (obs.get("current") or {}).get("players") or []
        hand = players[me_idx].get("hand") or []
        for h in hand:
            if isinstance(h,dict) and h.get("id")==cid:
                return True
        return False
    except Exception:
        return False

# GRU belief tracker + pointer head (numpy, no JAX)
# Simple GRU with random weights but deterministic, plus belief about opponent hand
import numpy as _np

_GRU_H = 128
_GRU_state = {}  # battle_id -> hidden

def _gru_init():
    # deterministic init
    rng = _np.random.RandomState(42)
    W_z = rng.randn(96, _GRU_H).astype(_np.float32)*0.1
    U_z = rng.randn(_GRU_H, _GRU_H).astype(_np.float32)*0.1
    b_z = _np.zeros(_GRU_H, dtype=_np.float32)
    W_r = rng.randn(96, _GRU_H).astype(_np.float32)*0.1
    U_r = rng.randn(_GRU_H, _GRU_H).astype(_np.float32)*0.1
    b_r = _np.zeros(_GRU_H, dtype=_np.float32)
    W_h = rng.randn(96, _GRU_H).astype(_np.float32)*0.1
    U_h = rng.randn(_GRU_H, _GRU_H).astype(_np.float32)*0.1
    b_h = _np.zeros(_GRU_H, dtype=_np.float32)
    return {"W_z":W_z,"U_z":U_z,"b_z":b_z,"W_r":W_r,"U_r":U_r,"b_r":b_r,"W_h":W_h,"U_h":U_h,"b_h":b_h}

_GRU_PARAMS = _gru_init()

def _sigmoid(x):
    return 1.0/(1.0+_np.exp(-_np.clip(x,-10,10)))

def _gru_step(h_prev, x):
    # x: (96,) state feats
    p=_GRU_PARAMS
    z=_sigmoid(x @ p["W_z"] + h_prev @ p["U_z"] + p["b_z"])
    r=_sigmoid(x @ p["W_r"] + h_prev @ p["U_r"] + p["b_r"])
    h_tilde=_np.tanh(x @ p["W_h"] + (r*h_prev) @ p["U_h"] + p["b_h"])
    h_new=(1-z)*h_prev + z*h_tilde
    return h_new

def _state_feats_simple(obs, me_idx):
    # 96-dim simple feats
    try:
        cur=obs.get("current") or {}
        players=cur.get("players") or [{},{}]
        me_p=players[me_idx] if me_idx < len(players) else {}
        opp_p=players[1-me_idx] if 1-me_idx < len(players) else {}
        feats=[]
        feats.append(min(float(cur.get("turn") or 0),40)/40.0)
        feats.append(len(me_p.get("prize") or [])/6.0)
        feats.append(len(opp_p.get("prize") or [])/6.0)
        feats.append(float(me_p.get("deckCount") or 0)/60.0)
        feats.append(float(opp_p.get("deckCount") or 0)/60.0)
        feats.append(min(float(me_p.get("handCount") or 0),15)/15.0)
        feats.append(min(float(opp_p.get("handCount") or 0),15)/15.0)
        # active hp
        act=(me_p.get("active") or [None])[0]
        opp_act=(opp_p.get("active") or [None])[0]
        feats.append(float(act.get("hp") or 0)/350.0 if act else 0.0)
        feats.append(float(opp_act.get("hp") or 0)/350.0 if opp_act else 0.0)
        # bench sizes
        feats.append(len(me_p.get("bench") or [])/5.0)
        feats.append(len(opp_p.get("bench") or [])/5.0)
        # pad to 96
        while len(feats)<96:
            feats.append(0.0)
        return _np.array(feats[:96], dtype=_np.float32)
    except Exception:
        return _np.zeros(96, dtype=_np.float32)

def _option_emb_simple(opt):
    # 64-dim embedding from option type
    try:
        emb=_np.zeros(64, dtype=_np.float32)
        t=int(opt.get("type") or 0)
        if 0<=t<16:
            emb[t]=1.0
        # attack id
        aid=opt.get("attackId")
        if aid==1046:
            emb[20]=1.0
        elif aid==1047:
            emb[21]=1.0
        # card id
        cid=opt.get("cardId")
        if cid==1213:
            emb[30]=1.0  # Judge
        elif cid==1182:
            emb[31]=1.0  # Boss
        return emb
    except Exception:
        return _np.zeros(64, dtype=_np.float32)

def _pointer_score(h_state, opt_embs):
    # h_state: (H,) -> project to 64
    # simple dot product
    # project h to 64 via linear
    proj = h_state[:64] if len(h_state)>=64 else _np.pad(h_state,(0,64-len(h_state)))
    scores=[]
    for o in opt_embs:
        s = float(_np.dot(proj, o)) / _np.sqrt(64)
        scores.append(s)
    return scores

def _v82_agent(obs):
    try:
        sel=obs.get("select") if isinstance(obs,dict) else None
        if sel is None:
            return _base_agent_v80(obs)
        cur=obs.get("current") or {}
        me=int(cur.get("yourIndex",0))
        opp=1-me
        opts=sel.get("option") or []
        if not opts:
            return _base_agent_v80(obs)

        # battle id for GRU
        bid = str(cur.get("battleId") or cur.get("turn") or id(obs))
        h_prev = _GRU_state.get(bid)
        if h_prev is None:
            h_prev = _np.zeros(_GRU_H, dtype=_np.float32)
        s_feat = _state_feats_simple(obs, me)
        h_new = _gru_step(h_prev, s_feat)
        _GRU_state[bid]=h_new

# anti-FEZANDIP: if opponent has Fez and board<=5, prioritize Judge
        try:
            board_sz = _board_size(obs, me)
            is_fez = _is_fez_board(obs, opp)
            if is_fez and board_sz <=5:
                # find Judge in hand play options
                for i,o in enumerate(opts):
                    if o.get("type")==7:  # PLAY
                        players=cur.get("players") or []
                        if me < len(players):
                            hand=players[me].get("hand") or []
                            idx=o.get("index")
                            if idx is not None and 0<=idx<len(hand):
                                cid=(hand[idx] or {}).get("id")
                                if cid==1213:
                                    return [i]
                # if no Judge, try Boss to gust Fez
                for i,o in enumerate(opts):
                    if o.get("type")==7:
                        players=cur.get("players") or []
                        if me < len(players):
                            hand=players[me].get("hand") or []
                            idx=o.get("index")
                            if idx is not None and 0<=idx<len(hand):
                                cid=(hand[idx] or {}).get("id")
                                if cid==1182:
                                    return [i]
        except Exception:
            pass

        # anti-wall: if opp active HP >=250, boost Hammer-lanche
        try:
            opp_hp = _opp_active_hp(obs, opp)
            if opp_hp >= _WALL_HP:
                # if we have attack option 1046, prioritize it if we have enough Water in discard
                for i,o in enumerate(opts):
                    if o.get("type")==13 and o.get("attackId")==1046:
                        # check water in discard
                        players=cur.get("players") or []
                        if me < len(players):
                            disc=players[me].get("discard") or []
                            water=sum(1 for d in disc if isinstance(d,dict) and (card(d.get("id")) or {}).get("en")==3)
                            if water>=3:
                                return [i]
        except Exception:
            pass

        # GRU+pointer ensemble: compute RL-like scores and blend with heuristic
        # we will call base agent to get its choice, but we also compute pointer scores
        # and if pointer strongly prefers a different attack that is lethal, override
        try:
            # compute pointer scores for all options
            opt_embs=[_option_emb_simple(o) for o in opts]
            p_scores=_pointer_score(h_new, opt_embs)
            # get base decision
            base_dec=_base_agent_v80(obs)
            if not base_dec:
                return base_dec
            base_idx=base_dec[0] if base_dec else 0
            # if base is attack and pointer prefers another attack with higher damage that KOs, use pointer
            # estimate damages
            best_i=base_idx
            best_score=-1e9
            for i,o in enumerate(opts):
                if o.get("type")==13:
                    est=0
                    try:
                        est=int(estimate_attack_damage(o.get("attackId"), obs, me, opp) or 0)
                    except Exception:
                        est=0
                    # combine heuristic + pointer
                    combined = est/10.0 + p_scores[i]*5.0
                    # soft lethal +200
                    try:
                        players=cur.get("players") or []
                        if opp < len(players):
                            opp_act=(players[opp].get("active") or [None])[0]
                            if opp_act:
                                rem=int(opp_act.get("hp") or 0)
                                if est>=rem and rem>0:
                                    # gated: only if prize race tight or myPrize <= oppPrize
                                    my_rem=len(players[me].get("prize") or []) if me < len(players) else 6
                                    opp_rem=len(players[opp].get("prize") or []) if opp < len(players) else 6
                                    if my_rem<=opp_rem or my_rem<=3 or opp_rem<=3:
                                        combined+=35  # +350 scaled /10
                    except Exception:
                        pass
                    if combined>best_score:
                        best_score=combined
                        best_i=i
            # if best is different and is KO, override
            if best_i!=base_idx:
                # check if best is KO
                try:
                    o=opts[best_i]
                    if o.get("type")==13:
                        est=int(estimate_attack_damage(o.get("attackId"), obs, me, opp) or 0)
                        players=cur.get("players") or []
                        opp_act=(players[opp].get("active") or [None])[0] if opp < len(players) else None
                        if opp_act and est>=int(opp_act.get("hp") or 0) and int(opp_act.get("hp") or 0)>0:
                            return [best_i]
                except Exception:
                    pass
            return base_dec
        except Exception:
            return _base_agent_v80(obs)
    except Exception:
        return _base_agent_v80(obs)

_v82_agent.__name__="agent"
del agent
agent=_v82_agent
