//! Testy integracyjne: guard zakresu, limiter, parser HAR i analiza różnicowa.
//!
//! Wszystko offline — zero żądań sieciowych, zero zależności od środowiska.

use nasktriage::analyze::{self, Account, Kind};
use nasktriage::har;
use nasktriage::rate::{TokenBucket, MAX_RPS};
use nasktriage::scope::{self, Scope, Tier};

const SCOPE: &str = r#"{
  "tier1": ["nask.pl", "dyzurnet.pl", "dns.pl", "oad.nask.pl", "zglos-dezinformacje.nask.pl"],
  "tier2": ["dataannotation.pllum.org.pl", "116sos.pl"]
}"#;

#[test]
fn scope_parses_and_classifies_tiers() {
    let scope = Scope::parse(SCOPE).expect("scope");
    assert_eq!(scope.tier_of("nask.pl"), Some(Tier::Tier1));
    assert_eq!(scope.tier_of("NASK.PL"), Some(Tier::Tier1), "wielkość liter nie ma znaczenia");
    assert_eq!(scope.tier_of("dataannotation.pllum.org.pl"), Some(Tier::Tier2));
    assert_eq!(scope.tier_of("panel.dns.pl"), None, "subdomena nie jest w zakresie");
    assert_eq!(scope.tier_of("gitlab.snkom.nask.pl"), None);
    assert_eq!(scope.tier_of("nask.pl.evil.example"), None, "sufiks nie wystarcza");
}

#[test]
fn scope_rejects_port_and_accepts_url() {
    let scope = Scope::parse(SCOPE).expect("scope");
    assert_eq!(scope.tier_of("nask.pl:443"), Some(Tier::Tier1));
    let (host, tier) = scope.check_url("https://oad.nask.pl/api/v1/status?x=1").expect("w zakresie");
    assert_eq!(host, "oad.nask.pl");
    assert_eq!(tier, Tier::Tier1);
    assert!(scope.check_url("https://panel.dns.pl/").is_err());
    assert!(scope.check_url("ftp://nask.pl/").is_err(), "tylko http/https");
}

#[test]
fn url_helpers_split_host_path_and_query() {
    assert_eq!(scope::host_of_url("https://user:pw@Example.COM:8443/x").unwrap(), "example.com");
    assert_eq!(scope::path_of_url("https://a.example/api/tasks/17?z=2#frag"), "/api/tasks/17");
    assert_eq!(scope::path_of_url("https://a.example"), "/");
    let q = scope::query_pairs("https://a.example/x?access_token=abc&page=2");
    assert_eq!(q[0].0, "access_token");
    assert_eq!(q[1].1, "2");
}

#[test]
fn rate_limiter_refuses_to_break_the_rules() {
    assert!(TokenBucket::new(5.0).is_ok(), "sufit regulaminowy jest dozwolony");
    assert!(TokenBucket::new(5.1).is_err(), "powyżej 5/s = odmowa startu");
    assert!(TokenBucket::new(0.0).is_err());
    assert_eq!(MAX_RPS, 5.0);
}

#[test]
fn rate_limiter_is_deterministic_with_injected_clock() {
    let mut bucket = TokenBucket::new(2.0).expect("2 rps");
    assert!(bucket.try_acquire(0.0));
    assert!(bucket.try_acquire(0.0));
    assert!(!bucket.try_acquire(0.0), "trzecie żądanie w tej samej sekundzie nie przechodzi");
    let delay = bucket.delay_s(0.0);
    assert!((delay - 0.5).abs() < 1e-9, "przy 2 rps czekamy 0,5 s, jest {delay}");
    assert!(bucket.try_acquire(0.5), "po 0,5 s wraca jeden token");
}

#[test]
fn identifiers_and_templates() {
    assert!(har::is_identifier("101"));
    assert!(har::is_identifier("550e8400-e29b-41d4-a716-446655440000"));
    assert!(har::is_identifier("550e8400e29b41d4a716446655440000"));
    assert!(har::is_identifier("a3f9c0d1e2b3a4f5c6d7e8f9"));
    assert!(!har::is_identifier("tasks"));
    assert!(!har::is_identifier("api"));
    assert!(!har::is_identifier(""));
    assert_eq!(har::template_path("/api/tasks/101/comments"), "/api/tasks/{id}/comments");
    assert_eq!(har::template_path("/api/health"), "/api/health");
}

