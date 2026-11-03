//! Hypothesis-driven probes.
//!
//! This is NOT a scanner. A probe is one hand-written request with a stated
//! hypothesis and an explicit marker that would confirm it. The programme
//! rewards a demonstrated chain and explicitly rejects raw scanner output, so
//! the tool only ever records: what was asked, what came back (status, length,
//! hash, a few headers), and whether a named marker was present. Bodies stay in
//! the workflow artifact and never in the public repository.

use rayon::prelude::*;
use regex::Regex;
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::sync::OnceLock;
use std::time::{Duration, Instant};

/// Markers are fixed here rather than taken from the plan file: a marker is a
/// statement about what counts as proof, and that should not be edited casually
/// while hunting.
fn marker_table() -> &'static [(&'static str, Regex)] {
    static M: OnceLock<Vec<(&'static str, Regex)>> = OnceLock::new();
    M.get_or_init(|| {
        [
            ("unix_passwd", r"(?m)^root:[^:]*:0:0:"),
            ("win_ini", r"(?i)\[fonts\]|for 16-bit app support"),
            ("env_file", r"(?m)^[A-Z][A-Z0-9_]{2,}="),
            ("aws_access_key", r"\bAKIA[0-9A-Z]{16}\b"),
            ("private_key", r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
            ("php_source", r"<\?php"),
            ("git_config", r"(?m)^\[core\]"),
            ("azure_metadata", r#""(compute|vmId|location)"\s*:"#),
            ("docker_api", r#""ApiVersion"\s*:"#),
            ("json_error", r#""(error|message|detail)"\s*:"#),
            ("html_error_pre", r"(?i)<pre[^>]*>"),
            ("not_found_pl", r"(?i)nieprawid|nie znaleziono|file not found|not found"),
            ("robots", r"(?m)^User-agent:"),
            ("xml_root", r"(?i)<\?xml"),
            ("directory_listing", r"(?i)Index of /|<title>Index of"),
        ]
        .iter()
        .map(|(n, p)| (*n, Regex::new(p).expect("marker regex")))
        .collect()
    })
}

fn sha256_hex(bytes: &[u8]) -> String {
    Sha256::digest(bytes).iter().map(|b| format!("{b:02x}")).collect()
}

/// Keep a snippet readable and safe: printable ASCII only, no long runs.
fn safe_snippet(bytes: &[u8], limit: usize) -> String {
    let text = String::from_utf8_lossy(bytes);
    let cleaned: String = text
        .chars()
        .map(|c| if c.is_control() && c != '\n' { ' ' } else { c })
        .collect();
    let mut out: String = cleaned.chars().take(limit).collect();
    if cleaned.chars().count() > limit {
        out.push('…');
    }
    out
}

pub struct ProbeResult {
    pub value: Value,
}

pub fn run_probes(
    client: &reqwest::blocking::Client,
    limiter: &crate::scope::Limiter,
    probes: &[Value],
    snippet_ok: bool,
) -> Vec<ProbeResult> {
    // One catch-all baseline per host: a random path that cannot exist. A probe
    // whose answer matches the baseline tells us nothing, and saying so out loud
    // is the difference between a finding and a false positive.
    let baseline_hosts: Vec<String> = {
        let mut v: Vec<String> = probes
            .iter()
            .filter_map(|p| p.get("url").and_then(|u| u.as_str()))
            .filter_map(|u| crate::scope::split_url(u).ok().map(|(h, _)| h))
            .collect();
        v.sort();
        v.dedup();
        v
    };

    let baselines: std::collections::HashMap<String, (u16, String)> = baseline_hosts
        .par_iter()
        .map(|host| {
            let path = format!("/zz-baseline-{:016x}", fnv1a(host.as_bytes()));
            let url = format!("https://{host}{path}");
            limiter.acquire();
            match client.get(url.as_str()).send() {
                Ok(r) => {
                    let status = r.status().as_u16();
                    let body = r.bytes().map(|b| sha256_hex(&b)).unwrap_or_default();
                    (host.clone(), (status, body))
                }
                Err(_) => (host.clone(), (0, String::new())),
            }
        })
        .collect();

    probes
        .par_iter()
        .map(|p| {
            let url = p.get("url").and_then(|u| u.as_str()).unwrap_or("");
            let id = p.get("id").and_then(|v| v.as_str()).unwrap_or("?");
            let note = p.get("note").and_then(|v| v.as_str()).unwrap_or("");
            let want_snippet = snippet_ok && p.get("snippet").and_then(|v| v.as_bool()) == Some(true);

            if let Err(e) = crate::scope::split_url(url) {
                return ProbeResult {
                    value: json!({"id": id, "url": url, "note": note, "error": e}),
                };
            }
            // Optional per-probe request headers. This is what makes a CORS test
            // meaningful: the answer is only a finding if the server reflects the
            // foreign Origin we sent, and allows credentials with it.
            let sent_origin = p
                .get("headers")
                .and_then(|h| h.get("Origin"))
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string();
            limiter.acquire();
            let t0 = Instant::now();
            let mut req = client.get(url);
            if let Some(hs) = p.get("headers").and_then(|h| h.as_object()) {
                for (k, v) in hs {
                    if let Some(vs) = v.as_str() {
                        req = req.header(k.as_str(), vs);
                    }
                }
            }
            let resp = req.send();
            let elapsed = t0.elapsed().as_millis() as u64;
            match resp {
                Ok(r) => {
                    let status = r.status().as_u16();
                    let hdr = |n: &str| {
                        r.headers()
                            .get(n)
                            .and_then(|v| v.to_str().ok())
                            .unwrap_or("")
                            .to_string()
                    };
                    // Capture every header we care about BEFORE moving the
                    // response into bytes(): a closure that borrows `r` cannot
                    // outlive the move (E0505).
                    let ctype = hdr("content-type");
                    let disp = hdr("content-disposition");
                    let location = hdr("location");
                    let acao = hdr("access-control-allow-origin");
                    let acac = hdr("access-control-allow-credentials");
                    let body = r.bytes().unwrap_or_default();
                    let digest = sha256_hex(&body);
                    let text = String::from_utf8_lossy(&body);
                    let mut hits: Vec<&str> = Vec::new();
                    for (name, re) in marker_table() {
                        if re.is_match(&text) {
                            hits.push(*name);
                        }
                    }
                    let (b_status, b_hash) = baselines
                        .get(
                            &crate::scope::split_url(url)
                                .map(|(h, _)| h)
                                .unwrap_or_default(),
                        )
                        .cloned()
                        .unwrap_or((0, String::new()));
                    let same_as_baseline = status == b_status && digest == b_hash;
                    // A finding needs a marker that is not merely the catch-all
                    // error page, or a response clearly different from it.
                    let meaningful: Vec<&str> = hits
                        .iter()
                        .copied()
                        .filter(|h| !(*h == "not_found_pl" || *h == "html_error_pre"))
                        .collect();
                    let cors_reflected = !sent_origin.is_empty() && acao == sent_origin;
                    let cors_wildcard_with_creds = acao == "*" && acac.eq_ignore_ascii_case("true");
                    let interesting = !meaningful.is_empty()
                        || cors_reflected
                        || cors_wildcard_with_creds
                        || (!same_as_baseline && status < 400);
                    let mut out = json!({
                        "id": id, "url": url, "note": note,
                        "sent_origin": sent_origin,
                        "acao": acao,
                        "acac": acac,
                        "cors_reflected": cors_reflected,
                        "cors_wildcard_with_credentials": cors_wildcard_with_creds,
                        "status": status,
                        "content_type": ctype,
                        "content_disposition": disp,
                        "location": location,
                        "bytes": body.len(),
                        "sha256": digest,
                        "ms": elapsed,
                        "markers": hits,
                        "baseline_status": b_status,
                        "same_as_baseline": same_as_baseline,
                        "interesting": interesting,
                    });
                    // A snippet is only kept when no marker fired: a hit means the
                    // body may contain sensitive material, which must not be
                    // committed to a public repository.
                    if want_snippet && meaningful.is_empty() {
                        out["snippet"] = json!(safe_snippet(&body, 400));
                    }
                    ProbeResult { value: out }
                }
                Err(e) => ProbeResult {
                    value: json!({"id": id, "url": url, "note": note,
                                  "status": null, "error": e.to_string(), "ms": elapsed}),
                },
            }
        })
        .collect()
}

fn fnv1a(bytes: &[u8]) -> u64 {
    let mut h: u64 = 0xcbf29ce484222325;
    for b in bytes {
        h ^= *b as u64;
        h = h.wrapping_mul(0x100000001b3);
    }
    h
}

pub fn default_client() -> Result<reqwest::blocking::Client, String> {
    reqwest::blocking::Client::builder()
        .redirect(reqwest::redirect::Policy::none())
        .timeout(Duration::from_secs(25))
        .connect_timeout(Duration::from_secs(10))
        .user_agent(crate::UA)
        .build()
        .map_err(|e| e.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn passwd_marker_fires() {
        let t = "root:x:0:0:root:/root:/bin/bash\n";
        assert!(marker_table().iter().any(|(n, r)| *n == "unix_passwd" && r.is_match(t)));
    }

    #[test]
    fn plain_html_does_not_trip_strong_markers() {
        let t = "<html><body>Witamy na stronie</body></html>";
        let strong = ["unix_passwd", "aws_access_key", "private_key", "azure_metadata"];
        for (name, re) in marker_table() {
            if strong.contains(name) {
                assert!(!re.is_match(t), "{} must not match plain html", name);
            }
        }
    }

    #[test]
    fn snippet_is_bounded_and_printable() {
        let s = safe_snippet(b"abc\x01\x02def\nghi", 5);
        assert!(s.chars().count() <= 6, "{s:?}");
    }
}
