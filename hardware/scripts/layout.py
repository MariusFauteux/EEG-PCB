"""Readability pass over the generated sheets: group parts into titled, commented frames and orient labels.

Run by build.py after every sheet has been written. Connectivity is never edited: each "cell" (a symbol with
the wires, labels, junctions and no-connect marks geometrically joined to it) is translated as a rigid unit by
a multiple of the 1.27 mm grid, so every connection point moves with the item it touches. Labels are only
re-oriented so that their body points away from the wire stub, instead of across the pin and part body.
Group membership, titles and comments come from layout_groups.py. A cell that matches no group fails the build.
"""
from pathlib import Path
import sexpdata as sx, uuid, math, re, textwrap

S = sx.Symbol
G = 1.27                                  # connection grid, mm
PAPERS = [('A3', 420, 297), ('A2', 594, 420), ('A1', 841, 594)]
MARGIN_X, TOP_Y, TITLE_BLOCK_H = 15.24, 25.4, 40.0
GAP_X, GAP_Y, PAD = 7.62, 7.62, 3.81      # between frames, between frames, frame inner padding
CELL_GX, CELL_GY = 5.08, 3.81             # between cells inside a frame
TITLE_SIZE, NOTE_SIZE = 2.0, 1.15
CHAR_W = 0.86                             # average stroke-font character width as a fraction of size

def key(a): return str(a[0]) if isinstance(a, list) and a else ''
def sub(a, k, default=None): return next((x for x in a if key(x) == k), default)
def subs(a, k): return [x for x in a if key(x) == k]
def E(k, *a): return [S(k), *a]
def P(x, y): return (round(x, 2), round(y, 2))
def snap(v): return round(v / G) * G

def font_size(item, default=1.27):
    eff = sub(item, 'effects')
    f = sub(eff, 'font') if eff else None
    s = sub(f, 'size') if f else None
    return float(s[1]) if s else default

def text_box(x, y, text, size, justify='center', angle=0):
    """Approximate extent of a horizontal stroke-font string anchored at (x, y)."""
    w = len(str(text)) * size * CHAR_W; h = size * 1.4
    if angle in (90, 270):
        return (x - h / 2, y - w / 2, x + h / 2, y + w / 2)
    if 'right' in justify: x0 = x - w
    elif 'left' in justify: x0 = x
    else: x0 = x - w / 2
    return (x0, y - h / 2, x0 + w, y + h / 2)

def union(b, c):
    if b is None: return c
    return (min(b[0], c[0]), min(b[1], c[1]), max(b[2], c[2]), max(b[3], c[3]))

class Lib:
    """Pin connection points and body extents of the sheet's embedded library symbols."""
    def __init__(self, doc):
        self.syms = {}
        for ls in sub(doc, 'lib_symbols')[1:]:
            name = ls[1]; units = {}
            for u in subs(ls, 'symbol'):
                m = re.match(r'.*_(\d+)_(\d+)$', u[1]); unit = int(m[1]) if m else 0
                pins, box = [], None
                for g in u[2:]:
                    k = key(g)
                    if k == 'rectangle':
                        s, e = sub(g, 'start'), sub(g, 'end'); box = union(box, (min(s[1], e[1]), min(s[2], e[2]), max(s[1], e[1]), max(s[2], e[2])))
                    elif k == 'polyline':
                        for xy in subs(sub(g, 'pts'), 'xy'): box = union(box, (xy[1], xy[2], xy[1], xy[2]))
                    elif k == 'pin':
                        at = sub(g, 'at'); ln = sub(g, 'length')[1]; a = math.radians(at[3])
                        ex, ey = at[1] + ln * math.cos(a), at[2] + ln * math.sin(a)
                        pins.append((at[1], at[2], at[3]))
                        box = union(box, (min(at[1], ex), min(at[2], ey), max(at[1], ex), max(at[2], ey)))
                units[unit] = (pins, box)
            self.syms[name] = units

    def geometry(self, lib_id, unit):
        units = self.syms[lib_id]; pins, box = [], None
        for u in (0, unit):
            if u in units:
                pins += units[u][0]; box = union(box, units[u][1]) if units[u][1] else box
        return pins, box or (0, 0, 0, 0)

