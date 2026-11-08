"""Step 14 VBUS overvoltage protection: clamp level, transient, downstream pin limits, inrush, on-resistance loss,
reverse current and the module VBUS pad. Datasheet-derived estimates, NOT measurements.
Writes checks/ovp_analysis.json; exits non-zero if a design rule fails.

Sources read for Step 14 (2026-11-08):
  TI SLVSCF6F TPD1S514x (May 2019): VOVP 5.90/5.95/5.99 V (TPD1S514-1, 25 C), tOVP_response 100 ns, VBUS_CON 30 V abs,
    VBUS_SYS 20 V abs, CLOAD 0.1-100 uF abs, RON 39/50 mOhm (25 C, 1 A), RthetaJA 89 C/W, TSHDN 145 C, tDELAY 20 ms,
    tSS 3.5 ms (typ only), VBUS_POWER 4.7-4.95 V at 5 V in and <= 5.5 V at 20 V in, 3 mA max, IDIODE 1 A.
  TI SBVS338H TPS7A20 (July 2024): VIN 6.0 V rec. / 6.5 V abs, VOUT +/-1.5 % (DBV), dropout <= 145 mV at 300 mA,
    COUT >= 0.47 uF effective, reverse current <= 5 % of 300 mA briefly.
  Nordic nRF52840 PS (docs.nordicsemi.com): VBUS 4.35-5.5 V operating, 5.8 V absolute; USB regulator 170 uA;
    max VBUS source resistance 6 ohm; VBUS detect 3.4-4.3 V rising.
  TI SLLSEN9F TUSB320: system VBUS 4-28 V recommended, VBUS_DET 4 V abs, RVBUS 855-920 k, internal pull-down 95 k typ.
  TI SLUSDV2C BQ25798: VBUS and VAC 30 V abs, VBUS operating 3.6-24 V, PMID-VBUS 6 V abs; no SYS-to-VBUS path unless OTG.
  TI SLLSEG9C TPD2E2U06 (VRWM 5.5 V, VBR 6.5 V min) and SN74LVC1G14 (VI 6.5 V abs), as recorded in Step 13.
Assumptions are marked ASSUMPTION in the output.
"""
from pathlib import Path
import json, sys

OUT = Path(__file__).resolve().parents[1] / 'checks' / 'ovp_analysis.json'
rules, notes = [], {}
def rule(ok, msg): rules.append((bool(ok), msg))

# 1. Steady clamp. TI specifies VOVP at 25 C only; +1 % is allowed for temperature (ASSUMPTION; Figure 3 not tabulated).
VOVP = (5.90, 5.95, 5.99); VOVP_HOT = VOVP[2] * 1.01
# 2. Transient during the 100 ns response: a step to 30 V through source and cable inductance L charges USB_5V.
#    ASSUMPTION: L >= 100 nH (a short USB-C cable alone is several hundred nH). Q = dV t^2 / (2 L).
L_MIN, T_RESP, V_FAULT = 100e-9, 100e-9, 30.0
q = (V_FAULT - VOVP_HOT) * T_RESP ** 2 / (2 * L_MIN)
# Effective capacitance on USB_5V alone (PMID ignored, worst case): C400 + C401 10 uF 1206 at 6 V (Murata -30 %,
# extrapolated from -27.3 % at 5.5 V), C321 + C326 1 uF 0805 (-3.5 %), C402 100 nF; -10 % tolerance, -15 % temperature.
c_usb5v = (2 * 10e-6 * 0.70 + 2 * 1e-6 * 0.965 + 0.1e-6) * 0.9 * 0.85
dv = q / c_usb5v
V_PEAK = VOVP_HOT + dv
notes['clamp'] = dict(vovp_25C_V=VOVP, vovp_with_temperature_allowance_V=round(VOVP_HOT, 3), response_ns=100,
                      step_charge_uC=round(q * 1e6, 3), c_usb5v_worst_uF=round(c_usb5v * 1e6, 2), overshoot_mV=round(dv * 1e3, 1),
                      usb5v_peak_V=round(V_PEAK, 3), assumption='L >= 100 nH, VOVP +1 % over temperature',
                      surge='TI: VBUS_SYS held below VOVP during IEC 61000-4-5 surges up to 100 V open circuit')

