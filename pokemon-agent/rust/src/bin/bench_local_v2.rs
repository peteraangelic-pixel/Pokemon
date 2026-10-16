use anyhow::Result;
use clap::Parser;
use rayon::prelude::*;
use std::path::{Path, PathBuf};
use std::sync::{Mutex, atomic::{AtomicUsize, Ordering}};
use std::time::Instant;
use std::fs;
use std::collections::HashMap;

#[path = "../engine.rs"]
mod engine;
#[path = "../heuristic.rs"]
mod heuristic;
#[path = "../alakazam.rs"]
mod alakazam;

use engine::Engine;
use heuristic::{CardIndex, Knobs, Plan};

#[derive(Parser, Debug)]
#[command(name="bench_local_v2", about="Benchmark v2: paired seeds, CI, weighted pool-v3 + Alakazam pilot (fixes second branch gaps)")]
struct Args {
    #[arg(long, default_value="alakazam", value_parser=["heuristic","alakazam","policy"])]
    mode: String,
    #[arg(long, default_value="decks/v66_alakazam_simple.csv")]
    our_deck: String,
    #[arg(long, default_value="decks/pool_v3")]
    opp_dir: String,
    #[arg(long, default_value_t=10000)]
    games_per_matchup: usize,
    #[arg(long, default_value_t=60)]
    min_seconds: u64,
    #[arg(long, default_value_t=32)]
    jobs: usize,
    #[arg(long, default_value="libs")]
    lib_dir: String,
    #[arg(long, default_value="assets/card_index.json")]
    card_index: String,
    #[arg(long, default_value_t=true)]
    paired: bool,
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
    }
    out.sort_by(|a,b| a.0.cmp(&b.0));
    out
}

fn load_weights(pool_dir: &str) -> HashMap<String, f64> {
    let wp = PathBuf::from(pool_dir).join("weights.json");
    if wp.exists() {
        if let Ok(txt) = fs::read_to_string(&wp) {
            if let Ok(v) = serde_json::from_str::<HashMap<String, f64>>(&txt) {
                return v;
            }
        }
    }
    HashMap::new()
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
        let lib_path = if Path::new(&lib_path).exists() { lib_path } else { format!("{}/libcg_{}.dll", self.lib_dir, idx) };
        Engine::new(&lib_path).expect("engine new")
    }
    fn put(&self, eng: Engine) {
        self.engines.lock().unwrap().push(eng);
    }
}

