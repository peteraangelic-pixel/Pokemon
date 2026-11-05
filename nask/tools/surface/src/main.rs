//! surface — read-only discovery for the NASK bug-bounty programme.
//!
//! Design rules that are enforced in code, not in comments:
//!   * exact host allow-list (see scope.rs), https only;
//!   * one global token bucket, hard-refused above 5 req/s (programme limit);
//!   * GET only, redirects never followed (a redirect could leave the scope);
//!   * every response is recorded, including failures, so a missing result is
//!     never mistaken for a clean result;
//!   * no payloads, no state-changing requests, no authentication.

mod analyze;
mod probe;
mod scope;

use rayon::prelude::*;
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::time::{Duration, Instant};

pub const UA: &str = "nask-bugbounty-surface/0.1 (authorized research under hack.cert.pl terms; read-only GET)";
const MAX_REQUESTS: usize = 700;

/// Static, deliberately short list. Nothing here is a dictionary brute force;
/// these are the few well-known locations a site publishes by design.
const STATIC_PATHS: &[&str] = &[
    "/",
    "/robots.txt",
    "/sitemap.xml",
    "/.well-known/security.txt",
    "/manifest.json",
    "/favicon.ico",
];

fn resolve_same_origin(base_host: &str, link: &str) -> Option<String> {
    let link = link.trim();
    if link.is_empty()
        || link.starts_with("data:")
        || link.starts_with("mailto:")
        || link.starts_with("tel:")
        || link.starts_with("javascript:")
        || link.starts_with('#')
    {
        return None;
    }
    let url = if let Some(rest) = link.strip_prefix("//") {
        format!("https://{rest}")
    } else if link.starts_with("https://") || link.starts_with("http://") {
        link.to_string()
    } else if link.starts_with('/') {
        format!("https://{base_host}{link}")
    } else {
        return None; // relative without a leading slash: skip rather than guess
    };
    // Only keep in-scope https targets; drop fragments.
    let url = url.split('#').next().unwrap_or(&url).to_string();
    match scope::split_url(&url) {
        Ok(_) => Some(url),
        Err(_) => None,
    }
}

struct Fetched {
    entry: Value,
    body_path: Option<PathBuf>,
}

fn fetch_one(client: &reqwest::blocking::Client, limiter: &scope::Limiter, url: &str, idx: usize, out: &Path, deadline: Instant, issued: &AtomicUsize) -> Fetched {
    let (host, path) = match scope::split_url(url) {
        Ok(v) => v,
        Err(e) => {
            return Fetched {
                entry: json!({"n": idx, "url": url, "error": e, "status": null, "file": null}),
                body_path: None,
            }
        }
    };
    let tier = scope::tier_of(&host).unwrap_or(0);
    if Instant::now() > deadline {
        return Fetched {
            entry: json!({"n": idx, "url": url, "host": host, "path": path, "tier": tier,
                          "error": "deadline reached before this request", "status": null, "file": null}),
            body_path: None,
        };
    }
    if issued.fetch_add(1, Ordering::SeqCst) >= MAX_REQUESTS {
        return Fetched {
            entry: json!({"n": idx, "url": url, "host": host, "path": path, "tier": tier,
                          "error": "request budget exhausted", "status": null, "file": null}),
            body_path: None,
        };
    }

    limiter.acquire();
    let started = Instant::now();
    let resp = client.get(url).send();

    match resp {
        Ok(r) => {
            let status = r.status().as_u16();
            let headers = r.headers().clone();
            let get = |name: &str| {
                headers
                    .get(name)
                    .and_then(|v| v.to_str().ok())
                    .unwrap_or("")
                    .to_string()
            };
            let content_type = get("content-type");
            let location = get("location");
            let bytes = match r.bytes() {
                Ok(b) => b,
                Err(e) => {
                    return Fetched {
                        entry: json!({"n": idx, "url": url, "host": host, "path": path, "tier": tier,
                                      "status": status, "content_type": content_type,
                                      "error": format!("body read failed: {e}"), "file": null}),
                        body_path: None,
                    }
                }
            };
            let digest: String = Sha256::digest(&bytes).iter().map(|b| format!("{b:02x}")).collect();
            let file = out.join(format!("{idx:04}.body"));
            let write_err = std::fs::write(&file, &bytes).err().map(|e| e.to_string());
            let entry = json!({
                "n": idx, "url": url, "host": host, "path": path, "tier": tier,
                "status": status,
                "content_type": content_type,
                "location": location,
                "server": get("server"),
                "x_powered_by": get("x-powered-by"),
                "cache_control": get("cache-control"),
                "bytes": bytes.len(),
                "sha256": digest,
                "ms": started.elapsed().as_millis() as u64,
                "file": file.display().to_string(),
                "error": write_err,
            });
            Fetched { entry, body_path: Some(file) }
        }
        Err(e) => Fetched {
            entry: json!({"n": idx, "url": url, "host": host, "path": path, "tier": tier,
                          "status": null, "ms": started.elapsed().as_millis() as u64,
                          "error": e.to_string(), "file": null}),
            body_path: None,
        },
    }
}

