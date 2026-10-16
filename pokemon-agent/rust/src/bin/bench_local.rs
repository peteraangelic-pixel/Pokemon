use anyhow::Result;
use clap::Parser;
use rayon::prelude::*;
use std::path::{Path, PathBuf};
use std::sync::{Mutex, atomic::{AtomicUsize, Ordering}};
use std::time::Instant;
use std::fs;

#[path = "../engine.rs"]
mod engine;
#[path = "../heuristic.rs"]
mod heuristic;

use engine::Engine;
use heuristic::{CardIndex, Knobs, Plan};

#[derive(Parser, Debug)]
#[command(name="bench_local", about="Local PC benchmark Rust+Rayon+FFI — min 60s to warm CPU, then estimates 1.6M")]
struct Args {
    #[arg(long, default_value="heuristic", value_parser=["heuristic","policy"])]
    mode: String,
    #[arg(long, default_value="decks/v66_alakazam_simple.csv")]
    our_deck: String,
    #[arg(long, default_value="decks/trolley_pool")]
    opp_dir: String,
    #[arg(long, default_value_t=0)]
    games: usize,
    #[arg(long, default_value_t=60)]
    min_seconds: u64,
    #[arg(long, default_value_t=32)]
    jobs: usize,
    #[arg(long, default_value="libs")]
    lib_dir: String,
    #[arg(long, default_value="assets/card_index.json")]
    card_index: String,
    #[arg(long, default_value="tools/policy_alakazam_iter6.json")]
    weights: String,
}

fn load_deck_ids(path: &Path) -> Result<Vec<i32>> {
    let content = fs::read_to_string(path)?;
    let mut ids = Vec::new();
    for token in content.split(|c: char| c==',' || c.is_whitespace()) {
        if token.trim().is_empty() { continue; }
        if let Ok(id) = token.trim().parse::<i32>() { ids.push(id); }
    }
    Ok(ids)
}

fn collect_opp_decks(dir: &str) -> Vec<(String, Vec<i32>)> {
    let mut out = Vec::new();
    let p = PathBuf::from(dir);
    if p.is_dir() {
        if let Ok(entries) = fs::read_dir(&p) {
            for e in entries.filter_map(|e| e.ok()) {
                let path = e.path();
                if path.extension().map(|e| e=="csv").unwrap_or(false) {
                    if let Ok(deck) = load_deck_ids(&path) {
                        if deck.len()==60 {
                            out.push((path.file_name().unwrap().to_string_lossy().to_string(), deck));
                        }
                    }
                }
            }
        }
    } else {
        if let Ok(deck) = load_deck_ids(&PathBuf::from(dir)) {
            if deck.len()==60 {
                out.push((dir.to_string(), deck));
            }
        }
    }
    out.sort_by(|a,b| a.0.cmp(&b.0));
    out
}

struct EnginePool {
    engines: Mutex<Vec<Engine>>,
    lib_dir: String,
    counter: AtomicUsize,
    copies: usize,
}

impl EnginePool {
    fn get(&self) -> Engine {
        if let Some(eng) = self.engines.lock().unwrap().pop() {
            return eng;
        }
        let idx = self.counter.fetch_add(1, Ordering::Relaxed) % self.copies;
        let lib_path = format!("{}/libcg_{}.so", self.lib_dir, idx);
        // Windows fallback: try .dll if .so not exists
        let lib_path = if Path::new(&lib_path).exists() {
            lib_path
        } else {
            let dll_path = format!("{}/libcg_{}.dll", self.lib_dir, idx);
            if Path::new(&dll_path).exists() { dll_path } else { lib_path }
        };
        Engine::new(&lib_path).expect("engine new")
    }
    fn put(&self, eng: Engine) {
        self.engines.lock().unwrap().push(eng);
    }
}

