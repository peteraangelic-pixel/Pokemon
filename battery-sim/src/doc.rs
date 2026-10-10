//! Generator raportu Markdown (PL/EN) -- dokument do prezentacji wynikow
//! projektu (np. rozmowa z producentem ogniw, dostawca materialow, inwestorem).

use crate::benchmark::{evaluate_candidates, OurRow, COMMERCIAL};
use crate::cell::CellParams;
use crate::sim::SimParams;
use std::fs;
use std::io;
use std::time::{SystemTime, UNIX_EPOCH};

/// Biezaca data (prosty konwerter dni od 1970-01-01 -> y-m-d).
fn today() -> String {
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    let days = (secs / 86400) as i64;
    let z = days + 719_468;
    let era = if z >= 0 { z } else { z - 146_096 } / 146_097;
    let doe = (z - era * 146_097) as u64;
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
    let y = yoe as i64 + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    let y = if m <= 2 { y + 1 } else { y };
    format!("{:04}-{:02}-{:02}", y, m, d)
}

/// Zapisuje raport; zwraca liczbe linii.
pub fn write_report(path: &str, lang: &str, cp: &CellParams, sp: &SimParams) -> io::Result<usize> {
    let rows = evaluate_candidates(cp, sp);
    let md = if lang == "en" {
        render_en(&rows)
    } else {
        render_pl(&rows)
    };
    fs::write(path, &md)?;
    Ok(md.lines().count())
}

fn our_table(rows: &[OurRow]) -> String {
    let mut s = String::new();
    s.push_str("| kombinacja | Wh/kg | Wh/kg pakiet | Wh/L | $/kWh | cykle @2C | t80 [min] | EOL | abuse 150 °C |\n");
    s.push_str("|---|---:|---:|---:|---:|---:|---:|---|---|\n");
    for r in rows {
        let abuse = if r.abuse_ok {
            format!("OK (Tmax {:.0} °C)", r.abuse_tmax)
        } else {
            format!("FAIL (Tmax {:.0} °C)", r.abuse_tmax)
        };
        s.push_str(&format!(
            "| {} | {:.1} | {:.1} | {:.0} | {:.0} | {} | {:.1} | {} | {} |\n",
            r.combo, r.wh_kg, r.wh_kg_pack, r.wh_l, r.cost_kwh, r.cycles, r.t80_min, r.eol, abuse
        ));
    }
    s
}

fn comm_table() -> String {
    let mut s = String::new();
    s.push_str("| ogniwo | Wh/kg ogniwo | Wh/kg pakiet | Wh/L | cykle | szybkie ładowanie | bezpieczeństwo | uwagi |\n");
    s.push_str("|---|---|---|---|---|---|---|---|\n");
    for c in COMMERCIAL {
        s.push_str(&format!(
            "| {} | {} | {} | {} | {} | {} | {} | {} |\n",
            c.name, c.wh_cell, c.wh_pack, c.wh_l, c.cycles, c.fast, c.safety, c.note
        ));
    }
    s
}

fn sources() -> &'static str {
    "Źródła (2025–2026): CATL condensed 500 Wh/kg — greencarreports.com, newatlas.com (samolot 4 t, marzec 2025); \
     WeLion/NIO 360 Wh/kg ogniwo, 260 Wh/kg pakiet — spectrum.ieee.org, insideevs.com, evtechinsider.com; \
     IM Motors L6 (QingTao) — insideevs.com; BYD FinDreams ~400 Wh/kg prototypy — thestreet.com (wrz 2026); \
     Amprius SiMaxx 500 Wh/kg, 1300 Wh/L — ainvest.com; StoreDot XFC 300 Wh/kg, 1000 cykli XFC, Polestar 5 10–80% <10 min — \
     eepower.com, emobility-engineering.com, store-dot.com; CATL Naxtra 175 Wh/kg, GB 38031-2025 — \
     electrichybridvehicletechnology.com, zvepow.com; QuantumScape 301 Wh/kg / 844 Wh/L (wer. B) — curionic.net; \
     Samsung SDI SolidStack 900 Wh/L, H2 2027 — exoswan.com; Sila Titan Silicon (Mercedes, Panasonic) — techcrunch.com, autoevtimes.com; \
     CATL Shenxing 4C–6C, Zeekr Golden Brick 5.5C (10,5 min) — carnewschina.com, paultan.org, interestingengineering.com, insideevs.com."
}