def items_points(doc, lib):
    """Connection points for every connectable top-level item."""
    out = {}
    for i, ob in enumerate(doc):
        k = key(ob)
        if k == 'symbol':
            at = sub(ob, 'at'); pins, _ = lib.geometry(sub(ob, 'lib_id')[1], sub(ob, 'unit')[1])
            out[i] = [P(at[1] + x, at[2] - y) for x, y, _ in pins]
        elif k == 'wire':
            out[i] = [P(xy[1], xy[2]) for xy in subs(sub(ob, 'pts'), 'xy')]
        elif k in ('label', 'global_label', 'junction', 'no_connect', 'hierarchical_label'):
            at = sub(ob, 'at'); out[i] = [P(at[1], at[2])]
    return out

def cells_of(doc, lib):
    pts = items_points(doc, lib); parent = {i: i for i in pts}
    def find(i):
        while parent[i] != i: parent[i] = parent[parent[i]]; i = parent[i]
        return i
    def join(a, b): parent[find(a)] = find(b)
    at = {}
    for i, ps in pts.items():
        for p in ps: at.setdefault(p, []).append(i)
    for p, ids in at.items():
        for j in ids[1:]: join(ids[0], j)
    wires = [(i, ps) for i, ps in pts.items() if key(doc[i]) == 'wire']
    for p, ids in at.items():          # T-connections: a point lying inside an axis-aligned wire
        for i, (a, b) in wires:
            if (a[0] == b[0] == p[0] and min(a[1], b[1]) < p[1] < max(a[1], b[1])) or (a[1] == b[1] == p[1] and min(a[0], b[0]) < p[0] < max(a[0], b[0])):
                join(ids[0], i)
    groups = {}
    for i in pts: groups.setdefault(find(i), []).append(i)
    return [sorted(g) for g in groups.values()]

def orient_labels(doc, lib):
    """Point each label body away from the wire or pin it terminates."""
    ends = {}
    for ob in doc:
        if key(ob) == 'wire':
            a, b = [P(xy[1], xy[2]) for xy in subs(sub(ob, 'pts'), 'xy')]
            ends.setdefault(a, []).append(b); ends.setdefault(b, []).append(a)
    pin_dir = {}
    for ob in doc:
        if key(ob) == 'symbol':
            at = sub(ob, 'at'); pins, _ = lib.geometry(sub(ob, 'lib_id')[1], sub(ob, 'unit')[1])
            for x, y, ang in pins: pin_dir[P(at[1] + x, at[2] - y)] = ang
    for ob in doc:
        k = key(ob)
        if k not in ('label', 'global_label'): continue
        at = sub(ob, 'at'); p = P(at[1], at[2]); away = None
        others = ends.get(p, [])
        if others:
            o = others[0]
            if o[1] == p[1] and o[0] != p[0]: away = 180 if o[0] > p[0] else 0
        elif p in pin_dir and pin_dir[p] in (0, 180):
            away = 180 if pin_dir[p] == 0 else 0
        if away is None: continue
        at[3] = away
        eff = sub(ob, 'effects'); just = sub(eff, 'justify')
        want = ['right' if away == 180 else 'left'] + (['bottom'] if k == 'label' else [])
        if just is None: eff.append(E('justify', *[S(w) for w in want]))
        else: just[1:] = [S(w) for w in want]

def item_box(ob, lib):
    k = key(ob)
    if k == 'symbol':
        at = sub(ob, 'at'); _, (x0, y0, x1, y1) = lib.geometry(sub(ob, 'lib_id')[1], sub(ob, 'unit')[1])
        b = (at[1] + x0, at[2] - y1, at[1] + x1, at[2] - y0)
        for pr in subs(ob, 'property'):
            eff = sub(pr, 'effects')
            if pr[1] in ('Reference', 'Value') and not (eff and S('hide') in eff) and str(pr[2]).strip():
                pa = sub(pr, 'at'); j = sub(eff, 'justify') if eff else None
                b = union(b, text_box(pa[1], pa[2], pr[2], font_size(pr, 1.0), ' '.join(map(str, j[1:])) if j else 'center'))
        return b
    if k == 'wire':
        xs = [P(xy[1], xy[2]) for xy in subs(sub(ob, 'pts'), 'xy')]
        return (min(p[0] for p in xs), min(p[1] for p in xs), max(p[0] for p in xs), max(p[1] for p in xs))
    if k in ('label', 'global_label'):
        at = sub(ob, 'at'); s = font_size(ob, 1.0)
        w = len(str(ob[1])) * s * CHAR_W + (2.5 * s if k == 'global_label' else 0.5)
        h = s * (2.2 if k == 'global_label' else 1.6)
        if at[3] == 180: return (at[1] - w, at[2] - h / 2, at[1], at[2] + h / 2)
        if at[3] == 90: return (at[1] - h / 2, at[2] - w, at[1] + h / 2, at[2])
        if at[3] == 270: return (at[1] - h / 2, at[2], at[1] + h / 2, at[2] + w)
        return (at[1], at[2] - h / 2, at[1] + w, at[2] + h / 2)
    at = sub(ob, 'at'); return (at[1] - 1, at[2] - 1, at[1] + 1, at[2] + 1)

