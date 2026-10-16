use serde_json::Value;
use crate::heuristic::CardIndex;

const ABRA: i32 = 741;
const KADABRA: i32 = 742;
const ALAKAZAM: i32 = 743;
const DUNSPARCE: i32 = 305;
const DUDUNSPARCE: i32 = 66;
const PIKIPEK: i32 = 1407;
const TOUCANNON: i32 = 1409;
const RARE_CANDY: i32 = 1079;
const POFFIN: i32 = 1086;
const POKE_PAD: i32 = 1152;
const BOSS: i32 = 1182;
const NIGHT_STRETCHER: i32 = 1097;
const SACRED_ASH: i32 = 1129;
const DAWN: i32 = 1231;
const HILDA: i32 = 1225;

fn poke_list<'a>(player: &'a Value, zone: &str) -> Vec<&'a Value> {
    match player.get(zone) {
        Some(v) if v.is_array() => v.as_array().unwrap().iter().filter(|x| !x.is_null()).collect(),
        Some(v) if v.is_object() => vec![v],
        _ => vec![],
    }
}

fn active<'a>(player: &'a Value) -> Option<&'a Value> {
    poke_list(player, "active").into_iter().next()
}

fn bench<'a>(player: &'a Value) -> Vec<&'a Value> {
    poke_list(player, "bench")
}

fn board<'a>(player: &'a Value) -> Vec<&'a Value> {
    let mut b = Vec::new();
    if let Some(a) = active(player) { b.push(a); }
    b.extend(bench(player));
    b
}

fn energies(poke: &Value) -> usize {
    if let Some(arr) = poke.get("energies").and_then(|x| x.as_array()) { return arr.len(); }
    if let Some(arr) = poke.get("energyCards").and_then(|x| x.as_array()) { return arr.len(); }
    0
}

fn hp(poke: &Value) -> i32 {
    poke.get("hp").and_then(|x| x.as_i64()).unwrap_or(0) as i32
}

fn hand_ids(player: &Value) -> Vec<i32> {
    let mut out = Vec::new();
    if let Some(hand) = player.get("hand").and_then(|x| x.as_array()) {
        for h in hand {
            if let Some(id) = h.get("id").and_then(|x| x.as_i64()) { out.push(id as i32); }
        }
    }
    out
}

fn prize_len(player: &Value) -> usize {
    player.get("prize").and_then(|x| x.as_array()).map(|a| a.len()).unwrap_or(6)
}

fn opt_hand_card(opt: &Value, player: &Value) -> Option<i32> {
    let idx = opt.get("index")?.as_u64()? as usize;
    let hand = player.get("hand")?.as_array()?;
    if idx < hand.len() {
        hand[idx].get("id")?.as_i64().map(|x| x as i32)
    } else { None }
}

fn best_damage(poke: &Value, hand_n: usize, my_bench: usize, opp_bench: usize, index: &CardIndex) -> i32 {
    let cid = match poke.get("id").and_then(|x| x.as_i64()) { Some(id) => id as i32, None => return 0 };
    let card = match index.card(cid) { Some(c) => c, None => return 0 };
    let mut best=0;
    for aid in &card.atk {
        if let Some(atk) = index.attack(*aid) {
            let mut d = atk.damage;
            if d==0 {
                let name = &atk.name;
                if name=="Powerful Hand" { d = (20 * hand_n) as i32; }
                else if name=="Feather Rondo" { d = 60 + 20 * (my_bench + opp_bench) as i32; }
                else if name=="Cruel Arrow" { d = 30; }
            } else {
                if atk.name=="Feather Rondo" { d = 60 + 20 * (my_bench + opp_bench) as i32; }
            }
            if d>best { best=d; }
        }
    }
    best
}

