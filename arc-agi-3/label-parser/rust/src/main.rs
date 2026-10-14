use rayon::prelude::*;
use regex::Regex;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::env;
use std::error::Error;
use std::fs;
use std::time::Instant;

/// Akcja z odpowiedzi modelu
#[derive(Debug, Clone, Serialize, Deserialize)]
struct Action {
    action: String,
    #[serde(default)]
    reasoning: Option<String>,
    #[serde(default)]
    row: Option<i32>,
    #[serde(default)]
    col: Option<i32>,
}

/// Odpowiedź modelu z metadanymi
#[derive(Debug, Clone, Serialize, Deserialize)]
struct ModelResponse {
    id: String,
    response: String,
    #[serde(default)]
    valid_actions: Vec<String>,
}

/// Wynik parsowania jednej odpowiedzi
#[derive(Debug, Clone, Serialize)]
struct ParseResult {
    response_id: String,
    actions_found: usize,
    actions_valid: usize,
    actions_invalid: usize,
    parse_success: bool,
    error: Option<String>,
}

/// Statystyki zbiorcze
#[derive(Debug, Clone, Serialize)]
struct Statistics {
    total_responses: usize,
    successful_parses: usize,
    failed_parses: usize,
    total_actions: usize,
    valid_actions: usize,
    invalid_actions: usize,
    success_rate: f64,
    validity_rate: f64,
    parsing_time_ms: u128,
}

/// Ekstrahuje JSON z bloku markdown ```json ... ```
fn extract_json_from_markdown(text: &str) -> Option<String> {
    let pattern = Regex::new(r"```json\s*(\[[\s\S]*?\]|\{[\s\S]*?\})\s*```").ok()?;
    
    if let Some(caps) = pattern.captures(text) {
        return caps.get(1).map(|m| m.as_str().to_string());
    }
    
    // Fallback: szukamy samego [...] lub {...}
    let pattern = Regex::new(r"(\[[\s\S]*?\]|\{[\s\S]*?\})").ok()?;
    if let Some(caps) = pattern.captures(text) {
        return caps.get(1).map(|m| m.as_str().to_string());
    }
    
    None
}

/// Parsuje JSON z akcjami
fn parse_json_actions(json_str: &str) -> Result<Vec<Action>, String> {
    // Spróbuj parsować jako listę
    if let Ok(actions) = serde_json::from_str::<Vec<Action>>(json_str) {
        return Ok(actions);
    }
    
    // Spróbuj parsować jako pojedynczy obiekt
    if let Ok(action) = serde_json::from_str::<Action>(json_str) {
        return Ok(vec![action]);
    }
    
    Err("Nieprawidłowy JSON".to_string())
}

/// Wyciąga akcje z tekstu swobodnego
fn extract_actions_from_text(text: &str) -> Vec<Action> {
    let mut actions = Vec::new();
    
    // Akcje kierunkowe
    if let Ok(pattern) = Regex::new(r"(?i)\b(RIGHT|LEFT|UP|DOWN)\b") {
        for cap in pattern.find_iter(text) {
            actions.push(Action {
                action: cap.as_str().to_uppercase(),
                reasoning: None,
                row: None,
                col: None,
            });
        }
    }
    
    // Akcje MOUSE(x,y)
    if let Ok(pattern) = Regex::new(r"(?i)MOUSE\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)") {
        for cap in pattern.captures_iter(text) {
            let row: i32 = cap[1].parse().unwrap_or(0);
            let col: i32 = cap[2].parse().unwrap_or(0);
            actions.push(Action {
                action: format!("MOUSE({}, {})", row, col),
                reasoning: None,
                row: Some(row),
                col: Some(col),
            });
        }
    }
    
    actions
}

