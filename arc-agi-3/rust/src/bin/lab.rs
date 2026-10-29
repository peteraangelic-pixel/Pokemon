//! `lab` — offline local test environment for ARC-AGI-3 policies. No GPU, no network.
//!
//! This is the Rust + rayon harness the analysis asks for: it replays a recorded
//! run (`benchmark.json` from `duck/ops/results/*/output/`) and answers the three
//! questions that actually decide the score, in parallel across games:
//!
//! ```text
//!   lab analyze   r018/benchmark.json                 # decomposition: coverage x efficiency
//!   lab ceiling   r018/benchmark.json 200 275 400 800 # score ceiling per action budget
//!   lab policies  r018/benchmark.json 275 400 600     # equal split vs value-greedy
//!   lab sweep     results/*/output/benchmark.json     # every run at once, in parallel
//! ```
//!
//! Everything here reads recorded data. Nothing here talks to Kaggle, and nothing
//! here is on the submission path — it exists so a policy change can be measured
//! before it costs one of our remaining daily submissions.
//!
//! NOT COMPILED in the authoring sandbox (no cargo there). Build it first —
//! see `rust/BUILD-AND-BENCH.md`.

use std::path::PathBuf;
use std::process::ExitCode;

use rayon::prelude::*;
use serde_json::Value;

/// One game from a recorded run.
#[derive(Clone, Debug)]
struct GameRecord {
    id: String,
    /// Human action count per level — the RHAE denominator. Present only in our
    /// own benchmark artifacts; never visible to the agent at eval time.
    human: Vec<u32>,
    /// Actions we actually spent per level.
    agent: Vec<u32>,
    completed: u32,
}

impl GameRecord {
    /// Number of levels in the game.
    ///
    /// `base_actions_per_level` has exactly one entry per level (verified: tn36
    /// has 7 entries and `number_of_levels` 7), and it is the scoring baseline, so
    /// it is also the bound every index below is sliced with.
    fn levels(&self) -> usize {
        self.human.len()
    }

    /// 1 + 2 + ... + L — the per-game score denominator.
    fn total_weight(&self) -> f64 {
        let l = self.levels() as f64;
        l * (l + 1.0) / 2.0
    }

    /// Fraction of this game's maximum the run actually banked, ignoring efficiency.
    fn coverage(&self) -> f64 {
        let k = self.completed as f64;
        if self.total_weight() == 0.0 {
            return 0.0;
        }
        (k * (k + 1.0) / 2.0) / self.total_weight()
    }

    /// Squared RHAE on the levels that were finished.
    fn efficiency(&self) -> f64 {
        let k = self.completed as usize;
        if k == 0 {
            return 0.0;
        }
        let mut num = 0.0;
        for l in 0..k.min(self.agent.len()).min(self.human.len()) {
            if self.agent[l] == 0 {
                continue;
            }
            let ratio = self.human[l] as f64 / self.agent[l] as f64;
            num += (l as f64 + 1.0) * ratio.min(1.0).powi(2);
        }
        let denom = k as f64 * (k as f64 + 1.0) / 2.0;
        if denom == 0.0 {
            0.0
        } else {
            num / denom
        }
    }

    fn score(&self) -> f64 {
        100.0 * self.coverage() * self.efficiency()
    }
}

fn read_games(path: &PathBuf) -> Result<Vec<GameRecord>, String> {
    let text = std::fs::read_to_string(path).map_err(|e| format!("{}: {}", path.display(), e))?;
    let root: Value =
        serde_json::from_str(&text).map_err(|e| format!("{}: bad json: {}", path.display(), e))?;
    let runs = root
        .get("game_runs")
        .and_then(|v| v.as_array())
        .ok_or_else(|| format!("{}: no game_runs[]", path.display()))?;

    let mut out = Vec::with_capacity(runs.len());
    for run in runs {
        let id = run
            .get("game_id")
            .and_then(|v| v.as_str())
            .unwrap_or("????")
            .chars()
            .take(4)
            .collect::<String>();
        let human = run
            .get("base_actions_per_level")
            .and_then(|v| v.as_array())
            .map(|a| a.iter().map(|x| x.as_u64().unwrap_or(0) as u32).collect())
            .unwrap_or_default();
        let agent = run
            .get("actions_per_level")
            .and_then(|v| v.as_array())
            .map(|a| a.iter().map(|x| x.as_u64().unwrap_or(0) as u32).collect())
            .unwrap_or_default();
        let completed = run
            .get("levels_completed")
            .and_then(|v| v.as_u64())
            .unwrap_or(0) as u32;
        out.push(GameRecord { id, human, agent, completed });
    }
    Ok(out)
}

