//! RHAE — Relative Human Action Efficiency, the ARC-AGI-3 metric.
//!
//! The competition data page states the official rule as:
//!
//! ```text
//! per-level score = min(human_actions / agent_actions, 1.0)²
//! per-game score  = weighted mean of level scores (weight = level index, 1-based)
//! total score     = mean of per-game scores, reported as 0–100
//! ```
//!
//! Note the cap is **1.0**: matching the human earns the full level, and there is
//! nothing to gain by going faster than human. An earlier revision of this file
//! used 1.15, which overstates any run where the agent beats the human baseline
//! (up to +32% on those levels) and therefore overstates our own smoke estimates.
//! `OFFICIAL_CAP` is the one to use; `SCALED_CAP` is kept only so old numbers can
//! be reproduced and compared.

/// Per-level points ceiling. NOT a ratio: the rule scores each completed level as
/// `min(115, (baseline/actions)^2 * 100)`, so the ratio cap is sqrt(1.15) ~ 1.072.
pub const LEVEL_CEILING: f64 = 115.0;

/// Legacy ratio caps, kept only to reproduce superseded benchmarks.
pub const SCALED_CAP: f64 = 1.15;
pub const OFFICIAL_CAP: f64 = 1.0;

/// Ratio cap implied by [`LEVEL_CEILING`].
pub const RHAE_CAP: f64 = 1.0723805294763597; // sqrt(1.15)

/// Score for one level. `human` and `agent` are action counts.
///
/// `agent == 0` cannot happen in practice (an agent that took no actions solved
/// nothing); we return 0.0 rather than divide by zero.
pub fn level_score(human: u32, agent: u32) -> f64 {
    if agent == 0 {
        return 0.0;
    }
    let ratio = human as f64 / agent as f64;
    ratio.min(RHAE_CAP).powi(2)
}

/// Unweighted mean over levels. Each entry is `(human_actions, agent_actions)`.
pub fn rhae(levels: &[(u32, u32)]) -> f64 {
    if levels.is_empty() {
        return 0.0;
    }
    let total: f64 = levels.iter().map(|&(h, a)| level_score(h, a)).sum();
    total / levels.len() as f64
}

/// Weighted mean (later levels carry more weight in the real benchmark).
/// Each entry is `(human_actions, agent_actions, weight)`.
pub fn rhae_weighted(levels: &[(u32, u32, f64)]) -> f64 {
    let wsum: f64 = levels.iter().map(|&(_, _, w)| w).sum();
    if wsum <= 0.0 {
        return 0.0;
    }
    let total: f64 = levels
        .iter()
        .map(|&(h, a, w)| w * level_score(h, a))
        .sum();
    total / wsum
}

/// How many extra levels' worth of headroom the cap leaves: the best achievable
/// mean (every level at or under the cap) is `RHAE_CAP²`.
pub fn ceiling() -> f64 {
    RHAE_CAP.powi(2)
}

/// Actions the agent may spend on a level before the cap stops paying out.
/// With the official cap of 1.0 this is simply the human action count: any faster
/// than a human earns no extra credit, only slower costs points.
pub fn actions_at_cap(human: u32) -> f64 {
    human as f64 / RHAE_CAP
}

/// Same per-level score but with the legacy 1.15 cap, for backwards comparison.
pub fn level_score_legacy(human: u32, agent: u32) -> f64 {
    if agent == 0 {
        return 0.0;
    }
    (human as f64 / agent as f64).min(SCALED_CAP).powi(2)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn approx(a: f64, b: f64) -> bool {
        (a - b).abs() < 1e-12
    }

    #[test]
    fn official_ceiling_is_one() {
        // Matching the human is the maximum; going faster pays nothing extra.
        assert!(approx(ceiling(), 1.0));
        assert!(approx(level_score(10, 10), 1.0));
        assert!(approx(level_score(10, 2), 1.0)); // five times faster still 1.0
    }

    #[test]
    fn legacy_cap_still_reproducible() {
        assert!(approx(level_score_legacy(10, 10), 1.0));
        assert!(approx(level_score_legacy(10, 2), 1.3225));
    }

    #[test]
    fn half_efficiency_is_a_quarter() {
        // The square is the whole point: 50% efficiency scores 25%.
        assert!(approx(level_score(10, 20), 0.25));
    }

    #[test]
    fn matching_human_scores_one() {
        assert!(approx(level_score(10, 10), 1.0));
    }

    #[test]
    fn quadratic_penalty() {
        assert!(approx(level_score(10, 20), 0.25));
        assert!(approx(level_score(10, 50), 0.04));
        assert!(approx(level_score(10, 100), 0.01));
    }

    #[test]
    fn beating_human_is_capped() {
        // agent uses fewer actions than the human -> capped, not unbounded
        assert!(approx(level_score(10, 5), ceiling()));
        assert!(approx(level_score(10, 1), ceiling()));
        assert!(approx(level_score(10, 8), ceiling())); // 10/8 = 1.25 > 1.15
    }

    #[test]
    fn just_under_cap_is_not_capped() {
        // 10/9 = 1.111 < 1.15 -> not capped
        assert!(approx(level_score(10, 9), (10.0 / 9.0_f64).powi(2)));
    }

    #[test]
    fn zero_agent_actions_is_zero_not_nan() {
        assert_eq!(level_score(10, 0), 0.0);
    }

    #[test]
    fn mean_over_levels() {
        let levels = vec![(10, 10), (10, 20)];
        assert!(approx(rhae(&levels), 0.625));
    }

    #[test]
    fn weighted_mean() {
        let levels = vec![(10, 10, 3.0), (10, 20, 1.0)];
        assert!(approx(rhae_weighted(&levels), 0.8125));
    }

    #[test]
    fn empty_inputs_are_zero() {
        assert_eq!(rhae(&[]), 0.0);
        assert_eq!(rhae_weighted(&[]), 0.0);
    }

    #[test]
    fn actions_at_cap_matches_cap() {
        let human = 10u32;
        let a = actions_at_cap(human);
        assert!(approx(level_score(human, a as u32), ceiling()));
    }
}