# 3. Downstream limits. (node, worst voltage, limit, source)
div = lambda v, rt, rb: v * rb / (rt + rb)
VPWR_MAX = 5.5                                     # U323 VBUS_POWER clamp at 20-30 V in
RVBUS_LO, RPD_HI = 887e3 * 0.99, 95e3 * 1.2        # ASSUMPTION: TUSB320 internal pull-down +/-20 % (typ only given)
limits = [
    ('BQ25798 VBUS/VAC1/VAC2 (USB_5V peak)', V_PEAK, 30.0, 'SLUSDV2C abs max'),
    ('BQ25798 VBUS operating range', V_PEAK, 24.0, 'SLUSDV2C VVBUS_OP max'),
    ('D312 TPD2E2U06 on USB_5V: below breakdown', V_PEAK, 6.5, 'TPD2E2U06 VBR min'),
    ('U324 TPS7A2050 VIN', V_PEAK, 6.5, 'SBVS338H abs max'),
    ('U324 TPS7A2050 VIN steady (25 C OVP ceiling)', VOVP[2], 6.0, 'SBVS338H recommended max'),
    ('Module pad 31 (MCU_VBUS = 5.0 V +1.5 %)', 5.0 * 1.015, 5.5, 'nRF52840 VBUS recommended max'),
    ('U321 input from USB_VPWR (10k/100k, 1 %)', VPWR_MAX * 101e3 / (9.9e3 + 101e3), 5.5, 'SN74LVC1G14 VI recommended max (Step 13)'),
    ('TUSB320 VBUS_DET at 30 V on VBUS_CON', div(30.0, RVBUS_LO, RPD_HI), 4.0, 'SLLSEN9F abs max'),
    ('VBUS_CON at the U323 rating', 30.0, 30.0, 'SLVSCF6F VBUS_CON abs max (C324 50 V)'),
]
notes['pins'] = [dict(node=n, volts=round(v, 3), limit=l, source=s, margin_mV=round((l - v) * 1e3)) for n, v, l, s in limits]
for n, v, l, s in limits:
    rule(v <= l, f'{n}: {v:.3f} V <= {l} V ({s})')
notes['d312_note'] = 'Between 5.5 V (VRWM) and the OVP ceiling D312 only sees a non-compliant source; leakage rises but it does not conduct.'
# Module pad 31 low end: Type-C vSafe5V minimum 4.75 V at the receptacle (ASSUMPTION: USB Type-C specification, not
# re-read), less U323 drop at 1.01 A and 75 mOhm, less TPS7A20 dropout at a few mA (~ 145 mV x 5/300).
v_pad_min = 4.75 - 1.01 * 0.075 - 0.145 * 5 / 300
rule(v_pad_min >= 4.35, f'Module pad 31 at a 4.75 V source: {v_pad_min:.3f} V >= 4.35 V (nRF52840 VBUS minimum)')
rule(4.3 <= 4.75 - 1.01 * 0.075, 'Module VBUS detect (4.3 V max) reached at the minimum source voltage')

# 4. Inrush. U323 starts with tDELAY 20 ms, then soft start tSS 3.5 ms (10-90 %) after plug-in (a UVLO event).
C_BEHIND = dict(C400=10e-6, C401=10e-6, C321=1e-6, C326=1e-6, C402=0.1e-6, C403=10e-6, C404=10e-6, C405=10e-6, C406=0.1e-6)
c_behind = sum(C_BEHIND.values()) * 1.1           # nominal +10 % tolerance, no DC-bias derating (worst for inrush)
TSS = 3.5e-3
i_inrush = c_behind * 0.8 * 5.25 / TSS
c_conn = 1e-6 * 1.1                                # C324 only, +10 %
notes['inrush'] = dict(c_behind_switch_uF=round(c_behind * 1e6, 1), soft_start_ms=3.5, inrush_mA=round(i_inrush * 1e3, 1),
                       connector_side_uF=round(c_conn * 1e6, 2), attach_charge_uC=round(c_conn * 5.5 * 1e6, 2),
                       inrush_if_tss_1ms_mA=round(c_behind * 0.8 * 5.25 / 1e-3 * 1e3),
                       note='TI gives tSS as typical only; a 1 ms soft start would still stay below 300 mA for ~1 ms')
