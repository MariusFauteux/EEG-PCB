"""Step 13 corner and transient review of the whole netlist. Run via hardware/rebuild.sh.

Automated: floating inputs, single-node nets, supply decoupling at every IC, capacitor voltage rating against the
highest voltage on its net, DC-bias effective capacitance where a requirement exists, I2C addresses and pull-ups,
pin voltages at the SYS and VBUS corners, and steady-state dissipation of regulators, charger and resistors.
Datasheet-derived estimates, NOT measurements. Writes checks/corner_review.json; exits non-zero if a rule fails.
Findings that are recorded as open (not rules) are printed as OPEN.

Sources (read for Step 13): TI SLUSDV2C (BQ25798: VAC_OVP 26 V default, RthetaJA 44.2 C/W, CBAT >= 3 uF effective),
TI SLLSEG9C (TPD2E2U06: VRWM 5.5 V, VBR 6.5-8.5 V), TI SCES... SN74LVC1G14 (VI abs max 6.5 V), TI SLVSD65A
(TPS3890: SENSE/VDD abs max 7 V, SENSE recommended <= 5.5 V), TI SLVSAM3 TPS62162 (VIN abs max 20 V),
TI SLLSEN9F (TUSB320: VBUS_DET abs max 4 V, SDA/SCL abs max VDD + 0.3 V), u-blox UBX-17052099 R15 Table 10
(VCC abs max 3.9 V; no VBUS limit given), Murata pim.murata.com DC-bias curves (25 C, read 2026-11-08).
"""
from pathlib import Path
import xml.etree.ElementTree as ET
import json, re, sys, collections

HW = Path(__file__).resolve().parents[1]; CHECKS = HW / 'checks'
root = ET.parse(CHECKS / 'netlist.xml').getroot()
comp = {c.get('ref'): c for c in root.findall('.//components/comp')}
field = lambda r, n: comp[r].findtext(f'fields/field[@name="{n}"]') or ''
offboard = {r for r, c in comp.items() if any(p.get('name') == 'exclude_from_board' for p in c.findall('property'))}
nets = collections.defaultdict(list); pinnet = {}
for n in root.findall('.//nets/net'):
    name = n.get('name').split('/')[-1]
    for x in n.findall('node'):
        nets[name].append((x.get('ref'), x.get('pin'), x.get('pintype') or '', x.get('pinfunction') or ''))
        pinnet[(x.get('ref'), x.get('pin'))] = name
rules, opens, info = [], [], {}
def rule(ok, msg): rules.append((bool(ok), msg))

# 1. Floating inputs: every input pin must share its net with something that can set its level.
DRIVERS = {'output', 'bidirectional', 'tri_state', 'power_out', 'open_collector', 'passive', 'power_in', 'open_emitter'}
floating = []
for name, nodes in nets.items():
    kinds = {t.split('+')[0] for _, _, t, _ in nodes}
    if any(t.startswith('input') for _, _, t, _ in nodes) and (name.startswith('unconnected-') or not (kinds - {'input', 'no_connect'})):
        floating.append(name)
rule(not floating, f'No floating input pins ({len(floating)} found: {floating})')
# Nets with one node that are not deliberate no-connects: stubs that reach nothing.
stubs = sorted(n for n, v in nets.items() if len(v) == 1 and not n.startswith('unconnected-'))
info['single_node_nets'] = stubs
# Nets that only a pull-up and an open-drain output share: an output nobody reads.
unread = []
for name, nodes in nets.items():
    refs = {r for r, _, _, _ in nodes}
    if len(nodes) == 2 and any(t == 'open_collector' for _, _, t, _ in nodes) and any(r.startswith('R') for r in refs):
        unread.append(name)
info['open_drain_outputs_without_reader'] = unread

# 2. Decoupling: each IC supply pin (power_in, not ground) has a capacitor to GND on the same net.
caps_on = collections.defaultdict(set)
for r in comp:
    if r.startswith('C') and r not in offboard:
        a, b = pinnet.get((r, '1')), pinnet.get((r, '2'))
        if b == 'GND': caps_on[a].add(r)
        if a == 'GND': caps_on[b].add(r)
undecoupled = []
for name, nodes in nets.items():
    if name == 'GND' or name.startswith('unconnected-'):
        continue
    for r, p, t, f in nodes:
        if r[0] in 'UY' and t == 'power_in' and not caps_on[name]:
            undecoupled.append(f'{r}.{p} {f} on {name}')
rule(not undecoupled, f'Every IC supply pin has a capacitor to GND on its net ({undecoupled})')

