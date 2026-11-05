//! Wspólny limiter tempa. Regulamin: **maks. 5 żądań/s** na wszystkie narzędzia razem.
//!
//! Świadomie nie da się go podnieść argumentem CLI: konstruktor odrzuca `rps > MAX_RPS`.
//! Zegar jest wstrzykiwany (`now_s`), więc test jest deterministyczny — bez `sleep`.

pub const MAX_RPS: f64 = 5.0;
/// Domyślnie pracujemy wolniej niż sufit: 1 żądanie/s łącznie.
pub const DEFAULT_RPS: f64 = 1.0;

#[derive(Debug, Clone)]
pub struct TokenBucket {
    rps: f64,
    capacity: f64,
    tokens: f64,
    last_s: f64,
}

impl TokenBucket {
    pub fn new(rps: f64) -> Result<TokenBucket, String> {
        if rps <= 0.0 || rps.is_nan() {
            return Err("rps musi być > 0".to_string());
        }
        if rps > MAX_RPS {
            return Err(format!(
                "rps {rps} przekracza regulaminowy sufit {MAX_RPS}/s — odmowa startu"
            ));
        }
        Ok(TokenBucket {
            rps,
            capacity: rps.max(1.0),
            tokens: rps.max(1.0),
            last_s: 0.0,
        })
    }

    pub fn rps(&self) -> f64 {
        self.rps
    }

    pub fn tokens(&self) -> f64 {
        self.tokens
    }

    fn refill(&mut self, now_s: f64) {
        let elapsed = (now_s - self.last_s).max(0.0);
        self.tokens = (self.tokens + elapsed * self.rps).min(self.capacity);
        self.last_s = self.last_s.max(now_s);
    }

    /// `true` = żądanie może iść teraz; `false` = trzeba czekać `delay_s`.
    pub fn try_acquire(&mut self, now_s: f64) -> bool {
        self.refill(now_s);
        if self.tokens >= 1.0 {
            self.tokens -= 1.0;
            true
        } else {
            false
        }
    }

    /// Ile sekund trzeba odczekać przed kolejnym żądaniem (0.0 = można teraz).
    pub fn delay_s(&mut self, now_s: f64) -> f64 {
        self.refill(now_s);
        if self.tokens >= 1.0 {
            0.0
        } else {
            (1.0 - self.tokens) / self.rps
        }
    }
}
