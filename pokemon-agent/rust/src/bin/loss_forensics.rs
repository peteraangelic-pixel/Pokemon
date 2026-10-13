//! loss_forensics — deep per-turn analysis of Kaggle replay JSONs (Rust + Rayon).
//!
//! Input:  a directory of `episode-<id>-replay.json` files
//!         + optional episodes_table.csv (episode_id,sub,...) for sub attribution
//! Output: <outdir>/forensics.jsonl      (one line per episode, full metrics)
//!         <outdir>/forensics_summary.md (W-L by opp archetype, early losses, dmg delta)
//!
//! Built for the 2026-10-13 loss forensics: WHY did we lose (incl. to weaker
//! opponents)? Early collapses, KO races, stalls, damage-rate gaps.

use anyhow::Result;
use clap::Parser;
use rayon::prelude::*;
use serde::Serialize;
use serde_json::Value;
use std::collections::BTreeMap;
use std::fs;
use std::path::Path;

#[derive(Parser)]
#[command(name = "loss_forensics", about = "Per-turn replay forensics (Rust+Rayon)")]
struct Args {
    /// Directory containing episode-*-replay.json files
    #[arg(long)]
    replays: String,
    /// Output directory (forensics.jsonl + forensics_summary.md)
    #[arg(long)]
    outdir: String,
    /// episodes_table.csv for episode_id -> sub mapping (optional)
    #[arg(long, default_value = "")]
    table: String,
}

const DECK_TAGS: &[(&str, &[u32])] = &[
    ("KYOGRE", &[721, 723]),
    ("LUCARIO", &[566, 567]),
    ("LUCARIO_ALT", &[678, 679]),
    ("DRAGAPULT", &[1057, 1058, 1059, 1060]),
    ("LATIAS", &[50, 51]),
    ("MEOWTH", &[107]),
    ("FEZANDIPITY", &[123, 124]),
    ("STARMIE", &[130, 131]),
    ("LUNATONE", &[318, 319]),
    ("KYUREM", &[144]),
    ("CONKELDURR", &[115]),
    ("OGERPON", &[1023, 1024, 1025, 1026]),
    ("SOLROCK", &[317]),
    ("DUNSPARCE", &[589]),
    ("MUNKIDORI", &[914]),
];

fn arch(ids: &[u32]) -> String {
    let mut tags: Vec<&str> = Vec::new();
    for (tag, cards) in DECK_TAGS {
        if ids.iter().any(|c| cards.contains(c)) {
            tags.push(tag);
        }
    }
    if tags.is_empty() {
        "?".to_string()
    } else {
        tags.join("+")
    }
}

#[derive(Serialize)]
struct TurnRow {
    turn: u32,
    our_active: Option<u32>,
    our_active_hp: i64,
    our_bench: usize,
    opp_active: Option<u32>,
    opp_active_hp: i64,
    opp_bench: usize,
    dmg_dealt: i64,
    dmg_taken: i64,
    ko_dealt: usize,
    ko_taken: usize,
    we_retreated: bool,
}

#[derive(Serialize)]
struct Ep {
    episode_id: String,
    sub: String,
    win: bool,
    turn: u32,
    our_arch: String,
    opp_arch: String,
    opp_name: String,
    ko_we: usize,
    ko_opp: usize,
    total_dealt: i64,
    total_taken: i64,
    dmg_per_turn_dealt: f64,
    dmg_per_turn_taken: f64,
    early_loss: bool,
    loss_class: String,
    turns: Vec<TurnRow>,
}

fn get_u32(v: &Value, key: &str) -> Option<u32> {
    v.get(key).and_then(|x| x.as_u64()).map(|x| x as u32)
}
fn get_i64(v: &Value, key: &str) -> i64 {
    v.get(key).and_then(|x| x.as_i64()).unwrap_or(0)
}
fn get_us(v: &Value, key: &str) -> usize {
    v.get(key).and_then(|x| x.as_u64()).map(|x| x as usize).unwrap_or(0)
}

