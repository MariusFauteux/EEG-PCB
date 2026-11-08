"""Step 13 costed BOM at prototype quantity. Run via hardware/rebuild.sh after build.py.

Groups the fitted parts in hardware/bom.csv by MPN, multiplies by BOARDS and prices each line at the quantity break
reached. Writes hardware/bom_cost.csv and checks/bom_cost.md. Prices are in EUR excluding VAT.

Price sources: DigiKey Germany (digikey.de) product or exact-match search pages, Coilcraft (coilcraft.com),
both read on 2026-11-08. 'confirmed' means the price was read for that exact MPN; 'family' means the value was
read for another value of the same series and size and is assumed equal; 'estimate' means no price was read.
Not included: PCB fabrication, assembly, enclosure, microSD card, battery pack, cables, shipping and VAT.
"""
from pathlib import Path
import csv, collections

HW = Path(__file__).resolve().parents[1]
BOARDS = 5
DATE = '2026-11-08'
DK, CC = 'DigiKey DE', 'Coilcraft'
# MPN -> (status, source, {break qty: unit price EUR}); list price = qty-1 price shown in an exact-match search.
C = 'confirmed'
PRICES = {
    'ADS1299IPAGR': (C, DK, {1: 78.63, 10: 65.569, 25: 62.3476}),
    'NINA-B306-00B': (C, DK, {1: 8.81}),
    'LT3045IDD#PBF': (C, DK, {1: 10.09, 10: 7.904, 25: 7.3556}),
    'BQ25798RQMR': (C, DK, {1: 5.24, 10: 4.009, 25: 3.702}),
    'TPS389001DSET': (C, DK, {1: 1.97, 10: 1.458, 25: 1.3304}),
    'TUSB320LAIRWBR': (C, DK, {1: 1.62, 10: 1.195, 25: 1.0864}),
    'TPS62162DSGR': (C, DK, {1: 1.77, 10: 1.30, 25: 1.184}),
    'TLP2761(TP,E)': (C, DK, {1: 1.19, 10: 0.837}),
    'SIT8008BIF11-33E-2.048000': (C, DK, {1: 2.26, 10: 1.964}),
    'TLV9061IDBVR': (C, DK, {1: 0.63, 10: 0.446}),
    'TLV7011DCKR': ('estimate', '-', {1: 0.60}),
    'MCP4725A0T-E/CH': (C, DK, {1: 1.13, 25: 0.9508}),
    'TPD2E2U06DCKR': (C, DK, {1: 0.59, 10: 0.363, 50: 0.2644, 100: 0.2321}),
    'CSD17381F4': (C, DK, {1: 0.42}), 'CSD17571Q2': (C, DK, {1: 0.67}),
    'SN74AUP1G08DBVR': (C, DK, {1: 0.33}), 'SN74LVC1G126DBVR': (C, DK, {1: 0.12}), 'SN74LVC1G14DBVR': (C, DK, {1: 0.12}),
    'SN74LVC1G74DCUR': (C, DK, {1: 0.56}), 'OPA376AIDBVR': (C, DK, {1: 1.80}),
    'BSS138': (C, DK, {1: 0.29}), 'BAT54,215': (C, DK, {1: 0.12}), '1N4148WS-7-F': (C, DK, {1: 0.16}),
    'LTST-C190GKT': (C, DK, {1: 0.12, 10: 0.083}),
    'TL3342F160QG': (C, DK, {1: 0.52, 10: 0.449, 25: 0.4184}),
    '16SVP100M': (C, DK, {1: 1.68, 10: 1.096}),
    'DM3AT-SF-PEJM5': (C, DK, {1: 3.15}), 'USB4105-GF-A': (C, DK, {1: 0.71}),
    'S3B-PH-K-S': (C, DK, {1: 0.13}), 'S2B-PH-K-S': (C, DK, {1: 0.11}),
    '61202021621': (C, DK, {1: 0.80, 10: 0.786}), '61300311121': (C, DK, {1: 0.12, 10: 0.095, 25: 0.0792}),
    '3220-10-0300-00': (C, DK, {1: 0.67}), '031-6575': (C, DK, {1: 11.18, 10: 9.497}),
    'T491D107K010AT': (C, DK, {1: 1.46}),
    'XFL4020-102MEC': ('family', CC, {1: 2.20}), 'XFL4020-222MEC': ('family', CC, {1: 2.20}),
    'ERJ-PB6B4702V': (C, DK, {1: 0.27, 10: 0.143, 25: 0.1152, 50: 0.0992, 100: 0.0868, 250: 0.0743}),
    'ERJ-3EKF1002V': (C, DK, {1: 0.09, 10: 0.035, 25: 0.0256, 50: 0.021, 100: 0.0173, 250: 0.01372}),
    'ERA-3ARB4992V': (C, DK, {1: 0.36, 10: 0.295, 50: 0.2584, 100: 0.2442}),
    'GCM188R71H104KA57D': (C, DK, {1: 0.18, 10: 0.101, 50: 0.072, 100: 0.063, 500: 0.04792}),
    'GRM32ER71E226KE15L': (C, DK, {1: 0.71, 10: 0.444, 50: 0.3392, 100: 0.3071}),
    # Step 14 (read 2026-11-08). GCM21BR71H105KA03L is active but on backorder at DigiKey DE (3000 due 30-Dec-2026);
    # LCSC C126592 lists it. In-stock fallback of the same rating: KEMET C0805C105K5RACTU.
    'TPD1S514-1YZR': (C, DK, {1: 1.29, 10: 0.937, 25: 0.8488, 100: 0.7529}),
    'TPS7A2050PDBVR': (C, DK, {1: 0.35, 10: 0.242, 25: 0.216, 100: 0.1863}),
    'GCM21BR71H105KA03L': (C, DK + ' (backorder)', {1: 0.21, 10: 0.122, 50: 0.087, 100: 0.0764}),
}
FAMILY = [('ERJ-PB6B', 'ERJ-PB6B4702V'), ('ERJ-3EKF', 'ERJ-3EKF1002V'), ('ERA-3A', 'ERA-3ARB4992V'), ('GCM188', 'GCM188R71H104KA57D'),
          ('GCM1885', 'GCM188R71H104KA57D'), ('GCM1555', 'GCM188R71H104KA57D')]
