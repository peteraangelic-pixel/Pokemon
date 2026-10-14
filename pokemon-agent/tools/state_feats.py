# shared state-feature extractor (used by gen + agent; keep in sync with v42.2 agent)
def state_features(obs, me_idx, opp_idx, cardfn):
    cur = obs.get("current") or {}
    players = cur.get("players") or [{}, {}]
    me = players[me_idx] if len(players) > me_idx else {}
    op = players[opp_idx] if len(players) > opp_idx else {}
    def act(p):
        a = p.get("active") or []
        return a[0] if a else {}
    my_a, op_a = act(me), act(op)
    def hp_ratio(poke):
        hp = float(poke.get("hp") or 0); mx = float(poke.get("maxHp") or 0)
        return (hp / mx if mx else 0.0), hp, mx
    my_hr, my_hp, my_mx = hp_ratio(my_a)
    op_hr, op_hp, op_mx = hp_ratio(op_a)
    def bench_ratio(p):
        b = p.get("bench") or []
        tot = sum(float(x.get("hp") or 0) for x in b if isinstance(x, dict))
        mxt = sum(float(x.get("maxHp") or 0) for x in b if isinstance(x, dict))
        return (tot / mxt if mxt else 0.0), len(b)
    my_br, my_bn = bench_ratio(me)
    op_br, op_bn = bench_ratio(op)
    def water_disc(p):
        return sum(1 for d in (p.get("discard") or []) if isinstance(d, dict) and d.get("id") == 3)
    my_prizes_taken = 6 - len(me.get("prize") or [])
    op_prizes_taken = 6 - len(op.get("prize") or [])
    return [
        min(float(cur.get("turn") or 0), 50) / 50.0,
        float(me.get("deckCount") or 0) / 60.0,
        float(op.get("deckCount") or 0) / 60.0,
        min(float(me.get("handCount") or 0), 12) / 12.0,
        min(float(op.get("handCount") or 0), 12) / 12.0,
        my_bn / 5.0, op_bn / 5.0,
        my_hr, op_hr,
        min(len(my_a.get("energies") or []), 5) / 5.0,
        min(len(op_a.get("energies") or []), 5) / 5.0,
        my_br, op_br,
        min(water_disc(me), 15) / 15.0,
        min(water_disc(op), 15) / 15.0,
        my_prizes_taken / 6.0,
        op_prizes_taken / 6.0,
        my_mx / 400.0, op_mx / 400.0,
        (my_hp - op_hp) / 400.0,
    ]

SPREAD_IDS = {741, 742, 743, 245, 119, 120, 121, 131, 132, 133, 112}
GRASS_IDS = {150, 348, 93, 347, 921, 89, 90, 42, 92, 149, 346}
FIGHT_IDS = {678, 333, 677, 974, 676}
WALL_IDS = {345, 533, 344, 532, 117, 386, 150, 283, 756, 1031}
MIRROR_IDS = {721, 722, 723}
ARCHES = ["SPREAD", "GRASS", "FIGHTING", "WALL", "MIRROR", "DEFAULT"]

def deck_archetype(deck_ids):
    s = set(deck_ids)
    if s & SPREAD_IDS: return "SPREAD"
    if s & MIRROR_IDS and 723 in s: return "MIRROR"
    if s & FIGHT_IDS: return "FIGHTING"
    if s & WALL_IDS and not (s & GRASS_IDS): return "WALL"
    if s & GRASS_IDS: return "GRASS"
    return "DEFAULT"
