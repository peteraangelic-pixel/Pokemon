#!/usr/bin/env python3
"""
Prototyp (referencja) modelu symulatora ogniwa 3-składnikowego: katoda | elektrolit | anoda.

Ten sam model fizykochemiczny jest zaimplementowany w Rust (katalog battery-sim/src).
Prototyp sluzy do walidacji stalych i logiki przed uruchomieniem sweepu w Rust.

Model:
  - pojemnosc/energia z krzywych OCV + bilansu masowego (Wh/kg, mAh/g na poziomie ogniwa)
  - opor wewnetrzny (jonowy + aktywacja + interfaza), rośnie z SEI, ladowaniem litu, degradacja
  - ladowanie litowe (plating) przy szybkim ladowaniu / niskiej temperaturze -> dead Li + dendryty
  - wzrost SEI (paraboliczny, Arrhenius), straty inwentarza Li, shuttle (Li-S), dead Li (Li metal)
  - degradacja katody (cykliczna, Arrhenius, zalezna od napiecia) + stres oksydacyjny
    elektrolitu przy katodach wysokonapieciowych (V > okno elektrolitu)
  - termika brylowa (lumped): I^2R + aktywacja + reakcje uboczne + egzotermie
    (reakcja litowanej anody z elektrolitem, stopienie Li, spalanie elektrolitu, rozklad katody)
  - test abusow: piec 150C + przeladowanie (separator PP: shutdown 130C, melt 160C)

Kryteria (zgodne z zalozeniami projektu):
  1) energia wlasciwa >= referencyjnego ogniwa Li-ion (NMC811/grafit/LP57)
  2) brak eksplozji / thermal runaway / zwarcia (cyklowanie + test abusow)
  3) >= 500 cykli przy SZYBKIM ladowaniu (>= 2C)

Jednostki: mAh/cm^2, mA/cm^2, V, Ohm*cm^2, °C, sekundy.
Uruchomienie:  python3 tools/model_prototype.py
"""
import math

F = 96485.33212      # C/mol
RG = 8.314462618     # J/mol/K


def arr(t_c, tref_c, ea):
    """Czynnik Arrheniusa: przyspieszenie reakcji w temperaturze t_c wzgledem tref_c."""
    t = t_c + 273.15
    tr = tref_c + 273.15
    return math.exp(-ea / RG * (1.0 / t - 1.0 / tr))


def interp(curve, x):
    """Interpolacja liniowa po krzywej [(x, v), ...] z zaciskiem na koncach."""
    if x <= curve[0][0]:
        return curve[0][1]
    if x >= curve[-1][0]:
        return curve[-1][1]
    for i in range(len(curve) - 1):
        x0, v0 = curve[i]
        x1, v1 = curve[i + 1]
        if x0 <= x <= x1:
            return v0 + (v1 - v0) * (x - x0) / (x1 - x0)
    return curve[-1][1]


# ---------------------------------------------------------------- materialy
# vcurve: [(SOC, V vs Li/Li+)]
#   katoda: SOC = stopien delitiacji (1 = naladowana)
#   anoda:  SOC = stopien litacji    (1 = naladowana)

CATHODES = {
    "NMC811": dict(cap=200.0, vcurve=[(0.0, 3.55), (0.3, 3.70), (0.6, 3.85), (0.9, 4.05), (1.0, 4.20)],
                   vmax=4.20, dens=4.6, act=0.96, fade=1.0, t_stable=280.0, i0=2.0, sd=0.0002, dH=600.0),
    "NMC532": dict(cap=160.0, vcurve=[(0.0, 3.50), (0.5, 3.70), (1.0, 4.20)],
                   vmax=4.20, dens=4.5, act=0.96, fade=0.7, t_stable=300.0, i0=2.0, sd=0.0002, dH=600.0),
    "NCA":    dict(cap=190.0, vcurve=[(0.0, 3.55), (0.5, 3.75), (1.0, 4.20)],
                   vmax=4.20, dens=4.7, act=0.96, fade=0.8, t_stable=290.0, i0=2.0, sd=0.0002, dH=600.0),
    "LFP":    dict(cap=160.0, vcurve=[(0.0, 3.20), (0.05, 3.45), (0.95, 3.45), (1.0, 3.60)],
                   vmax=3.65, dens=3.6, act=0.95, fade=0.25, t_stable=350.0, i0=2.5, sd=0.0001, dH=150.0),
    "LCO":    dict(cap=145.0, vcurve=[(0.0, 3.60), (0.5, 3.90), (1.0, 4.20)],
                   vmax=4.20, dens=5.0, act=0.96, fade=1.2, t_stable=250.0, i0=1.5, sd=0.0003, dH=500.0),
    "LMR":    dict(cap=240.0, vcurve=[(0.0, 3.60), (0.5, 3.80), (1.0, 4.60)],
                   vmax=4.60, dens=4.3, act=0.94, fade=2.5, t_stable=260.0, i0=2.0, sd=0.001, dH=500.0),
    "LNMO":   dict(cap=120.0, vcurve=[(0.0, 4.00), (0.5, 4.70), (1.0, 4.90)],
                   vmax=4.95, dens=4.8, act=0.95, fade=0.6, t_stable=320.0, i0=1.0, sd=0.0002, dH=200.0),
    "SULFUR": dict(cap=800.0, vcurve=[(0.0, 2.40), (0.5, 2.15), (1.0, 1.90)],
                   vmax=2.50, dens=1.8, act=0.90, fade=2.0, t_stable=115.0, i0=1.5, sd=0.008, dH=150.0),
}

