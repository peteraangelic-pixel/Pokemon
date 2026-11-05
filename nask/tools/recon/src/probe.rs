//! Prober: pobiera nagłówki i ciało z jednego hosta, z twardym limiterem i guardem zakresu.
//!
//! Ten moduł NIE wysyła payloadów atakujących. Robi dokładnie to, co robi przeglądarka
//! i nagłówek `security.txt`: GET na ścieżkę i odczyt odpowiedzi.

use crate::ratelimit::RateLimiter;
use crate::scope;
use serde_json::{json, Value};
use std::time::Duration;

pub struct Probe {
    pub host: String,
    pub path: String,
    pub status: u16,
    pub content_type: String,
    pub size: usize,
    pub server: String,
    pub powered_by: String,
    pub title: String,
    pub generator: String,
    pub forms: usize,
    pub cookies: usize,
    pub tech_hints: Vec<String>,
    pub in_scope: bool,
    pub tier: u8,
}

const UA: &str = "Mozilla/5.0 (compatible; naskrecon/0.1; kontakt: uczestnik hack.cert.pl)";

fn header(headers: &str, name: &str) -> String {
    for line in headers.lines() {
        let line = line.trim_end_matches('\r');
        if let Some((k, v)) = line.split_once(':') {
            if k.eq_ignore_ascii_case(name) {
                return v.trim().to_string();
            }
        }
    }
    String::new()
}

fn strip_tags(s: &str) -> String {
    let mut out = String::new();
    let mut inside = false;
    for c in s.chars() {
        match c {
            '<' => inside = true,
            '>' => { inside = false; }
            _ if !inside => out.push(c),
            _ => {}
        }
    }
    out.trim().to_string()
}

fn find_title(html: &str) -> String {
    let lower = html.to_ascii_lowercase();
    if let (Some(a), Some(b)) = (lower.find("<title"), lower.find("</title>")) {
        if let Some(gt) = lower[a..].find('>') {
            let start = a + gt + 1;
            if start < b {
                return strip_tags(&html[start..b]).chars().take(70).collect();
            }
        }
    }
    String::new()
}

fn find_generator(html: &str) -> String {
    let lower = html.to_ascii_lowercase();
    let mut idx = 0;
    while let Some(p) = lower[idx..].find("name=\"generator\"") {
        let abs = idx + p;
        if let Some(c) = lower[abs..].find("content=\"") {
            let s = abs + c + 9;
            if let Some(e) = html[s..].find('"') {
                return html[s..s + e].chars().take(60).collect();
            }
        }
        idx = abs + 1;
    }
    String::new()
}

/// Heurystyki technologiczne — wyłącznie na podstawie publicznej odpowiedzi.
fn tech_hints(headers: &str, body: &str) -> Vec<String> {
    let mut v = vec![];
    let h = headers.to_ascii_lowercase();
    let b = body.to_ascii_lowercase();
    let check = |name: &str, hit: bool, v: &mut Vec<String>| {
        if hit { v.push(name.to_string()) }
    };
    check("azure", h.contains("x-azure"), &mut v);
    check("envoy", h.contains("x-envoy"), &mut v);
    check("cloudflare", h.contains("cloudflare") || h.contains("cf-ray"), &mut v);
    check("akamai", h.contains("x-iinfo"), &mut v);
    check("nextjs", h.contains("x-nextjs") || b.contains("__next_data__"), &mut v);
    check("nginx", h.contains("server: nginx"), &mut v);
    check("iis", h.contains("microsoft-iis"), &mut v);
    check("wordpress", h.contains("wp-content") || b.contains("/wp-content/"), &mut v);
    check("drupal", b.contains("drupal") || h.contains("x-drupal"), &mut v);
    check("django", b.contains("csrfmiddlewaretoken"), &mut v);
    check("laravel", h.contains("laravel_session"), &mut v);
    check("aspnet", h.contains("asp.net") || h.contains("aspnet"), &mut v);
    check("java", h.contains("jsessionid"), &mut v);
    check("php", h.contains("phpsessid"), &mut v);
    check("graphql_hint", b.contains("graphql"), &mut v);
    check("swagger_hint", b.contains("swagger") || b.contains("openapi"), &mut v);
    check("gitlab", b.contains("gitlab") || h.contains("gitlab"), &mut v);
    check("keycloak", b.contains("keycloak"), &mut v);
    check("waf_block", b.contains("access denied") || b.contains("request rejected"), &mut v);
    v
}

pub fn probe(host: &str, path: &str, rl: &RateLimiter) -> Probe {
    rl.acquire();
    let url = format!("https://{}{}", host, path);
    let mut status = 0u16;
    let mut ct = String::new();
    let mut body = String::new();
    let mut headers = String::new();

    let agent = ureq::AgentBuilder::new()
        .timeout_connect(Duration::from_secs(10))
        .timeout_read(Duration::from_secs(20))
        .user_agent(UA)
        .redirects(0) // nie podążamy za redirectami — chcemy widzieć Location
        .build();

    match agent.get(&url).call() {
        Ok(resp) => {
            status = resp.status();
            ct = resp.header("content-type").unwrap_or("").to_string();
            for name in resp.headers_names() {
                if let Some(v) = resp.header(&name) {
                    headers.push_str(&format!("{}: {}\n", name, v));
                }
            }
            body = resp.into_string().unwrap_or_default();
        }
        Err(ureq::Error::Status(code, resp)) => {
            status = code;
            ct = resp.header("content-type").unwrap_or("").to_string();
            for name in resp.headers_names() {
                if let Some(v) = resp.header(&name) {
                    headers.push_str(&format!("{}: {}\n", name, v));
                }
            }
            body = resp.into_string().unwrap_or_default();
        }
        Err(_) => {
            status = 0;
        }
    }

    let scope_hit = scope::in_scope(host);
    Probe {
        host: host.to_string(),
        path: path.to_string(),
        status,
        content_type: ct,
        size: body.len(),
        server: header(&headers, "server"),
        powered_by: header(&headers, "x-powered-by"),
        title: find_title(&body),
        generator: find_generator(&body),
        forms: body.to_ascii_lowercase().matches("<form").count(),
        cookies: headers.to_ascii_lowercase().matches("set-cookie:").count(),
        tech_hints: tech_hints(&headers, &body),
        in_scope: scope_hit.is_some(),
        tier: scope_hit.map(|s| s.tier).unwrap_or(0),
    }
}

impl Probe {
    pub fn to_json(&self) -> Value {
        json!({
            "host": self.host,
            "path": self.path,
            "in_scope": self.in_scope,
            "tier": self.tier,
            "status": self.status,
            "content_type": self.content_type,
            "bytes": self.size,
            "server": self.server,
            "x_powered_by": self.powered_by,
            "title": self.title,
            "generator": self.generator,
            "forms": self.forms,
            "set_cookie": self.cookies,
            "tech": self.tech_hints,
        })
    }
}
