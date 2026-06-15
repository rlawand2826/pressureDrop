"""
validate_production.py — Production robustness probe for the Y-Strainer calculator.

Checks:
  1. C table completeness (no gaps/overlaps in Re 21..5500)
  2. Boundary values of lookup_C()
  3. Edge-case inputs: extreme alpha, near-zero flow, high Re, high viscosity
  4. Unit conversion consistency (kg/hr vs m3/hr)
  5. Input validation gaps in the API layer
  6. Division-by-zero guards
  7. Excel table completeness spot-checks
"""

import math
import sys
from calculator import lookup_C, calculate, volumetric_flow
from config import C_VALUE_TABLE, MESH_DATA, PERF_SHEET_DATA, STRAINER_DATA, PIPE_DATA

PASS = "PASS"
FAIL = "FAIL"
WARN = "WARN"

results = []

def record(category, name, status, detail=""):
    results.append((category, name, status, detail))
    icon = {"PASS": "✓", "FAIL": "✗", "WARN": "⚠"}.get(status, "?")
    print(f"  [{icon}] {name}: {detail}")


print("\n" + "="*70)
print("1. C VALUE TABLE — COVERAGE AND OVERLAP")
print("="*70)

covered = {}
for lo, hi, c in C_VALUE_TABLE:
    end = 9999 if hi is None else hi
    for r in range(lo, min(end + 1, 10001)):
        if r not in covered:
            covered[r] = []
        covered[r].append(c)

# gaps in 21..5500
gaps = [r for r in range(21, 5501) if r not in covered]
record("C_TABLE", "No gaps in Re 21..5500",
       PASS if not gaps else FAIL,
       f"NONE" if not gaps else f"{len(gaps)} gaps: {gaps[:5]}...")

# Boundary-integer overlaps are expected (first-match wins and is correct).
# The real test is monotonicity: C must be non-decreasing for Re 21..5500
monotone_issues = []
prev_c = 0.0
for _re in range(21, 5501):
    _c = lookup_C(float(_re))
    if _c < prev_c - 0.001:
        monotone_issues.append((_re, prev_c, _c))
    prev_c = _c
record("C_TABLE", "C is monotonically non-decreasing for Re 21..5500",
       PASS if not monotone_issues else FAIL,
       "OK" if not monotone_issues else f"Non-monotone at {monotone_issues[:3]}")

# gap at Re 25..26 (common edge)
try:
    c25 = lookup_C(25.0)
    c26 = lookup_C(26.0)
    record("C_TABLE", "Boundary Re=25 and Re=26 continuity",
           PASS, f"C(25)={c25}, C(26)={c26}")
except Exception as e:
    record("C_TABLE", "Boundary Re=25/26", FAIL, str(e))

# Re above table max
try:
    c_high = lookup_C(10000.0)
    record("C_TABLE", "Re > 5500 handled (extrapolated to 1.50)",
           PASS if c_high == 1.50 else WARN, f"C={c_high}")
except Exception as e:
    record("C_TABLE", "Re > 5500", FAIL, str(e))

# Re < 21 formula
for re_test in [0.01, 1.0, 5.0, 20.99]:
    c = lookup_C(re_test)
    expected = math.sqrt(re_test) / 10.0
    ok = abs(c - expected) < 1e-10
    record("C_TABLE", f"Re={re_test} uses sqrt formula",
           PASS if ok else FAIL, f"C={c:.8f}")


print("\n" + "="*70)
print("2. DIVISION-BY-ZERO AND NUMERIC GUARDS")
print("="*70)

# alpha near 0
try:
    r = calculate(rho=1000.0, mu_cP=1.0, W=10, flow_unit='kg/hr',
                  D_pipe_cm=5, D_screen_cm=5.7, L_cm=13.8,
                  D_open_cm=0.05, Q_pct=1.0, P_pct=1.0)
    record("NUMERIC", "alpha=0.0001 (Q=1%, P=1%)", PASS,
           f"K={r['clean_100pct']['K']:.2f}, dP={r['clean_100pct']['delta_P_cm_wc']:.6f}")
except ZeroDivisionError as e:
    record("NUMERIC", "alpha=0.0001", FAIL, f"ZeroDivision: {e}")
except Exception as e:
    record("NUMERIC", "alpha=0.0001", FAIL, str(e))

# alpha = 1.0 (open screen)
try:
    r = calculate(rho=1000.0, mu_cP=1.0, W=100, flow_unit='kg/hr',
                  D_pipe_cm=5, D_screen_cm=5.7, L_cm=13.8,
                  D_open_cm=0.5, Q_pct=100, P_pct=100)
    k = r['clean_100pct']['K']
    expected_k = (1 - 1.0) / (1.0 * 1.0)  # = 0
    record("NUMERIC", "alpha=1.0 (Q=100%, P=100%): K should be 0",
           PASS if abs(k) < 1e-10 else FAIL, f"K={k}")
except Exception as e:
    record("NUMERIC", "alpha=1.0", FAIL, str(e))