fn mean(xs: &[f64]) -> f64 {
    if xs.is_empty() {
        0.0
    } else {
        xs.iter().sum::<f64>() / xs.len() as f64
    }
}

/// Score ceiling: walk each game level by level while `budget` lasts.
///
/// `efficiency` scales the human cost, because to score `e^2` on a level we need
/// `human / e` actions.
fn ceiling(games: &[GameRecord], budget: f64, efficiency: f64) -> f64 {
    let per_game: Vec<f64> = games
        .par_iter()
        .map(|g| {
            let mut used = 0.0;
            let mut k = 0usize;
            for &h in &g.human {
                let cost = h as f64 / efficiency;
                if used + cost <= budget {
                    used += cost;
                    k += 1;
                } else {
                    break;
                }
            }
            let w = g.total_weight();
            if w == 0.0 {
                0.0
            } else {
                100.0 * (k * (k + 1) as usize) as f64 / 2.0 / w
            }
        })
        .collect();
    mean(&per_game)
}

/// Equal split: every game gets the same number of actions.
fn policy_equal(games: &[GameRecord], per_game: f64, efficiency: f64) -> f64 {
    ceiling(games, per_game, efficiency)
}

/// Value-greedy: spend the next quantum on the game with the best
/// `marginal_value / estimated_cost`, estimating cost only from what we observed.
///
/// `prior_cost` is the guess for a game's first level. The honest value is the
/// observed median first-level cost (~30 in our runs). The result is sensitive to
/// this — see MEGA-DIAGNOSIS.md §5 — so it is a parameter, not a constant.
fn policy_greedy(
    games: &[GameRecord],
    per_game_budget: f64,
    efficiency: f64,
    prior_cost: f64,
) -> f64 {
    let n = games.len();
    if n == 0 {
        return 0.0;
    }
    let mut spent = vec![0.0f64; n];
    let mut done = vec![0u32; n];
    let mut left = per_game_budget * n as f64;
    let quantum = 10.0;

    while left > 1e-9 {
        let mut best: Option<(f64, usize)> = None;
        for (i, g) in games.iter().enumerate() {
            let l = g.levels() as u32;
            if done[i] >= l {
                continue;
            }
            let value = arc3::plan::marginal_value(done[i], l);
            let cost = if done[i] == 0 {
                prior_cost
            } else {
                (spent[i] / done[i] as f64).max(1.0)
            };
            let priority = value / cost;
            if best.map_or(true, |(b, _)| priority > b) {
                best = Some((priority, i));
            }
        }
        let Some((_, i)) = best else { break };
        let need = games[i].human.get(done[i] as usize).copied().unwrap_or(0) as f64 / efficiency;
        let paid: f64 = games[i].human[..done[i] as usize]
            .iter()
            .map(|&h| h as f64 / efficiency)
            .sum();
        let on_level = spent[i] - paid;
        let step = quantum.min(need - on_level).min(left).max(1.0);
        spent[i] += step;
        left -= step;
        let target: f64 = games[i].human[..done[i] as usize + 1]
            .iter()
            .map(|&h| h as f64 / efficiency)
            .sum();
        if spent[i] >= target - 1e-9 {
            done[i] += 1;
        }
    }

    let per: Vec<f64> = (0..n)
        .map(|i| {
            let g = &games[i];
            let w = g.total_weight();
            if w == 0.0 {
                0.0
            } else {
                let k = done[i] as f64;
                100.0 * (k * (k + 1.0) / 2.0) / w
            }
        })
        .collect();
    mean(&per)
}

fn cmd_analyze(path: &PathBuf) -> Result<(), String> {
    let games = read_games(path)?;
    println!("{:<6} {:>4} {:>4} {:>10} {:>13} {:>7}", "gra", "L", "k", "pokrycie", "efektywnosc", "wynik");
    for g in &games {
        println!(
            "{:<6} {:>4} {:>4} {:>9.1}% {:>12.1}% {:>7.2}",
            g.id,
            g.levels(),
            g.completed,
            g.coverage() * 100.0,
            g.efficiency() * 100.0,
            g.score()
        );
    }
    let cov = mean(&games.iter().map(|g| g.coverage()).collect::<Vec<_>>());
    let eff = mean(&games.iter().map(|g| g.efficiency()).collect::<Vec<_>>());
    let score = mean(&games.iter().map(|g| g.score()).collect::<Vec<_>>());
    println!(
        "{:<6} {:>4} {:>4} {:>9.1}% {:>12.1}% {:>7.2}",
        "ŚREDNIA", "", "", cov * 100.0, eff * 100.0, score
    );
    Ok(())
}

