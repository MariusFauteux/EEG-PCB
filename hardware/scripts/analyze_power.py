"""Step 10 power and supervision envelope: closes the deferred Step 4 review at calculation level.

Static worst-case envelopes for the analogue rail and the five TPS389001 monitors, supervisor release
delays, rail-collapse timing and the edge rates presented to the reset logic. Datasheet-derived
estimates, NOT measurements. Writes checks/power_analysis.json and exits non-zero if a design rule fails.

Sources: TI TPS3890 SLVSD65A (thresholds, hysteresis, ISENSE, ICT, VCT, tPD); TI SN74AUP1G08 SCES502Q and
SN74LVC1G74 SCES794G (input transition limits); LT3045 limits as recorded in the Step 4 review
(ISET 98-102 uA full range, VOS +/-2 mV, 330 mV dropout up to 50 mA); ADS1299 AVDD 4.75-5.25 V.
"""
from pathlib import Path
import json, itertools, math, sys

OUT = Path(__file__).resolve().parents[1] / 'checks' / 'power_analysis.json'
ADC_MIN, ADC_MAX = 4.75, 5.25           # ADS1299 AVDD - AVSS recommended operating range
R_TOL = 0.002                           # 0.1 % initial + 10 ppm/K over 100 K
ISET = (98e-6, 102e-6); VOS = 2e-3      # LT3045 full-range SET current and OUTS offset
DROPOUT_50MA = 0.330
# CSET leakage: Murata class-II IR spec C > 0.047 uF: >= 500 ohm.F at rated voltage (room temperature).
# 4.7 uF -> >= 106 Mohm; at ~5.1 V on SET this diverts <= 48 nA from RSET (lowers VOUT). Hot IR is lower.
CSET = 4.7e-6; ILEAK_CSET = 5.1 / (500 / CSET)
VITN, VITP, VTH_ACC = 1.150, 1.157, 0.01   # TPS389001 falling/rising threshold, +/-1 % each
ISENSE = 100e-9                          # TPS389001 max sense current (sign treated as unknown)
ICT = (0.90e-6, 1.35e-6); VCT = (1.17, 1.29)

def corners(nom):
    return (nom * (1 - R_TOL), nom * (1 + R_TOL))

def rail(rset_parts):
    lo = sum(r * (1 - R_TOL) for r in rset_parts); hi = sum(r * (1 + R_TOL) for r in rset_parts)
    nom = sum(rset_parts) * 100e-6
    vmin = ISET[0] * lo - VOS - ILEAK_CSET * lo
    vmax = ISET[1] * hi + VOS
    return nom, vmin, vmax

def trip(r_top, r_bot, vit):
    """Rail voltage at which the SENSE node reaches the threshold, over resistor, threshold and ISENSE corners."""
    vals = []
    for rt, rb, v, i in itertools.product(corners(r_top), corners(r_bot), (vit * (1 - VTH_ACC), vit * (1 + VTH_ACC)), (-ISENSE, ISENSE)):
        vals.append((v + i * rt * rb / (rt + rb)) * (rt + rb) / rb)
    return (vit * (r_top + r_bot) / r_bot, min(vals), max(vals))

def monitor(name, r_top, r_bot):
    n, lo, hi = trip(r_top, r_bot, VITN); rn, rlo, rhi = trip(r_top, r_bot, VITP)
    return {'name': name, 'divider': [r_top, r_bot], 'assert_nom_V': round(n, 4), 'assert_V': [round(lo, 4), round(hi, 4)],
            'release_nom_V': round(rn, 4), 'release_V': [round(rlo, 4), round(rhi, 4)]}

# Step 13 (C10): RSET = 49.9k + 1.00k and ANALOG_OK 31.6k/9.88k, because the C7-C9 values 50.5k and 32.0k are
# E192-only and not orderable in the ERA-3ARB 0.1 % / 10 ppm/K series (Panasonic ERA-A data sheet, 24-Apr-2024).
old = rail([50.5e3, 383.0]); new = rail([49.9e3, 1.00e3])
mon = {k: monitor(k, *v) for k, v in {
    'ANALOG_OK': (31.6e3, 9.88e3), 'DIGITAL_OK': (17.4e3, 10e3), 'SYS_OK': (40.2e3, 10e3),
    'PACK_OK': (44.2e3, 10e3), 'BAT_WARN_OK': (47.5e3, 10e3)}.items()}
a = mon['ANALOG_OK']; a_c9 = monitor('ANALOG_OK', 32.0e3, 10e3)

def margins(r, a=None):
    a = a or mon['ANALOG_OK']
    nom, vmin, vmax = r
    return {'rail_nom_V': round(nom, 4), 'rail_V': [round(vmin, 4), round(vmax, 4)],
            'release_margin_mV': round((vmin - a['release_V'][1]) * 1e3, 1),
            'assert_above_adc_min_mV': round((a['assert_V'][0] - ADC_MIN) * 1e3, 1),
            'below_adc_max_mV': round((ADC_MAX - vmax) * 1e3, 1),
            'sys_inhibit_above_dropout_mV': round((mon['SYS_OK']['assert_V'][0] - (vmax + DROPOUT_50MA)) * 1e3, 1)}

