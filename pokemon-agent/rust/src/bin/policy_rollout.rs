// policy_rollout: fast self-play rollouts of the learned option-scorer policy.
// - one libcg.so COPY per rayon thread (engine is not thread-safe)
// - featurizer mirrors tools/policy_feats.py (DS=96, DO=64, MAX_OPT=32)
// - modes: train (log decisions, eps-greedy) / eval (argmax, winrate only)
use anyhow::Result;
use clap::Parser;
use libloading::{Library, Symbol};
use rand::rngs::StdRng;
use rand::{Rng, SeedableRng};
use rayon::prelude::*;
use serde_json::Value;
use std::cell::RefCell;
use std::collections::HashMap;
use std::ffi::CStr;
use std::fs::File;
use std::io::{BufWriter, Write};
use std::os::raw::{c_char, c_int, c_uchar, c_void};
use std::path::PathBuf;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Mutex;

const DS: usize = 96;
const DO: usize = 64;
const MAX_OPT: usize = 32;

#[repr(C)]
#[derive(Clone, Copy)]
struct StartData {
    battle_ptr: *mut c_void,
    error_player: c_int,
    error_type: c_int,
}

#[repr(C)]
struct SerialData {
    json: *const c_char,
    _data: *const c_uchar,
    _count: c_int,
    _select_player: c_int,
}

struct Engine {
    _lib: Library,
    battle_ptr: *mut c_void,
    init_done: bool,
}

impl Engine {
    fn new(lib_path: &str) -> Result<Self> {
        unsafe {
            let lib = Library::new(lib_path)?;
            {
                let init: Symbol<unsafe extern "C" fn()> = lib.get(b"GameInitialize")?;
                init();
            }
            Ok(Self { _lib: lib, battle_ptr: std::ptr::null_mut(), init_done: true })
        }
    }
    fn battle_start(&mut self, cards: &[c_int]) -> Result<Value> {
        unsafe {
            let func: Symbol<unsafe extern "C" fn(*const c_int) -> StartData> =
                self._lib.get(b"BattleStart")?;
            let sd = func(cards.as_ptr());
            if sd.battle_ptr.is_null() {
                anyhow::bail!("BattleStart null");
            }
            self.battle_ptr = sd.battle_ptr;
            self.get_data()
        }
    }
    fn get_data(&self) -> Result<Value> {
        unsafe {
            let func: Symbol<unsafe extern "C" fn(*mut c_void) -> SerialData> =
                self._lib.get(b"GetBattleData")?;
            let sd = func(self.battle_ptr);
            if sd.json.is_null() {
                anyhow::bail!("null json");
            }
            let s = CStr::from_ptr(sd.json).to_string_lossy();
            Ok(serde_json::from_str(&s)?)
        }
    }
    fn select(&self, indices: &[i32]) -> Result<Value> {
        unsafe {
            let func: Symbol<unsafe extern "C" fn(*mut c_void, *const c_int, c_int) -> c_int> =
                self._lib.get(b"Select")?;
            let ret = func(self.battle_ptr, indices.as_ptr(), indices.len() as c_int);
            if ret != 0 {
                anyhow::bail!("Select error {}", ret);
            }
            self.get_data()
        }
    }
    fn finish(&mut self) {
        if !self.battle_ptr.is_null() {
            unsafe {
                if let Ok(func) = self._lib.get::<unsafe extern "C" fn(*mut c_void)>(b"BattleFinish") {
                    func(self.battle_ptr);
                }
            }
            self.battle_ptr = std::ptr::null_mut();
        }
    }
}

impl Drop for Engine {
    fn drop(&mut self) {
        self.finish();
    }
}

// ---------------- card index ----------------
#[derive(Clone, Default)]
struct CardRec {
    ct: i64,
    b: bool,
    et: f32,
    hp: f32,
    ex: bool,
    mex: bool,
    ace: bool,
    rc: f32,
    en: f32,
    best_dmg: f32,
    min_cost: f32,
}

struct Index {
    cards: HashMap<i64, CardRec>,
    attacks: HashMap<i64, (f32, f32)>, // dmg, cost
}

