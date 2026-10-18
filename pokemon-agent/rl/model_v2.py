"""Transformer encoder-decoder + GRU belief core, 2-3M params, pointer head.
Wejscia: tokens [B,T,14], state [B,104] (96 global + 8 belief), opts [B,O,64], mask, hidden [B,128] (GRU belief)
Wyjscia: logits [B,O], value [B], new_hidden [B,128]
~2.3M przy d=256 L=4 H=8, belief 128
"""
import flax.linen as nn
import jax.numpy as jnp

class GRUCell(nn.Module):
    hidden_dim: int = 128
    @nn.compact
    def __call__(self, h, x):
        # x [B, in_dim], h [B, hidden]
        # concat
        hx = jnp.concatenate([h, x], axis=-1)
        r = nn.sigmoid(nn.Dense(self.hidden_dim, name="reset")(hx))
        z = nn.sigmoid(nn.Dense(self.hidden_dim, name="update")(hx))
        n_h = jnp.concatenate([r * h, x], axis=-1)
        n = nn.tanh(nn.Dense(self.hidden_dim, name="new")(n_h))
        h_new = (1 - z) * n + z * h
        return h_new

class PolicyNetV2(nn.Module):
    d: int = 256
    layers: int = 4
    heads: int = 8
    belief_dim: int = 128

    @nn.compact
    def __call__(self, tokens, state, opts, omask, hidden=None, train=False):
        B = tokens.shape[0]
        if hidden is None:
            hidden = jnp.zeros((B, self.belief_dim))
        # belief GRU: update hidden with state (which includes belief feats)
        # state 104d -> project to belief input
        belief_in = nn.Dense(self.belief_dim, name="belief_in")(state)
        belief_in = nn.gelu(belief_in)
        gru = GRUCell(self.belief_dim, name="gru")
        hidden_new = gru(hidden, belief_in)

        x = nn.Dense(self.d, name="tok_proj")(tokens)
        for i in range(self.layers):
            y = nn.MultiHeadDotProductAttention(num_heads=self.heads, qkv_features=self.d, name=f"attn_{i}")(x, x)
            x = nn.LayerNorm(name=f"ln1_{i}")(x + y)
            y = nn.Dense(self.d * 2, name=f"mlp1_{i}")(x)
            y = nn.gelu(y)
            y = nn.Dense(self.d, name=f"mlp2_{i}")(y)
            x = nn.LayerNorm(name=f"ln2_{i}")(x + y)
        board_ctx = jnp.mean(x, axis=1)  # [B,d]
        g = nn.Dense(self.d, name="state_proj")(state)
        g = nn.gelu(g)
        # combine board + state + belief hidden
        bh = nn.Dense(self.d, name="belief_proj")(hidden_new)
        bh = nn.gelu(bh)
        ctx = nn.LayerNorm(name="ctx_ln")(board_ctx + g + bh)
        ctx = nn.Dense(self.d, name="ctx_out")(ctx)

        o = nn.Dense(self.d, name="opt1")(opts)
        o = nn.gelu(o)
        o = nn.Dense(self.d, name="opt2")(o)  # [B,O,d]

        logits = jnp.einsum('bod,bd->bo', o, ctx) / jnp.sqrt(float(self.d))
        logits = logits + (1.0 - omask) * (-1e9)

        # value head with belief
        v = jnp.concatenate([ctx, hidden_new], axis=-1)
        v = nn.Dense(self.d, name="val1")(v)
        v = nn.gelu(v)
        value = nn.Dense(1, name="val2")(v)[:, 0]

        return logits, value, hidden_new

def count_params(params):
    import jax
    return sum(x.size for x in jax.tree_util.tree_leaves(params))
