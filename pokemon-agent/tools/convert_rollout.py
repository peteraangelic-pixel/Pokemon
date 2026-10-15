#!/usr/bin/env python3
"""Convert policy_rollout POL1 binary logs to the training .npz schema used by
tools/train_policy.py (S, O mask-padded to MAX_OPT, Y=chosen, R=outcome).
Memory-safe: two passes over the file, preallocated f16 arrays."""
import argparse
import struct
import numpy as np

DS, DO, MAX_OPT = 96, 64, 32
REC_HEAD = DS * 2 + 1  # state f16 + n u8


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bin")
    ap.add_argument("out")
    args = ap.parse_args()
    data = open(args.bin, "rb").read()
    assert data[:4] == b"POL1", "bad magic"
    n = len(data)
    # pass 1: count decisions
    pos, cnt = 4, 0
    while pos < n:
        no = data[pos + DS * 2]
        pos += REC_HEAD + no * DO * 2 + 3
        cnt += 1
    print(f"{cnt} decisions in log")
    S = np.zeros((cnt, DS), dtype=np.float32)
    O = np.zeros((cnt, MAX_OPT, DO), dtype=np.float16)
    M = np.zeros((cnt, MAX_OPT), dtype=np.float32)
    Y = np.zeros(cnt, dtype=np.int32)
    R = np.zeros(cnt, dtype=np.float32)
    # pass 2: fill
    pos = 4
    for i in range(cnt):
        S[i] = np.frombuffer(data, dtype="<f2", count=DS, offset=pos).astype(np.float32)
        pos += DS * 2
        no = data[pos]; pos += 1
        o = np.frombuffer(data, dtype="<f2", count=no * DO, offset=pos).reshape(no, DO)
        pos += no * DO * 2
        O[i, :no] = o
        M[i, :no] = 1.0
        Y[i] = struct.unpack_from("<H", data, pos)[0]; pos += 2
        R[i] = struct.unpack_from("<b", data, pos)[0]; pos += 1
    np.savez_compressed(args.out, S=S, O=O, M=M, Y=Y, R=R)
    print(f"converted {cnt} decisions -> {args.out}  win_frac={(R > 0).mean():.3f}")


if __name__ == "__main__":
    main()