fn load_index(path: &str) -> Result<Index> {
    let txt = std::fs::read_to_string(path)?;
    let v: Value = serde_json::from_str(&txt)?;
    let mut attacks = HashMap::new();
    if let Some(a) = v.get("attacks").and_then(|x| x.as_object()) {
        for (k, av) in a {
            if let Ok(id) = k.parse::<i64>() {
                let dmg = av.get("d").and_then(|x| x.as_f64()).unwrap_or(0.0) as f32;
                let cost = av.get("e").and_then(|x| x.as_array()).map(|e| e.len()).unwrap_or(0) as f32;
                attacks.insert(id, (dmg, cost));
            }
        }
    }
    let mut cards = HashMap::new();
    if let Some(c) = v.get("cards").and_then(|x| x.as_object()) {
        for (k, cv) in c {
            if let Ok(id) = k.parse::<i64>() {
                let truthy = |k: &str| -> bool {
                    match cv.get(k) {
                        Some(Value::Bool(b)) => *b,
                        Some(Value::Number(n)) => n.as_i64().unwrap_or(0) != 0,
                        _ => false,
                    }
                };
                let mut rec = CardRec {
                    ct: cv.get("ct").and_then(|x| x.as_i64()).unwrap_or(-1),
                    b: truthy("b"),
                    et: cv.get("et").and_then(|x| x.as_f64()).unwrap_or(0.0) as f32,
                    hp: cv.get("hp").and_then(|x| x.as_f64()).unwrap_or(0.0) as f32,
                    ex: truthy("ex"),
                    mex: truthy("mex"),
                    ace: truthy("ace"),
                    rc: cv.get("rc").and_then(|x| x.as_f64()).unwrap_or(0.0) as f32,
                    en: cv.get("en").and_then(|x| x.as_f64()).unwrap_or(0.0) as f32,
                    best_dmg: 0.0,
                    min_cost: 4.0,
                };
                if let Some(atk) = cv.get("atk").and_then(|x| x.as_array()) {
                    let mut mc = 4.0f32;
                    let mut bd = 0.0f32;
                    for aid in atk {
                        if let Some(aid) = aid.as_i64() {
                            if let Some((d, cst)) = attacks.get(&aid) {
                                bd = bd.max(*d);
                                mc = mc.min(*cst);
                            }
                        }
                    }
                    rec.best_dmg = bd;
                    rec.min_cost = mc;
                }
                cards.insert(id, rec);
            }
        }
    }
    Ok(Index { cards, attacks })
}

// ---------------- featurizer (mirror of tools/policy_feats.py) ----------------
fn gf(v: &Value, k: &str) -> f32 {
    v.get(k).and_then(|x| x.as_f64()).unwrap_or(0.0) as f32
}
fn gi(v: &Value, k: &str) -> i64 {
    v.get(k).and_then(|x| x.as_i64()).unwrap_or(0)
}
fn gb(v: &Value, k: &str) -> bool {
    v.get(k).and_then(|x| x.as_bool()).unwrap_or(false)
}
fn arr<'a>(v: &'a Value, k: &str) -> &'a [Value] {
    v.get(k).and_then(|x| x.as_array()).map(|a| a.as_slice()).unwrap_or(&[])
}

struct Feat<'a> {
    ix: &'a Index,
}

impl<'a> Feat<'a> {
    fn card_feats(&self, cid: Option<i64>, out: &mut [f32]) {
        let rec = cid.and_then(|c| self.ix.cards.get(&c));
        if let Some(r) = rec {
            let prize = if r.mex { 3.0 } else if r.ex { 2.0 } else { 1.0 };
            out[0] = if r.ct == 0 { 1.0 } else { 0.0 };
            out[1] = if r.b { 1.0 } else { 0.0 };
            out[2] = r.et / 3.0;
            out[3] = r.hp / 350.0;
            out[4] = if r.ex { 1.0 } else { 0.0 };
            out[5] = if r.mex { 1.0 } else { 0.0 };
            out[6] = if r.ace { 1.0 } else { 0.0 };
            out[7] = r.rc / 4.0;
            out[8] = r.best_dmg / 300.0;
            out[9] = r.min_cost / 4.0;
            out[10] = prize / 3.0;
            out[11] = r.en / 12.0;
            out[12] = if r.ct == 1 || r.ct == 2 { 1.0 } else { 0.0 };
            out[13] = if r.ct == 3 { 1.0 } else { 0.0 };
        }
    }