rule(c_conn <= 10e-6, f'Connector-side VBUS capacitance {c_conn * 1e6:.2f} uF <= 10 uF (USB Type-C sink bulk limit)')
rule(c_behind <= 100e-6, f'Capacitance behind U323 {c_behind * 1e6:.1f} uF <= 100 uF (TPD1S514 CLOAD abs max)')
rule(i_inrush <= 0.1, f'Soft-start inrush {i_inrush * 1e3:.0f} mA <= 100 mA (one USB 2.0 unit load; ASSUMPTION: limit from the USB 2.0 spec)')

# 5. On-resistance. RON 50 mOhm max at 25 C; ASSUMPTION x1.5 at hot junction (75 mOhm). RthetaJA 89 C/W (JEDEC board).
RON_HOT, RTHJA = 0.075, 89.0
cases = {'hardware ceiling 0.44 A': 0.44, '0.5 A charge at 8.4 V (input 1.01 A, Step 11)': 1.01, 'Type-C 1.5 A advertisement': 1.5, 'Type-C 3.0 A advertisement': 3.0}
notes['ron'] = {k: dict(I_A=i, drop_mV=round(i * RON_HOT * 1e3, 1), loss_mW=round(i * i * RON_HOT * 1e3, 1), rise_C=round(i * i * RON_HOT * RTHJA, 1)) for k, i in cases.items()}
rule(notes['ron']['0.5 A charge at 8.4 V (input 1.01 A, Step 11)']['rise_C'] <= 10, 'U323 junction rise at the 0.5 A charge design point <= 10 C')
rule(60 + notes['ron']['Type-C 3.0 A advertisement']['rise_C'] < 125, 'U323 at 3 A and 60 C ambient stays below 125 C (TSHDN 145 C)')
rule(1.01 * RON_HOT <= 0.1, 'U323 drop at the 1.01 A design input current <= 100 mV')

# 6. Reverse current and the module VBUS pad.
I_DISCHARGE = 1.1e-6 * 15e3                         # C303 + C327 following USB_5V at up to 15 V/ms (ASSUMPTION)
notes['reverse'] = dict(
    tpd1s514='Bidirectional nFET; body diode conducts VBUS_SYS to VBUS_CON (<= 1 A) only if USB_5V exceeds the connector, '
             'i.e. only in BQ25798 OTG mode. Firmware keeps EN_OTG = 0 (reset default). With USB absent nothing drives USB_5V: '
             'the BQ25798 has no SYS-to-VBUS path while not in OTG.',
    tps7a20_out_to_in_mA=round(I_DISCHARGE * 1e3, 1), tps7a20_limit_mA=15.0,
    d324='BAT54 MCU_VBUS -> USB_5V conducts this discharge at ~0.3 V, below the LDO body path.',
    vbus_power='USB_VPWR is an internal LDO output; with USB absent it is unpowered and the divider holds U321 low (USB_ABSENT high).')
notes['module_pad31'] = dict(volts=[round(v_pad_min, 3), round(5.0 * 1.015, 3)], source_resistance_ohm='< 1 (LDO output) vs 6 ohm allowed',
                             detect='USBDETECTED after U323 delay + soft start (~24 ms) and U324 start-up; VBUS detect 3.4-4.3 V')

OUT.write_text(json.dumps(dict(rules=[dict(ok=o, rule=m) for o, m in rules], **notes), indent=1))
for ok, m in rules:
    print(('PASS ' if ok else 'FAIL ') + m)
sys.exit(0 if all(ok for ok, _ in rules) else 1)
