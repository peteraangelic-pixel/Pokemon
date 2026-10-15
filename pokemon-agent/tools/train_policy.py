#!/usr/bin/env python3
"""Train the v58 option-scorer (JAX): concat(state, option) -> score.
Loss: cross-entropy over legal options (mask) toward the teacher's choice,
plus a value head (state -> game outcome) trained with MSE.

Exports numpy weights to --out (npz) for the self-contained agent.
"""
from __future__ import annotations

import argparse
import time

import numpy as np
import jax
import jax.numpy as jnp


def init_params(key, ds, do, h1=384, h2=256):
    ks = jax.random.split(key, 8)
    def w(k, a, b):
        return jax.random.normal(k, (a, b)) * jnp.sqrt(2.0 / a)
    return {
        "W1": w(ks[0], ds + do, h1), "b1": jnp.zeros(h1),
        "W2": w(ks[1], h1, h2), "b2": jnp.zeros(h2),
        "W3": w(ks[2], h2, 1), "b3": jnp.zeros(1),
        "V1": w(ks[3], ds, 128), "c1": jnp.zeros(128),
        "V2": w(ks[4], 128, 1), "c2": jnp.zeros(1),
    }


def forward(params, S, O):
    # S: (B, DS), O: (B, N, DO) -> scores (B, N), value (B,)
    B, N, DO = O.shape
    DS = S.shape[1]
    x = jnp.concatenate([jnp.broadcast_to(S[:, None, :], (B, N, DS)), O], axis=-1)
    x = x.reshape(B * N, DS + DO)
    h = jax.nn.gelu(x @ params["W1"] + params["b1"])
    h = jax.nn.gelu(h @ params["W2"] + params["b2"])
    sc = (h @ params["W3"] + params["b3"]).reshape(B, N)
    v = jax.nn.gelu(S @ params["V1"] + params["c1"])
    val = jnp.tanh((v @ params["V2"] + params["c2"])[:, 0])
    return sc, val


def loss_fn(params, S, O, M, Y, R):
    sc, val = forward(params, S, O)
    sc = sc + (1.0 - M) * -1e9
    logp = jax.nn.log_softmax(sc, axis=-1)
    ce = -jnp.mean(logp[jnp.arange(S.shape[0]), Y])
    vloss = jnp.mean((val - R) ** 2)
    pred = jnp.argmax(sc, axis=-1)
    acc = jnp.mean((pred == Y).astype(jnp.float32))
    return ce + 0.5 * vloss, (ce, vloss, acc)


@jax.jit
def step(params, opt_state, batch, lr):
    (loss, aux), grads = jax.value_and_grad(loss_fn, has_aux=True)(params, *batch)
    updates = jax.tree_util.tree_map(lambda g: -lr * g, grads)
    new_params = jax.tree_util.tree_map(lambda p, u: p + u, params, updates)
    return new_params, loss, aux


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="kaggle_results/bc_data.npz")
    ap.add_argument("--out", default="kaggle_results/policy_v58.npz")
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--bs", type=int, default=512)
    ap.add_argument("--lr", type=float, default=1e-3)
    a = ap.parse_args()
    d = np.load(a.data)
    S, O, M, Y, R = d["S"], d["O"], d["M"], d["Y"], d["R"]
    n = len(S)
    idx = np.random.RandomState(0).permutation(n)
    ntr = int(n * 0.92)
    tr, va = idx[:ntr], idx[ntr:]
    print(f"data: {n} decisions (train {len(tr)}, val {len(va)})")
    params = init_params(jax.random.PRNGKey(0), S.shape[1], O.shape[2])
    t0 = time.time()
    for ep in range(a.epochs):
        rng = np.random.RandomState(ep)
        order = rng.permutation(tr)
        tot = []
        for i in range(0, len(order), a.bs):
            b = order[i:i + a.bs]
            batch = tuple(jnp.array(x[b]) for x in (S, O, M, Y, R))
            params, loss, aux = step(params, None, batch, a.lr)
            tot.append(float(aux[2]))
        # val acc
        vacc = []
        for i in range(0, len(va), 2048):
            b = va[i:i + 2048]
            sc, _ = forward(params, jnp.array(S[b]), jnp.array(O[b]))
            sc = np.array(sc) + (1.0 - np.array(M[b])) * -1e9
            vacc.append((sc.argmax(-1) == np.array(Y[b])).mean())
        print(f"ep{ep}: train_acc~{np.mean(tot):.3f} val_acc={np.mean(vacc):.3f} ({time.time()-t0:.0f}s)", flush=True)
    out = {k: np.array(v) for k, v in params.items()}
    out["DS"] = np.array([S.shape[1]]); out["DO"] = np.array([O.shape[2]])
    np.savez(a.out, **out)
    print("saved ->", a.out)


if __name__ == "__main__":
    main()