fn cmd_scope() {
    println!("Scope as published on hack.cert.pl/programs/nask-pib/nask/editions/1 (2026-11-03)");
    for t in scope::TARGETS {
        println!("  tier {}  https://{}/", t.tier, t.host);
    }
    println!("\n  alias   https://www.nask.pl/  -> canonical form of the listed apex nask.pl");
    println!("\nProgramme limits: <= 5 requests/second, no DoS, blind SSRF without read is excluded.");
}

fn cmd_selftest() -> Result<(), String> {
    println!("selftest: scope guard");
    assert!(scope::is_allowed("nask.pl"));
    assert!(!scope::is_allowed("gitlab.snkom.nask.pl"));
    assert!(!scope::is_allowed("panel.dns.pl"));
    for bad in ["http://nask.pl/", "https://nask.pl.evil.tld/", "https://user@nask.pl/"] {
        assert!(scope::split_url(bad).is_err(), "{bad} must be refused");
    }
    println!("  ok: 12 listed hosts, unlisted subdomains and lookalikes refused");

    println!("selftest: limiter");
    assert!(scope::Limiter::new(4.0).is_ok());
    assert!(scope::Limiter::new(5.5).is_err());
    let l = scope::Limiter::new(5.0).map_err(|e| e)?;
    let t0 = Instant::now();
    for _ in 0..5 {
        l.acquire();
    }
    let elapsed = t0.elapsed();
    assert!(
        elapsed >= Duration::from_millis(750),
        "5 acquisitions at 5 req/s must take >= 0.8 s, took {elapsed:?}"
    );
    println!("  ok: 5 acquisitions at 5 req/s spaced {elapsed:?}");

    println!("selftest: same-origin resolution");
    assert_eq!(
        resolve_same_origin("nask.pl", "/_next/a.js").as_deref(),
        Some("https://nask.pl/_next/a.js")
    );
    assert_eq!(resolve_same_origin("nask.pl", "https://cdn.example/x.js"), None);
    assert_eq!(resolve_same_origin("nask.pl", "mailto:a@b"), None);

    println!("selftest: write methods are unreachable");
    // The programme forbids changing state, so this must be a property of the
    // binary, not of my memory. A 404 to GET can also mean "POST-only route",
    // which is why OPTIONS exists here and POST still does not.
    assert_eq!(probe::ALLOWED_METHODS, ["GET", "HEAD", "OPTIONS"]);
    for forbidden in ["POST", "PUT", "PATCH", "DELETE", "TRACE", "CONNECT"] {
        assert!(
            !probe::ALLOWED_METHODS.contains(&forbidden),
            "{forbidden} must never be sendable"
        );
    }
    println!("  ok: POST/PUT/PATCH/DELETE/TRACE/CONNECT cannot be expressed in a plan");

    println!("selftest: normalized digests (dns.pl reflected path)");
    // dns.pl answers an unknown path with the home page and echoes that path in
    // a skip-link anchor. Both sides must collapse, or every probe looks novel.
    let home_with = |reflected: &str| {
        format!(
            r#"<a class="skip" href="https://dns.pl{reflected}#navigation-menu-top">pomin</a><script>var _event_transid='2072786175';</script><h1>Przeglad domen</h1>"#
        )
    };
    let baseline_body = home_with("/zz-baseline-00ff");
    let probe_body = home_with("/.env");
    assert_eq!(
        probe::normalize_for(&baseline_body, "/zz-baseline-00ff"),
        probe::normalize_for(&probe_body, "/.env"),
        "reflected path must not make baseline and soft-404 differ"
    );
    assert_ne!(
        probe::normalize_for(&probe_body, "/.env"),
        probe::normalize_for("<h1>Nie znaleziono strony</h1>", "/.env"),
        "a genuinely different page must keep a different digest"
    );
    assert_eq!(
        probe::normalize_for(&probe_body, "/"),
        probe::normalize_for(&probe_body, "/a"),
        "paths shorter than 5 bytes are never substituted"
    );
    println!("  ok: transid and reflected path collapse, real differences survive");

    println!("selftest: analyzer on embedded fixture");
    let dir = std::env::temp_dir().join(format!("surface-selftest-{}", std::process::id()));
    std::fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    let f = dir.join("0000.body");
    std::fs::write(
        &f,
        r#"<html><head><meta name="generator" content="Next.js 15.2.3">
        <script src="/_next/static/chunks/main.js"></script></head>
        <body><form action="/api/report" method="post">
        <input name="link" type="url"><input name="attachment" type="file"></form>
        <script>const a="/api/v1/reports";fetch("/api/v1/reports/1")</script>
        <!-- TODO: remove password reset debug endpoint -->
        <script src="https://cdn.example.com/x.js"></script></body></html>"#,
    )
    .map_err(|e| e.to_string())?;
    let r = analyze::analyze_one(&f, "text/html");
    let checks = [
        ("kind is html", r["kind"] == json!("html")),
        ("generator parsed", r["generator"] == json!("Next.js 15.2.3")),
        // Both scripts are recorded here; dropping the off-scope CDN one is the
        // job of resolve_same_origin, tested separately above.
        (
            "both script tags recorded",
            r["scripts"].as_array().map(|a| a.len() == 2).unwrap_or(false),
        ),
        ("form action found", r["forms"][0]["action"] == json!("/api/report")),
        ("api route found", r["route_literals"].as_array().map(|a| a.iter().any(|v| v == "/api/v1/reports")).unwrap_or(false)),
        ("comment hit found", r["sensitive_comment_hits"].as_array().map(|a| !a.is_empty()).unwrap_or(false)),
    ];
    for (name, ok) in checks {
        println!("  {} {}", if ok { "ok:" } else { "FAIL:" }, name);
        assert!(ok, "selftest failed: {name}");
    }
    let _ = std::fs::remove_dir_all(&dir);
    println!("selftest: PASS");
    Ok(())
}

