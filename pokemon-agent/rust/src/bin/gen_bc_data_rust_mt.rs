use anyhow::Result;
use clap::Parser;
use std::path::{Path, PathBuf};
use std::fs;
use rand::{SeedableRng, rngs::StdRng, Rng};
use std::cell::RefCell;
use std::sync::{Arc, Mutex};
use rayon::prelude::*;

#[path = "../engine_mt.rs"]
mod engine_mt;
#[path = "../heuristic.rs"]
mod heuristic;
#[path = "../policy_feats.rs"]
mod policy_feats;

use engine_mt::EngineMT;
use heuristic::{CardIndex as HeurCardIndex, Knobs, Plan};
use policy_feats::Featurizer;

// Platform default for the cabt engine library. Windows ships cg.dll in the
// kaggle-environments wheel; place it next to the .exe or pass --lib.
const DEFAULT_LIB: &str = if cfg!(target_os = "windows") {
    "cg.dll"
} else if cfg!(target_os = "macos") {
    ".venv/lib/python3.11/site-packages/kaggle_environments/envs/cabt/cg/libcg.dylib"
} else {
    ".venv/lib/python3.11/site-packages/kaggle_environments/envs/cabt/cg/libcg.so"
};

#[derive(Parser, Debug)]
struct Args {
    #[arg(long, default_value="assets/card_index.json")]
    card_index: String,
    #[arg(long, default_value="decks")]
    deck_pool_dir: String,
    #[arg(long, default_value="kaggle_results/bc_data_rust.npz")]
    out: String,
    #[arg(long, default_value_t=200)]
    games: usize,
    #[arg(long, default_value_t=4)]
    jobs: usize,
    #[arg(long, default_value = DEFAULT_LIB)]
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
    for sub in ["top50_fresh22", "top50_fresh_all", "live_killers", "broad_field", "top30_live"] {
        let d = pool_dir.join(sub);
        if d.is_dir() {
            if let Ok(entries) = fs::read_dir(&d) {
                for e in entries.flatten() {
                    let path = e.path();
                    if path.extension().and_then(|s| s.to_str()) == Some("csv") {
                        out.push(path);
                    }
                }
            }
        }
    }
    if let Ok(entries) = fs::read_dir(pool_dir) {
        for e in entries.flatten() {
            let path = e.path();
            if path.extension().and_then(|s| s.to_str()) == Some("csv") {
                if !out.contains(&path) { out.push(path); }
            }
        }
    }
    out.sort();
    out.dedup();
    out
}

thread_local! {
    static THREAD_ENGINE: RefCell<Option<EngineMT>> = RefCell::new(None);
}

fn with_thread_engine<F, R>(lib_path: &str, f: F) -> R
where
    F: FnOnce(&mut EngineMT) -> R,
{
    THREAD_ENGINE.with(|cell| {
        let mut opt = cell.borrow_mut();
        if opt.is_none() {
            let eng = EngineMT::new(lib_path).expect("failed to create EngineMT");
            *opt = Some(eng);
        }
        f(opt.as_mut().unwrap())
    })
}