    fn poke_block(&self, poke: Option<&Value>) -> [f32; 10] {
        let mut o = [0f32; 10];
        if let Some(p) = poke {
            if p.is_null() {
                return o;
            }
            let cid = p.get("id").and_then(|x| x.as_i64());
            let rec = cid.and_then(|c| self.ix.cards.get(&c));
            let (et, ex, mex, best) = match rec {
                Some(r) => (r.et, r.ex, r.mex, r.best_dmg),
                None => (0.0, false, false, 0.0),
            };
            let max_hp = {
                let m = gf(p, "maxHp");
                if m > 0.0 { m } else { rec.map(|r| r.hp).unwrap_or(0.0) }
            };
            let cur_hp = if p.get("hp").is_some() { gf(p, "hp") } else { max_hp };
            let n_en = arr(p, "energies").len() as f32;
            let prize = if mex { 3.0 } else if ex { 2.0 } else { 1.0 };
            o[0] = if max_hp > 0.0 { cur_hp / max_hp } else { 0.0 };
            o[1] = max_hp / 350.0;
            o[2] = n_en.min(8.0) / 8.0;
            o[3] = et / 3.0;
            o[4] = if ex { 1.0 } else { 0.0 };
            o[5] = if mex { 1.0 } else { 0.0 };
            o[6] = prize / 3.0;
            o[7] = best / 300.0;
            o[8] = if cid.is_some() { 1.0 } else { 0.0 };
            o[9] = if !arr(p, "tools").is_empty() { 1.0 } else { 0.0 };
        }
        o
    }

    fn board_block(&self, player: &Value) -> [f32; 18] {
        let mut out = [0f32; 18];
        let active = arr(player, "active");
        let act = self.poke_block(active.first());
        out[..10].copy_from_slice(&act);
        let bench: Vec<&Value> = arr(player, "bench").iter().filter(|p| !p.is_null()).collect();
        if !bench.is_empty() {
            let blocks: Vec<[f32; 10]> = bench.iter().take(5).map(|p| self.poke_block(Some(p))).collect();
            let mut agg = [0f32; 8];
            agg[0] = blocks.len() as f32 / 5.0;
            agg[1] = blocks.iter().map(|b| b[0]).sum::<f32>() / 5.0;
            agg[2] = blocks.iter().map(|b| b[7]).fold(0.0f32, f32::max);
            agg[3] = blocks.iter().map(|b| b[2]).sum::<f32>() / 2.0;
            agg[4] = blocks.iter().map(|b| b[4] + b[5]).sum::<f32>() / 5.0;
            agg[5] = blocks.iter().map(|b| b[6]).sum::<f32>() / 2.0;
            agg[6] = blocks.iter().map(|b| b[1]).fold(0.0f32, f32::max);
            agg[7] = 1.0;
            out[10..].copy_from_slice(&agg);
        }
        out
    }

