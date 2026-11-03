"""Exercise real Rust FFI with explicitly fictional documents only."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ffi_analysis import analyze

parser = argparse.ArgumentParser()
parser.add_argument('--library', type=Path, required=True)
library = parser.parse_args().library
fixtures = [
    {'program':'fixture-a', 'source_url':'https://a.invalid/', 'body':'<form><input type="file"></form>'},
    {'program':'fixture-b', 'source_url':'https://b.invalid/a.js', 'body':"fetch('/api/example'); // żółw 🐢"},
    {'program':'fixture-c', 'source_url':'https://c.invalid/modernizr-custom.js', 'body':"new FormData(); input.type='file'"},
]
result = analyze(fixtures, library, 2)
assert result['confirmed_vulnerabilities'] == 0
assert result['documents'][0]['upload_surface']
assert result['documents'][1]['route_literals'] == ['/api/example']
assert not result['documents'][2]['upload_surface']
assert result['documents'][2]['file_control_mention']
try:
    analyze(fixtures, library, 0)
except ValueError:
    pass
else:
    raise AssertionError('FFI accepted an invalid thread count')
print('Rust/Python FFI synthetic smoke test passed')