fn main() -> Result<()> {
    let args = Args::parse();
    println!("=== gen_bc_data_rust_mt starting (Rayon) ===");
    println!("Args: {:?}", args);
    let heur_index = Arc::new(HeurCardIndex::load(&args.card_index)?);
    let feat = Arc::new(Featurizer::load(&args.card_index)?);
    println!("Loaded {} cards", heur_index.cards.len());
    let pool_dir = PathBuf::from(&args.deck_pool_dir);
    let deck_files = collect_deck_files(&pool_dir);
    println!("Deck pool: {} files", deck_files.len());
    let mut deck_cache: Vec<Vec<i32>> = Vec::new();
    for p in &deck_files {
        if let Ok(d) = load_deck_ids(p) {
            deck_cache.push(d);
        }
    }
    println!("Loaded {} valid decks", deck_cache.len());
    if deck_cache.is_empty() { anyhow::bail!("no valid decks"); }
    let deck_cache = Arc::new(deck_cache);

    let lib_path = if Path::new(&args.lib_path).exists() { args.lib_path.clone() } else {
        let alts = [
            "cg.dll",
            "Lib/site-packages/kaggle_environments/envs/cabt/cg/cg.dll",
            ".venv/lib/python3.11/site-packages/kaggle_environments/envs/cabt/cg/libcg.so",
            "/home/runner/work/Pokemon/Pokemon/pokemon-agent/.venv/lib/python3.11/site-packages/kaggle_environments/envs/cabt/cg/libcg.so",
            "/usr/local/lib/python3.11/dist-packages/kaggle_environments/envs/cabt/cg/libcg.so",
        ];
        let mut found = args.lib_path.clone();
        for alt in alts { if Path::new(alt).exists() { found = alt.to_string(); break; } }
        found
    };
    println!("Lib path: {}", lib_path);
    let lib_path_arc = Arc::new(lib_path);

    let knobs = Arc::new(Knobs::default());
    let games = args.games;
    let seed = args.seed;
    let start = std::time::Instant::now();

    // Prepare tasks: game indices
    let tasks: Vec<usize> = (0..games).collect();

    // Use rayon threadpool with specified jobs
    let pool = rayon::ThreadPoolBuilder::new().num_threads(args.jobs).build()?;
    let results = Arc::new(Mutex::new(Vec::new()));
    let failed = Arc::new(Mutex::new(0usize));

    pool.install(|| {
        tasks.par_iter().for_each(|&game_idx| {
            let deck_cache = Arc::clone(&deck_cache);
            let heur_index = Arc::clone(&heur_index);
            let feat = Arc::clone(&feat);
            let knobs = Arc::clone(&knobs);
            let lib_path = Arc::clone(&lib_path_arc);
            let results = Arc::clone(&results);
            let failed = Arc::clone(&failed);

            let mut rng = StdRng::seed_from_u64(seed + game_idx as u64);
            let a = rng.gen_range(0..deck_cache.len());
            let b = rng.gen_range(0..deck_cache.len());
            let deck_a = &deck_cache[a];
            let deck_b = &deck_cache[b];

            let plan_a = Plan::build(deck_a, &heur_index);
            let plan_b = Plan::build(deck_b, &heur_index);

            let game_result = with_thread_engine(&lib_path, |engine| {
                let mut obs = match engine.battle_start(deck_a, deck_b) {
                    Ok(o) => o,
                    Err(_) => return None,
                };
                let mut recs: [Vec<([f64; 96], Vec<[f64;64]>, i32)>; 2] = [Vec::new(), Vec::new()];
                let mut result: i32 = -1;
                let mut step = 0;
                loop {
                    step+=1;
                    if step > 3000 { break; }
                    let current = &obs["current"];
                    if current.is_null() { break; }
                    let res = current["result"].as_i64().unwrap_or(-1);
                    if res >= 0 { result = res as i32; break; }
                    let select = &obs["select"];
                    if select.is_null() { break; }
                    let me = obs["current"]["yourIndex"].as_u64().unwrap_or(0) as usize;
                    let (plan, _deck) = if me==0 { (&plan_a, deck_a) } else { (&plan_b, deck_b) };
                    let decision = heuristic::decide(&obs, &heur_index, plan, &knobs, if me==0 { deck_a } else { deck_b });
                    if decision.is_empty() { break; }
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
                        Err(_) => break,
                    }
                }
                if result <0 || result>2 { return None; }
                let mut out = Vec::new();
                for seat in 0..2 {
                    let win_val = if result==seat as i32 { 1.0 } else if result==2 { 0.0 } else { -1.0 };
                    for (s, ofeats, chosen) in recs[seat].iter() {
                        out.push((s.clone(), ofeats.clone(), *chosen, win_val));
                    }
                }
                Some(out)
            });

            if let Some(recs) = game_result {
                let mut r = results.lock().unwrap();
                r.extend(recs);
            } else {
                let mut f = failed.lock().unwrap();
                *f += 1;
            }
            if game_idx % 100 == 0 {
                println!("Game {} done", game_idx);
            }
        });
    });

    let elapsed = start.elapsed().as_secs_f64();
    let all_recs = results.lock().unwrap();
    let failed_count = *failed.lock().unwrap();
    println!("Total: {} games attempted, {} failed, {} decisions in {:.1}s ({:.1} games/s)", games, failed_count, all_recs.len(), elapsed, games as f64 / elapsed);

    if all_recs.is_empty() {
        anyhow::bail!("no decisions");
    }

    // Convert to arrays
    let mut all_s: Vec<[f32; 96]> = Vec::new();
    let mut all_o: Vec<[[f32;64];32]> = Vec::new();
    let mut all_m: Vec<[f32;32]> = Vec::new();
    let mut all_y: Vec<i32> = Vec::new();
    let mut all_r: Vec<f32> = Vec::new();

    for (s, ofeats, chosen, win_val) in all_recs.iter() {
        let mut o_mat = [[0.0f32; 64]; 32];
        let mut mask = [0.0f32; 32];
        for (j, of) in ofeats.iter().enumerate() {
            if j>=32 { break; }
            for k in 0..64 { o_mat[j][k] = of[k] as f32; }
            mask[j]=1.0;
        }
        let mut s_arr = [0.0f32; 96];
        for k in 0..96 { s_arr[k]=s[k] as f32; }
        all_s.push(s_arr);
        all_o.push(o_mat);
        all_m.push(mask);
        all_y.push(*chosen);
        all_r.push(*win_val as f32);
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

    let py_candidates = [
        ".venv/bin/python",
        "/home/runner/work/Pokemon/Pokemon/pokemon-agent/.venv/bin/python",
        "/usr/local/bin/python",
        "python3",
    ];
    let mut saved = false;
    for py in &py_candidates {
        println!("Trying python {} to save npz", py);
        let out = args.out.clone();
        let cmd = format!("import numpy as np, pathlib; d=pathlib.Path('/tmp/bc_rust_npy'); S=np.load(d/'S.npy'); O=np.load(d/'O.npy'); M=np.load(d/'M.npy'); Y=np.load(d/'Y.npy'); R=np.load(d/'R.npy'); np.savez_compressed('{}', S=S, O=O, M=M, Y=Y, R=R); print('saved')", out);
        let status = std::process::Command::new(py).arg("-c").arg(&cmd).status();
        match status {
            Ok(s) if s.success() => { println!("Saved via {} to {}", py, args.out); saved = true; break; },
            Ok(s) => eprintln!("python {} failed {:?}", py, s),
            Err(e) => eprintln!("python {} error {}", py, e),
        }
    }
    if !saved {
        anyhow::bail!("failed to save npz");
    }
    println!("Done {} decisions", n);
    Ok(())
}