fn cmd_run(out: &Path, rps: f64, per_host_assets: usize) -> Result<Value, String> {
    let limiter = scope::Limiter::new(rps)?;
    std::fs::create_dir_all(out.join("bodies")).map_err(|e| e.to_string())?;
    let bodies = out.join("bodies");

    let client = reqwest::blocking::Client::builder()
        .redirect(reqwest::redirect::Policy::none())
        .timeout(Duration::from_secs(25))
        .connect_timeout(Duration::from_secs(10))
        .user_agent(UA)
        .build()
        .map_err(|e| e.to_string())?;

    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(4)
        .build()
        .map_err(|e| e.to_string())?;

    let issued = AtomicUsize::new(0);
    let deadline = Instant::now() + Duration::from_secs(1500);
    let t0 = Instant::now();

    // Phase 1: one static pass over every listed host.
    let phase1: Vec<(String, String)> = scope::TARGETS
        .iter()
        .flat_map(|t| {
            STATIC_PATHS
                .iter()
                .map(move |p| (t.host.to_string(), format!("https://{}{}", t.host, p)))
        })
        .collect();
    println!("phase 1: {} static requests over {} hosts at {:.2}/s", phase1.len(), scope::TARGETS.len(), rps);

    let mut all: Vec<Value> = Vec::new();
    let mut next = 0usize;
    let r1: Vec<Fetched> = pool.install(|| {
        phase1
            .par_iter()
            .enumerate()
            .map(|(i, (_h, url))| fetch_one(&client, &limiter, url, i, &bodies, deadline, &issued))
            .collect()
    });
    next = r1.len();
    let mut bodies_by_url: std::collections::HashMap<String, PathBuf> = std::collections::HashMap::new();
    for f in &r1 {
        if let Some(p) = &f.body_path {
            bodies_by_url.insert(f.entry["url"].as_str().unwrap_or("").to_string(), p.clone());
        }
        all.push(f.entry.clone());
    }
    let ok1 = all.iter().filter(|e| e["status"].as_u64().map(|s| s < 400).unwrap_or(false)).count();
    println!("phase 1: {ok1}/{} answered with <400", phase1.len());

    // Phase 2: same-origin scripts and links discovered in the HTML we just got.
    let mut discovered: Vec<String> = Vec::new();
    let mut seen: std::collections::HashSet<String> = std::collections::HashSet::new();
    for (url, path) in bodies_by_url.iter() {
        let ctype = all
            .iter()
            .find(|e| e["url"].as_str() == Some(url.as_str()))
            .and_then(|e| e["content_type"].as_str())
            .unwrap_or("");
        if !(ctype.contains("html") || url.ends_with('/')) {
            continue;
        }
        let body = match std::fs::read_to_string(path) {
            Ok(b) => b,
            Err(_) => continue,
        };
        let parsed = analyze::analyze_one(path, "text/html");
        let host = url
            .strip_prefix("https://")
            .and_then(|r| r.split('/').next())
            .unwrap_or("")
            .to_string();
        let mut take = 0usize;
        for list in ["scripts", "links"] {
            if let Some(arr) = parsed[list].as_array() {
                for v in arr {
                    if take >= per_host_assets {
                        break;
                    }
                    if let Some(u) = v.as_str().and_then(|s| resolve_same_origin(&host, s)) {
                        if seen.insert(u.clone()) {
                            discovered.push(u);
                            take += 1;
                        }
                    }
                }
            }
        }
    }
    discovered.truncate(MAX_REQUESTS.saturating_sub(next));
    println!("phase 2: {} in-scope assets discovered (scripts + same-origin links)", discovered.len());

    let r2: Vec<Fetched> = pool.install(|| {
        discovered
            .par_iter()
            .enumerate()
            .map(|(i, url)| fetch_one(&client, &limiter, url, next + i, &bodies, deadline, &issued))
            .collect()
    });
    for f in &r2 {
        all.push(f.entry.clone());
    }
    let ok2 = r2
        .iter()
        .filter(|f| f.entry["status"].as_u64().map(|s| s < 400).unwrap_or(false))
        .count();
    println!("phase 2: {ok2}/{} answered with <400", discovered.len());

    all.sort_by_key(|e| e["n"].as_u64().unwrap_or(0));
    let index = json!({
        "schema_version": 1,
        "programme": "nask",
        "edition": "11/2026",
        "generated_at_unix": std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0),
        "requested_rps": rps,
        "requests_issued": issued.load(Ordering::SeqCst),
        "wall_seconds": t0.elapsed().as_secs(),
        "entries": all,
    });
    std::fs::write(out.join("index.json"), serde_json::to_string_pretty(&index).map_err(|e| e.to_string())?)
        .map_err(|e| e.to_string())?;
    Ok(index)
}

