"""Transformer encoder (board tokens) + pointer head over legal options.
JAX/Flax. Wejscia: tokens [B,T,14], state [B,104], opts [B,O,64], mask [B,O].
Wyjscia: policy logits [B,O], value [B]. ~0.6M parametrow przy d=128."""
import flax.linen as nn
import jax.numpy as jnp


class PolicyNet(nn.Module):
    d: int = 128
    layers: int = 3
    heads: int = 4

    @nn.compact
    def __call__(self, tokens, state, opts, omask, train=False):
        B = tokens.shape[0]
        x = nn.Dense(self.d)(tokens)
        # self-attention over board tokens
        for _ in range(self.layers):
            y = nn.MultiHeadDotProductAttention(num_heads=self.heads, qkv_features=self.d)(x, x)
            x = nn.LayerNorm()(x + y)
            y = nn.Dense(self.d * 2)(x)
            y = nn.gelu(y)
            y = nn.Dense(self.d)(y)
            x = nn.LayerNorm()(x + y)
        board_ctx = jnp.mean(x, axis=1)                      # [B,d]
        g = nn.Dense(self.d)(state)
        g = nn.gelu(g)
        ctx = nn.LayerNorm()(board_ctx + g)                  # [B,d]
        ctx = nn.Dense(self.d)(ctx)
        o = nn.Dense(self.d)(opts)
        o = nn.gelu(o)
        o = nn.Dense(self.d)(o)                              # [B,O,d]
        logits = jnp.einsum('bod,bd->bo', o, ctx) / jnp.sqrt(float(self.d))
        logits = logits + (1.0 - omask) * (-1e9)
        value = nn.Dense(1)(nn.gelu(nn.Dense(self.d)(ctx)))[:, 0]
        return logits, value


def count_params(params):
    import jax
    return sum(x.size for x in jax.tree_util.tree_leaves(params))