# 3. Capacitor voltage ratings against the highest steady voltage on the capacitor's nets.
VMAX = {'SYS': 8.6, 'PACK_POS': 8.4, 'PACK_IN': 8.4, 'CHG_PMID': 6.2, 'USB_5V': 6.2, 'VBUS_CON': 30.0, 'USB_VPWR': 5.5, 'MCU_VBUS': 5.1,  # Step 14: OVP ceiling + transient (analyze_ovp.py)
        'REGN': 5.2, 'CHG_SDRV': 13.6,
        '+5VA': 5.25, '+3V3': 3.6, '+3V3_ADC': 3.6}
SPECIAL = {'C407': 5.2, 'C408': 5.2}            # bootstrap capacitors see REGN across them
def vmax(net):
    return VMAX.get(net, 5.25)                  # every other net is derived from +5VA, +3V3 or REGN
caps = []
for r in sorted(comp):
    if not r.startswith('C') or r in offboard:
        continue
    m = re.search(r'(\d+(?:\.\d+)?) V', field(r, 'Description'))
    rated = float(m[1]) if m else None
    v = SPECIAL.get(r, max(vmax(pinnet.get((r, '1'), '')), vmax(pinnet.get((r, '2'), '')) if pinnet.get((r, '1')) != 'GND' and pinnet.get((r, '2')) != 'GND' else 0))
    if pinnet.get((r, '1')) == 'GND': v = vmax(pinnet.get((r, '2')))
    elif pinnet.get((r, '2')) == 'GND': v = vmax(pinnet.get((r, '1')))
    caps.append(dict(ref=r, mpn=field(r, 'MPN'), rated_V=rated, v_max=v, ratio=round(rated / v, 2) if rated else None))
low = [c for c in caps if not c['rated_V'] or c['rated_V'] < 1.5 * c['v_max']]
rule(not [c for c in caps if not c['rated_V'] or c['rated_V'] < c['v_max']], 'Every capacitor rated above the highest voltage on its net')
info['capacitors_below_1p5x_rating'] = [(c['ref'], c['mpn'], c['rated_V'], c['v_max']) for c in low]

# 4. DC-bias effective capacitance (Murata 25 C curves, % change; read 2026-11-08) with -10 % tolerance and
# -15 % X7R temperature allowance applied to the requirement checks.
DCB = {'GRM31CR71E106KA12L': [(0, 0), (3.3, -7.2), (5.1, -23.7), (5.5, -27.3), (8.4, -49.6)],
       'GRM32ER71E226KE15L': [(0, 0), (3.3, -6.2), (5.1, -21.5), (8.4, -46.7)],
       'GRM21BR71C475KE51L': [(0, 0), (3.3, -16.1), (5.0, -31.9), (5.1, -32.8)],
       'GCM21BR71E105KA56L': [(0, 0), (3.3, -0.7), (5.1, -2.9), (5.5, -3.5)]}
NOM = {'GRM31CR71E106KA12L': 10, 'GRM32ER71E226KE15L': 22, 'GRM21BR71C475KE51L': 4.7, 'GCM21BR71E105KA56L': 1.0}
def eff(mpn, v, worst=False):
    pts = DCB[mpn]
    for (v0, c0), (v1, c1) in zip(pts, pts[1:]):
        if v0 <= v <= v1:
            k = c0 + (c1 - c0) * (v - v0) / (v1 - v0); break
    else:
        k = pts[-1][1]
    return NOM[mpn] * (1 + k / 100) * ((0.9 * 0.85) if worst else 1)
def bank(refs, v, worst=False): return round(sum(eff(field(r, 'MPN'), v, worst) for r in refs), 2)
dcb = {
    'C203+C204 at 5.25 V (LT3045 needs >= 10 uF effective)': (bank(['C203', 'C204'], 5.25), bank(['C203', 'C204'], 5.25, True), 10.0, '>='),
    'C121 at 4.5 V (ADS1299 VCAP1 >= 10 uF effective, Step 1)': (bank(['C121'], 4.5), bank(['C121'], 4.5, True), 10.0, '>='),
    'SYS ceramics C410-C414 at 8.4 V': (bank([f'C{n}' for n in range(410, 415)], 8.4), bank([f'C{n}' for n in range(410, 415)], 8.4, True), None, ''),
    'BAT C417+C418 at 8.4 V (TI CBAT >= 3 uF effective)': (bank(['C417', 'C418'], 8.4), bank(['C417', 'C418'], 8.4, True), 3.0, '>='),
    'C201 CSET at 5.09 V': (bank(['C201'], 5.09), bank(['C201'], 5.09, True), None, ''),
    'C409 REGN at 5.0 V': (bank(['C409'], 5.0), bank(['C409'], 5.0, True), None, ''),
}
for k, (typ, worst, lim, op) in dcb.items():
    if lim is not None:
        rule(worst >= lim if op == '>=' else typ * 1.1 <= lim, f'{k}: {typ} uF typical, {worst} uF worst case')