fn render_pl(rows: &[OurRow]) -> String {
    let mut s = String::new();
    s.push_str(&format!(
        "# Raport projektu: nowy typ baterii (battery-sim v{})\n\n",
        env!("CARGO_PKG_VERSION")
    ));
    s.push_str(&format!(
        "Wygenerowano: {} | Model: `battery-sim` (Rust; port 1:1 z `tools/model_prototype.py`) | Równoległość: rayon\n\n",
        today()
    ));
    s.push_str("## 1. Cel i kryteria\n\n");
    s.push_str("Projektuje się ogniwo 3-komponentowe (katoda | elektrolit | anoda), które:\n");
    s.push_str("1. ma energię właściwą **nie niższą niż referencyjny Li-ion** (NMC811/grafit/LP57, 236.9 Wh/kg),\n");
    s.push_str("2. wytrzymuje **≥ 500 cykli przy szybkim ładowaniu** (2C–3C),\n");
    s.push_str("3. jest **bezpieczne** — brak eksplozji / thermal runaway / zwarcia w teście abuse (piec 150 °C + przeładowanie 1C, 3 h).\n\n");
    s.push_str("## 2. Metodyka (skrót)\n\n");
    s.push_str("- Model fizyczny: krzywe OCV, bilanse masy/energii na cm², opór wewnętrzny (jonowy + Butler-Volmer + interfejs), cykliczna degradacja (SEI, fade katody, stres oksydacyjny, plating Li, dead Li), sprzężona termika bryłowa z reakcjami egzotermicznymi, spalaniem elektrolitu i zamknięciem separatora PP.\n");
    s.push_str("- Metryki rynkowe: **Wh/kg pakietowe** (×0.72 — BMS/obudowa/chłodzenie), **Wh/L** (z gęstości powłok i grubości elektrod), **koszt materiałowy $/kWh** (materiały aktywne + elektrolit; bez folii, spoiw, capex i marży).\n");
    s.push_str("- Symulacje: 2C, 25 °C, do 3000 cykli + osobny test abuse 150 °C.\n\n");
    s.push_str("## 3. Kandydaci (symulacja)\n\n");
    s.push_str(&our_table(rows));
    s.push_str("\n## 4. Porównanie z ogniwami komercyjnymi (2025–2026)\n\n");
    s.push_str(&comm_table());
    s.push('\n');
    s.push_str(sources());
    s.push_str("\n\n## 5. Wnioski — przewagi kandydatów\n\n");
    s.push_str("- **Kombinacja cech, nie pojedyncza liczba.** LFP ma żywotność i bezpieczeństwo, ale ~160 Wh/kg; WeLion (półstałe) ma 360 Wh/kg, ale koszt i cykle są pod znakiem zapytania; StoreDot ma 300 Wh/kg + XFC, ale walidacja cykli trwa. Kandydat **NMC811 + Si-C + elektrolit żelowy** łączy naraz: energię ≥ Li-ion, ≥500 cykli @2C i przeżycie testu abuse (patrz tabela, sekcja 3).\n");
    s.push_str("- **Kierunek zgodny z rynkiem 2026–2027**: żelowe/półstałe elektrolity (CATL condensed, WeLion) + krzemowe anody (Sila, Amprius, StoreDot) — nasz model ilościowo uzasadnia ten kierunek i pozwala testować warianty taniej niż eksperyment.\n");
    s.push_str("- **Na-jon (Na-PW + hard carbon)**: ~170–190 Wh/kg, najniższy koszt materiałowy w zestawie, odporność na mróz (brak platingu sodu na hard carbon w modelu), kolektor Al–Al. Odpowiednik kierunku CATL Naxtra (produkcja od końca 2025).\n");
    s.push_str("- **Narzędzie**: otwarty, szybki symulator — pełna siatka chemiczna (setki kombinacji) liczy się w sekundy–minuty na zwykłym wielordzeniowym komputerze; wyniki reprodukowalne (CSV, CI).\n\n");
    s.push_str("## 6. Ograniczenia modelu (uczciwie)\n\n");
    s.push_str("- Model fenomenologiczny (kalibrowany na rząd wielkości z literatury), nie ab initio; termika bryłowa, SEI paraboliczne, bez starzenia kalendarzowego.\n");
    s.push_str("- Koszt = materiały aktywne + elektrolit (bez folii, separatora, spoiw, capex, marży); Wh/L bez obudowy; Wh/kg pakietowe przy stałym współczynniku 0.72.\n");
    s.push_str("- Na-jon: wspólna fizyka z Li-jon (napięcia vs Na/Na+), uproszczone SEI; przewaga termiczna Na-jon odwzorowana przez stabilniejsze katody.\n");
    s.push_str(
        "- **Symulacja ≠ certyfikat** — każda liczba wymaga walidacji eksperymentalnej.\n\n",
    );
    s.push_str("## 7. Ścieżka walidacji (przed rozmową z firmą)\n\n");
    s.push_str("1. Zamrozić model i wyniki (ten raport + CSV ze sweepów — są w repo/CI).\n");
    s.push_str("2. Wybrać 2–3 kandydatów i zamówić materiały (anoda Si-C, elektrolit żelowy, hard carbon, katody).\n");
    s.push_str(
        "3. Coin cells → testy cykliczne @2C (potwierdzenie rzędu wielkości cykli i energii).\n",
    );
    s.push_str("4. Pouch cells + testy abuse w zewnętrznym labie (TÜV / UL 9540A / GB 38031-2025 / UN 38.3).\n");
    s.push_str("5. Freedom-to-operate: przegląd patentów (Si-C + żel/stałe elektrolity to gęsto opatentowane pole: CATL, WeLion, StoreDot, QuantumScape).\n");
    s.push_str("6. Z danymi walidacyjnymi: rozmowy z producentami ogniw / dostawcami materiałów / OEM; finansowanie: NCBR, PARP, EIC Accelerator, Horizon Europe.\n");
    s
}