ANODES = {
    # k_an: stala reakcji litowanej anody z elektrolitem [mW/g] (Arrhenius, ref 150C, Ea 80kJ)
    # dH: cieplo topienia/reakcji dla Li metalu [J/g]
    # dead_li: ulamek litu zamieniajacego sie w "martwy" lit na cykl przy 1C (Li metal, Si)
    "GRAPHITE": dict(cap=340.0, vcurve=[(0.0, 0.20), (0.05, 0.12), (0.2, 0.10), (0.5, 0.09), (0.9, 0.08), (1.0, 0.05)],
                     dens=2.2, act=0.96, expansion=0.10, plat=1.0, sei=1.0, dend=0.004,
                     t_stable=120.0, fade=1.0, i0=4.0, k_an=1500.0, dH=400.0, dead_li=0.0),
    "LTO":      dict(cap=155.0, vcurve=[(0.0, 1.60), (0.5, 1.55), (1.0, 1.50)],
                     dens=3.4, act=0.95, expansion=0.00, plat=0.02, sei=0.05, dend=0.0,
                     t_stable=350.0, fade=0.15, i0=3.0, k_an=0.0, dH=30.0, dead_li=0.0),
    "SIC":      dict(cap=900.0, vcurve=[(0.0, 0.60), (0.3, 0.45), (0.7, 0.25), (1.0, 0.08)],
                     dens=2.0, act=0.93, expansion=0.60, plat=0.5, sei=2.0, dend=0.003,
                     t_stable=160.0, fade=1.5, i0=1.5, k_an=800.0, dH=250.0, dead_li=0.0001),
    "LIMETAL":  dict(cap=3860.0, vcurve=[(0.0, 0.05), (1.0, 0.0)],
                     dens=0.53, act=0.99, expansion=1.0, plat=0.0, sei=0.8, dend=0.04,
                     t_stable=180.0, fade=0.5, i0=5.0, k_an=0.0, dH=300.0, dead_li=0.0006),
    "HC":       dict(cap=300.0, vcurve=[(0.0, 0.50), (0.2, 0.30), (0.6, 0.15), (1.0, 0.02)],
                     dens=1.5, act=0.91, expansion=0.10, plat=0.8, sei=1.2, dend=0.004,
                     t_stable=150.0, fade=0.8, i0=3.0, k_an=1200.0, dH=350.0, dead_li=0.0),
}

ELECTROLYTES = {
    "LP57":  dict(kappa=10.0, t_decomp=170.0, flammable=True,  window=4.4, sei=1.0, r_if=0.5),
    "IONIC": dict(kappa=3.0,  t_decomp=300.0, flammable=False, window=5.0, sei=0.6, r_if=1.5),
    "SOLID": dict(kappa=1.0,  t_decomp=400.0, flammable=False, window=5.0, sei=0.2, r_if=3.0),
}

# ---------------------------------------------------------------- parametry ogniwa
CELL_DEFAULTS = dict(
    loading_cat=20.0,   # mg/cm^2 (masa powloki katodowej na jedna strone elektrody)
    np=1.10,            # stosunek pojemnosci anody do katody
    por_sep=0.45, t_sep=0.002,       # porowatosc / grubosc separatora [cm] (PP 20 um)
    por_e=0.32,                      # porowatosc elektrod
    foil_al=0.0012, dens_al=2.70,    # folia Al 12 um
    foil_cu=0.0008, dens_cu=8.96,    # folia Cu 8 um
    dens_sep=0.91,
    e_per_c=2.7,                     # elektrolit [g/Ah]
    pack=1.06,                       # obudowa/taby (pouch)
    h=10.0,                          # W/m^2/K (obie strony elektrody, konwekcja swobodna)
    cp=1.0,                          # J/g/K
    alpha=0.5,                       # wspolczynnik symetrii Butler-Volmera
    k_conc=0.5,                      # udzial polaryzacji koncentracyjnej w nadwoltazu anody
    v_margin_top=0.10,               # margines napiecia ladowania ponad OCV przy pelnym SOC
    v_margin_bot=0.25,               # margines rozladowania ponizej OCV przy pustym SOC
    i0_floor=0.25,                   # minimalny udzial i0 przy SOC = 0 / 1
)


