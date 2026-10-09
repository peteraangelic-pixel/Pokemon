//! Wypisywanie wynikow: tabele, szczegoly ogniwa, eksport CSV.

use crate::cell::Cell;
use crate::sim::SimResult;
use crate::sweep::{ComboResult, Criteria};
use std::fs::File;
use std::io::{self, Write};

pub fn bool_s(b: bool) -> &'static str {
    if b {
        "true"
    } else {
        "false"
    }
}

pub fn print_cell_summary(cell: &Cell) {
    println!(
        "Ogniwo {}/{}/{} load={:.0}/{:.0} mg/cm^2 (kat/an) N/P={:.2}: {:.1} Wh/kg, {:.1} mAh/g, V_avg={:.3}, R0={:.2} Ohm*cm^2",
        cell.cath.name, cell.an.name, cell.el.name, cell.loading_cat, cell.loading_an, cell.np,
        cell.wh_kg, cell.mah_g, cell.v_avg, cell.r0
    );
    println!(
        "  V [{:.2}, {:.2}], m_tot={:.1} mg/cm^2 (katoda {:.1}, anoda {:.1}, elektrolit {:.1}, sep {:.1})",
        cell.v_min, cell.v_max, cell.m_tot, cell.m_cat, cell.m_an, cell.m_el, cell.m_sep
    );
}

pub fn print_criteria(crit: &Criteria) {
    println!(
        "Kryteria: energia >= {:.1} Wh/kg (bazowe Li-ion x{:.2}), >= {} cykli przy ladowaniu {:?}C, bezpieczny (brak eksplozji/runaway/zwarcia w cyklowaniu i abusa {}°C)",
        crit.baseline_wh, crit.energy_factor, crit.min_cycles, crit.fast_rates, crit.abuse.t_oven
    );
}

pub fn print_sim_line(r: &SimResult) {
    let mut flags = String::new();
    if r.runaway {
        flags.push_str("RUNAWAY ");
    }
    if r.explosion {
        flags.push_str("EXPL ");
    }
    if r.short {
        flags.push_str("SHORT");
    }
    println!(
        "  {:>8}/{:<8}/{:<6} load={:>4.0} C={:>3.0} T={:>4.0} | {:6.1} Wh/kg {:6.1} mAh/g V={:4.2} | EOL {:>12} @cyc {:5} | Tmax {:6.1}C | t80 {:5.1}min eta {:5.1}% | deliv {:4.0}% | sei {:5.1}nm plat {:6.2} | {}",
        r.cath, r.an, r.el, r.loading, r.c_ch, r.t_amb,
        r.wh_kg, r.mah_g, r.v_avg, r.eol.label(), r.cycles, r.t_max,
        r.t80_min, r.eta * 100.0, r.delivered_frac * 100.0, r.sei, r.plated, flags
    );
}

pub fn print_sim_summary(r: &SimResult) {
    let mut flags = String::new();
    if r.runaway {
        flags.push_str("RUNAWAY ");
    }
    if r.explosion {
        flags.push_str("EXPLOSION ");
    }
    if r.short {
        flags.push_str("SHORT");
    }
    if flags.is_empty() {
        flags.push_str("brak zdarzen");
    }
    println!(
        "\nWynik symulacji {}/{}/{} (ladowanie {:.0}C, rozladowanie {:.0}C, N/P {:.2}):",
        r.cath, r.an, r.el, r.c_ch, r.c_dis, r.np
    );
    println!(
        "  EOL: {} po {} cyklach ({:.1} h pracy)",
        r.eol.label(),
        r.cycles,
        r.hours
    );
    println!(
        "  Tmax: {:.1}°C | sprawnosc: {:.1}%",
        r.t_max,
        r.eta * 100.0
    );
    if r.t80_set {
        println!("  t80 (ladowanie do 80% SOC): {:.1} min", r.t80_min);
    } else {
        println!("  t80: nie osiagnieto 80% SOC przy tym C-rate");
    }
    println!(
        "  deliv (ostatni cykl): {:.0}% | deliv (cykl 1): {:.0}%",
        r.delivered_frac * 100.0,
        r.delivered_frac_1 * 100.0
    );
    println!(
        "  SEI: {:.1} nm | zaladowany lit: {:.2} mAh/cm^2 | R x{:.3}",
        r.sei, r.plated, r.r_mult
    );
    println!("  bezpieczenstwo: {flags}");
}

pub fn print_abuse_line(r: &SimResult) {
    let mut flags = String::new();
    if r.runaway {
        flags.push_str("RUNAWAY ");
    }
    if r.explosion {
        flags.push_str("EXPLOSION ");
    }
    if r.short {
        flags.push_str("SHORT");
    }
    if flags.is_empty() {
        flags.push_str("survives");
    }
    println!(
        "  {:>8}/{:<8}/{:<6} | Tmax {:6.1}C | {} ({:.2} h)",
        r.cath, r.an, r.el, r.t_max, flags, r.hours
    );
}