    fn state_feats(&self, obs: &Value, me: usize) -> [f32; DS] {
        let mut out = [0f32; DS];
        let cur = match obs.get("current") {
            Some(c) => c.clone(),
            None => return out,
        };
        let players = arr(&cur, "players");
        if players.len() < 2 {
            return out;
        }
        let opp = 1 - me;
        let (mp, op) = (&players[me], &players[opp]);
        let mut v: Vec<f32> = Vec::with_capacity(DS);
        v.push(gf(&cur, "turn").min(40.0) / 40.0);
        v.push(if gi(&cur, "firstPlayer") == me as i64 { 1.0 } else { 0.0 });
        v.push(if gb(&cur, "supporterPlayed") { 1.0 } else { 0.0 });
        v.push(if gb(&cur, "energyAttached") { 1.0 } else { 0.0 });
        v.push(if gb(&cur, "retreated") { 1.0 } else { 0.0 });
        v.push(if cur.get("stadium").map(|s| !s.is_null()).unwrap_or(false) { 1.0 } else { 0.0 });
        v.push((6 - arr(mp, "prize").len() as i64).max(0) as f32 / 6.0);
        v.push((6 - arr(op, "prize").len() as i64).max(0) as f32 / 6.0);
        v.push(gf(mp, "deckCount") / 60.0);
        v.push(gf(op, "deckCount") / 60.0);
        let hand_n = |p: &Value| -> f32 {
            let hc = p.get("handCount").and_then(|x| x.as_f64())
                .unwrap_or(arr(p, "hand").len() as f64) as f32;
            hc.min(15.0) / 15.0
        };
        v.push(hand_n(mp));
        v.push(hand_n(op));
        let disc = arr(mp, "discard");
        v.push((disc.len() as f32).min(40.0) / 40.0);
        let water_disc = disc.iter().filter(|d| {
            d.get("id").and_then(|x| x.as_i64())
                .and_then(|id| self.ix.cards.get(&id))
                .map(|r| r.en == 3.0)
                .unwrap_or(false)
        }).count();
        v.push((water_disc as f32).min(20.0) / 20.0);
        v.push(gf(&cur, "turnActionCount").min(20.0) / 20.0);
        v.push(if gi(&cur, "yourIndex") == me as i64 { 1.0 } else { 0.0 });
        v.extend_from_slice(&self.board_block(mp));
        v.extend_from_slice(&self.board_block(op));
        let hand = arr(mp, "hand");
        let basics = hand.iter().filter(|h| {
            h.get("id").and_then(|x| x.as_i64()).and_then(|id| self.ix.cards.get(&id)).map(|r| r.b).unwrap_or(false)
        }).count();
        let energies = hand.iter().filter(|h| {
            h.get("id").and_then(|x| x.as_i64()).and_then(|id| self.ix.cards.get(&id)).map(|r| r.ct == 5 || r.ct == 6).unwrap_or(false)
        }).count();
        v.push((hand.len() as f32).min(15.0) / 15.0);
        v.push((basics as f32).min(6.0) / 6.0);
        v.push((energies as f32).min(8.0) / 8.0);
        for i in 0..DS.min(v.len()) {
            out[i] = v[i];
        }
        out
    }

    fn resolve_card(&self, opt: &Value, obs: &Value, me: usize) -> Option<i64> {
        if let Some(cid) = opt.get("cardId").and_then(|x| x.as_i64()) {
            if opt.get("area").is_none() || opt.get("area").map(|a| a.is_null()).unwrap_or(false) {
                return Some(cid);
            }
        }
        let area = opt.get("area").and_then(|x| x.as_i64());
        let idx = opt.get("index").and_then(|x| x.as_i64())? as usize;
        let owner = opt.get("playerIndex").and_then(|x| x.as_i64()).unwrap_or(me as i64) as usize;
        let cur = obs.get("current")?;
        let players = arr(cur, "players");
        match area {
            Some(2) if owner == me => {
                let hand = arr(&players[me], "hand");
                hand.get(idx).and_then(|h| h.get("id")).and_then(|x| x.as_i64())
            }
            Some(1) if owner == me => {
                let deck = obs.get("select").and_then(|s| s.get("deck")).and_then(|d| d.as_array())?;
                let e = deck.get(idx)?;
                e.get("id").and_then(|x| x.as_i64()).or_else(|| e.as_i64())
            }
            Some(4) | Some(5) => {
                if owner >= players.len() {
                    return None;
                }
                let zone = if area == Some(4) { "active" } else { "bench" };
                arr(&players[owner], zone).get(idx).and_then(|p| p.get("id")).and_then(|x| x.as_i64())
            }
            _ => None,
        }
    }