def build_cell(cath, an, el, loading_cat=None, np=None, p=CELL_DEFAULTS):
    c = CATHODES[cath]; a = ANODES[an]; e = ELECTROLYTES[el]
    loading_cat = loading_cat if loading_cat is not None else p["loading_cat"]
    np = np if np is not None else p["np"]

    cap = loading_cat * c["cap"] * c["act"] / 1000.0     # mAh/cm^2 (katoda ogranicza)
    loading_an = np * cap / (a["cap"] * a["act"]) * 1000.0   # mg/cm^2

    # masy na cm^2 elektrody [mg/cm^2]
    m_cat = loading_cat / c["act"]
    m_an = loading_an / a["act"]
    m_al = p["foil_al"] * p["dens_al"] * 1000.0
    m_cu = p["foil_cu"] * p["dens_cu"] * 1000.0
    m_sep = p["t_sep"] * p["dens_sep"] * 1000.0
    m_el = p["e_per_c"] * cap                            # g/Ah * mAh/cm^2 -> mg/cm^2
    m_tot = (m_cat + m_an + m_al + m_cu + m_sep + m_el) * p["pack"]  # mg/cm^2

    # srednie napiecie ogniwa (calka po SOC)
    n = 24
    v_avg = 0.0
    for i in range(n):
        s = (i + 0.5) / n
        v_avg += interp(c["vcurve"], s) - interp(a["vcurve"], min(1.0, s / np))
    v_avg /= n

    wh_kg = cap * v_avg / m_tot * 1000.0                 # Wh/kg
    mah_g = cap / (m_tot / 1000.0)                       # mAh/g

    # opor wewnetrzny [Ohm*cm^2]
    kap = e["kappa"] / 1000.0                            # S/cm
    t_cat = (m_cat / 1000.0) / (c["dens"] * (1.0 - p["por_e"]))   # cm
    t_an = (m_an / 1000.0) / (a["dens"] * (1.0 - p["por_e"]))
    r_sep = p["t_sep"] / (kap * p["por_sep"] ** 1.5)
    r_e = (t_cat + t_an) / (kap * p["por_e"] ** 1.5) / 4.0
    r_ct = RG * 298.15 / (F * (c["i0"] + a["i0"]) / 1000.0) * 0.2
    r0 = r_sep + r_e + r_ct + e["r_if"]

    v_max = c["vmax"] - interp(a["vcurve"], 1.0 / np) + p["v_margin_top"]
    v_min = interp(c["vcurve"], 0.0) - interp(a["vcurve"], 0.0) - p["v_margin_bot"]

    c_th = m_tot * p["cp"]                               # mJ/K na cm^2
    ha = 2.0 * p["h"] * 1e-4 * 1000.0                     # mW/K na cm^2 (obie strony)

    return dict(
        cath=cath, an=an, el=el, loading_cat=loading_cat, loading_an=loading_an, np=np,
        cap0=cap, cap=cap, wh_kg=wh_kg, mah_g=mah_g, v_avg=v_avg,
        m_tot=m_tot, m_cat=m_cat, m_an=m_an, m_el=m_el, m_sep=m_sep,
        r0=r0, v_max=v_max, v_min=v_min, c_th=c_th, ha=ha,
        sep_melt=160.0 if el != "SOLID" else 300.0,
        t_shutdown=130.0 if el != "SOLID" else 1.0e9,
    )


# ---------------------------------------------------------------- symulacja
SIM = dict(
    ea_fade=35000.0, ea_sei=50000.0, ea_ion=15000.0, ea_act=30000.0,
    ea_an_rxn=80000.0, tref_an_rxn=150.0,          # reakcja litowanej anody z elektrolitem
    ea_exo_sei=60000.0, tref_exo_sei=120.0, k_exo_sei=0.05,        # mW/g przy ref
    ea_exo_elec=110000.0, tref_exo_elec=160.0, k_exo_elec=200.0,  # rozklad elektrolitu (powolny)
    k_comb=100000.0,                                              # spalanie elektrolitu [mW/g] (>= t_decomp)
    ea_exo_cath=140000.0, tref_exo_cath=280.0, k_exo_cath=5000.0,
    tau_an=90.0, tau_cath=120.0,             # czas rozkladu energii egzotermicznej [s]
    k_sei=0.012,                             # nm / sqrt(h) przy 25C, sei_rate=elec=1
    li_per_nm=0.0008,                        # ubytek inwentarza Li na nm SEI
    fade_base=1.2e-4,                        # ulamek/cykl przy 1C, 25C, V=3.8, fade_mult=1
    plat_gain=0.002,                         # wzmocnienie frakcji ladowania litowego
    plat_k=0.025,                            # skala eksponencjalna platingu [V]
    ox_k=8e-4,                               # stres oksydacyjny elektrolitu (V ponad okno)^2
    t_runaway=200.0,
    dt_max=10.0, dt_min=0.5,
    min_delivered=0.30,                      # EOL "rate-limited" gdy ogniwo nie oddaje 30% w oknie
)


