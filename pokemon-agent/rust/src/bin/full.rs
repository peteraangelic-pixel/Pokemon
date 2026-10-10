use anyhow::Result;
use clap::Parser;
use rayon::prelude::*;
use std::path::{Path, PathBuf};
use std::fs;

mod engine {
    include!("../engine.rs");
}
mod heuristic {
    include!("../heuristic.rs");
}
use engine::Engine;
use heuristic::{CardIndex, Knobs};

#[derive(Parser, Debug)]
struct Args {
    #[arg(long, default_value="decks/v2_boss.csv")]
    our_deck: String,
    #[arg(long, default_value="decks/top7_live/Eugen_LNCanti.csv")]
    opp_deck: String,
    #[arg(long, default_value_t=2)]
    games: usize,
    #[arg(long, default_value=".venv/lib/python3.11/site-packages/kaggle_environments/envs/cabt/cg/libcg.so")]
    lib_path: String,
    #[arg(long, default_value="assets/card_index.json")]
    card_index: String,
}

fn load_deck(path: &Path) -> Result<Vec<i32>> {
    let content = fs::read_to_string(path)?;
    let mut ids = Vec::new();
    for tok in content.split(|c: char| c==',' || c.is_whitespace()) {
        if tok.trim().is_empty() { continue; }
        if let Ok(id) = tok.trim().parse::<i32>() { ids.push(id); }
    }
    Ok(ids)
}

fn run_one_game(our_deck: &[i32], opp_deck: &[i32], lib_path: &str, card_index: &CardIndex, knobs: &Knobs, seat: usize) -> Result<i32> {
    let (d0, d1) = if seat == 0 { (our_deck, opp_deck) } else { (opp_deck, our_deck) };
    let mut engine = Engine::new(lib_path)?;
    let mut obs = engine.battle_start(d0, d1)?;

    loop {
        let current = &obs["current"];
        if current.is_null() { break; }
        let result = current["result"].as_i64().unwrap_or(-1);
        if result >= 0 {
            let our_win = if seat == 0 { result == 0 } else { result == 1 };
            let is_draw = result == 2;
            if is_draw { return Ok(0); } else if our_win { return Ok(1); } else { return Ok(-1); }
        }

        let decision = heuristic::decide(&obs, card_index, knobs);
        if decision.is_empty() && obs["select"].is_null() { break; }

        obs = engine.select(&decision)?;
    }
    Ok(0)
}

fn main() -> Result<()> {
    let args = Args::parse();
    let our_deck = load_deck(Path::new(&args.our_deck))?;
    let opp_deck = load_deck(Path::new(&args.opp_deck))?;
    let card_index = CardIndex::load(&args.card_index)?;
    let knobs = Knobs::default();

    println!("Our deck: {} cards, Opp deck: {} cards", our_deck.len(), opp_deck.len());
    println!("Card index: {} cards, {} attacks", card_index.cards.len(), card_index.attacks.len());
    println!("Lib: {}", args.lib_path);
    println!("Games: {} (threads: {})", args.games, rayon::current_num_threads());

    let start = std::time::Instant::now();

    // Note: libcg.so has global state, so we cannot run parallel games in same process with rayon threads.
    // We run sequentially here, but outer rust_gauntlet can spawn multiple processes in parallel.
    // For demonstration, we run sequential.
    let mut results = Vec::new();
    for g in 0..args.games {
        let seat = g % 2;
        match run_one_game(&our_deck, &opp_deck, &args.lib_path, &card_index, &knobs, seat) {
            Ok(r) => results.push(r),
            Err(e) => {
                eprintln!("Game {} failed: {}", g, e);
                results.push(0);
            }
        }
    }

    let wins = results.iter().filter(|&&r| r==1).count();
    let losses = results.iter().filter(|&&r| r==-1).count();
    let draws = results.iter().filter(|&&r| r==0).count();

    println!("Results: {}W-{}L-{}D in {:.2}s", wins, losses, draws, start.elapsed().as_secs_f64());
    if wins+losses>0 {
        println!("Win rate: {:.3}", wins as f64 / (wins+losses) as f64);
    }

    Ok(())
}
