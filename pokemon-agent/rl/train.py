"""Trening: BC z championa (decyzje vs liga) -> PPO self-play vs zamrozona liga.
Uzycie: .venv/bin/python -m rl.train --bc-games 2000 --ppo-iters 50 --ppo-games 400
Wynik: rl/params_best.npz + rl/train_log.json. Ewaluacja w lidze co iteracje."""
import argparse, json, os, sys, time
import numpy as np
sys.path.insert(0, 'tools'); sys.path.insert(0, '.')
import gauntlet_ffi as G
from rl.features import RLFeaturizer
from rl.selfplay import load_pilot, play_game

LEAGUE = [
    ("champion", "agents/c87_v44.py", "decks/v57_trolley34w.csv"),
    ("v67", "agents/v67_wall_tempo_noimit.py", "decks/v57_trolley34w.csv"),
    ("v63", "agents/v63_super_sub.py", "decks/v57_trolley34w.csv"),
    ("alakazam", "agents/v65_alakazam.py", "decks/v66_alakazam_simple.csv"),
]
TROLLEY = "decks/v57_trolley34w.csv"


def batch(records, rng):
    tok = np.array([r[0] for r in records], np.float32)
    st = np.array([r[1] for r in records], np.float32)
    opts = np.array([r[2] for r in records], np.float32)
    mask = np.array([r[3] for r in records], np.float32)
    act = np.array([r[4] for r in records], np.int32)
    return tok, st, opts, mask, act


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bc-games', type=int, default=400)
    ap.add_argument('--bc-steps', type=int, default=300)
    ap.add_argument('--ppo-iters', type=int, default=0)
    ap.add_argument('--ppo-games', type=int, default=200)
    ap.add_argument('--eval-games', type=int, default=100)
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--out', default='rl/params_best.npz')
    a = ap.parse_args()
    import jax, jax.numpy as jnp, optax
    from rl.model import PolicyNet, count_params
    rng = np.random.default_rng(a.seed)
    ci = json.load(open('card_index.json'))
    rfz = RLFeaturizer(ci)
    lib = G.get_lib()
    pilots = {}
    for name, ag, dk in LEAGUE:
        pilots[name] = load_pilot(ag, dk, name)
    champ_fn, champ_deck = pilots["champion"]

    # ---------- BC: decyzje championa vs liga ----------
    rec = []
    t0 = time.time()
    for g in range(a.bc_games):
        oname = LEAGUE[g % len(LEAGUE)][0]
        ofn, odeck = pilots[oname]
        rfz.belief.reset()
        play_game(lib, champ_fn, ofn, champ_deck, odeck, g % 2, record=rec, rfz=rfz)
    print(f"BC dane: {len(rec)} decyzji z {a.bc_games} gier ({time.time()-t0:.0f}s)", flush=True)
    rec = [r for r in rec if 0 <= r[4] < 32]
    idx = rng.permutation(len(rec))
    tr = [rec[i] for i in idx[:int(0.9 * len(rec))]]
    va = [rec[i] for i in idx[int(0.9 * len(rec)):]]

    net = PolicyNet()
    key = jax.random.PRNGKey(a.seed)
    tok, st, opts, mask, act = batch(tr[:4], rng)
    params = net.init(key, tok, st, opts, mask)
    print("parametrow:", count_params(params), flush=True)
    opt = optax.adam(1e-3)
    osta = opt.init(params)

    @jax.jit
    def step_bc(params, osta, tok, st, opts, mask, act):
        def loss(p):
            logits, _ = net.apply(p, tok, st, opts, mask)
            return optax.softmax_cross_entropy_with_integer_labels(logits, act).mean()
        l, grads = jax.value_and_grad(loss)(params)
        upd, osta = opt.update(grads, osta)
        return optax.apply_updates(params, upd), osta, l

    @jax.jit
    def match_acc(params, tok, st, opts, mask, act):
        logits, _ = net.apply(params, tok, st, opts, mask)
        return (jnp.argmax(logits, -1) == act).mean()

    for s in range(a.bc_steps):
        sel = rng.integers(0, len(tr), 256)
        b = batch([tr[i] for i in sel], rng)
        params, osta, l = step_bc(params, osta, *b)
        if s % 50 == 0:
            vb = batch(va[:256], rng)
            print(f"BC step {s} loss={float(l):.3f} held-out match={float(match_acc(params, *vb)):.3f}", flush=True)

    def policy_fn(obs, sample=False, temp=1.0):
        sel = obs.get("select") if isinstance(obs, dict) else None
        if sel is not None:
            tt = sel.get("type")
            if tt is None or int(tt) != 0 or int(sel.get("maxCount") or 1) != 1:
                return champ_fn(obs)  # nie-MAIN delegujemy do championa
        cur = obs.get("current") or {}
        me = int(cur.get("yourIndex", 0))
        enc = rfz.encode(obs, me)
        tok = np.array([enc[0]], np.float32); st = np.array([enc[1]], np.float32)
        opts = np.array([enc[2]], np.float32); mask = np.array([enc[3]], np.float32)
        logits, _ = net.apply(params, tok, st, opts, mask)
        lg = np.array(logits[0])[:max(enc[4], 1)]
        if sample:
            p = np.exp((lg - lg.max()) / temp); p = p / p.sum()
            return [int(rng.choice(len(p), p=p))]
        return [int(np.argmax(lg))]

    def evaluate(games):
        out = {}
        for name in ("champion", "v67"):
            ofn, odeck = pilots[name]
            W = L = 0
            for g in range(games):
                rfz.belief.reset()
                r = play_game(lib, lambda o: policy_fn(o), ofn, champ_deck, odeck, g % 2)
                W += r == 1; L += r == -1
            out[name] = W / max(W + L, 1)
        return out

    print("eval po BC:", evaluate(a.eval_games), flush=True)

    # ---------- PPO vs liga (rollouty z logprob, advantage = return - V) ----------
    from rl.selfplay import play_game_pg

    def policy_lp(enc, temp=0.8):
        tok = np.array([enc[0]], np.float32); st = np.array([enc[1]], np.float32)
        opts = np.array([enc[2]], np.float32); mask = np.array([enc[3]], np.float32)
        logits, _ = net.apply(params, tok, st, opts, mask)
        lg = np.array(logits[0])[:max(enc[4], 1)]
        z = (lg - lg.max()) / temp
        p = np.exp(z); p = p / p.sum()
        ai = int(rng.choice(len(p), p=p)) if temp > 0 else int(np.argmax(lg))
        return ai, float(np.log(max(p[ai], 1e-9)))

    @jax.jit
    def step_ppo(params, osta, tok, st, opts, mask, act, oldlp, adv, ret):
        def loss(p):
            logits, val = net.apply(p, tok, st, opts, mask)
            logp = jax.nn.log_softmax(logits, -1)
            lp = jnp.take_along_axis(logp, act[:, None], -1)[:, 0]
            ratio = jnp.exp(lp - oldlp)
            surr = jnp.minimum(ratio * adv, jnp.clip(ratio, 0.8, 1.2) * adv)
            ent = -(jnp.exp(logp) * logp * mask).sum(-1) / jnp.maximum(mask.sum(-1), 1)
            return -(surr.mean()) + 0.5 * ((val - ret) ** 2).mean() - 0.01 * ent.mean()
        l, grads = jax.value_and_grad(loss)(params)
        upd, osta = opt.update(grads, osta)
        return optax.apply_updates(params, upd), osta, l

    opt_ppo = optax.adam(3e-4)
    osta = opt_ppo.init(params)
    for it in range(a.ppo_iters):
        traj, rets = [], []
        W = L = 0
        for g in range(a.ppo_games):
            oname = LEAGUE[(g + it) % len(LEAGUE)][0]
            ofn, odeck = pilots[oname]
            rfz.belief.reset()
            start_i = len(traj)
            r = play_game_pg(lib, policy_lp, ofn, champ_deck, odeck, g % 2, rfz, traj,
                             fallback_fn=champ_fn)
            W += r == 1; L += r == -1
            ret = 1.0 if r == 1 else (-1.0 if r == -1 else 0.0)
            rets.extend([ret] * (len(traj) - start_i))
        if not traj:
            print("PPO: brak trajektorii"); break
        traj = [t for t in traj if t[4] < 32]
        tok = np.array([t[0] for t in traj], np.float32); st = np.array([t[1] for t in traj], np.float32)
        opts = np.array([t[2] for t in traj], np.float32); mask = np.array([t[3] for t in traj], np.float32)
        act = np.array([t[4] for t in traj], np.int32); oldlp = np.array([t[5] for t in traj], np.float32)
        ret = np.array(rets, np.float32)
        _, vals = net.apply(params, tok, st, opts, mask)
        adv = ret - np.array(vals)
        adv = (adv - adv.mean()) / (adv.std() + 1e-6)
        for ep in range(2):
            sel = rng.permutation(len(traj))
            for i in range(0, len(sel), 512):
                b = sel[i:i + 512]
                params, osta, l = step_ppo(params, osta, tok[b], st[b], opts[b], mask[b],
                                           act[b], oldlp[b], adv[b].astype(np.float32), ret[b])
        print(f"PPO iter {it}: WR={W/max(W+L,1):.3f} decyzji={len(traj)} loss={float(l):.3f} "
              f"eval={evaluate(a.eval_games)}", flush=True)

    # zapis parametrow (splaszczone do npz pod numpy-inference)
    flat = {}
    def rec_flat(p, prefix=""):
        if isinstance(p, dict):
            for k, v in p.items():
                rec_flat(v, f"{prefix}/{k}")
        else:
            flat[prefix] = np.array(p)
    rec_flat(params)
    np.savez(a.out, **flat)
    print("zapisano", a.out, f"({len(flat)} tensorow)")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
