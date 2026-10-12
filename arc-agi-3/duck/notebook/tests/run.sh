#!/usr/bin/env bash
# Recreate the dev tree (duck-harness@7652836 + Franzen patch + our patches) and run the tests.
# Usage: bash arc-agi-3/duck/notebook/tests/run.sh   (needs network to github.com and pypi)
set -euo pipefail
HERE=$(cd "$(dirname "$0")/.." && pwd)
WORK=${WORK:-/tmp/duck-dev}
rm -rf "$WORK" && git clone -q https://github.com/Tufalabs/duck-harness.git "$WORK" && cd "$WORK" && git checkout -q 7652836
python3 - "$HERE" <<'PY'
import json, sys
nb = json.load(open(sys.argv[1] + "/base/franzen-m2.ipynb"))
cell = next("".join(c["source"]) for c in nb["cells"] if "".join(c["source"]).startswith("%%writefile /kaggle/harness-changes.patch"))
open("/tmp/franzen.patch", "w").write(cell.split("\n", 1)[1] + "\n")
PY
git apply --include='ARC3-Inference/*' /tmp/franzen.patch
for p in "$HERE"/patches/*.patch; do git apply --include='ARC3-Inference/*' "$p"; echo "applied $(basename "$p")"; done
python3 -m venv "$WORK/.venv" && "$WORK/.venv/bin/pip" -q install requests numpy pillow
cd ARC3-Inference
for t in "$HERE"/tests/test_*.py; do echo "== $(basename "$t")"; "$WORK/.venv/bin/python" "$t"; done
