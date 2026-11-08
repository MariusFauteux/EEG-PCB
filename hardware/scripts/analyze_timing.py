"""Step 9 timing budget: ADC clock choice, event-capture latency, trigger and photodiode front ends.

Datasheet-derived estimates, NOT measurements. Requirements T1-T3 are proposed design targets for visual ERP
work and must be confirmed against the experimental protocol.
"""
from pathlib import Path
import json, math

OUT = Path(__file__).resolve().parents[1] / 'checks' / 'timing_analysis.json'
FS = 1000.0                       # nominal sample rate, Hz
T = 1 / FS

# Proposed requirements (board-attributable timing only; display latency is measured by the photodiode).
REQ = {
    'T1_event_to_sample_alignment_us': 100,      # 10 % of a sample period
    'T2_epoch_timing_error_us_over_1s': 100,      # sample-interval knowledge within an ERP epoch
    'T3_session_drift_s_per_24h_without_external_sync': 10,  # local annotation only; triggers carry precise sync
}

def clock_case(name, ppm):
    return {
        'name': name, 'frequency_error_ppm': ppm,
        'epoch_1s_error_us': round(ppm * 1e-6 * 1.0 * 1e6, 1),
        'drift_per_24h_s': round(ppm * 1e-6 * 86400, 2),
        'meets_T2_uncorrected': ppm * 1.0 <= REQ['T2_epoch_timing_error_us_over_1s'],
        'meets_T3_uncorrected': ppm * 1e-6 * 86400 <= REQ['T3_session_drift_s_per_24h_without_external_sync'],
    }

clocks = [
    clock_case('ADS1299 internal oscillator, 25 degC (SBAS499C 7.5)', 5000),
    clock_case('ADS1299 internal oscillator, -40..85 degC (SBAS499C 7.5)', 25000),
    clock_case('SiT8008 +/-20 ppm incl. tolerance, 1st-year ageing, temperature', 20),
    clock_case('nRF52840 HFXO timebase, assumed +/-50 ppm (BLE carrier requirement; module figure not stated)', 50),
]

# Event latency chain (systematic part can be calibrated; jitter part cannot).
TICK = 1 / 16e6
chain = {
    'timer_resolution_ns': TICK * 1e9,
    'trigger_optocoupler_tpHL_typ_max_ns': [49, 80],          # TLP2761, IF 0->2 mA
    'trigger_pulse_width_distortion_max_ns': 25,
    'photodiode_tia_bandwidth_kHz': None,                     # filled below
    'photodiode_comparator_delay_ns': 260,                    # TLV7011 typical
    'gpiote_ppi_capture': 'deterministic, same path for DRDY and events; latency to be measured on hardware',
    'adc_group_delay_ms_estimate': 1.5 * T * 1e3,             # sinc3, 3 x tDR settling (SBAS499C 9.3.2.1.3): centre at 1.5 tDR
}

# Trigger input: series resistor + TLP2761 LED; recommended IF(ON) 2-6 mA, abs max 10 mA, VF 1.35-1.65 V @2 mA.
R_TRIG = 620.0
trig = {}
for v in [3.0, 3.3, 5.0, 5.5]:
    trig[f'{v} V source'] = {'IF_min_mA': round((v - 1.65) / R_TRIG * 1e3, 2),
                             'IF_max_mA': round((v - 1.35) / R_TRIG * 1e3, 2)}
trigger = {'series_ohm': R_TRIG, 'led_current': trig,
           'note': '3.0-5.0 V logic stays within IF(ON) 2-6 mA (5.0 V max 5.9 mA); 5.5 V reaches 6.7 mA, above the '
                   'recommended range but below the 10 mA absolute maximum. Threshold IFHL <= 1.6 mA max.'}

# Photodiode TIA: BPW34 70 pF at 0 V; assumed cable 100 pF; TLV9061 GBW 10 MHz.
RF, CF, GBW = 33e3, 15e-12, 10e6
CIN = 70e-12 + 100e-12 + 1.5e-12
cf_min = math.sqrt(CIN / (2 * math.pi * RF * GBW))
bw = 1 / (2 * math.pi * RF * CF)
chain['photodiode_tia_bandwidth_kHz'] = round(bw / 1e3, 1)
# Light estimate: Lambertian screen luminance L gives E = pi*L at contact; BPW34 Ik 70 uA at 1 klx (illuminant A).
photo = {}
for L in [50, 100, 200, 350]:
    E = math.pi * L
    for spectral_factor in [0.3, 1.0]:
        i = 70e-6 * E / 1000 * spectral_factor
        photo[f'{L} cd/m2, spectral factor {spectral_factor}'] = {
            'photocurrent_uA': round(i * 1e6, 1), 'tia_out_V': round(0.05 + i * RF, 2)}
tia = {'rf_ohm': RF, 'cf_pF': CF * 1e12, 'input_capacitance_pF_assumed': CIN * 1e12,
       'cf_min_for_stability_pF': round(cf_min * 1e12, 1), 'bandwidth_kHz': round(bw / 1e3, 1),
       'output_swing_limit_V': 3.3, 'light_estimates': photo,
       'note': 'Spectral factor accounts for LCD white having less near-IR than illuminant A; both bounds assumed.'}
comp = {'hysteresis_resistors': '10k input, 1M feedback', 'hysteresis_mV': round(3.3 * 10e3 / 1e6 * 1e3, 1),
        'internal_hysteresis_mV_min_typ_max': [1.2, 4.2, 14]}

def budget(clock_ppm, corrected):
    """Board timing error for an event 1 s after epoch start, us. corrected = per-session rate from DRDY timestamps."""
    rate_err = (50 if corrected else clock_ppm) * 1e-6 * 1.0 * 1e6
    capture = TICK * 1e6 + 0.08 + 0.025  # one tick + opto delay spread + PWD, us
    return round(rate_err + capture, 2)

decision = {
    'internal_uncorrected_us': budget(25000, False),
    'internal_corrected_by_mcu_crystal_us': budget(25000, True),
    'external_sit8008_uncorrected_us': budget(20, False),
    'requirement_T1_T2_us': REQ['T2_epoch_timing_error_us_over_1s'],
    'conclusion': 'Internal oscillator fails T2 by 50-250x unless every analysis applies a measured per-session '
                  'rate. The SiT8008 meets T2 and T3 without correction; DRDY timestamps are kept to verify it.',
}

out = {'note': __doc__.strip().split('\n')[0], 'requirements_proposed': REQ, 'clocks': clocks,
       'latency_chain': chain, 'trigger_input': trigger, 'photodiode_tia': tia, 'comparator': comp,
       'clock_decision': decision}
OUT.write_text(json.dumps(out, indent=2))
print(json.dumps({'clocks': clocks, 'decision': decision, 'tia_cf_min_pF': tia['cf_min_for_stability_pF'],
                  'tia_bw_kHz': tia['bandwidth_kHz'], 'trigger': trig}, indent=1))