def simulate(cell, c_ch, c_dis=1.0, t_amb=25.0, max_cycles=3000, abuse=None):
    """Symuluje cykle CC (ladowanie c_ch, rozladowanie c_dis) az do EOL.
    abuse=dict(t_oven=150.0, overcharge=1.0, t_max_h=3.0) -- test abusow (piec)."""
    c = CATHODES[cell["cath"]]; a = ANODES[cell["an"]]; e = ELECTROLYTES[cell["el"]]
    p = CELL_DEFAULTS
    cap0 = cell["cap0"]
    cap = cell["cap"]
    v_max, v_min = cell["v_max"], cell["v_min"]
    r0 = cell["r0"]
    alpha = p["alpha"]
    np_ = cell["np"]
    i0f = p["i0_floor"]
    is_solid = cell["el"] == "SOLID"

    state = dict(li_inv=1.0, cath_frac=1.0, r_mult=1.0, sei=5.0, plated=0.0, dend=0.0,
                 t=t_amb, cycle=0, eol=None, runaway=False, explosion=False, short=False,
                 t_max=t_amb, t80=None, eta_sum=0.0, eta_n=0, hours=0.0,
                 delivered_frac=0.0, delivered_frac_1=None,
                 li_melt_j=0.0, li_melt_done=False, cath_exo_j=0.0, cath_exo_done=False,
                 trace=[])

    if abuse is not None:
        t_amb = abuse["t_oven"]
        state["t"] = t_amb

    def ocv(s):
        return interp(c["vcurve"], s) - interp(a["vcurve"], min(1.0, s / np_))

    def eta_cat(i_ma, s, t):
        i0 = c["i0"] * (math.sqrt(max(1e-6, s * (1.0 - s))) + i0f) * arr(t, 25.0, SIM["ea_act"])
        x = abs(i_ma) / (2.0 * i0)
        return math.copysign(math.asinh(x) * RG * (t + 273.15) / (alpha * F), i_ma)

    def eta_an(i_ma, s, t):
        s_an = min(1.0, s / np_)
        i0 = a["i0"] * (math.sqrt(max(1e-6, s_an * (1.0 - s_an))) + i0f) \
            * p["k_conc"] * arr(t, 25.0, SIM["ea_act"])
        x = abs(i_ma) / (2.0 * i0)
        return math.copysign(math.asinh(x) * RG * (t + 273.15) / (alpha * F), i_ma)

    def r_int(t):
        r = r0 * state["r_mult"] * (1.0 + 0.004 * state["sei"] + 0.5 * state["plated"])
        return r / arr(t, 25.0, SIM["ea_ion"])   # przewodnictwo jonowe spada w zimnie

    def side_heat(t):
        """Cieplo reakcji ubocznych [mW/cm^2] w temperaturze t."""
        q = 0.0
        m_sei_g = state["sei"] * 1e-7 * 2.0            # nm -> cm, 2 g/cm^3
        q += m_sei_g * SIM["k_exo_sei"] * arr(t, SIM["tref_exo_sei"], SIM["ea_exo_sei"])
        # reakcja litowanej anody (z SEI) z elektrolitem -- narasta lawinowo od ~150C
        if a["k_an"] > 0.0:
            q += cell["m_an"] / 1000.0 * 0.9 * a["k_an"] \
                * arr(t, SIM["tref_an_rxn"], SIM["ea_an_rxn"]) * (0.3 if is_solid else 1.0)
        q += cell["m_el"] / 1000.0 * SIM["k_exo_elec"] * arr(t, SIM["tref_exo_elec"], SIM["ea_exo_elec"]) \
            * (1.0 if e["flammable"] else 0.3)
        if e["flammable"] and t >= e["t_decomp"]:
            q += cell["m_el"] / 1000.0 * SIM["k_comb"]      # zaplon / spalanie
        q += cell["m_cat"] / 1000.0 * SIM["k_exo_cath"] * arr(t, SIM["tref_exo_cath"], SIM["ea_exo_cath"]) \
            * (1.0 if c["t_stable"] < 300.0 else 0.3)
        return q

    def check_safety():
        t = state["t"]
        if t > state["t_max"]:
            state["t_max"] = t
        if cell["an"] == "LIMETAL" and t >= a["t_stable"] and not state["li_melt_done"]:
            # stopienie litu (180C) -> reakcja egzotermiczna (energia skonczona)
            state["li_melt_done"] = True
            state["li_melt_j"] = cell["m_an"] / 1000.0 * 0.9 * a["dH"] \
                * (0.3 if is_solid else 1.0) * 1000.0  # mJ/cm^2
        if t >= c["t_stable"] and not state["cath_exo_done"]:
            # rozklad katody (uwolnienie tlenu / stopienie siarki) -> egzotermia
            state["cath_exo_done"] = True
            state["cath_exo_j"] = cell["m_cat"] / 1000.0 * 0.9 * c["dH"] \
                * (0.5 if is_solid else 1.0) * 1000.0  # mJ/cm^2
        if t >= cell["sep_melt"] and not state["short"]:
            state["short"] = True
            if e["flammable"]:
                state["explosion"] = True
        if e["flammable"] and t >= e["t_decomp"]:
            state["explosion"] = True
        if t >= SIM["t_runaway"] or state["explosion"]:
            state["runaway"] = True

    def step(dt, i_ma, s):
        """Jeden krok czasowy. Zwraca (nowe s, e_in [mJ], e_out [mJ])."""
        t = state["t"]
        if t >= cell["t_shutdown"]:
            i_ma = 0.0     # separator PP: zamkniecie porow -> brak przewodnictwa jonowego
        r = r_int(t)
        v_ocv = ocv(s)
        eta = eta_cat(i_ma, s, t) + eta_an(i_ma, s, t)
        v = v_ocv + i_ma * r / 1000.0 + eta   # i_ma > 0: ladowanie (V = OCV + IR + eta)
        s_new = s + i_ma * dt / 3600.0 / cap
        # ladowanie litu na anodzie podczas szybkiego ladowania
        if i_ma > 0 and a["plat"] > 0.0:
            c_rate = i_ma / cap
            s_an_surf = min(1.0, s / np_ * (1.0 + 0.02 * c_rate))
            phi_an = interp(a["vcurve"], s_an_surf) - abs(eta_an(i_ma, s, t))
            if phi_an < 0.0:
                low_t = 1.0 + max(0.0, (283.15 - (t + 273.15)) / 283.15) * 4.0
                f_plat = a["plat"] * min(0.5, SIM["plat_gain"] * math.exp(-phi_an / SIM["plat_k"])) * low_t
                plated_mah = f_plat * i_ma * dt / 3600.0
                dead = 0.55 * plated_mah
                state["li_inv"] -= dead / cap0
                state["plated"] += plated_mah
                state["dend"] += dead * a["dend"] * (0.5 if is_solid else 1.0)
        # cieplo: I^2R + aktywacja + reakcje uboczne + egzotermie (energia skonczona)
        q_mw = abs(i_ma) * (abs(i_ma) * r / 1000.0 + abs(eta)) + side_heat(t)
        if state["li_melt_j"] > 0.0:
            q_add = state["li_melt_j"] / SIM["tau_an"]
            q_mw += q_add
            state["li_melt_j"] = max(0.0, state["li_melt_j"] - q_add * dt)
        if state["cath_exo_j"] > 0.0:
            q_add = state["cath_exo_j"] / SIM["tau_cath"]
            q_mw += q_add
            state["cath_exo_j"] = max(0.0, state["cath_exo_j"] - q_add * dt)
        q_mw -= cell["ha"] * (t - t_amb)
        state["t"] += q_mw * dt / cell["c_th"]
        e_in = max(0.0, i_ma * v) * dt
        e_out = max(0.0, -i_ma * v) * dt
        check_safety()
        return s_new, e_in, e_out

    # ------------------------------------------------------------- protokol abusow
    if abuse is not None:
        s = 0.0
        t_end = abuse["t_max_h"] * 3600.0
        i_ma = abuse["overcharge"] * cap0
        dt = 2.0
        t = 0.0
        while t < t_end and not state["runaway"] and not state["short"]:
            s, _, _ = step(dt, i_ma, min(1.0, s))
            t += dt
        state["hours"] = t / 3600.0
        return finish(state, cell, cap0, c_ch, c_dis, t_amb)

    # ------------------------------------------------------------- cykle
    while state["cycle"] < max_cycles:
        state["cycle"] += 1
        plated_before = state["plated"]
        # ---- ladowanie CC do V_max
        s = 0.0
        dt = min(SIM["dt_max"], max(SIM["dt_min"], 3600.0 / (c_ch * 150.0)))
        i_ma = c_ch * cap
        t_ch = 0.0
        e_in = e_out = 0.0
        while s < 1.0:
            v = ocv(s) + i_ma * r_int(state["t"]) / 1000.0 + abs(eta_cat(i_ma, s, state["t"])) \
                + abs(eta_an(i_ma, s, state["t"]))
            if v >= v_max:
                break
            s, ei, eo = step(dt, i_ma, s)
            e_in += ei; e_out += eo
            t_ch += dt
            if state["t80"] is None and s >= 0.8:
                state["t80"] = t_ch
            if state["runaway"] or state["short"]:
                break
        s_top = s
        # ---- rozladowanie CC do V_min
        dt = min(SIM["dt_max"], max(SIM["dt_min"], 3600.0 / (c_dis * 150.0)))
        i_ma = -c_dis * cap
        t_dis = 0.0
        while s > 0.0:
            v = ocv(s) + i_ma * r_int(state["t"]) / 1000.0 + eta_cat(i_ma, s, state["t"]) \
                + eta_an(i_ma, s, state["t"])
            if v <= v_min:
                break
            s, ei, eo = step(dt, i_ma, s)
            e_in += ei; e_out += eo
            t_dis += dt
            if state["runaway"] or state["short"]:
                break
        # ulamek pojemnosci odprowadzony w oknie napiec przy danym C-rate
        state["delivered_frac"] = s_top - s
        if state["delivered_frac_1"] is None:
            state["delivered_frac_1"] = state["delivered_frac"]
        state["hours"] += (t_ch + t_dis) / 3600.0
        if e_in > 0:
            state["eta_sum"] += e_out / e_in
            state["eta_n"] += 1
        state["trace"].append((state["cycle"], s_top, s, cap, state["li_inv"], state["cath_frac"],
                               state["r_mult"], state["sei"], state["plated"], state["t"],
                               t_ch, t_dis))
        # ---- degradacja na koniec cyklu
        t_avg = min(max(state["t"], -20.0), 60.0)
        f_t = arr(t_avg, 25.0, SIM["ea_fade"])
        f_v = (v_max / 3.8) ** 4
        f_c = 1.0 + 0.35 * max(0.0, c_ch - 1.0) + 0.15 * max(0.0, c_ch - 1.0) ** 2
        fade_frac = SIM["fade_base"] * c["fade"] * f_v * f_t * f_c
        # stres oksydacyjny elektrolitu (katody wysokonapieciowe poza oknem elektrolitu)
        ox = SIM["ox_k"] * max(0.0, v_max - e["window"]) ** 2 * f_t
        fade_frac += ox
        state["cath_frac"] *= (1.0 - fade_frac)
        # SEI (wzrost paraboliczny) + ubytek inwentarza
        h_cyc = (t_ch + t_dis) / 3600.0
        f_t_sei = arr(t_avg, 25.0, SIM["ea_sei"])
        d_sei = SIM["k_sei"] * a["sei"] * e["sei"] * math.sqrt(max(h_cyc, 1e-9)) * f_t_sei \
            * (1.0 + 0.25 * max(0.0, c_ch - 1.0))
        state["sei"] += d_sei
        state["li_inv"] -= d_sei * SIM["li_per_nm"]
        # shuttle / samo-rozladowanie katody (Li-S)
        state["li_inv"] -= c["sd"] * h_cyc / 2.0
        # dead Li (Li metal, Si) + dendryty
        if a["dead_li"] > 0.0:
            dead = a["dead_li"] * (0.5 + 0.5 * c_ch)
            state["li_inv"] -= dead
            state["dend"] += dead * a["dend"] * (0.5 if is_solid else 1.0)
        # opor rosnie
        state["r_mult"] += 0.0004 * d_sei + 0.5 * (state["plated"] - plated_before) \
            + 0.4 * fade_frac + 2.0 * ox
        # pojemnosc rzeczywista (inwentarz Li + struktura katody); EOL = 80% pojemnosci poczatkowej
        cap = min(cap0 * state["li_inv"], cap0 * state["cath_frac"])
        # dendryty -> zwarcie
        if state["dend"] > 1.0 and not state["short"]:
            state["short"] = True
            if e["flammable"]:
                state["explosion"] = True
        # EOL
        if state["runaway"]:
            state["eol"] = "runaway"
            break
        if state["short"]:
            state["eol"] = "short"
            break
        if state["delivered_frac"] < SIM["min_delivered"]:
            state["eol"] = "rate-limited"
            break
        if cap < 0.8 * cap0:
            state["eol"] = "fade80"
            break
        # lekkie chlodzenie miedzy cyklami
        state["t"] += (t_amb - state["t"]) * 0.02

    if state["eol"] is None:
        state["eol"] = f">={max_cycles}"
    return finish(state, cell, cap0, c_ch, c_dis, t_amb)


