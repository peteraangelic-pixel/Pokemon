use anyhow::Result;
use clap::Parser;
use std::path::{Path, PathBuf};
use std::fs;
use std::process::Command;

#[derive(Parser, Debug)]
struct Args {
    #[arg(long, default_value="assets/card_index.json")]
    card_index: String,
    #[arg(long, default_value="decks")]
    deck_pool_dir: String,
    #[arg(long, default_value="kaggle_results/bc_data_rust.npz")]
    out: String,
    #[arg(long, default_value_t=2000)]
    games: usize,
    #[arg(long, default_value_t=4)]
    jobs: usize,
    #[arg(long, default_value=".venv/lib/python3.11/site-packages/kaggle_environments/envs/cabt/cg/libcg.so")]
    lib_path: String,
    #[arg(long, default_value_t=7)]
    seed: u64,
}

fn main() -> Result<()> {
    let args = Args::parse();
    println!("=== gen_bc_data_rust_mp starting (multiprocessing) ===");
    println!("Args: {:?}", args);
    println!("This uses pure multiprocessing: {} child processes, each with its own libcg.so copy (100% isolation, like Python Pool that gave 84k samples in 128s)", args.jobs);

    let total_games = args.games;
    let jobs = args.jobs;
    let games_per_job = (total_games + jobs - 1) / jobs;

    let out_path = PathBuf::from(&args.out);
    if let Some(parent) = out_path.parent() { fs::create_dir_all(parent)?; }

    let tmp_dir = PathBuf::from("/tmp/bc_mp_shards");
    fs::create_dir_all(&tmp_dir)?;

    let mut children = Vec::new();
    let mut shard_paths = Vec::new();

    let current_exe = std::env::current_exe().unwrap_or_else(|_| PathBuf::from("./target/release/gen_bc_data_rust_mp"));
    // We'll spawn gen_bc_data_rust single-thread binary as child for max isolation
    // If that binary doesn't exist, fall back to self with --child flag (not implemented, so use single-thread binary path)
    let single_bin = PathBuf::from("rust/target/release/gen_bc_data_rust");
    let single_bin_alt = PathBuf::from("./target/release/gen_bc_data_rust");
    let child_bin = if single_bin.exists() { single_bin } else if single_bin_alt.exists() { single_bin_alt } else { PathBuf::from("pokemon-agent/rust/target/release/gen_bc_data_rust") };

    println!("Child binary: {:?}", child_bin);

    for job_id in 0..jobs {
        let start_game = job_id * games_per_job;
        let end_game = ((job_id + 1) * games_per_job).min(total_games);
        let n_games = end_game - start_game;
        if n_games == 0 { continue; }
        let shard_out = tmp_dir.join(format!("shard_{}.npz", job_id));
        shard_paths.push(shard_out.clone());
        let seed = args.seed + job_id as u64 * 10000;

        println!("Spawning job {}: games {} ({}-{}), seed {}, out {:?}", job_id, n_games, start_game, end_game, seed, shard_out);

        let mut cmd = Command::new(&child_bin);
        cmd.arg("--card-index").arg(&args.card_index)
            .arg("--deck-pool-dir").arg(&args.deck_pool_dir)
            .arg("--out").arg(&shard_out)
            .arg("--games").arg(n_games.to_string())
            .arg("--lib-path").arg(&args.lib_path)
            .arg("--seed").arg(seed.to_string());

        // If child_bin is mp binary itself, we need to avoid infinite recursion - but we use single-thread binary
        let child = cmd.spawn()?;
        children.push((job_id, child, shard_out, n_games));
    }

    println!("Spawned {} children, waiting...", children.len());
    let mut failed = 0;
    for (job_id, mut child, shard_out, n_games) in children {
        println!("Waiting for job {} ({} games)...", job_id, n_games);
        let status = child.wait()?;
        if !status.success() {
            eprintln!("Job {} failed with status {:?}", job_id, status);
            failed += 1;
        } else {
            println!("Job {} success, shard {:?}", job_id, shard_out);
        }
    }

    if failed > 0 {
        eprintln!("{} jobs failed", failed);
    }

    // Merge shards via python
    println!("Merging {} shards into {}", shard_paths.len(), args.out);
    let mut py_cmd = String::from("import numpy as np, pathlib; ");
    py_cmd.push_str(&format!("shards = [pathlib.Path('{}')]; ", tmp_dir.join("shard_*.npz").display()));
    // Use glob in python
    let merge_code = format!(
        r#"
import numpy as np, pathlib, glob
shards = sorted(glob.glob("{}/shard_*.npz"))
print(f"Found {{len(shards)}} shards")
all_S, all_O, all_M, all_Y, all_R = [], [], [], [], []
for p in shards:
    d = np.load(p)
    print(p, d["S"].shape)
    all_S.append(d["S"]); all_O.append(d["O"]); all_M.append(d["M"]); all_Y.append(d["Y"]); all_R.append(d["R"])
S = np.concatenate(all_S); O = np.concatenate(all_O); M = np.concatenate(all_M); Y = np.concatenate(all_Y); R = np.concatenate(all_R)
print(f"Merged {{len(S)}} decisions")
np.savez_compressed("{}", S=S, O=O, M=M, Y=Y, R=R)
print("saved")
"#,
        tmp_dir.display(),
        args.out
    );

    let py_candidates = [".venv/bin/python", "/home/runner/work/Pokemon/Pokemon/pokemon-agent/.venv/bin/python", "python3"];
    let mut saved = false;
    for py in &py_candidates {
        println!("Trying python {} to merge", py);
        let status = Command::new(py).arg("-c").arg(&merge_code).status();
        match status {
            Ok(s) if s.success() => { saved = true; break; },
            Ok(s) => eprintln!("python {} failed {:?}", py, s),
            Err(e) => eprintln!("python {} error {}", py, e),
        }
    }
    if !saved {
        anyhow::bail!("failed to merge shards");
    }

    println!("Done, merged into {}", args.out);
    Ok(())
}