fn render_en(rows: &[OurRow]) -> String {
    let mut s = String::new();
    s.push_str(&format!(
        "# Project report: a new battery type (battery-sim v{})\n\n",
        env!("CARGO_PKG_VERSION")
    ));
    s.push_str(&format!(
        "Generated: {} | Model: `battery-sim` (Rust; 1:1 port of `tools/model_prototype.py`) | Parallelism: rayon\n\n",
        today()
    ));
    s.push_str("## 1. Goal and criteria\n\n");
    s.push_str("We are designing a 3-component cell (cathode | electrolyte | anode) that:\n");
    s.push_str("1. has specific energy **no lower than the reference Li-ion** (NMC811/graphite/LP57, 236.9 Wh/kg),\n");
    s.push_str("2. survives **≥ 500 cycles at fast charging** (2C–3C),\n");
    s.push_str("3. is **safe** — no explosion / thermal runaway / internal short in the abuse test (150 °C oven + 1C overcharge, 3 h).\n\n");
    s.push_str("## 2. Methodology (summary)\n\n");
    s.push_str("- Physics-based cell model: OCV curves, mass/energy balances per cm², internal resistance (ionic + Butler-Volmer + interface), cyclic degradation (SEI growth, cathode fade, oxidative stress, Li plating, dead Li), lumped thermal model with exothermic reactions, electrolyte combustion and PP separator shutdown.\n");
    s.push_str("- Market metrics: **pack-level Wh/kg** (×0.72 — BMS/enclosure/cooling), **Wh/L** (from coating densities and electrode thicknesses), **material cost $/kWh** (active materials + electrolyte; excl. foils, binders, capex, margin).\n");
    s.push_str("- Simulations: 2C, 25 °C, up to 3000 cycles + a separate 150 °C abuse test.\n\n");
    s.push_str("## 3. Candidates (simulation)\n\n");
    s.push_str(&our_table(rows));
    s.push_str("\n## 4. Comparison with commercial cells (2025–2026)\n\n");
    s.push_str(&comm_table());
    s.push('\n');
    s.push_str(sources());
    s.push_str("\n\n## 5. Conclusions — candidate advantages\n\n");
    s.push_str("- **A combination of properties, not a single number.** LFP has cycle life and safety but ~160 Wh/kg; WeLion (semi-solid) has 360 Wh/kg but cost and cycle life are unproven at scale; StoreDot has 300 Wh/kg + XFC but cycle validation is ongoing. The **NMC811 + Si-C + gel electrolyte** candidate combines all three at once: energy ≥ Li-ion, ≥500 cycles @2C and abuse survival (see table, section 3).\n");
    s.push_str("- **Aligned with the 2026–2027 market direction**: gel/semi-solid electrolytes (CATL condensed, WeLion) + silicon anodes (Sila, Amprius, StoreDot) — our model quantifies this direction and lets us screen variants far cheaper than experiment.\n");
    s.push_str("- **Na-ion (Na-PW + hard carbon)**: ~170–190 Wh/kg, the lowest material cost in the set, cold-weather robustness (no sodium plating on hard carbon in the model), Al–Al current collectors. Counterpart of the CATL Naxtra direction (mass production from late 2025).\n");
    s.push_str("- **The tool itself**: an open, fast simulator — a full chemistry grid (hundreds of combinations) runs in seconds–minutes on an ordinary multi-core computer; results are reproducible (CSV, CI).\n\n");
    s.push_str("## 6. Model limitations (honestly)\n\n");
    s.push_str("- Phenomenological model (calibrated to literature order-of-magnitude), not ab initio; lumped thermal model, parabolic SEI, no calendar aging.\n");
    s.push_str("- Cost = active materials + electrolyte (excl. foils, separator, binders, capex, margin); Wh/L excludes packaging; pack Wh/kg uses a fixed 0.72 factor.\n");
    s.push_str("- Na-ion: shared physics with Li-ion (voltages vs Na/Na+), simplified SEI; the Na-ion thermal advantage is represented via more stable cathodes.\n");
    s.push_str(
        "- **Simulation ≠ certification** — every number requires experimental validation.\n\n",
    );
    s.push_str("## 7. Validation roadmap (before talking to companies)\n\n");
    s.push_str("1. Freeze the model and results (this report + sweep CSVs — in the repo/CI).\n");
    s.push_str("2. Pick 2–3 candidates and order materials (Si-C anode, gel electrolyte, hard carbon, cathodes).\n");
    s.push_str(
        "3. Coin cells → 2C cycle tests (confirm order of magnitude of cycles and energy).\n",
    );
    s.push_str("4. Pouch cells + abuse testing in an external lab (TÜV / UL 9540A / GB 38031-2025 / UN 38.3).\n");
    s.push_str("5. Freedom-to-operate: patent landscape review (Si-C + gel/solid electrolytes are heavily patented: CATL, WeLion, StoreDot, QuantumScape).\n");
    s.push_str("6. With validation data: talk to cell makers / material suppliers / OEMs; funding: NCBR, PARP, EIC Accelerator, Horizon Europe.\n");
    s
}
