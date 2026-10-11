//! Native rayon gauntlet: our deck vs every deck in --opp-dir, on libcg.so.
//!
//! CLI mirrors `tools/gauntlet_ffi.py` so results are directly comparable:
//!
//!   cargo run --release --bin gauntlet_native -- \
//!       --our-deck decks/v10_34_sig4.csv --opp-dir decks/top30_live \
//!       --games 8 --jobs 8
//!
//! Policy is `heuristic::decide` — i.e. the NATIVE heuristic. Until that is a
//! faithful port of `agents/best_from_search.py` (see rust/PORTING.md),
//! results from this binary are NOT the real policy's results; the acceptance
//! gate in PORTING.md §5 must pass before any number from it is trusted.

use anyhow::Result;
use clap::Parser;
use rayon::prelude::*;
use std::fs;
use std::path::{Path, PathBuf};

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
    #[arg(long, default_value = "decks/v10_34_sig4.csv")]
    our_deck: String,
    #[arg(long, default_value = "decks/top30_live")]
    opp_dir: String,
    #[arg(long, default_value_t = 8)]
    games: usize,
    /// rayon pool size (0 = all cores)
    #[arg(long, default_value_t = 0)]
    jobs: usize,
    /// comma-separated substring filter on opponent deck names
    #[arg(long, default_value = "")]
    only: String,
    #[arg(long, default_value = ".venv/lib/python3.11/site-packages/kaggle_environments/envs/cabt/cg/libcg.so")]
    lib_path: String,
    #[arg(long, default_value = "assets/card_index.json")]
    card_index: String,
}

fn load_deck(path: &Path) -> Result<Vec<i32>> {
    let content = fs::read_to_string(path)?;
    let mut ids = Vec::new();
    for tok in content.split(|c: char| c == ',' || c.is_whitespace()) {
        let t = tok.trim();
        if t.is_empty() {
            continue;
        }
        if let Ok(id) = t.parse::<i32>() {
            ids.push(id);
        }
    }
    if ids.len() != 60 {
        anyhow::bail!("{} has {} cards, need 60", path.display(), ids.len());
    }
    Ok(ids)
}

/// One game. Returns 1 win / -1 loss / 0 draw from OUR perspective (our_seat).
fn play_game(
    our_seat: usize,
    our_deck: &[i32],
    opp_deck: &[i32],
    lib_path: &str,
    index: &CardIndex,
    knobs: &Knobs,
) -> Result<i32> {
    let (d0, d1) = if our_seat == 0 {
        (our_deck, opp_deck)
    } else {
        (opp_deck, our_deck)
    };
    // NOTE: both decks are given to BattleStart; there is NO deck-submission
    // Select (verified against tools/gauntlet_ffi.py, which drives the same
    // libcg.so and runs clean games).
    let mut eng = Engine::new(lib_path)?;
    let mut obs = eng.battle_start(d0, d1)?;

    let mut steps = 0;
    loop {
        steps += 1;
        if steps > 5000 {
            eng.battle_finish();
            return Ok(0);
        }
        let cur = &obs["current"];
        if let Some(res) = cur["result"].as_i64() {
            eng.battle_finish();
            return Ok(if res == 2 { 0 } else if (res as usize) == our_seat { 1 } else { -1 });
        }
        if obs.get("select").is_none() {
            eng.battle_finish();
            return Ok(0);
        }
        // decide() expects the full obs value (reads obs["current"] + obs["select"]).
        let dec = heuristic::decide(&obs, index, knobs);
        if dec.is_empty() {
            eng.battle_finish();
            return Ok(0);
        }
        obs = eng.select(&dec)?;
    }
}

fn main() -> Result<()> {
    let args = Args::parse();
    let t0 = std::time::Instant::now();
    let index = CardIndex::load(&args.card_index)?;
    let knobs = Knobs::default();
    let our_deck = load_deck(Path::new(&args.our_deck))?;

    let opp_dir = PathBuf::from(&args.opp_dir);
    let mut names: Vec<String> = fs::read_dir(&opp_dir)?
        .filter_map(|e| e.ok())
        .map(|e| e.file_name().to_string_lossy().to_string())
        .filter(|f| f.ends_with(".csv"))
        .map(|f| f.trim_end_matches(".csv").to_string())
        .filter(|f| !f.starts_with('_'))
        .collect();
    if !args.only.is_empty() {
        let want: Vec<String> = args.only.split(',').map(|s| s.trim().to_string()).filter(|s| !s.is_empty()).collect();
        names.retain(|n| want.iter().any(|w| n.contains(w.as_str())));
    }
    names.sort();
    if names.is_empty() {
        anyhow::bail!("no opponent decks in {}", opp_dir.display());
    }

    let opp_decks: Vec<Option<Vec<i32>>> = names
        .par_iter()
        .map(|n| {
            let p = opp_dir.join(format!("{}.csv", n));
            load_deck(&p).ok()
        })
        .collect();

    if args.jobs > 0 {
        rayon::ThreadPoolBuilder::new().num_threads(args.jobs).build_global()
            .expect("rayon pool");
    }

    let lib = args.lib_path.clone();
    let results: Vec<(String, usize, usize, usize)> = names
        .par_iter()
        .zip(opp_decks.par_iter())
        .filter_map(|(name, od)| match od {
            Some(opp_deck) => {
                let (mut w, mut l, mut d) = (0usize, 0usize, 0usize);
                for g in 0..args.games {
                    let seat = g % 2;
                    match play_game(seat, &our_deck, opp_deck, &lib, &index, &knobs) {
                        Ok(1) => w += 1,
                        Ok(-1) => l += 1,
                        _ => d += 1,
                    }
                }
                Some((name.clone(), w, l, d))
            }
            None => {
                eprintln!("skip {}: not a 60-card deck", name);
                None
            }
        })
        .collect();

    let mut rows: Vec<(f64, usize, usize, usize, String)> = results
        .into_iter()
        .map(|(n, w, l, d)| (if w + l + d > 0 { w as f64 / (w + l + d) as f64 } else { 0.0 }, w, l, d, n))
        .collect();
    rows.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap_or(std::cmp::Ordering::Equal));

    let tw: usize = rows.iter().map(|r| r.1).sum();
    let tl: usize = rows.iter().map(|r| r.2).sum();
    let td: usize = rows.iter().map(|r| r.3).sum();
    for (rate, w, l, d, name) in &rows {
        println!("{:42} {:2}-{:2}-{:2}  {:.3}", name, w, l, d, rate);
    }
    let n = tw + tl + td;
    println!("\nTOTAL {}W-{}L-{}D = {:.3}  ({} decks x {} games, {:.0}s)",
        tw, tl, td, if n > 0 { tw as f64 / n as f64 } else { 0.0 },
        rows.len(), args.games, t0.elapsed().as_secs_f64());
    println!("worst 5:");
    for (rate, w, l, d, name) in rows.iter().rev().take(5) {
        println!("  {:42} {}-{}-{}  {:.3}", name, w, l, d, rate);
    }
    Ok(())
}