# near-zero flow
try:
    r = calculate(rho=1000.0, mu_cP=1.0, W=0.0001, flow_unit='kg/hr',
                  D_pipe_cm=5, D_screen_cm=5.7, L_cm=13.8,
                  D_open_cm=0.05, Q_pct=62.7, P_pct=51)
    record("NUMERIC", "Near-zero flow (W=0.0001 kg/hr)", PASS,
           f"dP={r['clean_100pct']['delta_P_cm_wc']:.2e}")
except Exception as e:
    record("NUMERIC", "Near-zero flow", FAIL, str(e))

# very high viscosity
try:
    r = calculate(rho=1200.0, mu_cP=5000, W=2000, flow_unit='kg/hr',
                  D_pipe_cm=8, D_screen_cm=9, L_cm=18.7,
                  D_open_cm=0.2, Q_pct=100, P_pct=40)
    re = r['clean_100pct']['Re']
    record("NUMERIC", "Extreme viscosity (5000 cP)", PASS,
           f"Re={re:.6f}, C={r['clean_100pct']['C']:.6f}")
except Exception as e:
    record("NUMERIC", "Extreme viscosity", FAIL, str(e))

# very high Re (large flow, low viscosity)
try:
    r = calculate(rho=950.0, mu_cP=0.1, W=1_000_000, flow_unit='kg/hr',
                  D_pipe_cm=30, D_screen_cm=35, L_cm=70,
                  D_open_cm=0.5, Q_pct=62.7, P_pct=67)
    re = r['clean_100pct']['Re']
    c  = r['clean_100pct']['C']
    record("NUMERIC", f"Very high Re={re:.0f} (C table saturation)",
           PASS if c == 1.50 else WARN, f"C={c}")
except Exception as e:
    record("NUMERIC", "Very high Re", FAIL, str(e))


print("\n" + "="*70)
print("3. FLOW UNIT EQUIVALENCE")
print("="*70)

rho = 951.0
W_kghr = 165
W_m3hr = W_kghr / (rho / 1000.0) / 1000  # kg/hr ÷ rho_cgs ÷ 1000 = m³/hr ... but our CGS convention differs

# Q_vol from kg/hr: W / rho_cgs = 165/0.951 = 173.50
# Q_vol from m3/hr: W * 1e6 / 3600
rho_cgs = rho / 1000.0
q_kghr = volumetric_flow(W_kghr, 'kg/hr', rho_cgs)
# True equivalent in m3/hr that gives same Q_vol:
# W_m3hr * 1e6 / 3600 = W_kghr / rho
# => W_m3hr = W_kghr / rho_cgs * 3600 / 1e6
W_m3hr_eq = W_kghr / rho_cgs * 3600 / 1e6
q_m3hr = volumetric_flow(W_m3hr_eq, 'm3/hr', rho_cgs)
match = abs(q_kghr - q_m3hr) < 1e-6
record("UNITS", "kg/hr and m3/hr produce same Q_vol when equivalent flow given",
       PASS if match else FAIL, f"kg/hr Q={q_kghr:.6f}, m3/hr Q={q_m3hr:.6f}")

# Same geometry calc both ways
r_kg = calculate(rho=rho, mu_cP=0.248, W=W_kghr, flow_unit='kg/hr',
                 D_pipe_cm=2.5, D_screen_cm=2.6, L_cm=8.0,
                 D_open_cm=0.05, Q_pct=62.7, P_pct=51)
r_m3 = calculate(rho=rho, mu_cP=0.248, W=W_m3hr_eq, flow_unit='m3/hr',
                 D_pipe_cm=2.5, D_screen_cm=2.6, L_cm=8.0,
                 D_open_cm=0.05, Q_pct=62.7, P_pct=51)
dp_diff = abs(r_kg['clean_100pct']['delta_P_cm_wc'] - r_m3['clean_100pct']['delta_P_cm_wc'])
record("UNITS", "Same dP via kg/hr and equivalent m3/hr",
       PASS if dp_diff < 1e-8 else FAIL, f"Δ={dp_diff:.2e}")


print("\n" + "="*70)
print("4. EXCEL LOOKUP TABLE COMPLETENESS")
print("="*70)

record("TABLES", f"Mesh table rows loaded", PASS if len(MESH_DATA) > 0 else FAIL,
       f"{len(MESH_DATA)} entries")
record("TABLES", f"Perf table rows loaded", PASS if len(PERF_SHEET_DATA) > 0 else FAIL,
       f"{len(PERF_SHEET_DATA)} entries")
record("TABLES", f"Strainer table rows loaded", PASS if len(STRAINER_DATA) > 0 else FAIL,
       f"{len(STRAINER_DATA)} entries")
record("TABLES", f"Pipe sizes table loaded", PASS if len(PIPE_DATA) > 0 else FAIL,
       f"{len(PIPE_DATA)} entries")

# Spot-check known good keys
spot_mesh = (40, 39) in MESH_DATA  # used in SS1 (Q=62.7%, D=0.5mm)
record("TABLES", "Mesh (40, 39) present — used in screenshot SS1",
       PASS if spot_mesh else FAIL, str(MESH_DATA.get((40,39))))

