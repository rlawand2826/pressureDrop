import math

g = 981
SEP = "="*70

def lookup_C(Re):
    # For very low Re (< 21): C = sqrt(Re) / 10  (back-calculated from software K values)
    if Re < 21:
        return math.sqrt(Re) / 10
    table = [
        (5500,None,1.5),(5001,5499,1.49),(4990,5000,1.48),(4500,4989,1.47),
        (4000,4499,1.46),(3500,3999,1.45),(3300,3499,1.44),(2907,3299,1.43),
        (2666,2906,1.42),(2659,2665,1.42),(2651,2658,1.42),(2504,2650,1.41),
        (2200,2503,1.40),(2093,2199,1.39),(1914,2092,1.38),(1841,1913,1.37),
        (1800,1840,1.36),(1700,1799,1.35),(1600,1699,1.34),(1500,1599,1.33),
        (1400,1499,1.32),(1250,1399,1.31),(1150,1249,1.30),(950,1149,1.29),
        (860,949,1.28),(830,859,1.27),(810,829,1.26),(716,809,1.25),
        (700,715,1.24),(675,699,1.23),(650,674,1.22),(625,649,1.21),
        (600,624,1.20),(575,599,1.19),(550,574,1.18),(525,549,1.17),
        (500,524,1.16),(490,499,1.15),(480,489,1.14),(470,479,1.13),
        (460,469,1.12),(450,459,1.11),(440,449,1.10),(430,439,1.09),
        (410,429,1.08),(400,409,1.07),(390,399,1.06),(376,389,1.05),
        (350,375,1.04),(340,349,1.03),(320,339,1.02),(301,319,1.01),
        (201,300,1.00),(175,200,0.95),(150,174,0.90),(125,149,0.85),
        (100,124,0.80),(90,99,0.77),(80,89,0.75),(70,79,0.73),
        (60,69,0.70),(50,59,0.65),(40,49,0.60),(39,40,0.59),(38,39,0.58),
        (37,38,0.57),(36,37,0.56),(35,36,0.55),(34,35,0.54),(33,34,0.53),
        (32,33,0.52),(31,32,0.51),(30,31,0.50),(29,30,0.49),(28,29,0.48),
        (27,28,0.47),(26,27,0.46),(21,25,0.45)
    ]
    for lo, hi, c in table:
        if hi is None and Re >= lo: return c
        if hi is not None and lo <= Re <= hi: return c
    return None