/// Parsuje etykiety z odpowiedzi modelu
fn parse_labels(response: &str) -> Result<Vec<Action>, String> {
    if response.trim().is_empty() {
        return Err("Pusta odpowiedź".to_string());
    }
    
    // Próba 1: JSON z markdown
    if let Some(json_str) = extract_json_from_markdown(response) {
        if let Ok(actions) = parse_json_actions(&json_str) {
            return Ok(actions);
        }
    }
    
    // Próba 2: Czysty JSON
    if response.trim().starts_with('[') || response.trim().starts_with('{') {
        if let Ok(actions) = parse_json_actions(response) {
            return Ok(actions);
        }
    }
    
    // Próba 3: Tekst swobodny
    let actions = extract_actions_from_text(response);
    if !actions.is_empty() {
        return Ok(actions);
    }
    
    Err("Nie udało się wyciągnąć żadnych akcji".to_string())
}

/// Waliduje czy akcja jest poprawna
fn is_action_valid(action: &Action, valid_actions: &[String]) -> bool {
    let action_name = action.action.to_uppercase();
    
    for valid in valid_actions {
        let valid_upper = valid.to_uppercase();
        
        if valid_upper.starts_with("MOUSE") {
            // MOUSE(x,y) - sprawdź tylko prefix
            if action_name.starts_with("MOUSE") {
                return true;
            }
        } else if action_name == valid_upper {
            return true;
        }
    }
    
    false
}

/// Parsuje jedną odpowiedź modelu
fn parse_response(model_response: &ModelResponse) -> ParseResult {
    match parse_labels(&model_response.response) {
        Ok(actions) => {
            let total = actions.len();
            let valid_count = actions
                .iter()
                .filter(|a| is_action_valid(a, &model_response.valid_actions))
                .count();
            
            ParseResult {
                response_id: model_response.id.clone(),
                actions_found: total,
                actions_valid: valid_count,
                actions_invalid: total - valid_count,
                parse_success: true,
                error: None,
            }
        }
        Err(e) => ParseResult {
            response_id: model_response.id.clone(),
            actions_found: 0,
            actions_valid: 0,
            actions_invalid: 0,
            parse_success: false,
            error: Some(e),
        },
    }
}

/// Analizuje wiele odpowiedzi paralelnie
fn analyze_responses(responses: &[ModelResponse]) -> (Vec<ParseResult>, Statistics) {
    let start = Instant::now();
    
    // Parsuj wszystkie odpowiedzi paralelnie używając rayon
    let results: Vec<ParseResult> = responses.par_iter().map(parse_response).collect();
    
    let elapsed = start.elapsed().as_millis();
    
    // Oblicz statystyki
    let total = results.len();
    let successful = results.iter().filter(|r| r.parse_success).count();
    let failed = total - successful;
    
    let total_actions: usize = results.iter().map(|r| r.actions_found).sum();
    let valid_actions: usize = results.iter().map(|r| r.actions_valid).sum();
    let invalid_actions: usize = results.iter().map(|r| r.actions_invalid).sum();
    
    let success_rate = if total > 0 {
        successful as f64 / total as f64
    } else {
        0.0
    };
    
    let validity_rate = if total_actions > 0 {
        valid_actions as f64 / total_actions as f64
    } else {
        0.0
    };
    
    let stats = Statistics {
        total_responses: total,
        successful_parses: successful,
        failed_parses: failed,
        total_actions,
        valid_actions,
        invalid_actions,
        success_rate,
        validity_rate,
        parsing_time_ms: elapsed,
    };
    
    (results, stats)
}

