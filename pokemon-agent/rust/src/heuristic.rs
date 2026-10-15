use serde_json::Value;
use std::collections::{HashMap, HashSet};
use regex::Regex;
use std::sync::OnceLock;

#[derive(Debug, Clone)]
pub struct Card {
    pub id: i32,
    pub name: String,
    pub ct: i32, // CardType
    pub pt: Option<i32>,
    pub hp: i32,
    pub w: Option<i32>,
    pub res: Option<i32>,
    pub en: Option<i32>,
    pub ex: bool,
    pub mex: bool,
    pub ace: bool,
    pub b: bool,
    pub s1: bool,
    pub s2: bool,
    pub ef: Option<String>,
    pub tr: bool,
    pub gu: bool,
    pub pv: Vec<String>,
    pub pvs: Option<String>,
    pub atk: Vec<i32>,
}

#[derive(Debug, Clone)]
pub struct Attack {
    pub id: i32,
    pub name: String,
    pub damage: i32,
    pub text: String,
    pub energies: Vec<i32>,
}

pub struct CardIndex {
    pub cards: HashMap<i32, Card>,
    pub attacks: HashMap<i32, Attack>,
    pub by_name: HashMap<String, Vec<i32>>,
}

impl CardIndex {
    pub fn load(path: &str) -> anyhow::Result<Self> {
        let content = std::fs::read_to_string(path)?;
        let v: Value = serde_json::from_str(&content)?;
        let mut cards = HashMap::new();
        let mut attacks = HashMap::new();
        let mut by_name: HashMap<String, Vec<i32>> = HashMap::new();

        if let Some(cards_obj) = v["cards"].as_object() {
            for (k, val) in cards_obj {
                if let Ok(id) = k.parse::<i32>() {
                    let pv = val["pv"].as_array().map(|arr| arr.iter().filter_map(|x| x.as_str().map(|s| s.to_string())).collect()).unwrap_or_default();
                    let pvs = val["pvs"].as_str().map(|s| s.to_string());
                    let c = Card {
                        id,
                        name: val["n"].as_str().unwrap_or("").to_string(),
                        ct: val["ct"].as_i64().unwrap_or(0) as i32,
                        pt: val["pt"].as_i64().map(|x| x as i32),
                        hp: val["hp"].as_i64().unwrap_or(0) as i32,
                        w: val["w"].as_i64().map(|x| x as i32),
                        res: val["res"].as_i64().map(|x| x as i32),
                        en: val["en"].as_i64().map(|x| x as i32),
                        ex: val["ex"].as_i64().unwrap_or(0) != 0,
                        mex: val["mex"].as_i64().unwrap_or(0) != 0,
                        ace: val["ace"].as_i64().unwrap_or(0) != 0,
                        b: val["b"].as_i64().unwrap_or(0) != 0,
                        s1: val["s1"].as_i64().unwrap_or(0) != 0,
                        s2: val["s2"].as_i64().unwrap_or(0) != 0,
                        ef: val["ef"].as_str().map(|s| s.to_string()),
                        tr: val["tr"].as_i64().unwrap_or(0) != 0,
                        gu: val["gu"].as_i64().unwrap_or(0) != 0,
                        pv,
                        pvs,
                        atk: val["atk"].as_array().map(|arr| arr.iter().filter_map(|x| x.as_i64().map(|y| y as i32)).collect()).unwrap_or_default(),
                    };
                    by_name.entry(c.name.clone()).or_default().push(id);
                    cards.insert(id, c);
                }
            }
        }
        if let Some(attacks_obj) = v["attacks"].as_object() {
            for (k, val) in attacks_obj {
                if let Ok(id) = k.parse::<i32>() {
                    let a = Attack {
                        id,
                        name: val["n"].as_str().unwrap_or("").to_string(),
                        damage: val["d"].as_i64().unwrap_or(0) as i32,
                        text: val["t"].as_str().unwrap_or("").to_string(),
                        energies: val["e"].as_array().map(|arr| arr.iter().filter_map(|x| x.as_i64().map(|y| y as i32)).collect()).unwrap_or_default(),
                    };
                    attacks.insert(id, a);
                }
            }
        }
        Ok(Self { cards, attacks, by_name })
    }
    pub fn card(&self, id: i32) -> Option<&Card> { self.cards.get(&id) }
    pub fn attack(&self, id: i32) -> Option<&Attack> { self.attacks.get(&id) }
}

#[derive(Debug, Clone)]
pub struct Plan {
    pub counts: HashMap<i32, i32>,
    pub primary: Option<i32>,
    pub line: HashSet<i32>,
    pub primary_power: i32,
}

impl Plan {
    pub fn build(deck: &[i32], index: &CardIndex) -> Self {
        let mut counts: HashMap<i32, i32> = HashMap::new();
        for &cid in deck {
            *counts.entry(cid).or_insert(0) += 1;
        }
        let mut pokemon: Vec<i32> = counts.keys().filter(|cid| index.card(**cid).map(|c| c.ct==0).unwrap_or(false)).cloned().collect();
        let mut primary: Option<i32> = None;
        let mut best_power = -1;
        for &cid in &pokemon {
            if let Some(c) = index.card(cid) {
                let mut power = c.hp;
                if c.mex { power += 200; }
                if c.ex { power += 120; }
                if c.s2 { power += 30; }
                if c.s1 { power += 15; }
                if power > best_power {
                    best_power = power;
                    primary = Some(cid);
                }
            }
        }
        let mut line: HashSet<i32> = HashSet::new();
        if let Some(p) = primary {
            line.insert(p);
            let mut cur = p;
            for _ in 0..4 {
                if let Some(card) = index.card(cur) {
                    if let Some(ef_name) = &card.ef {
                        if let Some(ids) = index.by_name.get(ef_name) {
                            if !ids.is_empty() {
                                let nxt = ids[0];
                                line.insert(nxt);
                                cur = nxt;
                                continue;
                            }
                        }
                    }
                }
                break;
            }
        }
        let mut primary_power = 0;
        if let Some(p) = primary {
            if let Some(card) = index.card(p) {
                for aid in &card.atk {
                    if let Some(atk) = index.attack(*aid) {
                        primary_power = primary_power.max(atk.damage);
                    }
                }
            }
        }
        Self { counts, primary, line, primary_power }
    }
    pub fn is_primary_line(&self, cid: i32) -> bool { self.line.contains(&cid) }
}