fn analyze(path: &Path) -> Option<Ep> {
    let raw = fs::read_to_string(path).ok()?;
    let d: Value = serde_json::from_str(&raw).ok()?;
    let info = d.get("info")?;
    let teams: Vec<String> = info
        .get("TeamNames")?
        .as_array()?
        .iter()
        .map(|x| x.as_str().unwrap_or("?").to_string())
        .collect();
    let our_idx = match teams.iter().position(|t| t.contains("PeterSharps")) {
        Some(i) => i,
        None => return None,
    };
    let opp_idx = 1 - our_idx;
    let rewards = d.get("rewards")?;
    let win = rewards
        .get(our_idx)
        .and_then(|x| x.as_i64())
        .map(|x| x == 1)
        .unwrap_or(false);
    let steps: &Vec<Value> = d.get("steps")?.as_array()?;

    let mut serial_map: [BTreeMap<u32, u32>; 2] = [BTreeMap::new(), BTreeMap::new()];
    let mut prev_active: [Option<(u32, i64)>; 2] = [None, None];
    let mut ko_we = 0usize;
    let mut ko_opp = 0usize;
    let mut turns: Vec<TurnRow> = Vec::new();
    let mut last_seen_turn: u32 = 0;
    let mut cur_turn: u32 = 0;
    // per-turn accumulators
    let mut turn_dmg_dealt = 0i64;
    let mut turn_dmg_taken = 0i64;
    let mut turn_ko_dealt = 0usize;
    let mut turn_ko_taken = 0usize;
    let mut we_retreated = false;

    let mut pending = None; // Option<TurnRow> for the turn in progress
    for step in steps {
        let step_arr = match step.as_array() {
            Some(a) => a,
            None => continue,
        };
        for (ai, ag) in step_arr.iter().enumerate() {
            let o = match ag.get("observation") {
                Some(x) if x.is_object() => x,
                _ => continue,
            };
            let cur = match o.get("current") {
                Some(x) if x.is_object() => x,
                _ => continue,
            };
            let turn = match get_u32(cur, "turn") {
                Some(t) if t > 0 => t,
                _ => continue,
            };
            let players = match cur.get("players").and_then(|x| x.as_array()) {
                Some(p) if p.len() == 2 => p,
                _ => continue,
            };

            // collect serials from logs (deck reconstruction)
            if let Some(logs) = o.get("logs").and_then(|x| x.as_array()) {
                for e in logs {
                    if let (Some(pi), Some(ser), Some(cid)) = (
                        e.get("playerIndex").and_then(|x| x.as_i64()),
                        e.get("serial").and_then(|x| x.as_u64()),
                        e.get("cardId").and_then(|x| x.as_u64()),
                    ) {
                        if (0..2).contains(&(pi as i64)) {
                            serial_map[pi as usize].insert(ser as u32, cid as u32);
                        }
                    }
                }
            }

            let read_active = |p: &Value| -> Option<(u32, i64, i64)> {
                let a = p.get("active")?.as_array()?.first()?;
                let id = get_u32(a, "id")?;
                Some((id, get_i64(a, "hp"), get_i64(a, "maxHp")))
            };
            let bench_len = |p: &Value| -> usize {
                p.get("bench").and_then(|x| x.as_array()).map(|x| x.len()).unwrap_or(0)
            };

            let a0 = read_active(&players[0]);
            let a1 = read_active(&players[1]);
            let b0 = bench_len(&players[0]);
            let b1 = bench_len(&players[1]);
            let actives: [Option<(u32, i64, i64)>; 2] = [a0, a1];
            let benches: [usize; 2] = [b0, b1];

            if turn != cur_turn {
                // flush the previous turn row
                if let Some(mut row) = pending.take() {
                    row.dmg_dealt = turn_dmg_dealt;
                    row.dmg_taken = turn_dmg_taken;
                    row.ko_dealt = turn_ko_dealt;
                    row.ko_taken = turn_ko_taken;
                    row.we_retreated = we_retreated;
                    turns.push(row);
                }
                cur_turn = turn;
                turn_dmg_dealt = 0;
                turn_dmg_taken = 0;
                turn_ko_dealt = 0;
                turn_ko_taken = 0;
                we_retreated = false;
                pending = Some(TurnRow {
                    turn,
                    our_active: actives[our_idx].map(|(i, _, _)| i),
                    our_active_hp: actives[our_idx].map(|(_, h, _)| h).unwrap_or(-1),
                    our_bench: benches[our_idx],
                    opp_active: actives[opp_idx].map(|(i, _, _)| i),
                    opp_active_hp: actives[opp_idx].map(|(_, h, _)| h).unwrap_or(-1),
                    opp_bench: benches[opp_idx],
                    dmg_dealt: 0,
                    dmg_taken: 0,
                    ko_dealt: 0,
                    ko_taken: 0,
                    we_retreated: false,
                });
                last_seen_turn = turn;
            } else if let Some(row) = pending.as_mut() {
                row.our_bench = benches[our_idx];
                row.opp_bench = benches[opp_idx];
            }

            // KOs + retreats: compare with prev_active
            for i in 0..2 {
                let new_a = actives[i].map(|(id, hp, _)| (id, hp));
                let old_a = prev_active[i];
                match (old_a, new_a) {
                    (Some((oid, ohp)), Some((nid, _))) if oid != nid => {
                        if ohp == 0 {
                            // KO
                            if i == opp_idx {
                                ko_we += 1;
                                turn_ko_dealt += 1;
                            } else {
                                ko_opp += 1;
                                turn_ko_taken += 1;
                            }
                        } else {
                            if i == our_idx {
                                we_retreated = true;
                            }
                        }
                    }
                    (Some((_, ohp)), None) if ohp == 0 => {
                        if i == opp_idx {
                            ko_we += 1;
                            turn_ko_dealt += 1;
                        } else {
                            ko_opp += 1;
                            turn_ko_taken += 1;
                        }
                    }
                    _ => {}
                }
                if let Some((_, hp, _mhp)) = actives[i] {
                    // damage delta vs previous observation on same card
                    if let Some((_, ph)) = prev_active[i] {
                        if let Some((id2, _)) = new_a {
                            let old_id = old_a.map(|(x, _)| x);
                            if old_id == Some(id2) {
                                let d = ph - hp;
                                if d > 0 {
                                    if i == opp_idx {
                                        turn_dmg_dealt += d;
                                    } else {
                                        turn_dmg_taken += d;
                                    }
                                }
                            }
                        }
                    }
                }
                prev_active[i] = new_a;
            }
        }
    }
    if let Some(mut row) = pending.take() {
        row.dmg_dealt = turn_dmg_dealt;
        row.dmg_taken = turn_dmg_taken;
        row.ko_dealt = turn_ko_dealt;
        row.ko_taken = turn_ko_taken;
        row.we_retreated = we_retreated;
        turns.push(row);
    }

    let our_deck: Vec<u32> = serial_map[our_idx].values().copied().collect::<BTreeSet2>().into_iter().collect();
    let opp_deck: Vec<u32> = serial_map[opp_idx].values().copied().collect::<BTreeSet2>().into_iter().collect();
    let total_dealt: i64 = turns.iter().map(|t| t.dmg_dealt).sum();
    let total_taken: i64 = turns.iter().map(|t| t.dmg_taken).sum();
    let n = turns.len().max(1) as f64;
    let loss_class = if win {
        String::new()
    } else if last_seen_turn <= 10 {
        "EARLY_COLLAPSE".to_string()
    } else if ko_we < ko_opp {
        "KO_RACE_LOST".to_string()
    } else if total_taken > total_dealt {
        "DAMAGE_RACE_LOST".to_string()
    } else {
        "OTHER".to_string()
    };

    Some(Ep {
        episode_id: path
            .file_name()?
            .to_str()?
            .replace("episode-", "")
            .replace("-replay.json", ""),
        sub: String::new(),
        win,
        turn: last_seen_turn,
        our_arch: arch(&our_deck),
        opp_arch: arch(&opp_deck),
        opp_name: teams.get(opp_idx).cloned().unwrap_or_default(),
        ko_we,
        ko_opp,
        total_dealt,
        total_taken,
        dmg_per_turn_dealt: total_dealt as f64 / n,
        dmg_per_turn_taken: total_taken as f64 / n,
        early_loss: !win && last_seen_turn <= 10,
        loss_class,
        turns,
    })
}

