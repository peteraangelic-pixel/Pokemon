//! Konstrukcja ogniwa: bilanse masy/energii, opor wewnetrzny, okno napiec.
//!
//! Wszystko liczone na cm^2 elektrody (jedna strona): masy powlok, folie
//! (Al 12 um / Cu 8 um), separator (PP 20 um), elektrolit (g/Ah), obudowa.

use crate::materials::{
    cost_an_usd_kg, cost_cath_usd_kg, cost_el_usd_kg, Anode, Cathode, Electrolyte,
};
use crate::util::{interp, F, RG};

/// Parametry konstrukcyjne ogniwa (identyczne dla wszystkich materialow).
/// (Masa powloki i N/P sa parametrami pojedynczego ogniwa — patrz `Cell::new`.)
#[derive(Clone, Copy)]
pub struct CellParams {
    /// porowatosc separatora
    pub por_sep: f64,
    /// grubosc separatora [cm] (PP 20 um)
    pub t_sep: f64,
    /// porowatosc elektrod
    pub por_e: f64,
    /// grubosc folii Al [cm]
    pub foil_al: f64,
    /// gestosc Al [g/cm^3]
    pub dens_al: f64,
    /// grubosc folii Cu [cm]
    pub foil_cu: f64,
    /// gestosc Cu [g/cm^3]
    pub dens_cu: f64,
    /// gestosc separatora [g/cm^3]
    pub dens_sep: f64,
    /// elektrolit [g/Ah]
    pub e_per_c: f64,
    /// mnoznik masy obudowy/tabow (pouch)
    pub pack: f64,
    /// wspolczynnik wnikania ciepla [W/m^2/K] (obie strony elektrody)
    pub h: f64,
    /// cieplo wlasciwe elektrod [J/g/K]
    pub cp: f64,
    /// wspolczynnik symetrii Butler-Volmera
    pub alpha: f64,
    /// udzial polaryzacji koncentracyjnej w nadwoltazu anody
    pub k_conc: f64,
    /// margines napiecia ladowania ponad OCV przy pelnym SOC [V]
    pub v_margin_top: f64,
    /// margines rozladowania ponizej OCV przy pustym SOC [V]
    pub v_margin_bot: f64,
    /// minimalny udzial i0 przy SOC = 0 / 1
    pub i0_floor: f64,
    /// udzial energii ogniwa dostarczanej na poziomie pakietu
    /// (ogniwo -> pakiet: BMS, obudowa, chlodzenie; typowo 0.70-0.75)
    pub pack_factor: f64,
}

impl Default for CellParams {
    fn default() -> Self {
        CellParams {
            por_sep: 0.45,
            t_sep: 0.002,
            por_e: 0.32,
            foil_al: 0.0012,
            dens_al: 2.70,
            foil_cu: 0.0008,
            dens_cu: 8.96,
            dens_sep: 0.91,
            e_per_c: 2.7,
            pack: 1.06,
            h: 10.0,
            cp: 1.0,
            alpha: 0.5,
            k_conc: 0.5,
            v_margin_top: 0.10,
            v_margin_bot: 0.25,
            i0_floor: 0.25,
            pack_factor: 0.72,
        }
    }
}

/// Zbudowane ogniwo (parametry wynikowe na cm^2 elektrody).
pub struct Cell {
    pub cath: Cathode,
    pub an: Anode,
    pub el: Electrolyte,
    /// masa powloki katodowej [mg/cm^2]
    pub loading_cat: f64,
    /// masa powloki anodowej [mg/cm^2]
    pub loading_an: f64,
    pub np: f64,
    /// pojemnosc poczatkowa [mAh/cm^2] (ogranicza katoda)
    pub cap0: f64,
    /// energia wlasciwa ogniwa [Wh/kg]
    pub wh_kg: f64,
    /// energia wlasciwa na poziomie pakietu [Wh/kg] (wh_kg * pack_factor)
    pub wh_kg_pack: f64,
    /// energia volumetryczna ogniwa [Wh/L] (bez obudowy pakietu)
    pub wh_l: f64,
    /// szacunkowy koszt materialowy [USD/kWh] (aktywne + elektrolit)
    pub cost_kwh: f64,
    /// grubosc ogniwa [cm] (katoda + anoda + separator + folie)
    pub t_tot: f64,
    /// pojemnosc wlasciwa ogniwa [mAh/g]
    pub mah_g: f64,
    /// srednie napiecie rozladowania (calka po SOC) [V]
    pub v_avg: f64,
    /// masa calkowita na cm^2 [mg/cm^2]
    pub m_tot: f64,
    pub m_cat: f64,
    pub m_an: f64,
    pub m_el: f64,
    pub m_sep: f64,
    /// opor wewnetrzny poczatkowy [Ohm*cm^2]
    pub r0: f64,
    /// napiecie odciecia ladowania [V]
    pub v_max: f64,
    /// napiecie odciecia rozladowania [V]
    pub v_min: f64,
    /// pojemnosc cieplna na cm^2 [mJ/K]
    pub c_th: f64,
    /// wspolczynnik oddawania ciepla na cm^2 [mW/K]
    pub ha: f64,
    /// temperatura topnienia separatora (zwarcie) [°C]
    pub sep_melt: f64,
    /// temperatura zamkniecia separatora PP (brak pradu) [°C]
    pub t_shutdown: f64,
}

