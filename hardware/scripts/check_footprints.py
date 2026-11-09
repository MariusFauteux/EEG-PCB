"""Step 13 footprint audit. Run via hardware/rebuild.sh after the netlist export.

For every on-board part in checks/netlist.xml: the assigned footprint must exist (KiCad stock library or the project
library EEG.pretty), every symbol pin number must have a pad, and every numbered pad must belong to a symbol pin
(so no exposed or shell pad is left unconnected). Project footprints are also checked for overlapping pads.
Also estimates board area from courtyards and lists tall parts. Writes checks/footprint_audit.json and .md;
exits non-zero on any failure.
"""
from pathlib import Path
import xml.etree.ElementTree as ET
import json, os, re, sys, collections
import sexpdata as sx

HW = Path(__file__).resolve().parents[1]; CHECKS = HW / 'checks'


def stock_dir():
    for k, v in sorted(os.environ.items()):
        if re.fullmatch(r'KICAD\d*_FOOTPRINT_DIR', k) and Path(v).is_dir():
            return Path(v)
    for c in ['/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints', '/usr/share/kicad/footprints', '/usr/local/share/kicad/footprints']:
        if Path(c).is_dir():
            return Path(c)
    raise SystemExit('KiCad footprint library not found; set KICAD10_FOOTPRINT_DIR')


STOCK = stock_dir()
tag = lambda x: str(x[0]) if isinstance(x, list) and x else ''
sub = lambda a, k: next((x for x in a if tag(x) == k), None)

# Body heights above the board (mm, maximum where the source gives one). Source in brackets; 'name' = package
# designation in the part number or footprint name; 'est.' = not confirmed from a drawing.
HEIGHT = {
    'J600': (12.5, 'Amphenol 031-6575 right-angle BNC body, est. - confirm from drawing'),
    'J500': (8.9, 'Wurth WR-BHD 2.54 mm box header, est. - confirm from drawing'),
    'JP': (11.0, '2.54 mm header 8.5 mm pins + shunt, est.'),
    'C416': (8.0, 'OS-CON on CP_Elec_10x7.9 footprint (7.9 mm can), footprint name'),
    'J300': (5.0, '1.27 mm shrouded header, est.'),
    'J401': (6.0, 'JST PH right-angle (S3B-PH-K-S), est.'),
    'J301': (6.0, 'JST PH right-angle (S2B-PH-K-S), est.'), 'J601': (6.0, 'JST PH right-angle (S2B-PH-K-S), est.'),
    'J310': (3.3, 'GCT USB4105 receptacle, est.'),
    'C116': (3.1, 'EIA 7343-31 case D, package designation'),
    'U300': (2.63, 'NINA-B3 C = 2.23 +0.40 mm, UBX-17052099 Table 28'),
    'L400': (2.1, 'Coilcraft XFL4020 (2.0 mm nominal), footprint/series name'), 'L240': (2.1, 'Coilcraft XFL4020, series name'),
    'SW': (3.5, 'E-Switch TL3342 with actuator, est.'),
    'C410': (2.7, 'Murata 1210 22 uF 25 V (2.5 +/-0.2 mm), Murata'),
}
TALL = 5.0      # report parts at or above this height
HEIGHT_LIMIT = 30.0


def footprint_path(fp):
    lib, name = fp.split(':')
    base = HW / 'EEG.pretty' if lib == 'EEG' else STOCK / f'{lib}.pretty'
    return base / f'{name}.kicad_mod'


def load(fp):
    doc = sx.loads(footprint_path(fp).read_text())
    pads, crt = [], []
    for x in doc:
        if tag(x) == 'pad':
            at, size = sub(x, 'at'), sub(x, 'size')
            layers = [str(l) for l in sub(x, 'layers')[1:]]
            pads.append(dict(num=str(x[1]), kind=str(x[2]), x=float(at[1]), y=float(at[2]), rot=float(at[3]) if len(at) > 3 else 0.0,
                             w=float(size[1]), h=float(size[2]), cu=any('Cu' in l for l in layers)))
        if tag(x) in ('fp_line', 'fp_rect', 'fp_poly', 'fp_circle', 'fp_arc') and str(sub(x, 'layer')[1]) == 'F.CrtYd':
            for k in ('start', 'end', 'center', 'mid'):
                p = sub(x, k)
                if p: crt.append((float(p[1]), float(p[2])))
            pts = sub(x, 'pts')
            if pts: crt += [(float(q[1]), float(q[2])) for q in pts[1:] if tag(q) == 'xy']
            if tag(x) == 'fp_circle':
                c, e = sub(x, 'center'), sub(x, 'end'); r = ((float(c[1]) - float(e[1])) ** 2 + (float(c[2]) - float(e[2])) ** 2) ** 0.5
                crt += [(float(c[1]) - r, float(c[2]) - r), (float(c[1]) + r, float(c[2]) + r)]
    if crt:
        xs, ys = [p[0] for p in crt], [p[1] for p in crt]
    else:  # no courtyard: copper extent plus 0.5 mm
        xs = [p['x'] + s * p['w'] / 2 for p in pads for s in (-1, 1)]; ys = [p['y'] + s * p['h'] / 2 for p in pads for s in (-1, 1)]
        xs, ys = [min(xs) - 0.5, max(xs) + 0.5], [min(ys) - 0.5, max(ys) + 0.5]
    return pads, (max(xs) - min(xs)) * (max(ys) - min(ys)), (round(max(xs) - min(xs), 2), round(max(ys) - min(ys), 2))


