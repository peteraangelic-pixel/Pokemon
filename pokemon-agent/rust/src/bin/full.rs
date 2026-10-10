use anyhow::Result;
use clap::Parser;
use rayon::prelude::*;
use std::path::{PathBuf, Path};
use std::fs;

mod engine {
    include!("../engine.rs");
}
use engine::Engine;

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
}

fn load_deck(path: &Path) -> Result<Vec<i32>> {
    let content = fs::read_to_string(path)?;
    let mut ids = Vec::new();
    for tok in content.split(|c: char| c==',' || c.is_whitespace()) {
        if tok.trim().is_empty() { continue; }
        if let Ok(id) = tok.trim().parse::<i32>() {
            ids.push(id);
        }
    }
    Ok(ids)
}

// Very simple agent: pick first legal option, or random if needed
// For now, just to test engine FFI
fn simple_agent(obs: &serde_json::Value) -> Vec<i32> {
    // obs["select"]["option"] is array, "maxCount" is int
    let select = &obs["select"];
    if select.is_null() {
        return vec![];
    }
    let max_count = select["maxCount"].as_i64().unwrap_or(0) as usize;
    let options = select["option"].as_array().map(|a| a.len()).unwrap_or(0);
    if max_count == 0 || options == 0 {
        return vec![];
    }
    // Pick first max_count options
    (0..max_count.min(options)).map(|i| i as i32).collect()
}

fn run_one_game(our_deck: &[i32], opp_deck: &[i32], lib_path: &str, seat: usize) -> Result<i32> {
    // seat 0 = we are player0, seat 1 = we are player1
    let (d0, d1) = if seat == 0 { (our_deck, opp_deck) } else { (opp_deck, our_deck) };
    let mut engine = Engine::new(lib_path)?;
    let mut obs = engine.battle_start(d0, d1)?;

    loop {
        let current = &obs["current"];
        if current.is_null() {
            break;
        }
        let result = current["result"].as_i64().unwrap_or(-1);
        if result >= 0 {
            // 0 = p0 win, 1 = p1 win, 2 = draw
            let our_win = if seat == 0 { result == 0 } else { result == 1 };
            let is_draw = result == 2;
            if is_draw {
                return Ok(0);
            } else if our_win {
                return Ok(1);
            } else {
                return Ok(-1);
            }
        }

        let your_index = current["yourIndex"].as_i64().unwrap_or(0) as usize;
        let is_our_turn = your_index == seat;

        let decision = if is_our_turn {
            simple_agent(&obs)
        } else {
            // Opponent also simple for now
            simple_agent(&obs)
        };

        if decision.is_empty() && obs["select"].is_null() {
            // No select, maybe need to provide deck? First turn deck selection
            // obs["select"] == None means need to return deck
            // For first turn, both players return deck - we already did via battle_start, so this shouldn't happen
            break;
        }

        obs = engine.select(&decision)?;
    }

    Ok(0)
}

fn main() -> Result<()> {
    let args = Args::parse();
    let our_deck = load_deck(Path::new(&args.our_deck))?;
    let opp_deck = load_deck(Path::new(&args.opp_deck))?;

    println!("Our deck: {} cards, Opp deck: {} cards", our_deck.len(), opp_deck.len());
    println!("Lib: {}", args.lib_path);
    println!("Games: {}", args.games);

    let start = std::time::Instant::now();

    let results: Vec<i32> = (0..args.games).into_par_iter()
        .map(|g| {
            let seat = g % 2;
            match run_one_game(&our_deck, &opp_deck, &args.lib_path, seat) {
                Ok(r) => r,
                Err(e) => {
                    eprintln!("Game {} failed: {}", g, e);
                    0
                }
            }
        })
        .collect();

    let wins = results.iter().filter(|&&r| r==1).count();
    let losses = results.iter().filter(|&&r| r==-1).count();
    let draws = results.iter().filter(|&&r| r==0).count();

    println!("Results: {}W-{}L-{}D in {:.2}s", wins, losses, draws, start.elapsed().as_secs_f64());
    if wins+losses>0 {
        println!("Win rate: {:.3}", wins as f64 / (wins+losses) as f64);
    }

    Ok(())
}
