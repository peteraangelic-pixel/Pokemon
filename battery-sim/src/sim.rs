//! Symulacja cykliczna (CC-CV-lite: ladowanie/rozladowanie CC z odcieciami
//! napieciowymi), degradacja, termika brylowa i bezpieczenstwo.
//!
//! v0.2: poprawki numeryczne po audycie; stare stale NIE sa ponownie skalibrowane.
//! Protokol cykliczny: CC, prad odniesiony do POCZATKOWEJ pojemnosci, bez etapu CV.

use crate::cell::{Cell, CellParams};
use crate::materials::{Anode, Cathode, Electrolyte};
use crate::util::{arrhenius, interp, F, RG};

/// Parametry modelu degradacji / termiki / bezpieczenstwa.
#[derive(Clone, Copy)]
pub struct SimParams {
    pub ea_fade: f64,     // aktywacja degradacji katody [J/mol]
    pub ea_sei: f64,      // aktywacja wzrostu SEI [J/mol]
    pub ea_ion: f64,      // aktywacja przewodnictwa jonowego [J/mol]
    pub ea_act: f64,      // aktywacja kinetyki elektrod [J/mol]
    pub ea_an_rxn: f64,   // aktywacja reakcji litowanej anody [J/mol]
    pub tref_an_rxn: f64, // temperatura referencyjna reakcji anody [°C]
    pub ea_exo_sei: f64,
    pub tref_exo_sei: f64,
    pub k_exo_sei: f64, // cieplo rozkladu SEI [mW/g] przy ref
    pub ea_exo_elec: f64,
    pub tref_exo_elec: f64,
    pub k_exo_elec: f64, // rozklad elektrolitu [mW/g] przy ref
    pub k_comb: f64,     // spalanie elektrolitu [mW/g] (>= t_decomp)
    pub ea_exo_cath: f64,
    pub tref_exo_cath: f64,
    pub k_exo_cath: f64,    // rozklad katody [mW/g] przy ref
    pub tau_an: f64,        // czas rozkladu energii egzotermicznej anody [s]
    pub tau_cath: f64,      // czas rozkladu energii egzotermicznej katody [s]
    pub k_sei: f64,         // wzrost SEI [nm / sqrt(h)] przy 25°C
    pub li_per_nm: f64,     // ubytek inwentarza Li na nm SEI
    pub fade_base: f64,     // degradacja katody [ulamek/cykl] przy 1C, 25°C, V=3.8
    pub plat_gain: f64,     // wzmocnienie frakcji ladowania litowego
    pub plat_k: f64,        // skala eksponencjalna platingu [V]
    pub ox_k: f64,          // stres oksydacyjny elektrolitu (V ponad okno)^2
    pub t_runaway: f64,     // prog thermal runaway [°C]
    pub dt_max: f64,        // maksymalny krok czasowy [s]
    pub dt_min: f64,        // minimalny krok czasowy [s]
    pub min_delivered: f64, // EOL "rate-limited" gdy ogniwo nie oddaje tej frakcji w oknie
}

impl Default for SimParams {
    fn default() -> Self {
        SimParams {
            ea_fade: 35000.0,
            ea_sei: 50000.0,
            ea_ion: 15000.0,
            ea_act: 30000.0,
            ea_an_rxn: 80000.0,
            tref_an_rxn: 150.0,
            ea_exo_sei: 60000.0,
            tref_exo_sei: 120.0,
            k_exo_sei: 0.05,
            ea_exo_elec: 110000.0,
            tref_exo_elec: 160.0,
            k_exo_elec: 200.0,
            k_comb: 100000.0,
            ea_exo_cath: 140000.0,
            tref_exo_cath: 280.0,
            k_exo_cath: 5000.0,
            tau_an: 90.0,
            tau_cath: 120.0,
            k_sei: 0.012,
            li_per_nm: 0.0008,
            fade_base: 1.2e-4,
            plat_gain: 0.002,
            plat_k: 0.025,
            ox_k: 8e-4,
            t_runaway: 200.0,
            dt_max: 10.0,
            dt_min: 0.5,
            min_delivered: 0.80,
        }
    }
}

/// Protokol testu abusow: piec + przeladowanie.
#[derive(Clone, Copy)]
pub struct Abuse {
    /// temperatura pieca [°C]
    pub t_oven: f64,
    /// prad przeladowania [C]
    pub overcharge: f64,
    /// czas trwania [h]
    pub t_max_h: f64,
}

/// Przyczyna zakonczenia symulacji (EOL).
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Eol {
    /// pojemnosc spadla ponizej 80% poczatkowej
    Fade80,
    /// zwarcie wewnetrzne (dendryty lub stopiony separator)
    Short,
    /// thermal runaway / eksplozja
    Runaway,
    /// ogniwo nie jest w stanie pracowac zadanym C-rate (poza oknem napiec)
    RateLimited,
    /// prad zablokowany przez separator lub przekroczony czas kroku/protokolu
    ProtocolStopped,
    /// symulacja osiagnela limit cykli
    Survived(u64),
}

