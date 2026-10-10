#!/bin/bash
# Offline toolchain + vendored dependencies for battery-sim.
# For sandboxed / air-gapped environments (no rustup, no crates.io access).
#
# What it does:
#   1. downloads the Rust 1.97.0 toolchain from PyPI (arena-rust-toolchain wheels),
#   2. downloads + vendors rayon and its deps from codeload.github.com,
#   3. assembles the toolchain and writes a cargo source-replacement config.
#
# Usage:
#   bash tools/setup-offline-toolchain.sh [DEST]        (default: ~/battery-sim-offline)
# Then:
#   export PATH="DEST/rust-toolchain/prefix/bin:$PATH" CARGO_HOME="DEST/cargo-home"
#   cd battery-sim && cargo build --release --offline
set -euo pipefail
DEST="${1:-$HOME/battery-sim-offline}"
mkdir -p "$DEST"
DEST=$(cd "$DEST" && pwd)
mkdir -p "$DEST/rustdl" "$DEST/pylibs" "$DEST/vendor-src" "$DEST/vendor" "$DEST/rust-toolchain" "$DEST/cargo-home"
echo "== DEST=$DEST =="

echo "== 1/4 toolchain wheels (PyPI) =="
pip download arena-rust-toolchain arena-rust-toolchain-data1 arena-rust-toolchain-data2 arena-rust-toolchain-data3 -d "$DEST/rustdl" --no-deps -q
python3 -c "import zstandard" 2>/dev/null || pip install --target "$DEST/pylibs" --break-system-packages -q zstandard

echo "== 2/4 vendored crates (codeload.github.com) =="
cd "$DEST/vendor-src"
curl -sL https://codeload.github.com/rayon-rs/rayon/tar.gz/refs/tags/v1.10.0 -o rayon.tgz
curl -sL https://codeload.github.com/rayon-rs/rayon/tar.gz/refs/tags/rayon-core-v1.12.1 -o rayon-core.tgz
curl -sL https://codeload.github.com/crossbeam-rs/crossbeam/tar.gz/refs/tags/crossbeam-utils-0.8.20 -o crossbeam-utils.tgz
curl -sL https://codeload.github.com/crossbeam-rs/crossbeam/tar.gz/refs/tags/crossbeam-epoch-0.9.18 -o crossbeam-epoch.tgz
curl -sL https://codeload.github.com/crossbeam-rs/crossbeam/tar.gz/refs/tags/crossbeam-deque-0.8.5 -o crossbeam-deque.tgz
curl -sL https://codeload.github.com/bluss/either/tar.gz/refs/tags/1.13.0 -o either.tgz
for f in *.tgz; do tar -xzf "$f"; done
mv rayon-1.10.0 "$DEST/vendor/rayon-1.10.0"
mv rayon-rayon-core-v1.12.1/rayon-core "$DEST/vendor/rayon-core-1.12.1"
mv crossbeam-crossbeam-utils-0.8.20/crossbeam-utils "$DEST/vendor/crossbeam-utils-0.8.20"
mv crossbeam-crossbeam-epoch-0.9.18/crossbeam-epoch "$DEST/vendor/crossbeam-epoch-0.9.18"
mv crossbeam-crossbeam-deque-0.8.5/crossbeam-deque "$DEST/vendor/crossbeam-deque-0.8.5"
mv either-1.13.0 "$DEST/vendor/either-1.13.0"
rm -rf rayon-rayon-core-v1.12.1 crossbeam-crossbeam-* *.tgz
# restore shared files that were symlinks into the crossbeam meta-repo
curl -sL https://codeload.github.com/crossbeam-rs/crossbeam/tar.gz/refs/tags/crossbeam-utils-0.8.20 -o cbu.tgz
tar -xzf cbu.tgz crossbeam-crossbeam-utils-0.8.20/no_atomic.rs crossbeam-crossbeam-utils-0.8.20/build-common.rs
find "$DEST/vendor" -type l -delete
cp crossbeam-crossbeam-utils-0.8.20/no_atomic.rs "$DEST/vendor/crossbeam-utils-0.8.20/no_atomic.rs"
cp crossbeam-crossbeam-utils-0.8.20/build-common.rs "$DEST/vendor/crossbeam-utils-0.8.20/build-common.rs"
cp "$DEST/vendor/crossbeam-utils-0.8.20/src/sync/once_lock.rs" "$DEST/vendor/crossbeam-epoch-0.9.18/src/sync/once_lock.rs"
rm -rf crossbeam-crossbeam-utils-0.8.20 cbu.tgz
# strip [lints] workspace + path deps; add checksum files
for d in "$DEST"/vendor/*/; do
python3 - "$d" <<'PYEOF'
import re, sys, pathlib
p = pathlib.Path(sys.argv[1]) / 'Cargo.toml'
s = p.read_text()
s = re.sub(r'\[lints[^\]]*\][^\[]*', '', s)
s = re.sub(r',\s*path\s*=\s*"[^"]*"', '', s)
s = re.sub(r'path\s*=\s*"[^"]*",\s*', '', s)
s = re.sub(r'path\s*=\s*"[^"]*"', '', s)
p.write_text(s)
PYEOF
echo '{"files":{}}' > "$d/.cargo-checksum.json"
done
cat > "$DEST/cargo-home/config.toml" <<EOF
[source.crates-io]
replace-with = "vendored-sources"

[source.vendored-sources]
directory = "$DEST/vendor"
EOF

echo "== 3/4 assemble Rust toolchain =="
cd "$DEST/rustdl" && mkdir -p x && cd x
for w in ../*.whl; do python3 -m zipfile -e "$w" . >/dev/null; done
BS_DEST="$DEST" PYTHONPATH="$DEST/pylibs" python3 - <<'PYEOF'
import zstandard, tarfile, os, shutil
dest = os.environ['BS_DEST']
base = os.path.join(dest, 'rustdl', 'x')
parts = [os.path.join(base, f'arena_rust_toolchain_data{i}', f'part_{i}') for i in (1, 2, 3)]
combined = os.path.join(dest, 'toolchain.tar.zst')
with open(combined, 'wb') as out:
    for p in parts:
        with open(p, 'rb') as f:
            shutil.copyfileobj(f, out, 1 << 20)
dctx = zstandard.ZstdDecompressor()
os.makedirs(os.path.join(dest, 'rust-toolchain'), exist_ok=True)
with open(combined, 'rb') as f, open(os.path.join(dest, 'toolchain.tar'), 'wb') as out:
    dctx.copy_stream(f, out)
with tarfile.open(os.path.join(dest, 'toolchain.tar')) as t:
    t.extractall(os.path.join(dest, 'rust-toolchain'))
tb = os.path.join(dest, 'rust-toolchain')
if not os.path.isdir(os.path.join(tb, 'prefix')):
    for child in os.listdir(tb):
        if child.startswith('rust-') and os.path.isdir(os.path.join(tb, child)):
            os.rename(os.path.join(tb, child), os.path.join(tb, 'prefix'))
            break
print('toolchain OK:', sorted(os.listdir(os.path.join(tb, 'prefix', 'bin')))[:8])
PYEOF

echo "== 4/4 done =="
echo "Use with:"
echo "  export PATH=\"$DEST/rust-toolchain/prefix/bin:\$PATH\" CARGO_HOME=\"$DEST/cargo-home\""
echo "  cd battery-sim && cargo build --release --offline"
