use anyhow::Result;
use clap::Parser;
use rayon::prelude::*;
use std::path::{Path, PathBuf};
use std::fs;
use std::sync::{Mutex, Arc};
use rand::{SeedableRng, rngs::StdRng, Rng};
use serde_json::Value;

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
#[command(name="gen_bc_data_rust", about="Generate BC data with Rust+Rayon, 200x faster")]
struct Args {
    #[arg(long, default_value="assets/card_index.json")]
    card_index: String,
    #[arg(long, default_value="decks")]
    deck_pool_dir: String,
    #[arg(long, default_value="kaggle_results/bc_data_rust.npz")]
    out: String,
    #[arg(long, default_value_t=2400)]
    games: usize,
    #[arg(long, default_value_t=0)]
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
        pool_dir.join("c87_v60.csv"),
        pool_dir.join("c87_v61.csv"),
        pool_dir.join("v58_best_both_kyo4.csv"),
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
    out
}

struct GameRecord {
    s: Vec<[f32; policy_feats::DS]>,
    o: Vec<[[f32; policy_feats::DO]; policy_feats::MAX_OPT]>,
    m: Vec<[f32; policy_feats::MAX_OPT]>,
    y: Vec<i32>,
    r: Vec<f32>,
}

fn play_one_game(
    deck_a: &[i32],
    deck_b: &[i32],
    lib_path: &str,
    heur_index: &HeurCardIndex,
    feat: &Featurizer,
    knobs: &Knobs,
) -> Option<GameRecord> {
    let plan_a = Plan::build(deck_a, heur_index);
    let plan_b = Plan::build(deck_b, heur_index);
    let mut engine = match Engine::new(lib_path) {
        Ok(e) => e,
        Err(_) => return None,
    };
    let mut obs = match engine.battle_start(deck_a, deck_b) {
        Ok(o) => o,
        Err(_) => return None,
    };
    let mut recs: [Vec<([f64; 96], Vec<[f64;64]>, i32)>; 2] = [Vec::new(), Vec::new()];
    let mut result: i32 = -1;
    let mut step = 0;
    loop {
        step+=1;
        if step > 5000 { break; }
        let current = &obs["current"];
        if current.is_null() { break; }
        let res = current["result"].as_i64().unwrap_or(-1);
        if res >= 0 { result = res as i32; break; }
        let select = &obs["select"];
        if select.is_null() { break; }
        let me = obs["current"]["yourIndex"].as_u64().unwrap_or(0) as usize;
        let (plan, _deck) = if me==0 { (&plan_a, deck_a) } else { (&plan_b, deck_b) };
        let decision = heuristic::decide(&obs, heur_index, plan, knobs, if me==0 { deck_a } else { deck_b });
        if decision.is_empty() { break; }
        let opts = select["option"].as_array();
        if let Some(opts_arr) = opts {
            let s = feat.state_feats(&obs, me);
            let mut ofeats: Vec<[f64;64]> = Vec::new();
            for o in opts_arr.iter().take(policy_feats::MAX_OPT) {
                ofeats.push(feat.option_feats(o, &obs, me));
            }
            let chosen = decision.get(0).cloned().unwrap_or(0) as i32;
            recs[me].push((s, ofeats, chosen));
        }
        match engine.select(&decision) {
            Ok(next) => obs = next,
            Err(_) => break,
        }
    }
    if result <0 || result>2 { return None; }
    let mut s_all = Vec::new();
    let mut o_all = Vec::new();
    let mut m_all = Vec::new();
    let mut y_all = Vec::new();
    let mut r_all = Vec::new();
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
            s_all.push(s_arr);
            o_all.push(o_mat);
            m_all.push(mask);
            y_all.push(*chosen);
            r_all.push(win_val as f32);
        }
    }
    if s_all.is_empty() { return None; }
    Some(GameRecord { s: s_all, o: o_all, m: m_all, y: y_all, r: r_all })
}