pub struct Knobs {
    pub supporter: i32,
    pub item: i32,
    pub bench: i32,
    pub evolve: i32,
    pub attach: i32,
    pub stadium: i32,
    pub ability: i32,
    pub attack_ko: i32,
    pub attack: i32,
    pub retreat_base: i32,
    pub retreat_no_atk: i32,
    pub retreat_ko: i32,
    pub retreat_wall: i32,
    pub gust_bonus: i32,
    pub wall_penalty: i32,
    pub wall_escape: i32,
    pub attach_wall_bonus: i32,
    pub attach_wall_penalty: i32,
    pub beach_wall: i32,
    pub fighter_ready: i32,
    pub fighter_not_ready: i32,
    pub prize_penalty: i32,
    pub enable_bonus: i32,
    pub progress_bonus: i32,
    pub active_bonus: i32,
    pub primary_bonus: i32,
}
impl Default for Knobs {
    fn default() -> Self {
        Self {
            supporter: 340,
            item: 330,
            bench: 320,
            evolve: 310,
            attach: 300,
            stadium: 290,
            ability: 270,
            attack_ko: 260,
            attack: 200,
            retreat_base: 120,
            retreat_no_atk: 219,
            retreat_ko: 277,
            retreat_wall: 344,
            gust_bonus: 59,
            wall_penalty: -650,
            wall_escape: 211,
            attach_wall_bonus: 30,
            attach_wall_penalty: -35,
            beach_wall: 335,
            fighter_ready: 22,
            fighter_not_ready: -63,
            prize_penalty: 16,
            enable_bonus: 14,
            progress_bonus: 32,
            active_bonus: 6,
            primary_bonus: 7,
        }
    }
}

// helpers to read JSON
fn get_i64(v: &Value, key: &str) -> Option<i64> { v.get(key).and_then(|x| x.as_i64()) }
fn get_usize(v: &Value, key: &str) -> usize { v.get(key).and_then(|x| x.as_u64()).unwrap_or(0) as usize }

fn obs_current(v: &Value) -> &Value { &v["current"] }
fn obs_select(v: &Value) -> &Value { &v["select"] }

fn active_pokemon<'a>(obs: &'a Value, owner: usize) -> Option<&'a Value> {
    obs_current(obs).get("players")?.as_array()?.get(owner)?.get("active")?.as_array()?.get(0).filter(|x| !x.is_null())
}
fn bench_pokemons<'a>(obs: &'a Value, owner: usize) -> Vec<&'a Value> {
    let mut out = Vec::new();
    if let Some(players) = obs_current(obs).get("players").and_then(|x| x.as_array()) {
        if let Some(p) = players.get(owner) {
            if let Some(bench) = p.get("bench").and_then(|x| x.as_array()) {
                for b in bench {
                    if !b.is_null() { out.push(b); }
                }
            }
        }
    }
    out
}
fn hand_cards<'a>(obs: &'a Value, owner: usize) -> Vec<&'a Value> {
    let mut out = Vec::new();
    if let Some(players) = obs_current(obs).get("players").and_then(|x| x.as_array()) {
        if let Some(p) = players.get(owner) {
            if let Some(hand) = p.get("hand").and_then(|x| x.as_array()) {
                for h in hand { out.push(h); }
            }
        }
    }
    out
}
fn discard_cards<'a>(obs: &'a Value, owner: usize) -> Vec<&'a Value> {
    let mut out = Vec::new();
    if let Some(players) = obs_current(obs).get("players").and_then(|x| x.as_array()) {
        if let Some(p) = players.get(owner) {
            if let Some(discard) = p.get("discard").and_then(|x| x.as_array()) {
                for d in discard { if !d.is_null() { out.push(d); } }
            }
        }
    }
    out
}
fn pokemon_at<'a>(obs: &'a Value, owner: usize, area: i64, idx: usize) -> Option<&'a Value> {
    let players = obs_current(obs).get("players")?.as_array()?;
    let p = players.get(owner)?;
    match area {
        4 => {
            let arr = p.get("active")?.as_array()?;
            let v = arr.get(idx)?;
            if v.is_null() { None } else { Some(v) }
        },
        5 => {
            let arr = p.get("bench")?.as_array()?;
            let v = arr.get(idx)?;
            if v.is_null() { None } else { Some(v) }
        },
        _ => None,
    }
}
fn hand_id(obs: &Value, owner: usize, idx: usize) -> Option<i32> {
    hand_cards(obs, owner).get(idx)?.get("id")?.as_i64().map(|x| x as i32)
}
fn board_card_id(obs: &Value, owner: usize, area: i64, idx: usize) -> Option<i32> {
    pokemon_at(obs, owner, area, idx)?.get("id")?.as_i64().map(|x| x as i32)
}
fn sel_card_id(opt: &Value, obs: &Value, me_idx: usize) -> Option<i32> {
    if let Some(cid) = opt.get("cardId").and_then(|x| x.as_i64()) {
        if opt.get("area").is_none() { return Some(cid as i32); }
    }
    let area = opt.get("area")?.as_i64()?;
    let idx = opt.get("index")?.as_u64()? as usize;
    let owner = opt.get("playerIndex").and_then(|x| x.as_u64()).unwrap_or(me_idx as u64) as usize;
    if area == 2 && owner == me_idx {
        return hand_id(obs, me_idx, idx);
    }
    if area == 1 && owner == me_idx {
        if let Some(deck_arr) = obs_select(obs).get("deck").and_then(|x| x.as_array()) {
            if idx < deck_arr.len() {
                let entry = &deck_arr[idx];
                if let Some(id) = entry.get("id").and_then(|x| x.as_i64()) { return Some(id as i32); }
                if let Some(id) = entry.as_i64() { return Some(id as i32); }
            }
        }
        return None;
    }
    board_card_id(obs, owner, area, idx)
}
fn card_value(cid: i32, index: &CardIndex, plan: &Plan) -> i32 {
    if let Some(c) = index.card(cid) {
        match c.ct {
            0 => {
                let mut v = 60;
                if plan.is_primary_line(cid) { v += 37; }
                if Some(cid) == plan.primary { v += 37; }
                v += c.hp / 4;
                if c.mex { v += 15; }
                if c.ex { v += 10; }
                v
            },
            5 => 12,
            6 => 38,
            3 => 72,
            1 => 66,
            2 => 44,
            4 => 40,
            _ => 50,
        }
    } else { 50 }
}
fn prize_value(cid: i32, index: &CardIndex) -> i32 {
    if let Some(c) = index.card(cid) {
        if c.mex { return 3; }
        if c.ex { return 2; }
    }
    1
}
fn damage_prevented(attacker_cid: i32, defender_cid: i32, damage: i32, index: &CardIndex) -> bool {
    let dfn = match index.card(defender_cid) { Some(c) => c, None => return false };
    if dfn.pv.is_empty() { return false; }
    if dfn.pvs.as_deref() == Some("bench") { return false; }
    let atk = match index.card(attacker_cid) { Some(c) => c, None => return false };
    let is_ex = atk.ex || atk.mex;
    for cls in &dfn.pv {
        match cls.as_str() {
            "ex" if is_ex => return true,
            "basicEx" if is_ex && atk.b => return true,
            "tera" if atk.tr => return true,
            "ability" if !atk.atk.is_empty() => { /* simplified: if attacker has ability? we check skill presence via atk? */ },
            "dmg200" if damage >= 200 => return true,
            "specialEnergy" => return true,
            "all" => return true,
            _ => {},
        }
    }
    false
}
fn plan_power(cid: i32, index: &CardIndex, plan: &Plan) -> i32 {
    if let Some(c) = index.card(cid) {
        if c.ct != 0 { return 0; }
        let mut score = c.hp;
        if plan.is_primary_line(cid) { score += 150; }
        if Some(cid) == plan.primary { score += 150; }
        if c.mex { score += 60; }
        if c.ex { score += 40; }
        score
    } else { 0 }
}
fn cheapest_attack_cost(poke: &Value, index: &CardIndex) -> Option<usize> {
    let cid = poke.get("id")?.as_i64()? as i32;
    let card = index.card(cid)?;
    let mut best: Option<usize> = None;
    for aid in &card.atk {
        if let Some(atk) = index.attack(*aid) {
            let cost = atk.energies.len();
            if cost > 0 {
                if best.is_none() || cost < best.unwrap() { best = Some(cost); }
            }
        }
    }
    best
}
fn energies_needed(poke: &Value, index: &CardIndex) -> i32 {
    if let Some(cost) = cheapest_attack_cost(poke, index) {
        let have = poke.get("energies").and_then(|x| x.as_array()).map(|a| a.len()).unwrap_or(0);
        if have >= cost { 0 } else { (cost - have) as i32 }
    } else { 99 }
}
fn attack_ready(poke: &Value, index: &CardIndex) -> bool {
    let cid = match poke.get("id").and_then(|x| x.as_i64()) { Some(id) => id as i32, None => return false };
    let have = poke.get("energies").and_then(|x| x.as_array()).map(|a| a.len()).unwrap_or(0);
    if let Some(card) = index.card(cid) {
        for aid in &card.atk {
            if let Some(atk) = index.attack(*aid) {
                let cost = atk.energies.len();
                if cost > 0 && cost <= have { return true; }
            }
        }
    }
    false
}
fn best_attack_damage(poke: &Value, attacker_cid: i32, defender_cid: i32, index: &CardIndex, obs: &Value, me_idx: usize, opp_idx: usize) -> i32 {
    let mut best = 0;
    if let Some(card) = index.card(attacker_cid) {
        for aid in &card.atk {
            let dmg = estimate_damage_raw(*aid, index, obs, me_idx, opp_idx);
            if dmg <= 0 { continue; }
            if damage_prevented(attacker_cid, defender_cid, dmg, index) { continue; }
            let mut d = dmg;
            if let Some(atk_card) = index.card(attacker_cid) {
                if let Some(def_card) = index.card(defender_cid) {
                    if atk_card.pt.is_some() && def_card.w.is_some() && atk_card.pt == def_card.w { d += 30; }
                    if atk_card.pt.is_some() && def_card.res.is_some() && atk_card.pt == def_card.res { d -= 30; }
                }
            }
            best = best.max(d.max(0));
        }
    }
    best
}
fn fighter_score(poke: &Value, index: &CardIndex, _plan: &Plan, knobs: &Knobs, obs: &Value, opp_active: Option<&Value>) -> i32 {
    let cid = match poke.get("id").and_then(|x| x.as_i64()) { Some(id) => id as i32, None => return -1000 };
    let have = poke.get("energies").and_then(|x| x.as_array()).map(|a| a.len()).unwrap_or(0);
    let mut best_dmg = 0;
    if let Some(card) = index.card(cid) {
        for aid in &card.atk {
            if let Some(atk) = index.attack(*aid) {
                if atk.energies.len() <= have {
                    best_dmg = best_dmg.max(atk.damage);
                }
            }
        }
    }
    let hp = poke.get("hp").and_then(|x| x.as_i64()).unwrap_or(0) as i32;
    let mut score = hp + 2 * best_dmg;
    if attack_ready(poke, index) { score += knobs.fighter_ready; } else { score += knobs.fighter_not_ready; }
    score -= knobs.prize_penalty * prize_value(cid, index);
    if let Some(opp_act) = opp_active {
        if let Some(opp_id) = opp_act.get("id").and_then(|x| x.as_i64()).map(|x| x as i32) {
            if damage_prevented(cid, opp_id, 1_000_000, index) {
                score += knobs.wall_penalty;
            } else {
                // if our current active is walled, this bench attacker is precious
                let me_idx = obs["current"]["yourIndex"].as_u64().unwrap_or(0) as usize;
                if let Some(my_act) = active_pokemon(obs, me_idx) {
                    if let Some(my_cid) = my_act.get("id").and_then(|x| x.as_i64()).map(|x| x as i32) {
                        if my_cid != cid && damage_prevented(my_cid, opp_id, 1_000_000, index) {
                            score += knobs.wall_escape;
                        }
                    }
                }
            }
        }
    }
    score
}
fn me_idx_from_obs(obs: &Value) -> usize { obs["current"]["yourIndex"].as_u64().unwrap_or(0) as usize }

