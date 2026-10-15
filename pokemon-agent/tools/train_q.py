#!/usr/bin/env python3
"""Train Q(state, option) on epsilon-greedy data (tools/gen_q_data.py).

Plain executed-row BCE: target = game outcome for the EXECUTED option only.
Game-split (gid % 5 == 0 -> test). Saves numpy MLP 30->128->64->1 to
kaggle_results/q_model.json (same layout as imitation model).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
rng = np.random.default_rng(3)
np.set_printoptions(suppress=True)


def forward(P, X):
    W1, b1, W2, b2, W3, b3 = P
    h = np.maximum(X @ W1 + b1, 0)
    h2 = np.maximum(h @ W2 + b2, 0)
    return (h2 @ W3 + b3).ravel(), (X, h, h2)


def main() -> int:
    d = np.load(ROOT / "kaggle_results/q_data.npz")
    X, starts, executed, won, gid = d["X"], d["starts"], d["executed"], d["won"], d["gid"]
    ends = np.append(starts[1:], len(X))
    rows = starts + executed  # executed option row per decision
    Xe = X[rows].astype(np.float32)
    y = won.astype(np.float32)
    test = (gid % 5) == 0
    print(f"executed rows={len(y)} winrate={y.mean():.4f} test_n={test.sum()}")

    mu, sd = Xe[~test].mean(0), Xe[~test].std(0) + 1e-6
    Xn = (Xe - mu) / sd

    F = 30
    P = [rng.normal(0, 0.15, (F, 128)), np.zeros(128),
         rng.normal(0, 0.15, (128, 64)), np.zeros(64),
         rng.normal(0, 0.15, (64, 1)), np.zeros(1)]
    m = [np.zeros_like(p) for p in P]
    v = [np.zeros_like(p) for p in P]
    Xtr, ytr = Xn[~test], y[~test]
    n = len(ytr)
    t = 0
    for ep in range(30):
        order = rng.permutation(n)
        for i in range(0, n, 1024):
            t += 1
            idx = order[i:i + 1024]
            xb, yb = Xtr[idx], ytr[idx]
            out, (Xin, h, h2) = forward(P, xb)
            p = 1 / (1 + np.exp(-np.clip(out, -30, 30)))
            grad = (p - yb) / len(idx)
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
            for j in range(len(P)):
                m[j] = 0.9 * m[j] + 0.1 * grads[j]
                v[j] = 0.999 * v[j] + 0.001 * grads[j] ** 2
                P[j] -= 1e-3 * (m[j] / (1 - 0.9 ** t)) / (np.sqrt(v[j] / (1 - 0.999 ** t)) + 1e-8)
        if ep % 10 == 9:
            out, _ = forward(P, Xn[test])
            p = 1 / (1 + np.exp(-np.clip(out, -30, 30)))
            ll = -np.mean(y[test] * np.log(p + 1e-9) + (1 - y[test]) * np.log(1 - p + 1e-9))
            acc = np.mean((p > 0.5) == (y[test] > 0.5))
            print(f"epoch {ep}: test logloss={ll:.4f} acc={acc:.4f} (base rate {y[test].mean():.4f})")

    # sanity: Q-argmax agreement with executed choice, in chunks (low memory)
    agree = 0
    tot = 0
    test_idx = np.where(test)[0][:20000]
    Xf = X.astype(np.float32)
    for k in test_idx:
        s, e = int(starts[k]), int(ends[k])
        seg, _ = forward(P, (Xf[s:e] - mu) / sd)
        if int(np.argmax(seg)) == int(executed[k]):
            agree += 1
        tot += 1
    print(f"Q-argmax == executed rate (test sample): {agree / tot:.3f}", flush=True)

    out = {"kind": "q_eps_greedy_mlp_30_128_64_1", "mu": mu.tolist(), "sd": sd.tolist(),
           "W1": P[0].tolist(), "b1": P[1].tolist(), "W2": P[2].tolist(),
           "b2": P[3].tolist(), "W3": P[4].ravel().tolist(), "b3": [float(P[5][0])]}
    (ROOT / "kaggle_results/q_model.json").write_text(json.dumps(out))
    print("saved kaggle_results/q_model.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
