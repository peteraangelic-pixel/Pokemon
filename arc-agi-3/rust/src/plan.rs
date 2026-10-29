//! Macro-action planner: turn one LLM decision into several game actions.
//!
//! Why
//! ---
//! Measured on 6034 actions across 30 recorded games, our harness issued
//! **1.00 game actions per LLM decision** (`MEGA-DIAGNOSIS.md` §4). Every single
//! move costs a full model round-trip of ~14 s and ~700-1100 generated tokens.
//! At ~200 actions per game the score ceiling is ~19-31 points; at 400 it is ~51.
//! So the binding constraint is not the model, it is how much action a decision
//! buys.
//!
//! This module is the "buy more action per decision" half of the plan:
//!
//! 1. Observe `(state, action) -> state` transitions while the agent plays.
//! 2. When the model states a *goal state* (or a click target), search the learned
//!    deterministic model for a shortest action sequence to it.
//! 3. Emit that sequence, verifying each real frame against the prediction, and
//!    abort the batch at the first mismatch so a wrong model costs one action,
//!    never the whole sequence.
//!
//! The safety property matters: actions count in the scoring denominator, so a
//! confident-but-wrong batch is worse than no batch at all. Everything here is
//! opt-in and self-truncating by design.
//!
//! Status: **not compiled in the authoring sandbox** (no `cargo` there). Build and
//! test on your own machine with `rust/BUILD-AND-BENCH.md` before trusting it.

use std::collections::{HashMap, VecDeque};
use std::hash::{Hash, Hasher};

use rayon::prelude::*;

/// A single game action. Mirrors the competition's action space.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum Action {
    /// ACTION1..ACTION5 — the five discrete controls.
    Key(u8),
    /// ACTION6 — click at grid coordinates.
    Click(u8, u8),
}

impl Action {
    pub fn key(k: u8) -> Self {
        debug_assert!((1..=5).contains(&k));
        Action::Key(k)
    }

    pub fn click(x: u8, y: u8) -> Self {
        Action::Click(x, y)
    }

    /// Stable identifier, useful for logging and for the offline replay format.
    pub fn id(&self) -> String {
        match self {
            Action::Key(k) => format!("ACTION{}", k),
            Action::Click(x, y) => format!("ACTION6({},{})", x, y),
        }
    }
}

/// A frame reduced to a hash, which is all the planner needs to reason about
/// identity. The harness keeps the real grids; this module never allocates one.
pub type StateId = u64;

/// Deterministic transition table learned purely from play.
///
/// Conflicts are recorded rather than silently overwritten: if the same
/// `(state, action)` is seen leading to two different states, the model is not
/// deterministic there and the planner must refuse to batch from that state.
#[derive(Default, Debug)]
pub struct TransitionModel {
    edges: HashMap<(StateId, Action), StateId>,
    conflicts: HashMap<(StateId, Action), u32>,
    observations: u64,
}

impl TransitionModel {
    pub fn new() -> Self {
        Self::default()
    }

    /// Record an observed transition.
    pub fn observe(&mut self, from: StateId, action: Action, to: StateId) {
        self.observations += 1;
        match self.edges.get(&(from, action)) {
            Some(&known) if known == to => {}
            Some(_) => {
                *self.conflicts.entry((from, action)).or_insert(0) += 1;
            }
            None => {
                self.edges.insert((from, action), to);
            }
        }
    }

    /// True when this action's outcome is known and has never varied.
    pub fn is_deterministic(&self, from: StateId, action: Action) -> bool {
        self.edges.contains_key(&(from, action)) && !self.conflicts.contains_key(&(from, action))
    }

    pub fn predict(&self, from: StateId, action: Action) -> Option<StateId> {
        if !self.is_deterministic(from, action) {
            return None;
        }
        self.edges.get(&(from, action)).copied()
    }

    pub fn observations(&self) -> u64 {
        self.observations
    }

    pub fn conflict_count(&self) -> usize {
        self.conflicts.len()
    }

    /// Actions known to work from `state`.
    pub fn actions_from(&self, state: StateId) -> Vec<Action> {
        let mut out: Vec<Action> = self
            .edges
            .keys()
            .filter(|(s, _)| *s == state)
            .map(|(_, a)| *a)
            .collect();
        out.sort_by_key(|a| a.id());
        out
    }
}

