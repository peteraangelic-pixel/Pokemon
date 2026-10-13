"""Offline feasibility check for a harness-run 'probe' of new level elements.

For every stuck level in a benchmark: replay to the START of that level, find object types that
were not present at the start of the previous level (= 'new elements'), then try cheap probes
on a copy of the game:
  * click games: click the centre cell of each new element once,
  * every game: each available simple action once,
and after each probe try UNDO (ACTION7) and check whether the board returns to the start state.
Prints per-level and aggregate stats. CPU only.

python probe_sim.py BENCH.json GAMES_DIR HARNESS_DIR [OUT.csv]
"""
import copy, csv, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from play import load_game
from arcengine import ActionInput, GameAction, GameState

bench, games_dir, harness = sys.argv[1:4]
out_csv = sys.argv[4] if len(sys.argv) > 4 else None
sys.path.insert(0, str(Path(harness) / "ARC3-Inference"))
from inference.utils.segmentation import segment_layer          # noqa: E402
from inference.utils.grid_utils import ARC_COLOR_CHARS           # noqa: E402


def frame(g):
    return g.camera.render(g.current_level.get_sprites())


def objects(grid):
    nodes = segment_layer(grid.tolist(), ARC_COLOR_CHARS)["nodes"]
    return [n for n in nodes if n["pixels"] < 0.25 * grid.size]   # drop backgrounds


def centre(node):
    rs = [p[0] for p in node["boundary"]]; cs = [p[1] for p in node["boundary"]]
    return (min(rs) + max(rs)) // 2, (min(cs) + max(cs)) // 2


def do(g, aid, data=None):
    return g.perform_action(ActionInput(id=GameAction[aid], data=data or {}))


runs = json.load(open(bench))["game_runs"]
rows = []
for idx, r in enumerate(runs):
    k = r["levels_completed"]
    if k >= r["number_of_levels"] or k == 0:
        continue                                   # finished, or stuck on level 1 (no previous level)
    g = load_game(games_dir, r["game_id"][:4])
    do(g, "RESET")
    starts = {0: frame(g).copy()}; lvl = 0
    for x in r["history"]:
        a = x["action"]; fd = do(g, a["id"], a.get("data"))
        if fd.levels_completed != lvl:
            lvl = fd.levels_completed
            starts[lvl] = frame(g).copy()
            if lvl == k:
                break
    start_state = copy.deepcopy(g)                 # game positioned at the start of the stuck level
    prev_types = {n["hash"] for n in objects(starts[k - 1])}
    seen_types = set().union(*({n["hash"] for n in objects(starts[j])} for j in range(k)))
    cur = objects(starts[k])
    new_vs_prev = [n for n in cur if n["hash"] not in prev_types]
    new_vs_all = [n for n in cur if n["hash"] not in seen_types]
    new_colors = {n["color"] for n in cur} - set().union(*({n["color"] for n in objects(starts[j])} for j in range(k)))
    avail = [a for a in fd.available_actions] if fd.available_actions else []
    base = frame(start_state)
    probes = []
    # click probes on new elements
    if 6 in avail:
        for n in new_vs_all[:8]:
            gg = copy.deepcopy(start_state); rr, cc = centre(n)
            fd2 = do(gg, "ACTION6", {"x": cc, "y": rr})
            ch = int((frame(gg) != base).sum())
            undo_ok = None
            if 7 in avail and ch:
                do(gg, "ACTION7"); undo_ok = int((frame(gg) != base).sum())
            probes.append(("click", n["color"], n["pixels"], ch, undo_ok, str(fd2.state).split(".")[-1], fd2.levels_completed > k))
    # simple-action probes
    for aid in [a for a in avail if a in (1, 2, 3, 4, 5)]:
        gg = copy.deepcopy(start_state)
        fd2 = do(gg, f"ACTION{aid}")
        ch = int((frame(gg) != base).sum())
        undo_ok = None
        if 7 in avail and ch:
            do(gg, "ACTION7"); undo_ok = int((frame(gg) != base).sum())
        probes.append((f"A{aid}", "", 0, ch, undo_ok, str(fd2.state).split(".")[-1], fd2.levels_completed > k))
    hud = min([p[3] for p in probes] or [0])          # cells every action changes (step counter etc.)
    probes = [(a, c, px, max(0, ch - hud), (None if u is None else u <= 2 * hud + 2), st, w) for a, c, px, ch, u, st, w in probes]
    clicks = [p for p in probes if p[0] == "click"]
    simple = [p for p in probes if p[0] != "click"]
    undo_tests = [p[4] for p in probes if p[4] is not None]
    rows.append(dict(run=idx, game=r["game_id"][:4], stuck_level=k + 1, n_objects=len(cur),
                     new_vs_prev=len(new_vs_prev), new_vs_all=len(new_vs_all), new_colors="".join(sorted(new_colors)),
                     click_probes=len(clicks), click_effect=sum(p[3] > 0 for p in clicks),
                     simple_probes=len(simple), simple_effect=sum(p[3] > 0 for p in simple),
                     undo_tests=len(undo_tests), undo_restores=sum(undo_tests),
                     probe_deaths=sum(p[5] == "GAME_OVER" for p in probes), probe_wins=sum(p[6] for p in probes)))
if out_csv:
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
n = len(rows)
tot = lambda key: sum(r[key] for r in rows)
print(f"stuck levels with a previous level: {n}")
print(f"  levels with >=1 new object type vs ALL earlier level starts: {sum(r['new_vs_all'] > 0 for r in rows)}"
      f"  (median new types {sorted(r['new_vs_all'] for r in rows)[n // 2]})")
print(f"  levels with a brand-new colour: {sum(bool(r['new_colors']) for r in rows)}")
print(f"  click probes on new elements: {tot('click_probes')} -> visible effect {tot('click_effect')}")
print(f"  simple-action probes: {tot('simple_probes')} -> visible effect {tot('simple_effect')}")
print(f"  UNDO after an effective probe restores the start board: {tot('undo_restores')}/{tot('undo_tests')}")
print(f"  probe deaths: {tot('probe_deaths')}, probe wins: {tot('probe_wins')}")