def run_case(name, rho, mu_cP, W, flow_unit,
             D_pipe_cm, D_screen_cm, L_cm, D_open_cm,
             Q_pct, P_pct,
             exp_alpha, exp_A_pipe, exp_A100, exp_A50, exp_net100, exp_net50,
             exp_ratio100, exp_ratio50, exp_flow, exp_V100, exp_V50,
             exp_Re100, exp_Re50, exp_C100, exp_C50, exp_K100, exp_K50,
             exp_dP100_cm, exp_dP50_cm):
    print("\n" + SEP)
    print("CASE: " + name)
    print(SEP)
    fails = []

    def chk(label, calc, exp, tol_pct=0.5):
        if exp is None:
            return
        diff_pct = abs(calc - exp) / abs(exp) * 100 if exp != 0 else abs(calc)
        ok = diff_pct <= tol_pct
        status = "OK  " if ok else "FAIL"
        print(f"  [{status}] {label:25s}: calc={calc:<14.6g}  exp={exp:<14.6g}  diff={diff_pct:.3f}%")
        if not ok:
            fails.append(label)

    alpha = (Q_pct / 100) * (P_pct / 100)
    chk("alpha", alpha, exp_alpha, 0.2)

    A_pipe = math.pi / 4 * D_pipe_cm**2
    chk("A_pipe", A_pipe, exp_A_pipe, 0.2)

    A100 = math.pi * D_screen_cm * L_cm
    A50 = A100 / 2
    chk("A_screen(100%)", A100, exp_A100, 0.2)
    chk("A_screen(50%)", A50, exp_A50, 0.2)

    net100 = A100 * alpha
    net50 = A50 * alpha
    chk("Net_area(100%)", net100, exp_net100, 0.2)
    chk("Net_area(50%)", net50, exp_net50, 0.2)
    chk("Ratio(100%)", net100 / A_pipe, exp_ratio100, 0.2)
    chk("Ratio(50%)", net50 / A_pipe, exp_ratio50, 0.2)

    # kg/hr: Q_vol = W/rho  (software CGS convention)
    # m3/hr: Q_vol = W * 1e6 / 3600  (true volumetric cm3/s)
    if flow_unit == 'kg/hr':
        Q_vol = W / rho
    else:
        Q_vol = W * 1e6 / 3600
    chk("Q_vol", Q_vol, exp_flow, 0.05)

    V100 = Q_vol / A100
    V50 = Q_vol / A50
    chk("V(100%)", V100, exp_V100, 0.2)
    chk("V(50%)", V50, exp_V50, 0.2)

    mu_p = mu_cP * 0.01
    D_eff = D_open_cm / alpha
    Re100 = D_eff * V100 * rho / mu_p
    Re50 = D_eff * V50 * rho / mu_p
    chk("Re(100%)", Re100, exp_Re100, 0.5)
    chk("Re(50%)", Re50, exp_Re50, 0.5)

    C100 = lookup_C(Re100)
    C50 = lookup_C(Re50)

    if Re100 < 21:
        print(f"  [INFO] C(100%): Re={Re100:.5f} < 21 => C=sqrt(Re)/10 = {C100:.6f}  (exp={exp_C100})")
    else:
        chk("C(100%)", C100, exp_C100, 0.01)

    if Re50 < 21:
        print(f"  [INFO] C(50%):  Re={Re50:.5f} < 21 => C=sqrt(Re)/10 = {C50:.6f}  (exp={exp_C50})")
    else:
        chk("C(50%)", C50, exp_C50, 0.01)

    K100 = (1 - alpha**2) / (C100**2 * alpha**2)
    K50  = (1 - alpha**2) / (C50**2  * alpha**2)
    chk("K(100%)", K100, exp_K100, 0.5)
    chk("K(50%)",  K50,  exp_K50,  0.5)
    dP100 = K100 * rho * V100**2 / (2 * g)
    dP50  = K50  * rho * V50**2  / (2 * g)
    chk("dP(100%) cm", dP100, exp_dP100_cm, 1.0)
    chk("dP(50%)  cm", dP50,  exp_dP50_cm,  1.0)

    verdict = "ALL PASS" if not fails else "FAILS: " + ", ".join(fails)
    print(f"  >>> {verdict}")
    return fails


all_fails = {}

# SS1: ND031-PZSY-0303 | FMSTR51/52CL600 | Rating 150 | Size 1 | kg/hr
all_fails['SS1: 0303'] = run_case(
    'SS1: ND031-PZSY-0303 | FMSTR51/52CL600 | Sz1 | Rating150 | LOW PRES STEAM',
    rho=0.951, mu_cP=0.248, W=165, flow_unit='kg/hr',
    D_pipe_cm=2.5,
    D_screen_cm=2.6, L_cm=8.0, D_open_cm=0.05, Q_pct=62.7, P_pct=51,
    exp_alpha=0.31977, exp_A_pipe=4.909375,
    exp_A100=65.3536, exp_A50=32.6768,
    exp_net100=20.898120672, exp_net50=10.449060336,
    exp_ratio100=4.25677824, exp_ratio50=2.1283891,
    exp_flow=173.501577287066,
    exp_V100=2.65481285, exp_V50=5.30962571,
    exp_Re100=159.18239, exp_Re50=318.36479,
    exp_C100=0.9, exp_C50=1.01,
    exp_K100=10.83911, exp_K50=8.60668,
    exp_dP100_cm=0.037029, exp_dP50_cm=0.11761)

# SS2: ND031-PZSY-0305 | FMSTR51/52CL600 | Rating 300 | Size 1 | flow in m^3/hr
all_fails['SS2: 0305'] = run_case(
    'SS2: ND031-PZSY-0305 | FMSTR51/52CL600 | Sz1 | Rating300 | m3/hr input',
    rho=0.951, mu_cP=0.248, W=0.165, flow_unit='m3/hr',
    D_pipe_cm=2.5,
    D_screen_cm=2.6, L_cm=8.0, D_open_cm=0.05, Q_pct=62.7, P_pct=51,
    exp_alpha=0.31977, exp_A_pipe=4.909375,
    exp_A100=65.3536, exp_A50=32.6768,
    exp_net100=20.898120672, exp_net50=10.449060336,
    exp_ratio100=4.2567782, exp_ratio50=2.1283891,
    exp_flow=45.83205,
    exp_V100=0.70129343, exp_V50=1.40258685,
    exp_Re100=42.04951, exp_Re50=84.09901,
    exp_C100=0.6, exp_C50=0.75,
    exp_K100=24.388, exp_K50=15.60832,
    exp_dP100_cm=0.005814, exp_dP50_cm=0.014883)

