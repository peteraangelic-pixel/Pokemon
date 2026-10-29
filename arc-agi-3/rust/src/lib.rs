//! `arc3` — CPU-side kernels for the ARC-AGI-3 (ARC Prize 2026) Kaggle competition.
//!
//! The agent's wall-clock budget on Kaggle is 9 hours, and ~99% of it goes to
//! LLM inference. That leaves no room for slow CPU work, and even less for the
//! offline analysis that tells us *where* the agent is wasting actions — which
//! is what RHAE punishes. This crate moves that work to Rust + rayon.
//!
//! Modules:
//! * [`grid`]    — segmentation of a frame into connected components (port of the
//!                 Duck harness' Python kernel, byte-identical output)
//! * [`score`]   — RHAE, the competition metric
//! * [`replay`]  — find wasted actions in recorded runs, sweep directories in parallel
//! * [`plan`]    — macro-action planner: turn one LLM decision into several actions

pub mod grid;
pub mod plan;
pub mod replay;
pub mod score;

pub use grid::{object_click_candidates, segment_layer, Grid, Node, Segmentation, ARC_COLOR_CHARS};
pub use score::{level_score, rhae, rhae_weighted};
pub use plan::{marginal_value, plan_to_goal, safe_prefix, Action, Batch, StateId, TransitionModel};