fn regex_per_each() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| Regex::new(r"(?i)does (\d+) damage for each").unwrap())
}
fn regex_mill() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| Regex::new(r"(?i)discard the top (\d+) cards? of your deck").unwrap())
}
fn regex_deck_count() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| Regex::new(r"(?i)(\d+) cards? from your deck").unwrap())
}

fn deck_energy_remaining(obs: &Value, me_idx: usize, energy_type: i32, deck: &[i32], index: &CardIndex) -> f64 {
    let total = deck.iter().filter(|cid| index.card(**cid).map(|c| c.en == Some(energy_type)).unwrap_or(false)).count() as f64;
    let mut seen = 0.0;
    for h in hand_cards(obs, me_idx) {
        if let Some(id) = h.get("id").and_then(|x| x.as_i64()).map(|x| x as i32) {
            if index.card(id).map(|c| c.en == Some(energy_type)).unwrap_or(false) { seen += 1.0; }
        }
    }
    for d in discard_cards(obs, me_idx) {
        if let Some(id) = d.get("id").and_then(|x| x.as_i64()).map(|x| x as i32) {
            if index.card(id).map(|c| c.en == Some(energy_type)).unwrap_or(false) { seen += 1.0; }
        }
    }
    // attached energies
    if let Some(players) = obs["current"]["players"].as_array() {
        if let Some(p) = players.get(me_idx) {
            for area in ["active", "bench"] {
                if let Some(slots) = p.get(area).and_then(|x| x.as_array()) {
                    for slot in slots {
                        if slot.is_null() { continue; }
                        if let Some(energies) = slot.get("energyCards").and_then(|x| x.as_array()) {
                            for e in energies {
                                if let Some(id) = e.get("id").and_then(|x| x.as_i64()).map(|x| x as i32) {
                                    if index.card(id).map(|c| c.en == Some(energy_type)).unwrap_or(false) { seen += 1.0; }
                                }
                            }
                        }
                        // also energies field is array of energy types? but we count energyCards
                    }
                }
            }
        }
    }
    (total - seen).max(0.0)
}
fn deck_energy_rate(obs: &Value, me_idx: usize, energy_type: i32, deck: &[i32], index: &CardIndex) -> f64 {
    let remaining_deck = obs["current"]["players"].as_array().and_then(|arr| arr.get(me_idx)).and_then(|p| p.get("deckCount")).and_then(|x| x.as_u64()).unwrap_or(0) as f64;
    if remaining_deck <= 1.0 { return 0.0; }
    let rem = deck_energy_remaining(obs, me_idx, energy_type, deck, index);
    (rem / remaining_deck).min(1.0)
}
fn count_for_each(subject: &str, obs: &Value, me_idx: usize, opp_idx: usize, index: &CardIndex) -> f64 {
    let s = subject.to_lowercase();
    let players = match obs["current"]["players"].as_array() { Some(p) => p, None => return 0.0 };
    let me = match players.get(me_idx) { Some(m) => m, None => return 0.0 };
    let opp = match players.get(opp_idx) { Some(o) => o, None => return 0.0 };

    if s.contains("discard pile") || s.contains("discarded") {
        let mut pile = Vec::new();
        for p in [me, opp] {
            if let Some(discard) = p.get("discard").and_then(|x| x.as_array()) {
                for d in discard { if !d.is_null() { pile.push(d); } }
            }
        }
        if s.contains("{w}") || s.contains("water") {
            return pile.iter().filter(|d| d.get("id").and_then(|x| x.as_i64()).map(|id| index.card(id as i32).map(|c| c.en == Some(3)).unwrap_or(false)).unwrap_or(false)).count() as f64;
        }
        if s.contains("basic") && s.contains("energy") {
            return pile.iter().filter(|d| d.get("id").and_then(|x| x.as_i64()).map(|id| index.card(id as i32).map(|c| c.ct==5).unwrap_or(false)).unwrap_or(false)).count() as f64;
        }
        if s.contains("energy") {
            return pile.iter().filter(|d| d.get("id").and_then(|x| x.as_i64()).map(|id| index.card(id as i32).map(|c| c.en.is_some()).unwrap_or(false)).unwrap_or(false)).count() as f64;
        }
        return pile.len() as f64;
    }
    if s.contains("in this way") || s.contains("discarded in this way") { return 0.0; }
    if s.contains("in your hand") { return me.get("hand").and_then(|x| x.as_array()).map(|a| a.len()).unwrap_or(0) as f64; }
    if s.contains("in your opponent") && s.contains("hand") { return opp.get("handCount").and_then(|x| x.as_u64()).unwrap_or(0) as f64; }
    if s.contains("bench") { return me.get("bench").and_then(|x| x.as_array()).map(|a| a.iter().filter(|b| !b.is_null()).count()).unwrap_or(0) as f64; }
    if s.contains("damage counter") && s.contains("this") {
        if let Some(active) = active_pokemon(obs, me_idx) {
            let max_hp = active.get("maxHp").and_then(|x| x.as_i64()).unwrap_or(0);
            let hp = active.get("hp").and_then(|x| x.as_i64()).unwrap_or(0);
            return ((max_hp - hp) / 10).max(0) as f64;
        }
        return 0.0;
    }
    if s.contains("prize") { return opp.get("prize").and_then(|x| x.as_array()).map(|a| a.iter().filter(|p| p.is_null()).count()).unwrap_or(0) as f64; }
    if s.contains("stadium") { return if obs["current"].get("stadium").and_then(|x| x.as_array()).map(|a| !a.is_empty()).unwrap_or(false) { 1.0 } else { 0.0 }; }
    if s.contains("tool") {
        let mut cnt = 0;
        if let Some(bench) = me.get("bench").and_then(|x| x.as_array()) {
            for b in bench {
                if b.is_null() { continue; }
                if let Some(tools) = b.get("tools").and_then(|x| x.as_array()) { cnt += tools.len(); }
            }
        }
        return cnt as f64;
    }
    0.0
}