    fn target_poke(&self, opt: &Value, obs: &Value, me: usize) -> (Option<usize>, Option<Value>) {
        let area = opt.get("inPlayArea").and_then(|x| x.as_i64());
        let idx = opt.get("inPlayIndex").and_then(|x| x.as_i64());
        if !matches!(area, Some(4) | Some(5)) || idx.is_none() {
            return (None, None);
        }
        let idx = idx.unwrap() as usize;
        let cur = match obs.get("current") {
            Some(c) => c,
            None => return (None, None),
        };
        let players = arr(cur, "players");
        let zone = if area == Some(4) { "active" } else { "bench" };
        let otype = opt.get("type").and_then(|x| x.as_i64()).unwrap_or(0);
        for owner in [me, 1 - me] {
            if owner < players.len() {
                if let Some(p) = arr(&players[owner], zone).get(idx) {
                    if !p.is_null() {
                        if otype == 8 || otype == 9 {
                            return (Some(me), Some((*p).clone()));
                        }
                        return (Some(owner), Some((*p).clone()));
                    }
                }
            }
        }
        (None, None)
    }

    fn option_feats(&self, opt: &Value, obs: &Value, me: usize) -> [f32; DO] {
        let mut out = [0f32; DO];
        let cur = obs.get("current").cloned().unwrap_or(Value::Null);
        let players = arr(&cur, "players");
        let otype = opt.get("type").and_then(|x| x.as_i64()).unwrap_or(0);
        if (0..16).contains(&otype) {
            out[otype as usize] = 1.0;
        }
        let area = opt.get("area").and_then(|x| x.as_i64()).unwrap_or(0);
        if (0..13).contains(&area) {
            out[16 + area as usize] = 1.0;
        }
        let ipa = opt.get("inPlayArea").and_then(|x| x.as_i64()).unwrap_or(0);
        if (0..13).contains(&ipa) {
            out[29 + ipa as usize] = 1.0;
        }
        let cid = self.resolve_card(opt, obs, me);
        let mut cf = [0f32; 14];
        self.card_feats(cid, &mut cf);
        out[42..56].copy_from_slice(&cf);
        if otype == 13 {
            let (dmg, cost) = opt.get("attackId").and_then(|x| x.as_i64())
                .and_then(|aid| self.ix.attacks.get(&aid)).cloned().unwrap_or((0.0, 0.0));
            let opp = 1 - me;
            let opp_active = if players.len() > opp { arr(&players[opp], "active").first() } else { None };
            let blk = self.poke_block(opp_active);
            let opp_hp = blk[0] * blk[1] * 350.0;
            out[56] = dmg / 300.0;
            out[57] = cost / 4.0;
            out[58] = if dmg > 0.0 && opp_hp <= dmg { 1.0 } else { 0.0 };
            out[59] = (dmg / 300.0) * blk[6];
        }
        let (towner, tpoke) = self.target_poke(opt, obs, me);
        if let Some(tp) = tpoke {
            let tb = self.poke_block(Some(&tp));
            out[60] = tb[0];
            out[61] = tb[2];
            out[62] = tb[6];
            out[63] = if towner == Some(me) { 1.0 } else { 0.0 };
        }
        out
    }
}

// ---------------- MLP ----------------
struct Mlp {
    w1: Vec<f32>, b1: Vec<f32>,
    w2: Vec<f32>, b2: Vec<f32>,
    w3: Vec<f32>, b3: Vec<f32>,
    h1: usize, h2: usize,
}

fn mat_from(v: &Value) -> (Vec<f32>, usize, usize) {
    let rows = v.as_array().unwrap();
    let r = rows.len();
    let c = rows[0].as_array().unwrap().len();
    let mut out = Vec::with_capacity(r * c);
    for row in rows {
        for x in row.as_array().unwrap() {
            out.push(x.as_f64().unwrap() as f32);
        }
    }
    (out, r, c)
}

fn load_mlp(path: &str) -> Result<Mlp> {
    let txt = std::fs::read_to_string(path)?;
    let v: Value = serde_json::from_str(&txt)?;
    let (w1, _r1, h1) = mat_from(&v["W1"]);
    let (w2, _r2, h2) = mat_from(&v["W2"]);
    let (w3, _r3, _c3) = mat_from(&v["W3"]);
    let vec = |k: &str| -> Vec<f32> {
        v[k].as_array().unwrap().iter().map(|x| x.as_f64().unwrap() as f32).collect()
    };
    Ok(Mlp { w1, b1: vec("b1"), w2, b2: vec("b2"), w3, b3: vec("b3"), h1, h2 })
}