fn main() -> Result<(), Box<dyn Error>> {
    let args: Vec<String> = env::args().collect();
    
    if args.len() < 2 {
        eprintln!("Użycie: {} <plik_z_odpowiedziami.json>", args[0]);
        eprintln!("\nFormat pliku JSON:");
        eprintln!("[");
        eprintln!("  {{");
        eprintln!("    \"id\": \"response_1\",");
        eprintln!("    \"response\": \"```json\\\\n[{\\\"action\\\": \\\"RIGHT\\\"}]\\\\n```\",");
        eprintln!("    \"valid_actions\": [\"RIGHT\", \"LEFT\", \"UP\", \"DOWN\", \"MOUSE\"]");
        eprintln!("  }},");
        eprintln!("  ...");
        eprintln!("]");
        std::process::exit(1);
    }
    
    let input_file = &args[1];
    println!("📖 Wczytywanie odpowiedzi z {}", input_file);
    
    let content = fs::read_to_string(input_file)?;
    let responses: Vec<ModelResponse> = serde_json::from_str(&content)?;
    
    println!("📊 Znaleziono {} odpowiedzi", responses.len());
    println!("🔍 Analiza paralelna z rayon...\n");
    
    let (results, stats) = analyze_responses(&responses);
    
    // Wydrukuj wyniki
    println!("=== Wyniki parsowania ===\n");
    
    for result in &results {
        if result.parse_success {
            println!(
                "✓ {} - {} akcji ({} poprawnych, {} niepoprawnych)",
                result.response_id, result.actions_found, result.actions_valid, result.actions_invalid
            );
        } else {
            println!(
                "✗ {} - BŁĄD: {}",
                result.response_id,
                result.error.as_deref().unwrap_or("nieznany")
            );
        }
    }
    
    // Wydrukuj statystyki
    println!("\n=== Statystyki ===\n");
    println!("Łączna liczba odpowiedzi: {}", stats.total_responses);
    println!("Udane parsowania: {} ({:.1}%)", 
        stats.successful_parses,
        stats.success_rate * 100.0
    );
    println!("Nieudane parsowania: {}", stats.failed_parses);
    println!("Łączna liczba akcji: {}", stats.total_actions);
    println!("Poprawne akcje: {} ({:.1}%)",
        stats.valid_actions,
        stats.validity_rate * 100.0
    );
    println!("Niepoprawne akcje: {}", stats.invalid_actions);
    println!("Czas parsowania: {} ms", stats.parsing_time_ms);
    
    if stats.parsing_time_ms > 0 && stats.total_responses > 0 {
        let per_response = stats.parsing_time_ms as f64 / stats.total_responses as f64;
        println!("Średni czas na odpowiedź: {:.2} ms", per_response);
    }
    
    // Zapisz statystyki do JSON
    let stats_json = serde_json::to_string_pretty(&stats)?;
    let output_file = format!("{}.stats.json", input_file.trim_end_matches(".json"));
    fs::write(&output_file, stats_json)?;
    println!("\n💾 Statystyki zapisano do {}", output_file);
    
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_extract_json_from_markdown() {
        let text = "Here are actions:\n```json\n[{\"action\": \"RIGHT\"}]\n```";
        let result = extract_json_from_markdown(text);
        assert!(result.is_some());
        assert!(result.unwrap().contains("RIGHT"));
    }
    
    #[test]
    fn test_parse_json_actions() {
        let json = r#"[{"action": "RIGHT"}, {"action": "DOWN"}]"#;
        let result = parse_json_actions(json);
        assert!(result.is_ok());
        assert_eq!(result.unwrap().len(), 2);
    }
    
    #[test]
    fn test_extract_actions_from_text() {
        let text = "I'll move RIGHT then MOUSE(5,10) then DOWN";
        let actions = extract_actions_from_text(text);
        assert_eq!(actions.len(), 3);
        assert_eq!(actions[0].action, "RIGHT");
        assert!(actions[1].action.starts_with("MOUSE"));
        assert_eq!(actions[2].action, "DOWN");
    }
    
    #[test]
    fn test_is_action_valid() {
        let action = Action {
            action: "RIGHT".to_string(),
            reasoning: None,
            row: None,
            col: None,
        };
        let valid = vec!["RIGHT".to_string(), "LEFT".to_string(), "UP".to_string(), "DOWN".to_string()];
        assert!(is_action_valid(&action, &valid));
        
        let invalid_action = Action {
            action: "JUMP".to_string(),
            reasoning: None,
            row: None,
            col: None,
        };
        assert!(!is_action_valid(&invalid_action, &valid));
    }
    
    #[test]
    fn test_parse_labels_json() {
        let response = r#"```json
[{"action": "RIGHT"}, {"action": "DOWN"}]
```"#;
        let result = parse_labels(response);
        assert!(result.is_ok());
        assert_eq!(result.unwrap().len(), 2);
    }
    
    #[test]
    fn test_parse_labels_text() {
        let response = "I'll move RIGHT then DOWN";
        let result = parse_labels(response);
        assert!(result.is_ok());
        assert_eq!(result.unwrap().len(), 2);
    }
}
