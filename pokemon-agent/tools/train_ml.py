#!/usr/bin/env python3
"""Train tiny MLP (numpy) on gen_ml_data.py output; embed weights into v42 agent."""
import base64, io, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
d = np.load(ROOT / "kaggle_results" / "ml_data.npz")
X, y, gid = d["X"], d["y"], d["gid"]
rng = np.random.default_rng(7)
games = np.unique(gid)
rng.shuffle(games)
cut = int(len(games) * 0.8)
tr_g, te_g = set(games[:cut].tolist()), set(games[cut:].tolist())
tr = np.array([g in tr_g for g in gid]); te = ~tr
mean = X[tr].mean(0); std = X[tr].std(0) + 1e-6
Xn = (X - mean) / std

D, H1, H2 = X.shape[1], 96, 64
W1 = rng.normal(0, np.sqrt(2 / D), (D, H1)).astype(np.float32); b1 = np.zeros(H1, np.float32)
W2 = rng.normal(0, np.sqrt(2 / H1), (H1, H2)).astype(np.float32); b2 = np.zeros(H2, np.float32)
W3 = rng.normal(0, np.sqrt(2 / H2), (H2, 1)).astype(np.float32); b3 = np.zeros(1, np.float32)
params = [W1, b1, W2, b2, W3, b3]
m = [np.zeros_like(p) for p in params]; v = [np.zeros_like(p) for p in params]

def forward(Xb):
    h1 = np.maximum(Xb @ W1 + b1, 0)
    h2 = np.maximum(h1 @ W2 + b2, 0)
    z = h1 * 0 + (h2 @ W3 + b3)  # placeholder to keep shapes clear
    return h1, h2, z

Xtr, ytr = Xn[tr], y[tr].reshape(-1, 1)
Xte, yte = Xn[te], y[te]
EPOCHS, BS = 14, 512
step = 0
for ep in range(EPOCHS):
    idx = rng.permutation(len(Xtr))
    for s in range(0, len(idx), BS):
        step += 1
        bidx = idx[s:s + BS]
        xb, yb = Xtr[bidx], ytr[bidx]
        h1 = np.maximum(xb @ W1 + b1, 0)
        h2 = np.maximum(h1 @ W2 + b2, 0)
        z = h2 @ W3 + b3
        p = 1 / (1 + np.exp(-z))
        dz = (p - yb) / len(xb)
        gW3 = h2.T @ dz; gb3 = dz.sum(0)
        dh2 = dz @ W3.T; dh2[h2 <= 0] = 0
        gW2 = h1.T @ dh2; gb2 = dh2.sum(0)
        dh1 = dh2 @ W2.T; dh1[h1 <= 0] = 0
        gW1 = xb.T @ dh1; gb1 = dh1.sum(0)
        grads = [gW1, gb1, gW2, gb2, gW3, gb3]
        for i in range(len(params)):
            m[i] = 0.9 * m[i] + 0.1 * grads[i]
            v[i] = 0.999 * v[i] + 0.001 * grads[i] ** 2
            mh = m[i] / (1 - 0.9 ** step); vh = v[i] / (1 - 0.999 ** step)
            params[i] -= 3e-3 * mh / (np.sqrt(vh) + 1e-8)
        W1, b1, W2, b2, W3, b3 = params

def predict(Xb):
    h1 = np.maximum(Xb @ W1 + b1, 0)
    h2 = np.maximum(h1 @ W2 + b2, 0)
    return (1 / (1 + np.exp(-(h2 @ W3 + b3)))).ravel()

ptr, pte = predict(Xtr), predict(Xte)
acc_tr = ((ptr > 0.5) == ytr.ravel()).mean(); acc_te = ((pte > 0.5) == yte).mean()
print(f"train acc {acc_tr:.3f} | test acc {acc_te:.3f} (baseline {max(yte.mean(), 1-yte.mean()):.3f})")

raw = np.concatenate([
    np.array([D, H1, H2, 0], dtype=np.float32),
    W1.ravel(), b1, W2.ravel(), b2, W3.ravel(), b3,
    mean.astype(np.float32), std.astype(np.float32),
]).astype(np.float32)
b64 = base64.b64encode(raw.tobytes()).decode()
agent = ROOT / "agents" / "main_heuristic_v42.py"
t = agent.read_text()
import re
t2 = re.sub(r'_ML_W_B64 = "[^"]*"  # filled by tools/train_ml.py',
            f'_ML_W_B64 = "{b64}"  # filled by tools/train_ml.py', t)
assert t2 != t
agent.write_text(t2)
print(f"embedded {len(b64)} b64 chars ({len(raw)*4/1024:.0f} KiB weights) into {agent.name}")