fn erf_approx(x: f32) -> f32 {
    // Abramowitz-Stegun 7.1.26
    let s = if x < 0.0 { -1.0 } else { 1.0 };
    let x = x.abs();
    let t = 1.0 / (1.0 + 0.3275911 * x);
    let y = 1.0 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * (-x * x).exp();
    s * y
}

fn gelu(x: f32) -> f32 {
    0.5 * x * (1.0 + erf_approx(x * std::f32::consts::FRAC_1_SQRT_2))
}

impl Mlp {
    fn scores(&self, state: &[f32; DS], opts: &[[f32; DO]]) -> Vec<f32> {
        let mut out = Vec::with_capacity(opts.len());
        let din = DS + DO;
        for o in opts {
            let mut x = vec![0f32; din];
            x[..DS].copy_from_slice(state);
            x[DS..].copy_from_slice(o);
            let mut h1 = vec![0f32; self.h1];
            for j in 0..self.h1 {
                let mut acc = self.b1[j];
                for i in 0..din {
                    acc += x[i] * self.w1[i * self.h1 + j];
                }
                h1[j] = gelu(acc);
            }
            let mut h2 = vec![0f32; self.h2];
            for j in 0..self.h2 {
                let mut acc = self.b2[j];
                for i in 0..self.h1 {
                    acc += h1[i] * self.w2[i * self.h2 + j];
                }
                h2[j] = gelu(acc);
            }
            let mut acc = self.b3[0];
            for i in 0..self.h2 {
                acc += h2[i] * self.w3[i];
            }
            out.push(acc);
        }
        out
    }
}

// ---------------- f16 ----------------
fn f32_to_f16(x: f32) -> u16 {
    let bits = x.to_bits();
    let sign = ((bits >> 16) & 0x8000) as u16;
    let exp = ((bits >> 23) & 0xff) as i32;
    let frac = bits & 0x7fffff;
    if exp == 255 {
        return sign | 0x7c00;
    }
    let e = exp - 112;
    if e >= 31 {
        return sign | 0x7c00;
    }
    if e <= 0 {
        return sign;
    }
    sign | ((e as u16) << 10) | ((frac >> 13) as u16)
}

// ---------------- rollout ----------------
#[derive(Parser, Debug)]
#[command(name = "policy_rollout")]
struct Args {
    #[arg(long)]
    lib_dir: String,
    #[arg(long)]
    card_index: String,
    #[arg(long)]
    weights: String,
    #[arg(long)]
    opp_weights: Option<String>,
    #[arg(long)]
    decks: String, // comma-separated csv paths and/or dirs
    #[arg(long, default_value_t = 1000)]
    games: usize,
    #[arg(long, default_value_t = 4)]
    jobs: usize,
    #[arg(long, default_value_t = 0.1)]
    eps: f32,
    #[arg(long, default_value_t = 42)]
    seed: u64,
    #[arg(long)]
    out: Option<String>,
    #[arg(long, default_value = "train")]
    mode: String,
    #[arg(long, default_value_t = 0.5)]
    league_frac: f64,
}

thread_local! {
    static ENG: RefCell<Option<Engine>> = RefCell::new(None);
}

fn with_engine<R>(lib_dir: &str, f: impl FnOnce(&mut Engine) -> Result<R>) -> Result<R> {
    ENG.with(|cell| {
        let mut slot = cell.borrow_mut();
        if slot.is_none() {
            let tid = rayon::current_thread_index().unwrap_or(0);
            let path = format!("{}/libcg_{}.so", lib_dir, tid);
            *slot = Some(Engine::new(&path)?);
        }
        f(slot.as_mut().unwrap())
    })
}

struct GameCfg {
    deck0: Vec<i32>,
    deck1: Vec<i32>,
    vs_league: bool,
    seed: u64,
}

struct Rec {
    s: [f32; DS],
    o: Vec<[f32; DO]>,
    chosen: u16,
    r: i8,
}

