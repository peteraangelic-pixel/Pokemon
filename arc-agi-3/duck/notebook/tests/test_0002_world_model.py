"""Patch 0002 (ARC3_WORLD_MODEL): executable world model helpers in the Python tool sandbox.

Runs the REAL sandbox (run_sandboxed_python) against a toy coin-collecting game so the whole
path is exercised: state payload -> check_model()/plan() -> action() -> automatic per-snippet
model check -> retained functions across snippets -> level change.
Run from ARC3-Inference/ (tests/run.sh does this).
"""
import json
import os
import sys
import time

sys.path.insert(0, ".")
os.environ["ARC3_WORLD_MODEL"] = "1"

import inference.utils.world_model as wm  # noqa: E402
from inference.agent.python_tool_sandbox import run_sandboxed_python  # noqa: E402

# ---------------------------------------------------------------- unit: helpers
assert wm.wm_parse_action("MOUSE(row=3, col=12)") == {"action": "MOUSE", "row": 3, "col": 12}
assert wm.wm_parse_action(" UP ") == "UP"
assert wm.wm_freeze({"b": [1, 2], "a": {3, 4}}) == wm.wm_freeze({"a": {4, 3}, "b": (1, 2)})
d = wm.wm_state_diff({"p": (1, 2), "coins": {(0, 0), (1, 1)}}, {"p": (1, 3), "coins": {(0, 0)}})
assert set(d) == {"p", "coins"} and "only_predicted" in d["coins"], d
print("helpers ok", d)

# ---------------------------------------------------------------- toy game
LEVELS = [
    {"walls": {(2, 2), (2, 3), (2, 4)}, "coins": {(0, 5), (4, 1)}, "player": (4, 4)},
    {"walls": {(1, 1), (3, 3), (4, 3), (5, 3)}, "coins": {(0, 0), (6, 6), (5, 5)}, "player": (6, 0)},
]
LEVELS.append(dict(LEVELS[0]))
N = 8
DIRS = {"UP": (-1, 0), "DOWN": (1, 0), "LEFT": (0, -1), "RIGHT": (0, 1)}


class Toy:
    def __init__(self):
        self.level = 0
        self.load()
        self.step_no = 0
        self.history = [{"action": "RESET", "frame": self.frame(), "result": {}}]  # as in the harness

    def load(self):
        lv = LEVELS[self.level]
        self.walls, self.coins, self.player = set(lv["walls"]), set(lv["coins"]), lv["player"]

    def grid(self):
        g = [[0] * N for _ in range(N)]
        for r, c in self.walls:
            g[r][c] = 5
        for r, c in self.coins:
            g[r][c] = 11
        r, c = self.player
        g[r][c] = 9
        return g

    def frame(self):
        g = self.grid()
        return {"ascii": "\n".join("".join("0123456789abcdef"[v] for v in row) for row in g),
                "step": self.step_no, "level": self.level + 1, "shape": [N, N], "grid": g}

    def act(self, name):
        dr, dc = DIRS[name]
        r, c = self.player[0] + dr, self.player[1] + dc
        if 0 <= r < N and 0 <= c < N and (r, c) not in self.walls:
            self.player = (r, c)
            self.coins.discard((r, c))
        self.step_no += 1
        result = {"executed": True, "level_completed": False, "game_over": False}
        if not self.coins:
            result["level_completed"] = True
            self.level += 1
            self.load()
        self.history.append({"action": name, "frame": self.frame(), "result": dict(result)})
        return result

    def state(self):
        return {"current_frame": self.frame(), "history": list(self.history),
                "valid_actions": ["UP", "DOWN", "LEFT", "RIGHT"], "last_action_call_result": {}}


game = Toy()
kept = []


def run(code):
    def handler(actions, stale_after=None):
        res = {}
        for a in actions:
            res = game.act(a["action"])
            if res.get("level_completed"):
                break
        return {"action_result": res, "state": game.state()}

    out = run_sandboxed_python(code=code, timeout_seconds=30, initial_state=game.state(),
                               action_handler=handler, kept_functions=list(kept))
    for f in out.get("keepable_functions") or []:
        kept[:] = [k for k in kept if not k.startswith(f"def {f['name']}(")] + [f["source"]]
    return out


# A deliberately incomplete model: walls block, but coins are never collected.
MODEL_V1 = '''
def model_state(frame):
    g = frame._grid
    cells = lambda v: frozenset((r, c) for r, row in enumerate(g) for c, x in enumerate(row) if x == v)
    return {"player": next(iter(cells(9))), "walls": cells(5), "coins": cells(11)}

def model_step(state, action):
    d = {"UP": (-1, 0), "DOWN": (1, 0), "LEFT": (0, -1), "RIGHT": (0, 1)}.get(action)
    if d is None:
        return None
    r, c = state["player"][0] + d[0], state["player"][1] + d[1]
    if not (0 <= r < 8 and 0 <= c < 8) or (r, c) in state["walls"]:
        return None
    return dict(state, player=(r, c))

def model_goal(state):
    return not state["coins"]
'''

# 1. no transitions yet; plan() cannot reach the goal with model v1 (coins never vanish)
out = run(MODEL_V1 + "\nprint(check_model())\nprint(plan(max_nodes=500))")
print("snippet1:", out["stdout"], out.get("error"))
assert "'checked': 0" in out["stdout"] and "'found': False" in out["stdout"], out
assert {k.split("(")[0][4:] for k in kept} >= {"model_state", "model_step", "model_goal"}, kept