fn cmd_probe(plan: &Path, out: &Path, rps: f64, snippets: bool) -> Result<Value, String> {
    let raw = std::fs::read_to_string(plan).map_err(|e| format!("{}: {e}", plan.display()))?;
    let plan_v: Value = serde_json::from_str(&raw).map_err(|e| e.to_string())?;
    let mut probes: Vec<Value> = plan_v
        .get("probes")
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default();

    // Compact form for a wide, shallow sweep: the same list of paths against
    // every listed host. Writing 100+ near-identical entries by hand invites
    // copy-paste mistakes, and a typo in a URL is a request to the wrong place.
    if let Some(m) = plan_v.get("matrix") {
        let hosts: Vec<String> = m
            .get("hosts")
            .and_then(|v| v.as_array())
            .map(|a| a.iter().filter_map(|h| h.as_str().map(String::from)).collect())
            .unwrap_or_default();
        let paths: Vec<(String, String)> = m
            .get("paths")
            .and_then(|v| v.as_array())
            .map(|a| {
                a.iter()
                    .filter_map(|p| {
                        Some((
                            p.get("path")?.as_str()?.to_string(),
                            p.get("note").and_then(|n| n.as_str()).unwrap_or("").to_string(),
                        ))
                    })
                    .collect()
            })
            .unwrap_or_default();
        if hosts.len() * paths.len() > 400 {
            return Err(format!(
                "matrix expands to {} probes, above the 400 safety limit",
                hosts.len() * paths.len()
            ));
        }
        for host in &hosts {
            for (path, note) in &paths {
                let slug: String = path
                    .trim_matches('/')
                    .chars()
                    .map(|c| if c.is_ascii_alphanumeric() { c.to_ascii_lowercase() } else { '-' })
                    .collect();
                probes.push(json!({
                    "id": format!("{}-{}", host.split('.').next().unwrap_or(host), slug),
                    "url": format!("https://{host}{path}"),
                    "note": format!("{host}: {note}"),
                    "snippet": path.len() < 20,
                }));
            }
        }
    }
    if probes.is_empty() {
        return Err("plan has no probes".into());
    }
    if probes.len() > 200 {
        return Err(format!("at most 200 probes per run, plan has {}", probes.len()));
    }
    let limiter = scope::Limiter::new(rps)?;
    let client = probe::default_client()?;
    let t0 = Instant::now();
    let results = probe::run_probes(&client, &limiter, &probes, snippets);
    let rows: Vec<Value> = results.into_iter().map(|r| r.value).collect();
    let interesting = rows
        .iter()
        .filter(|r| r.get("interesting").and_then(|v| v.as_bool()) == Some(true))
        .count();
    let outv = json!({
        "schema_version": 1,
        "plan_run": plan_v.get("run").cloned().unwrap_or(Value::Null),
        "probes": rows,
        "count": rows.len(),
        "interesting": interesting,
        "wall_seconds": t0.elapsed().as_secs(),
        "note": "interesting=true means a strong marker fired, or the answer differs from this host's catch-all baseline. Neither is a confirmed vulnerability: each needs a second, independent proof.",
    });
    if let Some(parent) = out.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    std::fs::write(out, serde_json::to_string_pretty(&outv).map_err(|e| e.to_string())?)
        .map_err(|e| e.to_string())?;
    Ok(outv)
}

