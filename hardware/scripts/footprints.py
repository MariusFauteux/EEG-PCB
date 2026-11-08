"""Generate the project footprint library hardware/EEG.pretty (Step 13). Run by build.py; also runnable alone.

Every dimension below is taken from the manufacturer package drawing named in each footprint's description.
Coordinates are KiCad top view in mm (x right, y down), origin at the package centre unless stated.
Drawings that are given with y pointing up (TI land patterns) are converted by negating y.

Sources (read for Step 13, 2026-11-08):
  BQ25798 RQM0029A  - TI SLUSDV2C (rev. June 2026), package outline and example board layout 4225253/A.
  TUSB320 RWB0012A  - TI SLLSEN9F (rev. March 2022), example board layout 4221631/B.
  CSD17381F4 YJC    - TI SLPS411G (rev. January 2022), sections 7.1-7.3 (land 4220651/B).
  CSD17571Q2 DQK    - TI SLPS393A (rev. January 2015), section 7.1.1 recommended PCB pattern; pin-out figure page 1.
  NINA-B306         - u-blox UBX-17052099 R15 (NINA-B3 data sheet), Table 28 and Figures 4, 15, 16;
                      UBX-17056748 R15 (system integration manual) section 3.8 (NSMD, paste = copper) and Figure 14
                      (8 mm x 3.1 mm ground cut-out under the antenna).
"""
from pathlib import Path
import uuid

LIB = Path(__file__).resolve().parents[1] / 'EEG.pretty'
NS = uuid.UUID('6f1d3c2e-5a4b-4c3d-9e8f-0a1b2c3d4e5f')   # fixed namespace: identical output on every rebuild


def f(v):
    return f'{round(v, 4):g}'


