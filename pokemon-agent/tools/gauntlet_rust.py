#!/usr/bin/env python3
"""Wrapper that uses rust_gauntlet binary if available, else falls back to Python gauntlet_live.py"""
import pathlib, subprocess, sys, shutil, os

ROOT=pathlib.Path(__file__).resolve().parents[1]
rust_bin=ROOT/"rust"/"bin"/"rust_gauntlet"

def main():
    args=sys.argv[1:]
    if rust_bin.exists() and os.access(rust_bin, os.X_OK):
        print(f"Using Rust binary {rust_bin} (rayon parallel)")
        cmd=[str(rust_bin)]+args
        # Ensure we run from ROOT
        result=subprocess.run(cmd, cwd=ROOT)
        sys.exit(result.returncode)
    else:
        print("Rust binary not found, falling back to Python gauntlet_live.py")
        cmd=[str(ROOT/".venv"/"bin"/"python"), "tools/gauntlet_live.py"]+args
        result=subprocess.run(cmd, cwd=ROOT)
        sys.exit(result.returncode)

if __name__=="__main__":
    main()