def shift(ob, dx, dy):
    if not isinstance(ob, list): return
    if key(ob) in ('at', 'xy', 'start', 'end') and len(ob) >= 3 and isinstance(ob[1], (int, float)):
        ob[1] = round(ob[1] + dx, 4); ob[2] = round(ob[2] + dy, 4); return
    for z in ob: shift(z, dx, dy)

def wrap(text, width_mm, size):
    n = max(20, int(width_mm / (size * CHAR_W)))
    return textwrap.wrap(text, n) or ['']

def header_lines(title, note, width):
    return [(title, TITLE_SIZE, True)] + [(l, NOTE_SIZE, False) for l in wrap(note, width, NOTE_SIZE)]

def header_height(lines):
    return sum(s * 1.9 for _, s, _ in lines) + 1.5

def text_item(t, x, y, size, bold=False):
    font = E('font', E('size', size, size), *([E('bold', S('yes'))] if bold else []))
    return E('text', t, E('exclude_from_sim', S('no')), E('at', round(x, 3), round(y, 3), 0), E('effects', font, E('justify', S('left'), S('top'))), E('uuid', str(uuid.uuid4())))

def frame_item(x0, y0, x1, y1):
    return E('rectangle', E('start', round(x0, 3), round(y0, 3)), E('end', round(x1, 3), round(y1, 3)),
             E('stroke', E('width', 0.2), E('type', S('dash'))), E('fill', E('type', S('none'))), E('uuid', str(uuid.uuid4())))

