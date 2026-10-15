use anyhow::Result;
use clap::Parser;
use std::path::{Path, PathBuf};
use std::fs;
use rand::{SeedableRng, rngs::StdRng, Rng};

#[path = "../engine.rs"]
mod engine;
#[path = "../heuristic.rs"]
mod heuristic;
#[path = "../policy_feats.rs"]
mod policy_feats;

use engine::Engine;
use heuristic::{CardIndex as HeurCardIndex, Knobs, Plan};
use policy_feats::Featurizer;

#[derive(Parser, Debug)]
struct Args {
    #[arg(long, default_value="assets/card_index.json")]
    card_index: String,
    #[arg(long, default_value="decks")]
    deck_pool_dir: String,
    #[arg(long, default_value="kaggle_results/bc_data_rust.npz")]
    out: String,
    #[arg(long, default_value_t=50)]
    games: usize,
    #[arg(long, default_value_t=1)]
    jobs: usize,
    #[arg(long, default_value=".venv/lib/python3.11/site-packages/kaggle_environments/envs/cabt/cg/libcg.so")]
    lib_path: String,
    #[arg(long, default_value_t=7)]
    seed: u64,
}

fn load_deck_ids(path: &Path) -> Result<Vec<i32>> {
    let content = fs::read_to_string(path)?;
    let mut ids = Vec::new();
    for token in content.split(|c: char| c==',' || c.is_whitespace()) {
        if token.trim().is_empty() { continue; }
        if let Ok(id) = token.trim().parse::<i32>() { ids.push(id); }
    }
    if ids.len() != 60 {
        anyhow::bail!("deck {:?} has {} cards, expected 60", path, ids.len());
    }
    Ok(ids)
}

fn collect_deck_files(pool_dir: &Path) -> Vec<PathBuf> {
    let mut out = Vec::new();
    let patterns = vec![
        pool_dir.join("v56_tuned_34W.csv"),
        pool_dir.join("v12_30_boss4.csv"),
    ];
    for p in patterns { if p.exists() { out.push(p); } }
    for sub in ["top50_fresh22", "live_killers"] {
        let d = pool_dir.join(sub);
        if d.is_dir() {
            if let Ok(entries) = fs::read_dir(&d) {
                for e in entries.flatten() {
                    let path = e.path();
                    if path.extension().and_then(|s| s.to_str()) == Some("csv") {
                        out.push(path);
                        if out.len() >= 20 { break; }
                    }
                }
            }
        }
    }
    if out.is_empty() {
        if let Ok(entries) = fs::read_dir(pool_dir) {
            for e in entries.flatten() {
                let path = e.path();
                if path.extension().and_then(|s| s.to_str()) == Some("csv") {
                    out.push(path);
                    if out.len() >= 10 { break; }
                }
            }
        }
    }
    out
}

