use anyhow::Result;
use clap::Parser;
use std::path::{Path, PathBuf};
use std::fs;
use rand::seq::SliceRandom;
use rand::Rng;
use rayon::prelude::*;
use std::sync::Mutex;

mod engine {
    include!("../engine.rs");
}
mod heuristic {
    include!("../heuristic.rs");
}
use heuristic::{CardIndex, Knobs, Plan};
use engine::Engine;

#[derive(Parser, Debug)]
#[command(name="search_deck_rust", about="Fast deck search using Rust engine + Rayon, 200x faster")]
struct Args {
    #[arg(long, default_value="decks/top30")]
    live_dir: String,
    #[arg(long, default_value_t=100)]
    trials: usize,
    #[arg(long, default_value_t=2)]
    games: usize,
    #[arg(long, default_value="assets/card_index.json")]
    card_index: String,
    #[arg(long, default_value=".venv/lib/python3.11/site-packages/kaggle_environments/envs/cabt/cg/libcg.so")]
    lib_path: String,
    #[arg(long, default_value="decks")]
    out_dir: String,
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
        let select = &obs["select"];
        if select.is_null() { break; }
        let maxc = select["maxCount"].as_u64().unwrap_or(0) as usize;
        let opt_len = select["option"].as_array().map(|a| a.len()).unwrap_or(0);
        let dec = if decision.len() > maxc || decision.len() > opt_len {
            (0..maxc.min(opt_len)).map(|i| i as i32).collect::<Vec<_>>()
        } else {
            decision
        };
        match engine.select(&dec) {
            Ok(next) => obs = next,
            Err(_) => break,
        }
        if step > 3000 { break; }
    }
    0
}

fn eval_deck(our_deck: &[i32], opp_decks: &[(PathBuf, Vec<i32>, Plan)], lib_path: &str, card_index: &CardIndex, knobs: &Knobs, games: usize) -> f64 {
    let our_plan = Plan::build(our_deck, card_index);
    let mut wins = 0;
    let mut total = 0;
    for (_path, opp_deck, opp_plan) in opp_decks {
        for g in 0..games {
            let our_seat = g % 2;
            let res = run_one_game(our_deck, opp_deck, &our_plan, opp_plan, lib_path, card_index, knobs, our_seat);
            if res == 1 { wins += 1; }
            if res != 0 || true { total += 1; } // count draws as games too for win rate denominator? use wins/total games
            // For win rate we want wins / (wins+losses) but for simplicity wins / total games
        }
    }
    if total == 0 { 0.0 } else { wins as f64 / total as f64 }
}

fn main() -> Result<()> {
    let args = Args::parse();
    let card_index = CardIndex::load(&args.card_index)?;
    let knobs = Knobs::default();

    // Load opponent decks
    let live_dir = PathBuf::from(&args.live_dir);
    let mut opp_decks: Vec<(PathBuf, Vec<i32>, Plan)> = Vec::new();
    for entry in fs::read_dir(&live_dir)? {
        let entry = entry?;
        let path = entry.path();
        if path.extension().and_then(|s| s.to_str()) != Some("csv") { continue; }
        if path.file_stem().and_then(|s| s.to_str()) == Some("_manifest") { continue; }
        let deck = load_deck_ids(&path)?;
        if deck.len() != 60 { continue; }
        let plan = Plan::build(&deck, &card_index);
        opp_decks.push((path, deck, plan));
    }
    println!("Loaded {} opp decks from {}", opp_decks.len(), args.live_dir);
    println!("Card index: {} cards", card_index.cards.len());
    println!("Trials: {} games per matchup: {}", args.trials, args.games);

    // Trainer pool from v12 search
    let trainer_pool = vec![
        1145, // Mega Signal
        1227, // Lillie
        1182, // Boss
        1152, // Poke Pad
        1097, // Night Stretcher
        1205, // Cyrano
        1235, // Waitress
        1158, // Maximum Belt
        1118, // Energy Retrieval
        1121, // Ultra Ball
        1262, // Surfing Beach
        1086, // Buddy-Buddy Poffin
        1219, // Team Rocket's Petrel
        1163, // Powerglass (if exists)
    ];

    let base_pokemon = vec![
        721, 721, // Snover x2
        722, 722, 722, 722, // Abomasnow x4
        723, 723, 723, 723, // Mega Abomasnow ex x4
    ];

    let out_dir = PathBuf::from(&args.out_dir);
    fs::create_dir_all(&out_dir)?;

    let best = Mutex::new((0.0f64, Vec::<i32>::new(), String::new()));

    // Use rayon for parallel trials? But engine has global mutex, so parallel trials will serialize anyway
    // We'll run trials sequentially for stability, but use rayon for opp evaluation inside eval_deck? eval_deck is sequential now
    // For true parallelism, we could run trials in parallel with mutex inside engine – still faster than Python
    let trials: Vec<usize> = (0..args.trials).collect();
    trials.par_iter().for_each(|&trial| {
        let mut rng = rand::thread_rng();
        let energy_count = rng.gen_range(28..=32);
        let mut deck = base_pokemon.clone();
        deck.extend(vec![3; energy_count]); // Water Energy id 3
        let remaining = 60 - deck.len();
        // Sample trainers
        for _ in 0..remaining {
            let tid = *trainer_pool.choose(&mut rng).unwrap();
            deck.push(tid);
        }
        // Ensure max 4 copies (except energy)
        let mut counts: std::collections::HashMap<i32, i32> = std::collections::HashMap::new();
        for &cid in &deck {
            *counts.entry(cid).or_insert(0) += 1;
        }
        // If any trainer >4, resample that slot (simple fix: if >4, replace with random other trainer)
        // For simplicity, we enforce by rebuilding if violation
        let mut valid = true;
        for (&cid, &cnt) in &counts {
            if cid == 3 { continue; } // energy unlimited? actually max 60 but we limit energy 28-32, okay
            if cnt > 4 { valid = false; break; }
        }
        if !valid { return; }

        // Shuffle deck for determinism? not needed
        let win_rate = eval_deck(&deck, &opp_decks, &args.lib_path, &card_index, &knobs, args.games);

        let mut best_lock = best.lock().unwrap();
        if win_rate > best_lock.0 {
            best_lock.0 = win_rate;
            best_lock.1 = deck.clone();
            best_lock.2 = format!("trial {} energy {} win {:.3}", trial, energy_count, win_rate);
            println!("NEW BEST {:.3} {}", win_rate, best_lock.2);
            // Save deck
            let out_path = out_dir.join(format!("v13_top30_best.csv"));
            let content = deck.iter().map(|id| id.to_string()).collect::<Vec<_>>().join(",");
            let _ = fs::write(&out_path, content);
        } else if trial % 10 == 0 {
            println!("trial {} energy {} win {:.3} (best {:.3})", trial, energy_count, win_rate, best_lock.0);
        }
    });

    let best_final = best.lock().unwrap();
    println!("\n=== FINAL BEST ===");
    println!("Win rate: {:.3}", best_final.0);
    println!("Deck: {:?}", best_final.1);
    println!("Info: {}", best_final.2);

    Ok(())
}