def finish(state, cell, cap0, c_ch, c_dis, t_amb):
    return dict(
        cath=cell["cath"], an=cell["an"], el=cell["el"],
        loading=cell["loading_cat"], np=cell["np"],
        c_ch=c_ch, c_dis=c_dis, t_amb=t_amb,
        wh_kg=cell["wh_kg"], mah_g=cell["mah_g"], v_avg=cell["v_avg"],
        cycles=state["cycle"], eol=state["eol"],
        runaway=state["runaway"], explosion=state["explosion"], short=state["short"],
        t_max=state["t_max"], t80_min=(state["t80"] or 0.0) / 60.0,
        eta=(state["eta_sum"] / state["eta_n"]) if state["eta_n"] else 0.0,
        sei=state["sei"], plated=state["plated"], r_mult=state["r_mult"],
        hours=state["hours"], delivered_frac=state["delivered_frac"],
        delivered_frac_1=state["delivered_frac_1"] if state["delivered_frac_1"] is not None else 0.0,
        trace=state["trace"],
    )


# ---------------------------------------------------------------- kryteria + sweep
BASELINE = ("NMC811", "GRAPHITE", "LP57")   # referencyjne ogniwo Li-ion
MIN_CYCLES = 500                            # wymagane cykle przy szybkim ladowaniu
FAST_RATES = (2.0, 3.0)                     # co uznajemy za "szybkie ladowanie"
ABUSE = dict(t_oven=150.0, overcharge=1.0, t_max_h=3.0)


