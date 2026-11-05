//! `nasktriage` — offline'owa analiza zrzutów HAR z dwóch własnych kont.
//!
//! Trzy moduły, każdy z jednym zadaniem:
//! * [`scope`] — dokładna lista hostów programu; host spoza listy nie jest testowany,
//! * [`rate`] — wspólny limiter ≤ 5 żądań/s; nie da się go podnieść argumentem,
//! * [`har`] i [`analyze`] — czytanie zrzutów i wskazywanie **hipotez** do ręcznego potwierdzenia.
//!
//! Biblioteka **nie wykonuje żadnych żądań sieciowych**. To decyzja projektowa: aktywne
//! testy podatności muszą być świadome i pojedyncze, nie ukryte w pętli narzędzia.

pub mod analyze;
pub mod har;
pub mod rate;
pub mod scope;

/// Wersja i jednolinijkowy opis — używane przez `--version` i dokumentację.
pub const ABOUT: &str =
    "nasktriage: offline HAR access-control triage for hack.cert.pl programs (no network)";
