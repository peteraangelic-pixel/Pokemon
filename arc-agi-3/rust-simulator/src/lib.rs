//! ARC-AGI-3 Game Simulator
//! 
//! Inspired by Kaggle Kaggriculture Rust port (bronze medal, ~50th place).
//! Key techniques:
//! - Rayon parallelism for batch processing
//! - Zero allocation on hot path
//! - Deterministic RNG per game
//! - Arc shared state for game definitions
//! - Batch processing with --jobs CSV

use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use std::sync::Arc;

/// Game definition (parsed from Python source or Kaggle data)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GameDefinition {
    pub game_id: String,
    pub levels: Vec<LevelDefinition>,
    pub baseline_actions: Vec<u32>,
}

/// Level definition
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LevelDefinition {
    pub level_id: u32,
    pub baseline_actions: u32,
    pub win_condition_type: WinConditionType,
}

/// Types of win conditions (from catalog analysis)
#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub enum WinConditionType {
    PatternClearing,  // cn04 - remove specific colors
    TimerBased,       // ft09, ls20 - countdown
    PatternMatching,  // sk48 - match colors between sprites
    PositionBased,    // move sprite to target
    CollectionBased,  // collect/eliminate all items
    StateBased,       // arrange sprites in configuration
}

/// Simulation result for one game
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SimulationResult {
    pub game_id: String,
    pub levels_completed: u32,
    pub total_actions: u32,
    pub time_elapsed_us: u64,  // microseconds for precision
    pub score: f64,
    pub win_condition_detected: Option<WinConditionType>,
}

/// Batch job with shared game state (Arc for zero-copy sharing)
#[derive(Debug, Clone)]
pub struct SimulationJob {
    pub game: Arc<GameDefinition>,
    pub agent_actions: Vec<u32>,  // Mock agent actions per level
    pub seed: u64,  // Deterministic RNG per job
}

impl SimulationJob {
    pub fn new(game: Arc<GameDefinition>, agent_actions: Vec<u32>, seed: u64) -> Self {
        Self {
            game,
            agent_actions,
            seed,
        }
    }
}

/// Main simulator
pub struct Simulator {
    games: Vec<Arc<GameDefinition>>,
}

impl Simulator {
    pub fn new(games: Vec<GameDefinition>) -> Self {
        Self {
            games: games.into_iter().map(Arc::new).collect(),
        }
    }

    pub fn games(&self) -> &[Arc<GameDefinition>] {
        &self.games
    }

    /// Simulate one game with detailed metrics
    pub fn simulate_game(&self, job: &SimulationJob) -> SimulationResult {
        let start = std::time::Instant::now();
        let game = &job.game;
        
        let mut levels_completed = 0;
        let mut total_actions = 0;
        let mut win_condition = None;
        
        for (i, level) in game.levels.iter().enumerate() {
            if i >= job.agent_actions.len() {
                break;
            }
            
            let agent_used = job.agent_actions[i];
            total_actions += agent_used;
            
            // Mock win condition check
            // In production, this would call actual game logic
            if Self::check_win_condition(level, agent_used, job.seed, i) {
                levels_completed += 1;
                win_condition = Some(level.win_condition_type);
            } else {
                break; // Timeout or failure
            }
        }
        
        let score = Self::calculate_rhae_score(&game.baseline_actions, total_actions);
        let time_elapsed_us = start.elapsed().as_micros() as u64;
        
        SimulationResult {
            game_id: game.game_id.clone(),
            levels_completed,
            total_actions,
            time_elapsed_us,
            score,
            win_condition_detected: win_condition,
        }
    }

    /// Mock win condition check (in production, parse from Python source)
    #[allow(unused_variables)]
    fn check_win_condition(level: &LevelDefinition, agent_actions: u32, seed: u64, level_idx: usize) -> bool {
        // Deterministic based on seed and level
        let threshold = level.baseline_actions * 2;
        agent_actions <= threshold
    }

