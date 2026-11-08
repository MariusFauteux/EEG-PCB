"""Step 12: powered-off backfeed of the analogue rail (+5VA) from the electrodes. DC estimates, NOT measurements.

With the analogue rail off (ship mode, or ANA_ENABLE low), a positive voltage between electrodes drives current
through 94k -> TPD2E2U06 node -> 4.7k into the ADS1299 (or OPA376) input clamp diode to AVDD. The current returns
to the body through the other legs' clamp diodes from GND. Whatever reaches +5VA must leave through the rail's
loads. This script solves the DC operating point for Rev C8 (loads only) and Rev C9 (loads plus the Q201 clamp).

Model (assumptions marked A):
- Per leg: electrode/source resistance, 94k, clamp node (TPD2E2U06: breakdown 6.5-8.5 V at 1 mA, forward diode
  from GND), 4.7k, IC input with diodes to AVDD and from GND (ADS1299 SBAS499C and OPA376 SBOS406G: inputs are
  diode-clamped to the rails, 10 mA continuous limit). 17 legs: 16 ADC inputs and the REF buffer input.
- A: clamp diodes Is/n not specified; two corners (1e-15 A, n 1.0) and (1e-9 A, n 1.5); worst result kept.
- A: TPD2E2U06 reverse conduction 1 mA x exp((V - VBR)/0.15 V); VBR 8.5 V (max) sends most current to AVDD.
- Rail loads: R205 4.7k, R210 + R211 42k, R203 + R204 150k. A: unpowered ADS1299/OPA376 draw nothing and the
  LT3045 passes no current from OUT to IN (reverse-current protection recorded at Step 4; data sheet not re-read).
  Both assumptions can only overstate the rail rise.
- Q201 CSD17381F4 (SLPS411G): VGS(th) 0.65-1.10 V at 250 uA, 25 C. A: 90 mV/decade below threshold, square law
  above (EKV interpolation); this understates conduction against Figure 5-3, so it overstates the clamp voltage.
  Gate tied to +5VA through R209 1M; drain through R208 100R; Q202 holds the gate low while ANA_ENABLE is high.
Writes checks/backfeed_analysis.json; exits non-zero if a rule fails.
"""
from pathlib import Path
import json, math, sys

OUT = Path(__file__).resolve().parents[1] / 'checks' / 'backfeed_analysis.json'
VT = 0.02585
R1, R2 = 94000.0, 4700.0
R_LOAD = 1 / (1 / 4700 + 1 / 42000 + 1 / 150000)
R_D, R_PU = 100.0, 1e6
VTH = (0.65, 1.10); NVT = 0.090 / math.log(10)
K_CB = 250e-6 / math.log(2) ** 2
C_RAIL = 2 * 22e-6 + 5 * 1.1e-6 + 10e-6     # C203, C204, AVDD pin pairs, C123 (nominal, no DC-bias derating)
DIODES = {'Is 1e-15 n 1.0': (1e-15, 1.0), 'Is 1e-9 n 1.5': (1e-9, 1.5)}
VBR = 8.5

def diode(v, isat, n):
    return isat * (math.exp(min(v / (n * VT), 80)) - 1)

def bisect(f, lo, hi, it=200):
    flo = f(lo)
    for _ in range(it):
        mid = (lo + hi) / 2; fm = f(mid)
        if (fm > 0) == (flo > 0): lo, flo = mid, fm
        else: hi = mid
    return (lo + hi) / 2

def leg(vs, rs, va, d):
    """Current from a source at vs (vs. board GND) through one leg. Returns (I into leg, I into AVDD)."""
    isat, n = d
    def tvs(c):
        return 1e-3 * math.exp(min((c - VBR) / 0.15, 80)) if c > 0 else -diode(-c, isat, n)
    def from_pin(p):             # walk outwards from the IC pin: everything follows from its voltage
        ip = diode(p - va, isat, n) - diode(-p, isat, n)
        c = p + R2 * ip; i = ip + tvs(c)
        return c + (rs + R1) * i, i, diode(p - va, isat, n)
    p = bisect(lambda p: from_pin(p)[0] - vs, -3, va + 3, 70)
    _, i, ia = from_pin(p)
    return i, ia

def crowbar(va, vth):
    i = K_CB * math.log1p(math.exp(min((va - vth) / (2 * NVT), 80))) ** 2
    return min(i, va / R_D)

def solve(case, d, clamp, vth=VTH[1]):
    v, rs, k, m = case['V'], case['Rs'], case['k'], case['m']
    def body(va):                # find body potential vb so that k legs in = m legs out
        vb = bisect(lambda vb: k * leg(vb + v, rs, va, d)[0] + m * leg(vb, 0, va, d)[0], -60, 60, 60)
        ia = k * leg(vb + v, rs, va, d)[1] + m * leg(vb, 0, va, d)[1]
        return vb, ia
    def net(va):
        ia = body(va)[1]
        return ia - va / R_LOAD - (crowbar(va, vth) if clamp else 0)
    va = bisect(net, 0, 20, 50)
    vb, ia = body(va)
    i_leg = leg(vb + v, rs, va, d)
    return {'AVDD_V': va, 'I_into_AVDD_A': ia, 'I_per_positive_leg_A': i_leg[0], 'I_per_IC_pin_A': i_leg[1]}

