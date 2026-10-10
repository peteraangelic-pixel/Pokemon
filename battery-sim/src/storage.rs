//! Starzenie kalendarzowe (shelf life): ogniwo STOI na polce przy zadanym
//! SOC i temperaturze — bez cyklowania. To często dominujący tryb starzenia
//! (EV stoi ~95% czasu, magazyny stoją miesiącami, telefony na 100%).
//!
//! Model (kalibrowany do literatury; patrz README "Starzenie kalendarzowe"):
//!   - SEI rośnie ~ sqrt(t), najszybciej przy wysokim SOC (niski potencjał anody),
//!   - elektrolit utlenia się przy wysokim potencjale katody (v_katody vs Li > 3.8 V)
//!     — najszybciej przy 100% SOC i wysokiej temperaturze,
//!   - samo-rozładowanie (shuttle) proporcjonalne do czasu i SOC.
//!
//! Wynik: krzywa retencji pojemności oraz „shelf life” = czas do 80%.

use crate::benchmark::CANDIDATES;
use crate::cell::{Cell, CellParams};
use crate::materials::{anode, cathode, electrolyte};
use crate::sim::SimParams;
use crate::util::{arrhenius, interp};

/// Wynik symulacji przechowywania.
pub struct StorageResult {
    pub soc: f64,
    pub temp: f64,
    pub years: f64,
    /// frakcja pojemności początkowej na końcu symulacji
    pub cap_final: f64,
    pub sei_nm: f64,
    pub li_inv: f64,
    /// czas do spadku poniżej 80% (None = nie zeszło w symulacji)
    pub shelf_years: Option<f64>,
    /// krzywa retencji: (lata, frakcja pojemności)
    pub curve: Vec<(f64, f64)>,
}

/// Jeden wiersz tabeli porównawczej przechowywania.
pub struct StorageRow {
    pub combo: String,
    /// shelf life przy 25 °C / 50% SOC (lata; ">20" gdy poza horyzontem)
    pub shelf_25_50: String,
    /// shelf life przy 45 °C / 100% SOC
    pub shelf_45_100: String,
    /// retencja po 10 latach przy 45 °C / 100% SOC [%]
    pub ret_10y_45_100: f64,
}

/// Symuluje `years` lat przechowywania ogniwa przy SOC=`soc` i temperaturze `temp`.
#[allow(clippy::too_many_arguments)]
pub fn simulate_storage(
    cell: &Cell,
    _cp: &CellParams,
    sp: &SimParams,
    soc: f64,
    temp: f64,
    years: f64,
) -> StorageResult {
    // krok 1 dzień; stałe kalibrowane tak, żeby NMC/grafit/LP57 przy 25 °C/100% SOC
    // tracił ~3%/rok (i ~3x szybciej przy 45 °C), a LFP/LTO prawie w ogóle
    let k_sei_cal = 0.06; // nm / sqrt(h) przy 25 °C, SOC=1
    let ox_cal_k = 1.8e-5; // utlenianie: frakcja/godz przy (v_kat - 3.8)^2 = 1, 25 °C
    let dt_h = 24.0f64;
    let steps = (years * 365.0) as u64;

    let v_cath = interp(cell.cath.vcurve, soc);
    let v_an = interp(cell.an.vcurve, (soc / cell.np).min(1.0));
    let v_an_full = interp(cell.an.vcurve, 1.0);
    // SEI najszybciej przy pełnym naładowaniu (anoda najniżej względem Li)
    let f_sei_soc = 0.25 + 0.75 * (-(v_an - v_an_full) / 0.06).exp().min(1.0);
    // utlenianie tylko gdy katoda wysoko vs Li (i czynnik SOC)
    let ox_v = (v_cath - 3.8).max(0.0).powi(2);
    let f_ox_soc = 0.3 + 0.7 * soc;
    let f_sd_soc = 0.3 + 0.7 * soc;

    let mut li_inv = 1.0f64;
    let mut cath_frac = 1.0f64;
    let mut sei = 5.0f64;
    let mut shelf = None;
    let mut curve = Vec::new();
    let mut t_h = 0.0f64;
    for i in 0..=steps {
        if i % 182 == 0 || i == steps {
            let cap = li_inv.min(cath_frac);
            curve.push((t_h / 8760.0, cap));
            if shelf.is_none() && cap < 0.8 {
                shelf = Some(t_h / 8760.0);
            }
        }
        if i == steps {
            break;
        }
        // prawo sqrt(t): przyrost SEI to roznica sqrt(t), malejaca z czasem
        let d_sei = k_sei_cal
            * cell.an.sei
            * cell.el.sei
            * f_sei_soc
            * arrhenius(temp, 25.0, sp.ea_sei)
            * ((t_h + dt_h).sqrt() - t_h.sqrt());
        sei += d_sei;
        li_inv = (li_inv - d_sei * sp.li_per_nm).max(0.0);
        let ox = ox_cal_k * ox_v * f_ox_soc * arrhenius(temp, 25.0, sp.ea_fade) * dt_h;
        cath_frac = (cath_frac - ox).max(0.0);
        // samo-rozladowanie kalendarzowe: ~100x wolniejsze niz podczas cyklowania
        // (powierzchnie sa juz spasywowane SEI) — kalibracja: NMC ~2%/rok przy 25 °C
        li_inv = (li_inv - cell.cath.sd * 0.01 * f_sd_soc * dt_h).max(0.0);
        t_h += dt_h;
    }
    StorageResult {
        soc,
        temp,
        years,
        cap_final: li_inv.min(cath_frac),
        sei_nm: sei,
        li_inv,
        shelf_years: shelf,
        curve,
    }
}