def evaluate_combo(cath, an, el, loading=20.0, np_=1.1, c_rates=FAST_RATES,
                   t_amb=25.0, max_cycles=3000, baseline_wh=None, energy_factor=1.0,
                   min_cycles=MIN_CYCLES):
    """Pelna ocena kombinacji materialow wg kryteriow projektu."""
    cell = build_cell(cath, an, el, loading_cat=loading, np=np_)
    if baseline_wh is None:
        baseline_wh = build_cell(*BASELINE, loading_cat=20.0, np=1.1)["wh_kg"]

    energy_pass = cell["wh_kg"] >= baseline_wh * energy_factor

    best = None   # najlepszy wynik sposrod szybkich C-rate
    worst_safe = True
    t_max_cyc = t_amb
    for cch in c_rates:
        r = simulate(cell, cch, 1.0, t_amb, max_cycles=max_cycles)
        if r["runaway"] or r["explosion"] or r["short"]:
            worst_safe = False
        t_max_cyc = max(t_max_cyc, r["t_max"])
        if best is None or r["cycles"] > best["cycles"]:
            best = r
    cycles_pass = (not (best["runaway"] or best["short"])) and best["cycles"] >= min_cycles

    # test abusow (piec 150C + przeladowanie): ogniwo nie moze wybuchnac ani wejsc w thermal runaway
    ab = simulate(cell, 1.0, 1.0, t_amb, max_cycles=1, abuse=ABUSE)
    abuse_safe = not (ab["explosion"] or ab["runaway"] or ab["short"])
    safety_pass = worst_safe and abuse_safe

    passed = energy_pass and cycles_pass and safety_pass
    t80 = best["t80_min"] if best["t80_min"] > 0.0 else 60.0
    score = (cell["wh_kg"] / 250.0 * 0.4
             + min(best["cycles"], 1500.0) / 1500.0 * 0.3
             + (1.0 if safety_pass else 0.0) * 0.2
             + min(1.0, 20.0 / t80) * 0.1)
    return dict(
        cath=cath, an=an, el=el, loading=loading, np=np_,
        wh_kg=cell["wh_kg"], mah_g=cell["mah_g"],
        energy_pass=energy_pass, cycles=best["cycles"], eol=best["eol"],
        c_best=best["c_ch"], t80=best["t80_min"], cycles_pass=cycles_pass,
        t_max=t_max_cyc, safety_pass=safety_pass,
        abuse_explosion=ab["explosion"], abuse_runaway=ab["runaway"], abuse_short=ab["short"],
        abuse_tmax=ab["t_max"],
        passed=passed, score=score,
    )