fn cmd_ceiling(path: &PathBuf, budgets: &[f64]) -> Result<(), String> {
    let games = read_games(path)?;
    println!("{:<10} {:>14} {:>14}", "akcji/grę", "sufit@100%", "sufit@90%");
    let rows: Vec<(f64, f64, f64)> = budgets
        .par_iter()
        .map(|&b| (b, ceiling(&games, b, 1.0), ceiling(&games, b, 0.9)))
        .collect();
    let mut rows = rows;
    rows.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap_or(std::cmp::Ordering::Equal));
    for (b, c100, c90) in rows {
        println!("{:<10.0} {:>14.1} {:>14.1}", b, c100, c90);
    }
    Ok(())
}

fn cmd_policies(path: &PathBuf, budgets: &[f64]) -> Result<(), String> {
    let games = read_games(path)?;
    println!(
        "{:<10} {:>9} {:>9} {:>9} {:>9}",
        "akcji/grę", "rowno", "greedy30", "greedy45", "greedy90"
    );
    let rows: Vec<(f64, f64, f64, f64, f64)> = budgets
        .par_iter()
        .map(|&b| {
            (
                b,
                policy_equal(&games, b, 0.9),
                policy_greedy(&games, b, 0.9, 30.0),
                policy_greedy(&games, b, 0.9, 45.0),
                policy_greedy(&games, b, 0.9, 90.0),
            )
        })
        .collect();
    let mut rows = rows;
    rows.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap_or(std::cmp::Ordering::Equal));
    for (b, e, g30, g45, g90) in rows {
        println!("{:<10.0} {:>9.1} {:>9.1} {:>9.1} {:>9.1}", b, e, g30, g45, g90);
    }
    Ok(())
}

fn cmd_sweep(paths: &[PathBuf]) -> Result<(), String> {
    // Every run in parallel; each run analyses its games in parallel too.
    let mut rows: Vec<(String, f64, f64, f64, usize)> = paths
        .par_iter()
        .filter_map(|p| {
            let games = read_games(p).ok()?;
            let name = p
                .parent()
                .and_then(|d| d.parent())
                .and_then(|d| d.file_name())
                .map(|s| s.to_string_lossy().to_string())
                .unwrap_or_else(|| p.display().to_string());
            let cov = mean(&games.iter().map(|g| g.coverage()).collect::<Vec<_>>());
            let eff = mean(&games.iter().map(|g| g.efficiency()).collect::<Vec<_>>());
            let sc = mean(&games.iter().map(|g| g.score()).collect::<Vec<_>>());
            Some((name, cov, eff, sc, games.len()))
        })
        .collect();
    rows.sort_by(|a, b| a.4.cmp(&b.4).then(a.0.cmp(&b.0)));
    println!("{:<18} {:>5} {:>10} {:>13} {:>7}", "run", "gier", "pokrycie", "efektywnosc", "wynik");
    for (name, cov, eff, sc, n) in rows {
        println!("{:<18} {:>5} {:>9.1}% {:>12.1}% {:>7.2}", name, n, cov * 100.0, eff * 100.0, sc);
    }
    Ok(())
}

fn usage() -> ExitCode {
    eprintln!(
        "użycie:\n  \
         lab analyze  <benchmark.json>\n  \
         lab ceiling  <benchmark.json> <budżet>... \n  \
         lab policies <benchmark.json> <budżet>...\n  \
         lab sweep    <benchmark.json>..."
    );
    ExitCode::from(2)
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.len() < 2 {
        return usage();
    }
    let cmd = args[0].as_str();
    let result = match cmd {
        "analyze" => cmd_analyze(&PathBuf::from(&args[1])),
        "sweep" => cmd_sweep(&args[1..].iter().map(PathBuf::from).collect::<Vec<_>>()),
        "ceiling" | "policies" => {
            let path = PathBuf::from(&args[1]);
            let budgets: Vec<f64> = args[2..].iter().filter_map(|s| s.parse().ok()).collect();
            let budgets = if budgets.is_empty() {
                vec![200.0, 275.0, 400.0, 800.0]
            } else {
                budgets
            };
            if cmd == "ceiling" {
                cmd_ceiling(&path, &budgets)
            } else {
                cmd_policies(&path, &budgets)
            }
        }
        _ => return usage(),
    };
    match result {
        Ok(()) => ExitCode::SUCCESS,
        Err(e) => {
            eprintln!("błąd: {}", e);
            ExitCode::FAILURE
        }
    }
}
