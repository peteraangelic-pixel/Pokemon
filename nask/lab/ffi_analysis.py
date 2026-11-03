"""Python/Rust FFI for offline synthetic document analysis, no network."""
import ctypes
import json
from pathlib import Path


def analyze(documents: list[dict], library: Path, threads: int) -> dict:
    lib = ctypes.CDLL(str(library.resolve()))
    lib.nasklab_analyze.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_size_t]
    lib.nasklab_analyze.restype = ctypes.c_void_p
    lib.nasklab_free.argtypes = [ctypes.c_void_p]
    lib.nasklab_free.restype = None
    payload = json.dumps(documents, ensure_ascii=False).encode('utf-8')
    if len(payload) > 64 * 1024 * 1024:
        raise ValueError('analysis input exceeds 64 MiB')
    buffer = ctypes.create_string_buffer(payload)
    pointer = lib.nasklab_analyze(buffer, len(payload), threads)
    if not pointer:
        raise RuntimeError('native analysis returned null')
    try:
        result = json.loads(ctypes.string_at(pointer).decode('utf-8'))
    finally:
        lib.nasklab_free(pointer)
    if 'error' in result:
        raise ValueError(result['error'])
    return result