def show(r):
    flags = ("RUNAWAY " if r["runaway"] else "") + ("EXPL " if r["explosion"] else "") \
        + ("SHORT" if r["short"] else "")
    print(f"  {r['cath']:>8}/{r['an']:<8}/{r['el']:<6} load={r['loading']:>4.0f} "
          f"C={r['c_ch']:>3.0f} T={r['t_amb']:>4.0f} | "
          f"{r['wh_kg']:6.1f} Wh/kg {r['mah_g']:6.1f} mAh/g V={r['v_avg']:4.2f} | "
          f"EOL {str(r['eol']):>12} @cyc {r['cycles']:5d} | Tmax {r['t_max']:6.1f}C | "
          f"t80 {r['t80_min']:5.1f}min eta {r['eta']*100:5.1f}% | "
          f"deliv {r['delivered_frac']*100:4.0f}% | "
          f"sei {r['sei']:5.1f}nm plat {r['plated']:6.2f} | {flags}")


def show_combo(r):
    print(f"  {r['cath']:>8}/{r['an']:<8}/{r['el']:<6} load={r['loading']:>4.0f} | "
          f"{r['wh_kg']:6.1f} Wh/kg {'E' if r['energy_pass'] else '.'} | "
          f"cyc@fast {r['cycles']:5d} {'C' if r['cycles_pass'] else '.'} (C={r['c_best']:.0f}, "
          f"t80 {r['t80']:4.1f}min) | Tmax {r['t_max']:5.1f}C "
          f"{'S' if r['safety_pass'] else '.'} (abuse T {r['abuse_tmax']:5.1f}C"
          f"{' EXPL' if r['abuse_explosion'] else ''}{' RUN' if r['abuse_runaway'] else ''}{' SHORT' if r['abuse_short'] else ''}) | "
          f"{'PASS' if r['passed'] else 'FAIL'} score {r['score']:.2f}")