fn play_game(
    cfg: &GameCfg,
    feat: &Feat,
    mlp: &Mlp,
    opp_mlp: Option<&Mlp>,
    eps: f32,
    train: bool,
    lib_dir: &str,
) -> (Vec<Rec>, i32) {
    let mut recs: Vec<(usize, Rec)> = Vec::new(); // (seat, rec)
    let result = with_engine(lib_dir, |eng| -> Result<i32> {
        let mut cards: Vec<c_int> = Vec::with_capacity(120);
        cards.extend(cfg.deck0.iter().map(|&x| x as c_int));
        cards.extend(cfg.deck1.iter().map(|&x| x as c_int));
        let mut obs = eng.battle_start(&cards)?;
        let mut rng = StdRng::seed_from_u64(cfg.seed);
        let mut steps = 0usize;
        let res = loop {
            steps += 1;
            if steps > 5000 {
                break -1;
            }
            let cur = obs.get("current").cloned().unwrap_or(Value::Null);
            if let Some(r) = cur.get("result").and_then(|x| x.as_i64()) {
                if r >= 0 {
                    break r as i32;
                }
            }
            let sel = match obs.get("select") {
                Some(s) if !s.is_null() => s.clone(),
                _ => break -1,
            };
            let me = cur.get("yourIndex").and_then(|x| x.as_i64()).unwrap_or(0) as usize;
            let use_opp = cfg.vs_league && me == 1;
            let net = if use_opp { opp_mlp.unwrap_or(mlp) } else { mlp };
            let opts_v = arr(&sel, "option");
            if opts_v.is_empty() {
                break -1;
            }
            let state = feat.state_feats(&obs, me);
            let ofeats: Vec<[f32; DO]> = opts_v.iter().take(MAX_OPT).map(|o| feat.option_feats(o, &obs, me)).collect();
            let scores = net.scores(&state, &ofeats);
            let n = scores.len();
            // choose
            let chosen = if train && rng.gen::<f32>() < eps {
                rng.gen_range(0..n)
            } else if train {
                // softmax sample
                let mx = scores.iter().cloned().fold(f32::MIN, f32::max);
                let exps: Vec<f32> = scores.iter().map(|s| (s - mx).exp()).collect();
                let tot: f32 = exps.iter().sum();
                let mut pick = rng.gen::<f32>() * tot;
                let mut idx = n - 1;
                for (i, e) in exps.iter().enumerate() {
                    pick -= e;
                    if pick <= 0.0 {
                        idx = i;
                        break;
                    }
                }
                idx
            } else {
                scores.iter().enumerate().max_by(|a, b| a.1.partial_cmp(b.1).unwrap()).map(|(i, _)| i).unwrap_or(0)
            };
            // executed set: top-maxCount by score (chosen forced first)
            let mx_count = sel.get("maxCount").and_then(|x| x.as_i64()).unwrap_or(1).max(1) as usize;
            let mut order: Vec<usize> = (0..n).collect();
            order.sort_by(|&a, &b| scores[b].partial_cmp(&scores[a]).unwrap_or(std::cmp::Ordering::Equal));
            let mut exec: Vec<i32> = Vec::new();
            if mx_count <= 1 {
                exec.push(chosen as i32);
            } else {
                let mut rest: Vec<usize> = order.into_iter().filter(|&i| i != chosen).collect();
                exec.push(chosen as i32);
                while exec.len() < mx_count.min(n) {
                    if let Some(nx) = rest.first().cloned() {
                        rest.remove(0);
                        exec.push(nx as i32);
                    } else {
                        break;
                    }
                }
            }
            if train && !(cfg.vs_league && me == 1) {
                recs.push((me, Rec { s: state, o: ofeats, chosen: chosen as u16, r: 0 }));
            }
            obs = eng.select(&exec)?;
        };
        eng.finish();
        Ok(res)
    });
    match result {
        Ok(r) if r == 0 || r == 1 => {
            let mut out = Vec::new();
            for (seat, mut rec) in recs {
                rec.r = if (r as usize) == seat { 1 } else { -1 };
                out.push(rec);
            }
            (out, r)
        }
        _ => (Vec::new(), -1),
    }
}

fn load_deck(path: &str) -> Vec<i32> {
    let txt = std::fs::read_to_string(path).unwrap_or_default();
    txt.split(|c: char| c == ',' || c.is_whitespace())
        .filter(|t| !t.is_empty())
        .filter_map(|t| t.parse::<i32>().ok())
        .collect()
}