# 2. act: one move onto empty cells, then one onto a coin -> the automatic check must flag the coin
out = run("action(['UP', 'UP'])\naction(['RIGHT'])")
print("snippet2:", out["stdout"], out.get("error"))
assert "[world model check] 3/3" in out["stdout"], out["stdout"]
out = run("action(['UP', 'UP', 'UP'])")  # (3,5) -> (2,5) -> (1,5) -> (0,5) = coin
print("snippet3:", out["stdout"], out.get("error"))
assert "[world model check] 2/3" in out["stdout"] and "coins" in out["stdout"], out["stdout"]

# 3. check_model over the whole level reports the miss with only the differing field
out = run("r = check_model()\nprint(r['correct'], r['checked'], r['by_action'])\nprint(r['mismatches'][0]['diff'])")
print("snippet4:", out["stdout"], out.get("error"))
assert out["stdout"].startswith("5 6") and "only_predicted" in out["stdout"], out["stdout"]

# 4. fix the model (coins are collected), verify, plan, execute the plan -> level 2
MODEL_V2_STEP = '''
def model_step(state, action):
    d = {"UP": (-1, 0), "DOWN": (1, 0), "LEFT": (0, -1), "RIGHT": (0, 1)}.get(action)
    if d is None:
        return None
    r, c = state["player"][0] + d[0], state["player"][1] + d[1]
    if not (0 <= r < 8 and 0 <= c < 8) or (r, c) in state["walls"]:
        return None
    return dict(state, player=(r, c), coins=state["coins"] - {(r, c)})
'''
t0 = time.time()
out = run(MODEL_V2_STEP + "\nr = check_model()\nprint('acc', r['accuracy'])\np = plan()\nprint(p)\naction(p['actions'])")
print("snippet5:", out["stdout"], out.get("error"), round(time.time() - t0, 2), "s")
assert "acc 1.0" in out["stdout"] and "'found': True" in out["stdout"], out["stdout"]
assert game.level == 1, game.level
assert "model_goal: 1/1 level wins predicted, 0 false wins" in out["stdout"], out["stdout"]

# 5. new level: retained model plans level 2 with a heuristic in one go
out = run("""
def h(s):
    p = s['player']
    return min((abs(p[0]-r)+abs(p[1]-c) for r, c in s['coins']), default=0) + 2*len(s['coins'])
p = plan(heuristic=h)
print(p['found'], p['length'])
action(p['actions'])
""")
print("snippet6:", out["stdout"], out.get("error"))
assert out["stdout"].startswith("True") and game.level == 2, (out, game.level)
print("all-level check:", run("r = check_model(scope='all'); print(r['correct'], r['checked'], r['goal'])")["stdout"])

# 6. model errors are reported, never crash the snippet
out = run("def model_step(state, action):\n    return state['nope']\naction(['DOWN'])\nprint('after')")
print("snippet7:", out["stdout"], out.get("error"))
assert "after" in out["stdout"] and "model errors" in out["stdout"], out

# 7. disabled -> helpers absent, no automatic line
os.environ["ARC3_WORLD_MODEL"] = "0"
out = run("try:\n    check_model\n    print('True')\nexcept NameError:\n    print('False')\naction(['UP'])")
assert out["stdout"].startswith("False") and "[world model check]" not in out["stdout"], out
print("disabled ok")

# 8. system prompt toggle
import inference.agent.tool_agent as t  # noqa: E402
os.environ.pop("ARC3_WORLD_MODEL", None)
p0 = t._build_system_prompt(tool_output_tokens=3072)
os.environ["ARC3_WORLD_MODEL"] = "1"
p1 = t._build_system_prompt(tool_output_tokens=3072)
assert "check_model" not in p0 and "check_model(scope='level'" in p1
print("prompt ok, delta chars:", len(p1) - len(p0))

# 9. per-turn world-model status (ARC3_WORLD_MODEL_NUDGE)
class A: pass
a = A()
a._kept_functions = {}
status = t.ToolAgent._arc3_world_model_status.__get__(a)
record = t.ToolAgent._arc3_wm_record.__get__(a)
os.environ.pop("ARC3_WORLD_MODEL_NUDGE", None)
assert status() == ""
os.environ["ARC3_WORLD_MODEL_NUDGE"] = "1"
assert "no `model_state`/`model_step` retained yet" in status(), status()
a._kept_functions = {"model_state": "def model_state(f):\n    return 1", "model_step": "def model_step(s, a):\n    return s"}
a._arc3_wm_carried = (a._kept_functions["model_state"], a._kept_functions["model_step"])
a._arc3_wm_level_totals = [0, 0, 0]
record({"stdout": "x\n[world model check] 3/4 of this snippet's ...; first miss t=2\n"})
record({"stdout": "[world model check] 0/0 of this snippet's transitions matched ...; 2 model errors, first: {}"})
st = status()
print(st)
assert "unchanged since the previous level" in st and "3/4 transitions predicted" in st
assert "raised 2 errors" in st and "`model_goal` is missing" in st
a._kept_functions["model_step"] = "def model_step(s, a):\n    return None"
assert "unchanged" not in status()
os.environ["ARC3_WORLD_MODEL"] = "0"
assert status() == ""
print("nudge ok")
print("ALL 0002 TESTS PASSED")
