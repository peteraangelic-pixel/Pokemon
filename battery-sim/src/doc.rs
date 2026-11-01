//! Reports contain current numerical results, without historical marketing claims.
use crate::benchmark::evaluate_candidates;
use crate::cell::CellParams;
use crate::sim::SimParams;
use std::{fs, io};

pub fn write_report(path: &str, lang: &str, cp: &CellParams, sp: &SimParams) -> io::Result<usize> {
    let md = render(lang, cp, sp);
    fs::write(path, &md)?;
    Ok(md.lines().count())
}

pub fn write_pitch(path: &str, lang: &str) -> io::Result<usize> {
    write_report(path, lang, &CellParams::default(), &SimParams::default())
}

pub fn write_investor(path: &str, lang: &str) -> io::Result<usize> {
    write_report(path, lang, &CellParams::default(), &SimParams::default())
}

fn render(lang: &str, cp: &CellParams, sp: &SimParams) -> String {
    let mut s = if lang == "en" {
        "# Battery research status — numerical model v0.2.0\n\n\
         **Unvalidated model. No physical cells, safety certification or manufacturing-cost validation.**\n\n\
         CC charging at 2C, discharge at 1C, currents referenced to initial capacity. No CV phase. \
         SOC is continuous between cycles. Qualification requires at least 80% of remaining capacity \
         delivered and a measured 10–80% SOC interval no longer than 30 minutes. \
         A counter value is not equivalent to full cycles: see EFC.\n\n\
         Nominal OCV energy is not delivered energy. Wh/L remains a dry-stack estimate, \
         and material costs cover only selected materials, excluding manufacturing and yield. \
         Pack energy uses an assumed fixed factor, not a designed pack. \
         Overcharge chemistry beyond full SOC is missing, so absence of a simulated thermal event \
         cannot produce a complete safety pass. Degradation constants have NOT been recalibrated after fixes.\n\n".to_string()
    } else {
        "# Stan badan baterii — model numeryczny v0.2.0\n\n\
         **Model niezwalidowany. Brak fizycznych ogniw, certyfikacji bezpieczenstwa i potwierdzenia kosztu produkcji.**\n\n\
         Ladowanie CC 2C, rozladowanie 1C, prady odniesione do poczatkowej pojemnosci. Brak fazy CV. \
         SOC jest ciagly miedzy cyklami. Cykl kwalifikowany oddaje >=80% aktualnej pojemnosci \
         i osiaga zmierzony przedzial 10–80% SOC w <=30 minut. Licznik cykli nie oznacza pelnych cykli: patrz EFC.\n\n\
         Energia nominalna OCV nie oznacza energii oddanej. Wh/L pozostaje przyblizeniem suchego stosu, \
         a koszt obejmuje wybrane materialy, bez produkcji i uzysku. Energia pakietu korzysta z zalozonego \
         stalego mnoznika, nie projektu pakietu. Brak chemii przeladowania poza pelnym SOC oznacza, ze brak \
         zdarzenia cieplnego w symulacji nie daje pelnego PASS bezpieczenstwa. Stale degradacji \
         NIE zostaly ponownie skalibrowane po poprawkach.\n\n".to_string()
    };
    s.push_str("| configuration / konfiguracja | nominal Wh/kg | delivered Wh/kg, cycle 1 | raw cycles | qualified cycles | EFC | 10–80% min, cycle 1 | EOL | abuse coverage | physical validation |\n");
    s.push_str("|---|---:|---:|---:|---:|---:|---:|---|---|---|\n");
    for r in evaluate_candidates(cp, sp) {
        let t = r
            .t10_80_min
            .map(|v| format!("{v:.2}"))
            .unwrap_or_else(|| "NA".into());
        s.push_str(&format!(
            "| {} | {:.1} | {:.1} | {} | {} | {:.1} | {} | {} | {} | unvalidated |\n",
            r.combo,
            r.wh_kg,
            r.delivered_wh_kg_1,
            r.cycles,
            r.qualifying_cycles,
            r.efc,
            t,
            r.eol,
            if r.abuse_model_complete {
                "thermal diagnostic only"
            } else {
                "incomplete"
            }
        ));
    }
    s.push_str("\nNo candidate is established as superior to commercial cells. No production date or production cost is established.\n\n");
    s.push_str("## Separate calendar-aging diagnostic (uncalibrated)\n\nThis phenomenological storage model is NOT coupled to cycling, pressure, gas generation or lithium-metal corrosion. Its projected years are not established shelf life.\n\n");
    s.push_str(&crate::storage::table_md(&crate::storage::storage_rows(
        cp, sp,
    )));
    s.push_str("Remaining gaps: silicon mechanics and formation loss; real anode-free lithium inventory and volume; electrolyte-specific mass, volume and salt compatibility; calibrated thermal geometry and reactions; combined calendar/cycling aging; independent validation datasets.\n\n");
    s.push_str("Historical audit and evidence: [audyt-2026-11-01](../audyt-2026-11-01/README.md). Release changes: [ZMIANY_V02.md](ZMIANY_V02.md). Python prototype is historical and is no longer a 1:1 reference.\n");
    s
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn report_distinguishes_nominal_energy_from_delivery_and_missing_validation() {
        let md = render("en", &CellParams::default(), &SimParams::default());
        assert!(md.contains("delivered Wh/kg"));
        assert!(md.contains("incomplete"));
        assert!(md.contains("NOT been recalibrated"));
        assert!(!md.contains("1–2 years"));
        assert!(!md.contains("within ~±15%"));
    }
}