def box(p):
    w, h = (p['h'], p['w']) if round(p['rot']) % 180 == 90 else (p['w'], p['h'])
    return p['x'] - w / 2, p['y'] - h / 2, p['x'] + w / 2, p['y'] + h / 2


def overlaps(pads):
    """Pairs of copper pads with different numbers whose rectangles touch, and the smallest gap between them."""
    cu = [p for p in pads if p['cu'] and p['num']]
    bad, gap = [], 99.0
    for i, a in enumerate(cu):
        for b in cu[i + 1:]:
            if a['num'] == b['num']:
                continue
            ax0, ay0, ax1, ay1 = box(a); bx0, by0, bx1, by1 = box(b)
            dx, dy = max(bx0 - ax1, ax0 - bx1, 0), max(by0 - ay1, ay0 - by1, 0)
            d = (dx * dx + dy * dy) ** 0.5
            gap = min(gap, d)
            if d < 1e-6:
                bad.append((a['num'], b['num']))
    return bad, round(gap, 3)


root = ET.parse(CHECKS / 'netlist.xml').getroot()
libpins = {(lp.get('lib'), lp.get('part')): {p.get('num') for p in lp.findall('pins/pin')} for lp in root.findall('.//libparts/libpart')}
results, fails, cache, area = [], [], {}, collections.Counter()
for c in root.findall('.//components/comp'):
    ref = c.get('ref'); props = {p.get('name') for p in c.findall('property')}
    if 'exclude_from_board' in props:
        continue
    fp = c.findtext('footprint') or ''
    ls = c.find('libsource'); pins = libpins[(ls.get('lib'), ls.get('part'))]
    if not fp:
        fails.append(f'{ref}: no footprint'); continue
    if not footprint_path(fp).exists():
        fails.append(f'{ref}: footprint {fp} not found'); continue
    if fp not in cache:
        cache[fp] = load(fp)
    pads, a, dims = cache[fp]
    padnums = {p['num'] for p in pads if p['num']}
    missing, unused = sorted(pins - padnums), sorted(padnums - pins)
    if missing: fails.append(f'{ref}: symbol pins {missing} have no pad in {fp}')
    if unused: fails.append(f'{ref}: pads {unused} of {fp} belong to no symbol pin (would be left unconnected)')
    h = HEIGHT.get(ref) or HEIGHT.get(re.sub(r'\d+$', '', ref)) or (HEIGHT['C410'] if fp.endswith('C_1210_3225Metric') else None)
    results.append(dict(ref=ref, footprint=fp, pins=len(pins), pads=len(padnums), courtyard_mm=dims, area_mm2=round(a, 2),
                        height_mm=h[0] if h else None, height_source=h[1] if h else None))
    area[fp.split(':')[0]] += a

project = {}
for f in sorted((HW / 'EEG.pretty').glob('*.kicad_mod')):
    fp = 'EEG:' + f.stem
    pads, a, dims = load(fp)
    bad, gap = overlaps(pads)
    project[f.stem] = dict(pads=len(pads), courtyard_mm=dims, min_gap_between_different_pads_mm=gap, overlaps=bad)
    if bad: fails.append(f'{f.stem}: overlapping pads {bad}')
    if gap < 0.1: fails.append(f'{f.stem}: pad gap {gap} mm below 0.1 mm')

total = sum(r['area_mm2'] for r in results)
board = 110 * 85                       # Step 14 (D56): one side of the enlarged board
tall = sorted([r for r in results if r['height_mm'] and r['height_mm'] >= TALL], key=lambda r: -r['height_mm'])
for r in results:
    if r['height_mm'] and r['height_mm'] > HEIGHT_LIMIT: fails.append(f"{r['ref']}: {r['height_mm']} mm exceeds {HEIGHT_LIMIT} mm")