fn collect_decks(spec: &str) -> Vec<Vec<i32>> {
    let mut out = Vec::new();
    for part in spec.split(',') {
        let p = PathBuf::from(part.trim());
        if p.is_dir() {
            let mut names: Vec<_> = std::fs::read_dir(&p).unwrap()
                .filter_map(|e| e.ok().map(|e| e.path()))
                .filter(|p| p.extension().map(|e| e == "csv").unwrap_or(false))
                .collect();
            names.sort();
            for n in names {
                let d = load_deck(&n.to_string_lossy());
                if d.len() == 60 {
                    out.push(d);
                }
            }
        } else {
            let d = load_deck(part.trim());
            if d.len() == 60 {
                out.push(d);
            }
        }
    }
    out
}

fn main() -> Result<()> {
    let args = Args::parse();
    let ix = load_index(&args.card_index)?;
    let feat = Feat { ix: &ix };
    let mlp = load_mlp(&args.weights)?;
    let opp_mlp = match &args.opp_weights {
        Some(p) => Some(load_mlp(p)?),
        None => None,
    };
    let decks = collect_decks(&args.decks);
    anyhow::ensure!(!decks.is_empty(), "no decks");
    let train = args.mode == "train";
    rayon::ThreadPoolBuilder::new().num_threads(args.jobs).build_global()?;

    let mut cfgs = Vec::with_capacity(args.games);
    let mut rng = StdRng::seed_from_u64(args.seed);
    for g in 0..args.games {
        let d0 = decks[rng.gen_range(0..decks.len())].clone();
        let d1 = decks[rng.gen_range(0..decks.len())].clone();
        let vs_league = opp_mlp.is_some() && rng.gen::<f64>() < args.league_frac;
        cfgs.push(GameCfg { deck0: d0, deck1: d1, vs_league, seed: args.seed + 1000003 * (g as u64) + 17 });
    }

    let wins = AtomicUsize::new(0);
    let games_done = AtomicUsize::new(0);
    let out_file: Option<Mutex<BufWriter<File>>> = match (&args.out, train) {
        (Some(p), true) => {
            let mut f = BufWriter::new(File::create(p)?);
            f.write_all(b"POL1")?;
            Some(Mutex::new(f))
        }
        _ => None,
    };
    let t0 = std::time::Instant::now();
    cfgs.par_iter().for_each(|cfg| {
        let (recs, res) = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            play_game(cfg, &feat, &mlp, opp_mlp.as_ref(), args.eps, train, &args.lib_dir)
        }))
        .unwrap_or((Vec::new(), -1));
        if res == 0 {
            wins.fetch_add(1, Ordering::Relaxed);
        }
        if res >= 0 {
            games_done.fetch_add(1, Ordering::Relaxed);
            if let Some(of) = &out_file {
                if !recs.is_empty() {
                    let mut buf: Vec<u8> = Vec::with_capacity(recs.len() * 600);
                    for r in &recs {
                        for v in r.s.iter() {
                            buf.extend_from_slice(&f32_to_f16(*v).to_le_bytes());
                        }
                        buf.push(r.o.len() as u8);
                        for o in r.o.iter() {
                            for v in o.iter() {
                                buf.extend_from_slice(&f32_to_f16(*v).to_le_bytes());
                            }
                        }
                        buf.extend_from_slice(&r.chosen.to_le_bytes());
                        buf.push(r.r as u8);
                    }
                    let mut g = of.lock().unwrap();
                    let _ = g.write_all(&buf);
                }
            }
        }
    });
    if let Some(of) = &out_file {
        of.lock().unwrap().flush()?;
    }
    let gd = games_done.load(Ordering::Relaxed);
    let w = wins.load(Ordering::Relaxed);
    let el = t0.elapsed().as_secs_f64();
    println!(
        "games={} valid={} seat0_wr={:.3} elapsed={:.1}s games_per_sec={:.1}",
        args.games,
        gd,
        if gd > 0 { w as f64 / gd as f64 } else { 0.0 },
        el,
        gd as f64 / el.max(0.001)
    );
    Ok(())
}