# Release delay: tD = CT * VCT / ICT (+ small fixed term, ignored). C0G +/-5 % for the selected CT parts.
def delay(c, tol):
    return [round(c * (1 - tol) * VCT[0] / ICT[1] * 1e3, 1), round(c * (1 + tol) * VCT[1] / ICT[0] * 1e3, 1)]
delays = {'100n C0G 5%': delay(100e-9, 0.05), '10n C0G 5%': delay(10e-9, 0.05), '100n X7R 10% (old)': delay(100e-9, 0.10)}

# Rail collapse. Path A: SYS falls; SYS_OK inhibits ANA_ENABLE (and so resets the ADC) while the LT3045 is
# still regulating, provided SYS crosses the window [vmax+dropout, SYS assert min] slower than the monitor responds.
# tPD(f) is typical only (18 us at VDD 3.3 V, 5 % overdrive); allow 3x for small overdrive and spread.
TPD = 18e-6; TPD_ALLOW = 3 * TPD
window = (mon['SYS_OK']['assert_V'][0] - (new[2] + DROPOUT_50MA))
sys_slew_max = window / TPD_ALLOW                  # V/s
sys_loads = {'average (analog 50 mA + digital 30 mA at 3.3 V)': 0.050 + 3.3 * 0.030 / 0.85 / 5.7,
             'peak (analog 50 mA + digital 480 mA at 3.3 V)': 0.050 + 3.3 * 0.480 / 0.85 / 5.7}
path_a = {k: {'I_SYS_A': round(i, 3), 'C_SYS_effective_needed_uF': round(i / sys_slew_max * 1e6, 1)} for k, i in sys_loads.items()}
# Path B: AVDD itself decays on its output capacitance (LT3045 blocks reverse current into SYS).
def path_b(i_load, c_out):
    slew = i_load / c_out
    undershoot = max(0.0, slew * TPD_ALLOW - (a['assert_V'][0] - ADC_MIN))
    return {'I_analog_mA': i_load * 1e3, 'C_out_eff_uF': c_out * 1e6, 'slew_mV_per_us': round(slew * 1e-3, 2),
            'AVDD_at_reset_worst_V': round(ADC_MIN - undershoot, 3)}
path_b_cases = [path_b(i, c) for i, c in [(0.010, 20e-6), (0.050, 20e-6), (0.050, 10e-6)]]

# Edge rate at reset-logic inputs: open-drain pull-up R with node capacitance C; 10-90 % over 0.8 VCC.
def edge(r, c):
    return round(2.2 * r * c / (0.8 * 3.3) * 1e9, 1)  # ns/V
edges = {f'{r/1e3:g}k / {c*1e12:g} pF': edge(r, c) for r, c in itertools.product([100e3, 10e3, 4.7e3], [10e-12, 20e-12, 30e-12])}
LIMITS = {'SN74LVC1G08 dt/dv max ns/V': 10, 'SN74AUP1G08 dt/dv max ns/V (Schmitt inputs)': 200}

result = {'C9_RSET_50k5_383R': margins(old, a_c9), 'C10_RSET_49k9_1k00': margins(new), 'monitors': mon, 'cset_leakage_nA_max_room_temp': round(ILEAK_CSET * 1e9, 1),
          'release_delay_ms': delays, 'collapse': {'tpd_allowance_us': TPD_ALLOW * 1e6, 'path_A_window_mV': round(window * 1e3, 1),
          'path_A_max_SYS_slew_mV_per_us': round(sys_slew_max * 1e-6 * 1e3, 2), 'path_A_capacitance': path_a, 'path_B': path_b_cases},
          'edge_rate_ns_per_V': edges, 'edge_limits_ns_per_V': LIMITS,
          'pullup_standby_current_mA_per_asserted_monitor': round(3.3 / 4.7e3 * 1e3, 2)}
# ---- Step 11: BQ25798 charger (TI SLUSDV2C). ----
# ILIM_HIZ hardware input-current ceiling: V = 1 V + 0.8 ohm x ILIM, divider from REGN (4.6-5.0 V at VBUS = 5 V).
REGN = (4.6, 5.0); RT_ILIM, RB_ILIM, RTOL = 27.0e3, 10.0e3, 0.01
def ilim(regn, rt, rb): return (regn * rb / (rt + rb) - 1.0) / 0.8
def pct(v, t): return (v * (1 - t), v * (1 + t))
ilim_vals = [ilim(g, rt, rb) for g in REGN for rt in pct(RT_ILIM, RTOL) for rb in pct(RB_ILIM, RTOL)]
ilim_nom = ilim(4.8, RT_ILIM, RB_ILIM)
# TS window with a 103AT-2 NTC (10k at 25 C, B25/85 = 3435 K). Thresholds as % of REGN: T1 rise 73.3 % (0 C), T5 fall 34.2 % (60 C).
def rntc(tc): return 10e3 * math.exp(3435 * (1 / (tc + 273.15) - 1 / 298.15))
def ts_ratio(tc, r1, r2):
    rp = 1 / (1 / r2 + 1 / rntc(tc)); return rp / (r1 + rp)
