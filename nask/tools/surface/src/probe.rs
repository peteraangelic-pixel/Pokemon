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


/// One request, fully measured. Reused for the original probe and for the single
/// same-origin redirect hop.
fn measure(
    client: &reqwest::blocking::Client,
    limiter: &crate::scope::Limiter,
    url: &str,
    sent_origin: &str,
    cookie: &str,
    reflect: &str,
    baselines: &std::collections::HashMap<String, (u16, String)>,
    want_snippet: bool,
) -> Value {
    limiter.acquire();
    let t0 = Instant::now();
    let mut req = client.get(url);
    if !sent_origin.is_empty() {
        req = req.header("Origin", sent_origin);
    }
    // A probe-level cookie is needed to tell a *constant* server value from a
    // value derived from the client's own state. Without it the control is
    // vacuous: two identical bodyless requests always agree.
    if !cookie.is_empty() {
        req = req.header("Cookie", cookie);
    }
    let resp = match req.send() {
        Ok(r) => r,
        Err(e) => {
            return json!({"url": url, "status": null, "bytes": 0, "ms": t0.elapsed().as_millis() as u64,
                          "error": e.to_string()})
        }
    };
    let status = resp.status().as_u16();
    let hdr = |n: &str| {
        resp.headers().get(n).and_then(|v| v.to_str().ok()).unwrap_or("").to_string()
    };
    let ctype = hdr("content-type");
    let disp = hdr("content-disposition");
    let location = hdr("location");
    let acao = hdr("access-control-allow-origin");
    let acac = hdr("access-control-allow-credentials");
    let body = resp.bytes().unwrap_or_default();
    let digest = sha256_hex(&body);
    let text = String::from_utf8_lossy(&body);
    let digest_norm = sha256_hex(normalize(&text).as_bytes());

    // Reflection check for XSS triage: the marker is unique, so finding it in
    // the body proves the parameter reaches the output. The window shows whether
    // it landed as text or as live markup - only the latter is a candidate.
    let mut reflection = Value::Null;
    if !reflect.is_empty() {
        reflection = match text.find(reflect) {
            Some(pos) => {
                let start = pos.saturating_sub(120);
                let end = (pos + reflect.len() + 120).min(text.len());
                let window = text
                    .get(start..end)
                    .map(|w| safe_snippet(w.as_bytes(), 260))
                    .unwrap_or_default();
                json!({"found": true, "offset": pos, "window": window})
            }
            None => json!({"found": false}),
        };
    }
    let mut hits: Vec<&'static str> = Vec::new();
    for (name, re) in marker_table() {
        if re.is_match(&text) {
            hits.push(*name);
        }
    }
    let meaningful: Vec<&str> = hits
        .iter()
        .copied()
        .filter(|h| !(*h == "not_found_pl" || *h == "html_error_pre"))
        .collect();
    let host = crate::scope::split_url(url).map(|(h, _)| h).unwrap_or_default();
    let (b_status, b_hash) = baselines.get(&host).cloned().unwrap_or((0, String::new()));
    let same_as_baseline = status == b_status && digest_norm == b_hash;
    let cors_reflected = !sent_origin.is_empty() && acao == sent_origin;
    let cors_wildcard_with_creds = acao == "*" && acac.eq_ignore_ascii_case("true");
    let mut out = json!({
        "url": url,
        "status": status,
        "content_type": ctype,
        "content_disposition": disp,
        "location": location,
        "acao": acao,
        "acac": acac,
        "cors_reflected": cors_reflected,
        "cors_wildcard_with_credentials": cors_wildcard_with_creds,
        "bytes": body.len(),
        "sha256": digest,
        "ms": t0.elapsed().as_millis() as u64,
        "markers": hits,
        "reflection": reflection,
        "baseline_status": b_status,
        "same_as_baseline": same_as_baseline,
        "interesting": !meaningful.is_empty()
            || cors_reflected
            || cors_wildcard_with_creds
            || reflection.get("found").and_then(|v| v.as_bool()).unwrap_or(false)
            || (!same_as_baseline && status < 400),
    });
    if want_snippet && meaningful.is_empty() {
        out["snippet"] = json!(safe_snippet(&body, 400));
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
                    let body = r.bytes().unwrap_or_default();
                    let norm = normalize(&String::from_utf8_lossy(&body));
                    (host.clone(), (status, sha256_hex(norm.as_bytes())))
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
            let sent_origin = p
                .get("headers")
                .and_then(|h| h.get("Origin"))
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string();

            let reflect = p.get("reflect").and_then(|v| v.as_str()).unwrap_or("");
            let cookie = p.get("cookie").and_then(|v| v.as_str()).unwrap_or("");
            let mut first = measure(
                client, limiter, url, &sent_origin, cookie, reflect, &baselines, want_snippet,
            );

            // Server frameworks commonly answer a canonical path with 308 to the
            // trailing-slash form. Following it is useful, but only if it stays on
            // the same host: a redirect is exactly how a request could leave the
            // published scope, which is why the client itself never follows one.
            let mut followed: Option<Value> = None;
            let status = first.get("status").and_then(|v| v.as_u64()).unwrap_or(0);
            let loc = first.get("location").and_then(|v| v.as_str()).unwrap_or("").to_string();
            if (300..400).contains(&status) && !loc.is_empty() {
                let (base_host, base_path) = crate::scope::split_url(url).unwrap_or_default();
                let target = if loc.starts_with("https://") {
                    Some(loc.clone())
                } else if loc.starts_with('/') {
                    Some(format!("https://{base_host}{loc}"))
                } else if loc.starts_with("http://") {
                    None // never downgrade
                } else {
                    // relative to the directory of the current path
                    let dir = match base_path.rfind('/') {
                        Some(i) => &base_path[..=i],
                        None => "/",
                    };
                    Some(format!("https://{base_host}{dir}{loc}"))
                };
                if let Some(t) = target {
                    if crate::scope::split_url(&t).is_ok() {
                        let hop_cookie = if crate::scope::split_url(&t).map(|(h, _)| h)
                            == crate::scope::split_url(url).map(|(h, _)| h)
                        {
                            cookie
                        } else {
                            ""
                        };
                        let hop = measure(
                            client, limiter, &t, &sent_origin, hop_cookie, reflect, &baselines,
                            want_snippet,
                        );
                        followed = Some(hop);
                    }
                }
            }

            let mut out = first.take();
            if let Some(o) = out.as_object_mut() {
                o.insert("id".into(), json!(id));
                o.insert("note".into(), json!(note));
                o.insert("sent_origin".into(), json!(sent_origin));
                if let Some(f) = followed {
                    let hop_interesting = f.get("interesting").and_then(|v| v.as_bool()) == Some(true);
                    o.insert("followed".into(), f);
                    if hop_interesting {
                        o.insert("interesting".into(), json!(true));
                    }
                }
            }
            ProbeResult { value: out }
        })
        .collect()
}

/// Replace digit/hex runs with a placeholder before hashing.
///
/// dns.pl stamps every response with a fresh `_event_transid`, so the raw hash of
/// two identical 404 pages never matches. Comparing raw hashes against the
/// catch-all baseline therefore flagged every such page as "interesting" -
/// a systematic false-positive generator. Normalising first removes the noise
/// while keeping the comparison meaningful.
fn normalize(text: &str) -> String {
    let mut out = String::with_capacity(text.len());
    let mut in_run = false;
    for c in text.chars() {
        if c.is_ascii_digit() {
            if !in_run {
                out.push('#');
                in_run = true;
            }
        } else {
            in_run = false;
            out.push(c);
        }
    }
    out
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