pub fn decide_alakazam(obs: &Value, index: &CardIndex) -> Vec<i32> {
    let select = match obs.get("select") { Some(s) => s, None => return vec![] };
    let options = match select.get("option").and_then(|x| x.as_array()) { Some(o) => o, None => return vec![] };
    if options.is_empty() { return vec![]; }
    let stype = select.get("type").and_then(|x| x.as_i64()).unwrap_or(-1);
    let cur = match obs.get("current") { Some(c) => c, None => return vec![0] };
    let players = match cur.get("players").and_then(|x| x.as_array()) { Some(p) => p, None => return vec![0] };
    let me_idx = cur.get("yourIndex").and_then(|x| x.as_u64()).unwrap_or(0) as usize;
    if me_idx>=players.len() { return vec![0]; }
    let me_p = &players[me_idx];
    let opp_p = &players[1-me_idx];
    let hand = hand_ids(me_p);
    let hand_n = hand.len();
    let board = board(me_p);
    let board_n = board.len();
    let my_bench_n = bench(me_p).len();
    let opp_bench_n = bench(opp_p).len();
    let our_prizes = prize_len(me_p);
    let opp_prizes = prize_len(opp_p);
    let endgame = our_prizes<=3 || opp_prizes<=3;

    if stype==0 {
        // 1) always evo Alakazam
        for (i, opt) in options.iter().enumerate() {
            if opt.get("type").and_then(|x| x.as_i64())==Some(9) {
                if let Some(cid) = opt_hand_card(opt, me_p) {
                    if cid==ALAKAZAM { return vec![i as i32]; }
                }
            }
        }
        // 2) Rare Candy
        if hand.contains(&ALAKAZAM) && board.iter().any(|p| p.get("id").and_then(|x| x.as_i64()).map(|id| id as i32==ABRA).unwrap_or(false)) {
            for (i, opt) in options.iter().enumerate() {
                if opt.get("type").and_then(|x| x.as_i64())==Some(7) {
                    if let Some(cid) = opt_hand_card(opt, me_p) {
                        if cid==RARE_CANDY { return vec![i as i32]; }
                    }
                }
            }
        }
        // 3) endgame bench guard >=2
        if endgame && board_n<=2 {
            for (i, opt) in options.iter().enumerate() {
                if opt.get("type").and_then(|x| x.as_i64())==Some(7) {
                    if let Some(cid) = opt_hand_card(opt, me_p) {
                        if let Some(card) = index.card(cid) {
                            if card.ct==0 && card.b { return vec![i as i32]; }
                        }
                    }
                }
            }
            for (i, opt) in options.iter().enumerate() {
                if opt.get("type").and_then(|x| x.as_i64())==Some(7) {
                    if let Some(cid) = opt_hand_card(opt, me_p) {
                        if cid==POFFIN || cid==POKE_PAD { return vec![i as i32]; }
                    }
                }
            }
        }
        // 4) hand refill <=4
        if hand_n<=4 {
            for (i, opt) in options.iter().enumerate() {
                if opt.get("type").and_then(|x| x.as_i64())==Some(7) {
                    if let Some(cid) = opt_hand_card(opt, me_p) {
                        if cid==DAWN || cid==HILDA { return vec![i as i32]; }
                    }
                }
            }
        }
        // 5) Boss KO
        if let Some(act) = active(me_p) {
            let dmg = best_damage(act, hand_n, my_bench_n, opp_bench_n, index);
            if dmg>0 {
                for b in bench(opp_p) {
                    let bhp = hp(b);
                    if bhp>0 && bhp <= dmg+10 {
                        for (i, opt) in options.iter().enumerate() {
                            if opt.get("type").and_then(|x| x.as_i64())==Some(7) {
                                if let Some(cid) = opt_hand_card(opt, me_p) {
                                    if cid==BOSS { return vec![i as i32]; }
                                }
                            }
                        }
                    }
                }
            }
        }
        // 6) recovery when board small
        if board_n<=2 {
            for (i, opt) in options.iter().enumerate() {
                if opt.get("type").and_then(|x| x.as_i64())==Some(7) {
                    if let Some(cid) = opt_hand_card(opt, me_p) {
                        if cid==NIGHT_STRETCHER || cid==SACRED_ASH { return vec![i as i32]; }
                    }
                }
            }
        }
        // 7) don't attack before setup
        if options.get(0).and_then(|o| o.get("type")).and_then(|x| x.as_i64())==Some(13) {
            for (i, opt) in options.iter().enumerate() {
                if opt.get("type").and_then(|x| x.as_i64())==Some(9) { return vec![i as i32]; }
            }
            if let Some(act) = active(me_p) {
                if energies(act)==0 {
                    for (i, opt) in options.iter().enumerate() {
                        if opt.get("type").and_then(|x| x.as_i64())==Some(8) && opt.get("inPlayArea").and_then(|x| x.as_i64())==Some(4) {
                            return vec![i as i32];
                        }
                    }
                }
            }
        }
        return vec![0];
    }

    // non-main: promotion / search
    let mut scored: Vec<(i32, usize)> = Vec::new();
    for (i, opt) in options.iter().enumerate() {
        let mut s=0;
        if opt.get("type").and_then(|x| x.as_i64())==Some(3) {
            let area = opt.get("area").and_then(|x| x.as_i64()).unwrap_or(-1);
            let idx = opt.get("index").and_then(|x| x.as_u64()).unwrap_or(0) as usize;
            if area==5 {
                let b = bench(me_p);
                if idx < b.len() {
                    if let Some(pid) = b[idx].get("id").and_then(|x| x.as_i64()).map(|x| x as i32) {
                        if endgame && board_n<=2 {
                            if pid==ABRA { s=-50; }
                            else if pid==ALAKAZAM { s=120; }
                            else if pid==DUDUNSPARCE { s=110; }
                            else { s=30; }
                        } else {
                            s = match pid {
                                x if x==ALAKAZAM => 100,
                                x if x==KADABRA => 60,
                                x if x==DUDUNSPARCE => 55,
                                x if x==ABRA => 30,
                                x if x==DUNSPARCE => 35,
                                _ => 20,
                            };
                        }
                        s += (energies(b[idx]).min(2) as i32)*8 + hp(b[idx])/20;
                    }
                }
            } else if area==4 {
                if let Some(p) = active(me_p) {
                    let pid = p.get("id").and_then(|x| x.as_i64()).map(|x| x as i32).unwrap_or(0);
                    s = match pid { x if x==ALAKAZAM => 100, x if x==KADABRA => 60, x if x==DUDUNSPARCE => 55, _ => 30 };
                }
            } else if area==2 {
                if let Some(hand_arr) = me_p.get("hand").and_then(|x| x.as_array()) {
                    if idx < hand_arr.len() {
                        if let Some(cid) = hand_arr[idx].get("id").and_then(|x| x.as_i64()).map(|x| x as i32) {
                            if endgame && board_n<=2 {
                                if cid==NIGHT_STRETCHER || cid==SACRED_ASH { s=90; }
                                else if cid==ALAKAZAM { s=100; }
                                else if cid==ABRA { s=70; }
                                else { s=30; }
                            } else {
                                s = match cid {
                                    x if x==ALAKAZAM => 100,
                                    x if x==KADABRA => 80,
                                    x if x==ABRA => 70,
                                    x if x==DUDUNSPARCE => 55,
                                    x if x==DUNSPARCE => 50,
                                    x if x==RARE_CANDY => 40,
                                    _ => 25,
                                };
                            }
                            if cid==5 || cid==13 || cid==19 {
                                let loaded: usize = board.iter().map(|p| energies(p)).sum();
                                s = if loaded < board.len() { 65 } else { 15 };
                            }
                        }
                    }
                }
            } else if let Some(cid) = opt.get("cardId").and_then(|x| x.as_i64()).map(|x| x as i32) {
                s = match cid {
                    x if x==ALAKAZAM => 100,
                    x if x==KADABRA => 80,
                    x if x==ABRA => 70,
                    _ => 25,
                };
            }
        } else if opt.get("type").and_then(|x| x.as_i64())==Some(1) {
            s=10;
        }
        scored.push((s,i));
    }
    scored.sort_by(|a,b| b.0.cmp(&a.0));
    let min_count = select.get("minCount").and_then(|x| x.as_u64()).unwrap_or(1) as usize;
    let k = min_count.max(1).min(options.len());
    let mut chosen: Vec<i32> = scored.iter().take(k).map(|(_, idx)| *idx as i32).collect();
    chosen.sort();
    chosen
}
