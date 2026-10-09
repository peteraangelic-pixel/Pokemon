//! Rownoleglosc: rayon (domyslnie, feature `rayon`) lub prosty pool watkow `std`.
//!
//! Kompilacja bez rayona: `cargo run --release --no-default-features`.

/// Mapuje `items` rownolegle przez `f`, zachowujac kolejnosc wynikow (rayon).
#[cfg(feature = "rayon")]
pub fn par_map<T, R, F>(items: Vec<T>, f: F) -> Vec<R>
where
    T: Send,
    R: Send,
    F: Fn(T) -> R + Sync + Send,
{
    use rayon::prelude::*;
    items.into_par_iter().map(f).collect()
}

/// Mapuje `items` rownolegle przez `f`, zachowujac kolejnosc wynikow (pool std).
#[cfg(not(feature = "rayon"))]
pub fn par_map<T, R, F>(items: Vec<T>, f: F) -> Vec<R>
where
    T: Send,
    R: Send,
    F: Fn(T) -> R + Sync + Send,
{
    std_pool::map(items, f)
}

/// Liczba watkow wykorzystywanych do rownoleglej pracy.
#[cfg(feature = "rayon")]
pub fn num_threads() -> usize {
    rayon::current_num_threads()
}

/// Liczba watkow wykorzystywanych do rownoleglej pracy (fallback std).
#[cfg(not(feature = "rayon"))]
pub fn num_threads() -> usize {
    std::thread::available_parallelism()
        .map(|v| v.get())
        .unwrap_or(4)
}

/// Nazwa aktywnego backendu rownoleglego.
#[cfg(feature = "rayon")]
pub fn backend_name() -> &'static str {
    "rayon"
}

/// Nazwa aktywnego backendu rownoleglego (fallback std).
#[cfg(not(feature = "rayon"))]
pub fn backend_name() -> &'static str {
    "std-threads"
}

#[cfg(not(feature = "rayon"))]
mod std_pool {
    use std::thread;

    /// Prosty pool: dzieli prace na kawalki i rozsyła po watkach (zakresowych).
    pub fn map<T, R, F>(items: Vec<T>, f: F) -> Vec<R>
    where
        T: Send,
        R: Send,
        F: Fn(T) -> R + Sync,
    {
        let n = thread::available_parallelism()
            .map(|v| v.get())
            .unwrap_or(4);
        let n = n.max(1).min(items.len().max(1));
        let chunk = items.len().div_ceil(n);
        let mut rest = items;
        let mut chunks: Vec<Vec<T>> = Vec::new();
        while !rest.is_empty() {
            let take = chunk.min(rest.len());
            let tail = rest.split_off(take);
            chunks.push(rest);
            rest = tail;
        }
        let f = &f;
        let mut out: Vec<R> = Vec::new();
        thread::scope(|s| {
            let handles: Vec<_> = chunks
                .into_iter()
                .map(|c| s.spawn(move || c.into_iter().map(f).collect::<Vec<R>>()))
                .collect();
            for h in handles {
                out.extend(h.join().expect("watek poolu std paniknal"));
            }
        });
        out
    }
}