// ---------------------------------------------------------------------------
// Authoritative scoring (added 2026-10-30)
//
// The functions above implement an older model that was wrong in two ways:
// it capped the RATIO at 1.15 and it had no completion cap. Verified against the
// 30 `final_score` values stored in `local/benchmarks/*.json`: the older model
// reproduces 2/30 (ratio cap 1.15) or 9/30 (cap 1.0), while the functions below
// reproduce **30/30** exactly. Reference implementation and tests:
// `local/metric.py`, `local/test_metric.py`.
//
//     for k = 1..n:  w_k = k
//                    s_k = min(115, (baseline_k / actions_k)^2 * 100)  if k <= completed
//                    s_k = 0 otherwise
//     raw   = sum(s_k * w_k) / sum(w_k)
//     cap   = 100 * sum(w_k where s_k > 0) / sum(w_k)
//     score = min(raw, cap)
//
// The consequence that matters: score <= 100 * coverage, always. Beating the
// human cannot lift you above the fraction of the game you finished, which is
// why depth dominates and why a level you never complete is worth exactly zero.
// ---------------------------------------------------------------------------

/// Points for one completed level, 0..115.
pub fn level_points(baseline: u32, actions: u32) -> f64 {
    if actions == 0 || baseline == 0 {
        return 0.0;
    }
    let ratio = baseline as f64 / actions as f64;
    (ratio * ratio * 100.0).min(LEVEL_CEILING)
}

/// Score of one game, 0..100, under the authoritative rule.
///
/// `actions` is one entry per level; entries for unfinished levels are ignored.
pub fn game_score(baselines: &[u32], actions: &[u32], completed: u32) -> f64 {
    let levels = baselines.len();
    if levels == 0 {
        return 0.0;
    }
    let denom: f64 = (1..=levels).map(|l| l as f64).sum();
    let mut weighted = 0.0;
    let mut done_weight = 0.0;
    for i in 0..levels {
        if (i as u32) >= completed {
            break;
        }
        let acts = actions.get(i).copied().unwrap_or(0);
        if acts == 0 {
            continue;
        }
        let w = (i + 1) as f64;
        weighted += level_points(baselines[i], acts) * w;
        done_weight += w;
    }
    let raw = weighted / denom;
    let completion_cap = 100.0 * done_weight / denom;
    raw.min(completion_cap)
}

#[cfg(test)]
mod authoritative_tests {
    use super::*;

    fn approx(a: f64, b: f64) -> bool {
        (a - b).abs() < 1e-9
    }

    #[test]
    fn perfect_match_scores_100() {
        assert!(approx(game_score(&[50, 50, 50], &[50, 50, 50], 3), 100.0));
    }

    #[test]
    fn beating_human_cannot_exceed_coverage() {
        // 3 of 4 levels, ten times faster than human: held at the completion cap.
        assert!(approx(game_score(&[50; 4], &[5, 5, 5, 0], 3), 60.0));
    }

    #[test]
    fn completing_three_of_four_is_sixty() {
        assert!(approx(game_score(&[50; 4], &[50, 50, 50, 0], 3), 60.0));
        assert!(approx(game_score(&[50; 4], &[50, 50, 0, 0], 2), 30.0));
        assert!(approx(game_score(&[50; 4], &[50, 0, 0, 0], 1), 10.0));
    }

    #[test]
    fn double_the_human_cost_is_a_quarter() {
        assert!(approx(game_score(&[50; 4], &[100; 4], 4), 25.0));
    }

    #[test]
    fn unfinished_level_scores_nothing() {
        assert!(approx(game_score(&[50; 4], &[50, 999, 0, 0], 1), 10.0));
    }

    #[test]
    fn level_points_ceiling() {
        assert!(approx(level_points(100, 10), 115.0));
        assert!(approx(level_points(100, 100), 100.0));
        assert!(approx(level_points(100, 200), 25.0));
    }
}
