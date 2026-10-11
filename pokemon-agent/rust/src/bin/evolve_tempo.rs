//! gen8 evolution — Rust+Rayon orchestrator (permanent tool).
//!
//! Same logic as tools/evolve_gen8.py (sandbox fast path), but the evolution
//! loop (population, selection, mutation, aggregation) runs natively and the
//! per-candidate evaluation is fanned out with rayon over Python worker
//! subprocesses (the real submission agent is Python; the engine is the
//! kaggle-environments libcg.so — the worker drives it via direct FFI, in
//! process, one GameInitialize per worker).
//!
//! Build:  cargo build --release --bin evolve_tempo   (needs cargo; this
//! sandbox has no toolchain — build & run on GitHub Actions, see
//! .github/workflows/evolve_gen8.yml)
//!
//! Usage (from pokemon-agent/):
//!   cargo run --release --bin evolve_tempo -- \
//!     --agent agents/main_heuristic_v11.py \
//!     --our-deck decks/v12_30_boss4.csv \
//!     --loss-dir decks/v14_losses --weak-dir decks/weak_field \
//!     --games 30 --pop 80 --gens 4 --workers 8 --seed 7 \
//!     --out search_results/gen8_rust.json

use anyhow::{Context, Result};
use clap::Parser;
use rayon::prelude::*;
use rand::rngs::StdRng;
use rand::Rng;
use rand::SeedableRng;
use regex::Regex;
use serde_json::{json, Map, Value};
use std::collections::HashMap;
use std::fs;
use std::path::Path;
use std::process::Command;
use std::time::Instant;

#[derive(Parser, Debug)]
#[command(name = "evolve_tempo", about = "tempo-aware heuristic config evolution (Rust+Rayon)")]
struct Args {
    #[arg(long, default_value = "agents/main_heuristic_v11.py")]
    agent: String,
    #[arg(long, default_value = "decks/v12_30_boss4.csv")]
    our_deck: String,
    #[arg(long, default_value = "decks/v14_losses")]
    loss_dir: String,
    #[arg(long, default_value = "YumeNeko,OceanMix,Kentaro_Totsuka,ANMOL_GARG,Leon_Liu,Darren_Sheehan")]
    meta_decks: String,
    #[arg(long, default_value = "decks/weak_field")]
    weak_dir: String,
    #[arg(long, default_value = "decks/top30_live")]
    meta_dir: String,
    #[arg(long, default_value_t = 30)]
    games: usize,
    #[arg(long, default_value_t = 80)]
    pop: usize,
    #[arg(long, default_value_t = 4)]
    gens: usize,
    #[arg(long, default_value_t = 8)]
    workers: usize,
    #[arg(long, default_value_t = 7)]
    seed: u64,
    #[arg(long, default_value = "search_results/gen8_rust.json")]
    out: String,
    #[arg(long, default_value = "python3")]
    python: String,
    /// repo root (parent of pokemon-agent/) — where worker_eval.py resolves
    /// .venv/libcg.so and card data.
    #[arg(long, default_value = ".")]
    repo: String,
}

type Config = HashMap<String, i32>;

#[derive(Debug, Clone)]
struct EvalResult {
    per_deck: HashMap<String, [usize; 2]>, // name -> [wins, losses]
    t9: f64,
    fp: f64,
    turns: f64,
    games: usize,
}

impl EvalResult {
    fn winrate(&self) -> f64 {
        let (mut w, mut l) = (0usize, 0usize);
        for (_, wl) in &self.per_deck {
            w += wl[0];
            l += wl[1];
        }
        if w + l == 0 {
            0.0
        } else {
            w as f64 / (w + l) as f64
        }
    }
    fn empty() -> Self {
        EvalResult {
            per_deck: HashMap::new(),
            t9: 0.0,
            fp: 10.0,
            turns: 0.0,
            games: 0,
        }
    }
}

