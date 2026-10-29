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

/// Official per-level cap from the competition data page.
pub const OFFICIAL_CAP: f64 = 1.0;

/// Legacy cap used before 2026-10-29. Kept for reproducing old benchmarks only.
pub const SCALED_CAP: f64 = 1.15;

/// Per-level cap currently used by [`level_score`]. Official value.
pub const RHAE_CAP: f64 = OFFICIAL_CAP;

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
