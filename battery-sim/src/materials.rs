//! Baza materialow: katody, anody, elektrolity.
//!
//! Ogniwo modelujemy jako trojke (katoda | elektrolit | anoda) -- kazdy
//! komponent ma wlasne parametry elektrochemiczne, termiczne i degradacyjne.

/// Krzywa OCV: `[(SOC, V vs Li/Li+)]`.
pub type Curve = &'static [(f64, f64)];

/// Material katodowy.
#[derive(Clone, Copy)]
pub struct Cathode {
    pub name: &'static str,
    /// praktyczna pojemnosc wlasciwa [mAh/g]
    pub cap_mah_g: f64,
    /// SOC katody = stopien delitiacji (1 = naladowana)
    pub vcurve: Curve,
    /// napiecie odciecia ladowania vs Li [V]
    pub vmax: f64,
    /// gestosc [g/cm^3]
    pub dens: f64,
    /// udzial materialu aktywnego w elektrodzie
    pub act: f64,
    /// mnoznik tempa degradacji cyklicznej
    pub fade: f64,
    /// temperatura rozkladu katody (uwolnienie tlenu) [°C]
    pub t_stable: f64,
    /// gestosc pradu wymiany [mA/cm^2]
    pub i0: f64,
    /// shuttle / samo-rozladowanie [ulamek/cykl przy 1C]
    pub sd: f64,
    /// cieplo rozkladu katody [J/g]
    pub dh_cath: f64,
}

/// Material anodowy.
#[derive(Clone, Copy)]
pub struct Anode {
    pub name: &'static str,
    /// praktyczna pojemnosc wlasciwa [mAh/g]
    pub cap_mah_g: f64,
    /// SOC anody = stopien litacji (1 = naladowana)
    pub vcurve: Curve,
    /// gestosc [g/cm^3]
    pub dens: f64,
    /// udzial materialu aktywnego w elektrodzie
    pub act: f64,
    /// rozszerzalmosc wloknista przy litacji (ulamkowo)
    pub expansion: f64,
    /// podatnosc na ladowanie litowe (plating) przy szybkim ladowaniu
    pub plat: f64,
    /// tempo tworzenia SEI (wzgledne)
    pub sei: f64,
    /// tempo wzrostu dendrytow na jednostke martwego Li
    pub dend: f64,
    /// temperatura rozkladu SEI / topnienia anody [°C]
    pub t_stable: f64,
    /// mnoznik tempa degradacji cyklicznej (zarezerwowane — model liczy fade katody)
    #[allow(dead_code)]
    pub fade: f64,
    /// gestosc pradu wymiany [mA/cm^2]
    pub i0: f64,
    /// stala reakcji litowanej anody z elektrolitem [mW/g] (Arrhenius, ref 150°C)
    pub k_an: f64,
    /// cieplo topienia/reakcji (dla Li metalu) [J/g]
    pub dh: f64,
    /// ulamek Li zamienianego w martwy na cykl przy 1C (Li metal, Si)
    pub dead_li: f64,
}

/// Elektrolit (ciekly / ciekly jonowy / staly).
#[derive(Clone, Copy)]
pub struct Electrolyte {
    pub name: &'static str,
    /// przewodnictwo jonowe [mS/cm]
    pub kappa_ms_cm: f64,
    /// temperatura rozkladu / samozaplonu [°C]
    pub t_decomp: f64,
    /// czy elektrolit jest palny (wybuch/pozar)
    pub flammable: bool,
    /// okno elektrochemiczne (stabilnosc napieciowa) [V]
    pub window: f64,
    /// mnoznik tempa tworzenia SEI
    pub sei: f64,
    /// opor interfazy [Ohm*cm^2]
    pub r_if: f64,
}

pub const CATHODES: &[Cathode] = &[
    Cathode {
        name: "NMC811",
        cap_mah_g: 200.0,
        vcurve: &[
            (0.0, 3.55),
            (0.3, 3.70),
            (0.6, 3.85),
            (0.9, 4.05),
            (1.0, 4.20),
        ],
        vmax: 4.20,
        dens: 4.6,
        act: 0.96,
        fade: 1.0,
        t_stable: 280.0,
        i0: 2.0,
        sd: 0.0002,
        dh_cath: 600.0,
    },
    Cathode {
        name: "NMC532",
        cap_mah_g: 160.0,
        vcurve: &[(0.0, 3.50), (0.5, 3.70), (1.0, 4.20)],
        vmax: 4.20,
        dens: 4.5,
        act: 0.96,
        fade: 0.7,
        t_stable: 300.0,
        i0: 2.0,
        sd: 0.0002,
        dh_cath: 600.0,
    },
    Cathode {
        name: "NCA",
        cap_mah_g: 190.0,
        vcurve: &[(0.0, 3.55), (0.5, 3.75), (1.0, 4.20)],
        vmax: 4.20,
        dens: 4.7,
        act: 0.96,
        fade: 0.8,
        t_stable: 290.0,
        i0: 2.0,
        sd: 0.0002,
        dh_cath: 600.0,
    },
    Cathode {
        name: "LFP",
        cap_mah_g: 160.0,
        vcurve: &[(0.0, 3.20), (0.05, 3.45), (0.95, 3.45), (1.0, 3.60)],
        vmax: 3.65,
        dens: 3.6,
        act: 0.95,
        fade: 0.25,
        t_stable: 350.0,
        i0: 2.5,
        sd: 0.0001,
        dh_cath: 150.0,
    },
    Cathode {
        name: "LCO",
        cap_mah_g: 145.0,
        vcurve: &[(0.0, 3.60), (0.5, 3.90), (1.0, 4.20)],
        vmax: 4.20,
        dens: 5.0,
        act: 0.96,
        fade: 1.2,
        t_stable: 250.0,
        i0: 1.5,
        sd: 0.0003,
        dh_cath: 500.0,
    },
    Cathode {
        name: "LMR",
        cap_mah_g: 240.0,
        vcurve: &[(0.0, 3.60), (0.5, 3.80), (1.0, 4.60)],
        vmax: 4.60,
        dens: 4.3,
        act: 0.94,
        fade: 2.5,
        t_stable: 260.0,
        i0: 2.0,
        sd: 0.001,
        dh_cath: 500.0,
    },
    Cathode {
        name: "LNMO",
        cap_mah_g: 120.0,
        vcurve: &[(0.0, 4.00), (0.5, 4.70), (1.0, 4.90)],
        vmax: 4.95,
        dens: 4.8,
        act: 0.95,
        fade: 0.6,
        t_stable: 320.0,
        i0: 1.0,
        sd: 0.0002,
        dh_cath: 200.0,
    },
    Cathode {
        name: "SULFUR",
        cap_mah_g: 800.0,
        vcurve: &[(0.0, 2.40), (0.5, 2.15), (1.0, 1.90)],
        vmax: 2.50,
        dens: 1.8,
        act: 0.90,
        fade: 2.0,
        t_stable: 115.0,
        i0: 1.5,
        sd: 0.008,
        dh_cath: 150.0,
    },
];

