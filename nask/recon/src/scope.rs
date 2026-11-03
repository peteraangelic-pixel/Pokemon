//! Definicja zakresu — JEDNO źródło prawdy, przepisane z regulaminu NASK edycja 11/2026 §5.
//!
//! Zmiana tej listy bez zmiany regulaminu = zgłoszenie poza konkursem = brak nagrody.

pub struct Scope {
    pub domain: &'static str,
    pub tier: u8,
    pub max_critical_pln: u32,
}

pub const COMPETITION_START: &str = "2026-11-03";
pub const COMPETITION_END: &str = "2026-11-30";
pub const PRIZE_POOL_PLN: u32 = 100_000;
pub const MAX_REQ_PER_SEC: f64 = 5.0; // §6 pkt 2 — bezwzględny sufit

/// Źródła (2026-11-03):
/// - https://hack.cert.pl/programs/nask-pib/nask/editions/1  → sekcja "Zakres systemów"
/// - PDF regulaminu, §5 pkt 1 (pobrany z /terms/download, 11 stron)
/// Zmiana tej listy bez zmiany regulaminu = zgłoszenie poza konkursem.
///
/// UWAGA: `subenum` z repo NASK@arena/a29ca234 generuje hosty typu X.nask.pl.
/// Tylko nieliczne z nich są w zakresie — guard poniżej odrzuca resztę.
pub const IN_SCOPE: &[Scope] = &[
    // Tier 1
    Scope { domain: "nask.pl",                    tier: 1, max_critical_pln: 20_000 },
    Scope { domain: "dyzurnet.pl",                tier: 1, max_critical_pln: 20_000 },
    Scope { domain: "dns.pl",                     tier: 1, max_critical_pln: 20_000 },
    Scope { domain: "oad.nask.pl",                tier: 1, max_critical_pln: 20_000 },
    Scope { domain: "zglos-dezinformacje.nask.pl", tier: 1, max_critical_pln: 20_000 },
    // Tier 2
    Scope { domain: "bezpiecznymiesiac.pl",       tier: 2, max_critical_pln: 10_000 },
    Scope { domain: "secure.edu.pl",              tier: 2, max_critical_pln: 10_000 },
    Scope { domain: "bezpiecznewybory.pl",        tier: 2, max_critical_pln: 10_000 },
    Scope { domain: "116sos.pl",                  tier: 2, max_critical_pln: 10_000 },
    Scope { domain: "pllum.org.pl",               tier: 2, max_critical_pln: 10_000 },
    Scope { domain: "science.nask.pl",            tier: 2, max_critical_pln: 10_000 },
    Scope { domain: "dataannotation.pllum.org.pl", tier: 2, max_critical_pln: 10_000 },
];

/// Stawki z §7 pkt 6 (CVSS 4.0).
pub fn payout(tier: u8, cvss: f32) -> u32 {
    let row: [u32; 4] = if tier == 1 {
        [600, 4_000, 9_000, 20_000]
    } else {
        [300, 2_000, 4_500, 10_000]
    };
    if cvss >= 9.0 { row[3] }
    else if cvss >= 7.0 { row[2] }
    else if cvss >= 4.0 { row[1] }
    else { row[0] }
}

/// Czy host mieści się w zakresie.
///
/// UWAGA: zakres to DOKŁADNIE wypisane domeny. Host typu `gitlab.snkom.nask.pl`
/// jest subdomeną nask.pl, ale nie jest wypisany — traktujemy go jako POZA zakresem.
/// To interpretacja zachowawcza: lepiej stracić okazję niż złożyć zgłoszenie odrzucone
/// proceduralnie (albo, w gorszym scenariuszu, testować system poza zgodą).
pub fn in_scope(host: &str) -> Option<&'static Scope> {
    let h = host.trim_end_matches('.').to_ascii_lowercase();
    // `www.d` traktujemy jako tę samą własność co wypisane `d` — to ta sama strona,
    // nie osobny asset. Każda INNA subdomena wymaga wypisania w §5.
    let apex = h.strip_prefix("www.").unwrap_or(&h);
    IN_SCOPE.iter().find(|s| apex == s.domain)
}

/// Host jest subdomeną domeny w zakresie, ale sam nie jest wypisany.
pub fn subdomain_of_in_scope(host: &str) -> Option<&'static str> {
    let h = host.trim_end_matches('.').to_ascii_lowercase();
    IN_SCOPE
        .iter()
        .find(|s| h.ends_with(s.domain) && h != s.domain)
        .map(|s| s.domain)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn exact_domains_are_in_scope() {
        for s in IN_SCOPE {
            assert!(in_scope(s.domain).is_some(), "{} powinno być w zakresie", s.domain);
        }
    }

    #[test]
    fn www_of_apex_is_the_same_asset() {
        assert!(in_scope("www.nask.pl").is_some());
        assert!(in_scope("www.dyzurnet.pl").is_some());
        assert_eq!(in_scope("www.oad.nask.pl").unwrap().tier, 1);
    }

    #[test]
    fn unlisted_subdomains_are_not() {
        // realne hosty widziane w Certificate Transparency, ale NIE wypisane w §5
        for h in ["gitlab.snkom.nask.pl", "nextcloud.snkom.nask.pl", "zakupy.nask.pl"] {
            assert!(in_scope(h).is_none(), "{} nie jest w zakresie", h);
            assert_eq!(subdomain_of_in_scope(h), Some("nask.pl"));
        }
    }

    #[test]
    fn oad_beats_parent_match() {
        // oad.nask.pl jest wypisane osobno w Tier 1 — musi trafić jako własny wpis
        assert_eq!(in_scope("oad.nask.pl").unwrap().tier, 1);
        assert_eq!(in_scope("dataannotation.pllum.org.pl").unwrap().tier, 2);
    }

    #[test]
    fn payouts_follow_regulation() {
        assert_eq!(payout(1, 9.5), 20_000);
        assert_eq!(payout(1, 7.5), 9_000);
        assert_eq!(payout(2, 9.5), 10_000);
        assert_eq!(payout(1, 1.0), 600);
    }
}