fn load_deck_ids(path: &Path) -> Result<Vec<i32>> {
    let content = fs::read_to_string(path)
        .with_context(|| format!("reading deck {}", path.display()))?;
    let mut ids = Vec::new();
    for token in content.split(|c: char| c == ',' || c.is_whitespace()) {
        if token.trim().is_empty() {
            continue;
        }
        if let Ok(id) = token.trim().parse::<i32>() {
            ids.push(id);
        }
    }
    Ok(ids)
}

fn read_base_config(agent: &Path) -> Result<Config> {
    let txt = fs::read_to_string(agent)
        .with_context(|| format!("reading agent {}", agent.display()))?;
    let re = Regex::new(r#"setdefault\("PTCG_(\w+)", "(-?\d+)"\)"#).unwrap();
    let mut base = HashMap::new();
    for m in re.captures_iter(&txt) {
        base.insert(m[1].to_string(), m[2].parse::<i32>().unwrap());
    }
    if base.is_empty() {
        anyhow::bail!("no PTCG_* setdefaults found in {}", agent.display());
    }
    Ok(base)
}

struct PoolEntry {
    name: String,
    deck: Vec<i32>,
    weight: f64,
}

fn build_pool(args: &Args) -> Result<Vec<PoolEntry>> {
    let mut opp: Vec<PoolEntry> = Vec::new();
    let add_dir = |d: &str, weight: f64, prefix: &str, out: &mut Vec<PoolEntry>| {
        let dir = Path::new(d);
        if !dir.is_dir() {
            eprintln!("warn: pool dir {} missing, skipping", d);
            return;
        }
        let mut paths: Vec<std::path::PathBuf> = fs::read_dir(dir)
            .unwrap()
            .filter_map(|e| e.ok())
            .map(|e| e.path())
            .filter(|p| p.extension().map_or(false, |x| x == "csv"))
            .filter(|p| p.file_name().map_or(true, |n| !n.to_string_lossy().starts_with('_')))
            .collect();
        paths.sort();
        for p in paths {
            if let Ok(deck) = load_deck_ids(&p) {
                let stem = p.file_stem().unwrap().to_string_lossy().to_string();
                out.push(PoolEntry {
                    name: format!("{}{}", prefix, stem),
                    deck,
                    weight,
                });
            }
        }
    };
    add_dir(&args.loss_dir, 3.0, "", &mut opp);
    for d in args.meta_decks.split(',') {
        let d = d.trim();
        if d.is_empty() {
            continue;
        }
        let p = Path::new(&args.meta_dir).join(format!("{}.csv", d));
        if let Ok(deck) = load_deck_ids(&p) {
            opp.push(PoolEntry {
                name: format!("meta:{}", d),
                deck,
                weight: 2.0,
            });
        } else {
            eprintln!("warn: meta deck {} missing", p.display());
        }
    }
    add_dir(&args.weak_dir, 1.0, "weak:", &mut opp);
    let mut seen: Vec<Vec<i32>> = Vec::new();
    let mut out = Vec::new();
    for e in opp {
        if seen.iter().any(|s| s == &e.deck) {
            continue;
        }
        seen.push(e.deck.clone());
        out.push(e);
    }
    Ok(out)
}

fn fitness(res: &EvalResult, pool: &[PoolEntry]) -> (f64, f64) {
    let wmap: HashMap<&str, f64> = pool.iter().map(|p| (p.name.as_str(), p.weight)).collect();
    let mut wsum = 0.0;
    let mut wwr = 0.0;
    for (name, wl) in &res.per_deck {
        let wt = wmap.get(name.as_str()).copied().unwrap_or(1.0);
        wwr += wt * wl[0] as f64;
        wsum += wt * (wl[0] + wl[1]) as f64;
    }
    let wwr = wwr / wsum.max(1.0);
    let t9n = (res.t9 / 2.0).min(1.0);
    let fpn = ((10.0 - res.fp) / 4.0).clamp(0.0, 1.0);
    (0.65 * wwr + 0.20 * t9n + 0.15 * fpn, wwr)
}

fn mutate(base: &Config, sigma: f64, rng: &mut StdRng) -> Config {
    let mut c = Config::with_capacity(base.len());
    for (k, v) in base {
        let nv = (*v as f64) * (1.0 + gaussian(rng, sigma));
        c.insert(k.clone(), nv.round() as i32);
    }
    c
}

/// Box-Muller normal(0, sigma).
fn gaussian(rng: &mut StdRng, sigma: f64) -> f64 {
    let u1: f64 = rng.gen_range(1e-12..1.0);
    let u2: f64 = rng.gen_range(0.0..1.0);
    (-2.0 * u1.ln()).sqrt() * (2.0 * std::f64::consts::PI * u2).cos() * sigma
}

fn parse_worker_output(buf: &[u8]) -> Result<EvalResult> {
    let s = String::from_utf8_lossy(buf);
    let line = s
        .lines()
        .find(|l| l.trim_start().starts_with('{'))
        .context("no JSON line in worker output")?;
    let v: Value = serde_json::from_str(line).context("worker JSON parse")?;
    let mut per_deck = HashMap::new();
    if let Some(m) = v.get("per_deck").and_then(|x| x.as_object()) {
        for (k, val) in m {
            if let Some(a) = val.as_array() {
                per_deck.insert(
                    k.clone(),
                    [
                        a.first().and_then(|x| x.as_u64()).unwrap_or(0) as usize,
                        a.get(1).and_then(|x| x.as_u64()).unwrap_or(0) as usize,
                    ],
                );
            }
        }
    }
    Ok(EvalResult {
        per_deck,
        t9: v.get("t9").and_then(|x| x.as_f64()).unwrap_or(0.0),
        fp: v.get("fp").and_then(|x| x.as_f64()).unwrap_or(10.0),
        turns: v.get("turns").and_then(|x| x.as_f64()).unwrap_or(0.0),
        games: v.get("games").and_then(|x| x.as_u64()).unwrap_or(0) as usize,
    })
}

/// Evaluate one candidate: spawn the Python worker (env carries the config),
/// pool comes from the --pool file written by main(), read one JSON summary.
fn evaluate_candidate(args: &Args, idx: usize, config: &Config, pool_file: &Path) -> (usize, Config, EvalResult) {
    let mut cmd = Command::new(&args.python);
    cmd.arg("rust/worker_eval.py")
        .arg("--agent").arg(&args.agent)
        .arg("--our-deck").arg(&args.our_deck)
        .arg("--repo").arg(&args.repo)
        .arg("--pool").arg(pool_file)
        .arg("--games").arg(args.games.to_string());
    for (k, v) in config {
        cmd.env(format!("PTCG_{}", k), v.to_string());
    }
    match cmd.output() {
        Ok(o) if o.status.success() => match parse_worker_output(&o.stdout) {
            Ok(r) => (idx, config.clone(), r),
            Err(e) => {
                eprintln!("warn: bad worker output for candidate {}: {}", idx, e);
                (idx, config.clone(), EvalResult::empty())
            }
        },
        Ok(o) => {
            eprintln!("warn: worker for candidate {} exited {}: {}",
                idx, o.status, String::from_utf8_lossy(&o.stderr).chars().take(300).collect::<String>());
            (idx, config.clone(), EvalResult::empty())
        }
        Err(e) => {
            eprintln!("warn: spawn worker for candidate {} failed: {}", idx, e);
            (idx, config.clone(), EvalResult::empty())
        }
    }
}

fn main() -> Result<()> {
    let args = Args::parse();
    rayon::ThreadPoolBuilder::new().num_threads(args.workers).build_global()
        .context("rayon pool (already set?)")?;

    let base = read_base_config(Path::new(&args.agent))?;
    let pool = build_pool(&args)?;
    let our_deck = load_deck_ids(Path::new(&args.our_deck))?;
    assert_eq!(our_deck.len(), 60, "our deck must have 60 cards");
    eprintln!(
        "pool: {} decks, {} games/candidate, base {} keys, {} workers",
        pool.len(),
        pool.len() * args.games,
        base.len(),
        args.workers
    );

    // pool file consumed by each worker (avoids a huge env payload)
    let pool_file = Path::new(&args.out)
        .parent()
        .map(|p| p.join("evolve_pool.json"))
        .unwrap_or_else(|| Path::new("evolve_pool.json").to_path_buf());
    if let Some(parent) = pool_file.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(
        &pool_file,
        serde_json::to_string(&pool.iter().map(|p| json!({"name": p.name, "deck": p.deck})).collect::<Vec<_>>())?,
    )?;

    let mut best: Option<(Config, EvalResult, f64, f64)> = None;
    let mut history: Vec<Value> = Vec::new();
    let mut rng = StdRng::seed_from_u64(args.seed);
    let mut pop: Vec<Config> = vec![base.clone()];
    for _ in 1..args.pop {
        pop.push(mutate(&base, 0.08, &mut rng));
    }

    for g in 0..args.gens {
        let sigma = [0.08, 0.04, 0.02, 0.01][g.min(3)];
        let nsel = [15, 10, 6, 6][g.min(3)];
        eprintln!("\n=== gen {} ({} candidates) ===", g, pop.len());
        let t0 = Instant::now();

        let results: Vec<(usize, Config, EvalResult, f64, f64)> = pop
            .par_iter()
            .enumerate()
            .map(|(i, c)| {
                let (idx, cfg, res) = evaluate_candidate(&args, i, c, &pool_file);
                let (fit, wwr) = fitness(&res, &pool);
                (idx, cfg, res, fit, wwr)
            })
            .collect();

        let mut sorted = results;
        sorted.sort_by(|a, b| b.3.partial_cmp(&a.3).unwrap_or(std::cmp::Ordering::Equal));
        for (idx, cfg, res, fit, wwr) in sorted.iter().take(5) {
            let diff: Map<String, Value> = cfg
                .iter()
                .filter(|(k, v)| base.get(*k).map_or(true, |bv| *bv != **v))
                .map(|(k, v)| (k.clone(), json!(v)))
                .collect();
            eprintln!(
                "  #{} f={:.4} wwr={:.3} wr={:.3} t9={:.2} fp={:.1} d={}",
                idx, fit, wwr, res.winrate(), res.t9, res.fp,
                serde_json::to_string(&diff).unwrap()
            );
        }
        let top: Vec<Value> = sorted
            .iter()
            .take(10)
            .map(|(_, cfg, res, fit, wwr)| {
                json!({"config": cfg, "fitness": fit, "wwr": wwr,
                       "agg": {"t9": res.t9, "fp": res.fp, "turns": res.turns, "games": res.games}})
            })
            .collect();
        history.push(json!({"gen": g, "top": top}));

        if best.as_ref().map_or(true, |(_, _, bf, _)| sorted[0].3 > *bf) {
            let (_, cfg, res, fit, wwr) = sorted.remove(0);
            best = Some((cfg, res, fit, wwr));
        }

        let mut nxt: Vec<Config> = vec![base.clone()];
        for (_, cfg, _, _, _) in sorted.iter().take(nsel) {
            nxt.push(mutate(cfg, sigma, &mut rng));
        }
        nxt.truncate(args.pop);
        pop = nxt;
        eprintln!("gen {} done in {:.0}s", g, t0.elapsed().as_secs_f64());
    }

    let (cfg, res, fit, wwr) = best.context("no candidates evaluated")?;
    eprintln!("\nBEST: f={:.4} wwr={:.3} wr={:.3} t9={:.2} fp={:.1} games={}", fit, wwr, res.winrate(), res.t9, res.fp, res.games);
    let out_v = json!({
        "base": base,
        "best": {"config": cfg, "fitness": fit, "wwr": wwr,
                 "agg": {"t9": res.t9, "fp": res.fp, "turns": res.turns, "games": res.games},
                 "per_deck": res.per_deck},
        "history": history,
    });
    fs::write(&args.out, serde_json::to_string_pretty(&out_v)?)?;
    eprintln!("wrote {}", args.out);
    Ok(())
}