type BTreeSet2 = std::collections::BTreeSet<u32>;

fn main() -> Result<()> {
    let args = Args::parse();
    let outdir = Path::new(&args.outdir);
    fs::create_dir_all(outdir)?;

    let sub_map: BTreeMap<String, String> = if !args.table.is_empty() {
        let mut m = BTreeMap::new();
        if let Ok(content) = fs::read_to_string(&args.table) {
            for line in content.lines().skip(1) {
                let mut it = line.split(',');
                if let (Some(id), Some(sub)) = (it.next(), it.next()) {
                    m.insert(id.trim().to_string(), sub.trim().to_string());
                }
            }
        }
        m
    } else {
        BTreeMap::new()
    };

    let files: Vec<std::path::PathBuf> = fs::read_dir(&args.replays)?
        .filter_map(|e| e.ok())
        .map(|e| e.path())
        .filter(|p| {
            p.file_name()
                .map(|n| n.to_string_lossy().contains("replay.json"))
                .unwrap_or(false)
        })
        .collect();

    let episodes: Vec<Option<Ep>> = files
        .par_iter()
        .map(|f| analyze(f))
        .collect();
    let mut eps: Vec<Ep> = episodes.into_iter().flatten().collect();
    for e in eps.iter_mut() {
        e.sub = sub_map
            .get(&e.episode_id)
            .cloned()
            .unwrap_or_else(|| "?".to_string());
    }
    eps.sort_by(|a, b| a.episode_id.cmp(&b.episode_id));

    // jsonl
    let jl = outdir.join("forensics.jsonl");
    let mut out = String::new();
    for e in &eps {
        out.push_str(&serde_json::to_string(e)?);
        out.push('\n');
    }
    fs::write(&jl, out)?;

    // summary
    let mut md = String::from("# Loss forensics (Rust+Rayon)\n\n");
    let wins = eps.iter().filter(|e| e.win).count();
    md.push_str(&format!(
        "- Episodes: {} (wins {}, losses {})\n\n",
        eps.len(),
        wins,
        eps.len() - wins
    ));

    // W-L by (sub, opp_arch)
    md.push_str("## W-L by sub × opp archetype\n\n");
    md.push_str("| sub | opp_arch | W | L | W% | avg turn (L) | avg dmg/t taken (L) | early losses |\n");
    md.push_str("|---|---|---|---|---|---|---|---|\n");
    let mut agg: BTreeMap<(String, String), (usize, usize, f64, f64, usize)> = BTreeMap::new();
    for e in &eps {
        let a = agg
            .entry((e.sub.clone(), e.opp_arch.clone()))
            .or_insert((0, 0, 0.0, 0.0, 0));
        if e.win {
            a.0 += 1;
        } else {
            a.1 += 1;
            a.2 += e.turn as f64;
            a.3 += e.dmg_per_turn_taken;
            a.4 += if e.early_loss { 1 } else { 0 };
        }
    }
    for ((sub, arch), (w, l, tsum, dsum, el)) in &agg {
        let n = w + l;
        md.push_str(&format!(
            "| {} | {} | {} | {} | {:.0}% | {:.1} | {:.0} | {} |\n",
            sub,
            arch,
            w,
            l,
            100.0 * f64::from(*w) / f64::from(*n),
            if *l > 0 { tsum / *l as f64 } else { 0.0 },
            if *l > 0 { dsum / *l as f64 } else { 0.0 },
            el
        ));
    }

    // loss classes
    md.push_str("\n## Loss classes\n\n");
    let mut cls: BTreeMap<String, usize> = BTreeMap::new();
    for e in eps.iter().filter(|e| !e.win) {
        *cls.entry(e.loss_class.clone()).or_insert(0) += 1;
    }
    for (c, n) in &cls {
        md.push_str(&format!("- {}: {}\n", c, n));
    }

    // per-episode table (losses only, with turn trace summary)
    md.push_str("\n## Losses (per episode)\n\n");
    md.push_str("| ep | sub | opp | arch | turn | KO we/opp | dmg/t dealt/taken | class |\n");
    md.push_str("|---|---|---|---|---|---|---|---|\n");
    for e in eps.iter().filter(|e| !e.win) {
        md.push_str(&format!(
            "| {} | {} | {} | {} | {} | {}/{} | {:.0}/{:.0} | {} |\n",
            e.episode_id,
            e.sub,
            e.opp_name,
            e.opp_arch,
            e.turn,
            e.ko_we,
            e.ko_opp,
            e.dmg_per_turn_dealt,
            e.dmg_per_turn_taken,
            e.loss_class
        ));
    }

    // early-loss detail: turn trace of first 10 turns
    md.push_str("\n## Early losses — turn traces\n\n");
    for e in eps.iter().filter(|e| e.early_loss) {
        md.push_str(&format!(
            "\n### {} vs {} ({}): turn {} collapse\n",
            e.episode_id, e.opp_name, e.opp_arch, e.turn
        ));
        md.push_str("| turn | our act (hp) | our bench | opp act (hp) | opp bench | dealt | taken | KO d/t | ret |\n");
        md.push_str("|---|---|---|---|---|---|---|---|---|\n");
        for t in e.turns.iter().take(12) {
            md.push_str(&format!(
                "| {} | {} ({}) | {} | {} ({}) | {} | {} | {} | {}/{} | {} |\n",
                t.turn,
                t.our_active.map(|x| x).unwrap_or(0),
                t.our_active_hp,
                t.our_bench,
                t.opp_active.map(|x| x).unwrap_or(0),
                t.opp_active_hp,
                t.opp_bench,
                t.dmg_dealt,
                t.dmg_taken,
                t.ko_dealt,
                t.ko_taken,
                if t.we_retreated { "R" } else { "" }
            ));
        }
    }

    fs::write(outdir.join("forensics_summary.md"), &md)?;
    println!(
        "loss_forensics: {} episodes -> {} + forensics_summary.md",
        eps.len(),
        jl.display()
    );
    Ok(())
}
