use serde_json::Value;
use std::collections::HashMap;

pub const DS: usize = 96;
pub const DO: usize = 64;
pub const MAX_OPT: usize = 32;

fn f64_from(v: &Value) -> f64 {
    if let Some(n) = v.as_f64() { n } else if let Some(n) = v.as_i64() { n as f64 } else { 0.0 }
}

fn get_f64(obj: &Value, key: &str) -> f64 {
    obj.get(key).map(|x| f64_from(x)).unwrap_or(0.0)
}

fn get_i64(obj: &Value, key: &str) -> i64 {
    obj.get(key).and_then(|x| x.as_i64()).unwrap_or(0)
}

#[derive(Debug, Clone)]
pub struct CardRec {
    pub ct: i64,
    pub b: i64,
    pub et: f64,
    pub hp: f64,
    pub ex: f64,
    pub mex: f64,
    pub ace: f64,
    pub rc: f64,
    pub en: f64,
    pub atk: Vec<i64>,
}

#[derive(Debug, Clone)]
pub struct AttackRec {
    pub d: f64,
    pub e_len: f64,
}

pub struct Featurizer {
    pub cards: HashMap<String, CardRec>,
    pub attacks: HashMap<String, AttackRec>,
}

impl Featurizer {
    pub fn load(path: &str) -> anyhow::Result<Self> {
        let content = std::fs::read_to_string(path)?;
        let v: Value = serde_json::from_str(&content)?;
        let mut cards = HashMap::new();
        let mut attacks = HashMap::new();
        if let Some(obj) = v.get("cards").and_then(|x| x.as_object()) {
            for (k, val) in obj {
                let atk = val.get("atk").and_then(|a| a.as_array()).map(|arr| arr.iter().filter_map(|x| x.as_i64()).collect()).unwrap_or_default();
                let rec = CardRec {
                    ct: get_i64(val, "ct"),
                    b: get_i64(val, "b"),
                    et: get_f64(val, "et"),
                    hp: get_f64(val, "hp"),
                    ex: get_f64(val, "ex"),
                    mex: get_f64(val, "mex"),
                    ace: get_f64(val, "ace"),
                    rc: get_f64(val, "rc"),
                    en: get_f64(val, "en"),
                    atk,
                };
                cards.insert(k.clone(), rec);
            }
        }
        if let Some(obj) = v.get("attacks").and_then(|x| x.as_object()) {
            for (k, val) in obj {
                let e_len = val.get("e").and_then(|a| a.as_array()).map(|a| a.len() as f64).unwrap_or(0.0);
                let rec = AttackRec {
                    d: get_f64(val, "d"),
                    e_len,
                };
                attacks.insert(k.clone(), rec);
            }
        }
        Ok(Self { cards, attacks })
    }

    fn card(&self, cid: Option<i64>) -> Option<&CardRec> {
        cid.and_then(|id| self.cards.get(&id.to_string()))
    }

    fn attack(&self, aid: Option<i64>) -> Option<&AttackRec> {
        aid.and_then(|id| self.attacks.get(&id.to_string()))
    }

    pub fn card_feats(&self, cid: Option<i64>) -> [f64; 14] {
        let mut out = [0.0; 14];
        if let Some(c) = self.card(cid) {
            let mut best_dmg = 0.0;
            let mut min_cost = 4.0;
            for aid in &c.atk {
                if let Some(a) = self.attacks.get(&aid.to_string()) {
                    if a.d > best_dmg { best_dmg = a.d; }
                    if a.e_len < min_cost { min_cost = a.e_len; }
                }
            }
            let prize = if c.mex > 0.5 { 3.0 } else if c.ex > 0.5 { 2.0 } else { 1.0 };
            out[0] = if c.ct == 0 { 1.0 } else { 0.0 };
            out[1] = if c.b != 0 { 1.0 } else { 0.0 };
            out[2] = c.et / 3.0;
            out[3] = c.hp / 350.0;
            out[4] = if c.ex > 0.5 { 1.0 } else { 0.0 };
            out[5] = if c.mex > 0.5 { 1.0 } else { 0.0 };
            out[6] = if c.ace > 0.5 { 1.0 } else { 0.0 };
            out[7] = c.rc / 4.0;
            out[8] = best_dmg / 300.0;
            out[9] = min_cost / 4.0;
            out[10] = prize / 3.0;
            out[11] = c.en / 12.0;
            out[12] = if c.ct == 1 || c.ct == 2 { 1.0 } else { 0.0 };
            out[13] = if c.ct == 3 { 1.0 } else { 0.0 };
        }
        out
    }

