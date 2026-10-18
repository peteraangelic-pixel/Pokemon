#!/usr/bin/env python3
"""
PPO vs frozen league – Phase 2 RL

League: v67_stack, c87_v44 champion, v65 Alakazam, v70_horizon (if available)
Our policy: transformer/MLP with value head, trained via PPO

Each iteration:
- Sample opponent from league
- Play N games our_policy vs opp (alternating seats)
- For each decision by our policy, store S,O,M, chosen, logp, value, reward (game outcome)
- Compute GAE advantages
- PPO update: clip 0.2, value loss 0.5, entropy 0.01

Uses gauntlet_ffi for fast engine, policy_feats for features, JAX for training.

Run: .venv/bin/python tools/train_ppo_league.py --policy /tmp/policy_fast.npz --games 40 --iters 3 --out /tmp/ppo.npz
"""
import argparse, ctypes, json, sys, pathlib, random, time, uuid
from collections import defaultdict
import numpy as np
import jax, jax.numpy as jnp

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"tools"))
import gauntlet_ffi as G
import policy_feats as PF

DS=PF.DS; DO=PF.DO; MAX_OPT=PF.MAX_OPT

def init_policy_params(key, ds=DS, do=DO, h1=128, h2=64):
    ks=jax.random.split(key,8)
    def w(k,a,b): return jax.random.normal(k,(a,b))*jnp.sqrt(2.0/a)
    return {"W1": w(ks[0], ds+do, h1), "b1": jnp.zeros(h1), "W2": w(ks[1], h1, h2), "b2": jnp.zeros(h2), "W3": w(ks[2], h2, 1), "b3": jnp.zeros(1), "V1": w(ks[3], ds, 64), "c1": jnp.zeros(64), "V2": w(ks[4], 64, 1), "c2": jnp.zeros(1)}

def forward(params,S,O):
    B,N,DO=O.shape; DS=S.shape[1]
    x=jnp.concatenate([jnp.broadcast_to(S[:,None,:], (B,N,DS)), O], axis=-1).reshape(B*N, DS+DO)
    h=jax.nn.gelu(x @ params["W1"] + params["b1"])
    h=jax.nn.gelu(h @ params["W2"] + params["b2"])
    sc=(h @ params["W3"] + params["b3"]).reshape(B,N)
    v=jax.nn.gelu(S @ params["V1"] + params["c1"])
    val=jnp.tanh((v @ params["V2"] + params["c2"])[:,0])
    return sc,val

def load_policy_npz(path):
    d=np.load(path)
    # support both old and new keys
    return {k: jnp.array(d[k]) for k in d.files if k not in ("DS","DO")}