def ts_temp(target, r1, r2):
    lo, hi = -40.0, 100.0                       # ratio falls with temperature
    for _ in range(60):
        mid = (lo + hi) / 2
        if ts_ratio(mid, r1, r2) > target: lo = mid
        else: hi = mid
    return (lo + hi) / 2
ts = {}
for name, (r1, r2) in {'TI example 5.24k/30.31k': (5.24e3, 30.31e3), 'selected E96 5.23k/30.1k': (5.23e3, 30.1e3)}.items():
    ts[name] = {'T1_charge_suspend_below_C': round(ts_temp(0.733, r1, r2), 2), 'T5_charge_suspend_above_C': round(ts_temp(0.342, r1, r2), 2)}
ts_shift = max(abs(ts['selected E96 5.23k/30.1k'][k] - ts['TI example 5.24k/30.31k'][k]) for k in ts['TI example 5.24k/30.31k'])
# SYS hold-up. Ceramic retention at 8.4 V from the Murata GRM32ER71E226KE15 DC-bias curve (25 C): -46.7 % (Step 13;
# Step 11 assumed 40 % retention). OS-CON -20 % tolerance. review_corners.py also applies -10 % / -15 % worst case.
c_sys_eff = 0.8 * 100e-6 + 5 * 22e-6 * (1 - 0.467)
need_avg = path_a[next(k for k in path_a if k.startswith('average'))]['C_SYS_effective_needed_uF'] * 1e-6
need_peak = path_a[next(k for k in path_a if k.startswith('peak'))]['C_SYS_effective_needed_uF'] * 1e-6
# Input budget: charge power available at the hardware ceiling before firmware raises it, and the 0.5 A target.
P_SERVICE = 0.13                                  # W from SYS with ADC off (digital ~30 mA at 3.3 V via buck), estimate
EFF = 0.85
charge_at_ceiling = max(0.0, (5.0 * ilim_nom * EFF - P_SERVICE) / 8.4)
charger = {'ilim_ceiling_A': {'nominal': round(ilim_nom, 3), 'min': round(min(ilim_vals), 3), 'max': round(max(ilim_vals), 3)},
           'iindpm_accuracy_note': 'TI: IINDPM = 500 mA regulates at 415-500 mA (VBUS 9 V); regulation sits below the setting',
           'ts_window': ts, 'ts_shift_from_TI_network_C': round(ts_shift, 2),
           'sys_effective_uF_estimate': round(c_sys_eff * 1e6, 1), 'sys_needed_uF': {'average': round(need_avg * 1e6, 1), 'peak': round(need_peak * 1e6, 1)},
           'charge_current_at_hardware_ceiling_A': round(charge_at_ceiling, 3),
           'input_current_for_0p5A_charge_A': round((8.4 * 0.5 / EFF + P_SERVICE) / 5.0, 2),
           'ship_mode_pack_drain_uA_max': 16 + 1, 'ship_mode_note': 'BQ25798 IQ_BAT_OFF 16 uA max at BATP + CSD17571Q2 IDSS 1 uA max; dividers are behind Q400'}
result['charger'] = charger
OUT.write_text(json.dumps(result, indent=2))
m = result['C10_RSET_49k9_1k00']
rules = [(m['release_margin_mV'] >= 40, 'release margin >= 40 mV'), (m['below_adc_max_mV'] >= 40, 'rail max >= 40 mV below 5.25 V'),
         (m['assert_above_adc_min_mV'] > 0, 'analogue reset asserts above 4.75 V'), (m['sys_inhibit_above_dropout_mV'] > 0, 'SYS inhibit above LDO dropout'),
         (edge(4.7e3, 30e-12) <= 200, '4.7k pull-up with 30 pF meets AUP 200 ns/V'),
         (max(ilim_vals) <= 0.5, 'charger hardware input ceiling <= 500 mA at all REGN/resistor corners'),
         (min(ilim_vals) >= 0.2, 'charger hardware input ceiling >= 200 mA (USB-only start-up)'),
         (ts_shift <= 1.0, 'E96 TS network within 1 C of the TI 103AT window'),
         (c_sys_eff >= 3 * need_avg, 'SYS hold-up >= 3x the average-load requirement')]
for ok, msg in rules:
    print(('PASS ' if ok else 'FAIL ') + msg)
print('C9', result['C9_RSET_50k5_383R']); print('C10', m)
sys.exit(0 if all(ok for ok, _ in rules) else 1)