    fn poke_block(&self, poke: Option<&Value>) -> [f64; 10] {
        let mut out = [0.0; 10];
        if let Some(p) = poke {
            let cid = p.get("id").and_then(|x| x.as_i64());
            let c = self.card(cid);
            let hp = c.map(|cc| cc.hp).unwrap_or(0.0);
            let dmg = p.get("damage").map(|x| f64_from(x)).unwrap_or(0.0);
            let dmg_adj = if dmg > hp && hp > 0.0 { dmg / 10.0 } else { dmg };
            let cur_hp = if hp > 0.0 { (hp - dmg_adj).max(0.0) } else { 0.0 };
            let n_en = p.get("energies").and_then(|x| x.as_array()).map(|a| a.len() as f64).unwrap_or(0.0);
            let mut best = 0.0;
            if let Some(cc) = c {
                for aid in &cc.atk {
                    if let Some(a) = self.attacks.get(&aid.to_string()) {
                        if a.d > best { best = a.d; }
                    }
                }
            }
            let ex = c.map(|cc| if cc.ex > 0.5 { 1.0 } else { 0.0 }).unwrap_or(0.0);
            let mex = c.map(|cc| if cc.mex > 0.5 { 1.0 } else { 0.0 }).unwrap_or(0.0);
            let prize = if mex > 0.5 { 3.0 } else if ex > 0.5 { 2.0 } else { 1.0 };
            out[0] = if hp > 0.0 { cur_hp / hp } else { 0.0 };
            out[1] = hp / 350.0;
            out[2] = (n_en.min(8.0)) / 8.0;
            out[3] = c.map(|cc| cc.et / 3.0).unwrap_or(0.0);
            out[4] = ex;
            out[5] = mex;
            out[6] = prize / 3.0;
            out[7] = best / 300.0;
            out[8] = if p.get("id").is_some() { 1.0 } else { 0.0 };
            let tool = p.get("tool");
            out[9] = match tool {
                Some(v) if v.is_number() => f64_from(v).min(1.0),
                Some(v) if !v.is_null() => 1.0,
                _ => 0.0,
            };
        }
        out
    }

    fn board_block(&self, player: Option<&Value>) -> [f64; 18] {
        let mut out = [0.0; 18];
        if let Some(pl) = player {
            let active = pl.get("active").and_then(|a| a.as_array()).and_then(|arr| arr.get(0)).filter(|x| !x.is_null());
            let act = self.poke_block(active);
            out[0..10].copy_from_slice(&act);
            let bench = pl.get("bench").and_then(|b| b.as_array()).map(|arr| arr.iter().filter(|x| !x.is_null()).collect::<Vec<_>>()).unwrap_or_default();
            if !bench.is_empty() {
                let mut blocks: Vec<[f64;10]> = Vec::new();
                for b in bench.iter().take(5) {
                    blocks.push(self.poke_block(Some(b)));
                }
                let n = blocks.len() as f64;
                out[10] = n / 5.0;
                out[11] = blocks.iter().map(|bb| bb[0]).sum::<f64>() / 5.0;
                out[12] = blocks.iter().map(|bb| bb[7]).fold(0.0, f64::max);
                out[13] = blocks.iter().map(|bb| bb[2]).sum::<f64>() / 2.0;
                out[14] = blocks.iter().map(|bb| bb[4] + bb[5]).sum::<f64>() / 5.0;
                out[15] = blocks.iter().map(|bb| bb[6]).sum::<f64>() / 2.0;
                out[16] = blocks.iter().map(|bb| bb[1]).fold(0.0, f64::max);
                out[17] = 1.0;
            }
        }
        out
    }