impl Eol {
    pub fn label(&self) -> String {
        match self {
            Eol::Fade80 => "fade80".to_string(),
            Eol::Short => "short".to_string(),
            Eol::Runaway => "runaway".to_string(),
            Eol::RateLimited => "rate-limited".to_string(),
            Eol::ProtocolStopped => "protocol-stopped".to_string(),
            Eol::Survived(n) => format!(">={n}"),
        }
    }
}

/// Jeden wpis przebiegu (koniec cyklu).
#[derive(Clone, Copy)]
pub struct TracePoint {
    pub cycle: u64,
    pub soc_start: f64,
    pub soc_top: f64,
    pub soc_end: f64,
    pub cap: f64,
    pub li_inv: f64,
    pub cath_frac: f64,
    pub r_mult: f64,
    pub sei: f64,
    pub plated: f64,
    pub temp: f64,
    pub t_charge_s: f64,
    pub t_discharge_s: f64,
    pub charge_mah: f64,
    pub discharge_mah: f64,
    pub energy_in_mwh: f64,
    pub energy_out_mwh: f64,
    pub efc: f64,
    pub t10_80_min: Option<f64>,
}

/// Wynik symulacji.
pub struct SimResult {
    pub cath: &'static str,
    pub an: &'static str,
    pub el: &'static str,
    pub loading: f64,
    pub np: f64,
    pub c_ch: f64,
    pub c_dis: f64,
    pub t_amb: f64,
    pub wh_kg: f64,
    pub wh_kg_pack: f64,
    pub wh_l: f64,
    pub cost_kwh: f64,
    pub mah_g: f64,
    pub v_avg: f64,
    pub cycles: u64,
    pub eol: Eol,
    pub runaway: bool,
    pub explosion: bool,
    pub short: bool,
    /// maksymalna temperatura podczas symulacji [°C]
    pub t_max: f64,
    /// czas ladowania do 80% SOC [min] (0 gdy nie osiagnieto)
    pub t80_min: f64,
    pub t80_set: bool,
    /// sprawnosc energetyczna (E_rozladowania / E_ladowania)
    pub eta: f64,
    pub sei: f64,
    pub plated: f64,
    pub r_mult: f64,
    pub hours: f64,
    /// ulamek pojemnosci odprowadzony w oknie napiec przy tym C-rate (ostatni cykl)
    pub delivered_frac: f64,
    /// to samo dla pierwszego cyklu (sprawnosc szybkosciowa swiezego ogniwa)
    pub delivered_frac_1: f64,
    /// energia rzeczywiscie oddana w pierwszym/ostatnim cyklu [Wh/kg]
    pub delivered_wh_kg_1: f64,
    pub delivered_wh_kg_last: f64,
    /// calkowity przeplyw ladunku odniesiony do poczatkowego Ah
    pub efc: f64,
    pub charge_mah: f64,
    pub discharge_mah: f64,
    pub energy_in_mwh: f64,
    pub energy_out_mwh: f64,
    pub t10_80_min_1: Option<f64>,
    pub t10_80_max_min: Option<f64>,
    pub qualifying_cycles: u64,
    /// model nie ma chemii przeladowania poza 100% SOC
    pub abuse_model_complete: bool,
    pub trace: Vec<TracePoint>,
}

struct SimState {
    cap: f64,
    li_inv: f64,
    cath_frac: f64,
    r_mult: f64,
    sei: f64,
    plated: f64,
    dend: f64,
    t: f64,
    cycle: u64,
    eol: Option<Eol>,
    runaway: bool,
    explosion: bool,
    short: bool,
    t_max: f64,
    t80: Option<f64>,
    eta_sum: f64,
    eta_n: u64,
    hours: f64,
    delivered_frac: f64,
    delivered_frac_1: Option<f64>,
    li_melt_j: f64,
    li_melt_done: bool,
    cath_exo_j: f64,
    cath_exo_done: bool,
    trace: Vec<TracePoint>,
    sei_elapsed_h: f64,
    charge_mah: f64,
    discharge_mah: f64,
    energy_in_mj: f64,
    energy_out_mj: f64,
    abuse_model_complete: bool,
}

/// Silnik symulacji (zamkniete nad stanem -- jak closures w Pythonie).
struct Engine<'a> {
    cell: &'a Cell,
    cp: &'a CellParams,
    sp: &'a SimParams,
    c: Cathode,
    a: Anode,
    e: Electrolyte,
    is_solid: bool,
    cap0: f64,
    v_max: f64,
    v_min: f64,
    r0: f64,
    alpha: f64,
    np: f64,
    i0f: f64,
    t_amb: f64,
    st: SimState,
}

