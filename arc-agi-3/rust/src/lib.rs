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

pub mod grid;
pub mod replay;
pub mod score;

pub use grid::{segment_layer, Grid, Node, Segmentation};
pub use score::{level_score, rhae, rhae_weighted};
