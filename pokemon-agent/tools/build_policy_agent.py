#!/usr/bin/env python3
"""Assemble agents/main_policy_v58.py = policy_feats + numpy MLP (weights b64)."""
from __future__ import annotations

import base64
import io
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TAIL = '''

# ---------------- learned policy (numpy inference) ----------------
import os as _os
import numpy as _np

_W = None
_FZ = None
_DECK = None


def _cand_dirs():
    dirs = []
    try:
        dirs.append(_os.path.dirname(_os.path.abspath(__file__)))
    except Exception:
        pass
    dirs.append(_os.getcwd())
    dirs.append("/kaggle_simulations/agent")
    return [d for d in dirs if d]


def _load_json_card_index():
    for d in _cand_dirs():
        p = _os.path.join(d, "card_index.json")
        if _os.path.exists(p):
            import json as _json
            with open(p, encoding="utf-8") as fh:
                return _json.load(fh)
    return {"cards": {}, "attacks": {}}


def _load_deck():
    for d in _cand_dirs():
        p = _os.path.join(d, "deck.csv")
        if _os.path.exists(p):
            ids = []
            with open(p, encoding="utf-8") as fh:
                for tok in fh.read().replace(",", " ").split():
                    try:
                        ids.append(int(tok))
                    except Exception:
                        pass
            if len(ids) == 60:
                return ids
    return []


def _policy_init():
    global _W, _FZ, _DECK
    if _W is not None:
        return
    import base64 as _b64
    raw = _b64.b64decode(_WEIGHTS_B64)
    _W = dict(_np.load(io.BytesIO(raw)))
    _FZ = Featurizer(_load_json_card_index())
    _DECK = _load_deck()


def _scores(S, O):
    W = _W
    import numpy as np
    B, N, DO = O.shape
    DS = S.shape[1]
    x = np.concatenate([np.broadcast_to(S[:, None, :], (B, N, DS)), O], axis=-1).reshape(B * N, DS + DO)
    h = x @ W["W1"] + W["b1"]
    h = np.where(h > 0, h, h * 0.01) + h * 0.0  # placeholder (gelu approx below)
    # gelu approx: 0.5*x*(1+tanh(0.79788456*(x+0.044715*x^3)))
    def gelu(v):
        return 0.5 * v * (1.0 + np.tanh(0.7978845608 * (v + 0.044715 * v ** 3)))
    h = gelu(x @ W["W1"] + W["b1"])
    h = gelu(h @ W["W2"] + W["b2"])
    return (h @ W["W3"] + W["b3"]).reshape(B, N)


def agent(obs):
    try:
        _policy_init()
        sel = obs.get("select") if isinstance(obs, dict) else None
        if sel is None:
            return list(_DECK)
        cur = obs.get("current") or {}
        me = int(cur.get("yourIndex", 0))
        opts = sel.get("option") or []
        if not opts:
            return []
        S = _np.array([_FZ.state_feats(obs, me)], dtype=_np.float32)
        scores = []
        for i0 in range(0, len(opts), MAX_OPT):
            chunk = opts[i0:i0 + MAX_OPT]
            O = _np.zeros((1, MAX_OPT, DO), dtype=_np.float32)
            for j, o in enumerate(chunk):
                O[0, j] = _FZ.option_feats(o, obs, me)
            sc = _scores(S, O)[0]
            scores.extend(float(sc[j]) for j in range(len(chunk)))
        order = sorted(range(len(opts)), key=lambda i: -scores[i])
        mx = int(sel.get("maxCount") or 1)
        mn = int(sel.get("minCount") or 0)
        k = max(mx, mn, 1)
        return order[:k]
    except Exception:
        try:
            sel = obs.get("select") or {}
            mn = int(sel.get("minCount") or 1)
            return list(range(max(mn, 1)))
        except Exception:
            return [0]
'''


def main():
    feats = (ROOT / "tools/policy_feats.py").read_text()
    marker = feats.index("DS = ")
    feats_body = feats[marker:]
    weights = (ROOT / "kaggle_results/policy_v58.npz").read_bytes()
    b64 = base64.b64encode(weights).decode()
    out = ("# v58 POLICY (a450): learned option-scorer, BC from champion v44 self-play.\n"
           "# Inference: pure numpy. Weights: kaggle_results/policy_v58.npz (JAX-trained).\n"
           "import io\n"
           f"_WEIGHTS_B64 = '{b64}'\n") + feats_body + TAIL
    (ROOT / "agents/main_policy_v58.py").write_text(out)
    print("wrote agents/main_policy_v58.py", len(out), "bytes")


if __name__ == "__main__":
    main()