impl<'a> Engine<'a> {
    fn ocv(&self, s: f64) -> f64 {
        interp(self.c.vcurve, s) - interp(self.a.vcurve, (s / self.np).min(1.0))
    }

    fn eta_cat(&self, i_ma: f64, s: f64, t: f64) -> f64 {
        let i0 = self.c.i0
            * ((s * (1.0 - s)).max(1e-6).sqrt() + self.i0f)
            * arrhenius(t, 25.0, self.sp.ea_act);
        let x = i_ma.abs() / (2.0 * i0);
        (x.asinh() * RG * (t + 273.15) / (self.alpha * F)).copysign(i_ma)
    }

    fn eta_an(&self, i_ma: f64, s: f64, t: f64) -> f64 {
        let s_an = (s / self.np).min(1.0);
        let i0 = self.a.i0
            * ((s_an * (1.0 - s_an)).max(1e-6).sqrt() + self.i0f)
            * self.cp.k_conc
            * arrhenius(t, 25.0, self.sp.ea_act);
        let x = i_ma.abs() / (2.0 * i0);
        (x.asinh() * RG * (t + 273.15) / (self.alpha * F)).copysign(i_ma)
    }

    fn r_int(&self, t: f64) -> f64 {
        let r = self.r0 * self.st.r_mult * (1.0 + 0.004 * self.st.sei + 0.5 * self.st.plated);
        r / arrhenius(t, 25.0, self.sp.ea_ion) // przewodnictwo jonowe spada w zimnie
    }

    /// Cieplo reakcji ubocznych [mW/cm^2] w temperaturze t.
    fn side_heat(&self, t: f64) -> f64 {
        let mut q = 0.0;
        let m_sei_g = self.st.sei * 1e-7 * 2.0; // nm -> cm, 2 g/cm^3
        q += m_sei_g * self.sp.k_exo_sei * arrhenius(t, self.sp.tref_exo_sei, self.sp.ea_exo_sei);
        // reakcja litowanej anody (z SEI) z elektrolitem -- narasta lawinowo od ~150°C
        if self.a.k_an > 0.0 {
            q += self.cell.m_an / 1000.0
                * 0.9
                * self.a.k_an
                * arrhenius(t, self.sp.tref_an_rxn, self.sp.ea_an_rxn)
                * if self.is_solid { 0.3 } else { 1.0 };
        }
        q += self.cell.m_el / 1000.0
            * self.sp.k_exo_elec
            * arrhenius(t, self.sp.tref_exo_elec, self.sp.ea_exo_elec)
            * if self.e.flammable { 1.0 } else { 0.3 };
        if self.e.flammable && t >= self.e.t_decomp {
            q += self.cell.m_el / 1000.0 * self.sp.k_comb; // zaplon / spalanie
        }
        q += self.cell.m_cat / 1000.0
            * self.sp.k_exo_cath
            * arrhenius(t, self.sp.tref_exo_cath, self.sp.ea_exo_cath)
            * if self.c.t_stable < 300.0 { 1.0 } else { 0.3 };
        q
    }

    fn check_safety(&mut self) {
        let t = self.st.t;
        if t > self.st.t_max {
            self.st.t_max = t;
        }
        if self.cell.an.name == "LIMETAL" && t >= self.a.t_stable && !self.st.li_melt_done {
            // stopienie litu (180°C) -> egzotermia (energia skonczona)
            self.st.li_melt_done = true;
            self.st.li_melt_j = self.cell.m_an / 1000.0
                * 0.9
                * self.a.dh
                * if self.is_solid { 0.3 } else { 1.0 }
                * 1000.0; // mJ/cm^2
        }
        if t >= self.c.t_stable && !self.st.cath_exo_done {
            // rozklad katody (uwolnienie tlenu / stopienie siarki) -> egzotermia
            self.st.cath_exo_done = true;
            self.st.cath_exo_j = self.cell.m_cat / 1000.0
                * 0.9
                * self.c.dh_cath
                * if self.is_solid { 0.5 } else { 1.0 }
                * 1000.0; // mJ/cm^2
        }
        if t >= self.cell.sep_melt && !self.st.short {
            self.st.short = true;
            if self.e.flammable {
                self.st.explosion = true;
            }
        }
        if self.e.flammable && t >= self.e.t_decomp {
            self.st.explosion = true;
        }
        if t >= self.sp.t_runaway || self.st.explosion {
            self.st.runaway = true;
        }
    }

