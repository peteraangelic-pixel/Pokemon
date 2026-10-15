#!/usr/bin/env python3
"""Train global + per-archetype state-value MLPs (numpy). Game-split validation.
Exports weights as JSON for embedding into main_heuristic_v42_2.py."""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from state_feats import ARCHES

ROOT = Path(__file__).resolve().parents[1]
d = np.load(ROOT / "kaggle_results" / "league_data.npz")
X, y, arch, gid = d["X"], d["y"], d["arch"], d["gid"]
print("rows", X.shape, "winrate", round(float(y.mean()), 3))
for i, a in enumerate(ARCHES):
    m = arch == i
    print(f"  {a}: {int(m.sum())} rows, wr {float(y[m].mean()) if m.sum() else 0:.3f}")

rng = np.random.default_rng(11)
games = np.unique(gid); rng.shuffle(games)
test_games = set(games[: int(len(games) * 0.15)].tolist())
te = np.array([g in test_games for g in gid]); tr = ~te

def train(Xtr, ytr, seed=3, epochs=10):
    r = np.random.default_rng(seed)
    D = Xtr.shape[1]; H1, H2 = 96, 64
    mean = Xtr.mean(0); std = Xtr.std(0) + 1e-6
    Xn = (Xtr - mean) / std
    W1 = r.normal(0, np.sqrt(2 / D), (D, H1)).astype(np.float32); b1 = np.zeros(H1, np.float32)
    W2 = r.normal(0, np.sqrt(2 / H1), (H1, H2)).astype(np.float32); b2 = np.zeros(H2, np.float32)
    W3 = r.normal(0, np.sqrt(2 / H2), (H2, 1)).astype(np.float32); b3 = np.zeros(1, np.float32)
    P = [W1, b1, W2, b2, W3, b3]
    m = [np.zeros_like(p) for p in P]; v = [np.zeros_like(p) for p in P]
    yv = ytr.reshape(-1, 1); step = 0
    for ep in range(epochs):
        idx = r.permutation(len(Xn))
        for s in range(0, len(idx), 512):
            step += 1
            b = idx[s:s + 512]; xb, yb = Xn[b], yv[b]
            h1 = np.maximum(xb @ P[0] + P[1], 0); h2 = np.maximum(h1 @ P[2] + P[3], 0)
            z = h2 @ P[4] + P[5]; p = 1 / (1 + np.exp(-z))
            dz = (p - yb) / len(xb)
            gW3 = h2.T @ dz; gb3 = dz.sum(0)
            dh2 = dz @ P[4].T; dh2[h2 <= 0] = 0
            gW2 = h1.T @ dh2; gb2 = dh2.sum(0)
            dh1 = dh2 @ P[2].T; dh1[h1 <= 0] = 0
            gW1 = xb.T @ dh1; gb1 = dh1.sum(0)
            for i, gr in enumerate([gW1, gb1, gW2, gb2, gW3, gb3]):
                m[i] = 0.9 * m[i] + 0.1 * gr; v[i] = 0.999 * v[i] + 0.001 * gr ** 2
                P[i] -= 3e-3 * (m[i] / (1 - 0.9 ** step)) / (np.sqrt(v[i] / (1 - 0.999 ** step)) + 1e-8)
    return {"W1": P[0].tolist(), "b1": P[1].tolist(), "W2": P[2].tolist(),
            "b2": P[3].tolist(), "W3": P[4].ravel().tolist(), "b3": P[5].tolist(),
            "mean": mean.tolist(), "std": std.tolist()}

def acc(model, Xb, yb):
    Xn = (Xb - np.array(model["mean"])) / np.array(model["std"])
    h1 = np.maximum(Xn @ np.array(model["W1"]) + np.array(model["b1"]), 0)
    h2 = np.maximum(h1 @ np.array(model["W2"]) + np.array(model["b2"]), 0)
    p = 1 / (1 + np.exp(-(h2 @ np.array(model["W3"]) + np.array(model["b3"]))))
    return float(((p.ravel() > 0.5) == yb).mean())

models = {}
gm = train(X[tr], y[tr])
models["GLOBAL"] = gm
print(f"GLOBAL: train-rows {int(tr.sum())} test acc {acc(gm, X[te], y[te]):.3f} (base {max(y[te].mean(), 1-y[te].mean()):.3f})")
for i, a in enumerate(ARCHES):
    mtr = tr & (arch == i); mte = te & (arch == i)
    if mtr.sum() < 800:
        print(f"{a}: too few ({int(mtr.sum())}) -> GLOBAL fallback"); continue
    mm = train(X[mtr], y[mtr], seed=5 + i)
    models[a] = mm
    print(f"{a}: rows {int(mtr.sum())} test acc {acc(mm, X[mte], y[mte]):.3f} (base {max(y[mte].mean(), 1-y[mte].mean()) if mte.sum() else 0:.3f}, n_te {int(mte.sum())})")

out = ROOT / "kaggle_results" / "league_models.json"
out.write_text(json.dumps(models))
print("wrote", out, f"{out.stat().st_size/1024:.0f} KiB")
