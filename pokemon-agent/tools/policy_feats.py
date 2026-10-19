#!/usr/bin/env python3
"""Feature extraction for the v58 learned option-scorer policy.

STATE: fixed vector describing the board from the deciding player's view.
OPTION: fixed vector per legal option (card stats, target stats, attack math).
Self-contained apart from a card_index dict ({cards: {id: rec}, attacks: {id: rec}}).
"""
from __future__ import annotations

DS = 96
DO = 64
MAX_OPT = 32

_OTYPES = 16
_AREAS = 13


def _f(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default


class Featurizer:
    def __init__(self, card_index: dict):
        self.cards = card_index.get("cards") or {}
        self.attacks = card_index.get("attacks") or {}

    def card(self, cid):
        if cid is None:
            return {}
        return self.cards.get(str(int(cid))) or {}

    def attack(self, aid):
        if aid is None:
            return {}
        return self.attacks.get(str(int(aid))) or {}

    def card_feats(self, cid):
        """14-dim card summary."""
        c = self.card(cid)
        if not c:
            return [0.0] * 14
        atks = c.get("atk") or []
        best_dmg, min_cost = 0.0, 4.0
        for aid in atks:
            a = self.attack(aid)
            best_dmg = max(best_dmg, _f(a.get("d")))
            e = a.get("e") or []
            min_cost = min(min_cost, float(len(e)) if e else 4.0)
        ex = 1.0 if c.get("ex") else 0.0
        mex = 1.0 if c.get("mex") else 0.0
        prize = 3.0 if mex else (2.0 if ex else 1.0)
        return [
            1.0 if c.get("ct") == 0 else 0.0,          # pokemon
            1.0 if c.get("b") else 0.0,                # basic
            _f(c.get("et")) / 3.0,                     # stage
            _f(c.get("hp")) / 350.0,
            ex, mex,
            1.0 if c.get("ace") else 0.0,
            _f(c.get("rc")) / 4.0,                     # retreat cost
            best_dmg / 300.0,
            min_cost / 4.0,
            prize / 3.0,
            _f(c.get("en")) / 12.0,                    # energy type
            1.0 if (c.get("ct") in (1, 2)) else 0.0,   # item/tool
            1.0 if c.get("ct") == 3 else 0.0,          # supporter
        ]

    def _poke_block(self, poke):
        """10-dim summary of one in-play pokemon dict (or zeros)."""
        if not isinstance(poke, dict):
            return [0.0] * 10
        cid = poke.get("id")
        c = self.card(cid)
        hp = _f(c.get("hp"))
        cur_hp = hp - _f(poke.get("damage", poke.get("damageCounter", 0))) * 1.0
        # engine uses damage counters in units of 10 sometimes; guard both
        dmg = _f(poke.get("damage", 0))
        if dmg > hp and hp > 0:
            dmg = dmg / 10.0
        cur_hp = max(hp - dmg, 0.0)
        energies = poke.get("energies") or poke.get("energy") or []
        n_en = len(energies) if isinstance(energies, list) else _f(energies)
        atks = c.get("atk") or []
        best = 0.0
        for aid in atks:
            best = max(best, _f(self.attack(aid).get("d")))
        ex = 1.0 if c.get("ex") else 0.0
        mex = 1.0 if c.get("mex") else 0.0
        return [
            (cur_hp / hp) if hp > 0 else 0.0,
            hp / 350.0,
            min(n_en, 8) / 8.0,
            _f(c.get("et")) / 3.0,
            ex, mex,
            (3.0 if mex else (2.0 if ex else 1.0)) / 3.0,
            best / 300.0,
            1.0 if poke.get("id") is not None else 0.0,
            min(_f(poke.get("tool", 0)) if isinstance(poke.get("tool"), (int, float)) else (1.0 if poke.get("tool") else 0.0), 1.0),
        ]

    def _board_block(self, player):
        """active block (10) + bench aggregate (8)."""
        if not isinstance(player, dict):
            return [0.0] * 18
        active = player.get("active") or []
        act = self._poke_block(active[0] if active else None)
        bench = [p for p in (player.get("bench") or []) if isinstance(p, dict)]
        agg = [0.0] * 8
        if bench:
            blocks = [self._poke_block(p) for p in bench[:5]]
            agg[0] = len(blocks) / 5.0
            agg[1] = sum(b[0] for b in blocks) / 5.0
            agg[2] = max(b[7] for b in blocks)
            agg[3] = sum(b[2] for b in blocks) / 2.0
            agg[4] = sum(b[4] + b[5] for b in blocks) / 5.0
            agg[5] = sum(b[6] for b in blocks) / 2.0
            agg[6] = max(b[1] for b in blocks)
            agg[7] = 1.0
        return act + agg

    def state_feats(self, obs, me):
        cur = obs.get("current") or {}
        players = cur.get("players") or [{}, {}]
        if len(players) < 2:
            return [0.0] * DS
        opp = 1 - me
        mp, op = players[me], players[opp]
        out = []
        out.append(min(_f(cur.get("turn")), 40) / 40.0)
        out.append(1.0 if cur.get("firstPlayer") == me else 0.0)
        out.append(1.0 if cur.get("supporterPlayed") else 0.0)
        out.append(1.0 if cur.get("energyAttached") else 0.0)
        out.append(1.0 if cur.get("retreated") else 0.0)
        out.append(1.0 if cur.get("stadium") else 0.0)
        out.append((6 - len(mp.get("prize") or [])) / 6.0)
        out.append((6 - len(op.get("prize") or [])) / 6.0)
        out.append(_f(mp.get("deckCount")) / 60.0)
        out.append(_f(op.get("deckCount")) / 60.0)
        out.append(min(_f(mp.get("handCount", len(mp.get("hand") or []))), 15) / 15.0)
        out.append(min(_f(op.get("handCount", len(op.get("hand") or []))), 15) / 15.0)
        disc = mp.get("discard") or []
        water_disc = sum(1 for d in disc if isinstance(d, dict) and self.card(d.get("id")).get("en") == 3)
        out.append(min(len(disc), 40) / 40.0)
        out.append(min(water_disc, 20) / 20.0)
        out.append(min(_f(cur.get("turnActionCount")), 20) / 20.0)
        out.append(1.0 if me == cur.get("yourIndex") else 0.0)
        out += self._board_block(mp)   # 18
        out += self._board_block(op)   # 18
        # hand composition (mine only)
        hand = mp.get("hand") or []
        basics = sum(1 for h in hand if isinstance(h, dict) and self.card(h.get("id")).get("b"))
        energies = sum(1 for h in hand if isinstance(h, dict) and self.card(h.get("id")).get("ct") in (5, 6))
        out.append(min(len(hand), 15) / 15.0)
        out.append(min(basics, 6) / 6.0)
        out.append(min(energies, 8) / 8.0)
        # pad to DS
        out = out[:DS]
        out += [0.0] * (DS - len(out))
        return out

    def _resolve_card(self, opt, obs, me):
        if opt.get("cardId") is not None:
            return opt.get("cardId")
        area, idx = opt.get("area"), opt.get("index")
        if idx is None:
            return None
        cur = obs.get("current") or {}
        players = cur.get("players") or []
        owner = opt.get("playerIndex", me)
        try:
            if area == 2 and owner == me:  # HAND
                hand = players[me].get("hand") or []
                return (hand[idx] or {}).get("id") if 0 <= idx < len(hand) else None
            if area == 1 and owner == me:  # DECK via select deck reveal
                deck = (obs.get("select") or {}).get("deck") or []
                if 0 <= idx < len(deck):
                    e = deck[idx]
                    return e.get("id") if isinstance(e, dict) else e
                return None
            # board areas
            zone = "active" if area == 4 else ("bench" if area == 5 else None)
            if zone and 0 <= owner < len(players):
                z = players[owner].get(zone) or []
                return (z[idx] or {}).get("id") if 0 <= idx < len(z) else None
        except Exception:
            return None
        return None

    def _target_poke(self, opt, obs, me):
        area = opt.get("inPlayArea")
        idx = opt.get("inPlayIndex")
        if area not in (4, 5) or idx is None:
            return None, None
        cur = obs.get("current") or {}
        players = cur.get("players") or []
        zone = "active" if area == 4 else "bench"
        cands = []
        for owner in (me, 1 - me):
            if 0 <= owner < len(players):
                z = players[owner].get(zone) or []
                if 0 <= idx < len(z) and isinstance(z[idx], dict):
                    cands.append((owner, z[idx]))
        # ATTACH/EVOLVE target own, others default to first found (mine preferred ordering above is me first)
        if opt.get("type") in (8, 9):
            return (me, cands[0][1]) if cands else (None, None)
        return cands[0] if cands else (None, None)

    def option_feats(self, opt, obs, me, state_cache=None):
        cur = obs.get("current") or {}
        players = cur.get("players") or [{}, {}]
        opp = 1 - me
        out = [0.0] * DO
        otype = int(opt.get("type") or 0)
        if 0 <= otype < _OTYPES:
            out[otype] = 1.0
        area = int(opt.get("area") or 0)
        if 0 <= area < _AREAS:
            out[16 + area] = 1.0
        ipa = int(opt.get("inPlayArea") or 0)
        if 0 <= ipa < _AREAS:
            out[29 + ipa] = 1.0
        cid = self._resolve_card(opt, obs, me)
        cf = self.card_feats(cid)
        out[42:56] = cf
        # attack-specific
        if otype == 13:  # ATTACK
            a = self.attack(opt.get("attackId"))
            dmg = _f(a.get("d"))
            cost = len(a.get("e") or [])
            opp_active = (players[opp].get("active") or [None])[0] if len(players) > opp else None
            blk = self._poke_block(opp_active)
            out[56] = dmg / 300.0
            out[57] = cost / 4.0
            out[58] = 1.0 if (blk[0] * blk[1] * 350.0) <= dmg and dmg > 0 else 0.0  # lethal on active
            out[59] = (dmg / 300.0) * blk[6]  # damage x prize value
        # target pokemon block summary (4)
        towner, tpoke = self._target_poke(opt, obs, me)
        if tpoke is not None:
            tb = self._poke_block(tpoke)
            out[60] = tb[0]
            out[61] = tb[2]
            out[62] = tb[6]
            out[63] = 1.0 if towner == me else 0.0
        return out