/// Shortest action sequence from `start` to any state satisfying `is_goal`.
///
/// BFS over the learned graph, depth-limited. Returns `None` when the goal is
/// unreachable *within the model* — which is the common case early in a level and
/// is exactly when the agent should fall back to the language model.
pub fn plan_to_goal<F>(
    model: &TransitionModel,
    start: StateId,
    max_depth: usize,
    is_goal: F,
) -> Option<Vec<Action>>
where
    F: Fn(StateId) -> bool,
{
    if is_goal(start) {
        return Some(Vec::new());
    }
    let mut seen: HashMap<StateId, (StateId, Action)> = HashMap::new();
    let mut queue: VecDeque<(StateId, usize)> = VecDeque::new();
    queue.push_back((start, 0));
    seen.insert(start, (start, Action::Key(1))); // root marker, never followed

    while let Some((state, depth)) = queue.pop_front() {
        if depth >= max_depth {
            continue;
        }
        for action in model.actions_from(state) {
            let Some(next) = model.predict(state, action) else {
                continue;
            };
            if seen.contains_key(&next) {
                continue;
            }
            seen.insert(next, (state, action));
            if is_goal(next) {
                // Walk the parent chain back to the start.
                let mut path = Vec::new();
                let mut cur = next;
                while cur != start {
                    let (prev, act) = seen[&cur];
                    path.push(act);
                    cur = prev;
                }
                path.reverse();
                return Some(path);
            }
            queue.push_back((next, depth + 1));
        }
    }
    None
}

/// Number of levels left, given the total from the first frame.
///
/// The harness exposes `win_levels` on every observation, so this is always
/// available — unlike the human baseline, which is not visible at eval time.
pub fn levels_remaining(win_levels: u32, completed: u32) -> u32 {
    win_levels.saturating_sub(completed)
}

/// Marginal score value of completing the next level of a game.
///
/// The competition weights level `l` (1-based) by `l` and divides by
/// `1 + 2 + ... + L`, so finishing level 1 of a 4-level game is worth 10% of that
/// game while level 1 of a 9-level game is worth 2.2%. Unfinished levels stay in
/// the denominator and score zero, which is why finishing matters more than
/// starting.
pub fn marginal_value(completed: u32, win_levels: u32) -> f64 {
    if win_levels == 0 || completed >= win_levels {
        return 0.0;
    }
    let next_weight = (completed + 1) as f64;
    let total: f64 = (1..=win_levels).map(|l| l as f64).sum();
    next_weight / total
}

/// A batch that survived validation against the real environment.
#[derive(Debug, Clone)]
pub struct Batch {
    pub actions: Vec<Action>,
    /// Predicted state after each action, used to cut the batch short.
    pub predicted: Vec<StateId>,
}

/// Trim a planned sequence at the first action whose outcome we cannot guarantee.
///
/// Called before anything is emitted, so the harness can decide "3 actions are
/// safe, the 4th is a guess — emit 3 and ask again".
pub fn safe_prefix(model: &TransitionModel, start: StateId, plan: &[Action]) -> Batch {
    let mut actions = Vec::new();
    let mut predicted = Vec::new();
    let mut cur = start;
    for &action in plan {
        match model.predict(cur, action) {
            Some(next) => {
                actions.push(action);
                predicted.push(next);
                cur = next;
            }
            None => break,
        }
    }
    Batch { actions, predicted }
}

/// How many of a batch's predictions actually held.
///
/// The harness feeds real observed states here; the moment `held < actions.len()`
/// the remainder of the batch was wasted and the model should be corrected.
pub fn validate(batch: &Batch, observed: &[StateId]) -> usize {
    batch
        .predicted
        .iter()
        .zip(observed.iter())
        .take_while(|(p, o)| p == o)
        .count()
}

/// Parallel fan-out over candidate models.
///
/// During analysis we often hold several plausible transition hypotheses (e.g.
/// "walls are solid" vs "walls are passable"). Running BFS for each on its own
/// core is what makes the planner fast enough to sit in an interactive loop.
pub fn plan_parallel(
    models: &[TransitionModel],
    start: StateId,
    max_depth: usize,
    goal: StateId,
) -> Option<(usize, Vec<Action>)> {
    models
        .par_iter()
        .enumerate()
        .filter_map(|(i, m)| {
            plan_to_goal(m, start, max_depth, |s| s == goal).map(|path| (i, path))
        })
        .min_by_key(|(_, path)| path.len())
}

/// Fingerprint a grid so it can be used as a [`StateId`]. Order-sensitive and
/// independent of Rust's `Hash` randomness, so ids are stable across processes —
/// the same requirement `replay::frame_hash` has.
pub fn state_id(cells: &[u8]) -> StateId {
    // FNV-1a, chosen because it is stable and needs no crate.
    let mut hash: u64 = 0xcbf29ce484222325;
    for &b in cells {
        hash ^= b as u64;
        hash = hash.wrapping_mul(0x100000001b3);
    }
    hash
}

