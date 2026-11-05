//! Guard zakresu: dokładna lista hostów z §5 programu, bez wildcardu.
//!
//! Reguła, którą ten moduł wymusza: **host spoza listy nie jest testowany**, a przekierowanie
//! na host spoza listy nie rozszerza upoważnienia. Lista jest danymi (`scope.json`), nie kodem.

use serde::Deserialize;
use std::collections::BTreeMap;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum Tier {
    Tier1,
    Tier2,
}

impl Tier {
    pub fn as_str(self) -> &'static str {
        match self {
            Tier::Tier1 => "tier1",
            Tier::Tier2 => "tier2",
        }
    }
}

#[derive(Debug, Deserialize, Default)]
struct RawScope {
    #[serde(default)]
    tier1: Vec<String>,
    #[serde(default)]
    tier2: Vec<String>,
}

#[derive(Debug, Clone, Default)]
pub struct Scope {
    hosts: BTreeMap<String, Tier>,
}

/// Normalizacja hosta: małe litery, bez kropki na końcu, bez portu, bez userinfo.
pub fn normalize_host(raw: &str) -> String {
    let mut h = raw.trim().to_ascii_lowercase();
    if let Some(at) = h.rfind('@') {
        h = h[at + 1..].to_string();
    }
    if let Some(colon) = h.rfind(':') {
        let tail = &h[colon + 1..];
        if !tail.is_empty() && tail.chars().all(|c| c.is_ascii_digit()) {
            h.truncate(colon);
        }
    }
    while h.ends_with('.') {
        h.pop();
    }
    h
}

/// Host z URL-a. Odrzuca schematy inne niż http/https — narzędzie nie dotyka innych protokołów.
pub fn host_of_url(url: &str) -> Result<String, String> {
    let lower = url.trim().to_ascii_lowercase();
    let rest = if let Some(r) = lower.strip_prefix("https://") {
        r
    } else if let Some(r) = lower.strip_prefix("http://") {
        r
    } else {
        return Err(format!("nieobsługiwany schemat (tylko http/https): {url}"));
    };
    let end = rest.find(['/', '?', '#']).unwrap_or(rest.len());
    let authority = &rest[..end];
    if authority.is_empty() {
        return Err(format!("brak hosta w URL: {url}"));
    }
    Ok(normalize_host(authority))
}

/// Ścieżka z URL-a (bez query i fragmentu); "/" gdy brak.
pub fn path_of_url(url: &str) -> String {
    let no_frag = url.split('#').next().unwrap_or(url);
    let after_scheme = match no_frag.find("://") {
        Some(i) => &no_frag[i + 3..],
        None => no_frag,
    };
    let start = match after_scheme.find('/') {
        Some(i) => i,
        None => return "/".to_string(),
    };
    let path_and_query = &after_scheme[start..];
    let path = path_and_query.split('?').next().unwrap_or("/");
    if path.is_empty() {
        "/".to_string()
    } else {
        path.to_string()
    }
}

/// Pary `name=value` z query stringa (bez dekodowania — do wykrywania nazw parametrów).
pub fn query_pairs(url: &str) -> Vec<(String, String)> {
    let mut out = Vec::new();
    let q = match url.split_once('?') {
        Some((_, q)) => q.split('#').next().unwrap_or(q),
        None => return out,
    };
    for part in q.split('&') {
        if part.is_empty() {
            continue;
        }
        let (name, value) = match part.split_once('=') {
            Some((n, v)) => (n, v),
            None => (part, ""),
        };
        out.push((name.to_string(), value.to_string()));
    }
    out
}

impl Scope {
    pub fn parse(json: &str) -> Result<Scope, String> {
        let raw: RawScope =
            serde_json::from_str(json).map_err(|e| format!("scope.json nie jest poprawny: {e}"))?;
        let mut hosts = BTreeMap::new();
        for h in raw.tier1 {
            hosts.insert(normalize_host(&h), Tier::Tier1);
        }
        for h in raw.tier2 {
            hosts.insert(normalize_host(&h), Tier::Tier2);
        }
        if hosts.is_empty() {
            return Err("scope.json nie zawiera ani jednego hosta".to_string());
        }
        Ok(Scope { hosts })
    }

    pub fn hosts(&self) -> impl Iterator<Item = (&String, Tier)> {
        self.hosts.iter().map(|(h, t)| (h, *t))
    }

    pub fn tier_of(&self, host: &str) -> Option<Tier> {
        self.hosts.get(&normalize_host(host)).copied()
    }

    /// `Ok((host, tier))` tylko dla hosta z listy; inaczej `Err` z powodem.
    pub fn check_url(&self, url: &str) -> Result<(String, Tier), String> {
        let host = host_of_url(url)?;
        match self.tier_of(&host) {
            Some(t) => Ok((host, t)),
            None => Err(format!("host poza zakresem programu: {host}")),
        }
    }
}
