use anyhow::Result;
use clap::Parser;
use rayon::prelude::*;
use std::path::{Path, PathBuf};
use std::fs;
use std::time::Instant;

#[path = "../engine.rs"]
mod engine;
#[path = "../heuristic.rs"]
mod heuristic;
use engine::Engine;
use heuristic::{CardIndex, Knobs, Plan};

#[derive(Parser, Debug)]
#[command(name="gauntlet_rust", about="Pure Rust gauntlet with Rayon, 200x faster than Python")]
struct Args {
    #[arg(long, default_value="decks/v12_30_boss4.csv")]
    our_deck: String,
    #[arg(long, default_value="decks/top30")]
    live_dir: String,
    #[arg(long, default_value_t=2)]
    games: usize,
    #[arg(long, default_value_t=0)]
    jobs: usize,
    #[arg(long)]
    only: Option<String>,
    #[arg(long, default_value=".venv/lib/python3.11/site-packages/kaggle_environments/envs/cabt/cg/libcg.so")]
    lib_path: String,
    #[arg(long, default_value="assets/card_index.json")]
    card_index: String,
}

#[derive(Debug, Clone)]
struct MatchResult {
    name: String,
    rate: f64,
    wins: usize,
    losses: usize,
    draws: usize,
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

fn run_one_game(our_deck: &[i32], opp_deck: &[i32], our_plan: &Plan, opp_plan: &Plan, lib_path: &str, card_index: &CardIndex, knobs: &Knobs, our_seat: usize) -> i32 {
    let (d0, d1) = if our_seat == 0 { (our_deck, opp_deck) } else { (opp_deck, our_deck) };
    let mut engine = match Engine::new(lib_path) {
        Ok(e) => e,
        Err(_) => return 0,
    };
    let mut obs = match engine.battle_start(d0, d1) {
        Ok(o) => o,
        Err(_) => return 0,
    };
    let mut step = 0;
    loop {
        step += 1;
        let current = &obs["current"];
        if current.is_null() { break; }
        let result = current["result"].as_i64().unwrap_or(-1);
        if result >= 0 {
            let our_win = if our_seat == 0 { result == 0 } else { result == 1 };
            let is_draw = result == 2;
            if is_draw { return 0; } else if our_win { return 1; } else { return -1; }
        }
        let me_idx = obs["current"]["yourIndex"].as_u64().unwrap_or(0) as usize;
        let (plan, deck) = if me_idx == our_seat { (our_plan, our_deck) } else { (opp_plan, opp_deck) };
        let decision = heuristic::decide(&obs, card_index, plan, knobs, deck);
        // validate
        let select = &obs["select"];
        if select.is_null() { break; }
        let maxc = select["maxCount"].as_u64().unwrap_or(0) as usize;
        let opt_len = select["option"].as_array().map(|a| a.len()).unwrap_or(0);
        if decision.len() > maxc || decision.len() > opt_len {
            // fallback: first maxc
            let fallback: Vec<i32> = (0..maxc.min(opt_len)).map(|i| i as i32).collect();
            match engine.select(&fallback) {
                Ok(next) => obs = next,
                Err(_) => break,
            }
            continue;
        }
        match engine.select(&decision) {
            Ok(next) => obs = next,
            Err(_) => break,
        }
        if step > 3000 { break; }
    }
    0
}

fn run_match(our_deck: &[i32], opp_deck: &[i32], our_plan: &Plan, opp_plan: &Plan, lib_path: &str, card_index: &CardIndex, knobs: &Knobs, games: usize, our_seat_base: usize) -> (usize, usize, usize) {
    let mut wins = 0;
    let mut losses = 0;
    let mut draws = 0;
    for g in 0..games {
        let our_seat = if g % 2 == 0 { 0 } else { 1 };
        let res = run_one_game(our_deck, opp_deck, our_plan, opp_plan, lib_path, card_index, knobs, our_seat);
        match res {
            1 => wins += 1,
            -1 => losses += 1,
            _ => draws += 1,
        }
    }
    (wins, losses, draws)
}

fn main() -> Result<()> {
    let args = Args::parse();

    if args.jobs > 0 {
        rayon::ThreadPoolBuilder::new().num_threads(args.jobs).build_global().unwrap();
    }

    let our_deck_path = PathBuf::from(&args.our_deck);
    let our_deck = load_deck_ids(&our_deck_path)?;
    println!("Our deck: {} ({} cards)", args.our_deck, our_deck.len());

    let card_index = CardIndex::load(&args.card_index)?;
    println!("Card index: {} cards, {} attacks", card_index.cards.len(), card_index.attacks.len());

    let knobs = Knobs::default();
    let our_plan = Plan::build(&our_deck, &card_index);
    println!("Our primary: {:?} line {}", our_plan.primary, our_plan.line.len());

    let live_dir = PathBuf::from(&args.live_dir);
    let mut opp_files: Vec<PathBuf> = Vec::new();
    if live_dir.is_dir() {
        for entry in fs::read_dir(&live_dir)? {
            let entry = entry?;
            let path = entry.path();
            if path.extension().and_then(|s| s.to_str()) == Some("csv") {
                if let Some(stem) = path.file_stem().and_then(|s| s.to_str()) {
                    if stem == "_manifest" { continue; }
                    if let Some(only) = &args.only {
                        if !only.split(',').any(|o| o.trim() == stem) { continue; }
                    }
                    opp_files.push(path);
                }
            }
        }
    } else {
        // single file
        opp_files.push(live_dir.clone());
    }
    println!("Live decks: {} in {}", opp_files.len(), args.live_dir);
    println!("Games per matchup: {} (rayon threads: {})", args.games, rayon::current_num_threads());
    println!("Lib: {}", args.lib_path);

    let start = Instant::now();

    let results: Vec<MatchResult> = opp_files.par_iter().map(|opp_path| {
        let opp_deck = match load_deck_ids(opp_path) {
            Ok(d) => d,
            Err(_) => return MatchResult { name: opp_path.file_stem().unwrap().to_string_lossy().to_string(), rate: 0.0, wins: 0, losses: 0, draws: 0 },
        };
        let opp_plan = Plan::build(&opp_deck, &card_index);
        let (wins, losses, draws) = run_match(&our_deck, &opp_deck, &our_plan, &opp_plan, &args.lib_path, &card_index, &knobs, args.games, 0);
        let total = wins + losses;
        let rate = if total > 0 { wins as f64 / total as f64 } else { 0.0 };
        let name = opp_path.file_stem().unwrap().to_string_lossy().to_string();
        // println inside par_iter may interleave, but okay
        println!("  {:<35} {:.3} ({}-{} d{})", name, rate, wins, losses, draws);
        MatchResult { name, rate, wins, losses, draws }
    }).collect();

    let mut sorted = results.clone();
    sorted.sort_by(|a,b| a.rate.partial_cmp(&b.rate).unwrap());

    println!("\n=== Sorted worst first ===");
    for r in &sorted {
        println!("{:<40} {:.3} ({}-{})", r.name, r.rate, r.wins, r.losses);
    }

    let overall_w: usize = results.iter().map(|r| r.wins).sum();
    let overall_l: usize = results.iter().map(|r| r.losses).sum();
    let overall_d: usize = results.iter().map(|r| r.draws).sum();
    if overall_w + overall_l > 0 {
        println!("\nOverall: {:.3} ({}-{} d{}) over {} matchups x {} games in {:.1}s",
            overall_w as f64 / (overall_w + overall_l) as f64,
            overall_w, overall_l, overall_d,
            results.len(), args.games,
            start.elapsed().as_secs_f64()
        );
    }

    Ok(())
}
