"""Forward PolicyNet w czystym numpy (parytet z Flax) - do agenta Kaggle."""
import numpy as np

P = "/params/"


def _dense(x, W, name):
    return x @ W[P + name + "/kernel"] + W[P + name + "/bias"]


def _ln(x, W, name, eps=1e-6):
    mu = x.mean(-1, keepdims=True)
    var = x.var(-1, keepdims=True)
    return (x - mu) / np.sqrt(var + eps) * W[P + name + "/scale"] + W[P + name + "/bias"]


def _gelu(x):
    return 0.5 * x * (1.0 + np.tanh(np.sqrt(2.0 / np.pi) * (x + 0.044715 * x ** 3)))


def _attn(x, W, name):
    q = np.einsum('btd,dhk->bthk', x, W[P + name + "/query/kernel"]) + W[P + name + "/query/bias"]
    k = np.einsum('btd,dhk->bthk', x, W[P + name + "/key/kernel"]) + W[P + name + "/key/bias"]
    v = np.einsum('btd,dhk->bthk', x, W[P + name + "/value/kernel"]) + W[P + name + "/value/bias"]
    att = np.einsum('bthk,bshk->bhts', q, k) / np.sqrt(q.shape[-1])
    att = np.exp(att - att.max(-1, keepdims=True))
    att = att / att.sum(-1, keepdims=True)
    o = np.einsum('bhts,bshk->bthk', att, v)
    return np.einsum('bthk,hkd->btd', o, W[P + name + "/out/kernel"]) + W[P + name + "/out/bias"]


def forward(W, tokens, state, opts, omask):
    x = _dense(tokens, W, "Dense_0")
    for i in range(3):
        x = _ln(x + _attn(x, W, f"MultiHeadDotProductAttention_{i}"), W, f"LayerNorm_{2*i}")
        y = _dense(_gelu(_dense(x, W, f"Dense_{1+2*i}")), W, f"Dense_{2+2*i}")
        x = _ln(x + y, W, f"LayerNorm_{2*i+1}")
    board_ctx = x.mean(1)
    g = _gelu(_dense(state, W, "Dense_7"))
    ctx = _dense(_ln(board_ctx + g, W, "LayerNorm_6"), W, "Dense_8")
    o = _dense(_gelu(_dense(opts, W, "Dense_9")), W, "Dense_10")
    logits = np.einsum('bod,bd->bo', o, ctx) / np.sqrt(ctx.shape[-1])
    logits = logits + (1.0 - omask) * (-1e9)
    value = _dense(_gelu(_dense(ctx, W, "Dense_12")), W, "Dense_11")[:, 0]
    return logits, value
