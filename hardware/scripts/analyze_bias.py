"""BIAS (common-mode feedback) loop: linear small-signal stability and DC/fault estimates.

NOT a substitute for bench measurement with an electrode simulator, and NOT a participant-safety
assessment. All electrode, cable and body-coupling values are assumed sweep parameters.

Model (per ADS1299 SBAS499C section 9.3.2.4.5 and Equation 11):
  BIASOUT --Rs (2 x 499k)-- node K (BIAS lead capacitance Ck to GND) --Zeb-- body B
  body B: capacitance Cbg to circuit GND (all body-to-board/battery paths); mains current id injected here
  each input leg: B --Ze-- node C (lead capacitance Cc) --94k-- node T (TVS 1.5 pF) --4.7k-- node A (ADC pin Ca)
  PGA common-mode gain 1; each sensed PGA output feeds BIASINV through Rint (330k text / 220k figure)
  bias amp: inverting stage, Zf = Rf || (Rz + 1/sCf), open loop A(s) = A0 / (1 + s A0 / wGBW)
Loop broken at the low-impedance PGA outputs driving Rint, so the return ratio is exact for this model:
  L(s) = G_inner(s) * H_out(s) * H_leg(s)
"""
from pathlib import Path
import itertools, json, math
import numpy as np

P = Path(__file__).resolve().parent
OUT = P.parent / 'checks' / 'bias_analysis.json'

GBW = 100e3        # Hz, datasheet typical, gain 1, 50k||10p load
A0 = 10 ** (100 / 20)  # assumed DC open-loop gain (not specified); margins insensitive above ~80 dB
R_SERIES = 998e3   # RB1 + RB2
R_LEG, R_POST = 94e3, 4.7e3
C_TVS, C_ADC = 1.5e-12, 20e-12   # TVS typical; ADC pin capacitance is a modelling assumption
LEGS = 16          # electrode legs on the body in an all-bipolar montage

def par(*z): return 1 / sum(1 / x for x in z)

def leg(s, ze, cc):
    """Input admittance seen from the body into one leg, and V_adc / V_body."""
    za = 1 / (s * C_ADC)
    zt = par(1 / (s * C_TVS), R_POST + za)
    zc = par(1 / (s * cc), R_LEG + zt) if cc else R_LEG + zt
    zin = ze + zc
    h = (zc / zin) * (zt / (R_LEG + zt)) * (za / (R_POST + za))
    return 1 / zin, h

def loop(f, rf=1e6, cf=10e-9, rz=100e3, rint=330e3, n=16, ze=100e3, zeb=100e3, ck=50e-12, cc=50e-12, cbg=47e-12):
    s = 2j * np.pi * np.asarray(f, float)
    zf = par(rf, rz + 1 / (s * cf))
    zin = rint / n
    a = A0 / (1 + s * A0 / (2 * np.pi * GBW))
    g_inner = (zf / zin) / (1 + (1 + zf / zin) / a)
    y_leg, h_leg = leg(s, ze, cc)
    y_body = s * cbg + LEGS * y_leg               # body load to GND, excluding the BIAS path
    z_b = 1 / y_body
    # V_body / V_out through Rs, node K (BIAS lead capacitance) and Zeb
    zkb = par(1 / (s * ck), zeb + z_b) if ck else zeb + z_b
    h_out = (zkb / (R_SERIES + zkb)) * (z_b / (zeb + z_b))
    return g_inner * h_out * h_leg

def margins(**kw):
    f = np.logspace(-1, 6, 6000)
    L = loop(f, **kw)
    mag, ph = np.abs(L), np.unwrap(np.angle(L))
    i = np.where((mag[:-1] >= 1) & (mag[1:] < 1))[0]
    if not len(i): return None
    k = i[0]
    fc = float(np.interp(0, [-math.log10(mag[k]), -math.log10(mag[k + 1])], [f[k], f[k + 1]]))
    pm = float(180 + np.degrees(np.interp(fc, f, ph)))
    j = np.where((ph[:-1] > -np.pi) & (ph[1:] <= -np.pi))[0]
    gm = float(-20 * math.log10(np.interp(f[j[0]], f, mag))) if len(j) else None
    peak = float(20 * math.log10(np.max(np.abs(1 / (1 + L)))))
    att50 = float(20 * math.log10(abs(1 + loop(50.0, **kw))))
    return {'dc_loop_gain': round(float(abs(loop(0.01, **kw))), 2), 'crossover_Hz': round(fc, 1),
            'phase_margin_deg': round(pm, 1), 'gain_margin_dB': None if gm is None else round(gm, 1),
            'closed_loop_peaking_dB': round(peak, 2), 'mains_cm_attenuation_50Hz_dB': round(att50, 1)}