    /// Jeden krok czasowy. Zwraca (nowe SOC, e_in [mJ], e_out [mJ]).
    fn step(&mut self, dt: f64, mut i_ma: f64, s: f64) -> (f64, f64, f64) {
        let t = self.st.t;
        if t >= self.cell.t_shutdown {
            i_ma = 0.0; // separator PP: zamkniecie porow -> brak przewodnictwa jonowego
        }
        let r = self.r_int(t);
        let v_ocv = self.ocv(s);
        let eta = self.eta_cat(i_ma, s, t) + self.eta_an(i_ma, s, t);
        let v = v_ocv + i_ma * r / 1000.0 + eta; // i_ma > 0: ladowanie (V = OCV + IR + eta)
        let s_new = s + i_ma * dt / 3600.0 / self.st.cap;
        // ladowanie litu na anodzie podczas szybkiego ladowania
        if i_ma > 0.0 && self.a.plat > 0.0 {
            let c_rate = i_ma / self.st.cap;
            let s_an_surf = (s / self.np * (1.0 + 0.02 * c_rate)).min(1.0);
            let phi_an = interp(self.a.vcurve, s_an_surf) - self.eta_an(i_ma, s, t).abs();
            if phi_an < 0.0 {
                let low_t = 1.0 + ((283.15 - (t + 273.15)).max(0.0) / 283.15) * 4.0;
                let f_plat = self.a.plat
                    * (self.sp.plat_gain * (-phi_an / self.sp.plat_k).exp()).min(0.5)
                    * low_t;
                let plated_mah = f_plat * i_ma * dt / 3600.0;
                let dead = 0.55 * plated_mah;
                self.st.li_inv -= dead / self.cap0;
                self.st.plated += plated_mah;
                self.st.dend += dead * self.a.dend * if self.is_solid { 0.5 } else { 1.0 };
            }
        }
        // cieplo: I^2R + aktywacja + reakcje uboczne + egzotermie (energia skonczona)
        let mut q_mw = i_ma.abs() * (i_ma.abs() * r / 1000.0 + eta.abs()) + self.side_heat(t);
        if self.st.li_melt_j > 0.0 {
            let q_add = self.st.li_melt_j / self.sp.tau_an;
            q_mw += q_add;
            self.st.li_melt_j = (self.st.li_melt_j - q_add * dt).max(0.0);
        }
        if self.st.cath_exo_j > 0.0 {
            let q_add = self.st.cath_exo_j / self.sp.tau_cath;
            q_mw += q_add;
            self.st.cath_exo_j = (self.st.cath_exo_j - q_add * dt).max(0.0);
        }
        q_mw -= self.cell.ha * (t - self.t_amb);
        self.st.t += q_mw * dt / self.cell.c_th;
        let e_in = (i_ma * v).max(0.0) * dt;
        let e_out = (-i_ma * v).max(0.0) * dt;
        self.st.charge_mah += i_ma.max(0.0) * dt / 3600.0;
        self.st.discharge_mah += (-i_ma).max(0.0) * dt / 3600.0;
        self.st.energy_in_mj += e_in;
        self.st.energy_out_mj += e_out;
        self.check_safety();
        (s_new, e_in, e_out)
    }

    fn finish(self, c_ch: f64, c_dis: f64, t_amb: f64) -> SimResult {
        let first = self.st.trace.first();
        let last = self.st.trace.last();
        let delivered_wh_kg_1 = first.map_or(0.0, |p| p.energy_out_mwh * 1000.0 / self.cell.m_tot);
        let delivered_wh_kg_last =
            last.map_or(0.0, |p| p.energy_out_mwh * 1000.0 / self.cell.m_tot);
        let t10_80_min_1 = first.and_then(|p| p.t10_80_min);
        let t10_80_max_min = self
            .st
            .trace
            .iter()
            .filter_map(|p| p.t10_80_min)
            .reduce(f64::max);
        let qualifying_cycles = self
            .st
            .trace
            .iter()
            .filter(|p| {
                p.t10_80_min.is_some_and(|t| t <= 30.0)
                    && p.discharge_mah / p.cap >= self.sp.min_delivered - 1e-9
            })
            .count() as u64;
        SimResult {
            cath: self.cell.cath.name,
            an: self.cell.an.name,
            el: self.cell.el.name,
            loading: self.cell.loading_cat,
            np: self.cell.np,
            c_ch,
            c_dis,
            t_amb,
            wh_kg: self.cell.wh_kg,
            wh_kg_pack: self.cell.wh_kg_pack,
            wh_l: self.cell.wh_l,
            cost_kwh: self.cell.cost_kwh,
            mah_g: self.cell.mah_g,
            v_avg: self.cell.v_avg,
            cycles: self.st.cycle,
            eol: self.st.eol.unwrap_or(Eol::Survived(0)),
            runaway: self.st.runaway,
            explosion: self.st.explosion,
            short: self.st.short,
            t_max: self.st.t_max,
            t80_min: self.st.t80.map(|v| v / 60.0).unwrap_or(0.0),
            t80_set: self.st.t80.is_some(),
            eta: if self.st.energy_in_mj > 0.0 {
                self.st.energy_out_mj / self.st.energy_in_mj
            } else {
                0.0
            },
            sei: self.st.sei,
            plated: self.st.plated,
            r_mult: self.st.r_mult,
            hours: self.st.hours,
            delivered_frac: self.st.delivered_frac,
            delivered_frac_1: self.st.delivered_frac_1.unwrap_or(0.0),
            delivered_wh_kg_1,
            delivered_wh_kg_last,
            efc: self.st.discharge_mah / self.cap0,
            charge_mah: self.st.charge_mah,
            discharge_mah: self.st.discharge_mah,
            energy_in_mwh: self.st.energy_in_mj / 3600.0,
            energy_out_mwh: self.st.energy_out_mj / 3600.0,
            t10_80_min_1,
            t10_80_max_min,
            qualifying_cycles,
            abuse_model_complete: self.st.abuse_model_complete,
            trace: self.st.trace,
        }
    }
}