# SS3: ND031-PZSY-0309 | FMSTR54-T | Rating 150 | Size 2 | CAUSTIC 10%
all_fails['SS3: 0309'] = run_case(
    'SS3: ND031-PZSY-0309 | FMSTR54-T | Sz2 | Rating150 | CAUSTIC 10%',
    rho=1.100, mu_cP=14, W=4000, flow_unit='kg/hr',
    D_pipe_cm=5,
    D_screen_cm=5.7, L_cm=13.8, D_open_cm=0.04, Q_pct=39.9, P_pct=51,
    exp_alpha=0.20349, exp_A_pipe=19.6375,
    exp_A100=247.14972, exp_A50=123.57486,
    exp_net100=50.2924965228, exp_net50=25.1462482614,
    exp_ratio100=2.561043744, exp_ratio50=1.2805219,
    exp_flow=3636.36363636364,
    exp_V100=14.71320152, exp_V50=29.42640304,
    exp_Re100=22.72421, exp_Re50=45.44842,
    exp_C100=0.45, exp_C50=0.6,
    exp_K100=114.32009, exp_K50=64.30505,
    exp_dP100_cm=13.874924, exp_dP50_cm=31.218578)

# SS4: ND031-PZSY-1304 | FMSTR51/52CL600 | Rating 150 | Size 1.5 | LOW PRES STEAM
all_fails['SS4: 1304'] = run_case(
    'SS4: ND031-PZSY-1304 | FMSTR51/52CL600 | Sz1.5 | Rating150 | LOW PRES STEAM',
    rho=0.951, mu_cP=0.248, W=1050, flow_unit='kg/hr',
    D_pipe_cm=4,
    D_screen_cm=4.8, L_cm=12.0, D_open_cm=0.05, Q_pct=62.7, P_pct=51,
    exp_alpha=0.31977, exp_A_pipe=12.568,
    exp_A100=180.9792, exp_A50=90.4896,
    exp_net100=57.871718784, exp_net50=28.935859392,
    exp_ratio100=4.604688, exp_ratio50=2.302344,
    exp_flow=1104.10094637224,
    exp_V100=6.1007063, exp_V50=12.20141261,
    exp_Re100=365.79793, exp_Re50=731.59586,
    exp_C100=1.04, exp_C50=1.25,
    exp_K100=8.11731, exp_K50=5.61899,
    exp_dP100_cm=0.146438, exp_dP50_cm=0.405471)

# SS5: ND031-PZSY-1311 | FMSTR54-T | Rating 300 | Size 3 | SUSPENDING AGENT | No Mesh
# Re < 21 => C = sqrt(Re)/10
all_fails['SS5: 1311'] = run_case(
    'SS5: ND031-PZSY-1311 | FMSTR54-T | Sz3 | Rating300 | SUSPENDING AGENT | No Mesh',
    rho=1.025, mu_cP=450, W=9225, flow_unit='kg/hr',
    D_pipe_cm=8, D_screen_cm=9, L_cm=18.7, D_open_cm=0.2, Q_pct=100, P_pct=40,
    exp_alpha=0.4, exp_A_pipe=50.272,
    exp_A100=528.7986, exp_A50=264.3993,
    exp_net100=211.51944, exp_net50=105.75972,
    exp_ratio100=4.2075, exp_ratio50=2.10375,
    exp_flow=9000,
    exp_V100=17.01971223, exp_V50=34.03942446,
    exp_Re100=1.93836, exp_Re50=3.87671,
    exp_C100=0.139225, exp_C50=0.196894,
    exp_K100=270.84752, exp_K50=135.42411,
    exp_dP100_cm=40.987757, exp_dP50_cm=81.975726)