fn estimate_damage_raw(aid: i32, index: &CardIndex, obs: &Value, me_idx: usize, opp_idx: usize) -> i32 {
    let ad = match index.attack(aid) { Some(a) => a, None => return 0 };
    let base = ad.damage;
    if base > 0 { return base; }
    let text = &ad.text;
    if text.is_empty() { return 0; }
    if let Some(cap) = regex_per_each().captures(text) {
        if let Some(m) = cap.get(1) {
            if let Ok(per) = m.as_str().parse::<i32>() {
                if text.to_lowercase().contains("in this way") {
                    let n_cards = regex_mill().captures(text).and_then(|c| c.get(1)).and_then(|m| m.as_str().parse::<i32>().ok()).unwrap_or(6);
                    let low = text.to_lowercase();
                    let rate = if low.contains("{w}") || low.contains("water") {
                        deck_energy_rate(obs, me_idx, 3, &[], index) // deck unknown here, we approximate with 0.5? but we have no deck param – use 0.5 for now
                    } else if low.contains("basic") && low.contains("energy") {
                        0.6
                    } else if low.contains("energy") {
                        0.6
                    } else {
                        return per * n_cards;
                    };
                    return (per as f64 * n_cards as f64 * rate.min(1.0)) as i32;
                }
                // try to parse subject after match
                if let Some(m2) = regex_per_each().find(text) {
                    let subject = &text[m2.end()..(m2.end()+120).min(text.len())];
                    let count = count_for_each(subject, obs, me_idx, opp_idx, index);
                    return (per as f64 * count) as i32;
                }
                return per;
            }
        }
    }
    0
}
fn estimate_damage_raw_with_deck(aid: i32, index: &CardIndex, obs: &Value, me_idx: usize, opp_idx: usize, deck: &[i32]) -> i32 {
    let ad = match index.attack(aid) { Some(a) => a, None => return 0 };
    let base = ad.damage;
    if base > 0 { return base; }
    let text = &ad.text;
    if text.is_empty() { return 0; }
    if let Some(cap) = regex_per_each().captures(text) {
        if let Some(m) = cap.get(1) {
            if let Ok(per) = m.as_str().parse::<i32>() {
                if text.to_lowercase().contains("in this way") {
                    let n_cards = regex_mill().captures(text).and_then(|c| c.get(1)).and_then(|m| m.as_str().parse::<i32>().ok()).unwrap_or(6);
                    let low = text.to_lowercase();
                    let rate = if low.contains("{w}") || low.contains("water") {
                        deck_energy_rate(obs, me_idx, 3, deck, index)
                    } else if low.contains("basic") && low.contains("energy") {
                        // sum over all basic energy types 1..8
                        (1..=8).map(|et| deck_energy_rate(obs, me_idx, et, deck, index)).sum::<f64>()
                    } else if low.contains("energy") {
                        (1..=8).map(|et| deck_energy_rate(obs, me_idx, et, deck, index)).sum::<f64>()
                    } else {
                        return per * n_cards;
                    };
                    return (per as f64 * n_cards as f64 * rate.min(1.0)) as i32;
                }
                if let Some(m2) = regex_per_each().find(text) {
                    let subject = &text[m2.end()..(m2.end()+120).min(text.len())];
                    let count = count_for_each(subject, obs, me_idx, opp_idx, index);
                    return (per as f64 * count) as i32;
                }
                return per;
            }
        }
    }
    0
}