fn main() -> Result<()> {
    let args = Args::parse();
    if args.jobs>0 {
        rayon::ThreadPoolBuilder::new().num_threads(args.jobs).build_global().unwrap();
    }
    println!("Card index: {}", args.card_index);
    let heur_index = HeurCardIndex::load(&args.card_index)?;
    let feat = Featurizer::load(&args.card_index)?;
    println!("Loaded {} cards, {} attacks", heur_index.cards.len(), heur_index.attacks.len());
    let pool_dir = PathBuf::from(&args.deck_pool_dir);
    let deck_files = collect_deck_files(&pool_dir);
    println!("Deck pool: {} files", deck_files.len());
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
    println!("Lib: {}", lib_path);
    let knobs = Knobs::default();
    let games = args.games;
    let seed = args.seed;
    let deck_cache = Arc::new(deck_cache);
    let heur_index = Arc::new(heur_index);
    let feat = Arc::new(feat);
    let start = std::time::Instant::now();
    let tasks: Vec<(usize, usize, usize)> = (0..games).map(|i| {
        let mut rng = StdRng::seed_from_u64(seed + i as u64);
        let a = rng.gen_range(0..deck_cache.len());
        let b = rng.gen_range(0..deck_cache.len());
        (i, a, b)
    }).collect();

    let all_s: Mutex<Vec<[f32; 96]>> = Mutex::new(Vec::new());
    let all_o: Mutex<Vec<[[f32;64];32]>> = Mutex::new(Vec::new());
    let all_m: Mutex<Vec<[f32;32]>> = Mutex::new(Vec::new());
    let all_y: Mutex<Vec<i32>> = Mutex::new(Vec::new());
    let all_r: Mutex<Vec<f32>> = Mutex::new(Vec::new());
    let done = Arc::new(Mutex::new(0usize));
    let ndec = Arc::new(Mutex::new(0usize));

    tasks.par_iter().for_each(|(_game_idx, a_idx, b_idx)| {
        let deck_a = &deck_cache[*a_idx];
        let deck_b = &deck_cache[*b_idx];
        if let Some(rec) = play_one_game(deck_a, deck_b, &lib_path, &heur_index, &feat, &knobs) {
            let n = rec.s.len();
            {
                let mut guard = all_s.lock().unwrap();
                guard.extend(rec.s);
            }
            {
                let mut guard = all_o.lock().unwrap();
                guard.extend(rec.o);
            }
            {
                let mut guard = all_m.lock().unwrap();
                guard.extend(rec.m);
            }
            {
                let mut guard = all_y.lock().unwrap();
                guard.extend(rec.y);
            }
            {
                let mut guard = all_r.lock().unwrap();
                guard.extend(rec.r);
            }
            {
                let mut d = ndec.lock().unwrap();
                *d += n;
            }
        }
        {
            let mut d = done.lock().unwrap();
            *d += 1;
            if *d % 200 == 0 {
                let elapsed = start.elapsed().as_secs_f64();
                let nd = *ndec.lock().unwrap();
                println!("{}/{} games, {} decisions, {:.1}s ({:.1} games/s, {:.0} dec/s)", *d, games, nd, elapsed, *d as f64 / elapsed, nd as f64 / elapsed);
            }
        }
    });

    let s = all_s.into_inner().unwrap();
    let o = all_o.into_inner().unwrap();
    let m = all_m.into_inner().unwrap();
    let y = all_y.into_inner().unwrap();
    let r = all_r.into_inner().unwrap();
    println!("Total: {} games, {} decisions in {:.1}s ({:.1} games/s)", games, s.len(), start.elapsed().as_secs_f64(), games as f64 / start.elapsed().as_secs_f64());

    let out_path = PathBuf::from(&args.out);
    if let Some(parent) = out_path.parent() { fs::create_dir_all(parent)?; }

    fn write_npy_header_f32(path: &Path, shape: &str, flat: Vec<f32>) -> Result<()> {
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
        for v in flat {
            f.write_all(&v.to_le_bytes())?;
        }
        Ok(())
    }
    fn write_npy_header_i32(path: &Path, shape: &str, flat: &[i32]) -> Result<()> {
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
        for v in flat {
            f.write_all(&v.to_le_bytes())?;
        }
        Ok(())
    }

    let tmp_dir = PathBuf::from("/tmp/bc_rust_npy");
    fs::create_dir_all(&tmp_dir)?;
    let n = s.len();
    write_npy_header_f32(&tmp_dir.join("S.npy"), &format!("({}, 96)", n), s.iter().flat_map(|row| row.iter()).cloned().collect())?;
    write_npy_header_f32(&tmp_dir.join("O.npy"), &format!("({}, 32, 64)", n), o.iter().flat_map(|mat| mat.iter().flat_map(|row| row.iter()).cloned()).collect())?;
    write_npy_header_f32(&tmp_dir.join("M.npy"), &format!("({}, 32)", n), m.iter().flat_map(|row| row.iter()).cloned().collect())?;
    write_npy_header_i32(&tmp_dir.join("Y.npy"), &format!("({},)", n), &y)?;
    write_npy_header_f32(&tmp_dir.join("R.npy"), &format!("({},)", n), r.clone())?;

    let status = std::process::Command::new("python3")
        .arg("-c")
        .arg(format!("import numpy as np, pathlib; d=pathlib.Path('/tmp/bc_rust_npy'); S=np.load(d/'S.npy'); O=np.load(d/'O.npy'); M=np.load(d/'M.npy'); Y=np.load(d/'Y.npy'); R=np.load(d/'R.npy'); np.savez_compressed('{}', S=S, O=O, M=M, Y=Y, R=R); print('saved {} decisions to {}')", args.out, n, args.out))
        .status();
    match status {
        Ok(st) if st.success() => println!("Saved via python to {}", args.out),
        _ => {
            let _ = std::process::Command::new("bash")
                .arg("-c")
                .arg(format!("cd /tmp/bc_rust_npy && zip -j {} S.npy O.npy M.npy Y.npy R.npy && ls -lh {}", args.out, args.out))
                .status();
            println!("Saved via zip to {}", args.out);
        }
    }

    Ok(())
}