    pub fn state_feats(&self, obs: &Value, me: usize) -> [f64; DS] {
        let mut out = [0.0; DS];
        let cur = obs.get("current").unwrap_or(&Value::Null);
        let players = cur.get("players").and_then(|p| p.as_array());
        if players.is_none() || players.as_ref().unwrap().len() < 2 {
            return out;
        }
        let players = players.unwrap();
        let opp = 1 - me;
        if me >= players.len() || opp >= players.len() { return out; }
        let mp = &players[me];
        let op = &players[opp];
        let mut idx = 0;
        let turn = cur.get("turn").map(|x| f64_from(x)).unwrap_or(0.0).min(40.0) / 40.0;
        out[idx] = turn; idx+=1;
        out[idx] = if cur.get("firstPlayer").and_then(|x| x.as_u64()).unwrap_or(99) as usize == me { 1.0 } else { 0.0 }; idx+=1;
        out[idx] = if cur.get("supporterPlayed").and_then(|x| x.as_bool()).unwrap_or(false) {1.0} else {0.0}; idx+=1;
        out[idx] = if cur.get("energyAttached").and_then(|x| x.as_bool()).unwrap_or(false) {1.0} else {0.0}; idx+=1;
        out[idx] = if cur.get("retreated").and_then(|x| x.as_bool()).unwrap_or(false) {1.0} else {0.0}; idx+=1;
        out[idx] = if cur.get("stadium").is_some() && !cur.get("stadium").unwrap().is_null() {1.0} else {0.0}; idx+=1;
        let prize_me = mp.get("prize").and_then(|x| x.as_array()).map(|a| a.len()).unwrap_or(0);
        let prize_op = op.get("prize").and_then(|x| x.as_array()).map(|a| a.len()).unwrap_or(0);
        out[idx] = (6 - prize_me.min(6)) as f64 / 6.0; idx+=1;
        out[idx] = (6 - prize_op.min(6)) as f64 / 6.0; idx+=1;
        out[idx] = mp.get("deckCount").map(|x| f64_from(x)).unwrap_or(0.0) / 60.0; idx+=1;
        out[idx] = op.get("deckCount").map(|x| f64_from(x)).unwrap_or(0.0) / 60.0; idx+=1;
        let hand_me = mp.get("handCount").map(|x| f64_from(x)).unwrap_or(mp.get("hand").and_then(|h| h.as_array()).map(|a| a.len() as f64).unwrap_or(0.0)).min(15.0) / 15.0;
        let hand_op = op.get("handCount").map(|x| f64_from(x)).unwrap_or(op.get("hand").and_then(|h| h.as_array()).map(|a| a.len() as f64).unwrap_or(0.0)).min(15.0) / 15.0;
        out[idx] = hand_me; idx+=1;
        out[idx] = hand_op; idx+=1;
        let disc = mp.get("discard").and_then(|d| d.as_array()).map(|a| a.len()).unwrap_or(0);
        let mut water_disc = 0;
        if let Some(arr) = mp.get("discard").and_then(|d| d.as_array()) {
            for d in arr {
                if let Some(id) = d.get("id").and_then(|x| x.as_i64()) {
                    if let Some(c) = self.cards.get(&id.to_string()) {
                        if (c.en as i64) == 3 { water_disc+=1; }
                    }
                }
            }
        }
        out[idx] = (disc.min(40) as f64) / 40.0; idx+=1;
        out[idx] = (water_disc.min(20) as f64) / 20.0; idx+=1;
        out[idx] = cur.get("turnActionCount").map(|x| f64_from(x)).unwrap_or(0.0).min(20.0)/20.0; idx+=1;
        out[idx] = if cur.get("yourIndex").and_then(|x| x.as_u64()).unwrap_or(0) as usize == me {1.0} else {0.0}; idx+=1;
        let bb_me = self.board_block(Some(mp));
        for i in 0..18 { out[idx+i] = bb_me[i]; } idx+=18;
        let bb_op = self.board_block(Some(op));
        for i in 0..18 { out[idx+i] = bb_op[i]; } idx+=18;
        let hand = mp.get("hand").and_then(|h| h.as_array());
        let hand_len = hand.map(|a| a.len()).unwrap_or(0);
        let mut basics = 0;
        let mut energies = 0;
        if let Some(arr) = hand {
            for h in arr {
                if let Some(id) = h.get("id").and_then(|x| x.as_i64()) {
                    if let Some(c) = self.cards.get(&id.to_string()) {
                        if c.b != 0 { basics+=1; }
                        if c.ct == 5 || c.ct == 6 { energies+=1; }
                    }
                }
            }
        }
        out[idx] = (hand_len.min(15) as f64)/15.0; idx+=1;
        out[idx] = (basics.min(6) as f64)/6.0; idx+=1;
        out[idx] = (energies.min(8) as f64)/8.0; idx+=1;
        // rest padded 0
        out
    }