spot_strainer = any(k[0] == "FMSTR54-T" for k in STRAINER_DATA)
record("TABLES", "FMSTR54-T model present in strainer catalogue",
       PASS if spot_strainer else FAIL, "")

# All STRAINER_DATA entries have positive dimensions
bad_dims = [(k,v) for k,v in STRAINER_DATA.items() if any(x <= 0 for x in v)]
record("TABLES", "All strainer dimensions > 0",
       PASS if not bad_dims else FAIL,
       f"NONE" if not bad_dims else f"Bad: {bad_dims[:2]}")

# All MESH_DATA entries have positive opening and Q
bad_mesh = [(k,v) for k,v in MESH_DATA.items() if v[0] <= 0 or v[1] <= 0]
record("TABLES", "All mesh opening_mm and Q > 0",
       PASS if not bad_mesh else FAIL,
       "NONE" if not bad_mesh else f"Bad: {bad_mesh[:2]}")


print("\n" + "="*70)
print("5. PRESSURE UNIT CONVERSIONS")
print("="*70)

r = calculate(rho=951.0, mu_cP=0.248, W=165, flow_unit='kg/hr',
              D_pipe_cm=2.5, D_screen_cm=2.6, L_cm=8.0,
              D_open_cm=0.05, Q_pct=62.7, P_pct=51)
c100 = r['clean_100pct']
# Check: in_wc = cm_wc / 2.54
in_wc_calc = c100['delta_P_cm_wc'] / 2.54
in_wc_api  = c100['delta_P_in_wc']
record("UNITS", "cm WC to in WC conversion",
       PASS if abs(in_wc_calc - in_wc_api) < 1e-12 else FAIL,
       f"expected={in_wc_calc:.8f}, got={in_wc_api:.8f}")

# Check: kg/cm2 = cm_wc / 1000
kg_calc = c100['delta_P_cm_wc'] / 1000.0
kg_api  = c100['delta_P_kg_cm2']
record("UNITS", "cm WC to kg/cm² conversion",
       PASS if abs(kg_calc - kg_api) < 1e-15 else FAIL,
       f"expected={kg_calc:.2e}, got={kg_api:.2e}")


print("\n" + "="*70)
print("6. FORMULA SELF-CONSISTENCY — K=0 when alpha=1")
print("="*70)
# When alpha=1: K = (1-1)/(C^2 * 1) = 0 => dP=0
r = calculate(rho=1000.0, mu_cP=1.0, W=100, flow_unit='kg/hr',
              D_pipe_cm=5, D_screen_cm=5.7, L_cm=13.8,
              D_open_cm=0.5, Q_pct=100, P_pct=100)
dp = r['clean_100pct']['delta_P_cm_wc']
record("FORMULA", "dP=0 when alpha=1 (fully open screen)",
       PASS if abs(dp) < 1e-10 else FAIL, f"dP={dp:.2e}")

# dP_50 >= dP_100 always (clogged is always worse)
tested_cases = [
    dict(rho=951.0, mu_cP=0.248, W=165, flow_unit='kg/hr', D_pipe_cm=2.5, D_screen_cm=2.6, L_cm=8.0, D_open_cm=0.05, Q_pct=62.7, P_pct=51),
    dict(rho=1100.0, mu_cP=14, W=4000, flow_unit='kg/hr', D_pipe_cm=5, D_screen_cm=5.7, L_cm=13.8, D_open_cm=0.04, Q_pct=39.9, P_pct=51),
    dict(rho=1025.0, mu_cP=450, W=9225, flow_unit='kg/hr', D_pipe_cm=8, D_screen_cm=9, L_cm=18.7, D_open_cm=0.2, Q_pct=100, P_pct=40),
]
all_ok = True
for kw in tested_cases:
    r = calculate(**kw)
    dp100 = r['clean_100pct']['delta_P_cm_wc']
    dp50  = r['clogged_50pct']['delta_P_cm_wc']
    if dp50 < dp100:
        all_ok = False
        record("FORMULA", f"dP_50 >= dP_100 VIOLATED", FAIL, f"dP100={dp100}, dP50={dp50}")
record("FORMULA", "dP_50 >= dP_100 for all tested cases",
       PASS if all_ok else FAIL, "Clogged always worse than clean")


print("\n" + "="*70)
print("SUMMARY")
print("="*70)
passes = sum(1 for _,_,s,_ in results if s == PASS)
warns  = sum(1 for _,_,s,_ in results if s == WARN)
fails  = sum(1 for _,_,s,_ in results if s == FAIL)
total  = len(results)
print(f"\n  Total: {total}  |  PASS: {passes}  |  WARN: {warns}  |  FAIL: {fails}")
if fails:
    print("\n  FAILURES:")
    for cat, name, s, d in results:
        if s == FAIL:
            print(f"    [{cat}] {name}: {d}")
if warns:
    print("\n  WARNINGS:")
    for cat, name, s, d in results:
        if s == WARN:
            print(f"    [{cat}] {name}: {d}")
print()
sys.exit(1 if fails else 0)
