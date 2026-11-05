use nasktriage::analyze::{self, Account, Report};
use nasktriage::har;
use nasktriage::rate::{TokenBucket, DEFAULT_RPS, MAX_RPS};
use nasktriage::scope::Scope;
use std::process::ExitCode;

fn usage() -> &'static str {
    "nasktriage — offline triage zrzutów HAR (bez ruchu sieciowego)

USAGE:
  nasktriage scope --scope <scope.json> [--host <host> | --url <url>]
  nasktriage scan <har...> [--account L:fragment_cookie]... [--scope <scope.json>]
                  [--md <out.md>] [--json <out.json>]
  nasktriage rate [--rps <n>]        # sprawdzenie limitera; > 5 = odmowa startu

PRZYKŁAD:
  nasktriage scan hive-A.har hive-B.har \\
      --account A:sessionid=aaa --account B:sessionid=bbb \\
      --scope scope.json --md raport.md"
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.is_empty() {
        println!("{}", usage());
        return ExitCode::from(2);
    }
    match args[0].as_str() {
        "scope" => cmd_scope(&args[1..]),
        "scan" => cmd_scan(&args[1..]),
        "rate" => cmd_rate(&args[1..]),
        "--help" | "-h" | "help" => {
            println!("{}", usage());
            ExitCode::SUCCESS
        }
        "--version" => {
            println!("nasktriage {} — {}", env!("CARGO_PKG_VERSION"), nasktriage::ABOUT);
            ExitCode::SUCCESS
        }
        other => {
            eprintln!("nieznana komenda: {other}\n\n{}", usage());
            ExitCode::from(2)
        }
    }
}

/// Prosty czytnik argumentów `--klucz wartość` + wartości pozycyjnych.
fn parse_args(args: &[String]) -> (Vec<String>, Vec<(String, String)>) {
    let mut positional = Vec::new();
    let mut flags: Vec<(String, String)> = Vec::new();
    let mut i = 0;
    while i < args.len() {
        let a = &args[i];
        if let Some(name) = a.strip_prefix("--") {
            let value = if i + 1 < args.len() && !args[i + 1].starts_with("--") {
                i += 1;
                args[i].clone()
            } else {
                "true".to_string()
            };
            flags.push((name.to_string(), value));
        } else {
            positional.push(a.clone());
        }
        i += 1;
    }
    (positional, flags)
}

fn flag<'a>(flags: &'a [(String, String)], name: &str) -> Option<&'a str> {
    flags
        .iter()
        .rev()
        .find(|(k, _)| k == name)
        .map(|(_, v)| v.as_str())
}

fn flags_all(flags: &[(String, String)], name: &str) -> Vec<String> {
    flags
        .iter()
        .filter(|(k, _)| k == name)
        .map(|(_, v)| v.clone())
        .collect()
}

fn cmd_scope(args: &[String]) -> ExitCode {
    let (_, flags) = parse_args(args);
    let path = match flag(&flags, "scope") {
        Some(p) => p.to_string(),
        None => {
            eprintln!("brak --scope <scope.json>");
            return ExitCode::from(2);
        }
    };
    let text = match std::fs::read_to_string(&path) {
        Ok(t) => t,
        Err(e) => {
            eprintln!("nie mogę przeczytać {path}: {e}");
            return ExitCode::from(2);
        }
    };
    let scope = match Scope::parse(&text) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("{e}");
            return ExitCode::from(2);
        }
    };
    if let Some(host) = flag(&flags, "host") {
        match scope.tier_of(host) {
            Some(t) => {
                println!("W ZAKRESIE: {host} ({})", t.as_str());
                return ExitCode::SUCCESS;
            }
            None => {
                println!("POZA ZAKRESEM: {host} — nie testować");
                return ExitCode::from(1);
            }
        }
    }
    if let Some(url) = flag(&flags, "url") {
        match scope.check_url(url) {
            Ok((h, t)) => {
                println!("W ZAKRESIE: {h} ({})", t.as_str());
                return ExitCode::SUCCESS;
            }
            Err(e) => {
                println!("ODRZUCONE: {e}");
                return ExitCode::from(1);
            }
        }
    }
    let mut n1 = 0;
    let mut n2 = 0;
    for (host, tier) in scope.hosts() {
        if tier == nasktriage::scope::Tier::Tier1 {
            n1 += 1;
        } else {
            n2 += 1;
        }
        println!("{:<32} {}", host, tier.as_str());
    }
    println!("\nhostów: {} (tier1: {n1}, tier2: {n2})", n1 + n2);
    ExitCode::SUCCESS
}

fn cmd_rate(args: &[String]) -> ExitCode {
    let (_, flags) = parse_args(args);
    let rps = flag(&flags, "rps")
        .and_then(|v| v.parse::<f64>().ok())
        .unwrap_or(DEFAULT_RPS);
    match TokenBucket::new(rps) {
        Ok(mut bucket) => {
            // sucho: 10 żądań w 1 sekundę powinno oddać dokładnie `rps` zgód
            let mut allowed = 0;
            for _ in 0..10 {
                if bucket.try_acquire(0.0) {
                    allowed += 1;
                }
            }
            println!(
                "limiter OK: rps={} (sufit regulaminowy {MAX_RPS}), w pierwszej sekundzie przepuszczono {allowed}",
                bucket.rps()
            );
            ExitCode::SUCCESS
        }
        Err(e) => {
            eprintln!("{e}");
            ExitCode::from(1)
        }
    }
}

