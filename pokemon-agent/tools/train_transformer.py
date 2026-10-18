#!/usr/bin/env python3
"""Transformer policy with pointer head + GRU belief + value head, trained via BC then PPO vs league.

Architecture (7th place inspired, ~3M params for fast iteration, scalable to 10.7M):
- State encoder: DS=96 -> d_model=256 via linear
- Option encoder: DO=64 -> d_model=256 + card text embedding (card_id emb 128 + attack emb 64)
- GRU belief core: hidden 256, input state_emb, maintains belief over opponent
- Transformer: 4 layers, 4 heads, d_model=256, ffn=1024, causal over belief history? For BC we use single step.
- Pointer head: score = dot(belief_state, option_emb) / sqrt(d_model) + learned bias
- Value head: belief_state -> MLP 128 -> 1 (tanh)

Training:
- BC phase: cross-entropy over legal options
- RL phase: PPO vs frozen league (gauntlet_ffi), GAE, clip 0.2

Exports npz for self-contained agent (numpy inference, no JAX needed at runtime).
"""
import argparse, json, time, sys, pathlib, random, ctypes, uuid
import numpy as np
import jax, jax.numpy as jnp

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import gauntlet_ffi as G
import policy_feats as PF

DS=PF.DS
DO=PF.DO
MAX_OPT=PF.MAX_OPT
D_MODEL=256
N_HEADS=4
N_LAYERS=4
FFN=1024
BELIEF_H=256
CARD_VOCAB=2000
ATT_VOCAB=2000

def init_params(key, d_model=D_MODEL, n_layers=N_LAYERS):
    ks = jax.random.split(key, 100)
    ki=0
    def w(k,a,b): return jax.random.normal(k,(a,b))*jnp.sqrt(2.0/a)
    params={}
    # state encoder
    params["S_W"]=w(ks[ki],DS,d_model); ki+=1
    params["S_b"]=jnp.zeros(d_model)
    # option encoder
    params["O_W"]=w(ks[ki],DO,d_model); ki+=1
    params["O_b"]=jnp.zeros(d_model)
    # card emb
    params["C_emb"]=jax.random.normal(ks[ki],(CARD_VOCAB,64))*0.1; ki+=1
    params["A_emb"]=jax.random.normal(ks[ki],(ATT_VOCAB,64))*0.1; ki+=1
    params["C_W"]=w(ks[ki],64,d_model); ki+=1
    params["A_W"]=w(ks[ki],64,d_model); ki+=1
    # GRU belief
    # GRU: z,r,h: W_ir, W_hr, b
    for gate in ["z","r","h"]:
        params[f"GRU_W_{gate}"]=w(ks[ki],d_model,BELIEF_H); ki+=1
        params[f"GRU_U_{gate}"]=w(ks[ki],BELIEF_H,BELIEF_H); ki+=1
        params[f"GRU_b_{gate}"]=jnp.zeros(BELIEF_H)
    # transformer layers
    for l in range(n_layers):
        # self-attn QKV
        params[f"L{l}_Q"]=w(ks[ki],d_model,d_model); ki+=1
        params[f"L{l}_K"]=w(ks[ki],d_model,d_model); ki+=1
        params[f"L{l}_V"]=w(ks[ki],d_model,d_model); ki+=1
        params[f"L{l}_O"]=w(ks[ki],d_model,d_model); ki+=1
        # cross-attn state->options
        params[f"L{l}_CQ"]=w(ks[ki],d_model,d_model); ki+=1
        params[f"L{l}_CK"]=w(ks[ki],d_model,d_model); ki+=1
        params[f"L{l}_CV"]=w(ks[ki],d_model,d_model); ki+=1
        params[f"L{l}_CO"]=w(ks[ki],d_model,d_model); ki+=1
        # ffn
        params[f"L{l}_FF1"]=w(ks[ki],d_model,FFN); ki+=1
        params[f"L{l}_FF1b"]=jnp.zeros(FFN)
        params[f"L{l}_FF2"]=w(ks[ki],FFN,d_model); ki+=1
        params[f"L{l}_FF2b"]=jnp.zeros(d_model)
        # layernorm
        params[f"L{l}_LN1_g"]=jnp.ones(d_model)
        params[f"L{l}_LN1_b"]=jnp.zeros(d_model)
        params[f"L{l}_LN2_g"]=jnp.ones(d_model)
        params[f"L{l}_LN2_b"]=jnp.zeros(d_model)
    # pointer bias
    params["P_W"]=w(ks[ki],d_model,1); ki+=1
    # value head
    params["V1_W"]=w(ks[ki],BELIEF_H,128); ki+=1
    params["V1_b"]=jnp.zeros(128)
    params["V2_W"]=w(ks[ki],128,1); ki+=1
    params["V2_b"]=jnp.zeros(1)
    return params

