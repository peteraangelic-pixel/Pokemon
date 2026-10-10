#![forbid(unsafe_code)]
//! battery-sim -- symulator ogniwa 3-skladnikowego (katoda | elektrolit | anoda).
//!
//! Modeluje: energie wlasciwa (Wh/kg), opor wewnetrzny, szybkie ladowanie
//! (plating litu, dendryty), zywotnosc cykliczna (SEI, degradacja katody,
//! stres oksydacyjny elektrolitu, dead Li), termike i bezpieczenstwo
//! (test abusow: piec + przeladowanie).
//!
//! Uzycie: `cargo run --release -- sweep` (zobacz `battery-sim help`).

mod benchmark;
mod cell;
mod doc;
mod materials;
mod par;
mod report;
mod sim;
mod sweep;
mod util;

use cell::{Cell, CellParams};
use materials::{anode, cathode, electrolyte, Anode, Cathode, Electrolyte};
use sim::{simulate, Abuse, SimParams};
use std::collections::{HashMap, HashSet};
use std::time::Instant;

const BASELINE: (&str, &str, &str) = ("NMC811", "GRAPHITE", "LP57");

struct Cli {
    sub: String,
    opts: HashMap<String, String>,
    flags: HashSet<String>,
}

impl Cli {
    fn get(&self, k: &str) -> Option<&str> {
        self.opts.get(k).map(|s| s.as_str())
    }
    fn get_f64(&self, k: &str, def: f64) -> f64 {
        self.get(k).and_then(|v| v.parse().ok()).unwrap_or(def)
    }
    fn get_u64(&self, k: &str, def: u64) -> u64 {
        self.get(k).and_then(|v| v.parse().ok()).unwrap_or(def)
    }
    fn get_usize(&self, k: &str, def: usize) -> usize {
        self.get(k).and_then(|v| v.parse().ok()).unwrap_or(def)
    }
    fn flag(&self, k: &str) -> bool {
        self.flags.contains(k)
    }
    fn get_list_f64(&self, k: &str, def: &[f64]) -> Vec<f64> {
        match self.get(k) {
            Some(v) => v.split(',').filter_map(|x| x.trim().parse().ok()).collect(),
            None => def.to_vec(),
        }
    }
    fn get_list_str(&self, k: &str) -> Vec<String> {
        match self.get(k) {
            Some(v) => v
                .split(',')
                .map(|x| x.trim().to_uppercase())
                .filter(|x| !x.is_empty())
                .collect(),
            None => Vec::new(),
        }
    }
}

fn parse_cli() -> Cli {
    let argv: Vec<String> = std::env::args().skip(1).collect();
    let mut cli = Cli {
        sub: "demo".to_string(),
        opts: HashMap::new(),
        flags: HashSet::new(),
    };
    let mut i = 0;
    let mut sub_set = false;
    while i < argv.len() {
        let a = &argv[i];
        if !sub_set && !a.starts_with("--") {
            cli.sub = a.clone();
            sub_set = true;
            i += 1;
            continue;
        }
        if let Some(eq) = a.find('=') {
            cli.opts
                .insert(a[..eq].to_string(), a[eq + 1..].to_string());
            i += 1;
        } else if i + 1 < argv.len() && !argv[i + 1].starts_with("--") {
            cli.opts.insert(a.clone(), argv[i + 1].clone());
            i += 2;
        } else {
            cli.flags.insert(a.clone());
            i += 1;
        }
    }
    cli
}