os_con = 0.8 * 100.0
sys_eff = bank([f'C{n}' for n in range(410, 415)], 8.4) + os_con
sys_worst = bank([f'C{n}' for n in range(410, 415)], 8.4, True) + os_con
info['sys_holdup_uF'] = dict(typical=round(sys_eff, 1), worst=round(sys_worst, 1), step11_estimate=124.0, peak_target=127.0, average_target=24.0)
rule(sys_worst >= 3 * 24.0, f'SYS hold-up {sys_worst:.0f} uF worst case >= 3 x the 24 uF average-load requirement')

# 5. I2C: addresses and pull-ups on the power bus.
I2C = {'U320': ('TUSB320LAI', 0x47, 'ADDR = GND'), 'U612': ('MCP4725A0', 0x60, 'A0 = GND'), 'U400': ('BQ25798', 0x6B, 'fixed')}
on_bus = {r for r, p, _, _ in nets['POWER_SDA'] if r[0] == 'U' and r != 'U300'}
rule(on_bus == set(I2C), f'I2C devices on POWER_SDA are {sorted(on_bus)}')
rule(len({a for _, a, _ in I2C.values()}) == len(I2C), 'No I2C address conflict (0x47, 0x60, 0x6B)')
pull = {}
for line in ('POWER_SDA', 'POWER_SCL'):
    rs = [r for r, p, _, _ in nets[line] if r.startswith('R')]
    other = [pinnet[(r, '1' if pinnet[(r, '2')] == line else '2')] for r in rs]
    rpar = 1 / sum(1 / 4.7e3 for _ in rs)
    pull[line] = dict(resistors=rs, to=other, R_ohm=round(rpar), sink_mA_at_0p4V=round((3.3 - 0.4) / rpar * 1e3, 2),
                      rise_ns_50pF=round(0.8473 * rpar * 50e-12 * 1e9), rise_ns_100pF=round(0.8473 * rpar * 100e-12 * 1e9))
    rule(len(rs) == 1 and other == ['+3V3'] and pull[line]['sink_mA_at_0p4V'] <= 3.0, f'{line}: one 4.7k pull-up to +3V3, {pull[line]["sink_mA_at_0p4V"]} mA at VOL 0.4 V (<= 3 mA)')
info['i2c'] = dict(devices={r: f'{n} 0x{a:02X} ({s})' for r, (n, a, s) in I2C.items()}, pullups=pull,
                   note='Rise time at 400 kHz needs <= 300 ns: met up to ~70 pF bus capacitance; run at 100 kHz otherwise.')

# 6. Pin voltages at the SYS (8.6 V) and VBUS corners.
div = lambda v, rt, rb: v * rb / (rt + rb)
pins = [
    ('SYS_OK SENSE at SYS 8.6 V (40.2k/10k)', div(8.6, 40.2e3, 10e3), 5.5, 'TPS3890 SENSE recommended max'),
    ('PACK_OK SENSE at 8.4 V (44.2k/10k)', div(8.4, 44.2e3, 10e3), 5.5, 'TPS3890 SENSE recommended max'),
    ('BAT_WARN SENSE at 8.4 V (47.5k/10k)', div(8.4, 47.5e3, 10e3), 5.5, 'TPS3890 SENSE recommended max'),
    ('TPS62162 VIN at SYS 8.6 V', 8.6, 17.0, 'TPS62162 VIN recommended max'),
    ('TPS62162 EN tied to VIN', 8.6, 8.6 + 0.3, 'TPS62162 EN abs max VIN + 0.3'),
    ('U321 input at USB_VPWR 5.5 V (10k/100k)', div(5.5, 10e3, 100e3), 5.5, 'SN74LVC1G14 VI recommended max'),
    ('TUSB320 SDA/SCL at +3V3', 3.6, 3.6 + 0.3, 'TUSB320 abs max VDD + 0.3'),
]
pv = [dict(node=n, volts=round(v, 2), limit=l, source=s, ok=v <= l) for n, v, l, s in pins]
for p in pv:
    rule(p['ok'], f"{p['node']}: {p['volts']} V <= {p['limit']} V ({p['source']})")