def play_one_game(lib, our_agent_fn, opp_agent, our_deck, opp_deck, seat, fz):
    """our_agent_fn: function(obs,me) -> (chosen_idx, logp, value, S,O,M) ; opp_agent is callable"""
    cards=(ctypes.c_int*120)(*(our_deck if seat==0 else opp_deck), *(opp_deck if seat==0 else our_deck))
    bp=lib.BattleStart(cards).battlePtr
    if not bp:
        return None
    traj=[] # list of (S,O,M,chosen,logp,value,me)
    result=2
    try:
        while True:
            data=lib.GetBattleData(bp)
            obs=json.loads(data.json)
            cur=obs.get("current") or {}
            res=cur.get("result")
            if res is not None and res>=0:
                result=0 if res==2 else (1 if res==seat else -1)
                break
            sel=obs.get("select")
            if sel is None:
                break
            me=int(cur.get("yourIndex",0))
            if me==seat:
                # our turn
                S=np.array([fz.state_feats(obs, me)], dtype=np.float32)
                opts=sel.get("option") or []
                O=np.zeros((1,MAX_OPT,DO), dtype=np.float32)
                for j,o in enumerate(opts[:MAX_OPT]):
                    O[0,j]=fz.option_feats(o, obs, me)
                M=np.zeros((1,MAX_OPT), dtype=np.float32)
                M[0,:len(opts)]=1.0
                # call our_agent_fn to get action
                chosen, logp, value = our_agent_fn(S,O,M, opts)
                traj.append((S[0], O[0], M[0], chosen, logp, value))
                dec=[chosen]
            else:
                dec=opp_agent(obs)
                if not isinstance(dec,list):
                    dec=[]
            if lib.Select(bp, (ctypes.c_int*len(dec))(*dec), len(dec))!=0:
                break
    finally:
        lib.BattleFinish(bp)
    if result==2:
        return None
    # assign rewards: +1 if we won, -1 if lost, 0 draw
    reward=1.0 if result==1 else (-1.0 if result==-1 else 0.0)
    # for each step, return with reward
    out=[]
    for S,O,M,ch,logp,val in traj:
        out.append((S,O,M,ch,logp,val,reward))
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--policy", default="/tmp/policy_fast.npz")
    ap.add_argument("--games", type=int, default=40)
    ap.add_argument("--iters", type=int, default=3)
    ap.add_argument("--out", default="/tmp/ppo.npz")
    ap.add_argument("--lr", type=float, default=3e-4)
    a=ap.parse_args()

    lib=G.get_lib()
    import tarfile
    with tarfile.open(ROOT/"bundles/v67_stack.tar.gz") as tf:
        ci=json.loads(tf.extractfile("card_index.json").read())
    fz=PF.Featurizer(ci)

    # league
    league=[]
    for name, ag_path, deck_path in [
        ("v67","agents/v67_stack.py","decks/v57_trolley34w.csv"),
        ("champ","agents/c87_v44.py","decks/c87_v44.csv"),
        ("alakazam","agents/v65_alakazam.py","decks/v66_alakazam_simple.csv"),
    ]:
        try:
            deck=G.load_deck(str(ROOT/deck_path))
            mod=G.load_module(str(ROOT/ag_path), f"_league_{name}_{uuid.uuid4().hex[:4]}")
            G.rebind(mod, deck)
            league.append((name, mod.agent, deck))
            print(f"league loaded {name}")
        except Exception as e:
            print(f"league fail {name} {e}")

    # load our policy
    params=load_policy_npz(a.policy)
    # define our agent fn that uses current params
    def make_agent_fn(params):
        def agent_fn(S,O,M, opts):
            # S: (1,DS), O: (1,N,DO), M: (1,N)
            sc,val=forward(params, jnp.array(S), jnp.array(O))
            sc=np.array(sc[0]); val=float(np.array(val[0]))
            # mask
            sc = sc + (1.0-M[0])* -1e9
            # softmax for logp
            max_sc=np.max(sc)
            exp_sc=np.exp(sc-max_sc)
            exp_sc=exp_sc*M[0]
            probs=exp_sc/(np.sum(exp_sc)+1e-9)
            # sample from probs (for PPO exploration)
            chosen=np.random.choice(len(opts), p=probs[:len(opts)]/ (np.sum(probs[:len(opts)])+1e-9))
            logp=np.log(probs[chosen]+1e-9)
            return int(chosen), float(logp), val
        return agent_fn

    for it in range(a.iters):
        print(f"\n=== PPO iter {it} ===")
        all_traj=[]
        for g in range(a.games):
            opp_name, opp_agent, opp_deck = random.choice(league)
            our_deck=G.load_deck(str(ROOT/"decks/v72_genial_judge.csv"))
            seat=g%2
            agent_fn=make_agent_fn(params)
            traj=play_one_game(lib, agent_fn, opp_agent, our_deck, opp_deck, seat, fz)
            if traj:
                all_traj.extend(traj)
        if not all_traj:
            print("no traj")
            continue
        print(f"collected {len(all_traj)} decisions")
        # prepare batch for PPO update (simplified: use BC loss toward winning decisions + value loss)
        # For PPO we need advantages: reward - value, but reward is sparse (only at end)
        # Use simple: if reward>0, we want to increase prob of chosen, else decrease
        S_batch=np.array([t[0] for t in all_traj], dtype=np.float32)
        O_batch=np.array([t[1] for t in all_traj], dtype=np.float32)
        M_batch=np.array([t[2] for t in all_traj], dtype=np.float32)
        Y_batch=np.array([t[3] for t in all_traj], dtype=np.int32)
        R_batch=np.array([t[6] for t in all_traj], dtype=np.float32)
        # compute values
        _, vals = forward(params, jnp.array(S_batch), jnp.array(O_batch))
        vals_np=np.array(vals)
        adv=R_batch - vals_np
        # PPO loss: we need old logp
        old_logp=np.array([t[4] for t in all_traj], dtype=np.float32)
        # for simplicity, do 1 epoch of policy gradient with advantage
        def ppo_loss(p, S,O,M,Y,Adv,R, old_logp):
            sc,val=forward(p,S,O)
            sc=sc + (1.0-M)* -1e9
            logp=jax.nn.log_softmax(sc,axis=-1)
            # gather logp of chosen
            chosen_logp=logp[jnp.arange(S.shape[0]), Y]
            # ratio
            ratio=jnp.exp(chosen_logp - old_logp)
            # clipped
            clip=0.2
            clipped=jnp.clip(ratio, 1-clip, 1+clip)
            pg_loss=-jnp.mean(jnp.minimum(ratio*Adv, clipped*Adv))
            vloss=jnp.mean((val-R)**2)
            # entropy
            probs=jnp.exp(logp)
            ent=-jnp.mean(jnp.sum(probs*logp,axis=-1))
            return pg_loss + 0.5*vloss - 0.01*ent, (pg_loss, vloss, ent)

        @jax.jit
        def ppo_step(p, batch, lr):
            (loss,aux),grads=jax.value_and_grad(ppo_loss, has_aux=True)(p,*batch)
            new_p=jax.tree_util.tree_map(lambda a,g: a - lr*g, p, grads)
            return new_p, loss, aux

        # batch
        bs=128
        perm=np.random.permutation(len(S_batch))
        for i in range(0,len(perm),bs):
            b=perm[i:i+bs]
            batch=(jnp.array(S_batch[b]), jnp.array(O_batch[b]), jnp.array(M_batch[b]), jnp.array(Y_batch[b]), jnp.array(adv[b]), jnp.array(R_batch[b]), jnp.array(old_logp[b]))
            params, loss, aux = ppo_step(params, batch, a.lr)
        print(f"iter {it} loss {float(loss):.4f} pg {float(aux[0]):.4f} v {float(aux[1]):.4f} ent {float(aux[2]):.4f} avgR {R_batch.mean():.3f}")

        # save
        out={k: np.array(v) for k,v in params.items()}
        out["DS"]=np.array([DS]); out["DO"]=np.array([DO])
        np.savez(a.out, **out)
        print(f"saved {a.out}")

if __name__=="__main__":
    main()
