//! Hard scope guard.
//!
//! The list below is copied from the programme page
//! <https://hack.cert.pl/programs/nask-pib/nask/editions/1> on 2026-11-03.
//! It contains exact hosts only; the programme defines no wildcards.
//! Any request to a host that is not in this list is refused in code, so a
//! mistyped plan cannot reach an out-of-scope system.

pub struct Target {
    pub host: &'static str,
    pub tier: u8,
}

/// Tier 1 and Tier 2 as published in "Zakres systemów".
pub const TARGETS: &[Target] = &[
    // Tier 1
    Target { host: "nask.pl", tier: 1 },
    Target { host: "dyzurnet.pl", tier: 1 },
    Target { host: "dns.pl", tier: 1 },
    Target { host: "oad.nask.pl", tier: 1 },
    Target { host: "zglos-dezinformacje.nask.pl", tier: 1 },
    // Tier 2
    Target { host: "bezpiecznymiesiac.pl", tier: 2 },
    Target { host: "secure.edu.pl", tier: 2 },
    Target { host: "bezpiecznewybory.pl", tier: 2 },
    Target { host: "116sos.pl", tier: 2 },
    Target { host: "pllum.org.pl", tier: 2 },
    Target { host: "science.nask.pl", tier: 2 },
    Target { host: "dataannotation.pllum.org.pl", tier: 2 },
];

/// `nask.pl` answers with a redirect to its canonical `www.` form. The apex is
/// listed explicitly in the programme, so the canonical form of the same site is
/// accepted here and nowhere else. Every other subdomain stays out of scope.
const ALIASES: &[(&str, &str)] = &[("www.nask.pl", "nask.pl")];

pub fn tier_of(host: &str) -> Option<u8> {
    let canonical = canonical_host(host)?;
    TARGETS.iter().find(|t| t.host == canonical).map(|t| t.tier)
}

pub fn canonical_host(host: &str) -> Option<&'static str> {
    if let Some(t) = TARGETS.iter().find(|t| t.host == host) {
        return Some(t.host);
    }
    if let Some((_, canonical)) = ALIASES.iter().find(|(alias, _)| *alias == host) {
        return Some(canonical);
    }
    None
}

pub fn is_allowed(host: &str) -> bool {
    canonical_host(host).is_some()
}

/// Parse `https://host/path?query` into `(host, path_and_query)`.
/// Refuses anything that is not plain https on an in-scope host.
pub fn split_url(url: &str) -> Result<(String, String), String> {
    let rest = url
        .strip_prefix("https://")
        .ok_or_else(|| format!("only https:// is allowed, got {url}"))?;
    let (host, tail) = match rest.find('/') {
        Some(i) => (&rest[..i], &rest[i..]),
        None => (rest, "/"),
    };
    if host.contains('@') || host.contains(':') {
        return Err(format!("refusing unusual authority in {url}"));
    }
    if !is_allowed(host) {
        return Err(format!("host {host} is not in the published scope"));
    }
    Ok((host.to_string(), tail.to_string()))
}

/// Global token bucket. Every request in the process goes through one limiter,
/// so the programme limit holds even with several worker threads. The check is
/// conservative: it spaces requests at `1/interval` from each other.
pub struct Limiter {
    interval: std::time::Duration,
    next_free: std::sync::Mutex<std::time::Instant>,
}

impl Limiter {
    pub fn new(requests_per_second: f64) -> Result<Self, String> {
        if !(0.1..=5.0).contains(&requests_per_second) {
            return Err(format!(
                "requests_per_second must be within 0.1..=5.0 (programme limit is 5); got {requests_per_second}"
            ));
        }
        Ok(Self {
            interval: std::time::Duration::from_secs_f64(1.0 / requests_per_second),
            next_free: std::sync::Mutex::new(std::time::Instant::now()),
        })
    }

    pub fn acquire(&self) {
        let mut guard = self.next_free.lock().unwrap_or_else(|e| e.into_inner());
        let now = std::time::Instant::now();
        if *guard > now {
            std::thread::sleep(*guard - now);
        }
        *guard = std::time::Instant::now() + self.interval;
    }

    pub fn interval(&self) -> std::time::Duration {
        self.interval
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn apex_and_canonical_are_allowed() {
        assert!(is_allowed("nask.pl"));
        assert!(is_allowed("www.nask.pl"));
    }

    #[test]
    fn unlisted_subdomains_are_refused() {
        for host in ["gitlab.snkom.nask.pl", "panel.dns.pl", "zakupy.nask.pl", "nask.pl.evil.tld"] {
            assert!(!is_allowed(host), "{host} must be out of scope");
        }
    }

    #[test]
    fn lookalike_hosts_are_refused() {
        for url in [
            "http://nask.pl/",
            "https://nask.pl.evil.tld/",
            "https://evil.tld/nask.pl",
            "https://user@nask.pl/",
            "https://nask.pl:8443/",
        ] {
            assert!(split_url(url).is_err(), "{url} must be refused");
        }
    }

    #[test]
    fn limiter_refuses_above_the_programme_cap() {
        assert!(Limiter::new(5.0).is_ok());
        assert!(Limiter::new(4.5).is_ok());
        assert!(Limiter::new(5.1).is_err());
        assert!(Limiter::new(50.0).is_err());
    }
}