fn run_heuristic_game(our_deck: &[i32], opp_deck: &[i32], our_plan: &Plan, opp_plan: &Plan, card_index: &CardIndex, knobs: &Knobs, pool: &EnginePool, our_seat: usize) -> i32 {
    let mut eng = pool.get();
    let result = (|| -> Result<i32> {
        let (d0,d1) = if our_seat==0 { (our_deck, opp_deck) } else { (opp_deck, our_deck) };
        let mut obs = eng.battle_start(d0, d1)?;
        let mut step=0;
        loop {
            step+=1;
            if step>4000 { break; }
            let cur = &obs["current"];
            if cur.is_null() { break; }
            let res = cur["result"].as_i64().unwrap_or(-1);
            if res>=0 {
                if res==2 { return Ok(0); }
                let our_win = if our_seat==0 { res==0 } else { res==1 };
                return Ok(if our_win {1} else {-1});
            }
            let me_idx = obs["current"]["yourIndex"].as_u64().unwrap_or(0) as usize;
            let (plan, deck) = if me_idx==our_seat { (our_plan, our_deck) } else { (opp_plan, opp_deck) };
            let decision = heuristic::decide(&obs, card_index, plan, knobs, deck);
            let sel = &obs["select"];
            if sel.is_null() { break; }
            let maxc = sel["maxCount"].as_u64().unwrap_or(1) as usize;
            let opt_len = sel["option"].as_array().map(|a| a.len()).unwrap_or(0);
            let exec = if decision.len()>maxc || decision.len()>opt_len {
                (0..maxc.min(opt_len)).map(|i| i as i32).collect::<Vec<_>>()
            } else { decision };
            obs = eng.select(&exec)?;
        }
        Ok(0)
    })();
    pool.put(eng);
    result.unwrap_or(0)
}

