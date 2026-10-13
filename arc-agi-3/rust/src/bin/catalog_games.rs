use rayon::prelude::*;
use std::fs;
use std::path::Path;

fn main() {
    let games_dir = Path::new("arc-agi-3/games/environment_files");
    
    // Collect all game directories
    let games: Vec<_> = fs::read_dir(games_dir)
        .unwrap()
        .filter_map(|e| e.ok())
        .filter(|e| e.path().is_dir())
        .collect();
    
    println!("Found {} games\n", games.len());
    
    // Analyze games in parallel
    let results: Vec<_> = games.par_iter().map(|game_dir| {
        let game_name = game_dir.file_name().to_string_lossy().to_string();
        let game_path = game_dir.path();
        
        // Find the .py file
        let py_files: Vec<_> = fs::read_dir(&game_path)
            .unwrap()
            .filter_map(|e| e.ok())
            .filter(|e| e.path().extension().map_or(false, |ext| ext == "py"))
            .collect();
        
        if py_files.is_empty() {
            return format!("### {}\nNo .py file found\n", game_name);
        }
        
        let py_content = fs::read_to_string(py_files[0].path()).unwrap();
        
        // Extract key functions
        let mut analysis = format!("### {}\n\n", game_name);
        
        // Find bool-returning functions (likely win conditions)
        let bool_fns: Vec<_> = py_content.lines()
            .enumerate()
            .filter(|(_, line)| line.contains("-> bool:") || line.contains(") -> bool"))
            .map(|(i, line)| (i, line.trim()))
            .collect();
        
        if !bool_fns.is_empty() {
            analysis.push_str("**Boolean functions (potential win conditions):**\n");
            for (line_num, line) in bool_fns {
                analysis.push_str(&format!("- Line {}: `{}`\n", line_num + 1, line));
            }
            analysis.push('\n');
        }
        
        // Find class definitions
        let classes: Vec<_> = py_content.lines()
            .enumerate()
            .filter(|(_, line)| line.trim().starts_with("class ") && line.contains("Game"))
            .map(|(i, line)| (i, line.trim()))
            .collect();
        
        if !classes.is_empty() {
            analysis.push_str("**Game classes:**\n");
            for (line_num, line) in classes {
                analysis.push_str(&format!("- Line {}: `{}`\n", line_num + 1, line));
            }
            analysis.push('\n');
        }
        
        // Count levels
        let level_count = py_content.matches("Level(").count();
        analysis.push_str(&format!("**Levels:** {}\n", level_count));
        
        analysis
    }).collect();
    
    // Print results
    for result in results {
        println!("{}", result);
    }
}