fn names(list: &[&'static str]) -> String {
    list.join(", ")
}

fn need_cathode(name: &str) -> Cathode {
    match cathode(name) {
        Some(c) => c,
        None => {
            eprintln!(
                "Nieznana katoda: {name}. Dostepne: {}",
                names(
                    &materials::CATHODES
                        .iter()
                        .map(|c| c.name)
                        .collect::<Vec<_>>()
                )
            );
            std::process::exit(2);
        }
    }
}

fn need_anode(name: &str) -> Anode {
    match anode(name) {
        Some(a) => a,
        None => {
            eprintln!(
                "Nieznana anoda: {name}. Dostepne: {}",
                names(&materials::ANODES.iter().map(|a| a.name).collect::<Vec<_>>())
            );
            std::process::exit(2);
        }
    }
}

fn need_electrolyte(name: &str) -> Electrolyte {
    match electrolyte(name) {
        Some(e) => e,
        None => {
            eprintln!(
                "Nieznany elektrolit: {name}. Dostepne: {}",
                names(
                    &materials::ELECTROLYTES
                        .iter()
                        .map(|e| e.name)
                        .collect::<Vec<_>>()
                )
            );
            std::process::exit(2);
        }
    }
}

fn need_cathode_cli(cli: &Cli, def: &str) -> Cathode {
    let name = cli.get("--cathode").unwrap_or(def).to_uppercase();
    need_cathode(&name)
}

fn need_anode_cli(cli: &Cli, def: &str) -> Anode {
    let name = cli.get("--anode").unwrap_or(def).to_uppercase();
    need_anode(&name)
}

fn need_electrolyte_cli(cli: &Cli, def: &str) -> Electrolyte {
    let name = cli.get("--electrolyte").unwrap_or(def).to_uppercase();
    need_electrolyte(&name)
}

fn resolve_cathodes(cli: &Cli, quick: bool) -> Vec<Cathode> {
    let wanted = cli.get_list_str("--cathodes");
    if wanted.is_empty() {
        if quick {
            return vec![
                need_cathode("NMC811"),
                need_cathode("LFP"),
                need_cathode("LMR"),
            ];
        }
        return materials::CATHODES.to_vec();
    }
    wanted.iter().map(|n| need_cathode(n)).collect()
}

fn resolve_anodes(cli: &Cli, quick: bool) -> Vec<Anode> {
    let wanted = cli.get_list_str("--anodes");
    if wanted.is_empty() {
        if quick {
            return vec![
                need_anode("GRAPHITE"),
                need_anode("LTO"),
                need_anode("SIC"),
                need_anode("LIMETAL"),
            ];
        }
        return materials::ANODES.to_vec();
    }
    wanted.iter().map(|n| need_anode(n)).collect()
}

fn resolve_electrolytes(cli: &Cli, quick: bool) -> Vec<Electrolyte> {
    let wanted = cli.get_list_str("--electrolytes");
    if wanted.is_empty() {
        if quick {
            return vec![
                need_electrolyte("LP57"),
                need_electrolyte("IONIC"),
                need_electrolyte("SOLID"),
            ];
        }
        return materials::ELECTROLYTES.to_vec();
    }
    wanted.iter().map(|n| need_electrolyte(n)).collect()
}

fn baseline_cell(cp: &CellParams) -> Cell {
    Cell::new(
        need_cathode(BASELINE.0),
        need_anode(BASELINE.1),
        need_electrolyte(BASELINE.2),
        20.0,
        1.1,
        cp,
    )
}

fn default_abuse(cli: &Cli) -> Abuse {
    Abuse {
        t_oven: cli.get_f64("--abuse-temp", 150.0),
        overcharge: 1.0,
        t_max_h: 3.0,
    }
}

fn run_demo(cp: &CellParams, sp: &SimParams) {
    println!(
        "== ogniwo referencyjne (bazowe Li-ion: {}/{}/{}) ==",
        BASELINE.0, BASELINE.1, BASELINE.2
    );
    let ref_cell = baseline_cell(cp);
    report::print_cell_summary(&ref_cell);
    for ld in [15.0, 20.0, 25.0] {
        let c = Cell::new(
            need_cathode(BASELINE.0),
            need_anode(BASELINE.1),
            need_electrolyte(BASELINE.2),
            ld,
            1.1,
            cp,
        );
        println!("  load={ld:4.0}: {:6.1} Wh/kg  R0={:5.2}", c.wh_kg, c.r0);
    }

    println!("\n== scenariusze pojedynczych ogniw ==");
    let scenarios: [(&str, &str, &str, f64, f64, f64, f64); 12] = [
        ("NMC811", "GRAPHITE", "LP57", 18.0, 1.1, 1.0, 25.0),
        ("NMC811", "GRAPHITE", "LP57", 18.0, 1.1, 2.0, 25.0),
        ("NMC811", "GRAPHITE", "LP57", 18.0, 1.1, 3.0, 25.0),
        ("NMC811", "GRAPHITE", "LP57", 18.0, 1.1, 1.0, 0.0),
        ("LFP", "LTO", "LP57", 20.0, 1.1, 3.0, 25.0),
        ("NMC811", "SIC", "LP57", 20.0, 1.1, 2.0, 25.0),
        ("NMC811", "LIMETAL", "SOLID", 22.0, 1.05, 2.0, 25.0),
        ("SULFUR", "LIMETAL", "IONIC", 20.0, 1.05, 1.0, 25.0),
        ("NMC811", "SIC", "GEL", 25.0, 1.1, 2.0, 25.0),
        ("NA_PW", "HC", "LP57", 30.0, 1.1, 3.0, 25.0),
        ("DRX", "SIC", "SOLID", 20.0, 1.1, 2.0, 25.0),
        ("LIO2", "LIMETAL", "IONIC", 10.0, 1.05, 1.0, 25.0),
    ];
    for (ca, an, el, ld, np, cch, tamb) in scenarios {
        let cell = Cell::new(
            need_cathode(ca),
            need_anode(an),
            need_electrolyte(el),
            ld,
            np,
            cp,
        );
        let r = simulate(&cell, cp, sp, cch, 1.0, tamb, 2000, None);
        report::print_sim_line(&r);
    }

    println!("\n== test abusow (piec 150C + przeladowanie 1C, 3 h) ==");
    let abuse = default_abuse(&Cli {
        sub: String::new(),
        opts: HashMap::new(),
        flags: HashSet::new(),
    });
    let abuse_cases: [(&str, &str, &str); 8] = [
        ("NMC811", "GRAPHITE", "LP57"),
        ("NMC811", "GRAPHITE", "IONIC"),
        ("LFP", "LTO", "LP57"),
        ("NMC811", "GRAPHITE", "SOLID"),
        ("NMC811", "LIMETAL", "SOLID"),
        ("NMC811", "SIC", "LP57"),
        ("NA_NFPP", "HC", "GEL"),
        ("DRX", "SIC", "SOLID"),
    ];
    for (ca, an, el) in abuse_cases {
        let cell = Cell::new(
            need_cathode(ca),
            need_anode(an),
            need_electrolyte(el),
            20.0,
            1.1,
            cp,
        );
        let r = simulate(&cell, cp, sp, 1.0, 1.0, 25.0, 1, Some(abuse));
        report::print_abuse_line(&r);
    }
    println!(
        "\nPelny sweep wg kryteriow: `battery-sim sweep` (rownolegle, {}).",
        par::backend_name()
    );
}

fn run_cell(cli: &Cli, cp: &CellParams, sp: &SimParams) {
    let cath = need_cathode_cli(cli, "NMC811");
    let an = need_anode_cli(cli, "GRAPHITE");
    let el = need_electrolyte_cli(cli, "LP57");
    if !materials::compatible(cath.name, an.name) {
        eprintln!(
            "Para {}/{} jest niespojna systemowo (katoda: {}, anoda: {}). Wybierz zgodne materialy (patrz `list`).",
            cath.name,
            an.name,
            materials::cath_system(cath.name),
            an.name
        );
        std::process::exit(2);
    }
    let loading = cli.get_f64("--loading", 20.0);
    let np = cli.get_f64("--np", 1.1);
    let c_ch = cli.get_f64("--c-rate", 2.0);
    let c_dis = cli.get_f64("--d-rate", 1.0);
    let t_amb = cli.get_f64("--temp", 25.0);
    let max_cycles = cli.get_u64("--cycles", 3000);
    let trace_every = cli.get_u64("--trace-every", 100);

    let cell = Cell::new(cath, an, el, loading, np, cp);
    report::print_cell_summary(&cell);

    let r = simulate(&cell, cp, sp, c_ch, c_dis, t_amb, max_cycles, None);
    report::print_sim_summary(&r);
    report::print_trace_table(&r, trace_every);

    if cli.flag("--abuse") {
        println!("\n== test abusow ==");
        let ab = simulate(&cell, cp, sp, 1.0, 1.0, t_amb, 1, Some(default_abuse(cli)));
        report::print_abuse_line(&ab);
    }

    if let Some(path) = cli.get("--csv") {
        match report::write_trace_csv(path, &r) {
            Ok(()) => println!("\nPrzebieg zapisany do {path}"),
            Err(e) => eprintln!("Blad zapisu CSV: {e}"),
        }
    }
}

fn run_sweep(cli: &Cli, cp: &CellParams, sp: &SimParams) {
    let quick = cli.flag("--quick");
    let caths = resolve_cathodes(cli, quick);
    let ans = resolve_anodes(cli, quick);
    let els = resolve_electrolytes(cli, quick);
    let loadings = cli.get_list_f64("--loadings", &[20.0]);
    let nps = cli.get_list_f64("--nps", &[1.1]);
    let fast_rates = cli.get_list_f64("--c-rates", if quick { &[2.0] } else { &[2.0, 3.0] });
    let temps = cli.get_list_f64("--temps", &[]);
    let temps = if temps.is_empty() {
        vec![cli.get_f64("--temp", 25.0)]
    } else {
        temps
    };
    let max_cycles = cli.get_u64("--cycles", if quick { 1500 } else { 3000 });
    let top = cli.get_usize("--top", 30);
    let samples = cli.get_usize("--samples", 0);

    let base = baseline_cell(cp);
    let crit = sweep::Criteria {
        baseline_wh: base.wh_kg,
        energy_factor: cli.get_f64("--energy-factor", 1.0),
        min_cycles: cli.get_u64("--min-cycles", 500),
        fast_rates,
        abuse: default_abuse(cli),
        max_cycles,
    };
    report::print_criteria(&crit);

    let mut jobs = sweep::build_grid(&caths, &ans, &els, &loadings, &nps, &temps);
    let total_full = jobs.len();
    if samples > 0 && samples < jobs.len() {
        jobs = sweep::sample(&jobs, samples, 42);
    }
    println!(
        "Siatka: {} katod x {} anod x {} elektrolitow x {} loadingow x {} N/P x {} temp = {} kombinacji (backend: {}, {} watkow)",
        caths.len(), ans.len(), els.len(), loadings.len(), nps.len(), temps.len(), jobs.len(),
        par::backend_name(), par::num_threads()
    );

    let t0 = Instant::now();
    let mut results: Vec<sweep::ComboResult> = Vec::with_capacity(jobs.len());
    let mut done = 0usize;
    for chunk in jobs.chunks(24) {
        let mut rs = par::par_map(chunk.to_vec(), |job| {
            sweep::evaluate_combo(&job, &crit, cp, sp)
        });
        results.append(&mut rs);
        done += chunk.len();
        println!("  ... {done}/{} kombinacji", jobs.len());
    }
    let elapsed = t0.elapsed();

    results.sort_by(|a, b| {
        b.score
            .partial_cmp(&a.score)
            .unwrap_or(std::cmp::Ordering::Equal)
    });
    let n_pass = results.iter().filter(|r| r.passed).count();
    println!(
        "\nSweep zakonczony: {} kombinacji w {:.1} s. PASS (wszystkie kryteria): {}/{}",
        results.len(),
        elapsed.as_secs_f64(),
        n_pass,
        results.len()
    );
    if total_full != jobs.len() {
        println!(
            "(przetestowano probke z {} kombinacji; bez --samples pelna siatka)",
            total_full
        );
    }
    report::print_combo_table(&results, top);

    if let Some(path) = cli.get("--csv") {
        match report::write_sweep_csv(path, &results) {
            Ok(()) => println!("\nWyniki zapisane do {path}"),
            Err(e) => eprintln!("Blad zapisu CSV: {e}"),
        }
    }
}

fn run_list() {
    println!("== katody ==");
    println!(
        "  {:<8} {:>6} {:>6} {:>5} {:>6} {:>7} {:>6} {:>7} {:>7}",
        "nazwa", "mAh/g", "Vmax", "g/cm3", "fade", "T_stab", "i0", "sd/cykl", "USD/kg"
    );
    for c in materials::CATHODES {
        println!(
            "  {:<8} {:6.0} {:6.2} {:5.1} {:6.2} {:7.0} {:6.1} {:7.4} {:7.0}",
            c.name,
            c.cap_mah_g,
            c.vmax,
            c.dens,
            c.fade,
            c.t_stable,
            c.i0,
            c.sd,
            materials::cost_cath_usd_kg(c.name)
        );
    }
    println!("\n== anody ==");
    println!(
        "  {:<8} {:>6} {:>6} {:>5} {:>5} {:>5} {:>6} {:>6} {:>7} {:>8} {:>8} {:>6} {:>7}",
        "nazwa",
        "mAh/g",
        "dens",
        "plat",
        "sei",
        "dend",
        "T_stab",
        "i0",
        "k_an",
        "deadLi",
        "dH",
        "expl",
        "USD/kg"
    );
    for a in materials::ANODES {
        println!(
            "  {:<8} {:6.0} {:6.1} {:5.2} {:5.2} {:5.3} {:6.0} {:6.1} {:7.0} {:8.4} {:8.0} {:6.2} {:7.0}",
            a.name,
            a.cap_mah_g,
            a.dens,
            a.plat,
            a.sei,
            a.dend,
            a.t_stable,
            a.i0,
            a.k_an,
            a.dead_li,
            a.dh,
            a.expansion,
            materials::cost_an_usd_kg(a.name)
        );
    }
    println!("\n== elektrolity ==");
    println!(
        "  {:<8} {:>8} {:>8} {:>9} {:>7} {:>5} {:>6} {:>7}",
        "nazwa", "kappa", "T_decomp", "palny", "okno V", "sei", "r_if", "USD/kg"
    );
    for e in materials::ELECTROLYTES {
        println!(
            "  {:<8} {:6.1} mS {:6.0} {:>9} {:7.1} {:5.1} {:6.1} {:7.0}",
            e.name,
            e.kappa_ms_cm,
            e.t_decomp,
            if e.flammable { "TAK" } else { "nie" },
            e.window,
            e.sei,
            e.r_if,
            materials::cost_el_usd_kg(e.name)
        );
    }
}

fn run_baseline(cp: &CellParams) {
    let base = baseline_cell(cp);
    println!("== ogniwo bazowe (Li-ion) i kryteria ==");
    report::print_cell_summary(&base);
    println!("\nKryteria dla nowego ogniwa:");
    println!("  1) energia wlasciwa >= {:.1} Wh/kg", base.wh_kg);
    println!(
        "  2) bezpieczenstwo: brak eksplozji / thermal runaway / zwarcia (cyklowanie + abus 150°C)"
    );
    println!("  3) >= 500 cykli przy szybkim ladowaniu (2C-3C)");
}

fn print_help() {
    println!(
        "battery-sim -- symulator ogniwa 3-skladnikowego (katoda | elektrolit | anoda)

Polecenia:
  demo        szybka demonstracja (domyslne): ogniwo bazowe, scenariusze, abusy
  cell        symulacja pojedynczego ogniwa + przebieg cykli (+ opcjonalnie CSV)
  sweep       przeszukiwanie siatki materialow wg kryteriow (rownolegle)
  list        wypisz dostepne materialy i ich parametry (+ koszt USD/kg)
  baseline    pokaz ogniwo bazowe i kryteria
  benchmark   nasi kandydaci kontra ogniwa komercyjne (tabele)
  report      raport Markdown PL/EN (--lang pl|en --out plik.md)
  help        ta pomoc

Opcje (cell):
  --cathode NMC811 --anode GRAPHITE --electrolyte LP57
  (metryki: Wh/kg ogniwa i pakietu x0.72, Wh/L, koszt materialowy $/kWh)
  --loading 20 (mg/cm^2)   --np 1.1
  --c-rate 2 --d-rate 1 --temp 25 --cycles 3000
  --trace-every 100        --abuse (dodatkowo test abusow)
  --csv przebieg.csv       (pelny przebieg cykli)

Opcje (sweep):
  --cathodes NMC811,LFP    --anodes GRAPHITE,SIC   --electrolytes LP57,SOLID
  --loadings 15,20,25      --nps 1.1
  --c-rates 2,3            --temps 0,25,45 (lub pojedyncze --temp 25)   --cycles 3000
  --min-cycles 500         --energy-factor 1.0     --abuse-temp 150
  --top 30                 --samples 60            --quick (mniejsza siatka)
  --csv wyniki.csv

Kompilacja:
  cargo run --release -- sweep          (z rayon, domyslnie)
  cargo run --release --no-default-features -- sweep   (bez rayona, czysty std)

Model: port 1:1 z tools/model_prototype.py (tam referencyjne stale i walidacja).
"
    );
}

fn run_report(cli: &Cli, cp: &CellParams, sp: &SimParams) {
    let lang = cli.get("--lang").unwrap_or("pl").to_lowercase();
    let lang = if lang.starts_with("en") { "en" } else { "pl" };
    let def_out = if lang == "en" {
        "report.md"
    } else {
        "raport.md"
    };
    let out = cli.get("--out").unwrap_or(def_out);
    match doc::write_report(out, lang, cp, sp) {
        Ok(n) => println!("Raport ({lang}) zapisany: {out} ({n} linii)"),
        Err(e) => eprintln!("Blad zapisu raportu: {e}"),
    }
}

fn main() {
    let cli = parse_cli();
    let cp = CellParams::default();
    let sp = SimParams::default();
    match cli.sub.as_str() {
        "demo" => run_demo(&cp, &sp),
        "cell" => run_cell(&cli, &cp, &sp),
        "sweep" => run_sweep(&cli, &cp, &sp),
        "list" => run_list(),
        "baseline" => run_baseline(&cp),
        "benchmark" => benchmark::print_benchmark(&cp, &sp),
        "report" => run_report(&cli, &cp, &sp),
        "help" | "--help" | "-h" => print_help(),
        other => {
            eprintln!("Nieznane polecenie: {other}");
            print_help();
            std::process::exit(2);
        }
    }
}