fn shelf_label(r: &StorageResult) -> String {
    match r.shelf_years {
        Some(y) => format!("{y:.1}"),
        None => format!(">{:.0}", r.years),
    }
}

/// Wiersze tabeli porównawczej dla kandydatów (dwa zestawy warunków).
pub fn storage_rows(cp: &CellParams, sp: &SimParams) -> Vec<StorageRow> {
    CANDIDATES
        .iter()
        .map(|&(ca, an, el, ld, np, _temp)| {
            let cell = Cell::new(
                cathode(ca).expect("katoda"),
                anode(an).expect("anoda"),
                electrolyte(el).expect("elektrolit"),
                ld,
                np,
                cp,
            );
            let r1 = simulate_storage(&cell, cp, sp, 0.5, 25.0, 20.0);
            let r2 = simulate_storage(&cell, cp, sp, 1.0, 45.0, 20.0);
            let r3 = simulate_storage(&cell, cp, sp, 1.0, 45.0, 10.0);
            StorageRow {
                combo: format!("{ca}/{an}/{el} load={ld:.0}"),
                shelf_25_50: shelf_label(&r1),
                shelf_45_100: shelf_label(&r2),
                ret_10y_45_100: r3.cap_final * 100.0,
            }
        })
        .collect()
}

/// Tabela Markdown (do raportu).
pub fn table_md(rows: &[StorageRow]) -> String {
    let mut s = String::new();
    s.push_str("| kandydat | shelf life @25 °C/50% SOC | shelf life @45 °C/100% SOC | retencja 10 lat @45 °C/100% |\n");
    s.push_str("|---|---|---|---|\n");
    for r in rows {
        s.push_str(&format!(
            "| {} | {} lat | {} lat | {:.0}% |\n",
            r.combo, r.shelf_25_50, r.shelf_45_100, r.ret_10y_45_100
        ));
    }
    s
}

/// Wypisuje tabelę porównawczą na konsolę.
pub fn print_table(cp: &CellParams, sp: &SimParams) {
    println!("== Starzenie kalendarzowe (przechowywanie, 20 lat horyzontu) ==");
    println!(
        "  {:<34} {:>16} {:>18} {:>16}",
        "kandydat", "shelf 25°C/50%", "shelf 45°C/100%", "retencja 10l 45/100"
    );
    for r in storage_rows(cp, sp) {
        println!(
            "  {:<34} {:>14} lat {:>16} lat {:>14.0}%",
            r.combo, r.shelf_25_50, r.shelf_45_100, r.ret_10y_45_100
        );
    }
}

/// Wypisuje pojedynczą symulację przechowywania (krzywa retencji).
pub fn print_single(r: &StorageResult) {
    println!(
        "Przechowywanie: SOC={:.0}%, T={:.0}°C, horyzont {:.0} lat",
        r.soc * 100.0,
        r.temp,
        r.years
    );
    println!(
        "  SEI na końcu: {:.1} nm | inwentarz Li: {:.1}%",
        r.sei_nm,
        r.li_inv * 100.0
    );
    match r.shelf_years {
        Some(y) => println!("  shelf life (do 80% pojemności): {y:.1} lat"),
        None => println!(
            "  shelf life: >{:.0} lat (pojemność {:.0}% po {:.0} latach)",
            r.years,
            r.cap_final * 100.0,
            r.years
        ),
    }
    println!("  retencja:");
    for (y, cap) in &r.curve {
        println!("    rok {y:>5.1}: {:5.1}%", cap * 100.0);
    }
}
