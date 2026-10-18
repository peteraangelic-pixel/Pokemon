"""Features for the RL policy: board tokens (transformer input), global state
(96d, tools/policy_feats), per-option features (64d) + belief features.

Belief: BeliefTracker utrzymuje per gre zbior kart przeciwnika juz widzianych
(lawka/aktywny/odrzucone + logi), zeby model mogl szacowac niewidoczna reke.
"""
from __future__ import annotations
import sys
sys.path.insert(0, 'tools')
from policy_feats import Featurizer, DS, DO, MAX_OPT  # noqa: E402

TOK_DIM = 14
MAX_TOK = 13  # 6 swoich + 6 opp + token globalny


class BeliefTracker:
    """Widoczne karty przeciwnika w trakcie jednej gry."""
    def __init__(self):
        self.reset()

    def reset(self):
        self.opp_seen = {}       # card_id -> liczba widzianych kopii (stale)
        self.opp_discard_seen = {}

    def observe(self, obs, me):
        try:
            cur = obs.get("current") or {}
            players = cur.get("players") or []
            if len(players) < 2:
                return
            opp = players[1 - me]
            for zone in ("active", "bench"):
                for c in opp.get(zone) or []:
                    if isinstance(c, dict) and c.get("id") is not None:
                        self.opp_seen[int(c["id"])] = self.opp_seen.get(int(c["id"]), 0) + 0  # tylko obecnosc
            for c in opp.get("discard") or []:
                if isinstance(c, dict) and c.get("id") is not None:
                    self.opp_discard_seen[int(c["id"])] = self.opp_discard_seen.get(int(c["id"]), 0) + 1
        except Exception:
            pass

    def feats(self, obs, me):
        """8d: ile juz wiemy o talii/rece przeciwnika."""
        try:
            cur = obs.get("current") or {}
            players = cur.get("players") or []
            opp = players[1 - me]
            board_n = 0
            for zone in ("active", "bench"):
                board_n += sum(1 for c in opp.get(zone) or [] if isinstance(c, dict))
            disc_n = len(opp.get("discard") or [])
            return [
                min(len(self.opp_seen), 20) / 20.0,
                min(sum(self.opp_discard_seen.values()), 30) / 30.0,
                min(board_n, 6) / 6.0,
                min(disc_n, 40) / 40.0,
                min(float(opp.get("handCount") or 0), 15) / 15.0,
                min(float(opp.get("deckCount") or 0), 60) / 60.0,
                min(len(opp.get("prize") or []), 6) / 6.0,
                1.0 if board_n else 0.0,
            ]
        except Exception:
            return [0.0] * 8


class RLFeaturizer:
    def __init__(self, card_index):
        self.fz = Featurizer(card_index)
        self.belief = BeliefTracker()

    def tokens(self, obs, me):
        """[MAX_TOK x TOK_DIM]: moje pokemony, opp pokemony, token globalny."""
        fz = self.fz
        cur = obs.get("current") or {}
        players = cur.get("players") or [{}, {}]
        toks = []
        for side, pl in ((0, players[me] if len(players) > me else {}),
                         (1, players[1 - me] if len(players) > 1 - me else {})):
            act = pl.get("active") or []
            slots = [act[0] if act else None] + list(pl.get("bench") or [])[:5]
            slots += [None] * (6 - len(slots))
            for pos, pk in enumerate(slots[:6]):
                blk = fz._poke_block(pk)
                toks.append(blk + [float(side), pos / 5.0,
                                   1.0 if pos == 0 else 0.0,
                                   1.0 if pk else 0.0])
        g = fz.state_feats(obs, me)
        toks.append([x for x in g[:10]] + [0.0, 0.0, 0.0, 1.0])  # global token marker
        return toks

    def encode(self, obs, me):
        """Zwraca (tokens, state(96+8 belief), options[MAX_OPT x DO], mask, nopts)."""
        self.belief.observe(obs, me)
        st = self.fz.state_feats(obs, me) + self.belief.feats(obs, me)
        sel = obs.get("select") or {}
        raw = sel.get("option") or []
        n = min(len(raw), MAX_OPT)
        opts = [[0.0] * DO for _ in range(MAX_OPT)]
        mask = [0.0] * MAX_OPT
        for i in range(n):
            try:
                opts[i] = self.fz.option_feats(raw[i], obs, me)
                mask[i] = 1.0
            except Exception:
                pass
        return self.tokens(obs, me), st, opts, mask, n
