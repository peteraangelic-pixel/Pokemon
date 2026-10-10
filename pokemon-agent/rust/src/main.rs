use clap::Parser;
use rayon::prelude::*;
use std::path::{PathBuf, Path};
use std::process::Command;
use std::fs;
use anyhow::{Result, Context};

#[derive(Parser, Debug)]
#[command(name="rust_gauntlet", about="Parallel gauntlet using Rayon")]
struct Args {
    #[arg(long, default_value="decks/v2_boss.csv")]
    our_deck: String,

    #[arg(long, default_value="agents/main_heuristic.py")]
    agent: String,

    #[arg(long, default_value="decks/top7_live")]
    live_dir: String,

    #[arg(long, default_value_t=2)]
    games: usize,

    #[arg(long, default_value_t=0)]
    jobs: usize,

    #[arg(long)]
    only: Option<String>,

    #[arg(long, default_value="false")]
    include_archetypes: bool,
}

#[derive(Debug, serde::Serialize, serde::Deserialize)]
struct MatchResult {
    name: String,
    rate: f64,
    wins: usize,
    losses: usize,
    draws: usize,
}

fn load_deck_ids(path: &Path) -> Result<Vec<i32>> {
    let content = fs::read_to_string(path).with_context(|| format!("read {:?}", path))?;
    let mut ids = Vec::new();
    for token in content.split(|c: char| c==',' || c.is_whitespace()) {
        if token.trim().is_empty() { continue; }
        if let Ok(id) = token.trim().parse::<i32>() {
            ids.push(id);
        }
    }
    Ok(ids)
}

fn run_single_match(our_deck: &str, opp_path: &Path, agent: &str, games: usize) -> Result<MatchResult> {
    // Call python gauntlet for single deck via --only
    let stem = opp_path.file_stem().unwrap().to_string_lossy().to_string();
    // Use python to run a small script that does run_matches
    // We'll invoke: .venv/bin/python tools/gauntlet_live.py --our-deck X --agent Y --live-dir DIR --only STEM --games N
    // But gauntlet_live.py prints to stdout, we need to parse last lines
    let output = Command::new(".venv/bin/python")
        .arg("tools/gauntlet_live.py")
        .arg("--our-deck").arg(our_deck)
        .arg("--agent").arg(agent)
        .arg("--live-dir").arg(opp_path.parent().unwrap().to_string_lossy().to_string())
        .arg("--only").arg(&stem)
        .arg("--games").arg(games.to_string())
        .current_dir(PathBuf::from(env!("CARGO_MANIFEST_DIR")).join(".."))
        .output()
        .with_context(|| format!("run gauntlet for {}", stem))?;

    let stdout = String::from_utf8_lossy(&output.stdout);
    // Parse lines like "  name   0.500 (1-1 d0)"
    // Look for line with stem
    let mut rate = 0.0;
    let mut wins = 0;
    let mut losses = 0;
    let mut draws = 0;
    for line in stdout.lines() {
        if line.contains(&stem) && line.contains('(') {
            // Example: "  Pawit_Sahare                        0.500 (1-1 d0)"
            // Split
            let parts: Vec<&str> = line.split_whitespace().collect();
            if parts.len() >= 2 {
                if let Ok(r) = parts[parts.len()-2].parse::<f64>() {
                    rate = r;
                }
                // Parse (w-l
                if let Some(paren) = line.split('(').nth(1) {
                    let inner = paren.split(')').next().unwrap_or("");
                    // inner like "1-1 d0" or "1-1"
                    let wl = inner.split_whitespace().next().unwrap_or("0-0");
                    let wl_parts: Vec<&str> = wl.split('-').collect();
                    if wl_parts.len()==2 {
                        wins = wl_parts[0].parse().unwrap_or(0);
                        losses = wl_parts[1].parse().unwrap_or(0);
                    }
                    if inner.contains("d") {
                        if let Some(d_part) = inner.split('d').nth(1) {
                            draws = d_part.trim().parse().unwrap_or(0);
                        }
                    }
                }
            }
        }
    }

    Ok(MatchResult { name: stem, rate, wins, losses, draws })
}

fn main() -> Result<()> {
    let args = Args::parse();

    if args.jobs > 0 {
        rayon::ThreadPoolBuilder::new().num_threads(args.jobs).build_global().unwrap();
    }

    let live_dir = PathBuf::from(&args.live_dir);
    let mut decks: Vec<PathBuf> = Vec::new();
    if live_dir.exists() {
        for entry in fs::read_dir(&live_dir)? {
            let entry = entry?;
            let path = entry.path();
            if path.extension().and_then(|s| s.to_str()) == Some("csv") {
                if let Some(only) = &args.only {
                    let stem = path.file_stem().unwrap().to_string_lossy();
                    if !only.split(',').any(|o| o==stem) {
                        continue;
                    }
                }
                decks.push(path);
            }
        }
    }

    println!("Our deck: {} ({} cards)", args.our_deck, load_deck_ids(Path::new(&args.our_deck)).unwrap_or_default().len());
    println!("Agent: {}", args.agent);
    println!("Live decks: {} in {}", decks.len(), args.live_dir);
    println!("Games per matchup: {} (rayon threads: {})", args.games, rayon::current_num_threads());

    let start = std::time::Instant::now();

    let results: Vec<MatchResult> = decks.par_iter()
        .map(|opp_path| {
            match run_single_match(&args.our_deck, opp_path, &args.agent, args.games) {
                Ok(r) => {
                    println!("  {:<35} {:.3} ({}-{} d{})", r.name, r.rate, r.wins, r.losses, r.draws);
                    r
                },
                Err(e) => {
                    eprintln!("  {} FAILED: {}", opp_path.display(), e);
                    MatchResult { name: opp_path.file_stem().unwrap().to_string_lossy().to_string(), rate: 0.0, wins: 0, losses: 0, draws: 0 }
                }
            }
        })
        .collect();

    let mut sorted = results.clone();
    sorted.sort_by(|a,b| a.rate.partial_cmp(&b.rate).unwrap());

    println!("\n=== Sorted worst first ===");
    for r in &sorted {
        println!("{:<40} {:.3} ({}-{})", r.name, r.rate, r.wins, r.losses);
    }

    let overall_w: usize = results.iter().map(|r| r.wins).sum();
    let overall_l: usize = results.iter().map(|r| r.losses).sum();
    if overall_w + overall_l > 0 {
        println!("\nOverall: {:.3} ({}-{}) over {} matchups x {} games in {:.1}s",
            overall_w as f64 / (overall_w + overall_l) as f64,
            overall_w, overall_l,
            results.len(), args.games,
            start.elapsed().as_secs_f64()
        );
    }

    Ok(())
}
