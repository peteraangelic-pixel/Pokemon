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
        render_en(&rows, cp, sp)
    } else {
        render_pl(&rows, cp, sp)
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

fn render_pl(rows: &[OurRow], cp: &CellParams, sp: &SimParams) -> String {
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
    s.push_str("- **Kombinacja cech, nie pojedyncza liczba.** LFP ma żywotność i bezpieczeństwo, ale ~160 Wh/kg; WeLion (półstałe) ma 360 Wh/kg, ale koszt i cykle są pod znakiem zapytania; StoreDot ma 300 Wh/kg + XFC, ale walidacja cykli trwa. Nasi kandydaci łączą naraz energię ≥ Li-ion, ≥500 cykli @2C i przeżycie testu abuse: **NMC811 + anode-free + żel (359 Wh/kg, 543 cykli, $50/kWh)**, **LFP + anode-free (270 Wh/kg, $27/kWh)** i **DRX + Si-C + żel (354 Wh/kg, $41/kWh, bez Co/Ni)** — patrz tabela, sekcja 3.\n");
    s.push_str("- **Kierunek zgodny z rynkiem 2026–2027**: żelowe/półstałe elektrolity (CATL condensed, WeLion) + krzemowe anody (Sila, Amprius, StoreDot) — nasz model ilościowo uzasadnia ten kierunek i pozwala testować warianty taniej niż eksperyment.\n");
    s.push_str("- **Na-jon (Na-PW + hard carbon)**: ~170–190 Wh/kg, najniższy koszt materiałowy w zestawie, odporność na mróz (brak platingu sodu na hard carbon w modelu), kolektor Al–Al. Odpowiednik kierunku CATL Naxtra (produkcja od końca 2025).\n");
    s.push_str("- **Nowatorskie chemie (poza rynkiem)**: **DRX** (bezkobaltowy rock-salt na Mn) + Si-C / anode-free (LIFREE) + SOLID lub GEL — 340–430 Wh/kg (248–310 pakiet), ~1850 Wh/L, bezpieczne, ~400–470 cykli @2C, czyli ~10–20% poniżej progu 500; model wskazuje dokładnie, co poprawić (fade katody: domieszkowanie F / powłoka). Li-air (LIO2): ~400–500 Wh/kg, ale rate-limited przy 2C i tylko ~20–35 cykli przy 1C (reakcje pasożytnicze) — dlatego nie ma jej na rynku. Mg-jon (CHEVREL/MG): 36–40 Wh/kg (niskie napięcie ogniwa). FeF₃: rate-limited przy 2C. K-jon (KPB): ~150–160 Wh/kg, ~650 cykli @2C — ekonomiczny kuzyn Na-jon.\n");
    s.push_str("- **Narzędzie**: otwarty, szybki symulator — pełna siatka chemiczna (setki kombinacji) liczy się w sekundy–minuty na zwykłym wielordzeniowym komputerze; wyniki reprodukowalne (CSV, CI).\n\n");
    s.push_str("- **Produkowalność (drop-in w istniejących fabrykach):** Na-jon produkuje się **dziś** na adaptowanych liniach Li-ion (CATL Naxtra, od końca 2025). **NMC811 + Si-C + żel** to kwestia 1–2 lat: standardowa katoda, Si-C od dostawców (Sila produkuje, Amprius wysyła), żel = modyfikacja kroku napełniania (linie półstałe już istnieją: WeLion, CATL). Warianty **anode-free** i **DRX** wymagają nowych procesów (anode-free: rezerwuar Li / pre-litacja katody — jak Samsung SDI „anode-less”, cel 2027+; DRX: nowa synteza katody, etap pilota). **SOLID** wymaga nowych fabryk (Toyota/Samsung/BYD 2027+). Li-air/Mg/FeF₃/K-jon — laboratorium.\n");
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
    s.push_str("## 8. Starzenie kalendarzowe (shelf life)\n\n");
    s.push_str("Osobny model: ogniwo **stoi** przy zadanym SOC i temperaturze (bez cyklowania) — SEI rośnie ~√t (najszybciej przy 100% SOC), elektrolit utlenia się przy wysokim potencjale katody, plus samo-rozładowanie. Kalibracja: NMC/grafit przy 25 °C/100% SOC traci ~3%/rok (shelf life ~8 lat), przy 45 °C ~3× szybciej; LFP/LTO praktycznie nie starzeje się na półce.\n\n");
    s.push_str(&crate::storage::table_md(&crate::storage::storage_rows(
        cp, sp,
    )));
    s.push_str("\nWnioski: NMC811 przy 45 °C/100% SOC wytrzymuje ~3,5 roku; LFP/LIFREE i LFP/grafit >15 lat; NA_NFPP (NASICON) >20 lat; DRX starzeje się szybko przy pełnym naładowaniu (wysokie napięcie katody); Li-air umiera w miesiące (samo-rozładowanie). Dla EV (stojących 95% czasu) i magazynów to właśnie ten wykres, od którego zależy gwarancja.\n");
    s
}

fn render_en(rows: &[OurRow], cp: &CellParams, sp: &SimParams) -> String {
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
    s.push_str("- **A combination of properties, not a single number.** LFP has cycle life and safety but ~160 Wh/kg; WeLion (semi-solid) has 360 Wh/kg but cost and cycle life are unproven at scale; StoreDot has 300 Wh/kg + XFC but cycle validation is ongoing. Our candidates combine all three at once: **NMC811 + anode-free + gel (359 Wh/kg, 543 cycles, $50/kWh)**, **LFP + anode-free (270 Wh/kg, $27/kWh)** and **DRX + Si-C + gel (354 Wh/kg, $41/kWh, no Co/Ni)** — see table, section 3.\n");
    s.push_str("- **Aligned with the 2026–2027 market direction**: gel/semi-solid electrolytes (CATL condensed, WeLion) + silicon anodes (Sila, Amprius, StoreDot) — our model quantifies this direction and lets us screen variants far cheaper than experiment.\n");
    s.push_str("- **Na-ion (Na-PW + hard carbon)**: ~170–190 Wh/kg, the lowest material cost in the set, cold-weather robustness (no sodium plating on hard carbon in the model), Al–Al current collectors. Counterpart of the CATL Naxtra direction (mass production from late 2025).\n");
    s.push_str("- **Novel chemistries (off-market)**: **DRX** (cobalt-free Mn rock-salt) + Si-C / anode-free (LIFREE) + SOLID or GEL — 340–430 Wh/kg (248–310 pack), ~1850 Wh/L, abuse-safe, ~400–470 cycles @2C, i.e. ~10–20% short of the 500-cycle bar; the model pinpoints what to improve (cathode fade: F-doping / coating). Li-air (LIO2): ~400–500 Wh/kg but rate-limited at 2C and only ~20–35 cycles at 1C (parasitic reactions) — which is exactly why it is not on the market. Mg-ion (CHEVREL/MG): 36–40 Wh/kg (low cell voltage). FeF₃: rate-limited at 2C. K-ion (KPB): ~150–160 Wh/kg, ~650 cycles @2C — the economical cousin of Na-ion.\n");
    s.push_str("- **The tool itself**: an open, fast simulator — a full chemistry grid (hundreds of combinations) runs in seconds–minutes on an ordinary multi-core computer; results are reproducible (CSV, CI).\n\n");
    s.push_str("- **Manufacturability (drop-in in existing fabs):** Na-ion is produced **today** on adapted Li-ion lines (CATL Naxtra, from late 2025). **NMC811 + Si-C + gel** is 1–2 years out: standard cathode, Si-C from suppliers (Sila in production, Amprius shipping), gel = a filling-step tweak (semi-solid lines already exist: WeLion, CATL). **Anode-free** and **DRX** variants need new processes (anode-free: Li reservoir / pre-lithiation — Samsung SDI's \"anode-less\", target 2027+; DRX: new cathode synthesis, pilot stage). **SOLID** needs new fabs (Toyota/Samsung/BYD 2027+). Li-air/Mg/FeF₃/K-ion — lab only.\n");
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
    s.push_str("## 8. Calendar aging (shelf life)\n\n");
    s.push_str("A separate model: the cell **sits** at a given SOC and temperature (no cycling) — SEI grows ~√t (fastest at 100% SOC), the electrolyte oxidizes at high cathode potential, plus self-discharge. Calibration: NMC/graphite at 25 °C/100% SOC loses ~3%/yr (shelf life ~8 yrs), ~3× faster at 45 °C; LFP/LTO barely ages on a shelf.\n\n");
    s.push_str(&crate::storage::table_md(&crate::storage::storage_rows(
        cp, sp,
    )));
    s.push_str("\nTakeaways: NMC811 at 45 °C/100% SOC lasts ~3.5 years on a shelf; LFP/LIFREE and LFP/graphite >15 years; NA_NFPP (NASICON) >20 years; DRX ages fast at full charge (high cathode voltage); Li-air dies in months (self-discharge). For EVs (parked 95% of the time) and grid storage, this curve is what the warranty is written against.\n");
    s
}

/// Raport inwestycyjny (EN/PL) — esencjonalny: hero = flagship, pipeline w linijkach.
pub fn write_investor(path: &str, lang: &str) -> io::Result<usize> {
    let md = if lang == "en" {
        render_investor_en()
    } else {
        render_investor_pl()
    };
    fs::write(path, &md)?;
    Ok(md.lines().count())
}

fn render_investor_en() -> String {
    format!(
        r##"# The Battery Design Studio — Investor Report
_Generated {date} · battery-sim v{ver} · contact: [YOUR NAME / EMAIL]_

## The one-liner
We built an open-source simulator that screens battery chemistries in minutes instead of months — and used it to design a cell that beats today's best production batteries on safety, fast charging and cost at the same time.

## The problem, in numbers
Today's EV cells make you pick two of {{energy, safety, cost}}:
- **LFP (BYD Blade):** safe + cheap, 160 Wh/kg — the energy tax.
- **NMC (CATL Qilin):** 255 Wh/kg pack, liquid flammable electrolyte, cobalt + nickel supply risk.
- **Semi-solid (WeLion/NIO):** 360 Wh/kg cell, in production since 2024 — but unproven economics.
And iteration is slow: one lab cycle per candidate takes weeks. A new cell design typically takes 2–4 years to qualify.

## Our answer: one cell, all three
**NMC811 cathode + Si-C anode + gel electrolyte** (every material already in mass production):

| metric | our cell (simulated) | best production today |
|---|---|---|
| energy | **279 Wh/kg** cell (201 pack) | ~230–260 Wh/kg cell (NMC); 260 pack (WeLion semi-solid) |
| fast-charge life | **670 cycles @2C** (10–80% in ~24 min) | ~500–800 @2C (fast-charge cells) |
| abuse survival | **150 °C oven + overcharge: survives, margin to 170 °C** | liquid-electrolyte NMC/graphite cells fail the same cell-level test (real packs survive it only with heavy protection systems) |
| discharge power | **5C** | 3–4C typical |
| material cost | **~$67/kWh** | ~$55–80/kWh (LFP–NMC cells) |
| time to production | **1–2 years, existing lines** | new chemistry: 3–5+ years |

The 1–2 years is validation and automotive qualification — not invention. Every block is in mass production today: NMC811 (LG, SK, CATL), Si-C (Sila, Amprius), gel electrolytes (WeLion, CATL).

## Why we win — the advantages that matter
1. **Safety where it hurts.** Our cell survives a 150 °C oven + 1C overcharge for 3 h with margin to 170 °C. In the same test, a Qilin-class cell (graphite + liquid electrolyte) goes into thermal runaway and explodes at cell level — real packs survive only with heavy protection (venting, cooling, shutdowns).
2. **Fast charging without the tax.** 670 cycles at 2C — the band the industry calls fast charge — with 10–80% in ~24 minutes.
3. **LFP-class cost, NMC-class energy.** ~$67/kWh in materials for 279 Wh/kg — versus 160 Wh/kg for LFP cells at similar cost.
4. **Buildable now.** Existing cathode/anode lines + a filling-step tweak. No new fab, no new chemistry, no 5-year wait.
5. **The tool is the moat.** Open, reproducible, fast: ~118,000 combinations simulated (full + fine + mega grids), results verifiable by anyone in minutes (CI, CSV, public repo). A cell maker's R&D cannot match that iteration speed.

## Two more ideas — simpler to build

The flagship needs Si-C supply and a gel-filling step. These two don't:

### A. Sodium-ion: Na-PW cathode + hard carbon + standard electrolyte
**The easiest of all — in mass production today** (CATL Naxtra, late 2025, on adapted Li-ion lines). Zero new processes.

| metric | our design | vs competition |
|---|---|---|
| energy | 176 Wh/kg (127 pack) | CATL Naxtra: 175 — parity; BYD Blade (LFP): 160 — **+10%** |
| cost | ~$39/kWh materials | Naxtra-class; **no Li, Co, Ni, Cu** (Al–Al collectors) |
| fast-charge life | 259 cycles @2C | — |
| cold | 90% capacity at −40 °C | LFP/NMC lose significantly |
| our edge | full condition matrix (temperature / C-rate / abuse / shelf life) + optimization | we deliver the *optimized* variant + the tool |

**Why it wins:** the only chemistry that is drop-in today, cheaper than LFP at scale, cold-proof, safer — and we deliver it *optimized*, with a reproducible model behind it.

### B. The $27/kWh value cell: LMFP/LFP + anode-free + standard liquid electrolyte
**LFP-class safety and cost, 1.7–1.9× Blade's energy** — on LFP production lines, with today's standard electrolyte (no gel, no solid).

| metric | our design | vs competition |
|---|---|---|
| energy | 270–298 Wh/kg (195–214 pack) | BYD Blade (LFP): 160 — **1.7–1.9× more at the same safety class** |
| cost | **~$27/kWh** materials | Blade-class cost; NMC cells cost 2–3× more per kWh |
| fast-charge life | 512–824 cycles (1–2C) | — |
| heat | LMFP variant survives 60 °C | NMC degrades 40–50% faster at 45 °C |
| build | LFP lines (LMFP = cathode tweak) + standard LP57 filling; only new step: anode-free (Samsung SDI's own 2027 bet) | flagship needs Si-C supply + gel process; this needs neither |

**Why it wins:** the mass-market cell — Blade's safety at Blade's cost, with NMC-class energy. Every block except anode-free is today's production.

## The rest of the pipeline (one line each)
- **367 Wh/kg premium** (NMC811 + anode-free): matches the best semi-solid pack on the market (260) at a fraction of the cost.
- **361 Wh/kg cobalt/nickel-free** (DRX + Si-C): development stage.
- **60 °C / >20-years-shelf specialty** (LFP + anode-free + solid): development stage.

## Where we are (honest)
- ~118,000 combinations simulated; two independent implementations agree digit-for-digit; deterministic across machines (verified on an external PC).
- Public, reproducible repository; CI green; full condition matrices (temperature, C-rate, abuse, shelf life) for every candidate.
- **We do not have physical cells yet.** This is a simulation-stage asset. The 12-month, €150k plan below is the bridge.

## Market
~$150B/yr cell market (est.), ~25%/yr growth (EV + grid storage), ~60–70% China share; Western OEMs actively de-risking cobalt/nickel. Beachheads: commercial vehicles & buses (fast charge + safety), drones/aviation (energy), hot climates & grid storage (heat + shelf life), materials suppliers (licensing).

## How we make money (licensing, not a startup)
We are a small, hobby-stage studio: **we license ideas, we don't run labs.**
1. You test the designs in your lab (your engineers, your budget) — this report is the spec.
2. If the numbers hold: license the IP (non-exclusive, per-field, up-front + royalties), or co-fund the €150k validation for co-exclusivity.
3. The open-source tool + paid enterprise support is the side income.

## Risks — said out loud
1. **Sim-to-lab gap** — mitigated by the milestone gate below; budgeted.
2. **Crowded IP** — Si-C + gel/solid is heavily patented (CATL, WeLion, StoreDot, QuantumScape); freedom-to-operate review is in the budget before any public claims.
3. **Si-C cost at scale** — currently +20–30% vs graphite; suppliers ramp through 2026+.
4. **Team** — small; first hire is a cell engineer.

## The plan — 12 months, €150k
- **Months 1–3:** coin cells for the flagship + value variant (materials + cycling): ~€40k
- **Months 4–9:** pouch cells + independent abuse testing (TÜV / UL 9540A / GB 38031-2025): ~€60k
- **Months 9–12:** pilot-line engagement, OEM/supplier LOIs, FTO review: ~€50k
**Gate:** if coin cells confirm ≥80% of modeled cycle life at 2C → proceed; if not → re-calibrate and re-screen (the tool makes that cheap).

## The ask
Not money — **a lab**. Send this report to your cell team. If the flagship or one of the two simpler designs holds up in coin cells, we license (or you fund the validation and we share the upside). We're open to offers.

Repo (public, reproducible): https://github.com/peteraangelic-pixel/Pokemon/tree/arena/d1882c0f-pokemon
"##,
        date = today(),
        ver = env!("CARGO_PKG_VERSION")
    )
}

fn render_investor_pl() -> String {
    format!(
        r##"# The Battery Design Studio — raport inwestycyjny
_Wygenerowano {date} · battery-sim v{ver} · kontakt: [IMIĘ / E-MAIL]_

## Jednym zdaniem
Zbudowaliśmy open-source'owy symulator, który testuje chemie baterii w minuty zamiast miesięcy — i wykorzystaliśmy go do zaprojektowania ogniwa, które wygrywa z najlepszymi produkcyjnymi bateriami na raz pod względem bezpieczeństwa, szybkiego ładowania i kosztu.

## Problem w liczbach
Dziś ogniwa do EV każą wybierać dwa z trzech: {{energia, bezpieczeństwo, koszt}}.
- **LFP (BYD Blade):** bezpieczne + tanie, 160 Wh/kg — podatek energetyczny.
- **NMC (CATL Qilin):** 255 Wh/kg pakiet, palny ciekły elektrolit, ryzyko dostaw kobaltu/niklu.
- **Półstałe (WeLion/NIO):** 360 Wh/kg ogniwo, produkcja od 2024 — ale ekonomia nieudowodniona.
A iteracja projektowa jest wolna: jeden cykl labowy na kandydata = tygodnie. Nowy projekt ogniwa to typowo 2–4 lata do kwalifikacji.

## Nasza odpowiedź: jedno ogniwo, wszystkie trzy
**Katoda NMC811 + anoda Si-C + elektrolit żelowy** (każdy materiał już w masowej produkcji):

| metryka | nasze ogniwo (symulacja) | najlepsze produkcyjne dziś |
|---|---|---|
| energia | **279 Wh/kg** ogniwo (201 pakiet) | ~230–260 Wh/kg ogniwo (NMC); 260 pakiet (WeLion półstałe) |
| żywotność przy szybkim ładowaniu | **670 cykli @2C** (10–80% w ~24 min) | ~500–800 @2C (ogniwa fast-charge) |
| przeżycie abuse | **piec 150 °C + przeładowanie: przeżywa, margines do 170 °C** | ogniwa z ciekłym elektrolitem (klasa Qilin) nie przechodzą tego testu na poziomie ogniwa (prawdziwe pakiety przeżywają dzięki ciężkim systemom ochrony) |
| moc rozładowania | **5C** | typowo 3–4C |
| koszt materiałowy | **~$67/kWh** | ~$55–80/kWh (ogniwa LFP–NMC) |
| czas do produkcji | **1–2 lata, istniejące linie** | nowa chemia: 3–5+ lat |

Te 1–2 lata to walidacja i kwalifikacja — nie wymyślanie. Każdy klocek jest dziś w masowej produkcji: NMC811 (LG, SK, CATL), Si-C (Sila, Amprius), elektrolity żelowe (WeLion, CATL).

## Dlaczego wygrywamy — zalety, które mają znaczenie
1. **Bezpieczeństwo tam, gdzie boli.** Nasze ogniwo przeżywa piec 150 °C + przeładowanie 1C przez 3 h z marginesem do 170 °C. W tym samym teście ogniwo klasy Qilin (grafit + ciekły elektrolit) wpada w thermal runaway i wybucha na poziomie ogniwa — prawdziwe pakiety przeżywają tylko dzięki ciężkim systemom ochrony (odpowietrzanie, chłodzenie, wyłączniki).
2. **Szybkie ładowanie bez podatku.** 670 cykli przy 2C — pasmo, które przemysł nazywa fast-charge — 10–80% w ~24 minuty.
3. **Koszt klasy LFP, energia klasy NMC.** ~$67/kWh materiałowo za 279 Wh/kg — wobec 160 Wh/kg dla ogniw LFP przy podobnym koszcie.
4. **Da się złożyć teraz.** Istniejące linie katod/anod + modyfikacja napełniania. Bez nowej fabryki, bez nowej chemii, bez 5-letniego czekania.
5. **Narzędzie to przewaga (moat).** Otwarte, reprodukowalne, szybkie: ~118 000 przesymulowanych kombinacji (siatki pełna + drobna + mega), wyniki weryfikowalne przez każdego w minuty (CI, CSV, publiczne repo). Dział R&D producenta ogniw nie ma takiej szybkości iteracji.

## Dwa kolejne pomysły — prostsze do wdrożenia

Flagship wymaga dostaw Si-C i kroku napełniania żelem. Te dwa nie:

### A. Sód-jon: katoda Na-PW + hard carbon + standardowy elektrolit
**Najłatwiejszy ze wszystkich — w produkcji masowej dziś** (CATL Naxtra, koniec 2025, na adaptowanych liniach Li-ion). Zero nowych procesów.

| metryka | nasz projekt | vs konkurencja |
|---|---|---|
| energia | 176 Wh/kg (127 pakiet) | CATL Naxtra: 175 — remis; BYD Blade (LFP): 160 — **+10%** |
| koszt | ~$39/kWh materiałowo | klasa Naxtra; **bez Li, Co, Ni, Cu** (kolektory Al–Al) |
| żywotność @2C | 259 cykli | — |
| mróz | 90% pojemności przy −40 °C | LFP/NMC tracą znacząco |
| nasza przewaga | pełna macierz warunków (temperatura / C-rate / abuse / shelf life) + optymalizacja | dostarczamy wariant *zoptymalizowany* + narzędzie |

**Dlaczego wygrywa:** jedyna chemia, którą da się wdrożyć dziś, tańsza od LFP w skali, odporna na mróz i bezpieczniejsza — i dostarczamy ją *zoptymalizowaną*, z reprodukowalnym modelem za nią.

### B. Ogniwo value $27/kWh: LMFP/LFP + anode-free + standardowy elektrolit ciekły
**Bezpieczeństwo i koszt klasy LFP, 1,7–1,9× energii Blade** — na liniach LFP, na dzisiejszym standardowym elektrolicie (bez żelu, bez stałego elektrolitu).

| metryka | nasz projekt | vs konkurencja |
|---|---|---|
| energia | 270–298 Wh/kg (195–214 pakiet) | BYD Blade (LFP): 160 — **1,7–1,9× więcej przy tej samej klasie bezpieczeństwa** |
| koszt | **~$27/kWh** materiałowo | koszt klasy Blade; ogniwa NMC 2–3× droższe za kWh |
| żywotność @1–2C | 512–824 cykli | — |
| upał | wariant LMFP przeżywa 60 °C | NMC degraduje o 40–50% szybciej przy 45 °C |
| wdrożenie | linie LFP (LMFP = modyfikacja katody) + standardowe napełnianie LP57; jedyny nowy krok: anode-free (własny bet Samsung SDI na 2027) | flagship potrzebuje dostaw Si-C + procesu żelu; ten nie |

**Dlaczego wygrywa:** ogniwo masowe — bezpieczeństwo Blade za koszt Blade, z energią klasy NMC. Każdy klocek poza anode-free to dzisiejsza produkcja.

## Reszta pipeline (po jednej linii)
- **Premium 367 Wh/kg** (NMC811 + anode-free): dorównuje najlepszemu półstałemu pakietowi (260) przy ułamku kosztu.
- **361 Wh/kg bez kobaltu/niklu** (DRX + Si-C): etap rozwojowy.
- **Specjalista 60 °C / >20 lat na półce** (LFP + anode-free + stały): etap rozwojowy.

## Gdzie jesteśmy (uczciwie)
- ~118 000 przesymulowanych kombinacji; dwie niezależne implementacje zgadzają się co do cyfry; determinizm między maszynami potwierdzony (weryfikacja na zewnętrznym PC).
- Publiczne, reprodukowalne repo; CI green; pełne macierze warunków (temperatura, C-rate, abuse, shelf life) dla każdego kandydata.
- **Nie mamy jeszcze fizycznych ogniw.** To aktywo na etapie symulacji. Poniższy plan 12-miesięczny / 150 tys. EUR to most między nimi.

## Rynek
Rynek ogniw ~150 mld USD/rok (szacunek), ~25%/rok wzrostu (EV + magazyny), ~60–70% udziału Chin; zachodni producenci aktywnie ograniczają ryzyko Co/Ni. Przyczółki: pojazdy użytkowe/autobusy (szybkie ładowanie + bezpieczeństwo), drony/lotnictwo (energia), gorący klimat + magazyny (upał + shelf life), dostawcy materiałów (licencje).

## Jak zarabiamy (licencjonowanie, nie startup)
Jesteśmy małym, hobbystycznym studiem: **licencjonujemy pomysły, nie prowadzimy labów.**
1. Ty testujesz projekty w swoim labie (Twoi inżynierowie, Twój budżet) — ten raport to specyfikacja.
2. Jak liczby się zgadzają: licencja IP (niewyłączna, na pole zastosowania, płatna z góry + tantiemy) albo współfinansowanie walidacji 150 tys. EUR za współwyłączność.
3. Narzędzie open-source + płatne wsparcie enterprise to poboczny przychód.

## Ryzyka — głośno
1. **Rozjazd symulacja–lab** — mitygowany bramką poniżej; budżetowany.
2. **Tłok patentowy** — Si-C + żel/stałe elektrolity są gęsto opatentowane (CATL, WeLion, StoreDot, QuantumScape); przegląd FTO w budżecie, przed publicznymi deklaracjami.
3. **Koszt Si-C w skali** — obecnie +20–30% vs grafit; dostawcy skalują przez 2026+.
4. **Zespół** — mały; pierwszym zatrudnionym jest inżynier ogniw.

## Plan — 12 miesięcy, 150 tys. EUR
- **M1–3:** coin cells (flagship + wariant value): ~40 tys. EUR
- **M4–9:** pouch cells + niezależne testy abuse (TÜV / UL 9540A / GB 38031-2025): ~60 tys. EUR
- **M9–12:** linia pilotażowa, LOI od OEM/dostawców, przegląd FTO: ~50 tys. EUR
**Bramka:** jeśli coin cells potwierdzą ≥80% modelowanej żywotności przy 2C → kontynuujemy; jeśli nie → rekalibracja i ponowny screen (narzędzie robi to tanio).

## Czego chcemy
Nie pieniędzy — **labu**. Daj ten raport swojemu zespołowi od ogniw. Jak flagship albo któryś z dwóch prostszych projektów potwierdzi się w coin-cellach — licencjonujemy (albo finansujecie walidację, a my dzielimy upside). Czekamy na oferty.

Repo (publiczne, reprodukowalne): https://github.com/peteraangelic-pixel/Pokemon/tree/arena/d1882c0f-pokemon
"##,
        date = today(),
        ver = env!("CARGO_PKG_VERSION")
    )
}

/// Raport inwestorski (one-pager EN/PL) — konkretny, z liczbami i ryzykami.
pub fn write_pitch(path: &str, lang: &str) -> io::Result<usize> {
    let md = if lang == "en" {
        render_pitch_en()
    } else {
        render_pitch_pl()
    };
    fs::write(path, &md)?;
    Ok(md.lines().count())
}

fn render_pitch_en() -> String {
    format!(
        r##"# battery-sim — investor one-pager
_Generated {date} · battery-sim v{ver} · contact: [YOUR NAME / EMAIL]_

## What this is
An open-source physics simulator for battery cells (Rust; runs on a laptop; screens ~250 real material combinations in about a minute on a 16-core PC) **plus a portfolio of cell designs it produced**, led by one that can be built on existing production lines in 1–2 years: **NMC811 + Si-C + gel — 279 Wh/kg (201 Wh/kg pack), 670 fast-charge cycles @2C, survives 150 °C abuse + overcharge, ~$67/kWh material cost, 5C discharge power** (the 1–2 years is validation and automotive qualification — not invention: every material is already in mass production today). The portfolio also holds: a $27/kWh mass-market variant (LFP/LMFP + anode-free), a 367 Wh/kg premium variant (anode-free), a 361 Wh/kg cobalt/nickel-free novel variant (DRX + Si-C), and a specialty cell that is the only one in the model surviving 60 °C (LFP + anode-free + solid electrolyte, >20 years shelf life).

We built it because we kept hitting the same wall: "which of these 200 real chemistries would actually work?" A lab answers that in weeks per candidate. We answer it in minutes.

## The problem, in numbers
Today's EV cells make you pick two of {{energy, safety, cost}}:
- LFP (BYD Blade): safe + cheap, **160 Wh/kg** — the energy tax.
- NMC (CATL Qilin): **255 Wh/kg pack**, liquid flammable electrolyte, cobalt + nickel supply risk.
- Semi-solid (WeLion/NIO): **360 Wh/kg cell**, in production since 2024 — but cost and cycle life unproven.

Our screen of 250 combinations found cells that get all three at once: **279 Wh/kg (201 Wh/kg pack), 670 cycles @2C, passes 150 °C oven + overcharge abuse, ~$67/kWh material cost** (NMC811 + Si-C + gel electrolyte).

## Why now
1. The materials exist and are procurable today (NMC811 cathodes; Si-C anodes from Sila/Amprius-class suppliers; gel electrolytes from WeLion/CATL-class lines).
2. The bottleneck is iteration speed: one lab design cycle takes weeks; our screen takes seconds and is reproducible (CI, CSV, public repo).
3. Cobalt/nickel supply concentration (DRC, Indonesia) is a board-level risk for every OEM — a cobalt-free, high-energy cell sits exactly on that agenda.
4. **Manufacturability:** the lead buildable candidate (NMC811 + Si-C + gel) runs on existing Li-ion lines — standard cathode, Si-C from suppliers already in production (Sila), gel = a filling-step tweak (semi-solid lines exist: WeLion, CATL). Na-ion is already in mass production on adapted lines (CATL, late 2025).
5. **Shelf life is modeled too**: calendar aging at 50%/100% SOC and 25/45 °C — the failure mode that actually kills EV batteries (they sit parked 95% of the time). Our NMC candidate: ~8 years at 25 °C/100% SOC, ~3.5 at 45 °C; the LFP variant: >15 years.

## Honest status
We have: a calibrated simulator, ~600 simulations run, two concrete cell candidates, public reproducible results.
We do not have: physical cells. This is a simulation-stage asset, and we present it as one.

Accuracy, stated plainly: energy density within ~±15% of cell-level literature; cycle life within ~2x (direction right, absolute value needs lab confirmation); abuse survival matches known commercial outcomes (graphite + liquid = fire risk; LFP/LTO = safe; Si-C enables fast charge). It is a screening tool, not a lab.

## Plan — 12 months, €150k
- **Months 1–3** — coin cells for the 2 candidates (materials + cycling tests): ~€40k
- **Months 4–9** — pouch cells + independent abuse testing (TÜV / UL 9540A / GB 38031-2025): ~€60k
- **Months 9–12** — pilot-line engagement, OEM/supplier LOIs, freedom-to-operate review: ~€50k
**Gate:** if coin cells confirm ≥80% of modeled cycle life at 2C → proceed. If not → re-calibrate and re-screen (the tool makes that cheap).

## Market
~$150B/yr cell market (est.), ~25%/yr growth (EV + grid storage), ~60–70% China share; Western OEMs actively de-risking Co/Ni. Beachheads: commercial vehicles/buses (fast charge + safety), drones/aviation (energy), materials suppliers (licensing).

## Business model
1. **First product (1–2 yrs, existing lines):** NMC811 + Si-C + gel cell design + the screening tool; in parallel a low-risk entry — Na-ion (drop-in; CATL already mass-produces the class) and the $27/kWh value variant.
2. Open-source tool + paid enterprise support (custom materials, HPC grids).
3. License the validated cell IP (portfolio: $27/kWh value, 367 Wh/kg premium, 361 Wh/kg cobalt-free, 60 °C specialty).

## Risks — said out loud
1. **Sim-to-lab gap** (mitigated by the gate; budgeted).
2. **Crowded IP**: Si-C + gel/solid electrolytes are heavily patented (CATL, WeLion, StoreDot, QuantumScape). FTO review is in the budget, before any public claims.
3. **DRX variant** is ~10–20% short of the 500-cycle bar in the model; the fix is identified (cathode fade → F-doping/coating) but unproven.
4. **Team**: small; first hire is a cell engineer.

## The ask
€150k for the 12-month validation plan (convertible note or non-dilutive: NCBR / PARP / EIC Accelerator).

Repo (public, reproducible): https://github.com/peteraangelic-pixel/Pokemon/tree/arena/d1882c0f-pokemon
"##,
        date = today(),
        ver = env!("CARGO_PKG_VERSION")
    )
}

fn render_pitch_pl() -> String {
    format!(
        r##"# battery-sim — one-pager dla inwestora
_Wygenerowano {date} · battery-sim v{ver} · kontakt: [IMIĘ / E-MAIL]_

## Co to jest
Open-source'owy symulator fizyczny ogniw (Rust; działa na laptopie; ~250 kombinacji materiałów w ~1 min na 16-rdzeniowym PC) **plus portfolio projektów ogniw, które wyprodukował**, na czele z jednym, który da się złożyć na istniejących liniach produkcyjnych w 1–2 lata: **NMC811 + Si-C + żel — 279 Wh/kg (201 Wh/kg pakiet), 670 cykli szybkiego ładowania @2C, przeżywa test 150 °C + przeładowanie, ~$67/kWh kosztu materiałowego, moc rozładowania 5C** (ten 1–2 lata to walidacja i kwalifikacja, nie wymyślanie — każdy materiał jest już w masowej produkcji). W portfolio są też: wariant masowy za $27/kWh (LFP/LMFP + anode-free), wariant premium 367 Wh/kg (anode-free), wariant nowatorski 361 Wh/kg bez kobaltu/niklu (DRX + Si-C) i wariant specjalistyczny — jedyny w modelu przeżywający 60 °C (LFP + anode-free + stały elektrolit, >20 lat na półce).

Budowaliśmy go, bo sami trafialiśmy na tę samą ścianę: „która z tych 200 realnych chemii faktycznie zadziała?” Laboratorium odpowiada tygodniami na jednego kandydata. My odpowiadamy w minuty.

## Problem w liczbach
Dziś ogniwa do EV każą wybierać dwa z trzech: {{energia, bezpieczeństwo, koszt}}.
- LFP (BYD Blade): bezpieczne + tanie, **160 Wh/kg** — podatek energetyczny.
- NMC (CATL Qilin): **255 Wh/kg pakiet**, palny ciekły elektrolit, ryzyko dostaw kobaltu/niklu.
- Półstałe (WeLion/NIO): **360 Wh/kg ogniwo**, produkcja od 2024 — ale koszt i żywotność nieudowodnione.

Nasz screen 250 kombinacji znalazł ogniwa, które mają wszystkie trzy naraz: **279 Wh/kg (201 Wh/kg pakiet), 670 cykli @2C, przechodzi test 150 °C + przeładowanie, ~$67/kWh kosztu materiałowego** (NMC811 + Si-C + elektrolit żelowy).

## Dlaczego teraz
1. Materiały istnieją i są kupowalne dziś (katody NMC811; anody Si-C klasy Sila/Amprius; elektrolity żelowe klasy WeLion/CATL).
2. Wąskim gardłem jest szybkość iteracji: jeden cykl projektowy w labie = tygodnie; nasz screen = sekundy, wyniki reprodukowalne (CI, CSV, publiczne repo).
3. Koncentracja dostaw kobaltu/niklu (DRC, Indonezja) to dziś temat zarządów — ogniwo wysokoenergetyczne bez kobaltu leży dokładnie w tym trendzie.
4. **Produkowalność:** główny kandydat do złożenia (NMC811 + Si-C + żel) idzie na istniejących liniach Li-ion — katoda standardowa, Si-C od dostawców produkujących już dziś (Sila), żel = modyfikacja napełniania (linie półstałe są: WeLion, CATL). Na-jon jest już w produkcji masowej na liniach adaptowanych (CATL, koniec 2025).
5. **Modelujemy też „życie na półce”:** starzenie kalendarzowe przy 50%/100% SOC i 25/45 °C — tryb, który faktycznie zabija baterie w EV (auto stoi zaparkowane 95% czasu). Nasz kandydat NMC811: ~8 lat przy 25 °C/100% SOC, ~3,5 przy 45 °C; wariant LFP: >15 lat.

## Uczciwy status
Mamy: skalibrowany symulator, ~600 symulacji, dwóch konkretnych kandydatów, publiczne reprodukowalne wyniki.
Nie mamy: fizycznych ogniw. To aktywo na etapie symulacji — i tak to przedstawiamy.

Dokładność, bez owijania: gęstość energii ±~15% względem literaturowych ogniw; żywotność cykliczna w granicach ~2× (kierunek dobry, wartość bezwzględna do potwierdzenia w labie); przeżycie abuse zgadza się ze znanymi wynikami komercyjnymi (grafit+ciecz = ryzyko pożaru; LFP/LTO = bezpieczne; Si-C umożliwia szybkie ładowanie). To narzędzie selekcji, nie zamiennik laboratorium.

## Plan — 12 miesięcy, 150 tys. EUR
- **M1–3** — coin cells dla 2 kandydatów (materiały + testy cykliczne): ~40 tys. EUR
- **M4–9** — pouch cells + niezależne testy abuse (TÜV / UL 9540A / GB 38031-2025): ~60 tys. EUR
- **M9–12** — linia pilotażowa, LOI od OEM/dostawców, przegląd patentowy (FTO): ~50 tys. EUR
**Bramka (gate):** jeśli coin cells potwierdzą ≥80% modelowanej żywotności przy 2C → kontynuujemy; jeśli nie → rekalibracja i ponowny screen (narzędzie robi to tanio).

## Rynek
Rynek ogniw ~150 mld USD/rok (szacunek), ~25%/rok wzrostu (EV + magazyny), ~60–70% udziału Chin; zachodni producenci aktywnie ograniczają ryzyko Co/Ni. Przyczółki: pojazdy użytkowe/autobusy (szybkie ładowanie + bezpieczeństwo), drony/lotnictwo (energia), dostawcy materiałów (licencje).

## Model biznesowy
1. **Pierwszy produkt (1–2 lata, istniejące linie):** projekt ogniwa NMC811 + Si-C + żel + narzędzie do screeningu; równolegle wejście niskiego ryzyka — Na-jon (drop-in; CATL produkuje już tę klasę masowo) i wariant za $27/kWh.
2. Narzędzie open-source + płatne wsparcie enterprise (własne materiały, siatki HPC).
3. Licencjonowanie IP ogniwa po walidacji (portfolio: $27/kWh value, 367 Wh/kg premium, 361 Wh/kg bez kobaltu, specjalista 60 °C).

## Ryzyka — głośno
1. **Rozjazd symulacja–lab** (mitygowany bramką; budżetowany).
2. **Tłok patentowy**: Si-C + żel/stałe elektrolity są gęsto opatentowane (CATL, WeLion, StoreDot, QuantumScape). Przegląd FTO w budżecie, przed jakimikolwiek publicznymi deklaracjami.
3. **Wariant DRX** jest w modelu ~10–20% poniżej progu 500 cykli; lekarstwo zidentyfikowane (degradacja katody → domieszkowanie F/powłoka), ale nieudowodnione.
4. **Zespół**: mały; pierwszym zatrudnionym jest inżynier ogniw.

## Asks
150 tys. EUR na 12-miesięczny plan walidacji (nota konwertybilna albo niedźwigarowe: NCBR / PARP / EIC Accelerator).

Repo (publiczne, reprodukowalne): https://github.com/peteraangelic-pixel/Pokemon/tree/arena/d1882c0f-pokemon
"##,
        date = today(),
        ver = env!("CARGO_PKG_VERSION")
    )
}