# Step 14 closes F01: U323 TPD1S514-1 limits USB_5V to the OVP ceiling (analyze_ovp.py has the transient and limits).
ovp = json.loads((CHECKS / 'ovp_analysis.json').read_text()) if (CHECKS / 'ovp_analysis.json').exists() else None
rule(ovp and all(r['ok'] for r in ovp['rules']), 'VBUS overvoltage protection rules pass (analyze_ovp.py, closes Step 13 F01)')
rule(pinnet.get(('R362', '1')) == 'USB_VPWR' and pinnet.get(('U300', '31')) == 'MCU_VBUS', 'USB-sense divider on USB_VPWR and module VBUS on MCU_VBUS, not on the connector or USB_5V')

# 7. Dissipation (steady state).
loads = {'+5VA load (ADS1299 + OPA376 + R205 bleeder + dividers), budget': 0.050}
p_ldo = (8.4 - 5.09) * 0.050
p_chg = 8.4 * 0.5 * (1 / 0.90 - 1)          # 0.5 A at 8.4 V, efficiency assumed 90 %
diss = {
    'LT3045 at SYS 8.4 V, 50 mA budget': dict(W=round(p_ldo, 3), rise_C=round(p_ldo * 34, 1), note='theta-JA 34 C/W assumed (ADI data sheet not re-read)'),
    'BQ25798 charging 0.5 A at 8.4 V': dict(W=round(p_chg, 3), rise_C=round(p_chg * 44.2, 1), note='efficiency 90 % assumed; RthetaJA 44.2 C/W (SLUSDV2C, JEDEC board)'),
    'TPS62162 at 480 mA peak, 85 %': dict(W=round(3.3 * 0.48 * (1 / 0.85 - 1), 3), note='peak only (SD write burst); average ~30 mA'),
    'Q400 ship FET at 0.5 A': dict(W=round(0.5 ** 2 * 0.029, 4), note='RDS(on) 29 mOhm max (Step 11)'),
    'R205 bleeder 4.7k at 5.25 V': dict(W=round(5.25 ** 2 / 4.7e3, 4), rating=0.1),
    'R600 620R, 5.0 V trigger, LED 1.15 V': dict(W=round((5.0 - 1.15) ** 2 / 620, 4), rating=0.25),
    'R407 2.2k charge LED from REGN': dict(W=round((5.2 - 2.0) ** 2 / 2.2e3, 4), rating=0.1),
    'R208 100R clamp drain at +5VA 5.25 V (only if Q201 conducts while the rail is held up)': dict(W=round(5.25 ** 2 / 100, 3), rating=0.25),
    '47k input resistor, 100 V between two electrodes (2 x 94k path)': dict(W=round((100 / 188e3) ** 2 * 47e3, 4), rating=0.25, volts=round(100 / 188e3 * 47e3, 1), lev=150),
    'RB1/RB2 499k, BIAS output at rail (5 V) into a grounded electrode': dict(W=round((5 / 998e3) ** 2 * 499e3, 7), rating=0.25),
}
for k, d in diss.items():
    if 'rating' in d and 'R208' not in k:
        rule(d['W'] <= 0.5 * d['rating'], f"{k}: {d['W']} W <= 50 % of {d['rating']} W")
rule(diss['47k input resistor, 100 V between two electrodes (2 x 94k path)']['volts'] <= 150, '47k input resistor sees <= 150 V element voltage at 100 V between electrodes')
opens.append(('F12', 'R208 (0.25 W) would dissipate 0.28 W if Q201 conducted while the LT3045 held +5VA up. Q202 and the LT3045 share ANA_ENABLE, so this needs a fault; the clamp is transient by design.', diss['R208 100R clamp drain at +5VA 5.25 V (only if Q201 conducts while the rail is held up)']))
rule(diss['BQ25798 charging 0.5 A at 8.4 V']['rise_C'] <= 40, 'BQ25798 junction rise while charging <= 40 C')

out = dict(rules=[dict(ok=o, rule=m) for o, m in rules], open_findings=[dict(id=i, text=t, data=d) for i, t, d in opens],
           info=info, capacitors=caps, dc_bias=dict((k, dict(typical_uF=a, worst_uF=b, limit_uF=c)) for k, (a, b, c, _) in dcb.items()),
           pin_voltages=pv, dissipation=diss)
(CHECKS / 'corner_review.json').write_text(json.dumps(out, indent=1, default=str))
for o, m in rules:
    print(('PASS ' if o else 'FAIL ') + m)
for i, t, _ in opens:
    print(f'OPEN {i}: {t}')
print('INFO single-node nets:', stubs or 'none', '| open-drain outputs nobody reads:', unread or 'none')
sys.exit(0 if all(o for o, _ in rules) else 1)
