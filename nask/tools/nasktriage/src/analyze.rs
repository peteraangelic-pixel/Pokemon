//! Analiza różnicowa: ten sam endpoint widziany z dwóch własnych kont.
//!
//! Cel jest wąski i celowo taki: **wskazać hipotezy**, nie „znaleźć podatność”.
//! Podatność potwierdza człowiek, jednym żądaniem, na własnych danych.

use crate::har::{self, Entry, Har};
use crate::scope::{path_of_url, query_pairs};
use rayon::prelude::*;
use std::collections::{BTreeMap, BTreeSet};

#[derive(Debug, Clone)]
pub struct Account {
    pub label: String,
    /// Fragment nagłówka `Cookie`, który identyfikuje to konto (np. `sessionid=abc`).
    pub needle: String,
}

impl Account {
    pub fn parse(spec: &str) -> Result<Account, String> {
        let (label, needle) = spec
            .split_once(':')
            .ok_or_else(|| format!("konto musi mieć formę etykieta:fragment_cookie — jest: {spec}"))?;
        if label.is_empty() || needle.is_empty() {
            return Err(format!("puste pole w specyfikacji konta: {spec}"));
        }
        Ok(Account {
            label: label.to_string(),
            needle: needle.to_string(),
        })
    }
}

#[derive(Debug, Clone)]
pub struct Observation {
    pub account: Option<String>,
    pub source: String,
    pub method: String,
    pub template: String,
    pub path: String,
    pub status: i64,
    pub mime: String,
    pub body_len: usize,
    pub shape: Vec<String>,
    pub query_params: Vec<String>,
    pub cache_control: String,
    pub has_set_cookie: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Kind {
    /// Ten sam endpoint: jedno konto dostaje 2xx, drugie 401/403.
    PermissionAsymmetry,
    /// Endpoint z identyfikatorem w ścieżce zwraca 2xx dla różnych ID o identycznym kształcie.
    IdorCandidate,
    /// Parametr w URL nazywa się jak token/klucz/sesja — wycieka w logach i Referer.
    TokenInUrl,
    /// Żądanie bez ciasteczka dostało 2xx na endpoincie, który konto widziało z 2xx.
    UnauthAccess,
    /// Odpowiedź z danymi (`Set-Cookie` lub JSON) oznaczona jako publicznie cache'owalna.
    SensitiveCached,
}

impl Kind {
    pub fn as_str(&self) -> &'static str {
        match self {
            Kind::PermissionAsymmetry => "permission_asymmetry",
            Kind::IdorCandidate => "idor_candidate",
            Kind::TokenInUrl => "token_in_url",
            Kind::UnauthAccess => "unauth_access",
            Kind::SensitiveCached => "sensitive_cached",
        }
    }
    pub fn title(&self) -> &'static str {
        match self {
            Kind::PermissionAsymmetry => "Asymetria uprawnień (2xx vs 401/403)",
            Kind::IdorCandidate => "Kandydat na IDOR (jednolity kształt dla różnych ID)",
            Kind::TokenInUrl => "Token/klucz w URL",
            Kind::UnauthAccess => "Dostęp bez uwierzytelnienia",
            Kind::SensitiveCached => "Dane w odpowiedzi cache'owalnej publicznie",
        }
    }
}

#[derive(Debug, Clone)]
pub struct Finding {
    pub kind: Kind,
    pub method: String,
    pub template: String,
    pub detail: String,
    pub evidence: Vec<String>,
}

#[derive(Debug, Clone, Default)]
pub struct Report {
    pub observations: usize,
    pub accounts: Vec<String>,
    pub rows: Vec<Row>,
    pub findings: Vec<Finding>,
}

#[derive(Debug, Clone)]
pub struct Row {
    pub method: String,
    pub template: String,
    /// account label → (liczba żądań, zbiór statusów)
    pub per_account: BTreeMap<String, (usize, BTreeSet<i64>)>,
    pub anonymous: (usize, BTreeSet<i64>),
}

fn classify(account_specs: &[Account], cookie: Option<&str>) -> Option<String> {
    let cookie = cookie?;
    account_specs
        .iter()
        .find(|a| cookie.contains(&a.needle))
        .map(|a| a.label.clone())
}

fn observe(entries: &[Entry], accounts: &[Account]) -> Vec<Observation> {
    entries
        .par_iter()
        .filter(|e| !e.request.url.is_empty())
        .map(|e| {
            let path = path_of_url(&e.request.url);
            let text = e.response.content.text.as_deref().unwrap_or("");
            Observation {
                account: classify(accounts, e.cookie()),
                source: String::new(),
                method: e.request.method.to_ascii_uppercase(),
                template: har::template_path(&path),
                path,
                status: e.response.status,
                mime: e.response.content.mime_type.clone(),
                body_len: har::body_len(e),
                shape: har::json_shape(text),
                query_params: query_pairs(&e.request.url)
                    .into_iter()
                    .map(|(n, _)| n)
                    .collect(),
                cache_control: e
                    .response_header("cache-control")
                    .unwrap_or("")
                    .to_ascii_lowercase(),
                has_set_cookie: e.response_header("set-cookie").is_some(),
            }
        })
        .collect()
}

