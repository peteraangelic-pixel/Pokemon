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
    println!(
        "  pakiet (mnoznik): {:.1} Wh/kg | suchy stos {:.0} Wh/L | grubosc {:.0} um | wybrane materialy ~${:.0}/kWh (bez produkcji)",
        cell.wh_kg_pack,
        cell.wh_l,
        cell.t_tot * 1.0e4,
        cell.cost_kwh
    );
}

pub fn print_criteria(crit: &Criteria) {
    println!(
        "Kryteria modelowe: energia ODDANA >= {:.1} Wh/kg (referencja 25C, 2C/1C CC x{:.2}), >= {} kwalifikowanych cykli przy {:?}C (>=2C; >=80% pojemnosci i 10-80% <=30 min), diagnostyka pieca {}°C; bezpieczenstwo fizyczne NIEZWERYFIKOWANE",
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
        "  Energia oddana: {:.1} Wh/kg (cykl 1), {:.1} Wh/kg (ostatni); nominalna OCV: {:.1} Wh/kg",
        r.delivered_wh_kg_1, r.delivered_wh_kg_last, r.wh_kg
    );
    println!(
        "  Przeplyw: {:.4} mAh/cm2 in, {:.4} out; {:.3} EFC; energia {:.4}/{:.4} mWh/cm2 in/out",
        r.charge_mah, r.discharge_mah, r.efc, r.energy_in_mwh, r.energy_out_mwh
    );
    println!(
        "  10-80% SOC: {} min (cykl 1), max {} min; kwalifikowane cykle: {}",
        option_display(r.t10_80_min_1),
        option_display(r.t10_80_max_min),
        r.qualifying_cycles
    );
    println!("  Protokol: CC, prad odniesiony do poczatkowego Ah; BEZ etapu CV; stale nieprzekalibrowane.");
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
    println!(
        "  pakiet: {:.1} Wh/kg | {:.0} Wh/L | koszt materialowy ~${:.0}/kWh",
        r.wh_kg_pack, r.wh_l, r.cost_kwh
    );
    println!("  zdarzenia w modelu: {flags}; bezpieczenstwo fizyczne NIEZWERYFIKOWANE");
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
        flags.push_str("brak zdarzen W MODELU");
    }
    println!(
        "  {:>8}/{:<8}/{:<6} | Tmax {:6.1}C | {} ({:.2} h)",
        r.cath, r.an, r.el, r.t_max, flags, r.hours
    );
    println!(
        "    przeplyw {:.4} mAh/cm2; pokrycie przeladowania: {}; walidacja fizyczna: NIE",
        r.charge_mah,
        if r.abuse_model_complete {
            "thermal-only"
        } else {
            "NIEPELNE (brak chemii poza 100% SOC)"
        }
    );
}

pub fn print_combo_line(r: &ComboResult) {
    println!(
        "  {:>8}/{:<8}/{:<6} load={:>4.0} T={:>3.0} | {:6.1} Wh/kg ({:5.1} pak) {:6.1} Wh/L ${:3.0}/kWh {} | cyc@fast {:5} {} (C={:.0}, t80 {:4.1}min) | Tmax {:5.1}C {} (abuse T {:5.1}C{}{}{}) | {} score {:.2}",
        r.cath, r.an, r.el, r.loading, r.t_amb, r.wh_kg, r.wh_kg_pack, r.wh_l, r.cost_kwh,
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
    println!("    energia oddana {:.1} Wh/kg; {:.1} EFC; {} kwalifikowanych cykli; 10-80% {} min; performance_pass={}; abuse_complete={}; physical_validation=unvalidated",
        r.delivered_wh_kg_1, r.efc, r.qualifying_cycles, option_number(r.t10_80_min), r.performance_pass, r.abuse_model_complete);
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
        "cathode,anode,electrolyte,loading_mg_cm2,np,temp_C,wh_kg,pack_wh_kg,wh_l,cost_usd_kwh,mah_g,energy_pass,cycles_fast,eol,c_best,t80_min,cycles_pass,t_max_cyc_C,safety_pass,abuse_tmax_C,abuse_explosion,abuse_runaway,abuse_short,passed,score,delivered_wh_kg_1,efc,qualifying_cycles,t10_80_min,performance_pass,abuse_model_complete,physical_validation,model_version,charge_protocol,current_reference"
    )?;
    for r in results {
        writeln!(
            f,
            "{},{},{},{:.1},{:.2},{:.0},{:.1},{:.1},{:.0},{:.0},{:.1},{},{},{},{:.0},{:.1},{},{:.1},{},{:.1},{},{},{},{},{:.3},{:.3},{:.4},{},{},{},{},unvalidated,0.2.0,CC,initial_capacity",
            r.cath, r.an, r.el, r.loading, r.np, r.t_amb, r.wh_kg, r.wh_kg_pack, r.wh_l, r.cost_kwh, r.mah_g,
            bool_s(r.energy_pass), r.cycles, r.eol.label(), r.c_best, r.t80_min,
            bool_s(r.cycles_pass), r.t_max, bool_s(r.safety_pass), r.abuse_tmax,
            bool_s(r.abuse_explosion), bool_s(r.abuse_runaway), bool_s(r.abuse_short),
            bool_s(r.passed), r.score, r.delivered_wh_kg_1, r.efc, r.qualifying_cycles,
            option_number(r.t10_80_min), bool_s(r.performance_pass), bool_s(r.abuse_model_complete)
        )?;
    }
    Ok(())
}

/// Zapisuje przebieg cykli (trace) do CSV.
pub fn write_trace_csv(path: &str, r: &SimResult) -> io::Result<()> {
    let mut f = File::create(path)?;
    writeln!(
        f,
        "cycle,soc_top,soc_end,capacity_mAh_cm2,li_inv,cath_frac,r_mult,sei_nm,plated_mAh_cm2,temp_C,t_charge_s,t_discharge_s,soc_start,charge_mAh_cm2,discharge_mAh_cm2,energy_in_mWh_cm2,energy_out_mWh_cm2,efc,t10_80_min"
    )?;
    for p in &r.trace {
        writeln!(
            f,
            "{},{:.6},{:.6},{:.6},{:.6},{:.6},{:.6},{:.4},{:.6},{:.4},{:.4},{:.4},{:.6},{:.6},{:.6},{:.6},{:.6},{:.6},{}",
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
            p.t_discharge_s, p.soc_start, p.charge_mah, p.discharge_mah,
            p.energy_in_mwh, p.energy_out_mwh, p.efc, option_number(p.t10_80_min)
        )?;
    }
    Ok(())
}

fn option_number(value: Option<f64>) -> String {
    value.map(|v| format!("{v:.4}")).unwrap_or_default()
}

fn option_display(value: Option<f64>) -> String {
    value
        .map(|v| format!("{v:.4}"))
        .unwrap_or_else(|| "NA".into())
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