pub fn print_combo_line(r: &ComboResult) {
    println!(
        "  {:>8}/{:<8}/{:<6} load={:>4.0} T={:>3.0} | {:6.1} Wh/kg {} | cyc@fast {:5} {} (C={:.0}, t80 {:4.1}min) | Tmax {:5.1}C {} (abuse T {:5.1}C{}{}{}) | {} score {:.2}",
        r.cath, r.an, r.el, r.loading, r.t_amb, r.wh_kg,
        if r.energy_pass { "E" } else { "." },
        r.cycles,
        if r.cycles_pass { "C" } else { "." },
        r.c_best, r.t80_min,
        r.t_max,
        if r.safety_pass { "S" } else { "." },
        r.abuse_tmax,
        if r.abuse_explosion { " EXPL" } else { "" },
        if r.abuse_runaway { " RUN" } else { "" },
        if r.abuse_short { " SHORT" } else { "" },
        if r.passed { "PASS" } else { "FAIL" },
        r.score
    );
}

pub fn print_combo_table(results: &[ComboResult], top: usize) {
    println!();
    println!("  kombinacja          | Wh/kg  E | cykle@szybkim C (t80)      | Tmax   S | abus (Tmax)      | PASS/FAIL score");
    println!("  ----------------------------------------------------------------------------------------------------------");
    for r in results.iter().take(top) {
        print_combo_line(r);
    }
    if results.len() > top {
        println!(
            "  ... ({} kombinacji wiecej, uzyj --top)",
            results.len() - top
        );
    }
}

/// Zapisuje wyniki sweepu do CSV.
pub fn write_sweep_csv(path: &str, results: &[ComboResult]) -> io::Result<()> {
    let mut f = File::create(path)?;
    writeln!(
        f,
        "cathode,anode,electrolyte,loading_mg_cm2,np,temp_C,wh_kg,mah_g,energy_pass,cycles_fast,eol,c_best,t80_min,cycles_pass,t_max_cyc_C,safety_pass,abuse_tmax_C,abuse_explosion,abuse_runaway,abuse_short,passed,score"
    )?;
    for r in results {
        writeln!(
            f,
            "{},{},{},{:.1},{:.2},{:.0},{:.1},{:.1},{},{},{},{:.0},{:.1},{},{:.1},{},{:.1},{},{},{},{},{:.3}",
            r.cath, r.an, r.el, r.loading, r.np, r.t_amb, r.wh_kg, r.mah_g,
            bool_s(r.energy_pass), r.cycles, r.eol.label(), r.c_best, r.t80_min,
            bool_s(r.cycles_pass), r.t_max, bool_s(r.safety_pass), r.abuse_tmax,
            bool_s(r.abuse_explosion), bool_s(r.abuse_runaway), bool_s(r.abuse_short),
            bool_s(r.passed), r.score
        )?;
    }
    Ok(())
}

/// Zapisuje przebieg cykli (trace) do CSV.
pub fn write_trace_csv(path: &str, r: &SimResult) -> io::Result<()> {
    let mut f = File::create(path)?;
    writeln!(
        f,
        "cycle,soc_top,soc_end,capacity_mAh_cm2,li_inv,cath_frac,r_mult,sei_nm,plated_mAh_cm2,temp_C,t_charge_s,t_discharge_s"
    )?;
    for p in &r.trace {
        writeln!(
            f,
            "{},{:.4},{:.4},{:.4},{:.5},{:.5},{:.4},{:.2},{:.4},{:.2},{:.0},{:.0}",
            p.cycle,
            p.soc_top,
            p.soc_end,
            p.cap,
            p.li_inv,
            p.cath_frac,
            p.r_mult,
            p.sei,
            p.plated,
            p.temp,
            p.t_charge_s,
            p.t_discharge_s
        )?;
    }
    Ok(())
}

/// Wypisuje co `every` cykli skrot przebiegu (do podgladu zywotnosci).
pub fn print_trace_table(r: &SimResult, every: u64) {
    if r.trace.is_empty() {
        return;
    }
    println!("\nPrzebieg (co {every} cykli):");
    println!("  {{ cykl | SOC top/kon | kap [mAh/cm2] | Li inv | katoda | R x | SEI nm | T °C }}");
    let n = r.trace.len() as u64;
    let mut shown = 0u64;
    for (i, p) in r.trace.iter().enumerate() {
        let last = i as u64 == n - 1;
        if p.cycle % every == 0 || last {
            println!(
                "  {:5} | {:.3}/{:.3} | {:6.3} | {:.4} | {:.4} | {:.3} | {:5.1} | {:5.1}",
                p.cycle,
                p.soc_top,
                p.soc_end,
                p.cap,
                p.li_inv,
                p.cath_frac,
                p.r_mult,
                p.sei,
                p.temp
            );
            shown += 1;
            if shown > 40 {
                println!("  ... (obcieto, pelny przebieg w --csv)");
                break;
            }
        }
    }
}