pub fn estimate_attack_damage(aid: i32, index: &CardIndex, obs: &Value, me_idx: usize, opp_idx: usize, deck: &[i32]) -> i32 {
    let dmg = estimate_damage_raw_with_deck(aid, index, obs, me_idx, opp_idx, deck);
    if dmg <= 0 { return 0; }
    if let (Some(atk), Some(dfn)) = (active_pokemon(obs, me_idx), active_pokemon(obs, opp_idx)) {
        if let (Some(atk_id), Some(dfn_id)) = (atk.get("id").and_then(|x| x.as_i64()).map(|x| x as i32), dfn.get("id").and_then(|x| x.as_i64()).map(|x| x as i32)) {
            if damage_prevented(atk_id, dfn_id, dmg, index) { return 0; }
        }
    }
    dmg
}
fn mill_would_deck_out(aid: i32, index: &CardIndex, obs: &Value, me_idx: usize) -> bool {
    let ad = match index.attack(aid) { Some(a) => a, None => return false };
    if let Some(cap) = regex_mill().captures(&ad.text) {
        if let Some(m) = cap.get(1) {
            if let Ok(n) = m.as_str().parse::<i64>() {
                if let Some(players) = obs["current"]["players"].as_array() {
                    if let Some(p) = players.get(me_idx) {
                        if let Some(rem) = p.get("deckCount").and_then(|x| x.as_i64()) {
                            return rem <= n + 1;
                        }
                    }
                }
            }
        }
    }
    false
}
fn wall_gust_bonus(cid: i32, index: &CardIndex, obs: &Value, me_idx: usize, opp_idx: usize) -> i32 {
    let card = match index.card(cid) { Some(c) => c, None => return 0 };
    if !card.gu { return 0; }
    let my_active = match active_pokemon(obs, me_idx) { Some(a) => a, None => return 0 };
    let opp_active = match active_pokemon(obs, opp_idx) { Some(a) => a, None => return 0 };
    let my_id = match my_active.get("id").and_then(|x| x.as_i64()) { Some(id) => id as i32, None => return 0 };
    let opp_id = match opp_active.get("id").and_then(|x| x.as_i64()) { Some(id) => id as i32, None => return 0 };
    if damage_prevented(my_id, opp_id, 1_000_000, index) { 60 } else { 0 }
}
fn count_water_in_discard(obs: &Value, me_idx: usize, index: &CardIndex) -> i32 {
    let mut cnt = 0;
    for d in discard_cards(obs, me_idx) {
        if let Some(id) = d.get("id").and_then(|x| x.as_i64()).map(|x| x as i32) {
            if let Some(c) = index.card(id) {
                if c.en == Some(3) { cnt += 1; }
            }
        }
    }
    cnt
}
fn gust_lethal_bonus(cid: i32, index: &CardIndex, obs: &Value, me_idx: usize, opp_idx: usize, deck: &[i32]) -> i32 {
    let card = match index.card(cid) { Some(c) => c, None => return 0 };
    if !card.gu { return 0; }
    let opp_bench = bench_pokemons(obs, opp_idx);
    if opp_bench.is_empty() { return 0; }
    let my_active = match active_pokemon(obs, me_idx) { Some(a) => a, None => return 0 };
    let my_bench = bench_pokemons(obs, me_idx);
    let mut attackers: Vec<&Value> = vec![my_active];
    for b in &my_bench {
        if attack_ready(b, index) { attackers.push(b); }
    }
    let mut best = 0;
    for target in opp_bench {
        let tid = match target.get("id").and_then(|x| x.as_i64()) { Some(id) => id as i32, None => continue };
        let thp = target.get("hp").and_then(|x| x.as_i64()).unwrap_or(0) as i32;
        if thp <= 0 || thp > 340 { continue; }
        let mut can_hit = false;
        let mut max_dmg = 0;
        for atk_poke in &attackers {
            let aid = match atk_poke.get("id").and_then(|x| x.as_i64()) { Some(id) => id as i32, None => continue };
            if damage_prevented(aid, tid, 1_000_000, index) { continue; }
            let mut bd = 0;
            if let Some(c) = index.card(aid) {
                for atk_id in &c.atk {
                    let raw = estimate_damage_raw_with_deck(*atk_id, index, obs, me_idx, opp_idx, deck);
                    if raw <= 0 { continue; }
                    if damage_prevented(aid, tid, raw, index) { continue; }
                    let mut r = raw;
                    if let Some(atk_card) = index.card(aid) {
                        if let Some(def_card) = index.card(tid) {
                            if atk_card.pt.is_some() && def_card.w.is_some() && atk_card.pt == def_card.w { r += 30; }
                            if atk_card.pt.is_some() && def_card.res.is_some() && atk_card.pt == def_card.res { r -= 30; }
                        }
                    }
                    // belt +50 vs ex
                    if let Some(tools) = atk_poke.get("tools").and_then(|x| x.as_array()) {
                        for t in tools {
                            if let Some(tid2) = t.get("id").and_then(|x| x.as_i64()).map(|x| x as i32) {
                                if let Some(tc) = index.card(tid2) {
                                    if tc.name == "Maximum Belt" {
                                        if let Some(dc) = index.card(tid) {
                                            if dc.ex || dc.mex { r += 50; }
                                        }
                                    }
                                }
                            }
                        }
                    }
                    r = r.max(0);
                    bd = bd.max(r);
                }
            }
            if bd > 0 { can_hit = true; max_dmg = max_dmg.max(bd); }
        }
        if !can_hit { continue; }
        if max_dmg >= thp {
            let mut bonus = 90 + 25 * prize_value(tid, index);
            if thp <= 70 { bonus += 30; } else if thp <= 120 { bonus += 15; }
            if target.get("energies").and_then(|x| x.as_array()).map(|a| a.len()).unwrap_or(0) >= 2 { bonus += 15; }
            best = best.max(bonus);
        }
    }
    best
}
fn retrieval_bonus(cid: i32, index: &CardIndex, obs: &Value, me_idx: usize, deck: &[i32]) -> i32 {
    if cid != 1118 { return 0; }
    let water_disc = count_water_in_discard(obs, me_idx, index);
    if water_disc == 0 { return -20; }
    let mut need = 0;
    if let Some(players) = obs["current"]["players"].as_array() {
        if let Some(p) = players.get(me_idx) {
            for area in ["active", "bench"] {
                if let Some(slots) = p.get(area).and_then(|x| x.as_array()) {
                    for slot in slots {
                        if slot.is_null() { continue; }
                        let en = energies_needed(slot, index);
                        if en > 0 && en < 99 { need += en; }
                    }
                }
            }
        }
    }
    let mut energy_in_hand = 0;
    for h in hand_cards(obs, me_idx) {
        if let Some(id) = h.get("id").and_then(|x| x.as_i64()).map(|x| x as i32) {
            if let Some(c) = index.card(id) {
                if c.en == Some(3) { energy_in_hand += 1; }
            }
        }
    }
    let mut bonus = 25 + 12 * water_disc + 8 * need;
    if energy_in_hand == 0 { bonus += 25; }
    if need >= 2 { bonus += 20; }
    bonus
}

