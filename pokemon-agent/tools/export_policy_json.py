#!/usr/bin/env python3
"""Export trained policy weights (.npz from train_policy.py) to JSON for the
Rust rollout binary."""
import argparse, json
import numpy as np

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("npz")
    ap.add_argument("out")
    args = ap.parse_args()
    d = np.load(args.npz)
    payload = {
        "W1": d["W1"].astype(np.float32).tolist(),
        "b1": d["b1"].astype(np.float32).tolist(),
        "W2": d["W2"].astype(np.float32).tolist(),
        "b2": d["b2"].astype(np.float32).tolist(),
        "W3": d["W3"].astype(np.float32).tolist(),
        "b3": d["b3"].astype(np.float32).tolist(),
    }
    with open(args.out, "w") as f:
        json.dump(payload, f)
    print("wrote", args.out)

if __name__ == "__main__":
    main()