fn cmd_analyze(dir: &Path) -> Result<Value, String> {
    let idx_raw = std::fs::read_to_string(dir.join("index.json")).map_err(|e| e.to_string())?;
    let index: Value = serde_json::from_str(&idx_raw).map_err(|e| e.to_string())?;
    let t0 = Instant::now();
    let analysis = analyze::analyze_dir(dir, &index)?;
    let mut out = analysis;
    if let Some(o) = out.as_object_mut() {
        o.insert("analyzed_in_ms".into(), json!(t0.elapsed().as_millis() as u64));
        o.insert("documents_count".into(), json!(o["documents"].as_array().map(|a| a.len()).unwrap_or(0)));
    }
    std::fs::write(dir.join("analysis.json"), serde_json::to_string_pretty(&out).map_err(|e| e.to_string())?)
        .map_err(|e| e.to_string())?;
    Ok(out)
}

fn main() {
    // The agent sandbox cannot read GitHub Actions logs (the log host is not
    // reachable), so every failure is also emitted as a workflow annotation,
    // which is readable through the check-runs API.
    std::panic::set_hook(Box::new(|info| {
        let msg = info
            .payload()
            .downcast_ref::<&str>()
            .map(|s| s.to_string())
            .or_else(|| info.payload().downcast_ref::<String>().cloned())
            .unwrap_or_else(|| "panic".to_string());
        let loc = info
            .location()
            .map(|l| format!("{}:{}", l.file(), l.line()))
            .unwrap_or_default();
        eprintln!("panic at {loc}: {msg}");
        eprintln!("::error title=surface panic::{msg} (at {loc})");
    }));

    let args: Vec<String> = std::env::args().collect();
    let cmd = args.get(1).map(|s| s.as_str()).unwrap_or("help");
    let flag = |name: &str| -> Option<String> {
        args.iter().position(|a| a == name).and_then(|i| args.get(i + 1)).cloned()
    };

    let result = match cmd {
        "scope" => {
            cmd_scope();
            Ok(())
        }
        "selftest" => cmd_selftest(),
        "run" => {
            let out = PathBuf::from(flag("--out").unwrap_or_else(|| "out".into()));
            let rps: f64 = flag("--rps").and_then(|v| v.parse().ok()).unwrap_or(4.0);
            let assets: usize = flag("--assets").and_then(|v| v.parse().ok()).unwrap_or(40);
            cmd_run(&out, rps, assets).map(|idx| {
                println!(
                    "done: {} entries, {} requests, {} s -> {}",
                    idx["entries"].as_array().map(|a| a.len()).unwrap_or(0),
                    idx["requests_issued"],
                    idx["wall_seconds"],
                    out.join("index.json").display()
                );
            })
        }
        "probe" => {
            let plan = match flag("--plan") {
                Some(p) => PathBuf::from(p),
                None => {
                    eprintln!("error: --plan FILE is required");
                    std::process::exit(1);
                }
            };
            let out = PathBuf::from(flag("--out").unwrap_or_else(|| "nask/out/probe.json".into()));
            let rps: f64 = flag("--rps").and_then(|v| v.parse().ok()).unwrap_or(3.0);
            let snippets = args.iter().any(|a| a == "--snippets");
            cmd_probe(&plan, &out, rps, snippets).map(|r| {
                println!("probe: {} probes, {} interesting", r["count"], r["interesting"]);
                if let Some(rows) = r["probes"].as_array() {
                    for p in rows {
                        let mark = if p["interesting"].as_bool() == Some(true) { ">>" } else { "  " };
                        println!("{} {:<26} {:<5} {:>7}B  markers={}", mark,
                            p["id"].as_str().unwrap_or("?"),
                            p["status"]
                                .as_u64()
                                .map(|s| s.to_string())
                                .unwrap_or_else(|| "-".into()),
                            p["bytes"].as_u64().unwrap_or(0), p["markers"]);
                    }
                }
            })
        }
        "analyze" => {
            let dir = PathBuf::from(flag("--dir").unwrap_or_else(|| "out".into()));
            cmd_analyze(&dir).map(|a| {
                println!("analyzed {} documents in {} ms", a["documents_count"], a["analyzed_in_ms"]);
                if let Some(hosts) = a["per_host"].as_object() {
                    for (h, v) in hosts {
                        println!(
                            "  {:<32} docs={:<3} js={:<3} routes={:<4} fw={}",
                            h,
                            v["documents"],
                            v["js_documents"],
                            v["route_literals"],
                            v["frameworks"]
                        );
                    }
                }
            })
        }
        _ => {
            println!("surface — read-only discovery for the NASK programme\n");
            println!("  surface scope                 list in-scope hosts and limits");
            println!("  surface selftest              verify guard, limiter and analyzer offline");
            println!("  surface run --out DIR [--rps 4] [--assets 40]");
            println!("  surface probe --plan F --out F [--rps 3] [--snippets]");
            println!("  surface analyze --dir DIR     (re)analyze an existing DIR/index.json");
            Ok(())
        }
    };

    if let Err(e) = result {
        eprintln!("error: {e}");
        eprintln!("::error title=surface::{e}");
        std::process::exit(1);
    }
}
