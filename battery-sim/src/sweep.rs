//! Sweep: siatka kombinacji materialow, kryteria projektu, scoring.
//!
//! Kryteria (zgodne z zalozeniami projektu):
//!   1) energia wlasciwa >= referencyjnego ogniwa Li-ion (NMC811/grafit/LP57)
//!   2) bezpieczenstwo: brak eksplozji / thermal runaway / zwarcia (cyklowanie + test abusow)
//!   3) >= 500 cykli przy SZYBKIM ladowaniu (>= 2C)

use crate::cell::{Cell, CellParams};
use crate::materials::{Anode, Cathode, Electrolyte};
use crate::sim::{simulate, Abuse, Eol, SimParams, SimResult};

/// Parametry kryteriow oceny.
pub struct Criteria {
    /// energia bazowa [Wh/kg] (NMC811/GRAPHITE/LP57, load=20, N/P=1.1)
    pub baseline_wh: f64,
    /// wymagany ulamek energii bazowej (1.0 = "nie gorsze niz Li-ion")
    pub energy_factor: f64,
    /// wymagana liczba cykli przy szybkim ladowaniu
    pub min_cycles: u64,
    /// C-rate'y uznawane za "szybkie ladowanie"
    pub fast_rates: Vec<f64>,
    /// protokol testu abusow
    pub abuse: Abuse,
    /// limit cykli w symulacji
    pub max_cycles: u64,
}

/// Jedna kombinacja do przetestowania.
#[derive(Clone)]
pub struct ComboJob {
    pub cath: Cathode,
    pub an: Anode,
    pub el: Electrolyte,
    pub loading: f64,
    pub np: f64,
    /// temperatura otoczenia podczas cyklowania [°C]
    pub t_amb: f64,
}

/// Wynik oceny kombinacji wg kryteriow.
pub struct ComboResult {
    pub cath: &'static str,
    pub an: &'static str,
    pub el: &'static str,
    pub loading: f64,
    pub np: f64,
    pub t_amb: f64,
    pub wh_kg: f64,
    pub mah_g: f64,
    pub energy_pass: bool,
    /// najlepsza liczba cykli sposrod szybkich C-rate
    pub cycles: u64,
    pub eol: Eol,
    /// C-rate, przy ktorym byla najlepsza liczba cykli
    pub c_best: f64,
    pub t80_min: f64,
    pub cycles_pass: bool,
    /// maksymalna temperatura podczas cyklowania [°C]
    pub t_max: f64,
    pub safety_pass: bool,
    pub abuse_explosion: bool,
    pub abuse_runaway: bool,
    pub abuse_short: bool,
    pub abuse_tmax: f64,
    /// wszystkie trzy kryteria spelnione
    pub passed: bool,
    /// wynik w skali 0..1 (do rankingu)
    pub score: f64,
}

/// Pelna ocena kombinacji materialow wg kryteriow projektu.
pub fn evaluate_combo(
    job: &ComboJob,
    crit: &Criteria,
    cp: &CellParams,
    sp: &SimParams,
) -> ComboResult {
    let cell = Cell::new(job.cath, job.an, job.el, job.loading, job.np, cp);
    let energy_pass = cell.wh_kg >= crit.baseline_wh * crit.energy_factor;

    let mut best: Option<SimResult> = None;
    let mut worst_safe = true;
    let mut t_max_cyc = job.t_amb;
    for &cch in &crit.fast_rates {
        let r = simulate(&cell, cp, sp, cch, 1.0, job.t_amb, crit.max_cycles, None);
        if r.runaway || r.explosion || r.short {
            worst_safe = false;
        }
        if r.t_max > t_max_cyc {
            t_max_cyc = r.t_max;
        }
        let better = match &best {
            None => true,
            Some(b) => r.cycles > b.cycles,
        };
        if better {
            best = Some(r);
        }
    }
    let best = best.expect("fast_rates nie moze byc puste");
    let cycles_pass = !(best.runaway || best.short) && best.cycles >= crit.min_cycles;

    // test abusow (piec + przeladowanie): ogniwo nie moze wybuchnac ani wejsc w thermal runaway
    let ab = simulate(&cell, cp, sp, 1.0, 1.0, job.t_amb, 1, Some(crit.abuse));
    let abuse_safe = !(ab.explosion || ab.runaway || ab.short);
    let safety_pass = worst_safe && abuse_safe;

    let passed = energy_pass && cycles_pass && safety_pass;
    let t80 = if best.t80_min > 0.0 {
        best.t80_min
    } else {
        60.0
    };
    let score = cell.wh_kg / 250.0 * 0.4
        + (best.cycles.min(1500) as f64) / 1500.0 * 0.3
        + if safety_pass { 0.2 } else { 0.0 }
        + (20.0 / t80).min(1.0) * 0.1;
    ComboResult {
        cath: cell.cath.name,
        an: cell.an.name,
        el: cell.el.name,
        loading: cell.loading_cat,
        np: cell.np,
        t_amb: job.t_amb,
        wh_kg: cell.wh_kg,
        mah_g: cell.mah_g,
        energy_pass,
        cycles: best.cycles,
        eol: best.eol,
        c_best: best.c_ch,
        t80_min: best.t80_min,
        cycles_pass,
        t_max: t_max_cyc,
        safety_pass,
        abuse_explosion: ab.explosion,
        abuse_runaway: ab.runaway,
        abuse_short: ab.short,
        abuse_tmax: ab.t_max,
        passed,
        score,
    }
}

/// Iloczyn kartezjanski osi siatki.
pub fn build_grid(
    cathodes: &[Cathode],
    anodes: &[Anode],
    electrolytes: &[Electrolyte],
    loadings: &[f64],
    nps: &[f64],
    temps: &[f64],
) -> Vec<ComboJob> {
    let mut jobs = Vec::new();
    for &cath in cathodes {
        for &an in anodes {
            for &el in electrolytes {
                for &loading in loadings {
                    for &np in nps {
                        for &t_amb in temps {
                            jobs.push(ComboJob {
                                cath,
                                an,
                                el,
                                loading,
                                np,
                                t_amb,
                            });
                        }
                    }
                }
            }
        }
    }
    jobs
}

/// Deterministyczny generator xorshift (do losowania podzbioru).
pub struct XorShift(u64);

impl XorShift {
    pub fn new(seed: u64) -> Self {
        XorShift(seed | 1)
    }
    pub fn next(&mut self) -> u64 {
        let mut x = self.0;
        x ^= x << 13;
        x ^= x >> 7;
        x ^= x << 17;
        self.0 = x;
        x
    }
    pub fn below(&mut self, n: usize) -> usize {
        (self.next() % n as u64) as usize
    }
}

/// Deterministyczna probka `k` elementow (mieszanie Fisher-Yates).
pub fn sample<T: Clone>(items: &[T], k: usize, seed: u64) -> Vec<T> {
    let k = k.min(items.len());
    let mut idx: Vec<usize> = (0..items.len()).collect();
    let mut rng = XorShift::new(seed);
    for i in 0..k {
        let j = i + rng.below(idx.len() - i);
        idx.swap(i, j);
    }
    idx[..k].iter().map(|&i| items[i].clone()).collect()
}
