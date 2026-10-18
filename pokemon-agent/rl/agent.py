"""Agent produkcyjny RL: decyzje MAIN z modelu (numpy), reszta delegowana
do championa v67. Brak params -> czysty champion (bezpieczny fallback)."""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, 'tools')
from rl.features import RLFeaturizer          # noqa: E402
from rl.numpy_model import forward            # noqa: E402

_W = None
_RFZ = None
_CHAMP = None


def _load():
    global _W, _RFZ, _CHAMP
    if _CHAMP is not None:
        return
    import importlib.util
    spec = importlib.util.spec_from_file_location("_champ_v67", "agents/v67_wall_tempo_noimit.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    _CHAMP = m.agent
    try:
        ci = json.load(open("card_index.json"))
        _RFZ = RLFeaturizer(ci)
        p = os.environ.get("PTCG_RL_PARAMS", "rl/params_best.npz")
        if os.path.exists(p):
            _W = dict(np.load(p))
    except Exception:
        _W = None


def agent(obs):
    _load()
    try:
        if not isinstance(obs, dict) or obs.get("select") is None:
            return _CHAMP(obs)
        sel = obs.get("select") or {}
        tt = sel.get("type")
        if _W is None or tt is None or int(tt) != 0 or int(sel.get("maxCount") or 1) != 1:
            return _CHAMP(obs)
        cur = obs.get("current") or {}
        me = int(cur.get("yourIndex", 0))
        enc = _RFZ.encode(obs, me)
        tok = np.array([enc[0]], np.float32); st = np.array([enc[1]], np.float32)
        opts = np.array([enc[2]], np.float32); mask = np.array([enc[3]], np.float32)
        logits, _ = forward(_W, tok, st, opts, mask)
        return [int(np.argmax(logits[0][:max(enc[4], 1)]))]
    except Exception:
        return _CHAMP(obs)
