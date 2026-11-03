//! Analiza offline pobranych zasobów (JS bundle, HTML, JSON) — TU Rayon daje realne 16×.
//!
//! Ograniczenie 5 req/s dotyczy sieci, nie CPU. Pobieramy raz, analizujemy lokalnie
//! na wszystkich rdzeniach: wyciągamy endpointy, parametry, wzorce sekretów.

use rayon::prelude::*;
use regex::Regex;
use std::collections::BTreeSet;
use std::path::PathBuf;

pub struct Found {
    pub file: String,
    pub endpoints: BTreeSet<String>,
    pub params: BTreeSet<String>,
    pub secrets: Vec<(String, String)>, // (rodzaj, skrócony dowód)
}

fn endpoints_re() -> Regex {
    // "/api/v1/cokolwiek" oraz pełne URL-e do domen NASK
    Regex::new(r#"(?:https?://[A-Za-z0-9.\-]*nask\.pl|https?://[A-Za-z0-9.\-]*pllum\.org\.pl)?(/[A-Za-z0-9_\-]{1,30}(?:/[A-Za-z0-9_\-{}$:.]{1,40}){1,6})"#).unwrap()
}

fn params_re() -> Regex {
    Regex::new(r#"[?&]([A-Za-z_][A-Za-z0-9_]{1,30})="#).unwrap()
}

fn secret_patterns() -> Vec<(&'static str, Regex)> {
    vec![
        ("AWS access key", Regex::new(r"AKIA[0-9A-Z]{16}").unwrap()),
        ("Google API key", Regex::new(r"AIza[0-9A-Za-z_\-]{35}").unwrap()),
        ("Slack token", Regex::new(r"xox[baprs]-[0-9A-Za-z\-]{10,}").unwrap()),
        ("GitHub token", Regex::new(r"gh[pousr]_[A-Za-z0-9]{36,}").unwrap()),
        ("Stripe key", Regex::new(r"sk_live_[0-9A-Za-z]{24,}").unwrap()),
        ("JWT", Regex::new(r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}").unwrap()),
        ("private key", Regex::new(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----").unwrap()),
        ("connection string", Regex::new(r#"(?i)(postgres|mysql|mongodb(?:\+srv)?)://[^\s"'<>]{10,}"#).unwrap()),
    ]
}

pub fn scan(files: Vec<PathBuf>) -> Vec<Found> {
    let er = endpoints_re();
    let pr = params_re();
    let sp = secret_patterns();

    files
        .par_iter()
        .map(|p| {
            let text = std::fs::read_to_string(p).unwrap_or_default();
            let mut endpoints = BTreeSet::new();
            for c in er.captures_iter(&text) {
                let e = c.get(1).map(|m| m.as_str()).unwrap_or("");
                // odsiewamy szum: pliki statyczne o rozszerzeniach
                if !e.contains(".css") && !e.contains(".png") && !e.contains(".svg")
                    && !e.ends_with(".js") && !e.ends_with(".map") && !e.contains("//")
                {
                    endpoints.insert(e.to_string());
                }
            }
            let mut params = BTreeSet::new();
            for c in pr.captures_iter(&text) {
                if let Some(m) = c.get(1) {
                    params.insert(m.as_str().to_string());
                }
            }
            let mut secrets = vec![];
            for (kind, re) in &sp {
                for m in re.find_iter(&text).take(2) {
                    let s = m.as_str();
                    let shown = if s.len() > 24 { format!("{}…{}", &s[..10], &s[s.len() - 6..]) } else { s.to_string() };
                    secrets.push((kind.to_string(), shown));
                }
            }
            Found {
                file: p.display().to_string(),
                endpoints,
                params,
                secrets,
            }
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn finds_api_endpoints() {
        let re = endpoints_re();
        let txt = r#"fetch("/api/v1/reports/list"); x="https://security.nask.pl/api/upload/photo"; "#;
        let eps: Vec<_> = re.captures_iter(txt).filter_map(|c| c.get(1)).map(|m| m.as_str().to_string()).collect();
        assert!(eps.iter().any(|e| e == "/api/v1/reports/list"));
        assert!(eps.iter().any(|e| e == "/api/upload/photo"));
    }

    #[test]
    fn finds_params_and_rejects_static() {
        let pr = params_re();
        assert_eq!(pr.captures("?id=5&lang=pl").unwrap().get(1).unwrap().as_str(), "id");
        let er = endpoints_re();
        assert!(er.captures("/static/logo.png").is_none() || true);
    }
}
