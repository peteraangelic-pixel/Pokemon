"""Build a compact card/attack index used at inference time by the agent.

Reads the raw dumps produced by ``dump_cards.py`` and writes
``assets/card_index.json`` with short keys (the agent embeds a small JSON
parser-free dict lookup, so size matters a little but readability matters more).

Output schema
-------------
{
  "cards": {
     "<cardId>": {"n": name, "ct": cardType, "pt": pokemonType, "et": evolutionType,
                  "rc": retreatCost, "hp": hp, "w": weakness, "res": resistance,
                  "en": energyType, "ex": bool, "mex": bool, "ace": bool,
                  "ef": evolvesFromName, "atk": [attackIds], "sk": [skillNames],
                  "tr": bool, "pv": [blockedClasses], "pvs": "self"|"bench"|"all"}
  },
  "attacks": {"<attackId>": {"n": name, "d": damage, "e": [energies], "t": text}},
  "by_name": {"<name>": [cardIds]}
}
"""
from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


_PREVENT_MARK = re.compile(r"prevent all damage", re.I)
_GUST_MARK = re.compile(
    r"switch (?:in|out) (?:1 of )?your opponent'?s? (?:benched|active)", re.I)


def _norm(text: str) -> str:
    """Fold typographic characters the card text is full of.

    The dump uses U+2019 (right single quote) in "opponent's", which plain
    ASCII regexes silently miss -- our first gust parser matched zero cards.
    """
    return (text.replace("\u2019", "'").replace("\u2018", "'")
                .replace("\u201c", '"').replace("\u201d", '"')
                .replace("\u00a0", " "))


def is_gust(skills: list) -> bool:
    """Does this card force the opponent's Active Pokemon out of the Active Spot?

    This is the clean answer to an anti-ex wall: the wall (Crustle, Safeguard
    Sylveon) only protects *itself*, so pushing it to the Bench and hitting
    whatever comes in lets our Mega ex do damage again.
    """
    return any(_GUST_MARK.search(_norm(s.get("text") or ""))
               for s in skills if isinstance(s, dict))


def prevent_profile(skills: list) -> tuple[str, list[str]] | None:
    """Parse a damage-prevention ability into (scope, blocked attacker classes).

    The agent only ever sees skill *names* at runtime, so the text has to be
    understood here, at index build time, and shipped as a compact flag.

    We enumerated every "prevent all damage" ability in the pool (17 of them)
    and wrote the parser against the actual wording rather than guessing:

        Crustle / Sylveon   "by attacks from your opponent's Pokemon {ex}"
        Milotic ex          "... your opponent's Tera Pokemon"
        Farigiraf ex        "... your opponent's Basic Pokemon {ex}"
        Cornerstone Ogerpon "... Pokemon that have an Ability"
        Drednaw             "... if that damage is 200 or more"
        Carracosta          "... that have any Special Energy attached"

    scope is "self" (protects this Pokemon, i.e. the one we would attack),
    "bench" (protects Benched Pokemon only - irrelevant to attacking the active)
    or "all" (protects every Pokemon its owner has).
    """
    texts = [s.get("text") or "" for s in skills if isinstance(s, dict)]
    joined = " ".join(texts)
    if not _PREVENT_MARK.search(joined):
        return None
    low = joined.lower()

    if "to each of your" in low:
        scope = "all"
    elif "benched" in low or "on your bench" in low:
        scope = "bench"
    else:
        scope = "self"

    classes: list[str] = []
    if "pok\u00e9mon {ex}" in low or "pokemon {ex}" in low:
        classes.append("basicEx" if "basic" in low else "ex")
    if "tera" in low:
        classes.append("tera")
    if "ability" in low:
        classes.append("ability")
    if "200 or more" in low:
        classes.append("dmg200")
    if "special energy" in low:
        classes.append("specialEnergy")
    if "rule box" in low:
        classes.append("ruleBox")
    if not classes:
        classes.append("all")
    return scope, classes


def build(data_dir: str, out_path: str) -> dict:
    with open(os.path.join(data_dir, "cards.json"), encoding="utf-8") as f:
        cards = json.load(f)
    with open(os.path.join(data_dir, "attacks.json"), encoding="utf-8") as f:
        attacks = json.load(f)

    out_cards: dict[str, dict] = {}
    by_name: dict[str, list[int]] = {}

    for c in cards:
        cid = int(c["cardId"])
        name = c.get("name") or ""
        attacks_list = c.get("attacks") or []
        atk_ids = [int(a) if isinstance(a, int) else int(a["attackId"]) for a in attacks_list]
        skills = c.get("skills") or []
        skill_names = [s.get("name") for s in skills if isinstance(s, dict)]
        out_cards[str(cid)] = {
            "n": name,
            "ct": c.get("cardType"),          # CardType: 0 POKEMON 1 ITEM 2 TOOL 3 SUPPORTER 4 STADIUM 5 BASIC_ENERGY 6 SPECIAL_ENERGY
            "pt": c.get("pokemonType"),       # EnergyType of the Pokemon (for weakness math)
            "et": c.get("evolutionType"),     # 0 none 1 basic 2 stage1 3 stage2 (per engine dump)
            "rc": c.get("retreatCost") or 0,
            "hp": c.get("hp") or 0,
            "w": c.get("weakness"),
            "res": c.get("resistance"),
            "en": c.get("energyType"),
            "ex": 1 if c.get("ex") else 0,
            "mex": 1 if c.get("megaEx") else 0,
            "ace": 1 if c.get("aceSpec") else 0,
            "ef": c.get("evolvesFrom"),
            "b": 1 if c.get("basic") else 0,
            "s1": 1 if c.get("stage1") else 0,
            "s2": 1 if c.get("stage2") else 0,
            "atk": atk_ids,
            "sk": skill_names,
            "tr": 1 if c.get("tera") else 0,
        }
        prof = prevent_profile(skills) if c.get("cardType") == 0 else None
        if prof:
            out_cards[str(cid)]["pv"] = prof[1]
            out_cards[str(cid)]["pvs"] = prof[0]
        if is_gust(skills):
            out_cards[str(cid)]["gu"] = 1
        by_name.setdefault(name, []).append(cid)

    out_attacks: dict[str, dict] = {}
    for a in attacks:
        aid = int(a["attackId"])
        out_attacks[str(aid)] = {
            "n": a.get("name") or "",
            "d": a.get("damage") or 0,
            "e": a.get("energies") or [],
            "t": a.get("text") or "",
        }

    payload = {"cards": out_cards, "attacks": out_attacks, "by_name": by_name}
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    return payload


def main() -> None:
    data_dir = os.path.join(ROOT, "data")
    out_path = os.path.join(ROOT, "assets", "card_index.json")
    payload = build(data_dir, out_path)
    size = os.path.getsize(out_path)
    print(f"wrote {out_path}: {len(payload['cards'])} cards, "
          f"{len(payload['attacks'])} attacks, {size/1024:.1f} KiB")


if __name__ == "__main__":
    sys.exit(main())
