"""Buduje samodzielny main.py agenta RL (v76): featurizer + features +
numpy transformer + wagi (base64) + champion v67 jako fallback + lethal-win.
Wynik: agents/v76_rl_main.py (jeden plik, tylko numpy+stdlib)."""
import base64, io, re

def read(p):
    return open(p).read()

feats = read('tools/policy_feats.py')
feats = feats.replace('#!/usr/bin/env python3\n', '').replace('from __future__ import annotations\n', '')
rlfeat = read('rl/features.py')
rlfeat = rlfeat.split('class BeliefTracker')[1]
rlfeat = 'class BeliefTracker' + rlfeat
rlfeat = rlfeat.replace('from policy_feats import Featurizer, DS, DO, MAX_OPT  # noqa: E402\n', '')
npmodel = read('rl/numpy_model.py')
champ = read('agents/v67_wall_tempo_noimit.py')
w = base64.b64encode(open('rl/params_best.npz', 'rb').read()).decode()

glue = '''
# ---------------- v76 glue: model RL (MAIN) + champion fallback + lethal-win
import base64 as _b64, io as _io, os as _os
_PARAMS = np.load(_io.BytesIO(_b64.b64decode(_W_B64)))
_W = {k: _PARAMS[k] for k in _PARAMS.files}
_RFZ = None

def _ci_path():
    for cand in (_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "card_index.json"),
                 "card_index.json", "/kaggle_simulations/agent/card_index.json"):
        if _os.path.exists(cand):
            return cand
    return None

def _rl_choice(obs, me):
    global _RFZ
    if _RFZ is None:
        _RFZ = RLFeaturizer(json.load(open(_ci_path())))
    enc = _RFZ.encode(obs, me)
    tok = np.array([enc[0]], np.float32); st = np.array([enc[1]], np.float32)
    opts = np.array([enc[2]], np.float32); mask = np.array([enc[3]], np.float32)
    logits, _v = forward(_W, tok, st, opts, mask)
    return int(np.argmax(logits[0][:max(enc[4], 1)]))

_champ_agent_v76 = agent  # champion v67 (zdefiniowany powyzej)

def agent(obs):
    try:
        if not isinstance(obs, dict) or obs.get("select") is None:
            return _champ_agent_v76(obs)
        sel = obs.get("select") or {}
        tt = sel.get("type")
        if tt is None or int(tt) != 0 or int(sel.get("maxCount") or 1) != 1:
            return _champ_agent_v76(obs)
        cur = obs.get("current") or {}
        players = cur.get("players") or []
        me = int(cur.get("yourIndex", 0))
        if len(players) < 2:
            return _champ_agent_v76(obs)
        # lethal-win override: atak bioracy ostatnie nagrody wygrywa od razu
        try:
            my_rem = len(players[me].get("prize") or [])
            opp_act = (players[1 - me].get("active") or [None])[0]
            if opp_act and my_rem:
                ci = json.load(open(_ci_path()))
                cards = ci.get("cards") or {}
                attacks = ci.get("attacks") or {}
                oc = cards.get(str(opp_act.get("id"))) or {}
                pv = 3 if oc.get("mex") else (2 if oc.get("ex") else 1)
                hp = float(opp_act.get("hp") or 0)
                if pv >= my_rem and hp > 0:
                    for i, o in enumerate(sel.get("option") or []):
                        if o.get("type") == 13:
                            a = attacks.get(str(o.get("attackId"))) or {}
                            if float(a.get("d") or 0) >= hp:
                                return [i]
        except Exception:
            pass
        return [_rl_choice(obs, me)]
    except Exception:
        return _champ_agent_v76(obs)
'''

for _part in ('feats', 'rlfeat', 'npmodel', 'champ'):
    pass
feats = feats.replace('from __future__ import annotations\n', '')
rlfeat = rlfeat.replace('from __future__ import annotations\n', '')
npmodel = npmodel.replace('from __future__ import annotations\n', '')
champ = champ.replace('from __future__ import annotations\n', '')
out = []
out.append('from __future__ import annotations\n')
out.append('"""v76 RL: transformer+pointer (BC+PPO vs liga), champion v67 fallback."""\n')
out.append('import json\nimport numpy as np\n')
out.append(feats + '\n')
out.append(rlfeat + '\n')
out.append(npmodel + '\n')
out.append(f'_W_B64 = "{w}"\n')
out.append(champ + '\n')
out.append(glue)
open('agents/v76_rl_main.py', 'w').write(''.join(out))
print('agents/v76_rl_main.py zbudowany')
