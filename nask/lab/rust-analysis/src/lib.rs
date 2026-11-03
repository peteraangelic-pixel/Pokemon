//! Local analysis only. This library does not make network requests.
use rayon::prelude::*;
use regex::Regex;
use serde_json::{json, Value};
use std::ffi::{c_char, CString};

pub fn analyze(input: &str, threads: usize) -> Result<Value, String> {
    let documents: Vec<Value> = serde_json::from_str(input).map_err(|e| e.to_string())?;
    if documents.len() > 200 || !(1..=32).contains(&threads) {
        return Err("at most 200 documents; threads must be 1..32".into());
    }
    let routes = Regex::new(r#"["']((?:https?://|/)[^"'\s<>]{1,160})["']"#).unwrap();
    let aws = Regex::new(r"\bAKIA[0-9A-Z]{16}\b").unwrap();
    let file_control = Regex::new(r#"(?i)\btype["']?\s*(?:=|:)\s*["']file["']"#).unwrap();
    let password_control = Regex::new(r#"(?i)\btype["']?\s*(?:=|:)\s*["']password["']"#).unwrap();
    let support_script = Regex::new(r"(?i)(?:^|[/._-])(?:modernizr|polyfills?|vendor|framework|webpack|runtime|react-dom)(?:[/._-]|$)").unwrap();
    let api_route = Regex::new(r"(?i)/(?:api|graphql)(?:/|$|[?#])").unwrap();
    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(threads)
        .build()
        .map_err(|e| e.to_string())?;
    let rows: Vec<Value> = pool.install(|| {
        documents
            .par_iter()
            .map(|doc| {
                let body = doc["body"].as_str().unwrap_or("");
                let lower = body.to_ascii_lowercase();
                let mut literals: Vec<String> = routes
                    .captures_iter(body)
                    .filter_map(|c| c.get(1))
                    .map(|m| m.as_str().to_string())
                    .filter(|s| !s.contains("data:") && !s.contains("\\"))
                    .take(300)
                    .collect();
                literals.sort();
                literals.dedup();
                // Generic FormData support occurs in polyfills and is not an upload control.
                // Even explicit controls remain surface hints, not proof of live functionality.
                let file_mention = file_control.is_match(body);
                let password_mention = password_control.is_match(body);
                let multipart = lower.contains("formdata");
                let support = support_script.is_match(doc["source_url"].as_str().unwrap_or(""));
                let upload = file_mention && !support;
                let auth = password_mention && !support;
                let api_count = literals.iter().filter(|s| api_route.is_match(s)).count();
                let forms = lower.matches("<form").count();
                // An identifier pattern alone does not establish a secret or a vulnerability.
                let indicators: Vec<Value> = aws
                    .find_iter(body)
                    .take(10)
                    .map(|m| {
                        json!({"kind":"aws_access_key_identifier", "offset":m.start(),
                    "length":m.len(), "value":"[REDACTED]", "confirmed":false})
                    })
                    .collect();
                let score = usize::from(upload) * 20
                    + usize::from(auth) * 15
                    + forms.min(3) * 5
                    + api_count.min(10);
                let score = if support { 0 } else { score };
                json!({"source_url":doc["source_url"],"program":doc["program"],
                "tier":doc["tier"],"sha256":doc["sha256"],"upload_surface":upload,
                "authentication_surface":auth,"html_forms":forms,"route_literals":literals,
                "multipart_capability_mention":multipart,"support_script_hint":support,
                "file_control_mention":file_mention,"password_control_mention":password_mention,
                "api_route_literal_count":api_count,
                "indicators":indicators,"triage_score":score,
                "verdict":"surface_only_not_a_confirmed_vulnerability"})
            })
            .collect()
    });
    Ok(json!({"schema_version":2,"documents":rows,"confirmed_vulnerabilities":0}))
}

fn output(value: Value) -> *mut c_char {
    CString::new(value.to_string()).unwrap().into_raw()
}

/// # Safety
/// `data` must refer to `len` readable bytes for this call. Free the returned
/// pointer exactly once with `nasklab_free`; never free it with Python/libc.
#[no_mangle]
pub unsafe extern "C" fn nasklab_analyze(
    data: *const u8,
    len: usize,
    threads: usize,
) -> *mut c_char {
    if data.is_null() || len == 0 || len > 64 * 1024 * 1024 {
        return output(json!({"error":"invalid input buffer"}));
    }
    let result = std::panic::catch_unwind(|| {
        let bytes = unsafe { std::slice::from_raw_parts(data, len) };
        let input = std::str::from_utf8(bytes).map_err(|e| e.to_string())?;
        analyze(input, threads)
    });
    match result {
        Ok(Ok(value)) => output(value),
        Ok(Err(error)) => output(json!({"error":error})),
        Err(_) => output(json!({"error":"analysis failed"})),
    }
}

/// # Safety
/// Pass only null or a live pointer returned by `nasklab_analyze`, once.
#[no_mangle]
pub unsafe extern "C" fn nasklab_free(pointer: *mut c_char) {
    if !pointer.is_null() {
        drop(unsafe { CString::from_raw(pointer) });
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::ffi::CStr;

    #[test]
    fn preserves_origin_and_never_calls_a_route_a_vulnerability() {
        let result = analyze(r#"[{"program":"test","source_url":"https://a.invalid/","body":"fetch('/api/x'); fetch('https://b.invalid/api/y')"}]"#, 2).unwrap();
        assert_eq!(
            result["documents"][0]["route_literals"],
            json!(["/api/x", "https://b.invalid/api/y"])
        );
        assert_eq!(result["confirmed_vulnerabilities"], 0);
    }

    #[test]
    fn masks_identifier_values_and_keeps_source() {
        let identifier = format!("AKIA{}", "A".repeat(16));
        let input = json!([{"source_url":"https://a.invalid/a.js","body":identifier}]).to_string();
        let result = analyze(&input, 1).unwrap().to_string();
        assert!(!result.contains(&identifier));
        assert!(result.contains("[REDACTED]"));
        assert!(result.contains("https://a.invalid/a.js"));
    }

    #[test]
    fn generic_browser_capability_is_not_an_application_upload() {
        let input = json!([
            {"source_url":"https://a.invalid/modernizr-custom.js", "body":"new FormData(); input.type='file'; input.type='password'; fetch('/api/capabilities')"},
            {"source_url":"https://a.invalid/page.js", "body":"new FormData(); fetch('/static/image.png')"},
            {"source_url":"https://a.invalid/", "body":"<form><input type = 'file'><input type=\"password\"></form>"}
        ]).to_string();
        let rows = analyze(&input, 2).unwrap()["documents"].clone();
        assert_eq!(rows[0]["upload_surface"], false);
        assert_eq!(rows[0]["authentication_surface"], false);
        assert_eq!(rows[0]["file_control_mention"], true);
        assert_eq!(rows[0]["multipart_capability_mention"], true);
        assert_eq!(rows[0]["triage_score"], 0);
        assert_eq!(rows[1]["triage_score"], 0);
        assert_eq!(rows[2]["upload_surface"], true);
        assert_eq!(rows[2]["authentication_surface"], true);
        assert_eq!(rows[2]["triage_score"], 40);
    }

    #[test]
    fn ffi_roundtrip_and_bad_utf8() {
        for bytes in [b"[]".as_slice(), &[255u8][..]] {
            let ptr = unsafe { nasklab_analyze(bytes.as_ptr(), bytes.len(), 1) };
            let text = unsafe { CStr::from_ptr(ptr) }.to_str().unwrap();
            assert!(serde_json::from_str::<Value>(text).is_ok());
            unsafe { nasklab_free(ptr) };
        }
    }

    #[test]
    fn rejects_invalid_threads_and_input() {
        assert!(analyze("[]", 0).is_err());
        assert!(analyze("bad json", 1).is_err());
    }
}
