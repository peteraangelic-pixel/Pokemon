#!/usr/bin/env python3
"""Benchmark multiprocessing vs sequential for summarize_recordings.

Pokazuje przyspieszenie z multiprocessing dla różnych rozmiarów zbiorów danych.
"""

import time
import sys
from pathlib import Path
from multiprocessing import cpu_count

# Importuj oryginalną funkcję (sequential)
sys.path.insert(0, str(Path(__file__).parent))
from summarize_recordings import summarize_paths
from summarize_recordings_mp import summarize_paths_parallel


def create_test_recordings(num_files: int, output_dir: Path):
    """Stwórz testowe pliki JSONL."""
    output_dir.mkdir(parents=True, exist_ok=True)

    for i in range(num_files):
        path = output_dir / f"test_game_{i:03d}.jsonl"
        with open(path, 'w') as f:
            # Symuluj nagranie z 100 eventami
            for j in range(100):
                event = {
                    "game_id": f"test_game_{i}",
                    "step": j,
                    "frame": [[i % 16] * 10 for _ in range(10)],  # Prosta siatka 10x10
                    "action": {"name": "RIGHT"},
                    "state": "PLAYING",
                    "levels_completed": 0
                }
                f.write(str(event) + "\n")

    return list(output_dir.glob("*.jsonl"))


def benchmark(num_files: int):
    """Benchmark sequential vs multiprocessing."""
    test_dir = Path(f"/tmp/test_recordings_{num_files}")

    # Stwórz testowe dane
    print(f"\n=== Benchmark: {num_files} plików ===")
    print(f"Tworzenie {num_files} testowych plików JSONL...", file=sys.stderr)
    paths = create_test_recordings(num_files, test_dir)

    # Sequential
    print(f"\nSequential processing...", file=sys.stderr)
    start = time.time()
    result_seq = summarize_paths(paths)
    time_seq = time.time() - start
    print(f"  Czas: {time_seq:.2f}s", file=sys.stderr)

    # Multiprocessing
    print(f"\nMultiprocessing ({cpu_count()} workers)...", file=sys.stderr)
    start = time.time()
    result_mp = summarize_paths_parallel(paths)
    time_mp = time.time() - start
    print(f"  Czas: {time_mp:.2f}s", file=sys.stderr)

    # Porównanie
    speedup = time_seq / time_mp if time_mp > 0 else 0
    print(f"\nPrzyspieszenie: {speedup:.1f}x", file=sys.stderr)

    return time_seq, time_mp, speedup


def main():
    print("Benchmark: Sequential vs Multiprocessing dla summarize_recordings")
    print(f"CPU count: {cpu_count()}\n")

    # Testuj dla różnych rozmiarów
    sizes = [10, 50, 100]
    results = []

    for size in sizes:
        time_seq, time_mp, speedup = benchmark(size)
        results.append((size, time_seq, time_mp, speedup))

    # Podsumowanie
    print("\n" + "="*60)
    print("PODSUMOWANIE")
    print("="*60)
    print(f"{'Pliki':<10} {'Sequential':<15} {'Multiprocessing':<15} {'Przyspieszenie':<15}")
    print("-"*60)
    for size, time_seq, time_mp, speedup in results:
        print(f"{size:<10} {time_seq:>10.2f}s {time_mp:>10.2f}s {speedup:>10.1f}x")
    print("="*60)


if __name__ == "__main__":
    main()
