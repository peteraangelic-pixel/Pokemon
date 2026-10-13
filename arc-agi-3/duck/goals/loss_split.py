"""Where do points go? Split lost score into 'level 1 never solved' vs 'stuck later'.

python loss_split.py ../ops/results/r005-output/out_dfranzen__arc-agi-3-milestone-2-solution/benchmark.json
"""
import json, statistics as st, sys

gr = json.load(open(sys.argv[1]))["game_runs"]
l1 = later = 0.0
share_l1, share_last, l1_tokens = [], [], []
for r in gr:
    n, k = r["number_of_levels"], r["levels_completed"]
    lost = sum(range(k + 1, n + 1)) / (n * (n + 1) / 2) * 100
    if k == 0:
        l1 += lost
    else:
        later += lost
    toks = [h.get("generated_tokens", 0) for h in r["history"]]
    T = sum(toks) or 1
    apl = r["actions_per_level"]
    if k >= 1:
        l1_tokens.append(sum(toks[: apl[0]]))
        share_l1.append(sum(toks[: apl[0]]) / T)
        share_last.append(sum(toks[sum(apl[:k]):]) / T)
N = len(gr)
print(f"runs={N} zero-level runs={sum(r['levels_completed']==0 for r in gr)}")
print(f"lost pts/game: level-1 never solved {l1/N:.1f} | after >=1 solved level {later/N:.1f}")
print(f"median level-1 tokens {st.median(l1_tokens):.0f}; mean token share level 1 {st.mean(share_l1):.2f}; "
      f"on the final unsolved level {st.mean(share_last):.2f}")
