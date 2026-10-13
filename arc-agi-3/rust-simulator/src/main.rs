//! ARC-AGI-3 Rust Simulator Benchmark
//! 
//! Based on Kaggle Kaggriculture techniques (bronze medal, ~50th place):
//! - Rayon parallelism for 4-8x speedup
//! - Arc shared state (zero-copy game definitions)
//! - Deterministic RNG per seed
//! - Batch processing with CSV jobs
//! - Microsecond precision timing

use arc3_simulator::{GameDefinition, LevelDefinition, SimulationJob, Simulator, WinConditionType};
use std::sync::Arc;
use std::time::Instant;

fn main() {
    println!("╔════════════════════════════════════════════════════════════╗");
    println!("║      ARC-AGI-3 Rust Simulator - Benchmark Suite         ║");
    println!("║  Based on Kaggle Kaggriculture (bronze medal, ~50th)    ║");
    println!("╚════════════════════════════════════════════════════════════╝\n");

    // Create 25 games with 6 levels each (like real ARC-AGI-3 demo games)
    let mut games = Vec::new();
    
    let win_conditions = [
        WinConditionType::TimerBased,
        WinConditionType::PatternClearing,
        WinConditionType::PatternMatching,
        WinConditionType::PositionBased,
        WinConditionType::CollectionBased,
    ];
    
    for i in 0..25 {
        let game_id = format!("game_{:02}", i);
        let mut levels = Vec::new();
        
        // Each game has 6 levels with increasing difficulty
        for j in 0..6 {
            levels.push(LevelDefinition {
                level_id: j,
                baseline_actions: 50 + j * 20,  // 50, 70, 90, 110, 130, 150
                win_condition_type: win_conditions[j % win_conditions.len()],
            });
        }
        
        let baseline_actions: Vec<u32> = levels.iter().map(|l| l.baseline_actions).collect();
        
        games.push(GameDefinition {
            game_id,
            levels,
            baseline_actions,
        });
    }

    println!("Created {} games with {} levels each\n", games.len(), 6);

    let simulator = Simulator::new(games);

    // Create jobs with varying agent strategies
    let jobs: Vec<SimulationJob> = simulator
        .games()
        .iter()
        .enumerate()
        .map(|(idx, game)| {
            // Simulate different agent strategies:
            // - Perfect agent (matches baseline)
            // - Slightly worse (1.5x baseline)
            // - Much worse (3x baseline - timeout)
            let strategy = idx % 3;
            let agent_actions = match strategy {
                0 => vec![50, 70, 90, 110, 130, 150],      // Perfect
                1 => vec![75, 105, 135, 165, 195, 225],    // 1.5x worse
                _ => vec![150, 210, 270, 330, 390, 450],   // 3x worse (timeout)
            };
            
            SimulationJob::new(Arc::clone(game), agent_actions, idx as u64)
        })
        .collect();

    println!("Simulating {} jobs with different thread counts...\n", jobs.len());
    println!("Agent strategies:");
    println!("  - Perfect (matches baseline)");
    println!("  - 1.5x worse (slightly inefficient)");
    println!("  - 3x worse (timeout/inefficient)\n");

    // Benchmark with different thread counts
    let thread_counts = [1, 4, 8, 16];
    let mut results_by_threads = Vec::new();

    for &threads in &thread_counts {
        let start = Instant::now();
        let results = simulator.simulate_batch(&jobs, threads);
        let elapsed = start.elapsed();

        let total_score: f64 = results.iter().map(|r| r.score).sum();
        let avg_score = total_score / results.len() as f64;
        let total_time_us: u64 = results.iter().map(|r| r.time_elapsed_us).sum();
        let avg_time_us = total_time_us / results.len() as u64;

        results_by_threads.push((threads, elapsed, avg_score, avg_time_us));

        println!(
            "Threads: {:2} | Total: {:8.3}ms | Per-job: {:6.1}µs | Avg score: {:.3}",
            threads,
            elapsed.as_micros() as f64 / 1000.0,
            avg_time_us,
            avg_score
        );
    }

    // Calculate speedup
    println!("\n═══════════════════════════════════════════════════════════");
    println!("Performance Analysis:");
    println!("═══════════════════════════════════════════════════════════");

    let baseline_time = results_by_threads[0].1;
    for &(threads, elapsed, _, _) in &results_by_threads {
        let speedup = baseline_time.as_nanos() as f64 / elapsed.as_nanos() as f64;
        println!(
            "Threads: {:2} | Speedup: {:.2}x vs baseline",
            threads, speedup
        );
    }

    // Score distribution
    println!("\n═══════════════════════════════════════════════════════════");
    println!("Score Distribution:");
    println!("═══════════════════════════════════════════════════════════");

    let final_results = &simulator.simulate_batch(&jobs, 4);
    let mut perfect = 0;
    let mut good = 0;
    let mut poor = 0;

    for result in final_results {
        if result.score >= 0.9 {
            perfect += 1;
        } else if result.score >= 0.5 {
            good += 1;
        } else {
            poor += 1;
        }
    }

    println!("Perfect (≥0.9):  {:3} games", perfect);
    println!("Good (0.5-0.9):  {:3} games", good);
    println!("Poor (<0.5):     {:3} games", poor);

    println!("\n═══════════════════════════════════════════════════════════");
    println!("Benchmark complete!");
    println!("═══════════════════════════════════════════════════════════");
}