ESTIMATE = {'ERJ-8ENF': {1: 0.10, 10: 0.05}, 'ERJ-3GEY0R00V': {1: 0.09, 10: 0.03}, 'GCM21BR71E105KA56L': {1: 0.25, 10: 0.15, 50: 0.10},
            'GRM31CR71E106KA12L': {1: 0.45, 10: 0.30, 50: 0.22}, 'GRM21BR71C475KE51L': {1: 0.25, 10: 0.16},
            'GRM31C5C1H104JA01L': {1: 0.60, 10: 0.45}}
EXTRA = [('Wurth Elektronik', '60900213421', 'Jumper shunt 2.54 mm for JP1-JP8 (not on the schematic)', 8, 'estimate', '-', {1: 0.15})]


def price(mpn):
    if mpn in PRICES:
        return PRICES[mpn]
    for prefix, ref in FAMILY:
        if mpn.startswith(prefix):
            s, src, br = PRICES[ref]; return 'family', f'{src} ({ref})', br
    for prefix, br in ESTIMATE.items():
        if mpn.startswith(prefix):
            return 'estimate', '-', br
    raise KeyError(f'no price for {mpn}')


def at(br, q):
    return br[max(k for k in br if k <= q)]


rows = [r for r in csv.DictReader(open(HW / 'bom.csv')) if r['Population'] == 'FIT']
groups = collections.OrderedDict()
for r in rows:
    g = groups.setdefault(r['MPN'], dict(mfr=r['Manufacturer'], descr=r['Description'], refs=[]))
    g['refs'].append(r['Ref'])
lines = []
for mpn, g in groups.items():
    status, src, br = price(mpn)
    per = len(g['refs']); q = per * BOARDS; u = at(br, q)
    lines.append(dict(mfr=g['mfr'], mpn=mpn, descr=g['descr'], per_board=per, qty=q, unit=u, total=u * q, status=status, source=src, refs=' '.join(g['refs'])))
for mfr, mpn, d, per, status, src, br in EXTRA:
    q = per * BOARDS; u = at(br, q)
    lines.append(dict(mfr=mfr, mpn=mpn, descr=d, per_board=per, qty=q, unit=u, total=u * q, status=status, source=src, refs='(JP1-JP8)'))
lines.sort(key=lambda l: -l['total'])
total = sum(l['total'] for l in lines)
by = collections.Counter()
for l in lines: by[l['status']] += l['total']
with (HW / 'bom_cost.csv').open('w') as f:
    w = csv.writer(f)
    w.writerow(['Manufacturer', 'MPN', 'Description', 'Qty per board', f'Qty for {BOARDS} boards', 'Unit price EUR', 'Line total EUR', 'Price status', 'Source', 'Date', 'References'])
    for l in lines:
        w.writerow([l['mfr'], l['mpn'], l['descr'], l['per_board'], l['qty'], f"{l['unit']:.4f}", f"{l['total']:.2f}", l['status'], l['source'], DATE, l['refs']])
md = [f'# Costed BOM, {BOARDS} prototype boards (Rev C11)\n',
      f'Parts only, EUR excluding VAT, prices read on {DATE}. {len(lines)} lines, {sum(l["qty"] for l in lines)} parts.\n',
      f'- Total for {BOARDS} boards: **€{total:.2f}** (≈ €{total / BOARDS:.2f} per board; with 19 % VAT ≈ €{1.19 * total / BOARDS:.2f})',
      *[f'- {k}: €{v:.2f} ({100 * v / total:.1f} %)' for k, v in by.most_common()],
      '\nNot included: PCB fabrication, assembly, enclosure, microSD card, battery pack, harness and cables, shipping.\n',
      '| MPN | Manufacturer | Per board | Qty | Unit € | Total € | Status |', '|---|---|---:|---:|---:|---:|---|']
md += [f"| {l['mpn']} | {l['mfr']} | {l['per_board']} | {l['qty']} | {l['unit']:.3f} | {l['total']:.2f} | {l['status']} |" for l in lines]
(HW / 'checks' / 'bom_cost.md').write_text('\n'.join(md) + '\n')
print(f'BOM cost: {len(lines)} lines, EUR {total:.2f} for {BOARDS} boards (EUR {total / BOARDS:.2f} per board, parts only, excl. VAT); '
      + ', '.join(f'{k} EUR {v:.2f}' for k, v in by.most_common()))
