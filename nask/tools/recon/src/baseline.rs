//! Odejmowanie catch-all: bez tego każdy wynik 200 jest fałszywym trafieniem.
//!
//! Metoda: dla każdego hosta pobieramy losową, na pewno nieistniejącą ścieżkę.
//! Jej odpowiedź to "szablon catch-all" danego hosta. Następnie każdą podejrzaną
//! odpowiedź normalizujemy (podstawiamy literalną ścieżkę słowem PLACEHOLDER)
//! i porównujemy z szablonem. Identyczne = catch-all = nie jest znaleziskiem.

use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};

#[derive(Clone, Debug)]
pub struct Baseline {
    pub status: u16,
    pub size: usize,
    pub fingerprint: u64,
}

/// Usuwa z treści elementy zmienne między żądaniami (nonce, CSRF, znaczniki czasu),
/// żeby dwa catch-alle tego samego hosta dały ten sam odcisk.
fn strip_dynamic(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    let b = s.as_bytes();
    let mut i = 0;
    while i < b.len() {
        let mut j = i;
        while j < b.len() && (b[j] as char).is_ascii_hexdigit() && !b[j].is_ascii_whitespace() { j += 1; }
        let run = j - i;
        if run >= 16 && j <= b.len() {
            out.push_str("<HEX>");
            i = j;
        } else {
            out.push(b[i] as char);
            i += 1;
        }
    }
    out
}

pub fn fingerprint(body: &str, path: &str) -> u64 {
    // normalizacja: usuń ścieżkę (może być wpleciona w canonical, title, breadcrumb)
    let normalized = strip_dynamic(&body.replace(path, "PLACEHOLDER"));
    // dodatkowo zwiń białe znaki, żeby różnice formatowania nie maskowały catch-all
    let normalized: String = normalized.split_whitespace().collect::<Vec<_>>().join(" ");
    let mut h = DefaultHasher::new();
    normalized.hash(&mut h);
    h.finish()
}

impl Baseline {
    pub fn from(body: &str, status: u16, path: &str) -> Self {
        Self {
            status,
            size: body.len(),
            fingerprint: fingerprint(body, path),
        }
    }

    /// TWARDA reguła dla ekspozycji plików: znaleziskiem jest tylko odpowiedź,
    /// która NIE jest dokumentem HTML i ma inny status niż catch-all.
    ///
    /// Uzasadnienie: prawdziwy `/.env`, `/.git/HEAD`, `/actuator/env` to tekst/JSON.
    /// Jeśli serwer zwraca HTML, to jest catch-all SPA — niezależnie od rozmiaru.
    pub fn is_real_file(&self, body: &str, status: u16, path: &str, content_type: &str) -> bool {
        if status != 200 || body.trim().is_empty() {
            return false;
        }
        let ct = content_type.to_ascii_lowercase();
        if ct.contains("html") {
            return false;
        }
        let head = body.trim_start();
        if head.starts_with('<') || head.to_ascii_lowercase().contains("<html") {
            return false;
        }
        self.is_distinct(body, status, path)
    }

    /// Czy odpowiedź na `path` jest inna niż catch-all. Wymagane: status 200.
    pub fn is_distinct(&self, body: &str, status: u16, path: &str) -> bool {
        if status != 200 {
            return false;
        }
        let fp = fingerprint(body, path);
        if fp == self.fingerprint {
            return false; // dokładnie ten sam szablon
        }
        // inny szablon, ale nadal HTML catch-all? sprawdź, czy treść nie jest stroną błędu
        let low = body.to_ascii_lowercase();
        !(low.contains("nie znaleziono") || low.contains("not found") || low.contains("nie istnieje"))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn catchall_with_echoed_path_is_detected() {
        let tmpl = "<html><link rel=canonical href=\"/zzz123\"><body>Aplikacja</body></html>";
        let b = Baseline::from(tmpl, 200, "/zzz123");
        let cand = "<html><link rel=canonical href=\"/.env\"><body>Aplikacja</body></html>";
        assert!(!b.is_distinct(cand, 200, "/.env"), "catch-all z wplecioną ścieżką musi być odrzucony");
    }

    #[test]
    fn real_file_is_distinct() {
        let tmpl = "<html><body>Aplikacja SPA</body></html>";
        let b = Baseline::from(tmpl, 200, "/zzz123");
        assert!(b.is_distinct("DB_PASSWORD=hunter2\nAPI_KEY=abc", 200, "/.env"));
    }

    #[test]
    fn html_is_never_a_file_exposure() {
        let b = Baseline::from("<html>catchall</html>", 200, "/zzz");
        assert!(!b.is_real_file("<!DOCTYPE html><html>inna strona</html>", 200, "/.env", "text/html; charset=utf-8"));
    }

    #[test]
    fn real_env_is_a_file_exposure() {
        let b = Baseline::from("<html>catchall</html>", 200, "/zzz");
        assert!(b.is_real_file("DB_PASSWORD=hunter2\nSECRET_KEY=abc", 200, "/.env", "text/plain"));
    }

    #[test]
    fn dynamic_nonce_does_not_defeat_fingerprint() {
        let a = "<html><input name=csrf value=9f8e7d6c5b4a39281706f5e4d3c2b1a0><body>x</body></html>";
        let b2 = "<html><input name=csrf value=11112222333344445555666677778888><body>x</body></html>";
        let base = Baseline::from(a, 200, "/zzz");
        assert!(!base.is_distinct(b2, 200, "/.env"), "rotujący token nie może udawać znaleziska");
    }

    #[test]
    fn non_200_never_finding() {
        let b = Baseline::from("x", 404, "/zzz");
        assert!(!b.is_distinct("DB_PASSWORD=1", 403, "/.env"));
    }
}
