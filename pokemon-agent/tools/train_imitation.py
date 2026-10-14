#!/usr/bin/env python3
"""Behavior cloning on replay decisions (NOTES_STRATEGY §19 step 3).

Grouped softmax over each decision's options: MLP 30->128->64->1 scores,
cross-entropy vs the human-chosen option. Split by EPISODE (no leakage).
Reports held-out top-1 accuracy for: model trained on all decisions vs
model trained on opponent-winners only, both evaluated on held-out
opponent-winner decisions (the 'strong play' target). Saves the better
model (numpy weights) to kaggle_results/imitation_model.json.

Usage: .venv/bin/python tools/train_imitation.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
rng = np.random.default_rng(11)


def load_groups(path):
    d = np.load(path, allow_pickle=True)
    X, starts, chosen = d["X"], d["starts"], d["chosen"]
    team, won, ep = d["team"], d["won"], d["episode"]
    ends = np.append(starts[1:], len(X))
    groups = [(int(s), int(e)) for s, e in zip(starts, ends)]
    return X, groups, chosen, team, won, ep


def make_batches(idx, groups, chosen, bs=256):
    order = rng.permutation(idx)
    for i in range(0, len(order), bs):
        yield order[i:i + bs]


def forward(P, Xg):
    W1, b1, W2, b2, W3, b3 = P
    h = np.maximum(Xg @ W1 + b1, 0)
    h2 = np.maximum(h @ W2 + b2, 0)
    return (h2 @ W3 + b3).ravel(), (Xg, h, h2)


def train(X, groups, chosen, train_idx, epochs=60, lr=3e-3):
    F = X.shape[1]
    P = [rng.normal(0, 0.15, (F, 128)), np.zeros(128),
         rng.normal(0, 0.15, (128, 64)), np.zeros(64),
         rng.normal(0, 0.15, (64, 1)), np.zeros(1)]
    m = [np.zeros_like(p) for p in P]
    v = [np.zeros_like(p) for p in P]
    t = 0
    for ep in range(epochs):
        for bidx in make_batches(train_idx, groups, chosen):
            t += 1
            rows, labs, spans = [], [], []
            for gi in bidx:
                s, e = groups[gi]
                rows.append(np.arange(s, e))
                labs.append(chosen[gi])
                spans.append(e - s)
            rows = np.concatenate(rows)
            Xg = X[rows]
            out, (Xin, h, h2) = forward(P, Xg)
            # softmax per group
            grad = np.zeros_like(out)
            off = 0
            for k, n in enumerate(spans):
                seg = out[off:off + n]
                z = seg - seg.max()
                p = np.exp(z) / np.exp(z).sum()
                p[labs[k]] -= 1.0
                grad[off:off + n] = p / len(bidx)
                off += n
            W1, b1, W2, b2, W3, b3 = P
            gW3 = h2.T @ grad[:, None]
            gb3 = np.array([grad.sum()])
            dh2 = grad[:, None] @ W3.T
            dh2[h2 <= 0] = 0
            gW2 = h.T @ dh2
            gb2 = dh2.sum(0)
            dh = dh2 @ W2.T
            dh[h <= 0] = 0
            gW1 = Xin.T @ dh
            gb1 = dh.sum(0)
            grads = [gW1, gb1, gW2, gb2, gW3, gb3]
            for i in range(len(P)):
                m[i] = 0.9 * m[i] + 0.1 * grads[i]
                v[i] = 0.999 * v[i] + 0.001 * grads[i] ** 2
                P[i] -= lr * (m[i] / (1 - 0.9 ** t)) / (np.sqrt(v[i] / (1 - 0.999 ** t)) + 1e-8)
    return P


def accuracy(P, X, groups, chosen, idx):
    ok = 0
    for gi in idx:
        s, e = groups[gi]
        out, _ = forward(P, X[s:e])
        if int(np.argmax(out)) == int(chosen[gi]):
            ok += 1
    return ok / max(1, len(idx))


def main() -> int:
    X, groups, chosen, team, won, ep = load_groups(ROOT / "kaggle_results/imitation_data.npz")
    mu, sd = X.mean(0), X.std(0) + 1e-6
    Xn = (X - mu) / sd
    eps = np.array(sorted(set(ep.tolist())))
    rng.shuffle(eps)
    test_eps = set(eps[: max(8, len(eps) // 5)].tolist())
    is_test = np.array([e in test_eps for e in ep])
    opp = team != "PeterSharps"
    strong = opp & (won == 1)
    idx_all = np.where(~is_test)[0]
    idx_strong_train = np.where(~is_test & strong)[0]
    idx_strong_test = np.where(is_test & strong)[0]
    idx_opp_test = np.where(is_test & opp)[0]
    print(f"decisions={len(groups)} train_all={len(idx_all)} "
          f"train_strong={len(idx_strong_train)} test_strong={len(idx_strong_test)} "
          f"test_opp={len(idx_opp_test)}")
    print(f"random baseline ~ {1/5.6:.3f}")

    models = {}
    for name, tr in [("all", idx_all), ("strong", idx_strong_train)]:
        P = train(Xn, groups, chosen, tr)
        models[name] = P
        print(f"[{name}] acc on held-out strong={accuracy(P, Xn, groups, chosen, idx_strong_test):.3f} "
              f"on held-out opp={accuracy(P, Xn, groups, chosen, idx_opp_test):.3f}")

    best_name = max(models, key=lambda n: accuracy(models[n], Xn, groups, chosen, idx_strong_test))
    P = models[best_name]
    out = {"kind": "imitation_bc_mlp_30_128_64_1", "trained_on": best_name,
           "mu": mu.tolist(), "sd": sd.tolist(),
           "W1": P[0].tolist(), "b1": P[1].tolist(), "W2": P[2].tolist(),
           "b2": P[3].tolist(), "W3": P[4].ravel().tolist(), "b3": [float(P[5][0])]}
    (ROOT / "kaggle_results/imitation_model.json").write_text(json.dumps(out))
    print("saved kaggle_results/imitation_model.json (model:", best_name, ")")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
