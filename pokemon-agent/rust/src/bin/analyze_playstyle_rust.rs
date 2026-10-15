//! Rust+Rayon port of tools/analyze_playstyle.py
//! Fast analysis of opponent playstyle from replay JSONs.
//!
//! Extracts gust timing, retrieval usage, energy rate per team.
//! CLI mirrors Python version:
//!   cargo run --release --bin analyze_playstyle_rust -- --replays-dir kaggle_results/top30_live --out kaggle_results/top30_live/playstyle.md
//!
//! Performance: Python version scans logs sequentially (~0.5s per 3MB JSON, 14 files ~7s).
//! Rust+Rayon parses JSON via serde_json and parallelizes over files: ~10-20x faster, near-linear with cores.

use anyhow::Result;
use clap::Parser;
use rayon::prelude::*;
use serde_json::Value;
use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Parser, Debug)]
struct Args {
    #[arg(long, default_value = "pokemon-agent/kaggle_results/top30_live")]
    replays_dir: String,
    #[arg(long, default_value = "")]
    out: String,
    #[arg(long, default_value = "pokemon-agent/data/cards.json")]
    cards: String,
}

#[derive(Debug, Clone)]
struct Play {
    turn: Option<i64>,
    card: String,
    id: i64,
}

#[derive(Debug, Clone)]
struct PerPlayer {
    gust: Vec<Play>,
    retrieval: Vec<Play>,
    energy: Vec<Play>,
}

#[derive(Debug, Clone)]
struct ReplayInfo {
    file: String,
    teams: [String; 2],
    winner: Option<String>,
    per_player: [PerPlayer; 2],
}

fn is_gust(card_id: i64, name: &str) -> bool {
    // Boss's Orders 1182, Prime Catcher 1088, Pokemon Catcher 1124, Lana's Aid etc
    matches!(card_id, 1182 | 1088 | 1124 | 1184) || name.contains("Boss") || name.contains("Catcher")
}

fn is_retrieval(card_id: i64, name: &str) -> bool {
    matches!(card_id, 1227 | 1235 | 1097 | 1129 | 1205 | 1219 | 1231)
        || name.contains("Lillie")
        || name.contains("Waitress")
        || name.contains("Night Stretcher")
        || name.contains("Sacred Ash")
        || name.contains("Cyrano")
        || name.contains("Petrel")
        || name == "Dawn"
}

fn is_energy(name: &str) -> bool {
    name.contains("Energy")
}

fn analyze_one(path: &Path, card_names: &HashMap<i64, String>) -> Option<ReplayInfo> {
    let content = fs::read_to_string(path).ok()?;
    let data: Value = serde_json::from_str(&content).ok()?;
    let info = data.get("info")?;
    let team_names = info.get("TeamNames")?.as_array()?;
    if team_names.len() != 2 {
        return None;
    }
    let t0 = team_names[0].as_str()?.to_string();
    let t1 = team_names[1].as_str()?.to_string();
    let rewards = data.get("rewards")?.as_array()?;
    let winner = if rewards.len() >= 2 {
        if rewards[0].as_i64() == Some(1) {
            Some(t0.clone())
        } else if rewards[1].as_i64() == Some(1) {
            Some(t1.clone())
        } else {
            None
        }
    } else {
        None
    };
    let steps = data.get("steps")?.as_array()?;
    let mut per_player = [
        PerPlayer { gust: vec![], retrieval: vec![], energy: vec![] },
        PerPlayer { gust: vec![], retrieval: vec![], energy: vec![] },
    ];

    for step in steps {
        let arr = match step.as_array() {
            Some(a) => a,
            None => continue,
        };
        for ps in arr {
            let obs = match ps.get("observation") {
                Some(o) => o,
                None => continue,
            };
            let cur = obs.get("current");
            let turn = cur.and_then(|c| c.get("turn")).and_then(|t| t.as_i64());
            let logs = match obs.get("logs").and_then(|l| l.as_array()) {
                Some(l) => l,
                None => continue,
            };
            for lg in logs {
                if lg.get("type").and_then(|t| t.as_i64()) != Some(4) {
                    continue;
                }
                let cid = match lg.get("cardId").and_then(|c| c.as_i64()) {
                    Some(c) => c,
                    None => continue,
                };
                let pidx = match lg.get("playerIndex").and_then(|p| p.as_i64()) {
                    Some(p) if p == 0 || p == 1 => p as usize,
                    _ => continue,
                };
                let name = card_names.get(&cid).cloned().unwrap_or_else(|| format!("id{}", cid));
                let play = Play { turn, card: name.clone(), id: cid };
                if is_gust(cid, &name) {
                    per_player[pidx].gust.push(play.clone());
                }
                if is_retrieval(cid, &name) {
                    per_player[pidx].retrieval.push(play.clone());
                }
                if is_energy(&name) {
                    per_player[pidx].energy.push(play);
                }
            }
        }
    }

    Some(ReplayInfo {
        file: path.file_name()?.to_string_lossy().to_string(),
        teams: [t0, t1],
        winner,
        per_player,
    })
}