# SS6: ND031-PZSY-1312 | FMSTR54-T | Rating 300 | Size 3 | SUSPENDING AGENT | No Mesh
# Re < 21 => C = sqrt(Re)/10
all_fails['SS6: 1312'] = run_case(
    'SS6: ND031-PZSY-1312 | FMSTR54-T | Sz3 | Rating300 | SUSPENDING AGENT | No Mesh',
    rho=1.025, mu_cP=230, W=10250, flow_unit='kg/hr',
    D_pipe_cm=8, D_screen_cm=9, L_cm=18.7, D_open_cm=0.2, Q_pct=100, P_pct=40,
    exp_alpha=0.4, exp_A_pipe=50.272,
    exp_A100=528.7986, exp_A50=264.3993,
    exp_net100=211.51944, exp_net50=105.75972,
    exp_ratio100=4.2075, exp_ratio50=2.10375,
    exp_flow=10000,
    exp_V100=18.91079137, exp_V50=37.82158273,
    exp_Re100=4.21382, exp_Re50=8.42764,
    exp_C100=0.205276, exp_C50=0.290304,
    exp_K100=124.59004, exp_K50=62.29502,
    exp_dP100_cm=23.277032, exp_dP50_cm=46.554063)

# ---------------------------------------------------------------------------
# SS7: ND031-PZSY-1319 | FMSTR54-T | Rating 150 | Size 2 | LOW PRES STEAM
# Mesh 40x34swg -> Q=39.9%, D=0.04cm | Perf 12mm x 14mm -> P=67%
# ---------------------------------------------------------------------------
all_fails['SS7: 1319'] = run_case(
    'SS7: ND031-PZSY-1319 | FMSTR54-T | Sz2 | Rating150 | LOW PRES STEAM',
    rho=0.951, mu_cP=0.245, W=4415, flow_unit='kg/hr',
    D_pipe_cm=5, D_screen_cm=5.7, L_cm=13.8, D_open_cm=0.04, Q_pct=39.9, P_pct=67,
    exp_alpha=0.26733,      exp_A_pipe=19.6375,
    exp_A100=247.14972,     exp_A50=123.57486,
    exp_net100=66.0705346476, exp_net50=33.0352673238,
    exp_ratio100=3.364508448, exp_ratio50=1.6822542,
    exp_flow=4642.48159831756,
    exp_V100=18.78408601,   exp_V50=37.56817202,
    exp_Re100=1090.98001,   exp_Re50=2181.96002,
    exp_C100=1.29,          exp_C50=1.39,
    exp_K100=7.8077,        exp_K50=6.7247,
    exp_dP100_cm=1.335318,  exp_dP50_cm=4.600389)

# ---------------------------------------------------------------------------
# SS8: ND031-PZSY-1616 | FMSTR54-T | Rating 300 | Size 4 | LOW PRES STEAM
# Mesh 40x36swg -> Q=48.4%, D=0.044cm | Perf 12mm x 14mm -> P=67%
# ---------------------------------------------------------------------------
all_fails['SS8: 1616-28k'] = run_case(
    'SS8: ND031-PZSY-1616 | FMSTR54-T | Sz4 | Rating300 | LOW PRES STEAM | W=28443',
    rho=0.998, mu_cP=1, W=28443, flow_unit='kg/hr',
    D_pipe_cm=10, D_screen_cm=11.8, L_cm=22.2, D_open_cm=0.044, Q_pct=48.4, P_pct=67,
    exp_alpha=0.32428,      exp_A_pipe=78.55,
    exp_A100=823.07832,     exp_A50=411.53916,
    exp_net100=266.9078376096, exp_net50=133.4539188048,
    exp_ratio100=3.397935552, exp_ratio50=1.6989678,
    exp_flow=28500,
    exp_V100=34.62610946,   exp_V50=69.25221891,
    exp_Re100=468.88544,    exp_Re50=937.77089,
    exp_C100=1.12,          exp_C50=1.28,
    exp_K100=6.78376,       exp_K50=5.19381,
    exp_dP100_cm=4.137228,  exp_dP50_cm=12.670244)

