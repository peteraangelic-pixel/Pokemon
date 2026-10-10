//! `arc3` command-line front-end.
//!
//! ```text
//! arc3 bench   [--size 64] [--frames 2000]   throughput of the segmentation kernel
//! arc3 segment <grid.json>                   segment one grid, print JSON
//! arc3 score   <levels.json>                 RHAE for [[human, agent], ...]
//! ```

use arc3::{rhae, segment_layer, Grid};
use rayon::prelude::*;
use std::env;
use std::fs;
use std::process::ExitCode;
use std::time::Instant;

fn usage() -> ExitCode {
    eprintln!("usage:");
    eprintln!("  arc3 bench   [--size N] [--frames N]");
    eprintln!("  arc3 segment <grid.json>");
    eprintln!("  arc3 score   <levels.json>");
    ExitCode::from(2)
}

fn flag(args: &[String], name: &str, default: usize) -> usize {
    args.windows(2)
        .find(|w| w[0] == name)
        .and_then(|w| w[1].parse().ok())
        .unwrap_or(default)
}

/// Deterministic pseudo-random frame so benchmarks are reproducible.
fn synthetic(size: usize, seed: u64) -> Grid {
    let mut state = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
    let mut rows = Vec::with_capacity(size);
    for _ in 0..size {
        let mut row = Vec::with_capacity(size);
        for _ in 0..size {
            state ^= state << 13;
            state ^= state >> 7;
            state ^= state << 17;
            // Bias towards a few colours so components are large and the
            // containment / contour paths are actually exercised.
            row.push(((state >> 33) % 4) as u8);
        }
        rows.push(row);
    }
    Grid::from_rows(&rows).expect("synthetic grid")
}

/// A frame closer to a real ARC-AGI-3 board: a handful of large solid objects
/// on a background, rather than salt-and-pepper noise.
fn synthetic_blobs(size: usize, seed: u64) -> Grid {
    let mut state = seed
        .wrapping_mul(6364136223846793005)
        .wrapping_add(1442695040888963407);
    let mut rand = move || {
        state ^= state << 13;
        state ^= state >> 7;
        state ^= state << 17;
        state
    };
    let mut rows = vec![vec![0u8; size]; size];
    for _ in 0..18 {
        let v = (rand() % 5 + 1) as u8;
        let h = (rand() % 8 + 3) as usize;
        let w = (rand() % 8 + 3) as usize;
        let r0 = (rand() % (size as u64 - h as u64 + 1)) as usize;
        let c0 = (rand() % (size as u64 - w as u64 + 1)) as usize;
        for r in r0..r0 + h {
            for c in c0..c0 + w {
                rows[r][c] = v;
            }
        }
    }
    Grid::from_rows(&rows).expect("blob grid")
}

fn cmd_bench(args: &[String]) -> ExitCode {
    let size = flag(args, "--size", 64);
    let frames = flag(args, "--frames", 2000);
    let mode = args
        .windows(2)
        .find(|w| w[0] == "--mode")
        .map(|w| w[1].as_str())
        .unwrap_or("salt");

    if frames == 0 {
        eprintln!("--frames must be >= 1");
        return usage();
    }

    let grids: Vec<Grid> = match mode {
        "blobs" => (0..frames)
            .map(|i| synthetic_blobs(size, i as u64 + 1))
            .collect(),
        "salt" => (0..frames).map(|i| synthetic(size, i as u64 + 1)).collect(),
        other => {
            eprintln!("unknown --mode {} (expected `salt` or `blobs`)", other);
            return usage();
        }
    };

    // warm up
    let _ = segment_layer(&grids[0]);

    let t0 = Instant::now();
    let segs: Vec<_> = grids.par_iter().map(segment_layer).collect();
    let elapsed = t0.elapsed();

    let total_nodes: usize = segs.iter().map(|s| s.nodes.len()).sum();
    let secs = elapsed.as_secs_f64().max(1e-9);

    println!("frames           : {}", frames);
    println!("grid             : {}x{}", size, size);
    println!("threads          : {}", rayon::current_num_threads());
    println!("wall clock       : {:.3} s", secs);
    println!("throughput       : {:.1} frames/s", frames as f64 / secs);
    println!("per frame        : {:.3} ms", secs * 1e3 / frames as f64);
    println!("total components : {}", total_nodes);
    println!("avg components   : {:.1}", total_nodes as f64 / frames as f64);
    ExitCode::SUCCESS
}

fn cmd_segment(path: &str) -> ExitCode {
    let text = match fs::read_to_string(path) {
        Ok(t) => t,
        Err(e) => {
            eprintln!("cannot read {}: {}", path, e);
            return ExitCode::FAILURE;
        }
    };
    let raw: Vec<Vec<u8>> = match serde_json::from_str(&text) {
        Ok(v) => v,
        Err(e) => {
            eprintln!("{} is not a 2D array of integers: {}", path, e);
            return ExitCode::FAILURE;
        }
    };
    let grid = match Grid::from_rows(&raw) {
        Ok(g) => g,
        Err(e) => {
            eprintln!("bad grid: {}", e);
            return ExitCode::FAILURE;
        }
    };
    println!("{}", segment_layer(&grid).to_json());
    ExitCode::SUCCESS
}

fn cmd_score(path: &str) -> ExitCode {
    let text = match fs::read_to_string(path) {
        Ok(t) => t,
        Err(e) => {
            eprintln!("cannot read {}: {}", path, e);
            return ExitCode::FAILURE;
        }
    };
    let raw: Vec<(u32, u32)> = match serde_json::from_str(&text) {
        Ok(v) => v,
        Err(e) => {
            eprintln!("expected [[human, agent], ...]: {}", e);
            return ExitCode::FAILURE;
        }
    };
    let total = rhae(&raw);
    let ceiling = 1.15_f64.powi(2);
    println!("levels           : {}", raw.len());
    println!("RHAE             : {:.6}", total);
    println!("ceiling          : {:.6}", ceiling);
    println!("% of ceiling     : {:.2}%", 100.0 * total / ceiling);
    ExitCode::SUCCESS
}

fn main() -> ExitCode {
    let args: Vec<String> = env::args().skip(1).collect();
    match args.first().map(|s| s.as_str()) {
        Some("bench") => cmd_bench(&args),
        Some("segment") => match args.get(1) {
            Some(p) => cmd_segment(p),
            None => usage(),
        },
        Some("score") => match args.get(1) {
            Some(p) => cmd_score(p),
            None => usage(),
        },
        _ => usage(),
    }
}