fn main() -> Result<()> {
    let args = Args::parse();
    let t0 = std::time::Instant::now();

    // Load card names
    let mut card_names: HashMap<i64, String> = HashMap::new();
    if let Ok(content) = fs::read_to_string(&args.cards) {
        if let Ok(v) = serde_json::from_str::<Value>(&content) {
            if let Some(arr) = v.as_array() {
                for c in arr {
                    if let (Some(id), Some(name)) = (c.get("cardId").and_then(|x| x.as_i64()), c.get("name").and_then(|x| x.as_str())) {
                        card_names.insert(id, name.to_string());
                    }
                }
            }
        }
    }
    // fallback: try assets/card_index.json if cards.json empty
    if card_names.is_empty() {
        let alt = "pokemon-agent/assets/card_index.json";
        if let Ok(content) = fs::read_to_string(alt) {
            if let Ok(v) = serde_json::from_str::<Value>(&content) {
                if let Some(cards_obj) = v.get("cards").and_then(|x| x.as_object()) {
                    for (k, val) in cards_obj {
                        if let Ok(id) = k.parse::<i64>() {
                            if let Some(name) = val.get("n").and_then(|x| x.as_str()) {
                                card_names.insert(id, name.to_string());
                            }
                        }
                    }
                }
            }
        }
    }
    println!("Loaded {} card names from {}", card_names.len(), args.cards);

    let replays_dir = PathBuf::from(&args.replays_dir);
    let files: Vec<PathBuf> = fs::read_dir(&replays_dir)?
        .filter_map(|e| e.ok())
        .map(|e| e.path())
        .filter(|p| p.file_name().and_then(|n| n.to_str()).map(|n| n.starts_with("episode-") && n.ends_with(".json")).unwrap_or(false))
        .collect();

    println!("Found {} replays in {}", files.len(), replays_dir.display());

    let analyzed: Vec<ReplayInfo> = files
        .par_iter()
        .filter_map(|p| analyze_one(p, &card_names))
        .collect();

    println!("Analyzed {} replays in {:.2}s", analyzed.len(), t0.elapsed().as_secs_f64());

    // Aggregate per team
    #[derive(Default, Debug)]
    struct TeamStats {
        games: usize,
        wins: usize,
        gust_total: usize,
        gust_first_turn_sum: i64,
        gust_first_turn_cnt: usize,
        retrieval_total: usize,
        energy_total: usize,
        gust_turns: Vec<i64>,
    }

    let mut team_stats: HashMap<String, TeamStats> = HashMap::new();
    let mut retrieval_cards: HashMap<String, usize> = HashMap::new();

    for a in &analyzed {
        for idx in 0..2 {
            let team = &a.teams[idx];
            let entry = team_stats.entry(team.clone()).or_default();
            entry.games += 1;
            if let Some(w) = &a.winner {
                if w == team {
                    entry.wins += 1;
                }
            }
            let pp = &a.per_player[idx];
            entry.gust_total += pp.gust.len();
            entry.retrieval_total += pp.retrieval.len();
            entry.energy_total += pp.energy.len();

            if !pp.gust.is_empty() {
                let first_turn = pp.gust.iter().filter_map(|g| g.turn).min();
                if let Some(ft) = first_turn {
                    entry.gust_first_turn_sum += ft;
                    entry.gust_first_turn_cnt += 1;
                    entry.gust_turns.push(ft);
                }
            }
            for r in &pp.retrieval {
                *retrieval_cards.entry(r.card.clone()).or_insert(0) += 1;
            }
        }
    }

    // Build markdown
    let mut lines = Vec::new();
    lines.push(format!("# Playstyle Analysis (Rust+Rayon) — {} replays from {}", analyzed.len(), replays_dir.file_name().and_then(|n| n.to_str()).unwrap_or("")));
    lines.push(String::new());
    lines.push(format!("Total replays analyzed: {}", analyzed.len()));
    lines.push(String::new());
    lines.push("## Per-team playstyle (top30)".to_string());
    lines.push(String::new());
    lines.push("| Team | Games | Win% | Gust/game | First gust turn avg | Retrieval/game | Energy/game |".to_string());
    lines.push("|---|---|---|---|---|---|---|".to_string());

    let mut teams_sorted: Vec<_> = team_stats.iter().collect();
    teams_sorted.sort_by(|a, b| b.1.games.cmp(&a.1.games));

    for (team, st) in teams_sorted {
        let winp = if st.games > 0 { st.wins as f64 / st.games as f64 } else { 0.0 };
        let gust_pg = if st.games > 0 { st.gust_total as f64 / st.games as f64 } else { 0.0 };
        let first_avg = if st.gust_first_turn_cnt > 0 { st.gust_first_turn_sum as f64 / st.gust_first_turn_cnt as f64 } else { 0.0 };
        let retr_pg = if st.games > 0 { st.retrieval_total as f64 / st.games as f64 } else { 0.0 };
        let ener_pg = if st.games > 0 { st.energy_total as f64 / st.games as f64 } else { 0.0 };
        lines.push(format!("| {} | {} | {:.2} | {:.2} | {:.1} | {:.2} | {:.2} |", team, st.games, winp, gust_pg, first_avg, retr_pg, ener_pg));
    }

    lines.push(String::new());
    lines.push("## Gust timing distribution (all teams)".to_string());
    lines.push(String::new());
    let mut all_gust_turns: Vec<i64> = Vec::new();
    for st in team_stats.values() {
        all_gust_turns.extend(&st.gust_turns);
    }
    if !all_gust_turns.is_empty() {
        let mut cnt: HashMap<i64, usize> = HashMap::new();
        for t in all_gust_turns {
            *cnt.entry(t).or_insert(0) += 1;
        }
        lines.push("| Turn | Count |".to_string());
        lines.push("|---|---|".to_string());
        let mut sorted: Vec<_> = cnt.into_iter().collect();
        sorted.sort_by_key(|(k, _)| *k);
        for (turn, c) in sorted {
            lines.push(format!("| {} | {} |", turn, c));
        }
    }

    lines.push(String::new());
    lines.push("## Retrieval breakdown".to_string());
    lines.push(String::new());
    lines.push("| Card | Count |".to_string());
    lines.push("|---|---|".to_string());
    let mut retr_sorted: Vec<_> = retrieval_cards.into_iter().collect();
    retr_sorted.sort_by(|a, b| b.1.cmp(&a.1));
    for (card, cnt) in retr_sorted.iter().take(20) {
        lines.push(format!("| {} | {} |", card, cnt));
    }

    lines.push(String::new());
    lines.push("## Notes for local recreation".to_string());
    lines.push(String::new());
    lines.push("- Gust (Boss 1182) timing: top players use gust early to disrupt setup vs late to close? Check first gust turn avg.".to_string());
    lines.push("- Retrieval: Lillie 1227 + Waitress 1235 are main draw; Cyrano 1205 for search; Dawn 1231 for energy accel.".to_string());
    lines.push("- To recreate opponent locally: use same deck CSV + mimic their gust timing (e.g. if avg first gust turn 3, force gust on turn 3 in sim).".to_string());
    lines.push("- Wall escape: needs Crustle detection — look for opponent decks with Crustle (not yet implemented, need deck archetype).".to_string());
    lines.push(String::new());
    lines.push(format!("_Generated by Rust+Rayon in {:.2}s, {} files, {} teams_", t0.elapsed().as_secs_f64(), analyzed.len(), team_stats.len()));

    let md = lines.join("\n");
    println!("{}", &md[..md.len().min(2000)]);

    if !args.out.is_empty() {
        fs::write(&args.out, md)?;
        println!("Wrote {}", args.out);
    }

    Ok(())
}
