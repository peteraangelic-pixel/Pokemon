use serde_json::Value;
use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct Card {
    pub id: i32,
    pub name: String,
    pub ct: i32,
    pub pt: Option<i32>,
    pub hp: i32,
    pub w: Option<i32>,
    pub res: Option<i32>,
    pub en: Option<i32>,
    pub ex: bool,
    pub mex: bool,
    pub ace: bool,
    pub atk: Vec<i32>,
}

#[derive(Debug, Clone)]
pub struct Attack {
    pub id: i32,
    pub name: String,
    pub damage: i32,
    pub text: String,
}

pub struct CardIndex {
    pub cards: HashMap<i32, Card>,
    pub attacks: HashMap<i32, Attack>,
}

impl CardIndex {
    pub fn load(path: &str) -> anyhow::Result<Self> {
        let content = std::fs::read_to_string(path)?;
        let v: Value = serde_json::from_str(&content)?;
        let mut cards = HashMap::new();
        let mut attacks = HashMap::new();
        if let Some(cards_obj) = v["cards"].as_object() {
            for (k, val) in cards_obj {
                if let Ok(id) = k.parse::<i32>() {
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
                        atk: val["atk"].as_array().map(|arr| arr.iter().filter_map(|x| x.as_i64().map(|y| y as i32)).collect()).unwrap_or_default(),
                    };
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
                    };
                    attacks.insert(id, a);
                }
            }
        }
        Ok(Self { cards, attacks })
    }
    pub fn card(&self, id: i32) -> Option<&Card> { self.cards.get(&id) }
    pub fn attack(&self, id: i32) -> Option<&Attack> { self.attacks.get(&id) }
}

pub struct Knobs {
    pub supporter: i32,
    pub bench: i32,
    pub evolve: i32,
    pub attach: i32,
    pub attack: i32,
    pub attack_ko: i32,
    pub retreat_base: i32,
    pub wall_penalty: i32,
    pub progress_bonus: i32,
    pub enable_bonus: i32,
}
impl Default for Knobs {
    fn default() -> Self {
        Self { supporter: 340, bench: 320, evolve: 310, attach: 300, attack: 200, attack_ko: 260, retreat_base: 120, wall_penalty: -677, progress_bonus: 32, enable_bonus: 30 }
    }
}

pub fn estimate_damage(attack_id: i32, index: &CardIndex, obs: &Value, me_idx: usize) -> i32 {
    if let Some(atk) = index.attack(attack_id) {
        let mut dmg = atk.damage;
        if dmg == 0 && atk.text.contains("Basic {W} Energy") {
            let mut water_in_discard = 0;
            if let Some(players) = obs["current"]["players"].as_array() {
                if let Some(me) = players.get(me_idx) {
                    if let Some(discard) = me["discard"].as_array() {
                        for d in discard {
                            if let Some(id) = d["id"].as_i64() {
                                if let Some(card) = index.card(id as i32) {
                                    if card.en == Some(3) { water_in_discard += 1; }
                                }
                            }
                        }
                    }
                }
            }
            dmg = water_in_discard * 100;
        }
        dmg
    } else { 0 }
}

pub fn score_main_option(opt: &Value, obs: &Value, me_idx: usize, opp_idx: usize, index: &CardIndex, knobs: &Knobs) -> i32 {
    if opt.get("attackId").is_some() {
        let aid = opt["attackId"].as_i64().unwrap_or(0) as i32;
        let est = estimate_damage(aid, index, obs, me_idx);
        let opp_hp = obs["current"]["players"][opp_idx]["active"][0]["hp"].as_i64().unwrap_or(0) as i32;
        let ko = est > 0 && est >= opp_hp;
        let mut score = if ko { knobs.attack_ko } else { knobs.attack };
        score += (est.min(240) / 4) as i32;
        if ko {
            let opp_active_id = obs["current"]["players"][opp_idx]["active"][0]["id"].as_i64().unwrap_or(0) as i32;
            let prize = if let Some(c) = index.card(opp_active_id) { if c.ex || c.mex { 2 } else { 1 } } else { 1 };
            score += 25 * prize;
            if let Some(prize_arr) = obs["current"]["players"][me_idx]["prize"].as_array() {
                let remaining = prize_arr.iter().filter(|p| !p.is_null()).count();
                if remaining == 1 { score += 50; }
            }
        }
        if est == 0 {
            score -= 40;
            if let Some(atk) = index.attack(aid) {
                if atk.text.to_lowercase().contains("into your deck") { score += 45; }
            }
        }
        return score;
    }
    // EVOLVE type 9, ATTACH 8, RETREAT 12, PLAY 7, etc - from OptionType
    if let Some(t) = opt["type"].as_i64() {
        match t {
            9 => return knobs.evolve + 10, // EVOLVE
            8 => { // ATTACH
                let mut score = knobs.attach;
                if opt["inPlayArea"].as_i64() == Some(4) { score += 12; } // ACTIVE=4
                return score;
            },
            12 => return knobs.retreat_base, // RETREAT
            7 => return 200, // PLAY
            14 => return 0, // END
            _ => {}
        }
    }
    100
}

pub fn decide(obs: &Value, index: &CardIndex, knobs: &Knobs) -> Vec<i32> {
    let select = &obs["select"];
    if select.is_null() { return vec![]; }
    let options = match select["option"].as_array() { Some(arr) => arr, None => return vec![] };
    let max_count = select["maxCount"].as_i64().unwrap_or(0) as usize;
    let stype = select["type"].as_i64().unwrap_or(0);

    if max_count == 0 || options.is_empty() { return vec![]; }

    // For non-MAIN selects (CARD=1, ENERGY=4, etc), use first max_count (safe fallback)
    // Only MAIN (0) needs heuristic scoring
    if stype != 0 {
        // For YES_NO (9), COUNT (8), etc, first option is usually safe
        // But for CARD selects, we could score wanted cards - for now first
        return (0..max_count.min(options.len())).map(|i| i as i32).collect();
    }

    let me_idx = obs["current"]["yourIndex"].as_i64().unwrap_or(0) as usize;
    let opp_idx = 1 - me_idx;
    let mut scored: Vec<(i32, usize)> = Vec::new();
    for (i, opt) in options.iter().enumerate() {
        let s = score_main_option(opt, obs, me_idx, opp_idx, index, knobs);
        scored.push((s, i));
    }
    scored.sort_by(|a,b| b.0.cmp(&a.0));
    let mut result: Vec<i32> = Vec::new();
    for k in 0..max_count.min(scored.len()) { result.push(scored[k].1 as i32); }
    result.sort();
    result
}
