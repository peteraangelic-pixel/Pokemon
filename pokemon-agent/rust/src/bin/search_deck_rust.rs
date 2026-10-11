use anyhow::Result;
use clap::Parser;
use std::path::{Path, PathBuf};
use std::fs;

mod engine {
    include!("../engine.rs");
}
mod heuristic {
    include!("../heuristic.rs");
}
use heuristic::{CardIndex, Knobs, Plan};

#[derive(Parser, Debug)]
#[command(name="search_deck_rust", about="Fast deck search using Rust engine")]
struct Args {
    #[arg(long, default_value="decks/v12_30_boss4.csv")]
    base_deck: String,
    #[arg(long, default_value="decks/top30")]
    live_dir: String,
    #[arg(long, default_value_t=50)]
    trials: usize,
    #[arg(long, default_value_t=2)]
    games: usize,
    #[arg(long, default_value="assets/card_index.json")]
    card_index: String,
    #[arg(long, default_value=".venv/lib/python3.11/site-packages/kaggle_environments/envs/cabt/cg/libcg.so")]
    lib_path: String,
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

fn main() -> Result<()> {
    let args = Args::parse();
    println!("Deck search placeholder — use Python search_deck.py for now, Rust version coming");
    println!("Base: {} trials {} games {}", args.base_deck, args.trials, args.games);
    Ok(())
}
