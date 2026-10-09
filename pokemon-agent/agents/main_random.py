"""Phase 0 smoke-test agent for the PTCG AI Battle Challenge.

Goal: exercise the *entire submission pipeline* end to end.  It does the bare
minimum needed to never fail a Validation Episode:

* at the deck-selection step (``obs["select"] is None``) it returns the 60-card
  deck read from ``deck.csv`` sitting next to this file;
* otherwise it returns a uniformly random sample of *legal* option indices,
  respecting ``minCount``/``maxCount``;
* it is wrapped in a blanket ``try/except`` so an unexpected observation shape
  can never raise inside the harness (a raise == ``Error`` submission).

Because it is the most conservative code we can write, it doubles as the
"reference agent" that proves packaging, deck loading and log retrieval work
before any strategy code is trusted.

Return contract (verified against ``kaggle_environments/envs/cabt/cabt.py``):

* the deck step expects a list of 60 card ids;
* every other step expects a list of *option indices* into
  ``obs["select"]["option"]``;
* ``obs["select"]["option"]`` can be an empty list while ``maxCount`` is 1 --
  the correct answer is then ``[]``.
"""
from __future__ import annotations

import os
import random

# --- deck ------------------------------------------------------------------
# Kept inline as a fallback so the agent still works if deck.csv cannot be
# found at runtime.  Must stay in sync with deck.csv.
_FALLBACK_DECK = (
    [721, 721, 722, 722, 722, 722, 723, 723, 723, 723]
    + [1092]
    + [1121, 1121, 1145, 1145, 1163, 1163]
    + [1219, 1219, 1219, 1219]
    + [1227, 1227, 1227, 1227]
    + [1262, 1262]
    + [3] * 33
)


def _load_deck() -> list[int]:
    """Read deck.csv from any location the harness might place us in.

    Kaggle exec()s our source rather than importing it, so __file__ does not
    exist there -- both of our first uploads died on that NameError at import
    time.  Never depend on it; the Kaggle paths are absolute and always first.
    """
    try:
        here = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        here = ""
    for path in (
        "/kaggle_simulations/agent/deck.csv",
        "/kaggle_simulations/agent/assets/deck.csv",
        os.path.join(os.getcwd(), "deck.csv"),
        os.path.join(here, "deck.csv") if here else "",
        os.path.join(here, "assets", "deck.csv") if here else "",
    ):
        try:
            with open(path, encoding="utf-8") as fh:
                ids: list[int] = []
                for line in fh:
                    for tok in line.replace(",", " ").split():
                        if tok.strip():
                            ids.append(int(tok))
                if len(ids) == 60:
                    return ids
        except Exception:
            continue
    return list(_FALLBACK_DECK)


try:
    DECK = _load_deck()
except Exception:
    DECK = list(_FALLBACK_DECK)


def _random_select(select: dict) -> list[int]:
    options = select.get("option") or []
    n = len(options)
    if n == 0:
        return []
    max_count = int(select.get("maxCount") or 0)
    min_count = int(select.get("minCount") or 0)
    k = max(min(max_count, n), 0)
    if k == 0:
        # Some prompts allow/require zero choices; choosing nothing is safest
        # only when minCount is 0, otherwise we must still return something.
        if min_count <= 0:
            return []
        k = min(min_count, n)
    return random.sample(range(n), k)


def agent(obs: dict) -> list[int]:
    try:
        select = obs.get("select")
        if select is None:
            return list(DECK)
        return _random_select(select)
    except Exception:
        # Last-resort: never raise.  Choosing the first index (or none) always
        # yields a legal action as long as the option list is non-empty.
        try:
            options = (obs.get("select") or {}).get("option") or []
            return [0] if options else []
        except Exception:
            return []