fn is_ok(status: i64) -> bool {
    (200..300).contains(&status)
}

fn is_denied(status: i64) -> bool {
    status == 401 || status == 403
}

/// Czy parametr nazywa się jak sekret?
pub fn looks_like_secret(name: &str) -> bool {
    let n = name.to_ascii_lowercase();
    const NEEDLES: [&str; 8] = [
        "token", "access_token", "apikey", "api_key", "key", "sig", "session", "auth",
    ];
    NEEDLES.iter().any(|needle| n == *needle || n.contains(needle))
}

pub fn analyze(hars: &[(String, Har)], accounts: &[Account]) -> Report {
    let mut all: Vec<Observation> = Vec::new();
    for (source, har) in hars {
        let mut obs = observe(&har.log.entries, accounts);
        for o in obs.iter_mut() {
            o.source = source.clone();
        }
        all.extend(obs);
    }

    let mut report = Report {
        observations: all.len(),
        accounts: accounts.iter().map(|a| a.label.clone()).collect(),
        ..Default::default()
    };

    // --- tabela endpointów -------------------------------------------------
    let mut rows: BTreeMap<(String, String), Row> = BTreeMap::new();
    for o in &all {
        let key = (o.method.clone(), o.template.clone());
        let row = rows.entry(key).or_insert_with(|| Row {
            method: o.method.clone(),
            template: o.template.clone(),
            per_account: BTreeMap::new(),
            anonymous: (0, BTreeSet::new()),
        });
        match &o.account {
            Some(label) => {
                let slot = row.per_account.entry(label.clone()).or_insert((0, BTreeSet::new()));
                slot.0 += 1;
                slot.1.insert(o.status);
            }
            None => {
                row.anonymous.0 += 1;
                row.anonymous.1.insert(o.status);
            }
        }
    }

    // --- findingi ----------------------------------------------------------
    let mut findings: Vec<Finding> = Vec::new();

    for ((method, template), row) in &rows {
        // 1. asymetria uprawnień między dwoma kontami
        let labels: Vec<&String> = row.per_account.keys().collect();
        for i in 0..labels.len() {
            for j in (i + 1)..labels.len() {
                let (a, b) = (&row.per_account[labels[i]], &row.per_account[labels[j]]);
                let a_ok = a.1.iter().any(|s| is_ok(*s));
                let b_ok = b.1.iter().any(|s| is_ok(*s));
                let a_denied = a.1.iter().any(|s| is_denied(*s));
                let b_denied = b.1.iter().any(|s| is_denied(*s));
                if (a_ok && b_denied) || (b_ok && a_denied) {
                    let (ok_l, den_l) = if a_ok && b_denied {
                        (labels[i], labels[j])
                    } else {
                        (labels[j], labels[i])
                    };
                    findings.push(Finding {
                        kind: Kind::PermissionAsymmetry,
                        method: method.clone(),
                        template: template.clone(),
                        detail: format!(
                            "konto {ok_l} dostało 2xx, konto {den_l} to samo 401/403 — sprawdź, czy to celowe"
                        ),
                        evidence: vec![format!(
                            "{ok_l}: {:?}   {den_l}: {:?}",
                            row.per_account[ok_l].1, row.per_account[den_l].1
                        )],
                    });
                }
            }
        }

        // 2. dostęp bez uwierzytelnienia na endpoincie używanym przez konto
        let account_ok = row
            .per_account
            .values()
            .any(|(_, st)| st.iter().any(|s| is_ok(*s)));
        if account_ok && row.anonymous.1.iter().any(|s| is_ok(*s)) {
            findings.push(Finding {
                kind: Kind::UnauthAccess,
                method: method.clone(),
                template: template.clone(),
                detail: "żądanie bez ciasteczka dostało 2xx; konto też dostaje 2xx".to_string(),
                evidence: vec![format!("anonimowo: {:?}", row.anonymous.1)],
            });
        }
    }

    // 3. IDOR-kandydat: ten sam wzorzec, ≥2 różne ID, 2xx, identyczny kształt
    let mut by_template: BTreeMap<(String, String), Vec<&Observation>> = BTreeMap::new();
    for o in all.iter().filter(|o| o.template.contains("{id}")) {
        by_template
            .entry((o.method.clone(), o.template.clone()))
            .or_default()
            .push(o);
    }
    for ((method, template), obs) in &by_template {
        let ok: Vec<&&Observation> = obs.iter().filter(|o| is_ok(o.status)).collect();
        let distinct_paths: BTreeSet<&String> = ok.iter().map(|o| &o.path).collect();
        let shapes: BTreeSet<&Vec<String>> = ok.iter().filter(|o| !o.shape.is_empty()).map(|o| &o.shape).collect();
        if distinct_paths.len() >= 2 && shapes.len() == 1 {
            let mut sample: Vec<String> = distinct_paths.iter().take(3).map(|p| (*p).clone()).collect();
            sample.sort();
            findings.push(Finding {
                kind: Kind::IdorCandidate,
                method: method.clone(),
                template: template.clone(),
                detail: format!(
                    "{} różnych identyfikatorów, wszystkie 2xx, identyczny zestaw kluczy JSON — sprawdź ID z konta A na sesji B",
                    distinct_paths.len()
                ),
                evidence: sample,
            });
        }
    }

    // 4. token w URL, 5. cache
    let mut seen_token: BTreeSet<(String, String)> = BTreeSet::new();
    for o in &all {
        for p in &o.query_params {
            if looks_like_secret(p) && seen_token.insert((o.method.clone(), p.clone())) {
                findings.push(Finding {
                    kind: Kind::TokenInUrl,
                    method: o.method.clone(),
                    template: o.template.clone(),
                    detail: format!("parametr `{p}` wygląda na sekret — sprawdź, czy trafia do logów/Referer i czy wygasa"),
                    evidence: vec![o.path.clone()],
                });
            }
        }
        if o.cache_control.contains("public")
            && (o.has_set_cookie || o.mime.contains("json"))
            && o.cache_control.contains("max-age")
        {
            findings.push(Finding {
                kind: Kind::SensitiveCached,
                method: o.method.clone(),
                template: o.template.clone(),
                detail: format!(
                    "Cache-Control: `{}`, treść: {}, Set-Cookie: {} — sprawdź cache deception",
                    o.cache_control, o.mime, o.has_set_cookie
                ),
                evidence: vec![o.path.clone()],
            });
        }
    }

    findings.sort_by(|a, b| {
        (a.kind.as_str(), &a.template, &a.method).cmp(&(b.kind.as_str(), &b.template, &b.method))
    });
    report.rows = rows.into_values().collect();
    report.findings = findings;
    report
}