fn main() -> Result<()> {
    let args = Args::parse();
    println!("=== gen_bc_data_rust starting ===");
    println!("Args: {:?}", args);
    println!("Card index: {}", args.card_index);
    let heur_index = HeurCardIndex::load(&args.card_index)?;
    let feat = Featurizer::load(&args.card_index)?;
    println!("Loaded {} cards, {} attacks", heur_index.cards.len(), heur_index.attacks.len());
    let pool_dir = PathBuf::from(&args.deck_pool_dir);
    let deck_files = collect_deck_files(&pool_dir);
    println!("Deck pool: {} files", deck_files.len());
    for f in &deck_files {
        println!("  pool: {:?}", f);
    }
    if deck_files.is_empty() {
        anyhow::bail!("no decks found in {}", args.deck_pool_dir);
    }
    let mut deck_cache: Vec<Vec<i32>> = Vec::new();
    for p in &deck_files {
        match load_deck_ids(p) {
            Ok(d) => deck_cache.push(d),
            Err(e) => eprintln!("skip {:?}: {}", p, e),
        }
    }
    println!("Loaded {} valid decks", deck_cache.len());
    let lib_path = args.lib_path.clone();
    let lib_path = if Path::new(&lib_path).exists() { lib_path } else {
        let alts = [
            ".venv/lib/python3.11/site-packages/kaggle_environments/envs/cabt/cg/libcg.so",
            "/home/runner/work/Pokemon/Pokemon/pokemon-agent/.venv/lib/python3.11/site-packages/kaggle_environments/envs/cabt/cg/libcg.so",
        ];
        let mut found = lib_path.clone();
        for alt in alts {
            if Path::new(alt).exists() { found = alt.to_string(); break; }
        }
        found
    };
    println!("Lib path: {}", lib_path);
    if !Path::new(&lib_path).exists() {
        eprintln!("ERROR: libcg.so not found at {}", lib_path);
        if let Ok(out) = std::process::Command::new("find").arg(".").arg("-name").arg("libcg.so").output() {
            eprintln!("find output: {}", String::from_utf8_lossy(&out.stdout));
        }
        anyhow::bail!("libcg.so not found");
    }
    println!("Creating Engine once...");
    let mut engine = Engine::new(&lib_path)?;
    println!("Engine created OK");

    let knobs = Knobs::default();
    let games = args.games;
    let seed = args.seed;
    let start = std::time::Instant::now();
    let mut all_s: Vec<[f32; 96]> = Vec::new();
    let mut all_o: Vec<[[f32;64];32]> = Vec::new();
    let mut all_m: Vec<[f32;32]> = Vec::new();
    let mut all_y: Vec<i32> = Vec::new();
    let mut all_r: Vec<f32> = Vec::new();

    for game_idx in 0..games {
        println!("--- Game {}/{} starting ---", game_idx+1, games);
        let mut rng = StdRng::seed_from_u64(seed + game_idx as u64);
        let a = rng.gen_range(0..deck_cache.len());
        let b = rng.gen_range(0..deck_cache.len());
        let deck_a = &deck_cache[a];
        let deck_b = &deck_cache[b];
        println!("  decks: {} vs {}", a, b);

        // Build plans
        let plan_a = Plan::build(deck_a, &heur_index);
        let plan_b = Plan::build(deck_b, &heur_index);
        println!("  plans built");

        // Battle start
        println!("  battle_start...");
        let mut obs = match engine.battle_start(deck_a, deck_b) {
            Ok(o) => {
                println!("  battle_start OK");
                o
            },
            Err(e) => {
                eprintln!("  battle_start failed: {}", e);
                continue;
            }
        };

        let mut recs: [Vec<([f64; 96], Vec<[f64;64]>, i32)>; 2] = [Vec::new(), Vec::new()];
        let mut result: i32 = -1;
        let mut step = 0;
        loop {
            step+=1;
            if step > 2000 {
                eprintln!("  step limit 2000 at game {}", game_idx);
                break;
            }
            let current = &obs["current"];
            if current.is_null() { 
                eprintln!("  current null at step {}", step);
                break; 
            }
            let res = current["result"].as_i64().unwrap_or(-1);
            if res >= 0 { result = res as i32; break; }
            let select = &obs["select"];
            if select.is_null() { 
                eprintln!("  select null at step {}", step);
                break; 
            }
            let me = obs["current"]["yourIndex"].as_u64().unwrap_or(0) as usize;
            let (plan, _deck) = if me==0 { (&plan_a, deck_a) } else { (&plan_b, deck_b) };
            let decision = heuristic::decide(&obs, &heur_index, plan, &knobs, if me==0 { deck_a } else { deck_b });
            if decision.is_empty() {
                eprintln!("  empty decision at step {}", step);
                break;
            }
            // Featurize
            if let Some(opts_arr) = select["option"].as_array() {
                let s = feat.state_feats(&obs, me);
                let mut ofeats: Vec<[f64;64]> = Vec::new();
                for o in opts_arr.iter().take(policy_feats::MAX_OPT) {
                    ofeats.push(feat.option_feats(o, &obs, me));
                }
                let chosen = decision[0] as i32;
                recs[me].push((s, ofeats, chosen));
            }
            match engine.select(&decision) {
                Ok(next) => obs = next,
                Err(e) => {
                    eprintln!("  select failed at step {}: {}", step, e);
                    break;
                }
            }
        }
        println!("  game {} ended result={} steps={} recs0={} recs1={}", game_idx, result, step, recs[0].len(), recs[1].len());
        if result <0 || result>2 { continue; }
        for seat in 0..2 {
            let win_val = if result==seat as i32 { 1.0 } else if result==2 { 0.0 } else { -1.0 };
            for (s, ofeats, chosen) in recs[seat].iter() {
                let mut o_mat = [[0.0f32; policy_feats::DO]; policy_feats::MAX_OPT];
                let mut mask = [0.0f32; policy_feats::MAX_OPT];
                for (j, of) in ofeats.iter().enumerate() {
                    if j>=policy_feats::MAX_OPT { break; }
                    for k in 0..policy_feats::DO { o_mat[j][k] = of[k] as f32; }
                    mask[j]=1.0;
                }
                let mut s_arr = [0.0f32; policy_feats::DS];
                for k in 0..policy_feats::DS { s_arr[k]=s[k] as f32; }
                all_s.push(s_arr);
                all_o.push(o_mat);
                all_m.push(mask);
                all_y.push(*chosen);
                all_r.push(win_val as f32);
            }
        }
        if (game_idx+1) % 10 == 0 {
            let elapsed = start.elapsed().as_secs_f64();
            println!("Progress {}/{} games, {} decisions, {:.1}s ({:.1} games/s)", game_idx+1, games, all_s.len(), elapsed, (game_idx+1) as f64 / elapsed);
        }
    }

    println!("Total: {} games, {} decisions in {:.1}s", games, all_s.len(), start.elapsed().as_secs_f64());
    if all_s.is_empty() {
        anyhow::bail!("no decisions collected");
    }

    let out_path = PathBuf::from(&args.out);
    if let Some(parent) = out_path.parent() { fs::create_dir_all(parent)?; }

    fn write_npy_f32(path: &Path, shape: &str, flat: Vec<f32>) -> Result<()> {
        use std::io::Write;
        let mut f = fs::File::create(path)?;
        let dict = format!("{{'descr': '<f4', 'fortran_order': False, 'shape': {}, }}", shape);
        let mut header = dict.into_bytes();
        header.push(b'\n');
        let pad = (64 - ((10 + header.len()) % 64)) % 64;
        header.extend(std::iter::repeat(b' ').take(pad));
        f.write_all(b"\x93NUMPY")?;
        f.write_all(&[1,0])?;
        f.write_all(&(header.len() as u16).to_le_bytes())?;
        f.write_all(&header)?;
        for v in flat { f.write_all(&v.to_le_bytes())?; }
        Ok(())
    }
    fn write_npy_i32(path: &Path, shape: &str, flat: &[i32]) -> Result<()> {
        use std::io::Write;
        let mut f = fs::File::create(path)?;
        let dict = format!("{{'descr': '<i4', 'fortran_order': False, 'shape': {}, }}", shape);
        let mut header = dict.into_bytes();
        header.push(b'\n');
        let pad = (64 - ((10 + header.len()) % 64)) % 64;
        header.extend(std::iter::repeat(b' ').take(pad));
        f.write_all(b"\x93NUMPY")?;
        f.write_all(&[1,0])?;
        f.write_all(&(header.len() as u16).to_le_bytes())?;
        f.write_all(&header)?;
        for v in flat { f.write_all(&v.to_le_bytes())?; }
        Ok(())
    }

    let tmp_dir = PathBuf::from("/tmp/bc_rust_npy");
    fs::create_dir_all(&tmp_dir)?;
    let n = all_s.len();
    write_npy_f32(&tmp_dir.join("S.npy"), &format!("({}, 96)", n), all_s.iter().flat_map(|r| r.iter()).cloned().collect())?;
    write_npy_f32(&tmp_dir.join("O.npy"), &format!("({}, 32, 64)", n), all_o.iter().flat_map(|m| m.iter().flat_map(|r| r.iter()).cloned()).collect())?;
    write_npy_f32(&tmp_dir.join("M.npy"), &format!("({}, 32)", n), all_m.iter().flat_map(|r| r.iter()).cloned().collect())?;
    write_npy_i32(&tmp_dir.join("Y.npy"), &format!("({},)", n), &all_y)?;
    write_npy_f32(&tmp_dir.join("R.npy"), &format!("({},)", n), all_r.clone())?;

    let status = std::process::Command::new("python3")
        .arg("-c")
        .arg(format!("import numpy as np, pathlib; d=pathlib.Path('/tmp/bc_rust_npy'); S=np.load(d/'S.npy'); O=np.load(d/'O.npy'); M=np.load(d/'M.npy'); Y=np.load(d/'Y.npy'); R=np.load(d/'R.npy'); np.savez_compressed('{}', S=S, O=O, M=M, Y=Y, R=R); print('saved')", args.out))
        .status()?;
    if !status.success() {
        anyhow::bail!("python save failed");
    }
    println!("Saved {} decisions to {}", n, args.out);
    Ok(())
}