class FP:
    def __init__(self, name, descr, tags, attr='smd'):
        self.name, self.descr, self.tags, self.attr, self.items, self.n = name, descr, tags, attr, [], 0

    def u(self):
        self.n += 1
        return str(uuid.uuid5(NS, f'{self.name}/{self.n}'))

    def pad(self, num, x, y, w, h, layers=('F.Cu', 'F.Mask', 'F.Paste'), shape='roundrect', rr=0.25, mask=None, paste=None):
        s = f'\t(pad "{num}" smd {shape}\n\t\t(at {f(x)} {f(y)})\n\t\t(size {f(w)} {f(h)})\n\t\t(layers {" ".join(chr(34)+l+chr(34) for l in layers)})\n'
        if shape == 'roundrect':
            s += f'\t\t(roundrect_rratio {rr})\n'
        if mask is not None:
            s += f'\t\t(solder_mask_margin {f(mask)})\n'
        if paste is not None:
            s += f'\t\t(solder_paste_margin {f(paste)})\n'
        self.items.append(s + f'\t\t(uuid "{self.u()}")\n\t)\n')

    def rect_pad(self, num, x0, y0, x1, y1, **kw):
        """Pad from corner coordinates (used for the segments of L-shaped corner leads)."""
        self.pad(num, (x0 + x1) / 2, (y0 + y1) / 2, abs(x1 - x0), abs(y1 - y0), **kw)

    def line(self, x0, y0, x1, y1, layer, w):
        self.items.append(f'\t(fp_line\n\t\t(start {f(x0)} {f(y0)})\n\t\t(end {f(x1)} {f(y1)})\n\t\t(stroke\n\t\t\t(width {w})\n\t\t\t(type default)\n\t\t)\n\t\t(layer "{layer}")\n\t\t(uuid "{self.u()}")\n\t)\n')

    def rect(self, x0, y0, x1, y1, layer, w):
        self.items.append(f'\t(fp_rect\n\t\t(start {f(x0)} {f(y0)})\n\t\t(end {f(x1)} {f(y1)})\n\t\t(stroke\n\t\t\t(width {w})\n\t\t\t(type default)\n\t\t)\n\t\t(fill no)\n\t\t(layer "{layer}")\n\t\t(uuid "{self.u()}")\n\t)\n')

    def text(self, kind, value, x, y, layer, hide=False):
        h = '\t\t(hide yes)\n' if hide else ''
        return (f'\t(property "{kind}" "{value}"\n\t\t(at {f(x)} {f(y)} 0)\n\t\t(layer "{layer}")\n{h}\t\t(uuid "{self.u()}")\n'
                f'\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1 1)\n\t\t\t\t(thickness 0.15)\n\t\t\t)\n\t\t)\n\t)\n')

    def keepout(self, pts, name):
        xy = ' '.join(f'(xy {f(x)} {f(y)})' for x, y in pts)
        self.items.append(f'\t(zone\n\t\t(net 0)\n\t\t(net_name "")\n\t\t(layers "F.Cu" "In1.Cu" "In2.Cu" "B.Cu")\n\t\t(uuid "{self.u()}")\n\t\t(name "{name}")\n'
                          f'\t\t(hatch edge 0.5)\n\t\t(connect_pads\n\t\t\t(clearance 0)\n\t\t)\n\t\t(min_thickness 0.25)\n'
                          f'\t\t(keepout\n\t\t\t(tracks not_allowed)\n\t\t\t(vias not_allowed)\n\t\t\t(pads not_allowed)\n\t\t\t(copperpour not_allowed)\n\t\t\t(footprints allowed)\n\t\t)\n'
                          f'\t\t(placement\n\t\t\t(enabled no)\n\t\t\t(sheetname "")\n\t\t)\n\t\t(fill\n\t\t\t(thermal_gap 0.5)\n\t\t\t(thermal_bridge_width 0.5)\n\t\t)\n'
                          f'\t\t(polygon\n\t\t\t(pts\n\t\t\t\t{xy}\n\t\t\t)\n\t\t)\n\t)\n')

    def outline(self, bx, by, cx, cy, pin1=True):
        """Fab body (half sizes bx, by), courtyard (half sizes cx, cy) and a silk pin-1 mark."""
        self.rect(-bx, -by, bx, by, 'F.Fab', 0.1)
        self.rect(-cx, -cy, cx, cy, 'F.CrtYd', 0.05)
        if pin1:
            self.line(-cx + 0.05, -cy + 0.05, -cx + 0.05, -cy + 0.55, 'F.SilkS', 0.12)
            self.line(-cx + 0.05, -cy + 0.05, -cx + 0.55, -cy + 0.05, 'F.SilkS', 0.12)

    def save(self, ref_y):
        head = (f'(footprint "{self.name}"\n\t(version 20260206)\n\t(generator "eeg_footprints")\n\t(generator_version "10.0")\n\t(layer "F.Cu")\n'
                f'\t(descr "{self.descr}")\n\t(tags "{self.tags}")\n'
                + self.text('Reference', 'REF**', 0, -ref_y, 'F.SilkS') + self.text('Value', self.name, 0, ref_y, 'F.Fab')
                + self.text('Datasheet', '', 0, 0, 'F.Fab', True) + self.text('Description', '', 0, 0, 'F.Fab', True)
                + f'\t(attr {self.attr})\n\t(duplicate_pad_numbers_are_jumpers no)\n')
        LIB.mkdir(exist_ok=True)
        (LIB / f'{self.name}.kicad_mod').write_text(head + ''.join(self.items) + '\t(embedded_fonts no)\n)\n')


def bq25798_rqm():
    """29-pin VQFN-HR 4 x 4 mm, 0.4/0.45 mm pitch, no exposed pad; corner leads 1, 9, 16, 24 are L-shaped.
    Land pattern 4225253/A (drawing y up, negated here). All lands 0.2 mm wide."""
    p = FP('Texas_RQM0029A_VQFN-HR-29_4x4mm', 'TI RQM0029A VQFN-HR 29 pin 4x4 mm (BQ25798), land pattern 4225253/A, TI SLUSDV2C', 'BQ25798 RQM VQFN-HR')
    up = lambda num, x0, y0, x1, y1: p.rect_pad(num, x0, -y1, x1, -y0, rr=0.25)
    up(1, -2.2, 1.5, -1.25, 1.7); up(1, -1.45, 1.5, -1.25, 2.2)            # pin 1 (L)
    for n in range(2, 9):
        y = 1.2 - 0.4 * (n - 2); up(n, -2.2, y - 0.1, -1.6, y + 0.1)
    up(9, -2.2, -1.7, -1.3, -1.5); up(9, -1.5, -2.2, -1.3, -1.5)           # pin 9 (L)
    for n in range(10, 16):
        x = -1.0 + 0.4 * (n - 10); up(n, x - 0.1, -2.2, x + 0.1, -1.6)
    up(16, 1.3, -1.7, 2.2, -1.5); up(16, 1.3, -2.2, 1.5, -1.5)             # pin 16 (L)
    length = {17: 0.7, 18: 0.65, 19: 0.675}
    for n in range(17, 24):
        y = -1.2 + 0.4 * (n - 17); up(n, 2.2 - length.get(n, 0.6), y - 0.1, 2.2, y + 0.1)
    up(24, 1.25, 1.5, 2.2, 1.7); up(24, 1.25, 1.5, 1.45, 2.2)              # pin 24 (L)
    for n in range(25, 30):
        x = 0.9 - 0.45 * (n - 25); up(n, x - 0.1, 1.2, x + 0.1, 2.2)
    p.outline(2.0, 2.0, 2.45, 2.45); p.save(3.2)


