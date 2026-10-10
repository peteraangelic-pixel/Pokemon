//! Drabiny testowe dla zwycięskich konfiguracji: C-rate, abuse, moc.
//!
//! `battery-sim ladder --csv optim_winners.csv --top 12` — bierze top N
//! kombinacji PASS z CSV sweepu i dla każdej liczy:
//!   - drabinę C-rate (1/2/3/4/6C): ile cykli do EOL przy każdym tempie ładowania,
//!   - drabinę abuse (piec 130–250 °C + overcharge): margines bezpieczeństwa,
//!   - moc: drabinę rozładowania 1–5C (delivered fraction w oknie napięć).

use crate::cell::{Cell, CellParams};
use crate::materials::{anode, cathode, electrolyte};
use crate::sim::{simulate, Abuse, SimParams};
use crate::Cli;
use std::fs;

const RATE_LADDER: [f64; 5] = [1.0, 2.0, 3.0, 4.0, 6.0];
const ABUSE_LADDER: [f64; 5] = [130.0, 150.0, 170.0, 200.0, 250.0];

struct Row {
    cath: String,
    an: String,
    el: String,
    loading: f64,
    np: f64,
    temp: f64,
    wh_kg: f64,
    cost: f64,
    score: f64,
}

impl Row {
    fn label(&self) -> String {
        format!(
            "{}/{}/{} load={:.0} N/P={:.2} T={:.0}°C",
            self.cath, self.an, self.el, self.loading, self.np, self.temp
        )
    }
    fn cell(&self, cp: &CellParams) -> Cell {
        Cell::new(
            cathode(&self.cath).expect("katoda z CSV"),
            anode(&self.an).expect("anoda z CSV"),
            electrolyte(&self.el).expect("elektrolit z CSV"),
            self.loading,
            self.np,
            cp,
        )
    }
}

fn read_rows(path: &str) -> Vec<Row> {
    let txt = fs::read_to_string(path).unwrap_or_else(|e| {
        eprintln!("Nie mogę odczytać {path}: {e}");
        std::process::exit(2);
    });
    let mut rows = Vec::new();
    for (i, line) in txt.lines().enumerate() {
        if i == 0 {
            continue; // header
        }
        let f: Vec<&str> = line.split(',').collect();
        if f.len() < 25 || f[23] != "true" {
            continue; // tylko wiersze PASS
        }
        rows.push(Row {
            cath: f[0].to_string(),
            an: f[1].to_string(),
            el: f[2].to_string(),
            loading: f[3].parse().unwrap_or(20.0),
            np: f[4].parse().unwrap_or(1.1),
            temp: f[5].parse().unwrap_or(25.0),
            wh_kg: f[6].parse().unwrap_or(0.0),
            cost: f[9].parse().unwrap_or(0.0),
            score: f[24].parse().unwrap_or(0.0),
        });
    }
    rows.sort_by(|a, b| {
        b.score
            .partial_cmp(&a.score)
            .unwrap_or(std::cmp::Ordering::Equal)
    });
    rows
}

