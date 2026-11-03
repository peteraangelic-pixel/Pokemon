mod baseline;
mod endpoints;
mod hypo;
mod probe;
mod ratelimit;
mod scope;

use clap::{Parser, Subcommand};
use ratelimit::RateLimiter;
use rayon::prelude::*;
use std::io::Write;

#[derive(Parser)]
#[command(name = "naskrecon", about = "Pasywny rekonesans dla konkursu Bug Bounty NASK (hack.cert.pl)")]
struct Cli {
    /// Żądania na sekundę. Regulamin §6 pkt 2 dopuszcza max 5. Nie przekraczaj.
    #[arg(long, default_value_t = 4.5)]
    rps: f64,

    /// Wątki. Sandbox ma 2, Ryzen 5950X ma 16 — limiter i tak trzyma sufit.
    #[arg(long, default_value_t = 8)]
    threads: usize,

    #[command(subcommand)]
    cmd: Cmd,
}

#[derive(Subcommand)]
enum Cmd {
    /// Wypisz domeny w zakresie konkursu i stawki
    Scope,
    /// Sprawdź, czy host jest w zakresie (kod wyjścia 0 = tak)
    Check { host: String },
    /// Pasywny rekonesans: jedna ścieżka na każdy host z zakresu
    Sweep {
        #[arg(long, default_value = "/")]
        path: String,
    },
    /// Testy hipotez: ominięcie middleware Next.js + ekspozycje plików
    Hypotheses {
        /// Trasy do sprawdzenia pod kątem middleware (jedno żądanie porównawcze każda)
        #[arg(long, value_delimiter = ',')]
        paths: Vec<String>,
    },
    /// Analiza offline pobranych plików (JS/HTML/JSON) — w pełni równoległa
    Scan {
        #[arg(long, num_args = 1..)]
        files: Vec<std::path::PathBuf>,
    },
    /// Rekonesans wybranych ścieżek na hostach z zakresu
    Paths {
        #[arg(long, value_delimiter = ',')]
        paths: Vec<String>,
        #[arg(long, value_delimiter = ',')]
        hosts: Vec<String>,
    },
}

fn main() {
    let cli = Cli::parse();
    if cli.rps > scope::MAX_REQ_PER_SEC {
        eprintln!(
            "ODMOWA: {} req/s przekracza regulaminowy sufit {} req/s (§6 pkt 2).",
            cli.rps,
            scope::MAX_REQ_PER_SEC
        );
        std::process::exit(2);
    }
    let _pool = rayon::ThreadPoolBuilder::new()
        .num_threads(cli.threads)
        .build()
        .expect("thread pool");
    let rl = RateLimiter::new(cli.rps);

    match cli.cmd {
        Cmd::Scope => {
            println!("Konkurs: {} – {}   pula: {} PLN", scope::COMPETITION_START, scope::COMPETITION_END, scope::PRIZE_POOL_PLN);
            println!("{:<32} {:>4} {:>12}", "domena", "tier", "max krytyczna");
            for s in scope::IN_SCOPE {
                println!("{:<32} {:>4} {:>10} zł", s.domain, s.tier, s.max_critical_pln);
            }
        }
        Cmd::Check { host } => match (scope::in_scope(&host), scope::subdomain_of_in_scope(&host)) {
            (Some(s), _) => {
                println!("W ZAKRESIE: {} (Tier {}, max {} zł)", s.domain, s.tier, s.max_critical_pln);
            }
            (None, Some(parent)) => {
                println!("POZA ZAKRESEM: {} — subdomena {}, ale §5 nie wypisuje jej wprost.", host, parent);
                std::process::exit(1);
            }
            (None, None) => {
                println!("POZA ZAKRESEM: {}", host);
                std::process::exit(1);
            }
        },
        Cmd::Sweep { path } => {
            let hosts: Vec<String> = scope::IN_SCOPE.iter().map(|s| s.domain.to_string()).collect();
            run(hosts, vec![path], &rl);
        }
        Cmd::Hypotheses { paths } => {
            let rl = &rl;
            // 1) ekspozycje plików — 16 ścieżek × 12 hostów = 192 żądania, ~45 s przy 4.5/s
            let epaths: Vec<(String, &str, &str)> = hypo::EXPOSURE_PATHS
                .iter()
                .map(|(p, sev, desc)| (p.to_string(), *sev, *desc))
                .collect();
            // 0) baseline catch-all na hosta — 1 żądanie, losowa ścieżka
            let mut baselines: std::collections::HashMap<String, baseline::Baseline> = Default::default();
            for s in scope::IN_SCOPE {
                let junk = format!("/zz-junk-{:08x}", std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH).unwrap().subsec_nanos() ^ (s.domain.len() as u32));
                let (st, body, _) = fetch_body(s.domain, &junk, rl);
                baselines.insert(s.domain.to_string(), baseline::Baseline::from(&body, st, &junk));
            }
            eprintln!("[i] baseline catch-all zebrany dla {} hostów", baselines.len());

            let jobs: Vec<(String, String)> = scope::IN_SCOPE
                .iter()
                .flat_map(|s| epaths.iter().map(move |(p, _, _)| (s.domain.to_string(), p.clone())))
                .collect();
            eprintln!("[i] ekspozycje: {} żądań", jobs.len());
            let hits: Vec<_> = jobs
                .par_iter()
                .map(|(h, p)| {
                    let (st, body, ct) = fetch_body(h, p, rl);
                    (h.clone(), p.clone(), st, body, ct)
                })
                .collect();
            println!("\n=== EKSPOZYCJE (200 ORAZ różne od catch-all) ===");
            let mut n = 0;
            for (h, p, st, body, ct) in &hits {
                let Some(b) = baselines.get(h) else { continue };
                if !b.is_real_file(body, *st, p, ct) { continue; }
                let meta = hypo::EXPOSURE_PATHS.iter().find(|(x, _, _)| x == p);
                let (sev, desc) = meta.map(|(_, s, d)| (*s, *d)).unwrap_or(("?", "?"));
                let snippet = body.trim().chars().take(90).collect::<String>().replace('\n', " ");
                println!("{:32} {:26} {:>7}B {:<9} {}\n         └ {:?} | {}", h, p, body.len(), sev, desc, ct, snippet);
                n += 1;
            }
            if n == 0 { println!("BRAK TRAFIEŃ — wszystko to catch-all albo kod != 200"); }

            // 2) middleware bypass na podanych trasach
            if !paths.is_empty() {
                println!("\n=== OMINIĘCIE MIDDLEWARE NEXT.JS ===");
                let mut any = false;
                for s in scope::IN_SCOPE {
                    for p in &paths {
                        if let Some(msg) = hypo::nextjs_bypass(s.domain, p, rl) {
                            println!("{}", msg);
                            any = true;
                        }
                    }
                }
                if !any { println!("brak sygnału (albo trasa nie istnieje, albo brak ochrony middleware)"); }
            }
            eprintln!("[i] łącznie żądań: {}", rl.issued());
        }
        Cmd::Scan { files } => {
            let found = endpoints::scan(files);
            let mut eps = std::collections::BTreeSet::new();
            let mut pars = std::collections::BTreeSet::new();
            for f in &found {
                eps.extend(f.endpoints.iter().cloned());
                pars.extend(f.params.iter().cloned());
                for (k, v) in &f.secrets {
                    println!("SEKRET? {:<18} {}  w {}", k, v, f.file);
                }
            }
            println!("\n=== ENDPOINTY ({}) ===", eps.len());
            for e in &eps { println!("  {}", e); }
            println!("\n=== PARAMETRY ({}) ===", pars.len());
            for p in &pars { print!("{} ", p); }
            println!();
        }
        Cmd::Paths { paths, hosts } => {
            let hosts: Vec<String> = if hosts.is_empty() {
                scope::IN_SCOPE.iter().map(|s| s.domain.to_string()).collect()
            } else {
                hosts
            };
            // guard: żadne żądanie nie wyjdzie poza zakres
            let mut allowed = vec![];
            for h in hosts {
                match scope::in_scope(&h) {
                    Some(_) => allowed.push(h),
                    None => eprintln!("pomijam {} — poza zakresem §5", h),
                }
            }
            run(allowed, paths, &rl);
        }
    }
}