def tusb320_rwb():
    """12-pin X2QFN 1.6 x 1.6 mm, 0.4 mm pitch. Land pattern 4221631/B: side lands 0.7 x 0.2 at x = +/-0.65,
    top/bottom lands 0.2 x 0.5 at y = +/-0.75."""
    p = FP('Texas_RWB0012A_X2QFN-12_1.6x1.6mm_P0.4mm', 'TI RWB0012A X2QFN 12 pin 1.6x1.6 mm (TUSB320), land pattern 4221631/B, TI SLLSEN9F', 'TUSB320 RWB X2QFN')
    for n, x, y in [(1, -0.65, -0.2), (2, -0.65, 0.2), (7, 0.65, 0.2), (8, 0.65, -0.2)]:
        p.pad(n, x, y, 0.7, 0.2)
    for i, n in enumerate([3, 4, 5, 6]):
        p.pad(n, -0.6 + 0.4 * i, 0.75, 0.2, 0.5)
    for i, n in enumerate([12, 11, 10, 9]):
        p.pad(n, -0.6 + 0.4 * i, -0.75, 0.2, 0.5)
    p.outline(0.8, 0.8, 1.25, 1.25); p.save(2.0)


def csd17381f4_yjc():
    """FemtoFET YJC0003A 1.0 x 0.6 mm. Solder-mask-defined lands (TI 7.2): mask openings 0.25 x 0.15 (pins 1, 2) and
    0.25 x 0.5 (pin 3), copper 0.05 mm larger all round; stencil (7.3) 0.25 x 0.2 and 0.25 x 0.5. Pin 1 gate, 2 source,
    3 drain (top-view figure, page 1)."""
    p = FP('Texas_YJC0003A_FemtoFET-3_1.0x0.6mm', 'TI YJC0003A FemtoFET 1.0x0.6 mm (CSD17381F4), solder-mask-defined land 4220651/B, TI SLPS411G', 'CSD17381F4 YJC FemtoFET PicoStar')
    for n, y in [(1, -0.175), (2, 0.175)]:
        p.pad(n, -0.325, y, 0.35, 0.25, layers=('F.Cu', 'F.Mask'), rr=0.4, mask=-0.05)
        p.pad('', -0.325, y, 0.25, 0.2, layers=('F.Paste',), rr=0.25)
    p.pad(3, 0.325, 0, 0.35, 0.6, layers=('F.Cu', 'F.Mask'), rr=0.4, mask=-0.05)
    p.pad('', 0.325, 0, 0.25, 0.5, layers=('F.Paste',), rr=0.25)
    p.outline(0.5, 0.3, 0.75, 0.55); p.save(1.4)