/// Uruchamia drabiny dla top-N konfiguracji PASS z CSV sweepu.
pub fn print_ladder(cli: &Cli, cp: &CellParams, sp: &SimParams) {
    let path = cli.get("--csv").unwrap_or("optim_winners.csv");
    let top = cli.get_usize("--top", 12);
    let mut rows = read_rows(path);
    rows.truncate(top);
    if rows.is_empty() {
        eprintln!("Brak wierszy PASS w {path} — najpierw uruchom sweep z --csv");
        std::process::exit(2);
    }
    println!(
        "Drabiny dla top {} PASS z {path} (każda komórka = cykle do EOL / wynik abuse):",
        rows.len()
    );

    println!("\n== Wybrane konfiguracje (top {} PASS) ==", rows.len());
    println!(
        "  {:<40} {:>8} {:>8} {:>7}",
        "konfiguracja", "Wh/kg", "$/kWh", "score"
    );
    for r in &rows {
        println!(
            "  {:<40} {:>8.1} {:>8.0} {:>7.2}",
            r.label(),
            r.wh_kg,
            r.cost,
            r.score
        );
    }

    println!("\n== Drabina C-rate (ładowanie; rozładowanie 1C) ==");
    println!(
        "  {:<40} {:>6} {:>6} {:>6} {:>6} {:>6} | max C z >=500 cyklami",
        "konfiguracja", "1C", "2C", "3C", "4C", "6C"
    );
    let mut best_rate: Vec<(String, f64)> = Vec::new();
    for r in &rows {
        let cell = r.cell(cp);
        let mut cycs = Vec::new();
        let mut max_c = 0.0f64;
        for &c in &RATE_LADDER {
            let s = simulate(&cell, cp, sp, c, 1.0, r.temp, 3000, None);
            if s.cycles >= 500 {
                max_c = c;
            }
            cycs.push(s.cycles);
        }
        best_rate.push((r.label(), max_c));
        println!(
            "  {:<40} {:>6} {:>6} {:>6} {:>6} {:>6} | {}",
            r.label(),
            cycs[0],
            cycs[1],
            cycs[2],
            cycs[3],
            cycs[4],
            if max_c > 0.0 {
                format!("{max_c:.0}C")
            } else {
                "brak".to_string()
            }
        );
    }

    println!("\n== Drabina abuse (piec + overcharge 1C, 3 h) ==");
    println!(
        "  {:<40} {:>14} {:>14} {:>14} {:>14} {:>14} | max bezpieczne T",
        "konfiguracja", "130°C", "150°C", "170°C", "200°C", "250°C"
    );
    let mut best_abuse: Vec<(String, f64)> = Vec::new();
    for r in &rows {
        let cell = r.cell(cp);
        let mut cells = Vec::new();
        let mut max_t = 0.0f64;
        for &t in &ABUSE_LADDER {
            let ab = Abuse {
                t_oven: t,
                overcharge: 1.0,
                t_max_h: 3.0,
            };
            let s = simulate(&cell, cp, sp, 1.0, 1.0, r.temp, 1, Some(ab));
            let ok = !(s.explosion || s.runaway || s.short);
            if ok {
                max_t = t;
            }
            let tag = if s.explosion {
                "EXPL"
            } else if s.runaway {
                "RUN"
            } else if s.short {
                "SHORT"
            } else {
                "OK"
            };
            cells.push(format!("{:.0}°C {}", s.t_max, tag));
        }
        best_abuse.push((r.label(), max_t));
        println!(
            "  {:<40} {:>14} {:>14} {:>14} {:>14} {:>14} | {}",
            r.label(),
            cells[0],
            cells[1],
            cells[2],
            cells[3],
            cells[4],
            if max_t > 0.0 {
                format!("{max_t:.0}°C")
            } else {
                "żadne".to_string()
            }
        );
    }

    println!("\n== Moc (drabina rozladowania przy 25 °C: deliv = % pojemnosci oddanej w oknie) ==");
    println!(
        "  {:<40} {:>7} {:>7} {:>7} {:>7} | max D z deliv >=50%",
        "konfiguracja", "1C", "2C", "3C", "5C"
    );
    const D_LADDER: [f64; 4] = [1.0, 2.0, 3.0, 5.0];
    let mut best_power: Vec<(String, f64)> = Vec::new();
    for r in &rows {
        let cell = r.cell(cp);
        let mut delivs = Vec::new();
        let mut max_d = 0.0f64;
        for &d in &D_LADDER {
            let s = simulate(&cell, cp, sp, 1.0, d, 25.0, 1, None);
            if s.delivered_frac_1 >= 0.5 {
                max_d = d;
            }
            delivs.push(s.delivered_frac_1 * 100.0);
        }
        best_power.push((r.label(), max_d));
        println!(
            "  {:<40} {:>6.0}% {:>6.0}% {:>6.0}% {:>6.0}% | {}",
            r.label(),
            delivs[0],
            delivs[1],
            delivs[2],
            delivs[3],
            if max_d > 0.0 {
                format!("{max_d:.0}C")
            } else {
                "brak".to_string()
            }
        );
    }

    println!("\n== Podsumowanie ==");
    if let Some((cfg, c)) = best_rate
        .iter()
        .max_by(|a, b| a.1.partial_cmp(&b.1).unwrap_or(std::cmp::Ordering::Equal))
    {
        println!("  najszybsze ładowanie z >=500 cyklami: {cfg} -> {c:.0}C");
    }
    if let Some((cfg, t)) = best_abuse
        .iter()
        .max_by(|a, b| a.1.partial_cmp(&b.1).unwrap_or(std::cmp::Ordering::Equal))
    {
        println!("  najwyzszy margines abuse: {cfg} -> {t:.0}°C");
    }
    if let Some((cfg, d)) = best_power
        .iter()
        .max_by(|a, b| a.1.partial_cmp(&b.1).unwrap_or(std::cmp::Ordering::Equal))
    {
        println!("  najwyzsza moc (rozladowanie, deliv >=50%): {cfg} -> {d:.0}C");
    }
}