pub fn render_markdown(report: &Report) -> String {
    let mut s = String::new();
    s.push_str("# Raport nasktriage (offline)\n\n");
    s.push_str(&format!(
        "Żądań w zrzutach: **{}**. Konta: {}.\n\n",
        report.observations,
        if report.accounts.is_empty() {
            "brak (podaj --account)".to_string()
        } else {
            report.accounts.join(", ")
        }
    ));

    s.push_str("## Hipotezy do ręcznego potwierdzenia\n\n");
    if report.findings.is_empty() {
        s.push_str("Brak. To też wynik: przy tych zrzutach nie ma czego potwierdzać.\n\n");
    } else {
        s.push_str("| # | typ | endpoint | co sprawdzić |\n|---:|---|---|---|\n");
        for (i, f) in report.findings.iter().enumerate() {
            s.push_str(&format!(
                "| {} | `{}` | `{} {}` | {} |\n",
                i + 1,
                f.kind.as_str(),
                f.method,
                f.template,
                f.detail.replace('|', "/")
            ));
        }
        s.push_str("\n### Dowody\n\n");
        for (i, f) in report.findings.iter().enumerate() {
            s.push_str(&format!("**{}.** {} `{} {}`\n", i + 1, f.kind.title(), f.method, f.template));
            for e in &f.evidence {
                s.push_str(&format!("- `{e}`\n"));
            }
            s.push('\n');
        }
    }

    s.push_str("## Mapa endpointów\n\n| metoda | endpoint | konta | anonimowo |\n|---|---|---|---|\n");
    for r in &report.rows {
        let per: Vec<String> = r
            .per_account
            .iter()
            .map(|(k, (n, st))| format!("{k}: {n}× {:?}", st))
            .collect();
        let anon = if r.anonymous.0 == 0 {
            "—".to_string()
        } else {
            format!("{}× {:?}", r.anonymous.0, r.anonymous.1)
        };
        s.push_str(&format!(
            "| {} | `{}` | {} | {} |\n",
            r.method,
            r.template,
            if per.is_empty() { "—".to_string() } else { per.join("<br>") },
            anon
        ));
    }
    s.push_str(
        "\n> Narzędzie nie wysyła żadnych żądań i nie zapisuje treści odpowiedzi.\n\
         > Potwierdzenie hipotezy = Twoje własne ręczne żądanie, na własnych kontach.\n",
    );
    s
}
