//! Globalny limiter: twardy sufit N żądań na sekundę, wspólny dla wszystkich wątków.
//!
//! Regulamin NASK §6 pkt 2: "maksymalna szybkość skanowania na poziomie 5 req/s".
//! Ten limiter jest CELOWO zachowawczy (domyślnie 4.5 req/s), żeby margines bezpieczeństwa
//! pokrył jitter sieci i retry. Nie należy go podnosić.

use std::sync::{Condvar, Mutex};
use std::time::{Duration, Instant};

pub struct RateLimiter {
    inner: Mutex<State>,
    cv: Condvar,
    min_gap: Duration,
}

struct State {
    next_ok: Instant,
    issued: u64,
}

impl RateLimiter {
    pub fn new(req_per_sec: f64) -> Self {
        assert!(req_per_sec > 0.0);
        Self {
            inner: Mutex::new(State {
                next_ok: Instant::now(),
                issued: 0,
            }),
            cv: Condvar::new(),
            min_gap: Duration::from_secs_f64(1.0 / req_per_sec),
        }
    }

    /// Blokuje wątek do momentu, aż może wysłać jedno żądanie.
    pub fn acquire(&self) {
        let mut st = self.inner.lock().unwrap();
        loop {
            let now = Instant::now();
            if now >= st.next_ok {
                st.next_ok = now + self.min_gap;
                st.issued += 1;
                return;
            }
            let wait = st.next_ok - now;
            let (guard, _) = self.cv.wait_timeout(st, wait).unwrap();
            st = guard;
        }
    }

    pub fn gap(&self) -> Duration {
        self.min_gap
    }

    pub fn issued(&self) -> u64 {
        self.inner.lock().unwrap().issued
    }
}