impl Cell {
    pub fn new(
        cath: Cathode,
        an: Anode,
        el: Electrolyte,
        loading_cat: f64,
        np: f64,
        p: &CellParams,
    ) -> Cell {
        let cap = loading_cat * cath.cap_mah_g * cath.act / 1000.0; // mAh/cm^2
        let loading_an = np * cap / (an.cap_mah_g * an.act) * 1000.0; // mg/cm^2

        // ogniwa sodowe (katody NA_*): kolektorem anody jest tez Al
        // (Na nie tworzy stopow z Al -- oszczednosc masy i kosztu vs Cu)
        let na_ion = cath.name.starts_with("NA_");
        // masy na cm^2 elektrody [mg/cm^2]
        let m_cat = loading_cat / cath.act;
        let m_an = loading_an / an.act;
        let m_al = p.foil_al * p.dens_al * 1000.0;
        let (m_foil_an, t_foil_an) = if na_ion {
            (p.foil_al * p.dens_al * 1000.0, p.foil_al)
        } else {
            (p.foil_cu * p.dens_cu * 1000.0, p.foil_cu)
        };
        let m_sep = p.t_sep * p.dens_sep * 1000.0;
        let m_el = p.e_per_c * cap; // g/Ah * mAh/cm^2 -> mg/cm^2
        let m_tot = (m_cat + m_an + m_al + m_foil_an + m_sep + m_el) * p.pack;

        // srednie napiecie ogniwa (calka po SOC)
        let n = 24;
        let mut v_avg = 0.0;
        for i in 0..n {
            let s = (i as f64 + 0.5) / n as f64;
            v_avg += interp(cath.vcurve, s) - interp(an.vcurve, (s / np).min(1.0));
        }
        v_avg /= n as f64;

        let wh_kg = cap * v_avg / m_tot * 1000.0;
        let wh_kg_pack = wh_kg * p.pack_factor;
        let mah_g = cap / (m_tot / 1000.0);

        // opor wewnetrzny [Ohm*cm^2]
        let kap = el.kappa_ms_cm / 1000.0; // S/cm
        let t_cat = (m_cat / 1000.0) / (cath.dens * (1.0 - p.por_e)); // cm
        let t_an = (m_an / 1000.0) / (an.dens * (1.0 - p.por_e));
        let t_tot = t_cat + t_an + p.t_sep + p.foil_al + t_foil_an; // cm
                                                                    // energia volumetryczna: mWh/cm^2 / cm^3/cm^2 = Wh/L
        let wh_l = cap * v_avg / t_tot;
        // koszt materialowy [USD/kWh]: aktywne materialy + elektrolit
        // (masy w mg/cm^2 -> kg/cm^2, koszt USD/kg -> USD/cm^2)
        let cost_cm2 = m_cat / 1.0e6 * cost_cath_usd_kg(cath.name)
            + m_an / 1.0e6 * cost_an_usd_kg(an.name)
            + m_el / 1.0e6 * cost_el_usd_kg(el.name);
        let cost_kwh = cost_cm2 / (cap * v_avg / 1000.0) * 1000.0;
        let r_sep = p.t_sep / (kap * p.por_sep.powf(1.5));
        let r_e = (t_cat + t_an) / (kap * p.por_e.powf(1.5)) / 4.0;
        let r_ct = RG * 298.15 / (F * (cath.i0 + an.i0) / 1000.0) * 0.2;
        let r0 = r_sep + r_e + r_ct + el.r_if;

        let v_max = cath.vmax - interp(an.vcurve, 1.0 / np) + p.v_margin_top;
        let v_min = interp(cath.vcurve, 0.0) - interp(an.vcurve, 0.0) - p.v_margin_bot;

        let c_th = m_tot * p.cp; // mJ/K na cm^2
        let ha = 2.0 * p.h * 1e-4 * 1000.0; // mW/K na cm^2 (obie strony)

        let is_solid = el.name == "SOLID";
        // elektrolit zelowy (GEL) wspolpracuje z separatorem ceramicznym
        // (wyzsza temperatura zwarcia niz standardowy PP 160°C)
        let sep_melt = if is_solid {
            300.0
        } else if el.name == "GEL" {
            200.0
        } else {
            160.0
        };
        Cell {
            cath,
            an,
            el,
            loading_cat,
            loading_an,
            np,
            cap0: cap,
            wh_kg,
            wh_kg_pack,
            wh_l,
            cost_kwh,
            t_tot,
            mah_g,
            v_avg,
            m_tot,
            m_cat,
            m_an,
            m_el,
            m_sep,
            r0,
            v_max,
            v_min,
            c_th,
            ha,
            sep_melt,
            t_shutdown: if is_solid { 1.0e9 } else { 130.0 },
        }
    }
}
