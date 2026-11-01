#![allow(dead_code)]
// Uses the audited source modules without modifying them.
#[cfg_attr(local_snapshot, path = "../Pokemon-arena-d1882c0f-pokemon/battery-sim/src/materials.rs")]
#[cfg_attr(not(local_snapshot), path = "../battery-sim/src/materials.rs")]
mod materials;
#[cfg_attr(local_snapshot, path = "../Pokemon-arena-d1882c0f-pokemon/battery-sim/src/util.rs")]
#[cfg_attr(not(local_snapshot), path = "../battery-sim/src/util.rs")]
mod util;
#[cfg_attr(local_snapshot, path = "../Pokemon-arena-d1882c0f-pokemon/battery-sim/src/cell.rs")]
#[cfg_attr(not(local_snapshot), path = "../battery-sim/src/cell.rs")]
mod cell;
#[cfg_attr(local_snapshot, path = "../Pokemon-arena-d1882c0f-pokemon/battery-sim/src/sim.rs")]
#[cfg_attr(not(local_snapshot), path = "../battery-sim/src/sim.rs")]
mod sim;

fn main() {
    let cp = cell::CellParams::default();
    let sp = sim::SimParams::default();
    println!("case,dead_li,expansion,cycles,abuse_runaway,abuse_short,wh_kg,wh_l");
    for dead in [0.0002, 0.001, 0.003] {
        let mut an = materials::anode("LIFREE").unwrap();
        an.dead_li = dead;
        let c = cell::Cell::new(materials::cathode("LFP").unwrap(), an,
            materials::electrolyte("LP57").unwrap(), 35., 1.02, &cp);
        let r = sim::simulate(&c, &cp, &sp, 2., 1., 25., 3000, None);
        let a = sim::simulate(&c, &cp, &sp, 1., 1., 25., 1,
            Some(sim::Abuse { t_oven:150., overcharge:1., t_max_h:3. }));
        println!("lfp_free,{dead},{},{},{},{},{:.3},{:.3}", an.expansion, r.cycles, a.runaway, a.short, c.wh_kg, c.wh_l);
    }
    for expansion in [0., 0.6, 3.] {
        let mut an = materials::anode("SIC").unwrap();
        an.expansion = expansion;
        let c = cell::Cell::new(materials::cathode("NMC811").unwrap(), an,
            materials::electrolyte("GEL").unwrap(), 30., 1.1, &cp);
        let r = sim::simulate(&c, &cp, &sp, 2., 1., 25., 3000, None);
        let a = sim::simulate(&c, &cp, &sp, 1., 1., 25., 1,
            Some(sim::Abuse { t_oven:150., overcharge:1., t_max_h:3. }));
        println!("sic_expansion,{},{expansion},{},{},{},{:.3},{:.3}", an.dead_li, r.cycles, a.runaway, a.short, c.wh_kg, c.wh_l);
    }
    let ca = materials::cathode("NMC811").unwrap();
    let an = materials::anode("SIC").unwrap();
    for name in ["LP57", "GEL", "SOLID"] {
        let c = cell::Cell::new(ca, an, materials::electrolyte(name).unwrap(),30.,1.1,&cp);
        println!("GEOMETRY {name}: mass_mg={:.6} electrolyte_mg={:.6} thickness_cm={:.6} wh_kg={:.6} wh_l={:.6}", c.m_tot,c.m_el,c.t_tot,c.wh_kg,c.wh_l);
    }
    let c = cell::Cell::new(ca,an,materials::electrolyte("GEL").unwrap(),30.,1.1,&cp);
    for overcharge in [0., 1., 10.] {
        let a = sim::simulate(&c,&cp,&sp,1.,1.,25.,1,
            Some(sim::Abuse { t_oven:150., overcharge, t_max_h:3. }));
        println!("ABUSE overcharge={overcharge}: Tmax={:.12} runaway={} short={}",a.t_max,a.runaway,a.short);
    }
}
