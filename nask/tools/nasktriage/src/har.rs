//! Minimalny czytnik HAR (format „Save all as HAR with content” z DevTools).
//!
//! Czytamy tylko to, co potrzebne do analizy uprawnień: metoda, URL, nagłówki, status,
//! typ treści i **kształt** odpowiedzi (zbiór kluczy JSON), a nie jej treść. Treści nie
//! zapisujemy nigdzie — narzędzie ma nie utrwalać danych osobowych.

use serde::Deserialize;

#[derive(Debug, Deserialize)]
pub struct Har {
    pub log: Log,
}

#[derive(Debug, Deserialize, Default)]
#[serde(default)]
pub struct Log {
    pub entries: Vec<Entry>,
}

#[derive(Debug, Deserialize, Default, Clone)]
#[serde(default)]
pub struct Entry {
    pub request: Request,
    pub response: Response,
}

#[derive(Debug, Deserialize, Default, Clone)]
#[serde(default)]
pub struct Request {
    pub method: String,
    pub url: String,
    pub headers: Vec<NameValue>,
}

#[derive(Debug, Deserialize, Default, Clone)]
#[serde(default)]
pub struct Response {
    pub status: i64,
    pub headers: Vec<NameValue>,
    pub content: Content,
}

#[derive(Debug, Deserialize, Default, Clone)]
#[serde(default)]
pub struct Content {
    #[serde(rename = "mimeType")]
    pub mime_type: String,
    pub size: Option<i64>,
    pub text: Option<String>,
}

#[derive(Debug, Deserialize, Default, Clone)]
#[serde(default)]
pub struct NameValue {
    pub name: String,
    pub value: String,
}

impl Entry {
    pub fn header<'a>(&'a self, wanted: &str) -> Option<&'a str> {
        self.request
            .headers
            .iter()
            .find(|h| h.name.eq_ignore_ascii_case(wanted))
            .map(|h| h.value.as_str())
    }

    pub fn response_header<'a>(&'a self, wanted: &str) -> Option<&'a str> {
        self.response
            .headers
            .iter()
            .find(|h| h.name.eq_ignore_ascii_case(wanted))
            .map(|h| h.value.as_str())
    }

    pub fn cookie(&self) -> Option<&str> {
        self.header("cookie")
    }
}

pub fn parse(json: &str) -> Result<Har, String> {
    serde_json::from_str::<Har>(json).map_err(|e| format!("HAR nie jest poprawny: {e}"))
}

/// Czy segment ścieżki jest identyfikatorem (liczbowym, UUID, długim hexem, długim tokenem)?
pub fn is_identifier(segment: &str) -> bool {
    if segment.is_empty() {
        return false;
    }
    if segment.chars().all(|c| c.is_ascii_digit()) {
        return true;
    }
    // UUID w dowolnej formie (8-4-4-4-12 lub bez myślników)
    let compact: String = segment.chars().filter(|c| *c != '-').collect();
    if compact.len() == 32 && compact.chars().all(|c| c.is_ascii_hexdigit()) {
        return true;
    }
    if segment.len() >= 16 && segment.len() <= 64 && segment.chars().all(|c| c.is_ascii_hexdigit()) {
        return true;
    }
    // długi token mieszany (np. slug+hash, base64url)
    if segment.len() >= 20
        && segment
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || c == '_' || c == '-')
    {
        return true;
    }
    false
}

/// Ścieżka z podstawionymi identyfikatorami: `/api/tasks/101` → `/api/tasks/{id}`.
pub fn template_path(path: &str) -> String {
    let segments: Vec<String> = path
        .split('/')
        .map(|s| {
            if is_identifier(s) {
                "{id}".to_string()
            } else {
                s.to_string()
            }
        })
        .collect();
    segments.join("/")
}

/// Zbiór kluczy JSON (posortowany) albo pusty, gdy treść nie jest JSON-em.
/// Dla tablicy obiektów bierzemy klucze pierwszego elementu z prefiksem `[]`.
pub fn json_shape(text: &str) -> Vec<String> {
    let value: serde_json::Value = match serde_json::from_str(text) {
        Ok(v) => v,
        Err(_) => return Vec::new(),
    };
    let mut keys: Vec<String> = match &value {
        serde_json::Value::Object(map) => map.keys().cloned().collect(),
        serde_json::Value::Array(items) => match items.first() {
            Some(serde_json::Value::Object(map)) => {
                map.keys().map(|k| format!("[]{k}")).collect()
            }
            _ => Vec::new(),
        },
        _ => Vec::new(),
    };
    keys.sort();
    keys
}

pub fn body_len(entry: &Entry) -> usize {
    match (&entry.response.content.text, entry.response.content.size) {
        (Some(t), _) => t.len(),
        (None, Some(s)) => s as usize,
        _ => 0,
    }
}