largest = sorted(results, key=lambda r: -r['area_mm2'])[:12]
PHYSICAL = {
    'EEG:u-blox_NINA-B306': 'Drawn from Table 28 positions; compare with a module sample or the u-blox EVK Gerbers before release; antenna cut-out per SIM Figure 14.',
    'EEG:Texas_RQM0029A_VQFN-HR-29_4x4mm': 'L-shaped corner lands drawn as two overlapping rectangles; check paste and 0.2 mm lands with the assembler.',
    'EEG:Texas_YJC0003A_FemtoFET-3_1.0x0.6mm': 'Solder-mask-defined lands; confirm the fabricator can hold 0.05 mm mask overlap.',
    'EEG:Texas_DQK_SON-6_2x2mm_CSD17571Q2': 'Exposed drain and source pads renumbered to 1 and 4; verify against a part.',
    'EEG:Texas_RWB0012A_X2QFN-12_1.6x1.6mm_P0.4mm': '0.2 mm lands at 0.4 mm pitch; confirm assembler capability.',
    'Connector_Coaxial:BNC_Amphenol_031-6575_Horizontal': 'Isolated trigger: body and mounting pegs carry TRIG_ISO_RTN; keep 8 mm to all other copper; confirm part drawing.',
    'Connector_IDC:IDC-Header_2x10_P2.54mm_Vertical': 'Stock box-header footprint; confirm Wurth 61202021621 pin 1 and key orientation.',
    'Connector_PinHeader_1.27mm:PinHeader_2x05_P1.27mm_Vertical': 'Plain header footprint; the CNC Tech 3220-10-0300-00 shroud is larger than the courtyard and its SMD/THT form must be confirmed.',
    'Capacitor_SMD:CP_Elec_10x7.9': 'Footprint chosen in Step 11 for 16SVP100M; confirm can diameter against the Panasonic drawing.',
    'Package_DFN_QFN:DFN-10-1EP_3x3mm_P0.5mm_EP1.65x2.38mm': 'LT3045 DD package: Analog Devices data sheet could not be re-downloaded; pin map from the Step 4 reading.',
}
used = {r['footprint'] for r in results}
out = dict(parts_checked=len(results), footprints=len(used), failures=fails, project_footprints=project,
           courtyard_area_mm2=round(total, 1), board_area_mm2=board, courtyard_fraction_of_one_side=round(total / board, 3),
           area_by_library=dict((k, round(v, 1)) for k, v in area.most_common()), largest_parts=largest, tall_parts=tall,
           physical_check=[dict(footprint=k, note=v) for k, v in PHYSICAL.items() if k in used], parts=results)
(CHECKS / 'footprint_audit.json').write_text(json.dumps(out, indent=1))
md = [f'# Footprint audit (Rev C12, Step 14)\n', f'{len(results)} on-board parts, {len(used)} footprints. '
      f'{"No failures." if not fails else str(len(fails)) + " failures."}\n']
md += [f'- FAIL: {x}' for x in fails]
md += ['\n## Project footprints (hardware/EEG.pretty)\n', '| Footprint | Pads | Courtyard (mm) | Min gap (mm) |', '|---|---:|---|---:|']
md += [f'| {k} | {v["pads"]} | {v["courtyard_mm"][0]} x {v["courtyard_mm"][1]} | {v["min_gap_between_different_pads_mm"]} |' for k, v in project.items()]
md += [f'\n## Area\n\nSum of courtyards: {total:.0f} mm² = {100 * total / board:.0f} % of one side of 110 x 85 mm.\n',
       '| Ref | Footprint | Courtyard (mm) | mm² |', '|---|---|---|---:|']
md += [f'| {r["ref"]} | {r["footprint"]} | {r["courtyard_mm"][0]} x {r["courtyard_mm"][1]} | {r["area_mm2"]:.0f} |' for r in largest]
md += ['\n## Tall parts (≥ 5 mm)\n', '| Ref | Height (mm) | Source |', '|---|---:|---|'] + [f'| {r["ref"]} | {r["height_mm"]} | {r["height_source"]} |' for r in tall]
md += ['\n## Needs a physical or 3D check\n'] + [f'- `{x["footprint"]}`: {x["note"]}' for x in out['physical_check']]
(CHECKS / 'footprint_audit.md').write_text('\n'.join(md) + '\n')
for x in fails:
    print('FAIL', x)
print(f'{"PASS" if not fails else "FAIL"} footprint audit: {len(results)} parts, {len(used)} footprints, pins and pads match'
      f'; courtyards {total:.0f} mm2 = {100 * total / board:.0f} % of one 110 x 85 mm side')
sys.exit(1 if fails else 0)
