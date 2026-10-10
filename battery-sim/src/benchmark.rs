//! Benchmark: nasi kandydaci kontra ogniwa komercyjne (dane rynkowe 2025-2026).
//!
//! Tabela komercyjna oparta na komunikatach producentow i prasie branzowej;
//! zrodla (z linkami) w README, sekcja "Benchmark kontra rynek".

use crate::cell::{Cell, CellParams};
use crate::materials::{anode, cathode, electrolyte};
use crate::par;
use crate::sim::{simulate, Abuse, SimParams};

/// Nasz kandydat: kombinacja + metryki z symulacji.
pub struct OurRow {
    pub combo: String,
    pub wh_kg: f64,
    pub wh_kg_pack: f64,
    pub wh_l: f64,
    pub cost_kwh: f64,
    pub cycles: u64,
    pub eol: String,
    pub t80_min: f64,
    pub abuse_ok: bool,
    pub abuse_tmax: f64,
}

/// Wiersz tabeli komercyjnej ("bd" = brak danych).
pub struct CommRow {
    pub name: &'static str,
    pub wh_cell: &'static str,
    pub wh_pack: &'static str,
    pub wh_l: &'static str,
    pub cycles: &'static str,
    pub fast: &'static str,
    pub safety: &'static str,
    pub note: &'static str,
}

/// Ogniwa komercyjne / przedprodukcyjne (2025-2026; * = deklaracja producenta).
pub const COMMERCIAL: &[CommRow] = &[
    CommRow {
        name: "CATL Qilin (NMC)",
        wh_cell: "bd",
        wh_pack: "255",
        wh_l: "bd",
        cycles: "bd",
        fast: "do 5C (Shenxing)",
        safety: "ciecz palna",
        note: "pakiet; Zeekr 009, AITO, Li Auto (od 2023)",
    },
    CommRow {
        name: "BYD Blade (LFP)",
        wh_cell: "160",
        wh_pack: "140",
        wh_l: "bd",
        cycles: ">3000",
        fast: "~2C",
        safety: "b. wysokie",
        note: "LFP bez kobaltu; bestsellery BYD",
    },
    CommRow {
        name: "WeLion x NIO (polstale)",
        wh_cell: "360",
        wh_pack: "260",
        wh_l: "bd",
        cycles: "bd",
        fast: "bd",
        safety: "wysokie (zel)",
        note: "pierwsze polstale w produkcji seryjnej (2024); 150 kWh",
    },
    CommRow {
        name: "CATL condensed",
        wh_cell: "500",
        wh_pack: "bd",
        wh_l: "bd",
        cycles: "bd",
        fast: "bd",
        safety: "wysokie (zel)",
        note: "lotnictwo; 4-tonowy samolot oblatany 2025",
    },
    CommRow {
        name: "Amprius SiMaxx (Si)",
        wh_cell: "500",
        wh_pack: "bd",
        wh_l: "1300",
        cycles: "bd",
        fast: "bd",
        safety: "bd",
        note: "nanodruty krzemowe; wysylki lotnictwo/drony",
    },
    CommRow {
        name: "StoreDot XFC (Si 40%)",
        wh_cell: "300",
        wh_pack: "bd",
        wh_l: "bd",
        cycles: "1000 XFC*",
        fast: "10-80% <10 min",
        safety: "UN 38.3",
        note: "anoda krzemowa + katoda niklowa; 340 Wh/kg w 2026",
    },
    CommRow {
        name: "CATL Naxtra (Na-jon)",
        wh_cell: "175",
        wh_pack: "bd",
        wh_l: "bd",
        cycles: "10000+*",
        fast: "bd",
        safety: "GB 38031-2025",
        note: "produkcja od konca 2025; -40C; ~30% taniej niz LFP",
    },
    CommRow {
        name: "QuantumScape (Li-metal)",
        wh_cell: "301",
        wh_pack: "bd",
        wh_l: "844",
        cycles: "bd",
        fast: "bd",
        safety: "staly elektrolit",
        note: "wer. B-sample; probki 2026, auta 2028 (VW)",
    },
    CommRow {
        name: "Samsung SDI SolidStack",
        wh_cell: "bd",
        wh_pack: "bd",
        wh_l: "900*",
        cycles: "bd",
        fast: "bd",
        safety: "staly elektrolit",
        note: "cel 900 Wh/L; produkcja H2 2027",
    },
    CommRow {
        name: "BYD FinDreams (stale)",
        wh_cell: "~400*",
        wh_pack: "bd",
        wh_l: "bd",
        cycles: "bd",
        fast: "bd",
        safety: "staly elektrolit",
        note: "prototypy 20/60 Ah; auto demo 2027, skala ~2030",
    },
];

