"""Step 14: summarise the KiCad DRC of the placed (unrouted) board and the placement rules. Run via rebuild.sh after
`kicad-cli pcb drc --refill-zones --save-board --severity-all --format json -o checks/drc.json`.

Unrouted connections are expected until Step 15. Every other DRC item must be absent or listed in ACCEPTED with the
reason it is accepted at this stage; anything else fails. Writes checks/pcb_report.md; exits non-zero on failure.
"""
from pathlib import Path
import json, re, sys, collections

HW = Path(__file__).resolve().parents[1]; CHECKS = HW / 'checks'
drc = json.loads((CHECKS / 'drc.json').read_text())
pl = json.loads((CHECKS / 'placement.json').read_text())

# (type, regular expression on the item descriptions) -> reason. Each entry names the part or zone it covers.
ACCEPTED = [
    ('isolated_copper', r"Zone 'In2 \+5VA", 'In2 +5VA plane has no via yet: it is joined to the LT3045 output and ADS1299 AVDD pins by vias in Step 15.'),
    ('isolated_copper', r"Zone 'In2 \+3V3", 'In2 +3V3 plane has no via yet: joined to the TPS62162 output and digital supply pins by vias in Step 15.'),
    ('isolated_copper', r"Zone 'In2 SYS", 'In2 SYS plane has no via yet: joined to the BQ25798 SYS pin and hold-up capacitors by vias in Step 15.'),
    ('isolated_copper', r"Zone 'In2 GND", 'In2 GND fill has no via yet: stitched to In1 GND and the GND pads by vias in Step 15.'),
    ('isolated_copper', r"Zone 'In1 GND", 'In1 GND plane has no via yet: every GND pad reaches it through a via in Step 15.'),
]
for ref, why in [('J401', 'pack JST PH body overhangs the bottom edge by design (mating face at the edge)'),
                 ('J600', 'BNC body front sits on the top edge; its outline continues over the panel bushing'),
                 ('J601', 'photodiode JST PH body overhangs the top edge by design'),
                 ('J301', 'interlock JST PH body overhangs the right edge by design'),
                 ('J310', 'USB-C receptacle front at the right edge by design'),
                 ('J420', 'microSD front at the top edge by design'),
                 ('U600', 'TLP2761 outline crosses the 8 x 1.2 mm isolation slot milled under the package (D36)')]:
    ACCEPTED.append(('silk_edge_clearance', rf'of {ref} on F\.Silkscreen', f'{ref}: {why}; the fabricator clips legend at board edges and slots.'))

viol = drc['violations']; unrouted = drc['unconnected_items']; parity = drc.get('schematic_parity', [])
accepted, failed = collections.defaultdict(list), []
for v in viol:
    text = ' || '.join(i['description'] for i in v['items'])
    hit = next((why for t, rx, why in ACCEPTED if t == v['type'] and re.search(rx, text)), None)
    if hit:
        accepted[hit].append(v)
    else:
        failed.append(v)
counts = collections.Counter((v['type'], v['severity']) for v in viol)
place_fail = [c for c in pl['checks'] if not c['ok']]
md = ['# PCB placement and DRC (Rev C11, Step 14)\n',
      f"Board {pl['board_mm'][0]:g} x {pl['board_mm'][1]:g} mm, {pl['parts']} parts and {pl['holes']} mounting holes placed on the top side; no tracks.",
      f"KiCad {drc.get('kicad_version', '?')} DRC: {len(unrouted)} unrouted connections (expected before routing), {len(viol)} other items, "
      f"{sum(len(x) for x in accepted.values())} accepted with a reason, {len(failed)} not accepted. Schematic parity: {len(parity)} differences.\n",
      '## DRC items by type\n', '| Type | Severity | Count |', '|---|---|---:|'] + [f'| {t} | {s} | {n} |' for (t, s), n in counts.most_common()]
md += ['\n## Accepted items\n'] + [f'- {len(v)} x `{v[0]["type"]}`: {why}' for why, v in accepted.items()]
md += ['\n## Not accepted\n'] + ([f"- `{v['type']}` ({v['severity']}): {v['description']} - " + ' || '.join(i['description'] for i in v['items']) for v in failed] or ['- none'])
md += ['\n## Placement rules\n'] + [('- PASS ' if c['ok'] else '- FAIL ') + c['rule'] for c in pl['checks']]
md += [f"\nParts placed outside their preferred region by the legaliser: {', '.join(pl['fallback']) or 'none'}."]
(CHECKS / 'pcb_report.md').write_text('\n'.join(md) + '\n')
for v in parity:
    print('FAIL parity', v['description'][:120])
for v in failed:
    print('FAIL DRC', v['type'], v['severity'], v['description'][:100], '|', ' || '.join(i['description'][:60] for i in v['items']))
for c in place_fail:
    print('FAIL', c['rule'])
print(f"DRC: schematic parity {len(parity)} differences, {len(unrouted)} unrouted (expected), {sum(len(x) for x in accepted.values())} accepted, {len(failed)} not accepted; "
      f"placement rules {sum(c['ok'] for c in pl['checks'])} of {len(pl['checks'])} pass")
sys.exit(1 if failed or place_fail or parity else 0)