CASES = [
    {'name': 'Half-cell / DC offset 0.5 V, one electrode against the other 16', 'V': 0.5, 'Rs': 0, 'k': 1, 'm': 16, 'class': 'realistic'},
    {'name': 'Dissimilar electrodes 1.0 V, 8 electrodes against 9', 'V': 1.0, 'Rs': 0, 'k': 8, 'm': 9, 'class': 'realistic'},
    {'name': 'Other instrument output, 15 V limited to 10 uA (300k + 1.2M), one electrode', 'V': 15, 'Rs': 1.5e6, 'k': 1, 'm': 16, 'class': 'realistic'},
    {'name': 'Other instrument single fault, 15 V limited to 50 uA (300k), one electrode', 'V': 15, 'Rs': 3e5, 'k': 1, 'm': 16, 'class': 'realistic'},
    {'name': 'Stimulator field or contact, 10 V across electrodes, 4 against 13', 'V': 10, 'Rs': 1e3, 'k': 4, 'm': 13, 'class': 'stimulator'},
    {'name': 'Stimulator compliance 30 V across electrodes, 8 against 9', 'V': 30, 'Rs': 1e3, 'k': 8, 'm': 9, 'class': 'stimulator'},
    {'name': 'Abuse: 100 V across electrodes, 8 against 9', 'V': 100, 'Rs': 0, 'k': 8, 'm': 9, 'class': 'abuse'},
]

res = {'assumptions': __doc__.split('Model (assumptions marked A):')[1].split('Writes')[0].strip(), 'R_load_ohm': R_LOAD, 'cases': []}
for case in CASES:
    row = {'case': case['name'], 'class': case['class']}
    for cfg, clamp in [('C8_no_clamp', False), ('C9_clamp', True)]:
        worst = None
        for dn, d in DIODES.items():
            for vth in (VTH if clamp else VTH[:1]):
                r = solve(case, d, clamp, vth); r['diode'] = dn
                if clamp: r['Vth'] = vth
                if worst is None or r['AVDD_V'] > worst['AVDD_V']: worst = r
                # current limits are checked at the worst current, not the worst voltage
                worst['max_I_per_IC_pin_A'] = max(worst.get('max_I_per_IC_pin_A', 0), r['I_per_IC_pin_A'])
        row[cfg] = worst
    res['cases'].append(row)

# Rail discharge after ANA_ENABLE falls (clamp at the high-threshold corner), Euler integration.
va, t, dt, times = 5.090, 0.0, 1e-5, {}   # C10 nominal +5VA (RSET 50.9k)
while va > 0.1 and t < 5:
    va -= (va / R_LOAD + crowbar(va, VTH[1])) / C_RAIL * dt; t += dt
    for lvl in (1.0, 0.5, 0.3):
        if va <= lvl and str(lvl) not in times: times[str(lvl)] = t
va, t2 = 5.090, 0.0
while va > 0.3 and t2 < 5:
    va -= va / R_LOAD / C_RAIL * dt; t2 += dt
res['discharge_s'] = {'C_rail_F': C_RAIL, 'C9_clamp_to_V': times, 'C8_bleeder_only_to_0.3V': t2,
                      'clamp_peak_current_A': 5.25 / R_D}
res['clamp_cost_in_operation_A'] = 5.25 / R_PU
# Isolated trigger (TLP2761, Toshiba data sheet): no galvanic path; barrier capacitance 0.4 pF typ, RS >= 1e12 ohm.
res['isolated_trigger'] = {'barrier_current_230Vrms_50Hz_A': 230 * 2 * math.pi * 50 * 0.4e-12,
                           'barrier_leakage_500V_A': 500 / 1e12, 'path': 'to board GND only; no route to +5VA'}

def get(cls, cfg, key='AVDD_V'): return max(c[cfg][key] for c in res['cases'] if c['class'] == cls)
rules = [
    ('C9: AVDD <= 0.5 V for half-cell, offset and current-limited instrument sources', get('realistic', 'C9_clamp') <= 0.5),
    ('C9: AVDD <= 1.5 V for stimulator cases up to 30 V', get('stimulator', 'C9_clamp') <= 1.5),
    ('C9: AVDD below the ADS1299 5.5 V absolute maximum even at 100 V', get('abuse', 'C9_clamp') < 5.5),
    ('C9: IC input-pin current <= 2 mA (5x margin to the 10 mA ADS1299/OPA376 limit) in every case',
     max(c['C9_clamp']['max_I_per_IC_pin_A'] for c in res['cases']) <= 2e-3),
    ('Clamp costs <= 10 uA from +5VA while the rail is on', res['clamp_cost_in_operation_A'] <= 10e-6),
    ('C9: rail reaches 0.3 V within 1 s of ANA_ENABLE falling (firmware waits 1 s before re-arming)',
     times.get('0.3', 9) <= 1.0),
]
res['C8_finding'] = {'stimulator_max_AVDD_V': get('stimulator', 'C8_no_clamp'), 'abuse_max_AVDD_V': get('abuse', 'C8_no_clamp'),
                     'realistic_max_AVDD_V': get('realistic', 'C8_no_clamp')}
res['rules'] = [{'rule': r, 'pass': bool(ok)} for r, ok in rules]
OUT.write_text(json.dumps(res, indent=2))
for c in res['cases']:
    print(f"{c['case'][:70]:70s} C8 {c['C8_no_clamp']['AVDD_V']:6.3f} V  C9 {c['C9_clamp']['AVDD_V']:6.3f} V  "
          f"I_AVDD {c['C9_clamp']['I_into_AVDD_A']*1e6:8.2f} uA  pin {c['C9_clamp']['max_I_per_IC_pin_A']*1e6:8.2f} uA")
print('discharge', res['discharge_s'])
for r, ok in rules: print(('PASS ' if ok else 'FAIL ') + r)
sys.exit(0 if all(ok for _, ok in rules) else 1)