def sweep(cf, rz):
    rows = []
    for rint, n, z, ck, cc, cbg in itertools.product([220e3, 330e3], [8, 16], [10e3, 100e3, 1e6],
                                                    [0, 50e-12, 200e-12], [0, 50e-12, 200e-12],
                                                    [10e-12, 47e-12, 220e-12]):
        m = margins(cf=cf, rz=rz, rint=rint, n=n, ze=z, zeb=z, ck=ck, cc=cc, cbg=cbg)
        rows.append({'rint_k': rint / 1e3, 'n_sensed': n, 'electrode_ohm': z, 'bias_lead_pF': ck * 1e12,
                     'input_lead_pF': cc * 1e12, 'body_to_gnd_pF': cbg * 1e12, **(m or {'unstable_or_no_crossover': True})})
    pms = [r['phase_margin_deg'] for r in rows if 'phase_margin_deg' in r]
    worst = min((r for r in rows if 'phase_margin_deg' in r), key=lambda r: r['phase_margin_deg'])
    return {'cf_nF': cf * 1e9, 'rz_kohm': rz / 1e3, 'cases': len(rows), 'min_phase_margin_deg': min(pms),
            'cases_below_45deg': sum(p < 45 for p in pms), 'cases_below_30deg': sum(p < 30 for p in pms),
            'worst_case': worst,
            'mains_attenuation_range_dB': [min(r['mains_cm_attenuation_50Hz_dB'] for r in rows),
                                           max(r['mains_cm_attenuation_50Hz_dB'] for r in rows)]}, rows

if __name__ == '__main__':
    nominal = dict(rint=330e3, n=16, ze=100e3, zeb=100e3, ck=50e-12, cc=50e-12, cbg=47e-12)
    # Rev C4 network (TI example values) versus the Step 8 selection; plus the Cf-only alternatives.
    networks = {'C4_TI_example_1M_par_1n5': (1.5e-9, 0), 'Cf_only_10n': (10e-9, 0), 'Cf_only_22n': (22e-9, 0),
                'C5_selected_1M_par_100k_plus_10n': (10e-9, 100e3), 'alt_1M_par_100k_plus_15n': (15e-9, 100e3),
                'alt_1M_par_100k_plus_22n': (22e-9, 100e3)}
    candidates = {}
    for name, (cf, rz) in networks.items():
        summary, _ = sweep(cf, rz)
        summary['nominal'] = margins(cf=cf, rz=rz, **nominal)
        candidates[name] = summary
    # DC and fault estimates (AVDD upper calculated corner 5.163 V, resistors -0.1 %)
    avdd, tol = 5.163, 0.999
    leak = LEGS * 10e-9  # TPD2E2U06 10 nA max at 2.5 V per leg, applied at body mid-supply
    dc = {
        'bias_series_ohm': R_SERIES,
        'max_dc_current_normal_uA': round(avdd / (R_SERIES * tol) * 1e6, 2),
        'max_dc_current_one_resistor_shorted_uA': round(avdd / (R_SERIES / 2 * tol) * 1e6, 2),
        'both_resistors_shorted': 'limited only by BIASOUT short-circuit current, 1.1 mA typical, not guaranteed',
        'tvs_leakage_total_nA': leak * 1e9,
        'tvs_leakage_drop_across_series_V': round(leak * R_SERIES, 3),
        'body_cm_error_from_leakage_mV_n16': round(leak * R_SERIES / (1 + 1e6 * 16 / 330e3) * 1e3, 2),
        'mains_displacement_current_uA_2pF_230V': round(230 * 2 * math.pi * 50 * 2e-12 * 1e6, 3),
        'bias_swing_for_that_current_1Mohm_electrode_Vpk': round(230 * 2 * math.pi * 50 * 2e-12 * math.sqrt(2) * (R_SERIES + 1e6), 3),
    }
    out = {'note': __doc__.strip().split('\n')[0], 'assumptions': {'GBW_Hz': GBW, 'A0_dB': 100, 'C_ADC_pF': 20,
           'C_TVS_pF': 1.5, 'legs': LEGS, 'nominal_case': {k: v for k, v in nominal.items()}},
           'feedback_capacitor_candidates': candidates, 'dc_and_fault': dc}
    OUT.write_text(json.dumps(out, indent=2))
    for k, v in candidates.items():
        print(k, 'minPM', round(v['min_phase_margin_deg'], 1), '<45:', v['cases_below_45deg'], '<30:', v['cases_below_30deg'],
              'of', v['cases'], 'att50', v['mains_attenuation_range_dB'], 'nominal', v['nominal'])
    print('selected worst case:', json.dumps(candidates['C5_selected_1M_par_100k_plus_10n']['worst_case']))
    print(json.dumps(dc, indent=1))