fn cmd_scan(args: &[String]) -> ExitCode {
    let (positional, flags) = parse_args(args);
    if positional.is_empty() {
        eprintln!("podaj co najmniej jeden plik .har\n\n{}", usage());
        return ExitCode::from(2);
    }
    let mut accounts = Vec::new();
    for spec in flags_all(&flags, "account") {
        match Account::parse(&spec) {
            Ok(a) => accounts.push(a),
            Err(e) => {
                eprintln!("{e}");
                return ExitCode::from(2);
            }
        }
    }

    let scope = match flag(&flags, "scope") {
        Some(p) => match std::fs::read_to_string(p).map(|t| Scope::parse(&t)) {
            Ok(Ok(s)) => Some(s),
            Ok(Err(e)) => {
                eprintln!("{e}");
                return ExitCode::from(2);
            }
            Err(e) => {
                eprintln!("nie mogę przeczytać {p}: {e}");
                return ExitCode::from(2);
            }
        },
        None => None,
    };

    let mut parsed: Vec<(String, har::Har)> = Vec::new();
    for path in &positional {
        let text = match std::fs::read_to_string(path) {
            Ok(t) => t,
            Err(e) => {
                eprintln!("nie mogę przeczytać {path}: {e}");
                return ExitCode::from(2);
            }
        };
        match har::parse(&text) {
            Ok(h) => parsed.push((path.clone(), h)),
            Err(e) => {
                eprintln!("{path}: {e}");
                return ExitCode::from(2);
            }
        }
    }

    // Guard zakresu: raportujemy, ile żądań w zrzutach było poza §5. Nie blokujemy analizy
    // (to zrzut z przeglądarki), ale to jest sygnał: te hosty nie są upoważnione do testów.
    if let Some(scope) = &scope {
        let mut outside: std::collections::BTreeSet<String> = std::collections::BTreeSet::new();
        let mut total = 0usize;
        for (_, h) in &parsed {
            for e in &h.log.entries {
                if e.request.url.is_empty() {
                    continue;
                }
                total += 1;
                if scope.check_url(&e.request.url).is_err() {
                    if let Ok(host) = nasktriage::scope::host_of_url(&e.request.url) {
                        outside.insert(host);
                    }
                }
            }
        }
        if outside.is_empty() {
            println!("zakres: wszystkie {total} żądań do hostów z §5");
        } else {
            println!(
                "zakres: {} z {} żądań do hostów POZA §5: {}",
                outside.len(),
                total,
                outside.iter().cloned().collect::<Vec<_>>().join(", ")
            );
        }
    }

    let report: Report = analyze::analyze(&parsed, &accounts);
    let md = analyze::render_markdown(&report);
    println!("{md}");

    if let Some(out) = flag(&flags, "md") {
        if let Err(e) = std::fs::write(out, &md) {
            eprintln!("nie mogę zapisać {out}: {e}");
            return ExitCode::from(2);
        }
    }
    if let Some(out) = flag(&flags, "json") {
        let value = report_to_json(&report);
        match serde_json::to_string_pretty(&value) {
            Ok(text) => {
                if let Err(e) = std::fs::write(out, text) {
                    eprintln!("nie mogę zapisać {out}: {e}");
                    return ExitCode::from(2);
                }
            }
            Err(e) => {
                eprintln!("błąd serializacji: {e}");
                return ExitCode::from(2);
            }
        }
    }
    ExitCode::SUCCESS
}

fn report_to_json(report: &Report) -> serde_json::Value {
    use serde_json::{json, Value};
    let findings: Vec<Value> = report
        .findings
        .iter()
        .map(|f| {
            json!({
                "kind": f.kind.as_str(),
                "method": f.method,
                "template": f.template,
                "detail": f.detail,
                "evidence": f.evidence,
            })
        })
        .collect();
    let rows: Vec<Value> = report
        .rows
        .iter()
        .map(|r| {
            let per: Vec<Value> = r
                .per_account
                .iter()
                .map(|(k, (n, st))| json!({"account": k, "requests": n, "statuses": st}))
                .collect();
            json!({
                "method": r.method,
                "template": r.template,
                "accounts": per,
                "anonymous_requests": r.anonymous.0,
                "anonymous_statuses": r.anonymous.1,
            })
        })
        .collect();
    json!({
        "tool": "nasktriage",
        "version": env!("CARGO_PKG_VERSION"),
        "observations": report.observations,
        "accounts": report.accounts,
        "findings": findings,
        "endpoints": rows,
        "note": "Hipotezy, nie potwierdzone podatności. Potwierdzenie ręczne, na własnych kontach.",
    })
}