/// Nasi kandydaci: (katoda, anoda, elektrolit, loading, N/P).
pub const CANDIDATES: &[(&str, &str, &str, f64, f64)] = &[
    ("NMC811", "SIC", "GEL", 30.0, 1.1),
    ("NMC811", "SIC", "IONIC", 30.0, 1.1),
    ("NMC811", "SIC", "SOLID", 20.0, 1.1),
    ("NMC811", "GRAPHITE", "SOLID", 20.0, 1.1),
    ("NMC811", "SIC", "GEL", 25.0, 1.2),
    ("NA_PW", "HC", "LP57", 30.0, 1.1),
    ("NA_O3", "HC", "GEL", 25.0, 1.1),
    ("NA_NFPP", "HC", "GEL", 25.0, 1.1),
    ("DRX", "SIC", "SOLID", 20.0, 1.1),
    ("DRX", "LIFREE", "SOLID", 20.0, 1.05),
    ("LIO2", "LIMETAL", "IONIC", 10.0, 1.05),
    ("KPB", "GRAPHITE", "LP57", 30.0, 1.1),
];

/// Ocenia wszystkich kandydatow (2C, 25°C, 3000 cykli + test abusow).
pub fn evaluate_candidates(cp: &CellParams, sp: &SimParams) -> Vec<OurRow> {
    let abuse = Abuse {
        t_oven: 150.0,
        overcharge: 1.0,
        t_max_h: 3.0,
    };
    par::par_map(CANDIDATES.to_vec(), |(ca, an, el, ld, np)| {
        let cell = Cell::new(
            cathode(ca).expect("katoda"),
            anode(an).expect("anoda"),
            electrolyte(el).expect("elektrolit"),
            ld,
            np,
            cp,
        );
        let r = simulate(&cell, cp, sp, 2.0, 1.0, 25.0, 3000, None);
        let ab = simulate(&cell, cp, sp, 1.0, 1.0, 25.0, 1, Some(abuse));
        OurRow {
            combo: format!("{}/{}/{} load={:.0} N/P={:.2}", ca, an, el, ld, np),
            wh_kg: cell.wh_kg,
            wh_kg_pack: cell.wh_kg_pack,
            wh_l: cell.wh_l,
            cost_kwh: cell.cost_kwh,
            cycles: r.cycles,
            eol: r.eol.label(),
            t80_min: r.t80_min,
            abuse_ok: !(ab.explosion || ab.runaway || ab.short),
            abuse_tmax: ab.t_max,
        }
    })
}

/// Wypisuje obie tabele: nasi kandydaci + rynek.
pub fn print_benchmark(cp: &CellParams, sp: &SimParams) {
    println!("== Nasi kandydaci (symulacja: 2C, 25°C, pakiet x0.72) ==");
    println!(
        "  {:<36} {:>7} {:>8} {:>6} {:>6} {:>8} {:>6} {:>10}  abuse 150C",
        "kombinacja", "Wh/kg", "pak Wh/kg", "Wh/L", "$/kWh", "cykle@2C", "t80min", "EOL"
    );
    for r in evaluate_candidates(cp, sp) {
        println!(
            "  {:<36} {:7.1} {:8.1} {:6.0} {:6.0} {:8} {:6.1} {:>10}  {}",
            r.combo,
            r.wh_kg,
            r.wh_kg_pack,
            r.wh_l,
            r.cost_kwh,
            r.cycles,
            r.t80_min,
            r.eol,
            if r.abuse_ok {
                format!("OK (Tmax {:.0}°C)", r.abuse_tmax)
            } else {
                format!("FAIL (Tmax {:.0}°C)", r.abuse_tmax)
            }
        );
    }
    println!("\n== Ogniwa komercyjne (dane producentow/prasa 2025-2026; * = deklaracja; zrodla w README) ==");
    println!(
        "  {:<26} {:>8} {:>8} {:>6} {:>10} {:>16} {:>16}  uwagi",
        "ogniwo", "Wh/kg", "pak Wh/kg", "Wh/L", "cykle", "szybkie ladow.", "bezpiecz."
    );
    for c in COMMERCIAL {
        println!(
            "  {:<26} {:>8} {:>8} {:>6} {:>10} {:>16} {:>16}  {}",
            c.name, c.wh_cell, c.wh_pack, c.wh_l, c.cycles, c.fast, c.safety, c.note
        );
    }
}
