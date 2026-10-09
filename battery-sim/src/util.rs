//! Stale fizyczne i funkcje pomocnicze.

/// Stala Faradaya [C/mol]
pub const F: f64 = 96485.33212;
/// Stala gazowa [J/mol/K]
pub const RG: f64 = 8.314462618;

/// Czynnik Arrheniusa: przyspieszenie reakcji w temperaturze `t_c` wzgledem `tref_c`.
/// Obie temperatury w stopniach Celsjusza, `ea` w J/mol.
pub fn arrhenius(t_c: f64, tref_c: f64, ea: f64) -> f64 {
    let t = t_c + 273.15;
    let tr = tref_c + 273.15;
    (-ea / RG * (1.0 / t - 1.0 / tr)).exp()
}

/// Interpolacja liniowa po krzywej `[(x, v), ...]` z zaciskiem na koncach.
pub fn interp(curve: &[(f64, f64)], x: f64) -> f64 {
    if x <= curve[0].0 {
        return curve[0].1;
    }
    if x >= curve[curve.len() - 1].0 {
        return curve[curve.len() - 1].1;
    }
    for i in 0..curve.len() - 1 {
        let (x0, v0) = curve[i];
        let (x1, v1) = curve[i + 1];
        if x0 <= x && x <= x1 {
            return v0 + (v1 - v0) * (x - x0) / (x1 - x0);
        }
    }
    curve[curve.len() - 1].1
}
