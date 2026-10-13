"""Replay every run and measure behaviour on the level where it got stuck (CPU only).

python stuck_metrics.py BENCH.json GAMES_DIR OUT.csv
"""
import csv, hashlib, json, sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from play import load_game
from arcengine import ActionInput, GameAction, GameState


def h(g):
    return hashlib.md5(g.camera.render(g.current_level.get_sprites()).tobytes()).hexdigest()


def main(bench, games_dir, out):
    runs = json.load(open(bench))["game_runs"]
    rows = []
    for idx, r in enumerate(runs):
        g = load_game(games_dir, r["game_id"][:4])
        g.perform_action(ActionInput(id=GameAction.RESET))
        k = r["levels_completed"]; lvl = 0; start = 0
        hist = r["history"]
        per = []  # (state_hash, changed, reset/gameover, tokens) on stuck level
        prev = h(g)
        for i, x in enumerate(hist):
            a = x["action"]
            fd = g.perform_action(ActionInput(id=GameAction[a["id"]], data=a.get("data") or {}))
            if fd.levels_completed != lvl:
                lvl = fd.levels_completed; start = i + 1; per = []; prev = h(g); continue
            cur = h(g)
            over = fd.state == GameState.GAME_OVER
            if over:  # harness auto-resets after game over
                g.perform_action(ActionInput(id=GameAction.RESET)); cur = h(g)
            per.append((cur, cur != prev, a["id"] == "RESET" or over, x.get("generated_tokens", 0)))
            prev = cur
        n = len(per); c = Counter(s for s, *_ in per)
        tot_tok = sum(x.get("generated_tokens", 0) for x in hist) or 1
        rows.append(dict(run=idx, game=r["game_id"][:4], pass_=int((r.get("solver_analysis_html") or "_p0.").rsplit("_p", 1)[-1].split(".")[0]),
                         levels=r["number_of_levels"], solved=k, stuck_level=k + 1,
                         actions=n, noop_frac=round(sum(not ch for _, ch, *_ in per) / n, 2) if n else 0,
                         resets=sum(rs for *_, rs, _ in per),
                         distinct_frac=round(len(c) / n, 2) if n else 0,
                         max_revisit=max(c.values()) if c else 0,
                         tok_share=round(sum(t for *_, t in per) / tot_tok, 2),
                         stuck_tokens=sum(t for *_, t in per),
                         base=r["base_actions_per_level"][k] if k < r["number_of_levels"] else 0))
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {out}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
