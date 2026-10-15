"""Deck-construction rules enforced by the cabt engine.

These were established **experimentally**, not from documentation: the engine
rejects an illegal deck at ``battle_start`` by returning ``errorPlayer >= 0`` with
``errorType 4``, and the episode is then marked ``INVALID`` without ever
exercising the agent.  Getting this wrong locally means every "robustness" game
silently tests nothing.

Rules (all verified):

* exactly **60** cards;
* at most **4** cards sharing a **name**.  This is by *name*, not by card id --
  one ``Espurr`` printing plus four of a different ``Espurr`` printing is five
  Espurr and is illegal;
* **basic Energy** is exempt from the 4-copy limit;
* at most **one ACE SPEC** card in the whole deck.  Note ACE SPEC includes some
  *special energies* (Legacy Energy, Neo Upper Energy, Enriching Energy), not
  just trainers.

Useful for Phase 2 deck optimisation: any candidate list must pass
``deck_is_legal`` before it is worth measuring.
"""
from __future__ import annotations

import json
import os
from typing import Iterable

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CARD_TYPE_POKEMON = 0
CARD_TYPE_BASIC_ENERGY = 5


def load_library(path: str | None = None) -> dict:
    """cardId -> raw card metadata, for the rule checks."""
    if path is None:
        path = os.path.join(ROOT, "data", "cards.json")
    with open(path, encoding="utf-8") as fh:
        cards = json.load(fh)
    return {int(c["cardId"]): c for c in cards}


def deck_problems(deck: Iterable[int], library: dict) -> list[str]:
    """Return a list of human-readable rule violations (empty == legal)."""
    deck = list(deck)
    problems: list[str] = []
    if len(deck) != 60:
        problems.append(f"deck has {len(deck)} cards, must be exactly 60")

    by_name: dict[str, list[int]] = {}
    for cid in deck:
        c = library.get(cid)
        if c is None:
            problems.append(f"unknown card id {cid}")
            continue
        by_name.setdefault(c.get("name") or f"#{cid}", []).append(cid)

    ace = 0
    for name, cids in by_name.items():
        infos = [library.get(c) or {} for c in cids]
        if any(c.get("aceSpec") for c in infos):
            ace += len(cids)
            if len(cids) > 1:
                problems.append(f"ACE SPEC '{name}' appears {len(cids)}x (limit 1)")
        if all(c.get("cardType") == CARD_TYPE_BASIC_ENERGY for c in infos):
            continue
        if len(cids) > 4:
            problems.append(f"'{name}' appears {len(cids)}x (limit 4 by name)")
    if ace > 1:
        problems.append(f"{ace} ACE SPEC cards in deck (limit 1)")
    if not any((library.get(c) or {}).get("cardType") == CARD_TYPE_POKEMON
               and (library.get(c) or {}).get("basic") for c in deck):
        problems.append("deck contains no Basic Pokemon")
    return problems


def deck_is_legal(deck: Iterable[int], library: dict) -> bool:
    return not deck_problems(deck, library)


if __name__ == "__main__":
    lib = load_library()
    default_deck = [int(x) for x in
                    open(os.path.join(ROOT, "deck.csv"), encoding="utf-8").read().split()]
    problems = deck_problems(default_deck, lib)
    print(f"deck.csv: {len(default_deck)} cards")
    print("legal" if not problems else "PROBLEMS:")
    for p in problems:
        print("  -", p)
