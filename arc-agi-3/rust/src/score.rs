//! RHAE — Relative Human Action Efficiency, the ARC-AGI-3 metric.
//!
//! ```text
//! RHAE = (1/|L|) · Σ_l  w_l · min( H_l / A_l , 1.15 )²
//! ```
//!
//! `H_l` = median human action count for level `l`, `A_l` = the agent's action count.
//! The cap means beating the human pays up to 1.15² ≈ 1.3225 per level; the square
//! means wasting actions is punished far harder than intuition suggests.

/// Per-level cap on the human/agent action ratio.
pub const RHAE_CAP: f64 = 1.15;

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

/// Actions the agent may spend on a level before the 1.15 cap stops paying out.
/// Levels are also hard-capped at 5× the human count in the real benchmark.
pub fn actions_at_cap(human: u32) -> f64 {
    human as f64 / RHAE_CAP
}

#[cfg(test)]
mod tests {
    use super::*;

    fn approx(a: f64, b: f64) -> bool {
        (a - b).abs() < 1e-12
    }

    #[test]
    fn cap_is_1_15_squared() {
        assert!(approx(ceiling(), 1.3225));
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