# ---------------------------------------------------------------------------
# SS9: ND031-PZSY-4311 | FMSTR54-T | Rating 150 | Size 2 | WATER
# Mesh 40x36swg -> Q=48.4%, D=0.044cm | Perf 6mm x 8mm -> P=51%
# ---------------------------------------------------------------------------
all_fails['SS9: 4311'] = run_case(
    'SS9: ND031-PZSY-4311 | FMSTR54-T | Sz2 | Rating150 | WATER',
    rho=0.983, mu_cP=0.5, W=3932, flow_unit='kg/hr',
    D_pipe_cm=5, D_screen_cm=5.7, L_cm=13.8, D_open_cm=0.044, Q_pct=48.4, P_pct=51,
    exp_alpha=0.24684,      exp_A_pipe=19.6375,
    exp_A100=247.14972,     exp_A50=123.57486,
    exp_net100=61.0064368848, exp_net50=30.5032184424,
    exp_ratio100=3.106629504, exp_ratio50=1.5533148,
    exp_flow=4000,
    exp_V100=16.18452167,   exp_V50=32.36904335,
    exp_Re100=567.17949,    exp_Re50=1134.35899,
    exp_C100=1.18,          exp_C50=1.29,
    exp_K100=11.06886,      exp_K50=9.26163,
    exp_dP100_cm=1.452637,  exp_dP50_cm=4.861851)

# ---------------------------------------------------------------------------
# SS10: ND031-PZSY-4312 | FMSTR54-T | Rating 300 | Size 2 | WATER
# Mesh 40x36swg -> Q=48.4%, D=0.044cm | Perf 6mm x 8mm -> P=51%
# ---------------------------------------------------------------------------
all_fails['SS10: 4312'] = run_case(
    'SS10: ND031-PZSY-4312 | FMSTR54-T | Sz2 | Rating300 | WATER | W=3953',
    rho=0.941, mu_cP=0.3, W=3953, flow_unit='kg/hr',
    D_pipe_cm=5, D_screen_cm=5.7, L_cm=13.8, D_open_cm=0.044, Q_pct=48.4, P_pct=51,
    exp_alpha=0.24684,      exp_A_pipe=19.6375,
    exp_A100=247.14972,     exp_A50=123.57486,
    exp_net100=61.0064368848, exp_net50=30.5032184424,
    exp_ratio100=3.106629504, exp_ratio50=1.5533148,
    exp_flow=4200.85015940489,
    exp_V100=16.99718761,   exp_V50=33.99437523,
    exp_Re100=950.3478,     exp_Re50=1900.69561,
    exp_C100=1.29,          exp_C50=1.37,
    exp_K100=9.26163,       exp_K50=8.21156,
    exp_dP100_cm=1.283312,  exp_dP50_cm=4.551247)

# ---------------------------------------------------------------------------
# SS11: ND031-PZSY-4312-1 | FMSTR54-T | Rating 300 | Size 2 | WATER
# Mesh 40x36swg -> Q=48.4%, D=0.044cm | Perf 12mm x 14mm -> P=67%
# ---------------------------------------------------------------------------
all_fails['SS11: 4312-1'] = run_case(
    'SS11: ND031-PZSY-4312-1 | FMSTR54-T | Sz2 | Rating300 | WATER | W=5100',
    rho=0.941, mu_cP=0.3, W=5100, flow_unit='kg/hr',
    D_pipe_cm=5, D_screen_cm=5.7, L_cm=13.8, D_open_cm=0.044, Q_pct=48.4, P_pct=67,
    exp_alpha=0.32428,      exp_A_pipe=19.6375,
    exp_A100=247.14972,     exp_A50=123.57486,
    exp_net100=80.1457112016, exp_net50=40.0728556008,
    exp_ratio100=4.081258368, exp_ratio50=2.0406292,
    exp_flow=5419.76620616366,
    exp_V100=21.92908091,   exp_V50=43.85816182,
    exp_Re100=933.3001,     exp_Re50=1866.60019,
    exp_C100=1.28,          exp_C50=1.37,
    exp_K100=5.19381,       exp_K50=4.53383,
    exp_dP100_cm=1.197892,  exp_dP50_cm=4.1827)

