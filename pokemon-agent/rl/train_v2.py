"""Trening V2: BC 6000g + PPO vs frozen league 8 pilotów, transformer D128 L3 + GRU belief, pointer head, gated lethal, mask dominated"""
import argparse, json, os, sys, time, math
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

def batch(records, rng):
    tok = np.array([r[0] for r in records], np.float32)
    st = np.array([r[1] for r in records], np.float32)
    opts = np.array([r[2] for r in records], np.float32)
    mask = np.array([r[3] for r in records], np.float32)
    act = np.array([r[4] for r in records], np.int32)
    return tok, st, opts, mask, act

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bc-games', type=int, default=6000)
    ap.add_argument('--bc-steps', type=int, default=2500)
    ap.add_argument('--ppo-iters', type=int, default=20)
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
        try:
            pilots[name] = load_pilot(ag, dk, name)
        except Exception as e:
            print(f"league skip {name}: {e}")
    champ_fn, champ_deck = pilots["champion"]

    rec = []
    t0 = time.time()
    for g in range(a.bc_games):
        oname = list(pilots.keys())[g % len(pilots)]
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
        if s % 200 == 0:
            vb = batch(va[:256], rng)
            print(f"BC step {s} loss={float(l):.3f} held-out match={float(match_acc(params, *vb)):.3f}", flush=True)

    def policy_fn(obs):
        sel = obs.get("select") if isinstance(obs, dict) else None
        if sel is not None:
            tt = sel.get("type")
            if tt is None or int(tt) != 0 or int(sel.get("maxCount") or 1) != 1:
                return champ_fn(obs)
        cur = obs.get("current") or {}
        me = int(cur.get("yourIndex", 0))
        enc = rfz.encode(obs, me)
        tok = np.array([enc[0]], np.float32); st = np.array([enc[1]], np.float32)
        opts = np.array([enc[2]], np.float32); mask = np.array([enc[3]], np.float32)
        logits, _ = net.apply(params, tok, st, opts, mask)
        lg = np.array(logits[0])[:max(enc[4], 1)]
        return [int(np.argmax(lg))]

    def evaluate(games):
        out = {}
        for name in ("champion","v67"):
            if name not in pilots: continue
            ofn, odeck = pilots[name]
            W=L=0
            for g in range(games):
                rfz.belief.reset()
                r = play_game(lib, lambda o: policy_fn(o), ofn, champ_deck, odeck, g%2)
                W+=r==1; L+=r==-1
            out[name]=W/max(W+L,1)
        return out

    print("eval po BC:", evaluate(a.eval_games), flush=True)

    # PPO fixed
    import ctypes
    import json as json2

    def policy_lp(enc, hidden, temp=1.0):
        tok = np.array([enc[0]], np.float32); st = np.array([enc[1]], np.float32)
        opts = np.array([enc[2]], np.float32); mask = np.array([enc[3]], np.float32)
        logits, val = net.apply(params, tok, st, opts, mask)
        lg = np.array(logits[0])[:max(enc[4],1)]
        v = float(val[0])
        z = (lg - lg.max()) / temp
        p = np.exp(z); p = p / p.sum()
        ai = int(rng.choice(len(p), p=p)) if temp>0 else int(np.argmax(lg))
        lp = float(np.log(max(p[ai], 1e-9)))
        return ai, lp, v

    opt_ppo = optax.chain(optax.clip_by_global_norm(1.0), optax.adam(1e-4))
    osta_ppo = opt_ppo.init(params)

    @jax.jit
    def step_ppo(params, osta, tok, st, opts, mask, act, oldlp, adv, ret):
        def loss(p):
            logits, val = net.apply(p, tok, st, opts, mask)
            logp = jax.nn.log_softmax(logits, -1)
            lp = jnp.take_along_axis(logp, act[:, None], -1)[:,0]
            ratio = jnp.exp(lp - oldlp)
            surr1 = ratio * adv
            surr2 = jnp.clip(ratio, 0.8, 1.2) * adv
            pg_loss = -jnp.mean(jnp.minimum(surr1, surr2))
            v_loss = 0.5 * ((val - ret)**2).mean()
            ent = -(jnp.exp(logp) * logp * mask).sum(-1) / jnp.maximum(mask.sum(-1),1)
            ent_loss = -0.02 * ent.mean()
            return pg_loss + v_loss + ent_loss
        l, grads = jax.value_and_grad(loss)(params)
        grads = jax.tree_util.tree_map(lambda g: jnp.clip(g, -1.0, 1.0), grads)
        upd, osta = opt_ppo.update(grads, osta)
        return optax.apply_updates(params, upd), osta, l

    osta = osta_ppo
    for it in range(a.ppo_iters):
        traj, rets = [], []
        W=L=0
        for g in range(a.ppo_games):
            oname = list(pilots.keys())[(g+it) % len(pilots)]
            ofn, odeck = pilots[oname]
            rfz.belief.reset()
            cards = (ctypes.c_int * 120)(*(champ_deck if g%2==0 else odeck), *(odeck if g%2==0 else champ_deck))
            bp = lib.BattleStart(cards).battlePtr
            if not bp:
                continue
            game_traj = []
            r = 0
            try:
                while True:
                    obs = json2.loads(lib.GetBattleData(bp).json)
                    cur = obs.get("current") or {}
                    res = cur.get("result")
                    if res is not None and res>=0:
                        r = 0 if res==2 else (1 if res==(g%2) else -1)
                        break
                    if obs.get("select") is None:
                        break
                    me = int(cur.get("yourIndex",0))
                    if me == g%2:
                        sel = obs.get("select") or {}
                        tt = sel.get("type")
                        if tt is not None and int(tt)==0 and int(sel.get("maxCount") or 1)==1:
                            enc = rfz.encode(obs, me)
                            ai, lp, v = policy_lp(enc, np.zeros(128), temp=1.0)
                            game_traj.append((enc[0], enc[1], enc[2], enc[3], ai, lp, v))
                            dec = [ai]
                        else:
                            dec = champ_fn(obs)
                    else:
                        dec = ofn(obs)
                    if not isinstance(dec, list):
                        dec=[]
                    if lib.Select(bp, (ctypes.c_int * len(dec))(*dec), len(dec))!=0:
                        break
            finally:
                lib.BattleFinish(bp)
            W+=r==1; L+=r==-1
            ret = 1.0 if r==1 else (-1.0 if r==-1 else 0.0)
            for t in game_traj:
                traj.append(t)
                rets.append(ret)

        if not traj:
            print("PPO: brak trajektorii"); break
        traj_f = [t for t in traj if t[4] < 32]
        rets_f = [rets[i] for i,t in enumerate(traj) if t[4] < 32]
        tok = np.array([t[0] for t in traj_f], np.float32); st = np.array([t[1] for t in traj_f], np.float32)
        opts = np.array([t[2] for t in traj_f], np.float32); mask = np.array([t[3] for t in traj_f], np.float32)
        act = np.array([t[4] for t in traj_f], np.int32); oldlp = np.array([t[5] for t in traj_f], np.float32)
        vals = np.array([t[6] for t in traj_f], np.float32)
        ret = np.array(rets_f, np.float32)
        adv = ret - vals
        adv = (adv - adv.mean()) / (adv.std() + 1e-6)
        for ep in range(2):
            sel = rng.permutation(len(traj_f))
            for i in range(0, len(sel), 256):
                b = sel[i:i+256]
                params, osta, l = step_ppo(params, osta, tok[b], st[b], opts[b], mask[b], act[b], oldlp[b], adv[b].astype(np.float32), ret[b])
        print(f"PPO iter {it}: WR={W/max(W+L,1):.3f} decyzji={len(traj_f)} loss={float(l):.3f} eval={evaluate(a.eval_games)}", flush=True)
        # save intermediate
        flat_tmp = {}
        def rec_tmp(p, prefix=""):
            if isinstance(p, dict):
                for k,v in p.items():
                    rec_tmp(v, f"{prefix}/{k}")
            else:
                flat_tmp[prefix] = np.array(p)
        rec_tmp(params)
        np.savez(a.out, **flat_tmp)
        print(f"intermediate saved {a.out}")

    flat = {}
    def rec_flat(p, prefix=""):
        if isinstance(p, dict):
            for k,v in p.items():
                rec_flat(v, f"{prefix}/{k}")
        else:
            flat[prefix] = np.array(p)
    rec_flat(params)
    np.savez(a.out, **flat)
    print("zapisano", a.out, f"({len(flat)} tensorow)")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