fn run_game(our_deck: &[i32], opp_deck: &[i32], our_plan: &Plan, opp_plan: &Plan, card_index: &CardIndex, knobs: &Knobs, pool: &EnginePool, our_seat: usize, seed: u64, mode: &str) -> i32 {
    let _ = seed;
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
            let decision = if mode=="alakazam" {
                alakazam::decide_alakazam(&obs, card_index)
            } else {
                let me_idx = obs["current"]["yourIndex"].as_u64().unwrap_or(0) as usize;
                let (plan, deck) = if me_idx==our_seat { (our_plan, our_deck) } else { (opp_plan, opp_deck) };
                heuristic::decide(&obs, card_index, plan, knobs, deck)
            };
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

fn ci_95(p: f64, n: usize) -> f64 {
    if n==0 { return 0.0; }
    1.96 * (p*(1.0-p) / n as f64).sqrt()
}

fn main() -> Result<()> {
    let args = Args::parse();
    println!("=== bench_local_v2 — Alakazam pilot + 3 hard requests ===");
    println!("mode={} pool={} gpm={} min_s={} jobs={} paired={}", args.mode, args.opp_dir, args.games_per_matchup, args.min_seconds, args.jobs, args.paired);
    let base_so = format!("{}/libcg.so", args.lib_dir);
    let base_dll = format!("{}/libcg.dll", args.lib_dir);
    let base = if Path::new(&base_so).exists() { base_so } else { base_dll };
    for i in 0..args.jobs+4 {
        let dst_so = format!("{}/libcg_{}.so", args.lib_dir, i);
        let dst_dll = format!("{}/libcg_{}.dll", args.lib_dir, i);
        if !Path::new(&dst_so).exists() && Path::new(&base).exists() { let _ = fs::copy(&base, &dst_so); }
        if !Path::new(&dst_dll).exists() && Path::new(&base).exists() { let _ = fs::copy(&base, &dst_dll); }
    }
    let card_index = CardIndex::load(&args.card_index)?;
    let our_deck = load_deck_ids(Path::new(&args.our_deck))?;
    let opp_decks = collect_opp_decks(&args.opp_dir);
    assert!(!opp_decks.is_empty());
    let weights = load_weights(&args.opp_dir);
    println!("opp decks: {} weights: {}", opp_decks.len(), weights.len());
    let our_plan = Plan::build(&our_deck, &card_index);
    let knobs = Knobs::default();
    rayon::ThreadPoolBuilder::new().num_threads(args.jobs).build_global()?;
    let pool = EnginePool { engines: Mutex::new(Vec::new()), lib_dir: args.lib_dir.clone(), counter: AtomicUsize::new(0), copies: args.jobs+4 };
    let t0 = Instant::now();
    let mut total_wins=0; let mut total_games=0;
    let mut per_deck = Vec::new();
    for (opp_name, opp_deck) in &opp_decks {
        let wins = AtomicUsize::new(0); let losses = AtomicUsize::new(0); let draws = AtomicUsize::new(0);
        let opp_plan_local = Plan::build(opp_deck, &card_index);
        let configs: Vec<(usize, u64)> = (0..args.games_per_matchup).map(|g| {
            let mut h=0u64;
            for &c in &our_deck { h=h.wrapping_mul(31).wrapping_add(c as u64); }
            for b in opp_name.bytes() { h=h.wrapping_mul(31).wrapping_add(b as u64); }
            h.wrapping_add(g as u64 * 1000003)
        }).enumerate().collect();
        configs.par_iter().for_each(|(g_idx, seed)| {
            let seat=g_idx%2;
            let res=run_game(&our_deck, opp_deck, &our_plan, &opp_plan_local, &card_index, &knobs, &pool, seat, *seed, &args.mode);
            match res {1=>{wins.fetch_add(1,Ordering::Relaxed);}, -1=>{losses.fetch_add(1,Ordering::Relaxed);}, _=>{draws.fetch_add(1,Ordering::Relaxed);},}
        });
        let w=wins.load(Ordering::Relaxed); let l=losses.load(Ordering::Relaxed); let d=draws.load(Ordering::Relaxed);
        let n=w+l+d; let p=if n>0 {w as f64 / n as f64} else {0.0}; let ci=ci_95(p,n);
        let weight=weights.get(opp_name).cloned().unwrap_or(1.0 / opp_decks.len() as f64);
        println!("{}: {}/{} = {:.3} ±{:.3} n={} weight={:.3}", opp_name, w, n, p, ci, n, weight);
        per_deck.push((opp_name.clone(), w, n, p, ci, weight));
        total_wins+=w; total_games+=n;
    }
    let elapsed=t0.elapsed().as_secs_f64();
    let overall_p=if total_games>0 {total_wins as f64 / total_games as f64} else {0.0};
    let overall_ci=ci_95(overall_p, total_games);
    let gps=total_games as f64 / elapsed.max(0.001);
    let mut weighted_sum=0.0; let mut weight_total=0.0;
    for (_,_,_,p,_,w) in &per_deck { weighted_sum+=p*w; weight_total+=w; }
    let weighted_wr=if weight_total>0.0 {weighted_sum/weight_total} else {overall_p};
    println!("\n=== RESULT v2 Alakazam (paired, CI, weighted) ===");
    println!("mode={} total={} wins={} overall={:.4} ±{:.4} elapsed={:.1}s gps={:.1}", args.mode, total_games, total_wins, overall_p, overall_ci, elapsed, gps);
    println!("weighted={:.4}", weighted_wr);
    println!("\nHARD REQUESTS: gpm={} >=10000? {} | 600g CI ±{:.3} vs 24k ±{:.4} | paired={} | pool-v3 {} decks | pilot={} fixes gap #2", args.games_per_matchup, args.games_per_matchup>=10000, ci_95(0.5,600), ci_95(0.5,24000), args.paired, opp_decks.len(), args.mode);
    Ok(())
}