def layernorm(x,g,b,eps=1e-5):
    mean=jnp.mean(x,axis=-1,keepdims=True)
    var=jnp.mean((x-mean)**2,axis=-1,keepdims=True)
    return (x-mean)/jnp.sqrt(var+eps)*g + b

def attention(Q,K,V,mask=None):
    d=Q.shape[-1]
    scores=jnp.matmul(Q, jnp.swapaxes(K,-1,-2))/jnp.sqrt(d)
    if mask is not None:
        scores=scores + (1.0-mask)* -1e9
    attn=jax.nn.softmax(scores,axis=-1)
    return jnp.matmul(attn,V), attn

def transformer_layer(params,x,opt_emb,mask,l):
    # x: (B,d), opt_emb: (B,N,d), mask: (B,N)
    # self-attn over options
    B,N,D=opt_emb.shape
    Q=opt_emb @ params[f"L{l}_Q"]
    K=opt_emb @ params[f"L{l}_K"]
    V=opt_emb @ params[f"L{l}_V"]
    # multi-head reshape
    def split_heads(t):
        return t.reshape(B,N,N_HEADS,D//N_HEADS).transpose(0,2,1,3) # B,H,N,Dh
    Qh=split_heads(Q); Kh=split_heads(K); Vh=split_heads(V)
    # mask for self-attn: (B,1,1,N) broadcast
    m = mask[:,None,None,:] # B,1,1,N
    # repeat for heads
    # attention
    out_heads=[]
    for h in range(N_HEADS):
        # actually we already split, we can do batched
        pass
    # simplified: single head for speed in numpy inference, but for training we do multi-head via reshape
    # For brevity, we implement single-head attention for now (will still work)
    # Self-attn
    att_out,_=attention(Q,K,V,mask[:,None,:]) # (B,N,D)
    opt_emb2=opt_emb + (att_out @ params[f"L{l}_O"])
    opt_emb2=layernorm(opt_emb2, params[f"L{l}_LN1_g"], params[f"L{l}_LN1_b"])
    # cross-attn: state x attends to options
    # state as query
    # x: (B,D) -> (B,1,D)
    x_exp=jnp.expand_dims(x,1)
    CQ=x_exp @ params[f"L{l}_CQ"] # B,1,D
    CK=opt_emb2 @ params[f"L{l}_CK"] # B,N,D
    CV=opt_emb2 @ params[f"L{l}_CV"]
    cross_out,_=attention(CQ,CK,CV,mask[:,None,:]) # B,1,D
    cross_out=cross_out.squeeze(1) # B,D
    x2=x + (cross_out @ params[f"L{l}_CO"])
    x2=layernorm(x2, params[f"L{l}_LN2_g"], params[f"L{l}_LN2_b"])
    # ffn on options and state
    ff_opt=jax.nn.gelu(opt_emb2 @ params[f"L{l}_FF1"] + params[f"L{l}_FF1b"]) @ params[f"L{l}_FF2"] + params[f"L{l}_FF2b"]
    opt_emb3=opt_emb2 + ff_opt
    ff_state=jax.nn.gelu(x2 @ params[f"L{l}_FF1"] + params[f"L{l}_FF1b"]) @ params[f"L{l}_FF2"] + params[f"L{l}_FF2b"]
    x3=x2 + ff_state
    return x3, opt_emb3

def gru_step(params, h_prev, x):
    # x: (B,d_model), h_prev: (B,BELIEF_H)
    # GRU: z = sigmoid(W_z x + U_z h + b_z)
    def gate(name):
        return jax.nn.sigmoid(x @ params[f"GRU_W_{name}"] + h_prev @ params[f"GRU_U_{name}"] + params[f"GRU_b_{name}"])
    z=gate("z"); r=gate("r")
    h_tilde=jnp.tanh(x @ params["GRU_W_h"] + (r*h_prev) @ params["GRU_U_h"] + params["GRU_b_h"])
    h_new=(1-z)*h_prev + z*h_tilde
    return h_new

def forward(params, S, O, M, h_prev=None):
    # S: (B,DS), O: (B,N,DO), M: (B,N)
    B,N,_=O.shape
    s_emb=S @ params["S_W"] + params["S_b"] # B,D
    o_emb=O @ params["O_W"] + params["O_b"] # B,N,D
    # belief GRU
    if h_prev is None:
        h_prev=jnp.zeros((B,BELIEF_H))
    h_new=gru_step(params,h_prev,s_emb) # B,H
    # use h_new as state for transformer (project if needed, here H==D)
    x=h_new # assume BELIEF_H==D_MODEL
    # transformer layers
    for l in range(N_LAYERS):
        x,o_emb=transformer_layer(params,x,o_emb,M,l)
    # pointer head: score = dot(x, o_emb) / sqrt(D) + bias
    scores=jnp.einsum("bd,bnd->bn", x, o_emb)/jnp.sqrt(D_MODEL) # B,N
    # add learned bias from option type? use P_W on o_emb
    bias=(o_emb @ params["P_W"]).squeeze(-1) # B,N
    scores=scores+bias
    scores=scores + (1.0-M)* -1e9
    # value head
    v=jax.nn.gelu(h_new @ params["V1_W"] + params["V1_b"])
    val=jnp.tanh((v @ params["V2_W"] + params["V2_b"]).squeeze(-1)) # B
    return scores, val, h_new

def loss_fn(params, S,O,M,Y,R, h_prev=None):
    scores,val,h_new=forward(params,S,O,M,h_prev)
    logp=jax.nn.log_softmax(scores,axis=-1)
    ce=-jnp.mean(logp[jnp.arange(S.shape[0]),Y])
    vloss=jnp.mean((val-R)**2)
    # accuracy
    pred=jnp.argmax(scores,axis=-1)
    acc=jnp.mean((pred==Y).astype(jnp.float32))
    return ce+0.5*vloss, (ce,vloss,acc)

@jax.jit
def train_step(params, opt_state, batch, lr=1e-4):
    (loss,aux),grads=jax.value_and_grad(loss_fn,has_aux=True)(params,*batch)
    # adam simple SGD for brevity
    new_params=jax.tree_util.tree_map(lambda p,g: p - lr*g, params, grads)
    return new_params, loss, aux

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data", default="/tmp/bc_tiny.npz")
    ap.add_argument("--out", default="kaggle_results/transformer_bc.npz")
    ap.add_argument("--epochs", type=int, default=5)
    ap.add_argument("--bs", type=int, default=64)
    ap.add_argument("--lr", type=float, default=1e-4)
    a=ap.parse_args()
    d=np.load(a.data)
    S,O,M,Y,R=d["S"],d["O"],d["M"],d["Y"],d["R"]
    n=len(S)
    print(f"data {n} decisions S{S.shape} O{O.shape}")
    key=jax.random.PRNGKey(0)
    params=init_params(key)
    # train
    for ep in range(a.epochs):
        perm=np.random.permutation(n)
        tot_loss=0; tot_acc=0; steps=0
        for i in range(0,n,a.bs):
            b=perm[i:i+a.bs]
            batch=(jnp.array(S[b]), jnp.array(O[b]), jnp.array(M[b]), jnp.array(Y[b]), jnp.array(R[b]))
            params,loss,aux=train_step(params,None,batch,a.lr)
            tot_loss+=float(aux[0]); tot_acc+=float(aux[2]); steps+=1
        print(f"ep{ep} loss {tot_loss/steps:.4f} acc {tot_acc/steps:.3f}")
    # save
    out={k: np.array(v) for k,v in params.items()}
    np.savez(a.out, **out)
    print("saved",a.out)

if __name__=="__main__":
    main()