    fn resolve_card(&self, opt: &Value, obs: &Value, me: usize) -> Option<i64> {
        if let Some(cid) = opt.get("cardId").and_then(|x| x.as_i64()) {
            if opt.get("area").is_none() { return Some(cid); }
        }
        let area = opt.get("area").and_then(|x| x.as_i64())?;
        let idx = opt.get("index").and_then(|x| x.as_u64())? as usize;
        let cur = obs.get("current")?;
        let players = cur.get("players").and_then(|p| p.as_array())?;
        let owner = opt.get("playerIndex").and_then(|x| x.as_u64()).unwrap_or(me as u64) as usize;
        if area == 2 && owner == me {
            let hand = players.get(me)?.get("hand").and_then(|h| h.as_array())?;
            return hand.get(idx)?.get("id").and_then(|x| x.as_i64());
        }
        if area == 1 && owner == me {
            let deck = obs.get("select").and_then(|s| s.get("deck")).and_then(|d| d.as_array())?;
            if idx < deck.len() {
                let e = &deck[idx];
                if let Some(id) = e.get("id").and_then(|x| x.as_i64()) { return Some(id); }
                if let Some(id) = e.as_i64() { return Some(id); }
            }
            return None;
        }
        let zone = if area == 4 { "active" } else if area == 5 { "bench" } else { return None; };
        if owner < players.len() {
            let z = players.get(owner)?.get(zone).and_then(|x| x.as_array())?;
            return z.get(idx)?.get("id").and_then(|x| x.as_i64());
        }
        None
    }

    fn target_poke<'a>(&self, opt: &Value, obs: &'a Value, me: usize) -> (Option<usize>, Option<&'a Value>) {
        let area = opt.get("inPlayArea").and_then(|x| x.as_i64());
        let idx = opt.get("inPlayIndex").and_then(|x| x.as_u64()).map(|x| x as usize);
        if area.is_none() || idx.is_none() { return (None, None); }
        let area = area.unwrap();
        let idx = idx.unwrap();
        if area != 4 && area != 5 { return (None, None); }
        let cur = match obs.get("current") { Some(c) => c, None => return (None, None) };
        let players = match cur.get("players").and_then(|p| p.as_array()) { Some(p) => p, None => return (None, None) };
        let zone = if area == 4 { "active" } else { "bench" };
        // prefer me first
        for owner in [me, 1-me] {
            if owner < players.len() {
                if let Some(z) = players.get(owner).and_then(|pl| pl.get(zone)).and_then(|x| x.as_array()) {
                    if idx < z.len() {
                        let v = &z[idx];
                        if !v.is_null() {
                            return (Some(owner), Some(v));
                        }
                    }
                }
            }
        }
        (None, None)
    }

    pub fn option_feats(&self, opt: &Value, obs: &Value, me: usize) -> [f64; DO] {
        let mut out = [0.0; DO];
        let otype = opt.get("type").and_then(|x| x.as_i64()).unwrap_or(0) as usize;
        if otype < 16 { out[otype] = 1.0; }
        let area = opt.get("area").and_then(|x| x.as_i64()).unwrap_or(0) as usize;
        if area < 13 { out[16+area] = 1.0; }
        let ipa = opt.get("inPlayArea").and_then(|x| x.as_i64()).unwrap_or(0) as usize;
        if ipa < 13 { out[29+ipa] = 1.0; }
        let cid = self.resolve_card(opt, obs, me);
        let cf = self.card_feats(cid);
        for i in 0..14 { out[42+i] = cf[i]; }
        if otype == 13 {
            let aid = opt.get("attackId").and_then(|x| x.as_i64());
            if let Some(a) = self.attack(aid) {
                let dmg = a.d;
                let cost = a.e_len;
                out[56] = dmg / 300.0;
                out[57] = cost / 4.0;
                // lethal check vs opp active
                let cur = obs.get("current");
                if let Some(cur) = cur {
                    if let Some(players) = cur.get("players").and_then(|p| p.as_array()) {
                        let opp = 1-me;
                        if opp < players.len() {
                            let opp_active = players[opp].get("active").and_then(|a| a.as_array()).and_then(|arr| arr.get(0)).filter(|x| !x.is_null());
                            if let Some(oa) = opp_active {
                                let blk = self.poke_block(Some(oa));
                                let cur_hp_ratio = blk[0];
                                let hp_norm = blk[1];
                                let cur_hp_abs = cur_hp_ratio * hp_norm * 350.0;
                                if dmg >= cur_hp_abs && dmg > 0.0 {
                                    out[58] = 1.0;
                                }
                                out[59] = (dmg/300.0) * blk[6];
                            }
                        }
                    }
                }
            }
        }
        let (towner, tpoke) = self.target_poke(opt, obs, me);
        if let Some(tp) = tpoke {
            let tb = self.poke_block(Some(tp));
            out[60] = tb[0];
            out[61] = tb[2];
            out[62] = tb[6];
            out[63] = if towner == Some(me) { 1.0 } else { 0.0 };
        }
        out
    }
}
