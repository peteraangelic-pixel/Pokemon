//! Offline analysis of already-downloaded bodies.
//!
//! Nothing here talks to the network. This is where the CPU actually matters:
//! bundles of a few hundred kilobytes to several megabytes each, scanned in
//! parallel with Rayon. At the network side the programme caps us at 5 req/s,
//! so parsing is the only part that scales with cores.

use rayon::prelude::*;
use regex::Regex;
use serde_json::{json, Value};
use std::path::Path;
use std::sync::OnceLock;

fn re_script() -> &'static Regex {
    static R: OnceLock<Regex> = OnceLock::new();
    R.get_or_init(|| Regex::new(r#"(?i)<script[^>]+src\s*=\s*["']([^"']+)["']"#).unwrap())
}

fn re_link() -> &'static Regex {
    static R: OnceLock<Regex> = OnceLock::new();
    R.get_or_init(|| Regex::new(r#"(?i)<(?:a|link)\b[^>]+href\s*=\s*["']([^"'#]+)["']"#).unwrap())
}

fn re_form() -> &'static Regex {
    static R: OnceLock<Regex> = OnceLock::new();
    R.get_or_init(|| Regex::new(r#"(?is)<form\b([^>]*)>(.*?)</form>"#).unwrap())
}

fn re_attr() -> &'static Regex {
    static R: OnceLock<Regex> = OnceLock::new();
    R.get_or_init(|| Regex::new(r#"(?i)\b(action|method|name|type|id)\s*=\s*["']([^"']*)["']"#).unwrap())
}

/// String literals that look like a route: `"/api/x"`, `'/v1/y'`, `https://host/z`.
///
/// Kept deliberately flat. A nested repetition such as
/// `(?:/[\w\-.~%]{0,60}){1,8}` compiles to more than the regex crate's 10 MB
/// DFA limit and fails at runtime with `CompiledTooBig`.
fn re_route() -> &'static Regex {
    static R: OnceLock<Regex> = OnceLock::new();
    R.get_or_init(|| {
        Regex::new(r#"["'`]((?:https?://[^"'`\s<>]{4,120})|/[\w\-.~%/]{1,300}(?:\?[^"'`\s<>]{0,120})?)["'`]"#)
            .unwrap()
    })
}

fn re_sourcemap() -> &'static Regex {
    static R: OnceLock<Regex> = OnceLock::new();
    R.get_or_init(|| Regex::new(r#"(?i)sourceMappingURL=([^\s*"']+)"#).unwrap())
}

fn re_comment() -> &'static Regex {
    static R: OnceLock<Regex> = OnceLock::new();
    R.get_or_init(|| {
        Regex::new(r#"(?i)(?:TODO|FIXME|HACK|XXX|password|secret|api[_-]?key|token|bearer|authorization)\b[^\n\r*/]{0,80}"#)
            .unwrap()
    })
}

fn re_next_build() -> &'static Regex {
    static R: OnceLock<Regex> = OnceLock::new();
    R.get_or_init(|| Regex::new(r#""buildId"\s*:\s*"([^"]+)""#).unwrap())
}

fn re_generator() -> &'static Regex {
    static R: OnceLock<Regex> = OnceLock::new();
    R.get_or_init(|| Regex::new(r#"(?i)<meta[^>]+name\s*=\s*["']generator["'][^>]+content\s*=\s*["']([^"']+)["']"#).unwrap())
}

fn cap<T>(v: &mut Vec<T>, n: usize) {
    if v.len() > n {
        v.truncate(n);
    }
}

pub fn analyze_one(path: &Path, content_type: &str) -> Value {
    let body = match std::fs::read_to_string(path) {
        Ok(b) => b,
        Err(_) => return json!({"file": path.display().to_string(), "readable": false}),
    };
    let is_html = content_type.contains("html") || body.trim_start().starts_with('<');
    let is_js = content_type.contains("javascript") || content_type.contains("ecmascript");

    let mut scripts: Vec<String> = Vec::new();
    let mut links: Vec<String> = Vec::new();
    let mut forms: Vec<Value> = Vec::new();
    let mut routes: Vec<String> = Vec::new();
    let mut maps: Vec<String> = Vec::new();
    let mut hits: Vec<String> = Vec::new();
    let mut build_id = String::new();
    let mut generator = String::new();

    if is_html {
        for c in re_script().captures_iter(&body) {
            scripts.push(c[1].to_string());
        }
        for c in re_link().captures_iter(&body) {
            links.push(c[1].to_string());
        }
        for c in re_form().captures_iter(&body) {
            let attrs = &c[1];
            let inner = &c[2];
            let mut action = String::new();
            let mut method = String::new();
            let mut fields: Vec<Value> = Vec::new();
            for a in re_attr().captures_iter(attrs) {
                match a[1].to_lowercase().as_str() {
                    "action" => action = a[2].to_string(),
                    "method" => method = a[2].to_string(),
                    _ => {}
                }
            }
            for a in re_attr().captures_iter(inner) {
                let key = a[1].to_lowercase();
                if key == "name" || key == "type" {
                    fields.push(json!({"field": key, "value": a[2]}));
                }
            }
            forms.push(json!({"action": action, "method": method, "fields": fields}));
        }
        if let Some(c) = re_generator().captures(&body) {
            generator = c[1].to_string();
        }
        if let Some(c) = re_next_build().captures(&body) {
            build_id = c[1].to_string();
        }
    }

    for c in re_route().captures_iter(&body) {
        routes.push(c[1].to_string());
    }
    for c in re_sourcemap().captures_iter(&body) {
        maps.push(c[1].to_string());
    }
    for c in re_comment().captures_iter(&body) {
        hits.push(c[0].trim().to_string());
    }

    // Dedupe while keeping the first occurrence order.
    let mut seen = std::collections::HashSet::new();
    routes.retain(|r| seen.insert(r.clone()));
    scripts.sort();
    scripts.dedup();
    links.sort();
    links.dedup();
    maps.sort();
    maps.dedup();
    hits.sort();
    hits.dedup();

    let routes_total = routes.len();
    cap(&mut routes, 400);
    cap(&mut links, 120);
    cap(&mut scripts, 120);
    cap(&mut hits, 30);

    json!({
        "file": path.display().to_string(),
        "readable": true,
        "bytes": body.len(),
        "kind": if is_html { "html" } else if is_js { "js" } else { "other" },
        "generator": generator,
        "next_build_id": build_id,
        "has_next": body.contains("/_next/") || body.contains("__NEXT_DATA__"),
        "has_wordpress": body.contains("wp-content") || body.contains("wp-json"),
        "has_nuxt": body.contains("__NUXT__") || body.contains("/_nuxt/"),
        "has_react": body.contains("react") || body.contains("__REACT"),
        "has_sourcemap": !maps.is_empty(),
        "sourcemaps": maps,
        "scripts": scripts,
        "links": links,
        "forms": forms,
        "route_literals_total": routes_total,
        "route_literals": routes,
        "sensitive_comment_hits": hits,
    })
}

/// Analyze every `*.body` file in `dir`, in parallel.
pub fn analyze_dir(dir: &Path, index: &Value) -> Result<Value, String> {
    // index entries: [{file, url, host, path, tier, status, content_type, bytes}]
    let entries: Vec<Value> = index
        .get("entries")
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default();

    let rows: Vec<Value> = entries
        .par_iter()
        .map(|e| {
            let file = e.get("file").and_then(|v| v.as_str()).unwrap_or("");
            let ctype = e.get("content_type").and_then(|v| v.as_str()).unwrap_or("");
            let mut row = analyze_one(Path::new(file), ctype);
            if let Some(obj) = row.as_object_mut() {
                obj.insert("url".into(), e.get("url").cloned().unwrap_or(Value::Null));
                obj.insert("host".into(), e.get("host").cloned().unwrap_or(Value::Null));
                obj.insert("tier".into(), e.get("tier").cloned().unwrap_or(Value::Null));
                obj.insert("status".into(), e.get("status").cloned().unwrap_or(Value::Null));
            }
            row
        })
        .collect();

    // Aggregate per host: which endpoints and which JS assets were seen.
    let mut per_host: std::collections::BTreeMap<String, Value> = std::collections::BTreeMap::new();
    for row in &rows {
        let host = row.get("host").and_then(|v| v.as_str()).unwrap_or("?").to_string();
        let entry = per_host.entry(host).or_insert_with(|| json!({
            "documents": 0, "js_documents": 0, "route_literals": 0,
            "has_sourcemap": false, "frameworks": []
        }));
        if let Some(o) = entry.as_object_mut() {
            let docs = o["documents"].as_u64().unwrap_or(0) + 1;
            o.insert("documents".into(), json!(docs));
            if row.get("kind").and_then(|v| v.as_str()) == Some("js") {
                let js = o["js_documents"].as_u64().unwrap_or(0) + 1;
                o.insert("js_documents".into(), json!(js));
            }
            let rl = o["route_literals"].as_u64().unwrap_or(0)
                + row.get("route_literals_total").and_then(|v| v.as_u64()).unwrap_or(0);
            o.insert("route_literals".into(), json!(rl));
            if row.get("has_sourcemap").and_then(|v| v.as_bool()) == Some(true) {
                o.insert("has_sourcemap".into(), json!(true));
            }
            let mut fw: Vec<String> = o["frameworks"]
                .as_array()
                .map(|a| a.iter().filter_map(|v| v.as_str().map(String::from)).collect())
                .unwrap_or_default();
            for (flag, name) in [
                ("has_next", "next"),
                ("has_wordpress", "wordpress"),
                ("has_nuxt", "nuxt"),
                ("has_react", "react"),
            ] {
                if row.get(flag).and_then(|v| v.as_bool()) == Some(true) && !fw.iter().any(|f| f == name) {
                    fw.push(name.to_string());
                }
            }
            o.insert("frameworks".into(), json!(fw));
        }
    }

    Ok(json!({
        "schema_version": 1,
        "documents": rows,
        "per_host": per_host,
        "confirmed_vulnerabilities": 0,
        "note": "Discovery output only. A route literal is not an exposed endpoint and nothing here is a finding."
    }))
}