/// Symuluje cykle CC (ladowanie `c_ch`, rozladowanie `c_dis`) az do EOL.
/// Gdy `abuse` = Some, wykonuje protokol testu abusow (piec + przeladowanie).
#[allow(clippy::too_many_arguments)]
pub fn simulate(
    cell: &Cell,
    cp: &CellParams,
    sp: &SimParams,
    c_ch: f64,
    c_dis: f64,
    t_amb: f64,
    max_cycles: u64,
    abuse: Option<Abuse>,
) -> SimResult {
    assert!(
        c_ch.is_finite() && c_ch > 0.0 && c_dis.is_finite() && c_dis > 0.0,
        "C-rate must be finite and positive"
    );
    assert!(
        t_amb.is_finite() && t_amb > -273.15 && t_amb < cell.t_shutdown,
        "cycling temperature must be finite, above absolute zero and below shutdown"
    );
    assert!(max_cycles > 0, "max_cycles must be positive");
    if let Some(ab) = abuse {
        assert!(
            ab.t_oven.is_finite()
                && ab.t_oven > -273.15
                && ab.overcharge.is_finite()
                && ab.overcharge >= 0.0
                && ab.t_max_h.is_finite()
                && ab.t_max_h > 0.0,
            "invalid abuse protocol"
        );
    }
    let mut t_amb = t_amb;
    if let Some(ab) = abuse {
        t_amb = ab.t_oven;
    }
    let mut eng = Engine {
        cell,
        cp,
        sp,
        c: cell.cath,
        a: cell.an,
        e: cell.el,
        is_solid: cell.el.name == "SOLID",
        cap0: cell.cap0,
        v_max: cell.v_max,
        v_min: cell.v_min,
        r0: cell.r0,
        alpha: cp.alpha,
        np: cell.np,
        i0f: cp.i0_floor,
        t_amb,
        st: SimState {
            cap: cell.cap0,
            li_inv: 1.0,
            cath_frac: 1.0,
            r_mult: 1.0,
            sei: 5.0,
            plated: 0.0,
            dend: 0.0,
            t: t_amb,
            cycle: 0,
            eol: None,
            runaway: false,
            explosion: false,
            short: false,
            t_max: t_amb,
            t80: None,
            eta_sum: 0.0,
            eta_n: 0,
            hours: 0.0,
            delivered_frac: 0.0,
            delivered_frac_1: None,
            li_melt_j: 0.0,
            li_melt_done: false,
            cath_exo_j: 0.0,
            cath_exo_done: false,
            trace: Vec::new(),
            sei_elapsed_h: 0.0,
            charge_mah: 0.0,
            discharge_mah: 0.0,
            energy_in_mj: 0.0,
            energy_out_mj: 0.0,
            abuse_model_complete: false,
        },
    };

    // ------------------------------------------------------------- protokol abusow
    if let Some(ab) = abuse {
        // Kontynuacja poprawki upstream: dwa etapy pozostaja diagnostyka.
        // Nie udajemy fizyki poza 100% SOC: overcharge oznacza niepelne pokrycie modelu.
        eng.st.abuse_model_complete = ab.overcharge == 0.0;
        // AUDYT 2026-11-01: stary test laczyl piec 150C z przeładowaniem i startowal
        // od razu w 150C przy SOC=0 — shutdown (PP 130C) zerowal prad od t=0, a piec
        // dominowal bilans cieplny, wiec wynik byl identyczny dla 0C/1C/10C.
        // Dwa uproszczone etapy diagnostyczne; to NIE jest protokol normatywny:
        //  1) soak w piecu (bez pradu): ogniwo startuje w 25C, PELNE SOC;
        //  2) przeładowanie przy 25C otoczenia, pelne SOC.
        eng.st.t = 25.0;
        eng.st.t_max = 25.0;
        let dt = 2.0;
        let t_end = ab.t_max_h * 3600.0;
        let mut t_all = 0.0;
        // etap 1: piec (thermal abuse), bez pradu
        eng.t_amb = ab.t_oven;
        let mut t = 0.0;
        while t < t_end && !eng.st.runaway && !eng.st.short {
            let _ = eng.step(dt, 0.0, 1.0);
            t += dt;
        }
        t_all += t;
        // etap 2: przeładowanie w temperaturze pokojowej
        eng.t_amb = 25.0;
        eng.st.t = 25.0;
        let i_ma = ab.overcharge * eng.cap0;
        let mut t = 0.0;
        let mut s: f64 = 1.0;
        while t < t_end && !eng.st.runaway && !eng.st.short {
            let (sn, _, _) = eng.step(dt, i_ma, s.min(1.0));
            s = sn;
            t += dt;
        }
        t_all += t;
        eng.st.hours = t_all / 3600.0;
        return eng.finish(c_ch, c_dis, t_amb);
    }

    // SOC jest stanem ciaglym; odciecie rozladowania nie rozladowuje ogniwa do zera.
    let mut s = 0.0f64;
    // ------------------------------------------------------------- cykle
    while eng.st.cycle < max_cycles {
        eng.st.cycle += 1;
        let plated_before = eng.st.plated;
        let soc_start = s;
        let charge_before = eng.st.charge_mah;
        let discharge_before = eng.st.discharge_mah;
        let mut t10 = if s <= 0.1 { None } else { Some(f64::NAN) };
        let mut t80 = None;
        // ---- ladowanie CC do V_max
        let dt = sp.dt_max.min((3600.0 / (c_ch * 150.0)).max(sp.dt_min));
        let i_ma = c_ch * eng.cap0;
        let mut t_ch = 0.0;
        let mut e_in = 0.0;
        let mut e_out = 0.0;
        while s < 1.0 - 1e-12 {
            if eng.st.t >= cell.t_shutdown || t_ch >= 7200.0 / c_ch {
                eng.st.eol = Some(Eol::ProtocolStopped);
                break;
            }
            let v = eng.ocv(s)
                + i_ma * eng.r_int(eng.st.t) / 1000.0
                + eng.eta_cat(i_ma, s, eng.st.t).abs()
                + eng.eta_an(i_ma, s, eng.st.t).abs();
            if v >= eng.v_max {
                break;
            }
            let step_dt = dt.min((1.0 - s) * eng.st.cap * 3600.0 / i_ma);
            let s_prev = s;
            let (sn, ei, eo) = eng.step(step_dt, i_ma, s);
            s = sn;
            e_in += ei;
            e_out += eo;
            if t10.is_none() && s >= 0.1 {
                t10 = Some(t_ch + step_dt * (0.1 - s_prev) / (s - s_prev));
            }
            if t80.is_none() && s >= 0.8 {
                t80 = Some(t_ch + step_dt * (0.8 - s_prev) / (s - s_prev));
            }
            t_ch += step_dt;
            if eng.st.runaway || eng.st.short {
                break;
            }
        }
        let s_top = s;
        if eng.st.cycle == 1 {
            eng.st.t80 = t80;
        }
        let t10_80_min = t10.zip(t80).and_then(|(a, b)| {
            if a.is_finite() {
                Some((b - a) / 60.0)
            } else {
                None
            }
        });
        // ---- rozladowanie CC do V_min
        let dt = sp.dt_max.min((3600.0 / (c_dis * 150.0)).max(sp.dt_min));
        let i_ma = -c_dis * eng.cap0;
        let mut t_dis = 0.0;
        while s > 1e-12 && !eng.st.runaway && !eng.st.short && eng.st.eol.is_none() {
            if eng.st.t >= cell.t_shutdown || t_dis >= 7200.0 / c_dis {
                eng.st.eol = Some(Eol::ProtocolStopped);
                break;
            }
            let v = eng.ocv(s)
                + i_ma * eng.r_int(eng.st.t) / 1000.0
                + eng.eta_cat(i_ma, s, eng.st.t)
                + eng.eta_an(i_ma, s, eng.st.t);
            if v <= eng.v_min {
                break;
            }
            let step_dt = dt.min(s * eng.st.cap * 3600.0 / -i_ma);
            let (sn, ei, eo) = eng.step(step_dt, i_ma, s);
            s = sn;
            e_in += ei;
            e_out += eo;
            t_dis += step_dt;
            if eng.st.runaway || eng.st.short {
                break;
            }
        }
        s = s.clamp(0.0, 1.0);
        // ulamek pojemnosci odprowadzony w oknie napiec przy danym C-rate
        eng.st.delivered_frac = s_top - s;
        if eng.st.delivered_frac_1.is_none() {
            eng.st.delivered_frac_1 = Some(eng.st.delivered_frac);
        }
        eng.st.hours += (t_ch + t_dis) / 3600.0;
        if e_in > 0.0 {
            eng.st.eta_sum += e_out / e_in;
            eng.st.eta_n += 1;
        }
        eng.st.trace.push(TracePoint {
            cycle: eng.st.cycle,
            soc_start,
            soc_top: s_top,
            soc_end: s,
            cap: eng.st.cap,
            li_inv: eng.st.li_inv,
            cath_frac: eng.st.cath_frac,
            r_mult: eng.st.r_mult,
            sei: eng.st.sei,
            plated: eng.st.plated,
            temp: eng.st.t,
            t_charge_s: t_ch,
            t_discharge_s: t_dis,
            charge_mah: eng.st.charge_mah - charge_before,
            discharge_mah: eng.st.discharge_mah - discharge_before,
            energy_in_mwh: e_in / 3600.0,
            energy_out_mwh: e_out / 3600.0,
            efc: eng.st.discharge_mah / eng.cap0,
            t10_80_min,
        });
        // ---- degradacja na koniec cyklu
        let t_avg = eng.st.t.clamp(-20.0, 60.0);
        let f_t = arrhenius(t_avg, 25.0, sp.ea_fade);
        let f_v = (eng.v_max / 3.8).powi(4);
        let f_c = 1.0 + 0.35 * (c_ch - 1.0).max(0.0) + 0.15 * (c_ch - 1.0).max(0.0).powi(2);
        let mut fade_frac = sp.fade_base * eng.c.fade * f_v * f_t * f_c;
        // stres oksydacyjny elektrolitu (katody wysokonapieciowe poza oknem elektrolitu)
        let ox = sp.ox_k * (eng.v_max - eng.e.window).max(0.0).powi(2) * f_t;
        fade_frac += ox;
        eng.st.cath_frac *= 1.0 - fade_frac;
        // SEI (wzrost paraboliczny) + ubytek inwentarza
        let h_cyc = (t_ch + t_dis) / 3600.0;
        let f_t_sei = arrhenius(t_avg, 25.0, sp.ea_sei);
        let d_sei = sp.k_sei
            * eng.a.sei
            * eng.e.sei
            * sqrt_time_increment(eng.st.sei_elapsed_h, h_cyc)
            * f_t_sei
            * (1.0 + 0.25 * (c_ch - 1.0).max(0.0));
        eng.st.sei_elapsed_h += h_cyc;
        eng.st.sei += d_sei;
        eng.st.li_inv -= d_sei * sp.li_per_nm;
        // shuttle / samo-rozladowanie katody (Li-S)
        eng.st.li_inv -= eng.c.sd * h_cyc / 2.0;
        // dead Li (Li metal, Si) + dendryty
        if eng.a.dead_li > 0.0 {
            let charged_frac = (eng.st.charge_mah - charge_before) / eng.cap0;
            let dead = eng.a.dead_li * (0.5 + 0.5 * c_ch) * charged_frac;
            eng.st.li_inv -= dead;
            eng.st.dend += dead * eng.a.dend * if eng.is_solid { 0.5 } else { 1.0 };
        }
        // opor rosnie
        eng.st.r_mult +=
            0.0004 * d_sei + 0.5 * (eng.st.plated - plated_before) + 0.4 * fade_frac + 2.0 * ox;
        // pojemnosc rzeczywista (inwentarz Li + struktura katody); EOL = 80% pojemnosci poczatkowej
        eng.st.cap = (eng.cap0 * eng.st.li_inv).min(eng.cap0 * eng.st.cath_frac);
        // dendryty -> zwarcie
        if eng.st.dend > 1.0 && !eng.st.short {
            eng.st.short = true;
            if eng.e.flammable {
                eng.st.explosion = true;
            }
        }
        // EOL
        if eng.st.runaway {
            eng.st.eol = Some(Eol::Runaway);
            break;
        }
        if eng.st.short {
            eng.st.eol = Some(Eol::Short);
            break;
        }
        if eng.st.eol.is_some() {
            break;
        }
        if eng.st.delivered_frac < sp.min_delivered - 1e-9 {
            eng.st.eol = Some(Eol::RateLimited);
            break;
        }
        if eng.st.cap < 0.8 * eng.cap0 {
            eng.st.eol = Some(Eol::Fade80);
            break;
        }
        // lekkie chlodzenie miedzy cyklami
        eng.st.t += (t_amb - eng.st.t) * 0.02;
    }

    if eng.st.eol.is_none() {
        eng.st.eol = Some(Eol::Survived(max_cycles));
    }
    eng.finish(c_ch, c_dis, t_amb)
}