#[test]
fn json_shape_reads_object_keys_and_array_of_objects() {
    assert_eq!(har::json_shape(r#"{"b":1,"a":2}"#), vec!["a", "b"]);
    assert_eq!(har::json_shape(r#"[{"id":1,"title":"x"}]"#), vec!["[]id", "[]title"]);
    assert!(har::json_shape("<html>nie json</html>").is_empty());
}

fn entry(
    method: &str,
    url: &str,
    cookie: Option<&str>,
    status: i64,
    body: &str,
) -> serde_json::Value {
    let headers: Vec<serde_json::Value> = match cookie {
        Some(c) => vec![serde_json::json!({"name": "Cookie", "value": c})],
        None => vec![],
    };
    serde_json::json!({
        "request": {"method": method, "url": url, "headers": headers},
        "response": {
            "status": status,
            "headers": [],
            "content": {"mimeType": "application/json", "text": body}
        }
    })
}

fn har_of(entries: Vec<serde_json::Value>) -> har::Har {
    let doc = serde_json::json!({ "log": { "entries": entries } });
    har::parse(&doc.to_string()).expect("HAR testowy")
}

fn two_account_har() -> har::Har {
    let ok_a = r#"{"id":101,"title":"zadanie A","owner":"A"}"#;
    let ok_a2 = r#"{"id":102,"title":"inne zadanie","owner":"A"}"#;
    let admin = r#"{"users":[1,2,3]}"#;
    let public = r#"{"status":"ok"}"#;
    har_of(vec![
        entry("GET", HOST_TASKS_101, Some("sessionid=aaa"), 200, ok_a),
        entry("GET", HOST_TASKS_102, Some("sessionid=aaa"), 200, ok_a2),
        entry("GET", HOST_ADMIN, Some("sessionid=aaa"), 200, admin),
        entry("GET", HOST_TASKS_101, Some("sessionid=bbb"), 403, ""),
        entry("GET", HOST_ADMIN, Some("sessionid=bbb"), 403, ""),
        entry("GET", HOST_PUBLIC, None, 200, public),
        entry("GET", HOST_PUBLIC, Some("sessionid=aaa"), 200, public),
        entry("GET", HOST_EXPORT, Some("sessionid=aaa"), 200, ""),
    ])
}

const HOST_TASKS_101: &str = "https://dataannotation.pllum.org.pl/api/tasks/101";
const HOST_TASKS_102: &str = "https://dataannotation.pllum.org.pl/api/tasks/102";
const HOST_ADMIN: &str = "https://dataannotation.pllum.org.pl/api/admin/users";
const HOST_PUBLIC: &str = "https://dataannotation.pllum.org.pl/api/public";
const HOST_EXPORT: &str = "https://dataannotation.pllum.org.pl/api/export?access_token=deadbeef";

#[test]
fn analysis_finds_every_hypothesis_class() {
    let accounts = vec![
        Account::parse("A:sessionid=aaa").unwrap(),
        Account::parse("B:sessionid=bbb").unwrap(),
    ];
    let report = analyze::analyze(&[("test.har".to_string(), two_account_har())], &accounts);

    assert_eq!(report.observations, 8);
    assert_eq!(report.accounts, vec!["A".to_string(), "B".to_string()]);

    let kinds: Vec<&str> = report.findings.iter().map(|f| f.kind.as_str()).collect();
    assert!(kinds.contains(&"permission_asymmetry"), "kinds = {kinds:?}");
    assert!(kinds.contains(&"idor_candidate"), "kinds = {kinds:?}");
    assert!(kinds.contains(&"unauth_access"), "kinds = {kinds:?}");
    assert!(kinds.contains(&"token_in_url"), "kinds = {kinds:?}");

    let idor = report
        .findings
        .iter()
        .find(|f| f.kind == Kind::IdorCandidate)
        .expect("IDOR-kandydat");
    assert_eq!(idor.template, "/api/tasks/{id}");
    assert!(idor.detail.contains("2 różnych"), "opis: {}", idor.detail);

    let asym = report
        .findings
        .iter()
        .find(|f| f.kind == Kind::PermissionAsymmetry)
        .expect("asymetria");
    assert_eq!(asym.template, "/api/admin/users");
}

#[test]
fn analysis_says_nothing_when_captures_are_clean() {
    let h = har_of(vec![
        entry("GET", "https://nask.pl/", None, 200, ""),
        entry("GET", "https://nask.pl/o-nas", None, 200, ""),
    ]);
    let report = analyze::analyze(&[("clean.har".to_string(), h)], &[]);
    assert!(report.findings.is_empty(), "findings: {:?}", report.findings);
    let md = analyze::render_markdown(&report);
    assert!(md.contains("Brak. To też wynik"), "raport: {md}");
}

#[test]
fn markdown_report_is_usable_and_carries_the_limits() {
    let accounts = vec![Account::parse("A:sessionid=aaa").unwrap()];
    let report = analyze::analyze(&[("t.har".to_string(), two_account_har())], &accounts);
    let md = analyze::render_markdown(&report);
    assert!(md.contains("Raport nasktriage"));
    assert!(md.contains("/api/tasks/{id}"));
    assert!(md.contains("nie wysyła żadnych żądań"), "musi nieść zastrzeżenie");
}

#[test]
fn account_spec_requires_colon() {
    assert!(Account::parse("A").is_err());
    assert!(Account::parse(":napis").is_err());
    assert!(Account::parse("A:sessionid=x").is_ok());
}

#[test]
fn secret_parameter_names_are_recognised() {
    for name in ["token", "access_token", "api_key", "apikey", "X-Amz-Signature", "session", "auth"] {
        assert!(analyze::looks_like_secret(name), "{name} powinno być rozpoznane");
    }
    for name in ["page", "limit", "q", "sort"] {
        assert!(!analyze::looks_like_secret(name), "{name} nie jest sekretem");
    }
}
