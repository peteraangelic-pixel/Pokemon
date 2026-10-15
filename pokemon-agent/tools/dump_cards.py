"""Dump the full card / attack database from the cabt native engine."""
import ctypes, json, os, sys
from kaggle_environments.envs.cabt.cg.sim import lib

def _dump(fn):
    f = getattr(lib, fn)
    f.restype = ctypes.c_char_p
    f.argtypes = []
    raw = f()
    return json.loads(raw.decode("utf-8"))

def main(outdir="data"):
    os.makedirs(outdir, exist_ok=True)
    cards = _dump("AllCard")
    attacks = _dump("AllAttack")
    with open(os.path.join(outdir, "cards.json"), "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False)
    with open(os.path.join(outdir, "attacks.json"), "w", encoding="utf-8") as f:
        json.dump(attacks, f, ensure_ascii=False)
    print(f"cards={len(cards)} attacks={len(attacks)}")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data")