fn main() -> Result<()> {
    let args = Args::parse();
    println!("=== bench_local Rust+Rayon+FFI — min {}s to warm CPU ===", args.min_seconds);
    println!("mode={} our_deck={} opp_dir={} games={} min_seconds={} jobs={} lib_dir={}", args.mode, args.our_deck, args.opp_dir, args.games, args.min_seconds, args.jobs, args.lib_dir);
    
    // prepare lib copies
    let base_so = format!("{}/libcg.so", args.lib_dir);
    let base_dll = format!("{}/libcg.dll", args.lib_dir);
    let base = if Path::new(&base_so).exists() { base_so.clone() } else if Path::new(&base_dll).exists() { base_dll.clone() } else { base_so.clone() };
    if !Path::new(&base).exists() {
        let alt = ".venv/lib/python3.11/site-packages/kaggle_environments/envs/cabt/cg/libcg.so";
        let alt_win = ".venv/Lib/site-packages/kaggle_environments/envs/cabt/cg/libcg.dll";
        if Path::new(alt).exists() {
            fs::create_dir_all(&args.lib_dir)?;
            fs::copy(alt, &base)?;
            println!("copied lib from {}", alt);
        } else if Path::new(alt_win).exists() {
            fs::create_dir_all(&args.lib_dir)?;
            fs::copy(alt_win, &base)?;
            println!("copied lib from {}", alt_win);
        } else {
            anyhow::bail!("libcg not found in {} nor {} nor {}", args.lib_dir, alt, alt_win);
        }
    }
    for i in 0..args.jobs+4 {
        let dst_so = format!("{}/libcg_{}.so", args.lib_dir, i);
        let dst_dll = format!("{}/libcg_{}.dll", args.lib_dir, i);
        // copy both extensions if base is so, also create dll copy for Windows
        if base.ends_with(".so") {
            if !Path::new(&dst_so).exists() { fs::copy(&base, &dst_so)?; }
            if !Path::new(&dst_dll).exists() { let _ = fs::copy(&base, &dst_dll); }
        } else {
            if !Path::new(&dst_dll).exists() { fs::copy(&base, &dst_dll)?; }
            if !Path::new(&dst_so).exists() { let _ = fs::copy(&base, &dst_so); }
        }
    }
    println!("lib copies ready: {} copies", args.jobs+4);

    let card_index = CardIndex::load(&args.card_index)?;
    println!("card_index: {} cards", card_index.cards.len());

    let our_deck = load_deck_ids(Path::new(&args.our_deck))?;
    assert_eq!(our_deck.len(), 60);
    let opp_decks = collect_opp_decks(&args.opp_dir);
    assert!(!opp_decks.is_empty(), "no opp decks");
    println!("opp decks: {} from {}", opp_decks.len(), args.opp_dir);

    let our_plan = Plan::default();
    let opp_plan = Plan::default();
    let knobs = Knobs::default();

    rayon::ThreadPoolBuilder::new().num_threads(args.jobs).build_global()?;

    let pool = EnginePool {
        engines: Mutex::new(Vec::new()),
        lib_dir: args.lib_dir.clone(),
        counter: AtomicUsize::new(0),
        copies: args.jobs+4,
    };

    // determine games needed for min_seconds: if games==0, run until min_seconds
    let target_games = if args.games==0 {
        // estimate: 400 g/s * 60s = 24000
        (400 * args.min_seconds as usize).max(600)
    } else {
        args.games
    };

    let wins = AtomicUsize::new(0);
    let losses = AtomicUsize::new(0);
    let draws = AtomicUsize::new(0);
    let total_done = AtomicUsize::new(0);

    let t0 = Instant::now();
    let mut batch = 0;
    loop {
        batch+=1;
        let games_this_batch = target_games;
        let mut configs = Vec::with_capacity(games_this_batch);
        for i in 0..games_this_batch {
            let (opp_name, opp_deck) = &opp_decks[i % opp_decks.len()];
            let seat = i % 2;
            configs.push((opp_name.clone(), opp_deck.clone(), seat));
        }

        configs.par_iter().for_each(|(opp_name, opp_deck, seat)| {
            let res = run_heuristic_game(&our_deck, opp_deck, &our_plan, &opp_plan, &card_index, &knobs, &pool, *seat);
            match res {
                1 => { wins.fetch_add(1, Ordering::Relaxed); },
                -1 => { losses.fetch_add(1, Ordering::Relaxed); },
                _ => { draws.fetch_add(1, Ordering::Relaxed); },
            }
            total_done.fetch_add(1, Ordering::Relaxed);
        });

        let elapsed = t0.elapsed().as_secs_f64();
        let total = total_done.load(Ordering::Relaxed);
        let gps = total as f64 / elapsed.max(0.001);
        println!("[batch {}] {}/{} games, {:.1}s elapsed, {:.1} g/s", batch, total, target_games, elapsed, gps);

        if elapsed >= args.min_seconds as f64 {
            break;
        }
        if args.games!=0 && total>=args.games {
            // if user specified games and we already reached min_seconds, break
            if elapsed >= args.min_seconds as f64 { break; }
            // else continue looping to reach min_seconds
        }
        if args.games==0 && elapsed >= args.min_seconds as f64 {
            break;
        }
    }

    let elapsed = t0.elapsed().as_secs_f64();
    let w = wins.load(Ordering::Relaxed);
    let l = losses.load(Ordering::Relaxed);
    let d = draws.load(Ordering::Relaxed);
    let total = w+l+d;
    let wr = if total>0 { w as f64 / total as f64 } else { 0.0 };
    let gps = total as f64 / elapsed.max(0.001);

    println!("\n=== RESULT (CPU warmed) ===");
    println!("mode={} games={} wins={} losses={} draws={} winrate={:.3} elapsed={:.1}s games_per_sec={:.1}", args.mode, total, w, l, d, wr, elapsed, gps);
    
    println!("\n=== ESTIMATES FOR YOUR PC ({} threads, warmed) ===", args.jobs);
    println!("600g test: {:.1}s @ {:.1} g/s", 600.0 / gps, gps);
    println!("40k rollout: {:.1}s = {:.1} min", 40000.0 / gps, 40000.0 / gps / 60.0);
    println!("1.6M rollout: {:.1}s = {:.1} min = {:.2}h", 1600000.0 / gps, 1600000.0 / gps / 60.0, 1600000.0 / gps / 3600.0);
    let train_40k = 8.0*60.0;
    let iter_time = 40000.0 / gps + train_40k;
    println!("40 iters (1.6M) + trening 8min/iter: {:.1}h", 40.0 * iter_time / 3600.0);
    println!("Do 0.709 (+20pp @0.5pp/40k): ~40 iters = {:.1}h, realnie 5-10M = {:.1}h-{:.1}h", 40.0 * iter_time / 3600.0, 125.0 * iter_time / 3600.0, 250.0 * iter_time / 3600.0);

    Ok(())
}