def main():
    print("== ogniwo referencyjne (bazowe Li-ion) ==")
    ref = build_cell(*BASELINE, loading_cat=20.0, np=1.1)
    print(f"REF {'/'.join(BASELINE)} load=20 NP=1.1: {ref['wh_kg']:.1f} Wh/kg, "
          f"{ref['mah_g']:.1f} mAh/g, V_avg={ref['v_avg']:.3f}, R0={ref['r0']:.2f} Ohm*cm^2, "
          f"V [{ref['v_min']:.2f}, {ref['v_max']:.2f}], m_tot={ref['m_tot']:.1f} mg/cm^2")
    for ld in (15.0, 20.0, 25.0):
        cc = build_cell(*BASELINE, loading_cat=ld)
        print(f"  load={ld:4.0f}: {cc['wh_kg']:6.1f} Wh/kg  R0={cc['r0']:5.2f}")

    print("\n== scenariusze pojedynczych ogniw ==")
    scenarios = [
        ("NMC811", "GRAPHITE", "LP57", 18.0, 1.1, 1.0, 25.0, 2000),
        ("NMC811", "GRAPHITE", "LP57", 18.0, 1.1, 2.0, 25.0, 2000),
        ("NMC811", "GRAPHITE", "LP57", 18.0, 1.1, 3.0, 25.0, 2000),
        ("NMC811", "GRAPHITE", "LP57", 18.0, 1.1, 6.0, 25.0, 2000),
        ("NMC811", "GRAPHITE", "LP57", 18.0, 1.1, 1.0, 0.0, 2000),
        ("NMC811", "GRAPHITE", "LP57", 18.0, 1.1, 2.0, 0.0, 2000),
        ("LFP", "LTO", "LP57", 20.0, 1.1, 3.0, 25.0, 2000),
        ("LFP", "LTO", "LP57", 20.0, 1.1, 6.0, 25.0, 2000),
        ("LFP", "LTO", "IONIC", 20.0, 1.1, 6.0, 25.0, 2000),
        ("NMC811", "SIC", "LP57", 20.0, 1.1, 2.0, 25.0, 2000),
        ("NMC811", "SIC", "IONIC", 22.0, 1.1, 3.0, 25.0, 2000),
        ("NMC811", "LIMETAL", "SOLID", 22.0, 1.05, 2.0, 25.0, 2000),
        ("SULFUR", "LIMETAL", "IONIC", 20.0, 1.05, 1.0, 25.0, 2000),
        ("NMC532", "HC", "LP57", 20.0, 1.1, 2.0, 25.0, 2000),
        ("LNMO", "GRAPHITE", "LP57", 20.0, 1.1, 2.0, 25.0, 2000),
        ("LNMO", "GRAPHITE", "IONIC", 20.0, 1.1, 2.0, 25.0, 2000),
        ("LMR", "GRAPHITE", "IONIC", 22.0, 1.1, 2.0, 25.0, 2000),
    ]
    for (ca, an, el, ld, np_, cch, tamb, mc) in scenarios:
        cell = build_cell(ca, an, el, loading_cat=ld, np=np_)
        r = simulate(cell, cch, 1.0, tamb, max_cycles=mc)
        show(r)

    print("\n== test abusow (piec 150C + przeladowanie 1C, 3 h) ==")
    for (ca, an, el) in [("NMC811", "GRAPHITE", "LP57"), ("NMC811", "GRAPHITE", "IONIC"),
                         ("LFP", "LTO", "IONIC"), ("LFP", "LTO", "LP57"),
                         ("LFP", "LTO", "SOLID"), ("NMC811", "GRAPHITE", "SOLID"),
                         ("NMC811", "LIMETAL", "SOLID"), ("NMC811", "LIMETAL", "LP57"),
                         ("LCO", "GRAPHITE", "LP57"), ("SULFUR", "LIMETAL", "IONIC"),
                         ("NMC811", "SIC", "LP57"), ("LFP", "GRAPHITE", "LP57"),
                         ("NMC811", "LTO", "LP57"), ("NMC532", "HC", "IONIC")]:
        cell = build_cell(ca, an, el, loading_cat=20.0)
        r = simulate(cell, 1.0, 1.0, 25.0, max_cycles=1, abuse=ABUSE)
        flags = ("RUNAWAY " if r["runaway"] else "") + ("EXPLOSION " if r["explosion"] else "") \
            + ("SHORT" if r["short"] else "survives")
        print(f"  {ca:>8}/{an:<8}/{el:<6} | Tmax {r['t_max']:6.1f}C | {flags} ({r['hours']:.2f} h)")

    print("\n== mini-sweep wg kryteriow (load=20, szybkie ladowanie 2C) ==")
    base_wh = build_cell(*BASELINE, loading_cat=20.0, np=1.1)["wh_kg"]
    print(f"  (bazowe Wh/kg = {base_wh:.1f}; kryteria: E>={base_wh:.0f} Wh/kg, >=500 cykli @>=2C, bezpieczny)")
    combos = []
    for ca in ("NMC811", "LFP", "NMC532", "LMR"):
        for an in ("GRAPHITE", "LTO", "SIC", "LIMETAL"):
            for el in ("LP57", "IONIC", "SOLID"):
                combos.append((ca, an, el))
    results = []
    for (ca, an, el) in combos:
        r = evaluate_combo(ca, an, el, loading=20.0, np_=1.1,
                           c_rates=(2.0,), max_cycles=1200, baseline_wh=base_wh)
        results.append(r)
        show_combo(r)
    results.sort(key=lambda r: -r["score"])
    print("\n== TOP 10 wg score ==")
    for r in results[:10]:
        show_combo(r)


if __name__ == "__main__":
    main()
