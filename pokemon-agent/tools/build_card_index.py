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
                  "ef": evolvesFromName, "atk": [attackIds], "sk": [skillNames]}
  },
  "attacks": {"<attackId>": {"n": name, "d": damage, "e": [energies], "t": text}},
  "by_name": {"<name>": [cardIds]}
}
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


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
        }
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
