"""Opponent surrogate: a board-development bot.

WHY: our local gauntlet is self-play — both seats run OUR agent, which has
the same thin-board defect (live forensics 2026-10-12: we play ~2-3 pokemon
of a 10-pokemon deck; live opponents play 4-5). Against a mirror of itself
the defect is invisible (both sides thin; tempo decides), so A/B results on
self-play pools overstate live strength.

thickbot plays like the live field on the development axis: always play a
basic while bench has room, evolve, attach, use searches, then attack.
Deliberately dumb about one-shot races — it exists to be DEVELOPED AGAINST,
not to be out-tempoed.
"""
import json
import os

try:
    _DB = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      os.pardir, "data", "cards.json")))
    _CARD = {str(c["cardId"]): c for c in _DB}
except Exception:
    _CARD = {}

DECK = []


def _basic(cid):
    c = _CARD.get(str(cid)) or {}
    return c.get("cardType") == 0 and c.get("basic", True)


def agent(obs: dict) -> list:
    if obs.get("select") is None:
        return list(DECK)
    sel = obs["select"]
    opts = sel.get("option") or []
    stype = sel.get("type")
    cur = obs.get("current") or {}
    me = int(cur.get("yourIndex") or 0)

    if stype == 0:  # MAIN
        hand = (cur.get("players") or [{}])[me].get("hand") or []

        def is_basic_play(o):
            if o.get("type") != 7 or o.get("index") is None:
                return False
            try:
                return _basic(hand[o["index"]].get("id"))
            except Exception:
                return False

        for i, o in enumerate(opts):          # 1) develop: play a basic
            if is_basic_play(o):
                return [i]
        for i, o in enumerate(opts):          # 2) evolve
            if o.get("type") == 9:
                return [i]
        for i, o in enumerate(opts):          # 3) attach energy
            if o.get("type") == 8:
                return [i]
        for i, o in enumerate(opts):          # 4) any other card (searches etc.)
            if o.get("type") in (1, 3, 7):
                return [i]
        for i, o in enumerate(opts):          # 5) attack
            if o.get("type") == 13:
                return [i]
        for i, o in enumerate(opts):          # 6) end
            if o.get("type") == 14:
                return [i]
        return [0]

    # non-MAIN selects: deterministic first choices
    k = min(int(sel.get("maxCount") or 1), len(opts))
    return list(range(max(k, 1)))