fn run(hosts: Vec<String>, paths: Vec<String>, rl: &RateLimiter) {
    let jobs: Vec<(String, String)> = hosts
        .iter()
        .flat_map(|h| paths.iter().map(move |p| (h.clone(), p.clone())))
        .collect();
    eprintln!("[i] {} żądań, limiter {:.1} req/s", jobs.len(), 1.0 / rl.gap().as_secs_f64());

    let mut rows: Vec<_> = jobs
        .par_iter()
        .map(|(h, p)| probe::probe(h, p, rl))
        .collect();
    rows.sort_by(|a, b| (a.host.clone(), a.path.clone()).cmp(&(b.host.clone(), b.path.clone())));

    let mut out = std::fs::File::create("recon-out.jsonl").expect("recon-out.jsonl");
    for r in &rows {
        writeln!(out, "{}", r.to_json()).ok();
    }
    eprintln!("[i] wysłano {} żądań, zapisano {} wierszy do recon-out.jsonl", rl.issued(), rows.len());

    // podsumowanie na stdout
    println!("{:<32} {:<24} {:>4} {:>7} {:>5} {:>6} {}", "host", "ścieżka", "kod", "bajty", "form", "cookie", "tech");
    for r in &rows {
        println!(
            "{:<32} {:<24} {:>4} {:>7} {:>5} {:>6} {}",
            r.host,
            r.path,
            r.status,
            r.size,
            r.forms,
            r.cookies,
            r.tech_hints.join(",")
        );
    }
}


/// Pobiera (status, ciało, content-type). Jedno żądanie, przez limiter.
fn fetch_body(host: &str, path: &str, rl: &RateLimiter) -> (u16, String, String) {
    rl.acquire();
    let url = format!("https://{}{}", host, path);
    let agent = ureq::AgentBuilder::new()
        .timeout_connect(std::time::Duration::from_secs(10))
        .timeout_read(std::time::Duration::from_secs(25))
        .user_agent("Mozilla/5.0 (compatible; naskrecon/0.1; hack.cert.pl)")
        .redirects(0)
        .build();
    match agent.get(&url).call() {
        Ok(r) => {
            let ct = r.header("content-type").unwrap_or("").to_string();
            (r.status(), r.into_string().unwrap_or_default(), ct)
        }
        Err(ureq::Error::Status(c, r)) => {
            let ct = r.header("content-type").unwrap_or("").to_string();
            (c, r.into_string().unwrap_or_default(), ct)
        }
        Err(_) => (0, String::new(), String::new()),
    }
}
