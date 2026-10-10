//! Replay analysis: find where an agent wastes actions.
//!
//! RHAE punishes action waste quadratically, so the cheapest wins come from
//! finding actions that did nothing. This module turns a recorded action
//! sequence into the numbers that matter, and can sweep whole run directories
//! in parallel with rayon.

use rayon::prelude::*;
use serde_json::Value;
use std::fs;
use std::path::{Path, PathBuf};

/// Statistics for one recorded action sequence.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct ActionStats {
    pub total: usize,
    pub unique: usize,
    /// Longest run of the same action repeated back-to-back.
    pub longest_repeat_run: usize,
    /// Actions that were an exact repeat of the immediately previous action.
    /// These are the first place to look for waste: repeating an action that
    /// just failed to change anything is pure RHAE loss.
    pub immediate_repeats: usize,
    /// Distinct 3-action subsequences that occur more than once — a signature of
    /// the agent looping without learning.
    pub repeated_trigrams: usize,
}

fn trigrams(actions: &[String]) -> Vec<[&str; 3]> {
    actions
        .windows(3)
        .map(|w| [w[0].as_str(), w[1].as_str(), w[2].as_str()])
        .collect()
}

pub fn action_stats(actions: &[String]) -> ActionStats {
    if actions.is_empty() {
        return ActionStats::default();
    }
    let total = actions.len();

    let mut seen: Vec<&str> = actions.iter().map(|s| s.as_str()).collect();
    seen.sort_unstable();
    seen.dedup();
    let unique = seen.len();

    let mut longest_repeat_run = 1usize;
    let mut current_run = 1usize;
    let mut immediate_repeats = 0usize;
    for i in 1..total {
        if actions[i] == actions[i - 1] {
            current_run += 1;
            immediate_repeats += 1;
            longest_repeat_run = longest_repeat_run.max(current_run);
        } else {
            current_run = 1;
        }
    }

    let repeated_trigrams = if total >= 3 {
        let mut tri = trigrams(actions);
        let n = tri.len();
        tri.sort_unstable();
        let mut dup_groups = 0usize;
        let mut i = 0usize;
        while i < n {
            let mut j = i + 1;
            while j < n && tri[j] == tri[i] {
                j += 1;
            }
            if j - i > 1 {
                dup_groups += 1;
            }
            i = j;
        }
        dup_groups
    } else {
        0
    };

    ActionStats {
        total,
        unique,
        longest_repeat_run,
        immediate_repeats,
        repeated_trigrams,
    }
}

/// Best-effort summary of one Duck run directory.
///
/// The Duck emits `score.json`, `evaluation.json`, `benchmark.json` and a
/// `transcripts/` directory. We read what is present and never fail on schema
/// drift — missing fields simply come back as `None`.
#[derive(Debug, Clone, Default)]
pub struct RunSummary {
    pub dir: PathBuf,
    pub game_id: Option<String>,
    pub score: Option<f64>,
    pub actions: Option<usize>,
    pub levels_completed: Option<usize>,
}

fn first_number(v: &Value, keys: &[&str]) -> Option<f64> {
    for k in keys {
        if let Some(n) = v.get(k).and_then(|x| x.as_f64()) {
            return Some(n);
        }
    }
    None
}

fn first_string(v: &Value, keys: &[&str]) -> Option<String> {
    for k in keys {
        if let Some(s) = v.get(k).and_then(|x| x.as_str()) {
            return Some(s.to_string());
        }
    }
    None
}

fn read_json(path: &Path) -> Option<Value> {
    fs::read_to_string(path).ok().and_then(|s| serde_json::from_str(&s).ok())
}

pub fn scan_run(dir: &Path) -> RunSummary {
    let score_path = dir.join("score.json");
    let eval_path = dir.join("evaluation.json");

    let mut summary = RunSummary {
        dir: dir.to_path_buf(),
        ..Default::default()
    };

    for path in [&score_path, &eval_path] {
        if let Some(v) = read_json(path) {
            summary.game_id = summary
                .game_id
                .or_else(|| first_string(&v, &["game_id", "game", "id"]));
            summary.score = summary
                .score
                .or_else(|| first_number(&v, &["score", "rhae", "mean_score"]));
            summary.actions = summary.actions.or_else(|| {
                first_number(&v, &["actions", "n_actions", "total_actions"]).map(|n| n as usize)
            });
            summary.levels_completed = summary.levels_completed.or_else(|| {
                first_number(&v, &["levels_completed", "levels_solved", "n_levels"])
                    .map(|n| n as usize)
            });
        }
    }

    if summary.game_id.is_none() {
        summary.game_id = dir.file_name().map(|n| n.to_string_lossy().to_string());
    }
    summary
}

/// Scan many run directories in parallel.
pub fn scan_runs(dirs: &[PathBuf]) -> Vec<RunSummary> {
    dirs.par_iter().map(|d| scan_run(d)).collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn v(items: &[&str]) -> Vec<String> {
        items.iter().map(|s| s.to_string()).collect()
    }

    #[test]
    fn empty_sequence() {
        assert_eq!(action_stats(&[]), ActionStats::default());
    }

    #[test]
    fn counts_totals_and_unique() {
        let s = action_stats(&v(&["LEFT", "LEFT", "RIGHT"]));
        assert_eq!(s.total, 3);
        assert_eq!(s.unique, 2);
    }

    #[test]
    fn detects_immediate_repeats() {
        let s = action_stats(&v(&["LEFT", "LEFT", "UP", "UP", "UP"]));
        assert_eq!(s.immediate_repeats, 3);
        assert_eq!(s.longest_repeat_run, 3);
    }

    #[test]
    fn no_repeats_in_alternating_sequence() {
        let s = action_stats(&v(&["LEFT", "RIGHT", "LEFT", "RIGHT"]));
        assert_eq!(s.immediate_repeats, 0);
        assert_eq!(s.longest_repeat_run, 1);
    }

    #[test]
    fn detects_looping_trigrams() {
        // "A B C" appears twice -> one duplicated trigram group
        let s = action_stats(&v(&["A", "B", "C", "D", "A", "B", "C"]));
        assert_eq!(s.repeated_trigrams, 1);
    }

    #[test]
    fn short_sequences_have_no_trigrams() {
        assert_eq!(action_stats(&v(&["A", "B"])).repeated_trigrams, 0);
    }

    #[test]
    fn scan_of_missing_dir_is_tolerated() {
        let s = scan_run(Path::new("/nonexistent/path/that/does/not/exist"));
        assert!(s.score.is_none());
        assert!(s.actions.is_none());
        // game_id falls back to the directory name
        assert_eq!(s.game_id, Some("exist".to_string()));
    }
}