def csd17571q2_dqk():
    """SON 2 x 2 mm DQK for CSD17571Q2 (TI 7.1.1). Exposed drain pad numbered 1 and exposed source pad numbered 4,
    so they join the drain (1, 2, 5, 6) and source (4) pins; the KiCad stock Texas_DQK numbers them 7 and 8 and
    would leave them unconnected."""
    p = FP('Texas_DQK_SON-6_2x2mm_CSD17571Q2', 'TI DQK SON 2x2 mm (CSD17571Q2), recommended PCB pattern TI SLPS393A 7.1.1; exposed D pad = 1, S pad = 4', 'CSD17571Q2 DQK SON')
    for n, y in [(1, -0.65), (2, 0), (3, 0.65)]:
        p.pad(n, -0.9225, y, 0.455, 0.4, paste=-0.05)
    for n, y in [(4, 0.65), (5, 0), (6, -0.65)]:
        p.pad(n, 0.9225, y, 0.455, 0.4, paste=-0.05)
    p.pad(1, 0, -0.325, 1.1, 1.05, rr=0.1, paste=-0.05)        # exposed drain
    p.pad(4, 0.096, 0.65, 0.85, 0.4, rr=0.2, paste=-0.05)      # exposed source
    p.outline(1.0, 1.0, 1.4, 1.25); p.save(2.2)


def nina_b306():
    """NINA-B306 10 x 15 mm LGA, top view, antenna end towards +y. Positions from Table 28 (mm from the module's
    top-left corner, non-antenna end at the top): pin 1 D = 1.80 from the short edge, E = 0.875 from the long edge.
    NSMD lands equal to the module pins with mask 0.05 mm larger per side; paste = copper (SIM 3.8)."""
    p = FP('u-blox_NINA-B306', 'u-blox NINA-B306 (NINA-B3x6) LGA 10x15 mm with EGP/EAGP ground pads and antenna copper keep-out; '
           'UBX-17052099 R15 Table 28, UBX-17056748 R15 3.8 and Figure 14', 'NINA-B306 NINA-B3 u-blox BLE module')
    o = lambda x, y: (x - 5.0, y - 7.5)
    def land(num, x, y, w, h):
        cx, cy = o(x, y); p.pad(num, cx, cy, w, h, shape='rect', mask=0.05)
    for k in range(10):
        land(1 + k, 0.875, 1.8 + k, 1.15, 0.7)                    # 1-10 left
        land(16 + k, 9.125, 10.8 - k, 1.15, 0.7)                  # 16-25 right, 16 at the antenna end
    for k in range(5):
        land(11 + k, 3.0 + k, 10.725, 0.7, 1.15)                  # 11-15 antenna row
        land(26 + k, 7.0 - k, 1.875, 0.7, 1.15)                   # 26-30 second row
    for k in range(6):
        land(31 + k, 2.25, 3.25 + 1.1 * k, 0.7, 0.7)              # 31-36 inner left
        land(37 + k, 7.75, 8.75 - 1.1 * k, 0.7, 0.7)              # 37-42 inner right
    for k in range(4):
        land(43 + k, 6.65 - 1.1 * k, 3.25, 0.7, 0.7)              # 43-46 inner top
    for k in range(9):
        land(47 + k, 9.0 - k, 0.65, 0.7, 0.7)                     # 47-55 outer row
    cols = [3.275, 4.425, 5.575, 6.725]
    for y, xs in [(4.575, cols[1:3]), (5.725, cols), (6.875, cols[1:3]), (8.025, cols)]:
        for x in xs:
            land('EGP', x, y, 0.7, 0.7)                           # 12 exposed ground pads
    for x in (0.65, 9.35):
        for y in (11.8, 14.35):
            land('EAGP', x, y, 0.7, 0.7)                          # 4 antenna ground pads (B306 only)
    p.keepout([o(1.0, 11.9), o(9.0, 11.9), o(9.0, 15.0), o(1.0, 15.0)], 'NINA-B306 antenna ground cut-out (SIM Figure 14)')
    p.rect(-5.0, -7.5, 5.0, 7.5, 'F.Fab', 0.1)
    p.line(-5.0, 3.5, 5.0, 3.5, 'F.Fab', 0.1)                     # antenna area begins (y = 11 from the top edge)
    p.rect(-5.25, -7.75, 5.25, 7.75, 'F.CrtYd', 0.05)
    p.line(-5.12, -7.62, -3.5, -7.62, 'F.SilkS', 0.12); p.line(-5.12, -7.62, -5.12, -6.0, 'F.SilkS', 0.12)
    p.save(8.6)


def build():
    for fn in (bq25798_rqm, tusb320_rwb, csd17381f4_yjc, csd17571q2_dqk, nina_b306):
        fn()
    return sorted(x.stem for x in LIB.glob('*.kicad_mod'))


if __name__ == '__main__':
    print(build())