fn sqrt_time_increment(elapsed: f64, duration: f64) -> f64 {
    (elapsed + duration).sqrt() - elapsed.sqrt()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::materials::{anode, cathode, electrolyte};

    fn fixture(ca: &str, an: &str, el: &str, ld: f64, np: f64) -> (Cell, CellParams, SimParams) {
        let cp = CellParams::default();
        let c = Cell::new(
            cathode(ca).unwrap(),
            anode(an).unwrap(),
            electrolyte(el).unwrap(),
            ld,
            np,
            &cp,
        );
        (c, cp, SimParams::default())
    }

    #[test]
    fn residual_soc_is_preserved_and_charge_balances() {
        let (c, cp, mut sp) = fixture("DRX", "SIC", "GEL", 40.0, 1.02);
        sp.min_delivered = 0.0; // follow partial cycles for this continuity test only
        let r = simulate(&c, &cp, &sp, 2.0, 1.0, -10.0, 3, None);
        assert_eq!(r.trace.len(), 3);
        assert!(r.trace[0].soc_end > 0.1);
        for pair in r.trace.windows(2) {
            assert!((pair[1].soc_start - pair[0].soc_end).abs() < 1e-12);
        }
        for p in &r.trace {
            assert!((p.charge_mah - p.cap * (p.soc_top - p.soc_start)).abs() < 1e-10);
            assert!((p.discharge_mah - p.cap * (p.soc_top - p.soc_end)).abs() < 1e-10);
        }
    }

    #[test]
    fn soc_bounds_hold_and_current_is_referenced_to_initial_capacity() {
        let (c, cp, mut sp) = fixture("NMC811", "SIC", "LP57", 20.0, 1.1);
        sp.min_delivered = 0.0;
        sp.fade_base = 0.01;
        let r = simulate(&c, &cp, &sp, 2.3, 1.7, 25.0, 3, None);
        assert_eq!(r.trace.len(), 3);
        assert!(r.trace[2].cap < r.trace[0].cap);
        for p in &r.trace {
            assert!((0.0..=1.0).contains(&p.soc_end));
            assert!((0.0..=1.0 + 1e-12).contains(&p.soc_top));
            assert!((p.charge_mah / (p.t_charge_s / 3600.0) - 2.3 * c.cap0).abs() < 1e-9);
            assert!((p.discharge_mah / (p.t_discharge_s / 3600.0) - 1.7 * c.cap0).abs() < 1e-9);
        }
    }

    #[test]
    fn energy_and_efc_are_integrated_from_actual_discharge() {
        let (c, cp, sp) = fixture("NMC811", "SIC", "GEL", 30.0, 1.1);
        let r = simulate(&c, &cp, &sp, 2.0, 1.0, 25.0, 3, None);
        let q: f64 = r.trace.iter().map(|p| p.discharge_mah).sum();
        let e: f64 = r.trace.iter().map(|p| p.energy_out_mwh).sum();
        assert!((q / c.cap0 - r.efc).abs() < 1e-10);
        assert!((e - r.energy_out_mwh).abs() < 1e-10);
        assert!(r.delivered_wh_kg_1 > 0.0 && r.delivered_wh_kg_1 < c.wh_kg);
        let efficiency = r.energy_out_mwh / r.energy_in_mwh;
        assert!((r.eta - efficiency).abs() < 1e-12);
    }

    #[test]
    fn cold_partial_cycle_does_not_qualify_as_fast_charging() {
        let (c, cp, sp) = fixture("DRX", "SIC", "GEL", 40.0, 1.02);
        let r = simulate(&c, &cp, &sp, 2.0, 1.0, -10.0, 3000, None);
        assert_eq!(r.eol, Eol::RateLimited);
        assert_eq!(r.cycles, 1);
        assert_eq!(r.qualifying_cycles, 0);
        assert!(r.t10_80_min_1.is_none());
        assert!(!r.t80_set);
    }

    #[test]
    fn sqrt_sei_growth_is_invariant_to_time_subdivision() {
        let coarse = sqrt_time_increment(0.0, 100.0);
        let fine: f64 = (0..100).map(|n| sqrt_time_increment(n as f64, 1.0)).sum();
        assert!((coarse - fine).abs() < 1e-12);
        assert!(sqrt_time_increment(99.0, 1.0) < sqrt_time_increment(0.0, 1.0));
    }

    #[test]
    fn separator_shutdown_stops_cycling_instead_of_spinning() {
        let (mut c, cp, sp) = fixture("NMC811", "SIC", "GEL", 30.0, 1.1);
        c.t_shutdown = 25.00001;
        let r = simulate(&c, &cp, &sp, 2.0, 1.0, 25.0, 3, None);
        assert_eq!(r.eol, Eol::ProtocolStopped);
        assert!(r.hours < 1.0);
    }

    #[test]
    fn overcharge_is_explicitly_marked_incomplete() {
        let (c, cp, sp) = fixture("NMC811", "SIC", "GEL", 30.0, 1.1);
        let r = simulate(
            &c,
            &cp,
            &sp,
            1.0,
            1.0,
            25.0,
            1,
            Some(Abuse {
                t_oven: 150.0,
                overcharge: 1.0,
                t_max_h: 0.01,
            }),
        );
        assert!(!r.abuse_model_complete);
    }

    #[test]
    #[should_panic(expected = "C-rate")]
    fn rejects_zero_current() {
        let (c, cp, sp) = fixture("NMC811", "SIC", "GEL", 30.0, 1.1);
        simulate(&c, &cp, &sp, 0.0, 1.0, 25.0, 1, None);
    }
}