pub const ANODES: &[Anode] = &[
    Anode {
        name: "GRAPHITE",
        cap_mah_g: 340.0,
        vcurve: &[
            (0.0, 0.20),
            (0.05, 0.12),
            (0.2, 0.10),
            (0.5, 0.09),
            (0.9, 0.08),
            (1.0, 0.05),
        ],
        dens: 2.2,
        act: 0.96,
        expansion: 0.10,
        plat: 1.0,
        sei: 1.0,
        dend: 0.004,
        t_stable: 120.0,
        fade: 1.0,
        i0: 4.0,
        k_an: 1500.0,
        dh: 400.0,
        dead_li: 0.0,
    },
    Anode {
        name: "LTO",
        cap_mah_g: 155.0,
        vcurve: &[(0.0, 1.60), (0.5, 1.55), (1.0, 1.50)],
        dens: 3.4,
        act: 0.95,
        expansion: 0.00,
        plat: 0.02,
        sei: 0.05,
        dend: 0.0,
        t_stable: 350.0,
        fade: 0.15,
        i0: 3.0,
        k_an: 0.0,
        dh: 30.0,
        dead_li: 0.0,
    },
    Anode {
        name: "SIC",
        cap_mah_g: 900.0,
        vcurve: &[(0.0, 0.60), (0.3, 0.45), (0.7, 0.25), (1.0, 0.08)],
        dens: 2.0,
        act: 0.93,
        expansion: 0.60,
        plat: 0.5,
        sei: 2.0,
        dend: 0.003,
        t_stable: 160.0,
        fade: 1.5,
        i0: 1.5,
        k_an: 800.0,
        dh: 250.0,
        dead_li: 0.0001,
    },
    Anode {
        name: "LIMETAL",
        cap_mah_g: 3860.0,
        vcurve: &[(0.0, 0.05), (1.0, 0.0)],
        dens: 0.53,
        act: 0.99,
        expansion: 1.0,
        plat: 0.0,
        sei: 0.8,
        dend: 0.04,
        t_stable: 180.0,
        fade: 0.5,
        i0: 5.0,
        k_an: 0.0,
        dh: 300.0,
        dead_li: 0.0006,
    },
    Anode {
        name: "HC",
        cap_mah_g: 300.0,
        vcurve: &[(0.0, 0.50), (0.2, 0.30), (0.6, 0.15), (1.0, 0.02)],
        dens: 1.5,
        act: 0.91,
        expansion: 0.10,
        plat: 0.8,
        sei: 1.2,
        dend: 0.004,
        t_stable: 150.0,
        fade: 0.8,
        i0: 3.0,
        k_an: 1200.0,
        dh: 350.0,
        dead_li: 0.0,
    },
];

pub const ELECTROLYTES: &[Electrolyte] = &[
    Electrolyte {
        name: "LP57",
        kappa_ms_cm: 10.0,
        t_decomp: 170.0,
        flammable: true,
        window: 4.4,
        sei: 1.0,
        r_if: 0.5,
    },
    Electrolyte {
        name: "IONIC",
        kappa_ms_cm: 3.0,
        t_decomp: 300.0,
        flammable: false,
        window: 5.0,
        sei: 0.6,
        r_if: 1.5,
    },
    Electrolyte {
        name: "SOLID",
        kappa_ms_cm: 1.0,
        t_decomp: 400.0,
        flammable: false,
        window: 5.0,
        sei: 0.2,
        r_if: 3.0,
    },
];

pub fn cathode(name: &str) -> Option<Cathode> {
    CATHODES.iter().find(|c| c.name == name).copied()
}

pub fn anode(name: &str) -> Option<Anode> {
    ANODES.iter().find(|a| a.name == name).copied()
}

pub fn electrolyte(name: &str) -> Option<Electrolyte> {
    ELECTROLYTES.iter().find(|e| e.name == name).copied()
}