// scoring helpers
fn can_my_active_attack(obs: &Value) -> bool {
    if let Some(opts) = obs_select(obs).get("option").and_then(|x| x.as_array()) {
        for o in opts {
            if o.get("type").and_then(|x| x.as_i64()) == Some(13) { return true; }
        }
    }
    false
}
fn score_main_option(opt: &Value, obs: &Value, me_idx: usize, opp_idx: usize, index: &CardIndex, plan: &Plan, knobs: &Knobs, deck: &[i32]) -> i32 {
    let otype = opt.get("type").and_then(|x| x.as_i64()).unwrap_or(-1);
    let my_active = active_pokemon(obs, me_idx);
    let opp_active = active_pokemon(obs, opp_idx);
    let my_bench = bench_pokemons(obs, me_idx);
    if otype == 14 { return 0; } // END
    if otype == 13 { // ATTACK
        let aid = opt.get("attackId").and_then(|x| x.as_i64()).unwrap_or(0) as i32;
        if my_active.is_none() || opp_active.is_none() { return if aid != 0 { 200 } else { 150 }; }
        let mut est = estimate_attack_damage(aid, index, obs, me_idx, opp_idx, deck);
        // weakness/resistance already in estimate? we add again for active vs active? estimate already handles wall but not weakness? we handle in estimate_raw_with_deck includes weakness? Actually we added weakness in gust_lethal but not in estimate_attack_damage – we should add here
        if let (Some(my_act), Some(opp_act)) = (my_active, opp_active) {
            if let (Some(my_id), Some(opp_id)) = (my_act.get("id").and_then(|x| x.as_i64()).map(|x| x as i32), opp_act.get("id").and_then(|x| x.as_i64()).map(|x| x as i32)) {
                if let (Some(my_card), Some(opp_card)) = (index.card(my_id), index.card(opp_id)) {
                    if my_card.pt.is_some() && opp_card.w.is_some() && my_card.pt == opp_card.w { est += 30; }
                    if my_card.pt.is_some() && opp_card.res.is_some() && my_card.pt == opp_card.res { est -= 30; }
                }
            }
        }
        est = est.max(0);
        if mill_would_deck_out(aid, index, obs, me_idx) { return 5; }
        let opp_hp = opp_active.and_then(|a| a.get("hp")).and_then(|x| x.as_i64()).unwrap_or(0) as i32;
        let ko = est > 0 && est >= opp_hp;
        let mut score = if ko { knobs.attack_ko } else { knobs.attack };
        score += (est.min(240) / 4) as i32;
        if ko {
            if let Some(opp_id) = opp_active.and_then(|a| a.get("id")).and_then(|x| x.as_i64()).map(|x| x as i32) {
                score += 25 * prize_value(opp_id, index);
            }
        }
        if est == 0 {
            score -= 40;
            if let Some(atk) = index.attack(aid) {
                if atk.text.to_lowercase().contains("shuffle those cards into your deck") || atk.text.to_lowercase().contains("into your deck") {
                    score += 45;
                }
            }
        }
        return score;
    }
    if otype == 12 { // RETREAT
        let mut score = knobs.retreat_base;
        if my_active.is_none() { return score; }
        let my_act = my_active.unwrap();
        let opp_power = if let Some(opp_act) = opp_active {
            if let (Some(opp_id), Some(my_id)) = (opp_act.get("id").and_then(|x| x.as_i64()).map(|x| x as i32), my_act.get("id").and_then(|x| x.as_i64()).map(|x| x as i32)) {
                best_attack_damage(opp_act, opp_id, my_id, index, obs, opp_idx, me_idx)
            } else { 0 }
        } else { 0 };
        let my_hp = my_act.get("hp").and_then(|x| x.as_i64()).unwrap_or(0) as i32;
        let can_attack = can_my_active_attack(obs);
        let backup_ok = my_bench.iter().any(|p| {
            if let Some(pid) = p.get("id").and_then(|x| x.as_i64()).map(|x| x as i32) {
                plan_power(pid, index, plan) >= plan_power(my_act.get("id").and_then(|x| x.as_i64()).map(|x| x as i32).unwrap_or(0), index, plan) - 40
            } else { false }
        });
        if !can_attack && !my_bench.is_empty() { score = knobs.retreat_no_atk; }
        if opp_power >= my_hp && !my_bench.is_empty() && backup_ok && my_hp <= 80 { score = knobs.retreat_ko; }
        // wall escape
        if let (Some(my_id), Some(opp_id)) = (my_act.get("id").and_then(|x| x.as_i64()).map(|x| x as i32), opp_active.and_then(|a| a.get("id")).and_then(|x| x.as_i64()).map(|x| x as i32)) {
            if damage_prevented(my_id, opp_id, 1_000_000, index) {
                for p in &my_bench {
                    if let Some(pid) = p.get("id").and_then(|x| x.as_i64()).map(|x| x as i32) {
                        if !damage_prevented(pid, opp_id, 1_000_000, index) {
                            score = score.max(knobs.retreat_wall);
                            break;
                        }
                    }
                }
            }
        }
        return score;
    }
    if otype == 9 { // EVOLVE
        let idx = opt.get("index").and_then(|x| x.as_u64()).unwrap_or(0) as usize;
        let src = hand_id(obs, me_idx, idx);
        let mut score = knobs.evolve;
        if let Some(cid) = src {
            if plan.is_primary_line(cid) { score += 25; }
        }
        if opt.get("inPlayArea").and_then(|x| x.as_i64()) == Some(4) { score += 15; }
        return score;
    }
    if otype == 8 { // ATTACH
        let idx = opt.get("index").and_then(|x| x.as_u64()).unwrap_or(0) as usize;
        let src = hand_id(obs, me_idx, idx);
        let target_area = opt.get("inPlayArea").and_then(|x| x.as_i64()).unwrap_or(-1);
        let target_idx = opt.get("inPlayIndex").and_then(|x| x.as_u64()).unwrap_or(0) as usize;
        let target = pokemon_at(obs, me_idx, target_area, target_idx);
        let mut score = knobs.attach;
        if let Some(cid) = src {
            if let Some(c) = index.card(cid) {
                if c.ct == 2 { // TOOL
                    score = knobs.attach - 12;
                    if target_area == 4 { score += 8; }
                    return score;
                }
            }
        }
        if let Some(t) = target {
            if let Some(cost) = cheapest_attack_cost(t, index) {
                let have = t.get("energies").and_then(|x| x.as_array()).map(|a| a.len()).unwrap_or(0);
                if have + 1 >= cost && have < cost { score += knobs.enable_bonus; }
                else if have < cost { score += knobs.progress_bonus; }
                else { score += 4; }
            } else { score += 5; }
            if target_area == 4 { score += knobs.active_bonus; }
            if let Some(tid) = t.get("id").and_then(|x| x.as_i64()).map(|x| x as i32) {
                if plan.is_primary_line(tid) { score += 10; }
            }
            // wall awareness
            if let Some(opp_act) = opp_active {
                if let Some(opp_id) = opp_act.get("id").and_then(|x| x.as_i64()).map(|x| x as i32) {
                    if let Some(my_act) = active_pokemon(obs, me_idx) {
                        if let Some(my_id) = my_act.get("id").and_then(|x| x.as_i64()).map(|x| x as i32) {
                            if damage_prevented(my_id, opp_id, 1_000_000, index) {
                                if let Some(tid) = t.get("id").and_then(|x| x.as_i64()).map(|x| x as i32) {
                                    if !damage_prevented(tid, opp_id, 1_000_000, index) {
                                        score += knobs.attach_wall_bonus;
                                    } else {
                                        score += knobs.attach_wall_penalty;
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        return score;
    }
    if otype == 10 { return knobs.ability; } // ABILITY
    if otype == 7 { // PLAY
        let idx = opt.get("index").and_then(|x| x.as_u64()).unwrap_or(0) as usize;
        let cid = match hand_id(obs, me_idx, idx) { Some(c) => c, None => return 40 };
        let c = match index.card(cid) { Some(card) => card, None => return 40 };
        match c.ct {
            0 => {
                if my_bench.len() >= 5 { return 30; }
                if my_bench.is_empty() {
                    if let Some(my_act) = my_active {
                        if my_act.get("hp").and_then(|x| x.as_i64()).unwrap_or(100) <= 80 { return 335; }
                    }
                }
                let mut score = knobs.bench;
                if plan.is_primary_line(cid) { score += 10; }
                return score;
            },
            3 => {
                if obs["current"]["supporterPlayed"].as_bool().unwrap_or(false) { return 25; }
                return knobs.supporter + wall_gust_bonus(cid, index, obs, me_idx, opp_idx) + gust_lethal_bonus(cid, index, obs, me_idx, opp_idx, deck) + retrieval_bonus(cid, index, obs, me_idx, deck);
            },
            1 => {
                return knobs.item + wall_gust_bonus(cid, index, obs, me_idx, opp_idx) + gust_lethal_bonus(cid, index, obs, me_idx, opp_idx, deck) + retrieval_bonus(cid, index, obs, me_idx, deck);
            },
            4 => {
                if obs["current"]["stadiumPlayed"].as_bool().unwrap_or(false) { return 25; }
                if let Some(stadium) = obs["current"].get("stadium").and_then(|x| x.as_array()) {
                    if !stadium.is_empty() { return 150; }
                }
                return knobs.stadium;
            },
            5 | 6 => return 40,
            _ => return 200,
        }
    }
    if otype == 11 { return 20; } // DISCARD
    60
}

fn score_wanted_card(cid: i32, index: &CardIndex, plan: &Plan, obs: &Value, me_idx: usize) -> i32 {
    let c = match index.card(cid) { Some(card) => card, None => return 50 };
    match c.ct {
        0 => {
            let mut score = 100 + plan_power(cid, index, plan) / 3;
            if bench_pokemons(obs, me_idx).is_empty() && c.b { score += 60; }
            score
        },
        3 => 95,
        1 => 90,
        4 => 45,
        2 => 55,
        5 => 40,
        6 => 60,
        _ => 60,
    }
}
fn discard_rank(cid: i32, index: &CardIndex, plan: &Plan, obs: &Value, me_idx: usize) -> i32 {
    let val = card_value(cid, index, plan);
    let copies = hand_cards(obs, me_idx).iter().filter(|h| h.get("id").and_then(|x| x.as_i64()).map(|x| x as i32) == Some(cid)).count() as i32;
    val - 6 * (copies - 1).max(0)
}
fn score_generic_card(opt: &Value, obs: &Value, me_idx: usize, opp_idx: usize, index: &CardIndex, plan: &Plan, deck: &[i32]) -> i32 {
    let ctx = obs_select(obs).get("context").and_then(|x| x.as_i64()).unwrap_or(0);
    let cid = sel_card_id(opt, obs, me_idx).unwrap_or(0);
    let owner = opt.get("playerIndex").and_then(|x| x.as_u64()).unwrap_or(me_idx as u64) as usize;
    let area = opt.get("area").and_then(|x| x.as_i64()).unwrap_or(-1);
    let idx = opt.get("index").and_then(|x| x.as_u64()).unwrap_or(0) as usize;
    let poke = pokemon_at(obs, owner, area, idx);

    match ctx {
        1 => { // SETUP_ACTIVE
            let hp = index.card(cid).map(|c| c.hp).unwrap_or(0);
            return 100 + plan_power(cid, index, plan) / 2 + hp / 4;
        },
        2 => return 100 + plan_power(cid, index, plan) / 3, // SETUP_BENCH
        5 | 6 => return 100 + plan_power(cid, index, plan) / 2, // TO_BENCH, TO_FIELD
        4 | 3 => { // TO_ACTIVE, SWITCH
            if let Some(p) = poke {
                let opp_active = active_pokemon(obs, opp_idx);
                return 400 + fighter_score(p, index, plan, &Knobs::default(), obs, opp_active) / 2;
            }
            return 100 + plan_power(cid, index, plan) / 2;
        },
        7 => return score_wanted_card(cid, index, plan, obs, me_idx), // TO_HAND
        8 | 10 | 9 | 11 | 20 => return 1000 - discard_rank(cid, index, plan, obs, me_idx), // DISCARD, TO_DECK_BOTTOM, TO_DECK, TO_PRIZE, DEVOLVE
        26 | 27 | 28 => return 1000 - plan_power(poke.and_then(|p| p.get("id")).and_then(|x| x.as_i64()).map(|x| x as i32).unwrap_or(0), index, plan) / 4, // DISCARD_ENERGY etc
        13 | 14 | 15 | 25 => { // DAMAGE_COUNTER etc
            // damage target scoring
            let owner2 = opt.get("playerIndex").and_then(|x| x.as_u64()).unwrap_or(me_idx as u64) as usize;
            let area2 = opt.get("area").and_then(|x| x.as_i64()).unwrap_or(-1);
            let idx2 = opt.get("index").and_then(|x| x.as_u64()).unwrap_or(0) as usize;
            if let Some(p) = pokemon_at(obs, owner2, area2, idx2) {
                let hp = p.get("hp").and_then(|x| x.as_i64()).unwrap_or(0) as i32;
                let cid2 = p.get("id").and_then(|x| x.as_i64()).map(|x| x as i32).unwrap_or(0);
                let mut score = 0;
                if owner2 == opp_idx {
                    score = 200 - (hp.min(200) / 2) as i32;
                    if area2 == 4 { score += 30; }
                    score += 20 * prize_value(cid2, index);
                    if hp <= 60 { score += 40; }
                } else { score = 20; }
                return score;
            }
            return 50;
        },
        16 | 17 => return 100 + plan_power(poke.and_then(|p| p.get("id")).and_then(|x| x.as_i64()).map(|x| x as i32).unwrap_or(0), index, plan) / 2, // REMOVE_DAMAGE_COUNTER, HEAL
        18 | 19 => return 100 + plan_power(cid, index, plan) / 2, // EVOLVES_FROM, EVOLVES_TO
        21 | 22 => return 100 + plan_power(cid, index, plan) / 3, // ATTACH_FROM, ATTACH_TO
        24 => return score_wanted_card(cid, index, plan, obs, me_idx), // LOOK
        12 => return 50, // NOT_MOVE
        _ => return score_wanted_card(cid, index, plan, obs, me_idx),
    }
}
fn score_generic_context(opt: &Value, obs: &Value, me_idx: usize, opp_idx: usize, index: &CardIndex, plan: &Plan, deck: &[i32], ctx: i64) -> i32 {
    match ctx {
        30 | 31 | 32 | 33 => { // DISCARD_ENERGY, TO_HAND_ENERGY, etc
            let poke = pokemon_at(obs, opt.get("playerIndex").and_then(|x| x.as_u64()).unwrap_or(me_idx as u64) as usize, opt.get("area").and_then(|x| x.as_i64()).unwrap_or(-1), opt.get("index").and_then(|x| x.as_u64()).unwrap_or(0) as usize);
            let base = plan_power(poke.and_then(|p| p.get("id")).and_then(|x| x.as_i64()).map(|x| x as i32).unwrap_or(0), index, plan) / 4;
            if ctx == 31 || ctx == 32 || ctx == 33 { return base; }
            return 1000 - base;
        },
        _ => score_generic_card(opt, obs, me_idx, opp_idx, index, plan, deck),
    }
}
fn score_yes_no(opt: &Value, obs: &Value, me_idx: usize, ctx: i64, _select: &Value) -> i32 {
    let is_yes = opt.get("type").and_then(|x| x.as_i64()) == Some(1);
    match ctx {
        41 => { // IS_FIRST
            let go_first = true; // default
            if go_first { if is_yes { 10 } else { 0 } } else { if is_yes { 0 } else { 10 } }
        },
        42 => { // MULLIGAN
            let has_basic = hand_cards(obs, me_idx).iter().any(|h| {
                if let Some(id) = h.get("id").and_then(|x| x.as_i64()).map(|x| x as i32) {
                    if let Some(c) = _global_index().and_then(|idx| idx.card(id)) { c.b } else { false }
                } else { false }
            });
            if has_basic { if is_yes { 0 } else { 10 } } else { if is_yes { 10 } else { 0 } }
        },
        43 | 44 | 45 | 46 => if is_yes { 10 } else { 0 },
        _ => if is_yes { 10 } else { 0 },
    }
}

// global index for mulligan check (hack)
static mut GLOBAL_INDEX_PTR: *const CardIndex = std::ptr::null();
fn _global_index() -> Option<&'static CardIndex> {
    unsafe { if GLOBAL_INDEX_PTR.is_null() { None } else { Some(&*GLOBAL_INDEX_PTR) } }
}
fn set_global_index(idx: &CardIndex) { unsafe { GLOBAL_INDEX_PTR = idx as *const CardIndex; } }

pub fn decide(obs: &Value, index: &CardIndex, plan: &Plan, knobs: &Knobs, deck: &[i32]) -> Vec<i32> {
    set_global_index(index);
    let select = obs_select(obs);
    if select.is_null() { return vec![]; }
    let options = match select.get("option").and_then(|x| x.as_array()) { Some(arr) => arr, None => return vec![] };
    let max_count = select.get("maxCount").and_then(|x| x.as_u64()).unwrap_or(0) as usize;
    let min_count = select.get("minCount").and_then(|x| x.as_u64()).unwrap_or(0) as usize;
    if max_count == 0 || options.is_empty() { return vec![]; }
    let stype = select.get("type").and_then(|x| x.as_i64()).unwrap_or(-1);
    let me_idx = obs["current"]["yourIndex"].as_u64().unwrap_or(0) as usize;
    let opp_idx = 1 - me_idx;

    let mut scored: Vec<(i32, usize)> = Vec::new();

    if stype == 0 { // MAIN
        for (i, opt) in options.iter().enumerate() {
            let s = score_main_option(opt, obs, me_idx, opp_idx, index, plan, knobs, deck);
            scored.push((s, i));
        }
    } else if [1,2,3,4,5,7,10].contains(&stype) {
        let ctx = select.get("context").and_then(|x| x.as_i64()).unwrap_or(0);
        for (i, opt) in options.iter().enumerate() {
            let s = score_generic_context(opt, obs, me_idx, opp_idx, index, plan, deck, ctx);
            scored.push((s, i));
        }
    } else if stype == 6 { // ATTACK
        for (i, opt) in options.iter().enumerate() {
            let dmg = opt.get("attackId").and_then(|x| x.as_i64()).map(|aid| {
                index.attack(aid as i32).map(|a| a.damage).unwrap_or(0)
            }).unwrap_or(0);
            scored.push((dmg as i32, i));
        }
    } else if stype == 8 { // COUNT
        let ctx = select.get("context").and_then(|x| x.as_i64()).unwrap_or(0);
        for (i, opt) in options.iter().enumerate() {
            let num = opt.get("number").and_then(|x| x.as_i64()).unwrap_or(0) as i32;
            let s = if [38,39,40].contains(&ctx) { num } else { -num.abs() };
            scored.push((s, i));
        }
    } else if stype == 9 { // YES_NO
        let ctx = select.get("context").and_then(|x| x.as_i64()).unwrap_or(0);
        for (i, opt) in options.iter().enumerate() {
            let s = score_yes_no(opt, obs, me_idx, ctx, select);
            scored.push((s, i));
        }
    } else {
        for i in 0..options.len() { scored.push((0, i)); }
    }

    scored.sort_by(|a,b| b.0.cmp(&a.0).then_with(|| a.1.cmp(&b.1)));
    let mut k = max_count.min(options.len());
    if k == 0 && min_count > 0 && !scored.is_empty() { k = 1; }
    let mut chosen: Vec<i32> = scored.iter().take(k).map(|(_, idx)| *idx as i32).collect();
    chosen.sort();
    chosen
}

// compatibility wrapper used by old full.rs
pub fn decide_legacy(obs: &Value, index: &CardIndex, knobs: &Knobs) -> Vec<i32> {
    // build dummy plan from empty deck
    let deck: Vec<i32> = vec![];
    let plan = Plan { counts: HashMap::new(), primary: None, line: HashSet::new(), primary_power: 0 };
    decide(obs, index, &plan, knobs, &deck)
}