#[allow(dead_code)]
fn hash_one<T: Hash>(value: &T) -> u64 {
    // Kept for callers that already have hashable state; not used by state_id.
    let mut h = std::collections::hash_map::DefaultHasher::new();
    value.hash(&mut h);
    h.finish()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn model_with(edges: &[(StateId, Action, StateId)]) -> TransitionModel {
        let mut m = TransitionModel::new();
        for &(a, act, b) in edges {
            m.observe(a, act, b);
        }
        m
    }

    #[test]
    fn learns_and_predicts() {
        let m = model_with(&[(1, Action::key(1), 2), (2, Action::key(1), 3)]);
        assert_eq!(m.predict(1, Action::key(1)), Some(2));
        assert_eq!(m.predict(2, Action::key(1)), Some(3));
        assert_eq!(m.predict(3, Action::key(1)), None);
    }

    #[test]
    fn conflicting_observation_disables_batching() {
        let mut m = model_with(&[(1, Action::key(2), 2)]);
        assert!(m.is_deterministic(1, Action::key(2)));
        m.observe(1, Action::key(2), 3); // same input, different outcome
        assert!(!m.is_deterministic(1, Action::key(2)));
        assert_eq!(m.predict(1, Action::key(2)), None);
        assert_eq!(m.conflict_count(), 1);
    }

    #[test]
    fn bfs_finds_shortest_path() {
        // 1 -R-> 2 -R-> 3, plus a longer 1 -D-> 4 -R-> 5 -R-> 3
        let m = model_with(&[
            (1, Action::key(1), 2),
            (2, Action::key(1), 3),
            (1, Action::key(2), 4),
            (4, Action::key(1), 5),
            (5, Action::key(1), 3),
        ]);
        let path = plan_to_goal(&m, 1, 8, |s| s == 3).expect("reachable");
        assert_eq!(path.len(), 2);
        assert_eq!(path, vec![Action::key(1), Action::key(1)]);
    }

    #[test]
    fn bfs_respects_depth_limit() {
        let m = model_with(&[(1, Action::key(1), 2), (2, Action::key(1), 3)]);
        assert!(plan_to_goal(&m, 1, 1, |s| s == 3).is_none());
        assert!(plan_to_goal(&m, 1, 2, |s| s == 3).is_some());
    }

    #[test]
    fn unborn_states_are_not_reachable() {
        let m = model_with(&[(1, Action::key(1), 2)]);
        assert!(plan_to_goal(&m, 1, 10, |s| s == 99).is_none());
    }

    #[test]
    fn safe_prefix_stops_at_unknown_edge() {
        let m = model_with(&[(1, Action::key(1), 2)]);
        let plan = vec![Action::key(1), Action::key(1), Action::key(1)];
        let batch = safe_prefix(&m, 1, &plan);
        // Only the first step is predictable: state 2 has no learned edges here.
        assert_eq!(batch.actions.len(), 1);
        assert_eq!(batch.predicted, vec![2]);
    }

    #[test]
    fn validate_counts_held_predictions() {
        let batch = Batch {
            actions: vec![Action::key(1); 3],
            predicted: vec![2, 3, 4],
        };
        assert_eq!(validate(&batch, &[2, 3, 4]), 3);
        assert_eq!(validate(&batch, &[2, 3, 9]), 2);
        assert_eq!(validate(&batch, &[7, 3, 4]), 0);
    }

    #[test]
    fn marginal_value_is_back_loaded() {
        // Level 1 of a 7-level game is 1/28; the last level is 7/28.
        assert!((marginal_value(0, 7) - 1.0 / 28.0).abs() < 1e-12);
        assert!((marginal_value(6, 7) - 7.0 / 28.0).abs() < 1e-12);
        // A short game pays much better for the same first level.
        assert!(marginal_value(0, 4) > 4.0 * marginal_value(0, 9));
        assert_eq!(marginal_value(7, 7), 0.0);
    }

    #[test]
    fn state_id_is_stable_and_order_sensitive() {
        assert_eq!(state_id(&[1, 2, 3]), state_id(&[1, 2, 3]));
        assert_ne!(state_id(&[1, 2, 3]), state_id(&[3, 2, 1]));
        assert_ne!(state_id(&[1, 2]), state_id(&[1, 2, 0]));
    }

    #[test]
    fn parallel_plan_prefers_the_shortest_model() {
        let long = model_with(&[
            (1, Action::key(1), 2),
            (2, Action::key(1), 3),
            (3, Action::key(1), 9),
        ]);
        let short = model_with(&[(1, Action::key(5), 9)]);
        let models = vec![long, short];
        let (idx, path) = plan_parallel(&models, 1, 8, 9).expect("one model reaches it");
        assert_eq!(idx, 1);
        assert_eq!(path.len(), 1);
    }

    #[test]
    fn levels_remaining_saturates() {
        assert_eq!(levels_remaining(7, 3), 4);
        assert_eq!(levels_remaining(7, 7), 0);
        assert_eq!(levels_remaining(7, 9), 0);
    }
}