# ---------------------------------------------------------------------------
# SS12: ND031-PZSY-4312-2 | FMSTR54-T | Rating 300 | Size 2 | WATER | W=5600
# Mesh 40x34swg -> Q=39.9%, D=0.04cm | Perf 12mm x 14mm -> P=67%
# ---------------------------------------------------------------------------
all_fails['SS12: 4312-2a'] = run_case(
    'SS12: ND031-PZSY-4312-2 | FMSTR54-T | Sz2 | Rating300 | WATER | W=5600',
    rho=0.983, mu_cP=0.3, W=5600, flow_unit='kg/hr',
    D_pipe_cm=5, D_screen_cm=5.7, L_cm=13.8, D_open_cm=0.04, Q_pct=39.9, P_pct=67,
    exp_alpha=0.26733,      exp_A_pipe=19.6375,
    exp_A100=247.14972,     exp_A50=123.57486,
    exp_net100=66.0705346476, exp_net50=33.0352673238,
    exp_ratio100=3.364508448, exp_ratio50=1.6822542,
    exp_flow=5696.84638860631,
    exp_V100=23.05018346,   exp_V50=46.10036692,
    exp_Re100=1130.10538,   exp_Re50=2260.21076,
    exp_C100=1.29,          exp_C50=1.4,
    exp_K100=7.8077,        exp_K50=6.62898,
    exp_dP100_cm=2.078387,  exp_dP50_cm=7.05846)

# ---------------------------------------------------------------------------
# SS13: ND031-PZSY-4312-2 | FMSTR54-T | Rating 300 | Size 2 | WATER | W=7250
# Mesh 40x39swg -> Q=62.7%, D=0.05cm | Perf 12mm x 14mm -> P=67%
# ---------------------------------------------------------------------------
all_fails['SS13: 4312-2b'] = run_case(
    'SS13: ND031-PZSY-4312-2 | FMSTR54-T | Sz2 | Rating300 | WATER | W=7250',
    rho=0.983, mu_cP=0.3, W=7250, flow_unit='kg/hr',
    D_pipe_cm=5, D_screen_cm=5.7, L_cm=13.8, D_open_cm=0.05, Q_pct=62.7, P_pct=67,
    exp_alpha=0.42009,      exp_A_pipe=19.6375,
    exp_A100=247.14972,     exp_A50=123.57486,
    exp_net100=103.8251258748, exp_net50=51.9125629374,
    exp_ratio100=5.287084704, exp_ratio50=2.6435424,
    exp_flow=7375.38148524924,
    exp_V100=29.84175538,   exp_V50=59.68351075,
    exp_Re100=1163.81591,   exp_Re50=2327.63182,
    exp_C100=1.3,           exp_C50=1.4,
    exp_K100=2.76125,       exp_K50=2.38087,
    exp_dP100_cm=1.231995,  exp_dP50_cm=4.249119)

# ---------------------------------------------------------------------------
# SS14: ND031-PZSY-1616 | FMSTR54-T | Rating 300 | Size 4 | LOW PRES STEAM | W=10200
# Mesh 40x38swg -> Q=57.8%, D=0.048cm | Perf 12mm x 14mm -> P=67%
# ---------------------------------------------------------------------------
all_fails['SS14: 1616-10k'] = run_case(
    'SS14: ND031-PZSY-1616 | FMSTR54-T | Sz4 | Rating300 | LOW PRES STEAM | W=10200',
    rho=0.998, mu_cP=1, W=10200, flow_unit='kg/hr',
    D_pipe_cm=10, D_screen_cm=11.8, L_cm=22.2, D_open_cm=0.048, Q_pct=57.8, P_pct=67,
    exp_alpha=0.38726,      exp_A_pipe=78.55,
    exp_A100=823.07832,     exp_A50=411.53916,
    exp_net100=318.7453102032, exp_net50=159.3726551016,
    exp_ratio100=4.057865184, exp_ratio50=2.0289326,
    exp_flow=10220.4408817635,
    exp_V100=12.41733701,   exp_V50=24.83467401,
    exp_Re100=153.60226,    exp_Re50=307.20452,
    exp_C100=0.9,           exp_C50=1.01,
    exp_K100=6.99751,       exp_K50=5.5563,
    exp_dP100_cm=0.548823,  exp_dP50_cm=1.743148)

print("\n" + SEP)
print("MASTER SUMMARY")
print(SEP)
for case, fails in all_fails.items():
    status = "ALL PASS" if not fails else "FAIL: " + ", ".join(fails)
    print(f"  {case:20s}: {status}")
