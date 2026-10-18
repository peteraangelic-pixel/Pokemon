"""Forward PolicyNetV2 w czystym numpy (parytet z Flax) - do agenta Kaggle.
D=256 L=4 H=8 belief 128, ~2.3M params
"""
import numpy as np

def _dense(x, W, prefix):
    k = W.get(f"{prefix}/kernel")
    b = W.get(f"{prefix}/bias")
    if k is None:
        # try with /params/ prefix
        k = W.get(f"/params/{prefix}/kernel")
        b = W.get(f"/params/{prefix}/bias")
    if k is None:
        raise KeyError(f"missing {prefix}")
    return x @ k + b

def _ln(x, W, prefix, eps=1e-6):
    # LayerNorm: scale, bias
    scale = W.get(f"{prefix}/scale") or W.get(f"/params/{prefix}/scale")
    bias = W.get(f"{prefix}/bias") or W.get(f"/params/{prefix}/bias")
    if scale is None:
        raise KeyError(f"ln missing {prefix}")
    mu = x.mean(-1, keepdims=True)
    var = x.var(-1, keepdims=True)
    return (x - mu) / np.sqrt(var + eps) * scale + bias

def _gelu(x):
    return 0.5 * x * (1.0 + np.tanh(np.sqrt(2.0 / np.pi) * (x + 0.044715 * x ** 3)))

def _attn(x, W, prefix):
    # MultiHeadDotProductAttention
    # query, key, value, out
    def get_qkv(name):
        k = W.get(f"{prefix}/{name}/kernel") or W.get(f"/params/{prefix}/{name}/kernel")
        b = W.get(f"{prefix}/{name}/bias") or W.get(f"/params/{prefix}/{name}/bias")
        return k, b
    qk, qb = get_qkv("query")
    kk, kb = get_qkv("key")
    vk, vb = get_qkv("value")
    ok, ob = get_qkv("out")
    # x [B,T,D]
    # qk [D, H, K] ?
    # In Flax, qkv_features = D, num_heads = H, so K = D//H
    # We'll use einsum generic: assume qk shape [D, H, K]
    # Compute Q = x @ qk + qb
    # qb shape [H,K] ?
    # We'll handle via tensordot
    # For simplicity, use same logic as numpy_model.py but with named params
    # Flax stores query kernel as [D, H, K]
    # Let's do einsum
    B, T, D = x.shape
    H = qk.shape[1]
    K = qk.shape[2]
    # x [B,T,D] @ qk [D,H,K] -> [B,T,H,K]
    Q = np.einsum('btd,dhk->bthk', x, qk)
    if qb is not None:
        Q = Q + qb  # broadcast [H,K]
    Kmat = np.einsum('btd,dhk->bthk', x, kk) + (kb if kb is not None else 0)
    V = np.einsum('btd,dhk->bthk', x, vk) + (vb if vb is not None else 0)
    # attention scores
    att = np.einsum('bthk,bshk->bhts', Q, Kmat) / np.sqrt(K)
    # softmax
    att = att - att.max(axis=-1, keepdims=True)
    att = np.exp(att)
    att = att / att.sum(axis=-1, keepdims=True)
    o = np.einsum('bhts,bshk->bthk', att, V)
    # out projection: [H,K,D] ?
    # ok shape [H,K,D] ? Actually Flax out kernel [H,K,D] or [H*K,D]?
    # In Flax, out kernel shape [H, K, D] ? Let's assume [H,K,D]
    if ok.ndim == 3:
        out = np.einsum('bthk,hkd->btd', o, ok) + (ob if ob is not None else 0)
    else:
        # ok [H*K, D]
        o_flat = o.reshape(B, T, H*K)
        out = o_flat @ ok + (ob if ob is not None else 0)
    return out

def _gru_cell(h, x, W, prefix):
    # h [B, H], x [B, D]
    # reset, update, new
    # hx = concat(h,x)
    hx = np.concatenate([h, x], axis=-1)
    # reset gate
    r = 1.0 / (1.0 + np.exp(-_dense(hx, W, f"{prefix}/reset")))
    z = 1.0 / (1.0 + np.exp(-_dense(hx, W, f"{prefix}/update")))
    rh = r * h
    n_hx = np.concatenate([rh, x], axis=-1)
    n = np.tanh(_dense(n_hx, W, f"{prefix}/new"))
    h_new = (1 - z) * n + z * h
    return h_new

def forward_v2(W, tokens, state, opts, omask, hidden=None):
    B = tokens.shape[0]
    belief_dim = 128
    if hidden is None:
        hidden = np.zeros((B, belief_dim), dtype=np.float32)
    # belief_in
    belief_in = _gelu(_dense(state, W, "belief_in"))
    hidden_new = _gru_cell(hidden, belief_in, W, "gru")

    x = _dense(tokens, W, "tok_proj")
    for i in range(4):
        x = _ln(x + _attn(x, W, f"attn_{i}"), W, f"ln1_{i}")
        y = _dense(_gelu(_dense(x, W, f"mlp1_{i}")), W, f"mlp2_{i}")
        x = _ln(x + y, W, f"ln2_{i}")
    board_ctx = x.mean(axis=1)  # [B,d]
    g = _gelu(_dense(state, W, "state_proj"))
    bh = _gelu(_dense(hidden_new, W, "belief_proj"))
    ctx = _ln(board_ctx + g + bh, W, "ctx_ln")
    ctx = _dense(ctx, W, "ctx_out")

    o = _dense(_gelu(_dense(opts, W, "opt1")), W, "opt2")
    logits = np.einsum('bod,bd->bo', o, ctx) / np.sqrt(ctx.shape[-1])
    logits = logits + (1.0 - omask) * (-1e9)

    v = np.concatenate([ctx, hidden_new], axis=-1)
    v = _gelu(_dense(v, W, "val1"))
    value = _dense(v, W, "val2")[:, 0]
    return logits, value, hidden_new