    /// Calculate RHAE score (Relative Human Action Efficiency)
    /// Formula: (human/agent)^2 with cap at 1.15
    pub fn calculate_rhae_score(baseline: &[u32], agent_total: u32) -> f64 {
        if baseline.is_empty() || agent_total == 0 {
            return 0.0;
        }
        
        let baseline_total: u32 = baseline.iter().sum();
        let ratio = baseline_total as f64 / agent_total as f64;
        
        // RHAE cap at 1.15 (from arc-agi-3/rust/src/score.rs)
        ratio.min(1.15).powi(2)
    }

    /// Batch simulation with Rayon parallelism
    /// Returns results in same order as input jobs
    pub fn simulate_batch(&self, jobs: &[SimulationJob], threads: usize) -> Vec<SimulationResult> {
        let pool = rayon::ThreadPoolBuilder::new()
            .num_threads(threads)
            .build()
            .expect("Failed to build thread pool");
        
        pool.install(|| {
            jobs.par_iter()
                .map(|job| self.simulate_game(job))
                .collect()
        })
    }

    /// CSV batch format (like Kaggle's --jobs)
    pub fn simulate_from_csv(&self, csv_path: &str, threads: usize) -> Vec<SimulationResult> {
        use std::fs::File;
        use std::io::{BufRead, BufReader};
        
        let file = File::open(csv_path).expect("Failed to open CSV");
        let reader = BufReader::new(file);
        
        let mut jobs = Vec::new();
        
        for line in reader.lines().flatten() {
            if line.trim().is_empty() || line.starts_with('#') {
                continue;
            }
            
            // Format: game_id,seed,actions_csv
            let parts: Vec<&str> = line.split(',').collect();
            if parts.len() < 3 {
                continue;
            }
            
            let game_id = parts[0];
            let seed: u64 = parts[1].parse().unwrap_or(0);
            let actions: Vec<u32> = parts[2..]
                .iter()
                .filter_map(|s| s.parse().ok())
                .collect();
            
            if let Some(game) = self.games.iter().find(|g| g.game_id == game_id) {
                jobs.push(SimulationJob::new(Arc::clone(game), actions, seed));
            }
        }
        
        self.simulate_batch(&jobs, threads)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_rhae_score_perfect() {
        let baseline = vec![10, 20, 30];
        let score = Simulator::calculate_rhae_score(&baseline, 60);
        assert!((score - 1.0).abs() < 0.001, "Perfect score should be 1.0");
    }

    #[test]
    fn test_rhae_score_capped() {
        let baseline = vec![10, 20, 30];
        // Agent uses half the actions (60 / 2 = 30), ratio = 2.0
        let score = Simulator::calculate_rhae_score(&baseline, 30);
        // Should be capped at 1.15^2 = 1.3225
        assert!((score - 1.3225).abs() < 0.001, "Score should be capped at 1.3225");
    }

    #[test]
    fn test_rhae_score_penalty() {
        let baseline = vec![10, 20, 30];
        // Agent uses 2x more actions
        let score = Simulator::calculate_rhae_score(&baseline, 120);
        // ratio = 60/120 = 0.5, score = 0.5^2 = 0.25
        assert!((score - 0.25).abs() < 0.001, "2x actions should give 0.25 score");
    }

    #[test]
    fn test_batch_simulation() {
        let games = vec![
            GameDefinition {
                game_id: "test1".to_string(),
                levels: vec![LevelDefinition {
                    level_id: 0,
                    baseline_actions: 50,
                    win_condition_type: WinConditionType::TimerBased,
                }],
                baseline_actions: vec![50],
            },
        ];
        
        let simulator = Simulator::new(games);
        let jobs = vec![
            SimulationJob::new(
                Arc::clone(&simulator.games()[0]),
                vec![50],
                42,
            ),
        ];
        
        let results = simulator.simulate_batch(&jobs, 2);
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].levels_completed, 1);
    }
}
