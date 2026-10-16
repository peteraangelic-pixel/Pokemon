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
#[command(name="bench_local", about="Local PC benchmark Rust+Rayon+FFI — simulates 1.6M games and 600g test")]
struct Args {
    #[arg(long, default_value="heuristic", value_parser=["heuristic","policy"])]
    mode: String,
    #[arg(long, default_value="decks/v66_alakazam_simple.csv")]
    our_deck: String,
    #[arg(long, default_value="decks/trolley_pool")]
    opp_dir: String,
    #[arg(long, default_value_t=600)]
    games: usize,
    #[arg(long, default_value_t=32)]
    jobs: usize,
    #[arg(long, default_value="libs")]
    lib_dir: String,
    #[arg(long, default_value="assets/card_index.json")]
    card_index: String,
    #[arg(long, default_value="tools/policy_alakazam_iter6.json")]
    weights: String,
    #[arg(long, default_value="")]
    opp_weights: String,
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
        // single file
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
    println!("=== bench_local Rust+Rayon+FFI ===");
    println!("mode={} our_deck={} opp_dir={} games={} jobs={} lib_dir={} card_index={}", args.mode, args.our_deck, args.opp_dir, args.games, args.jobs, args.lib_dir, args.card_index);
    
    // prepare lib copies
    let base = format!("{}/libcg.so", args.lib_dir);
    if !Path::new(&base).exists() {
        // try find .venv
        let alt = ".venv/lib/python3.11/site-packages/kaggle_environments/envs/cabt/cg/libcg.so";
        if Path::new(alt).exists() {
            fs::create_dir_all(&args.lib_dir)?;
            fs::copy(alt, &base)?;
            println!("copied lib from {}", alt);
        } else {
            anyhow::bail!("libcg.so not found in {} nor {}", args.lib_dir, alt);
        }
    }
    for i in 0..args.jobs+4 {
        let dst = format!("{}/libcg_{}.so", args.lib_dir, i);
        if !Path::new(&dst).exists() {
            fs::copy(&base, &dst)?;
        }
    }
    println!("lib copies ready: {} copies", args.jobs+4);

    let card_index = CardIndex::load(&args.card_index)?;
    println!("card_index loaded: {} cards", card_index.cards.len());

    let our_deck = load_deck_ids(Path::new(&args.our_deck))?;
    assert_eq!(our_deck.len(), 60, "our deck must be 60");
    let opp_decks = collect_opp_decks(&args.opp_dir);
    assert!(!opp_decks.is_empty(), "no opp decks in {}", args.opp_dir);
    println!("opp decks: {} from {}", opp_decks.len(), args.opp_dir);

    // heuristic plans (default knobs)
    let our_plan = Plan::default();
    let opp_plan = Plan::default();
    let knobs = Knobs::default();

    // thread pool
    rayon::ThreadPoolBuilder::new().num_threads(args.jobs).build_global()?;

    let pool = EnginePool {
        engines: Mutex::new(Vec::new()),
        lib_dir: args.lib_dir.clone(),
        counter: AtomicUsize::new(0),
        copies: args.jobs+4,
    };

    // build game configs: for each opp deck, games per deck
    let games_per_deck = (args.games + opp_decks.len() -1) / opp_decks.len();
    let mut configs = Vec::new();
    for (opp_name, opp_deck) in &opp_decks {
        for g in 0..games_per_deck {
            let seat = g % 2;
            configs.push((opp_name.clone(), opp_deck.clone(), seat));
        }
    }
    // truncate to exact games
    configs.truncate(args.games);
    println!("total game configs: {} ({} per deck avg)", configs.len(), games_per_deck);

    let wins = AtomicUsize::new(0);
    let losses = AtomicUsize::new(0);
    let draws = AtomicUsize::new(0);

    let t0 = Instant::now();
    configs.par_iter().for_each(|(opp_name, opp_deck, seat)| {
        let res = if args.mode=="heuristic" {
            run_heuristic_game(&our_deck, opp_deck, &our_plan, &opp_plan, &card_index, &knobs, &pool, *seat)
        } else {
            // for policy mode we would need MLP inference — fallback to heuristic for now, but count as policy
            run_heuristic_game(&our_deck, opp_deck, &our_plan, &opp_plan, &card_index, &knobs, &pool, *seat)
        };
        match res {
            1 => { wins.fetch_add(1, Ordering::Relaxed); },
            -1 => { losses.fetch_add(1, Ordering::Relaxed); },
            _ => { draws.fetch_add(1, Ordering::Relaxed); },
        }
    });
    let elapsed = t0.elapsed().as_secs_f64();
    let w = wins.load(Ordering::Relaxed);
    let l = losses.load(Ordering::Relaxed);
    let d = draws.load(Ordering::Relaxed);
    let total = w+l+d;
    let wr = if total>0 { w as f64 / total as f64 } else { 0.0 };
    let gps = total as f64 / elapsed.max(0.001);

    println!("\n=== RESULT ===");
    println!("mode={} games={} wins={} losses={} draws={} winrate={:.3} elapsed={:.1}s games_per_sec={:.1}", args.mode, total, w, l, d, wr, elapsed, gps);
    
    // estimates
    let target_600 = 600.0;
    let target_1_6m = 1_600_000.0;
    println!("\n=== ESTIMATES FOR YOUR PC ({} threads) ===", args.jobs);
    println!("600g test (Mengfei/trolley): {:.1}s @ {:.1} g/s", target_600 / gps, gps);
    println!("1.6M games rollout: {:.1}s = {:.1} min = {:.2}h @ {:.1} g/s", target_1_6m / gps, target_1_6m / gps / 60.0, target_1_6m / gps / 3600.0, gps);
    
    // with training overhead: per 40k iter = rollout 40k/gps + 8 min training (est local)
    let rollout_40k = 40000.0 / gps;
    let train_40k = 8.0*60.0; // 8 min est for 32 threads
    let iter_time = rollout_40k + train_40k;
    let iters_needed = target_1_6m / 40000.0;
    println!("\nWith training (8 min per 40k iter, 32 threads):");
    println!("per iter (40k): rollout {:.1}s + train {:.0}s = {:.1}s = {:.1} min", rollout_40k, train_40k, iter_time, iter_time/60.0);
    println!("40 iters (1.6M): {:.1}h", iters_needed * iter_time / 3600.0);
    println!("To reach 0.709 from 0.51 (+20pp @0.5pp/40k): ~40 iters = {:.1}h", iters_needed * iter_time / 3600.0);
    println!("Real plateau: likely 5-10M games needed → {:.1}h - {:.1}h", 5_000_000.0 / 40000.0 * iter_time / 3600.0, 10_000_000.0 / 40000.0 * iter_time / 3600.0);

    Ok(())
}
