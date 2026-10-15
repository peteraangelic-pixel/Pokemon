#!/usr/bin/env python3
"""Convert policy_rollout POL1 binary logs to the training .npz schema used by
tools/train_policy.py (S, O mask-padded to MAX_OPT, Y=chosen, R=outcome)."""
import argparse
import numpy as np

DS, DO, MAX_OPT = 96, 64, 32

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bin")
    ap.add_argument("out")
    args = ap.parse_args()
    raw = np.fromfile(args.bin, dtype=np.uint8)
    assert raw[:4].tobytes() == b"POL1", "bad magic"
    # parse via uint16 view for f16 payloads
    u16 = np.frombuffer(raw.tobytes(), dtype="<u2")
    # walk byte offsets manually
    data = raw.tobytes()
    n = len(data)
    pos = 4
    Ss, Os, Ms, Ys, Rs = [], [], [], [], []
    import struct
    while pos < n:
        s_bytes = data[pos:pos + DS * 2]; pos += DS * 2
        s = np.frombuffer(s_bytes, dtype="<f2").astype(np.float32)
        no = data[pos]; pos += 1
        o_bytes = data[pos:pos + no * DO * 2]; pos += no * DO * 2
        o = np.frombuffer(o_bytes, dtype="<f2").astype(np.float32).reshape(no, DO)
        chosen = struct.unpack_from("<H", data, pos)[0]; pos += 2
        r = struct.unpack_from("<b", data, pos)[0]; pos += 1
        Ss.append(s)
        pad = np.zeros((MAX_OPT, DO), dtype=np.float32)
        pad[:no] = o
        Os.append(pad)
        Ms.append(no)
        Ys.append(chosen)
        Rs.append(float(r))
    S = np.stack(Ss).astype(np.float32)
    O = np.stack(Os).astype(np.float16)
    M = (np.arange(MAX_OPT)[None, :] < np.array(Ms)[:, None]).astype(np.float32)
    Y = np.array(Ys, dtype=np.int32)
    R = np.array(Rs, dtype=np.float32)
    np.savez_compressed(args.out, S=S, O=O, M=M, Y=Y, R=R)
    print(f"converted {len(Y)} decisions -> {args.out}  win_frac={(R > 0).mean():.3f}")

if __name__ == "__main__":
    main()