def layout_sheet(path, spec):
    doc = sx.loads(path.read_text()); lib = Lib(doc)
    doc[:] = [ob for ob in doc if key(ob) != 'rectangle']   # frames from a previous pass
    # Sheet notes: keep the first heading line, move every other free text into a notes frame.
    texts = [ob for ob in doc if key(ob) == 'text']
    heading = min(texts, key=lambda t: sub(t, 'at')[2]) if texts else None
    notes = [str(t[1]) for t in sorted(texts, key=lambda t: (sub(t, 'at')[2], sub(t, 'at')[1])) if t is not heading]
    doc[:] = [ob for ob in doc if not (key(ob) == 'text' and ob is not heading)]
    if 'notes' in spec: notes = list(spec['notes'])
    if heading is not None:
        at = sub(heading, 'at'); at[1], at[2] = MARGIN_X, 19.05
        if 'heading' in spec: heading[1] = spec['heading']
    # Capacitor reference and value read left-justified beside the body instead of centred across it.
    for ob in doc:
        if key(ob) == 'symbol' and sub(ob, 'lib_id')[1] == 'EEG:C':
            sa = sub(ob, 'at')
            for pr in subs(ob, 'property'):
                if pr[1] in ('Reference', 'Value'):
                    pa = sub(pr, 'at'); pa[1] = round(sa[1] + 2.54, 3); pa[2] = round(sa[2] + (-1.27 if pr[1] == 'Reference' else 1.27), 3)
                    eff = sub(pr, 'effects'); eff[:] = [z for z in eff if key(z) != 'justify'] + [E('justify', S('left'))]
    orient_labels(doc, lib)
    cells = cells_of(doc, lib)
    refs = {}
    for c in cells:
        refs[id(c)] = [next(z[2] for z in doc[i] if key(z) == 'property' and z[1] == 'Reference') for i in c if key(doc[i]) == 'symbol']
    cells = [c for c in cells if refs[id(c)]] + [c for c in cells if not refs[id(c)]]
    stray = [c for c in cells if not refs[id(c)]]
    assert not stray, f'{path.name}: wiring not attached to any symbol: {[doc[c[0]] for c in stray][:2]}'
    # Assign cells to groups.
    groups = [dict(g, cells=[]) for g in spec['groups']]
    def matches(g, r): return any(re.fullmatch(p, r) for p in g['refs'])
    for c in cells:
        rs = refs[id(c)]
        hit = [g for g in groups if any(matches(g, r) for r in rs)]
        assert hit, f'{path.name}: no group for {rs}'
        assert len(hit) == 1, f"{path.name}: wired cell {rs} spans groups {[h['title'] for h in hit]}"
        order = min(i for i, p in enumerate(hit[0]['refs']) for r in rs if re.fullmatch(p, r))
        hit[0]['cells'].append((order, rs, c))
    # Pack cells inside each group (shelf packing, reading order), then size the frame.
    boxes = []
    for g in groups:
        if not g['cells']: raise AssertionError(f"{path.name}: group '{g['title']}' is empty")
        g['cells'].sort(key=lambda t: t[0])
        cb = []
        for _, _, c in g['cells']:
            b = None
            for i in c: b = union(b, item_box(doc[i], lib))
            cb.append((c, b))
        limit = max(max(b[2] - b[0] for _, b in cb), g.get('width', 170))
        x = y = rowh = 0; placed = []
        for c, b in cb:
            w, h = b[2] - b[0], b[3] - b[1]
            if x > 0 and x + w > limit: x = 0; y += rowh + CELL_GY; rowh = 0
            placed.append((c, b, x, y)); x += w + CELL_GX; rowh = max(rowh, h)
        cw = max(px + (b[2] - b[0]) for _, b, px, _ in placed); ch = y + rowh
        width = max(cw, g.get('min_width', 0)) + 2 * PAD
        lines = header_lines(g['title'], g.get('note', ''), width - 2 * PAD)
        hh = header_height(lines)
        boxes.append(dict(g=g, placed=placed, w=width, h=hh + ch + 2 * PAD, hh=hh, lines=lines))
    if notes:
        lines = [('Sheet notes', TITLE_SIZE, True)]
        for n in notes: lines += [(l, NOTE_SIZE, False) for l in wrap(n, 200, NOTE_SIZE)]
        w = max(len(l) * s * CHAR_W for l, s, _ in lines) + 2 * PAD
        boxes.append(dict(g=None, placed=[], w=w, h=header_height(lines) + 2 * PAD, hh=header_height(lines), lines=lines))
    # Place frames on the smallest paper that holds them.
    for paper, pw, ph in PAPERS:
        right, bottom = pw - MARGIN_X, ph - TITLE_BLOCK_H - 5
        x, y, rowh, pos, ok = MARGIN_X, TOP_Y, 0, [], True
        for bx in boxes:
            if x > MARGIN_X and x + bx['w'] > right: x = MARGIN_X; y += rowh + GAP_Y; rowh = 0
            pos.append((snap(x), snap(y))); x += bx['w'] + GAP_X; rowh = max(rowh, bx['h'])
            if x - GAP_X > right + 0.01 or y + bx['h'] > bottom: ok = False
        if ok: break
    sub(doc, 'paper')[1] = paper
    new = []
    for bx, (fx, fy) in zip(boxes, pos):
        new.append(frame_item(fx, fy, fx + bx['w'], fy + bx['h']))
        ty = fy + PAD * 0.6
        for t, s, bold in bx['lines']:
            new.append(text_item(t, fx + PAD, ty, s, bold)); ty += s * 1.9
        for c, b, cx, cy in bx['placed']:
            dx = snap(fx + PAD + cx - b[0]); dy = snap(fy + PAD + bx['hh'] + cy - b[1])
            for i in c: shift(doc[i], dx, dy)
    doc.extend(new)
    path.write_text(sx.dumps(doc))
    return paper, len(boxes)

def run(hw_dir, groups):
    report = []
    for name, spec in groups.items():
        paper, n = layout_sheet(Path(hw_dir) / f'{name}.kicad_sch', spec)
        report.append(f'{name}: {n} frames on {paper}')
    return report
