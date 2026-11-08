# Step 14 review: VBUS overvoltage protection, floor plan and placement (Rev C11)

Date: 2026-11-08 • Revision: C11 • Status: drawn, placed and checked by script; not routed, built or measured

Step 14 had two parts, agreed with the user before work began:

- **Part A** closes D54: an overvoltage switch between the USB-C VBUS contacts and every USB_5V load.
- **Part B** resolves D55: the board grows to about 110 × 85 mm with every part on the top side, which revises D15. This step adds a generated KiCad PCB with stack-up, rules, keep-outs, planes and placement. It does not route the board.

Decisions D56–D60 are recorded in [../decision_log.md](../decision_log.md). Everything here comes from manufacturer documents read on 2026-11-08 and listed in section 7, or is marked as an assumption.

## 1. Result in brief

| Check | Result |
|---|---|
| Netlist assertions (`validate.py`) | 477 pass (441 at Step 13) |
| KiCad ERC | 0 errors, 0 warnings |
| Footprint audit | Pass: 375 on-board parts, 41 footprints. Courtyards cover 4812 mm², 51 % of one 110 × 85 mm side |
| OVP analysis (`analyze_ovp.py`, new) | 17 of 17 rules pass |
| Corner review | 27 of 27 rules pass. F01 is closed and replaced by two rules |
| Other analyses and host tests | Unchanged, all pass |
| PCB placement rules (`pcb_place.py`) | 33 of 33 pass |
| KiCad DRC (`kicad-cli pcb drc`, all severities, schematic parity) | 0 parity differences; 499 unrouted connections (expected). 30 other items, all warnings, each accepted with a reason in `check_pcb.py`. No errors |
| BOM | 368 fitted parts, €950.09 for 5 boards, about €190 per board in parts (Step 13: €937.64) |

## 2. Part A: VBUS overvoltage protection

### 2.1 What was wrong

At Rev C10, J310's VBUS contacts were the USB_5V net. A compliant source never exceeds 5.5 V. A faulty charger, or a PD source that applies a higher voltage without negotiation, would reach every USB_5V load directly:

- D312 (TPD2E2U06, breakdown 6.5–8.5 V);
- the USB-sense inverter U321, whose 6.5 V absolute maximum is reached at VBUS = 7.15 V;
- the module VBUS pad.

The BQ25798 alone stops at 26 V (F01, D54).

### 2.2 Choice: TI TPD1S514-1

Two TI parts were read in full.

| | TPD4S014 (SLVSAU0G) | **TPD1S514-1 (SLVSCF6F), chosen** |
|---|---|---|
| VBUS rating | 30 V absolute, 28 V DC protection | 30 V absolute on VBUS_CON, IEC 61000-4-5 100 V surge with an internal clamp |
| OVP rising threshold | 5.90–6.45 V | 5.90 / 5.95 / 5.99 V (min/typ/max, 25 °C) |
| Response | 11 µs typical, no maximum | < 100 ns |
| Switch | 151/200 mΩ | 39/50 mΩ at 1 A, bidirectional nFET |
| Start-up | 17 ms | 20 ms delay, then 3.5 ms soft start after every UVLO (plug-in) or OVP event |
| Extra | ESD on D+, D−, ID; ACK output | VBUS_POWER: always-on LDO output, 4.7–4.95 V at 5 V in, ≤ 5.5 V with 20–30 V in, 3 mA |
| Package | WSON-10, 2 × 2 mm | WCSP-12 (YZ0012), 0.4 mm pitch |

The TPD4S014's 6.45 V maximum trip point sits 50 mV below D312's breakdown. Its 11 µs typical response lets a fast step through. The TPD1S514-1 has a tight threshold, a 100 ns response, a lower resistance and the VBUS_POWER output, which Part A uses (see below).

The cost is a 0.4 mm pitch WCSP. Every inner ball shares a net with a neighbouring outer ball (B2 with A2, B3 with C2/C3), so all twelve balls escape on the top layer without via-in-pad. The land pattern follows TI 4221703/A: 0.225 mm non-solder-mask-defined lands and a 0.25 mm stencil. It is generated as `EEG:Texas_YZ0012_DSBGA-12_P0.4mm`.

Price: €0.937 at 10 (DigiKey DE, 5153 in stock).

Wiring (`scripts/ovp.py`, `build.py`):

- **J310 and VBUS_CON.** J310's four VBUS contacts are now the new net VBUS_CON. U323's VBUS_CON balls sit on it, with C324 (1 µF, 50 V, GCM21BR71H105KA03L) at the balls.
- **USB_5V.** U323's VBUS_SYS balls feed USB_5V, which serves the BQ25798, C400, the new C401, C402, C321, D312 and the LDO below.
- **EN.** EN is tied low (TI section 9.2.1, "always enabled"). The OVP and UVLO protection stay active, and no GPIO is needed.
- **VBUS_POWER (net USB_VPWR).** It drives C325 (1 µF, which TI requires) and the top of the USB-sense divider R362/R363. USB_ABSENT therefore goes low whenever a cable carries VBUS, including while U323 is blocking an overvoltage source. This matters for SERVICE_OK: a faulty charger must not be able to make the board think no cable is attached.
- **R360 (887 kΩ, TUSB320 VBUS_DET).** It moves to the connector side, as TI SLLSEN9F asks ("connected through a 900-kΩ resistor to VBUS on the Type-C").
- **Module VBUS pad 31: new 5.0 V LDO (U324, TPS7A2050PDBVR).** The nRF52840 VBUS pin is rated 4.35–5.5 V for operation and 5.8 V absolute maximum (Nordic nRF52840 Product Specification, "Recommended operating conditions" and "Absolute maximum ratings"). The TPD1S514-1 ceiling of 5.99 V is above both, so U324 feeds pad 31 its own 5.0 V ±1.5 %. U324 takes IN and EN from USB_5V, has C326 on its input and C327 and C303 on its output. Nordic's 6 Ω maximum VBUS source resistance is met by an LDO output.
- **D324 (BAT54) from MCU_VBUS to USB_5V.** TI SBVS338H 6.3.7 limits reverse current through the TPS7A20 to 5 % of 300 mA. After unplugging, the charger can pull USB_5V down faster than MCU_VBUS decays: about 16.5 mA from 1.1 µF at 15 V/ms (assumption). D324 carries that discharge.
- **C401.** A second 10 µF goes on USB_5V, because TI recommends 2 × 10 µF + 100 nF at the BQ25798 VBUS pins (SLUSDV2C pin table). Step 11 had held this back to stay within the USB Type-C sink bulk limit. That limit no longer applies behind U323's soft start (section 2.4).

### 2.3 Clamp level, worst-case transient and downstream parts

Steady state: USB_5V ≤ 5.99 V (TI, 25 °C). Over temperature, 6.05 V is allowed (+1 %; assumption, because Figure 3 of SLVSCF6F is not tabulated).

Fastest transient: a step from 6.05 V to 30 V during the 100 ns response. With a source and cable inductance of at least 100 nH (assumption; a USB-C cable alone is several hundred nH), the charge that gets through is ΔV·t²/2L = 1.2 µC. Into the worst-case 12.3 µF of effective USB_5V capacitance this adds 98 mV, so the peak is **6.15 V**. PMID capacitance is ignored, which is the worst case. TI also states that VBUS_SYS stays below VOVP during 100 V IEC 61000-4-5 surges.

| Node | Worst case | Limit | Source |
|---|---:|---:|---|
| BQ25798 VBUS, VAC1, VAC2 | 6.15 V | 30 V absolute, 24 V operating | SLUSDV2C |
| D312 TPD2E2U06 on USB_5V | 6.15 V | 6.5 V breakdown minimum | SLLSEG9C |
| U324 TPS7A2050 VIN | 6.15 V peak; 5.99 V steady | 6.5 V absolute; 6.0 V recommended | SBVS338H |
| Module pad 31 (MCU_VBUS) | 4.67–5.08 V | 4.35–5.5 V operating, 5.8 V absolute | nRF52840 PS |
| U321 input (divider from USB_VPWR, 1 %) | 5.01 V | 5.5 V recommended | Step 13 |
| TUSB320 VBUS_DET at 30 V on VBUS_CON | 3.45 V | 4 V absolute | SLLSEN9F; internal pull-down taken as 95 kΩ + 20 % (assumption) |
| C324 on VBUS_CON | 30 V | 50 V rating | Murata |

Two margins are thin and are recorded as risks:

- **D312.** Between 5.5 V (its stand-off voltage) and the OVP ceiling, D312's leakage rises but it does not conduct. Only a non-compliant source puts it there.
- **U324 VIN.** It is 10 mV inside its recommended 6.0 V at 25 °C and may exceed it slightly when hot. It stays 350 mV inside the absolute maximum.

### 2.4 Inrush and the USB Type-C sink limit

At plug-in the source sees only C324: 1.1 µF worst case, 6 µC at 5.5 V. That is well inside the 10 µF sink bulk limit and the 50 µC USB 2.0 inrush charge. Both limits come from the USB specifications as recorded in Step 11; they were not re-read.

After the 20 ms delay, U323 soft-starts over 3.5 ms (10–90 %) into everything behind it: C400, C401, C321, C326, C402, PMID C403–C406. That is 57.4 µF with +10 % tolerance and no DC-bias derating, which is the worst case for inrush. The resulting current is 69 mA, below one 100 mA unit load and inside the 100 µF CLOAD maximum.

TI gives tSS as a typical value only. A 1 ms soft start would give about 240 mA for 1 ms, which is acceptable but noted. Rule set: `analyze_ovp.py`.

### 2.5 On-resistance loss

RON is 50 mΩ maximum at 25 °C; 75 mΩ is assumed hot (×1.5, assumption). RθJA is 89 °C/W (JEDEC board).

| Input current | Drop | Loss | Junction rise |
|---|---:|---:|---:|
| 0.44 A (hardware ILIM ceiling) | 33 mV | 15 mW | 1 °C |
| 1.01 A (0.5 A charge at 8.4 V, Step 11) | 76 mV | 77 mW | 7 °C |
| 1.5 A (Type-C 1.5 A advertisement) | 113 mV | 169 mW | 15 °C |
| 3.0 A (Type-C 3 A advertisement) | 225 mV | 675 mW | 60 °C (120 °C at 60 °C ambient; TSHDN 145 °C) |

Firmware should cap IINDPM at the 1.5 A level unless a 3 A charge rate is ever needed.

### 2.6 Reverse current and module VBUS behaviour

- **TPD1S514-1.** Its body diode conducts from VBUS_SYS to VBUS_CON (up to 1 A) only if USB_5V is above the connector. That happens only in BQ25798 OTG mode. The BQ25798 has no SYS-to-VBUS path outside OTG: Q1's body diode points from SW1 to PMID, and Q3's from SW2 to SYS. Firmware must leave EN_OTG = 0, the reset default. It may also set VAC_OVP = 11 (7.0 V) as a second layer.
- **Module pad 31.** It rises about 24 ms after plug-in, after U323's delay and soft start plus U324's start-up. USBDETECTED then fires: VBUS detect is 3.4–4.3 V. With USB absent, MCU_VBUS is discharged through U324 and D324.
- **USB_VPWR.** It is unpowered with USB absent, so R363 holds U321's input low and USB_ABSENT high.

### 2.7 Checks added

- `hardware/baseline/step13_netlist.xml` was copied from the Step 13 export.
- `validate.py` now has a Step 14 block (36 new assertions):
  - **Added:** U323, U324, D324, C324–C327 and C401, and nothing else.
  - **Changed:** the J310 VBUS contacts, R360 pin 1, R362 pin 1, U300 pad 31 and C303 pin 1 moved off USB_5V, each to its stated net.
  - **Retained:** all 1096 other pin connections keep the same partners, and no existing value changed.
  - The new nets are checked as complete member sets, and the MPNs and the project footprint are checked.
- `analyze_ovp.py` is new: 17 rules, `checks/ovp_analysis.json`.
- `review_corners.py`: F01 is closed. The new rail limits (VBUS_CON 30 V, USB_5V 6.2 V, USB_VPWR 5.5 V, MCU_VBUS 5.1 V) feed the capacitor-rating rule.
- `layout_groups.py` has two new titled frames on the USB-C sheet: "VBUS overvoltage switch (Step 14)" and "Module VBUS regulator (Step 14)".
- The BOM and the footprint audit cover the new parts. GCM21BR71H105KA03L is active but on backorder at DigiKey DE (3000 due 30 December 2026). KEMET C0805C105K5RACTU is an in-stock part of the same rating.

## 3. Part B: board, stack-up and rules

### 3.1 Board size (D56)

The board is 110 × 85 mm with 3 mm corner radii and all parts on the top side. Courtyards fill 51 % of one side (68 % of 100 × 70 at Step 13). That leaves room for the 8 mm trigger barrier, the antenna clearance and routing.

There are four M3 holes (3.2 mm, NPTH), 3.5 mm in from each corner.

The 2S pack sits beside the board. J401 is on the bottom edge, so with the tallest part (the BNC, estimated 12.5 mm) a 30 mm enclosure height is still possible. D15's €500 budget and four layers stand. Its 100 × 70 mm footprint is superseded.

### 3.2 Stack-up: JLCPCB JLC04161H-3313, 1.6 mm

Source: jlcpcb.com/impedance, 4-layer table, read 2026-11-08.

| Layer | Use | Material | Thickness |
|---|---|---|---:|
| F.Cu | Signal and all parts | Copper, 1 oz | 0.035 mm |
| | | Prepreg 3313 × 1 (εr 4.1) | 0.0994 mm |
| In1.Cu | Continuous GND | Copper, 0.5 oz | 0.0152 mm |
| | | Core | 1.265 mm |
| In2.Cu | Power: +5VA, +3V3, SYS islands in a GND fill | Copper, 0.5 oz | 0.0152 mm |
| | | Prepreg 3313 × 1 | 0.0994 mm |
| B.Cu | Signal | Copper, 1 oz | 0.035 mm |

The thin 3313 prepreg puts F.Cu 0.1 mm above the GND plane. That keeps return loops small under the ADC and converters, and makes a 90 Ω differential pair practical.

Estimate for the USB pair: 0.15 mm tracks with a 0.18 mm gap give about 90 Ω. This uses the IPC-2141 edge-coupled microstrip approximation, h = 0.0994 mm, t = 0.035 mm, εr = 4.1, Z0 ≈ 49.8 Ω, coupling factor 0.91; solder mask is ignored. It is an estimate: confirm the width with JLCPCB's impedance calculator before routing.

The stack-up is written into the board's setup with ENIG finish. ENIG is needed because JLCPCB requires it for 0.2–0.25 mm BGA pads, and the U323 lands are 0.225 mm.

### 3.3 Design rules (JLCPCB capabilities page, multilayer, read 2026-11-08)

| Rule | JLCPCB | Board setting |
|---|---|---|
| Track / space | 0.09 / 0.09 mm | 0.10 / 0.10 mm minimum; 0.20 / 0.15 mm default |
| Via | 0.15 mm hole / 0.25 mm diameter minimum; diameter ≥ hole + 0.1 (0.15 preferred); preferred hole 0.2 mm | 0.25 / 0.50 mm standard via; minimum 0.15 / 0.25 |
| Via hole to track; NPTH to track | 0.2 mm | 0.20 mm hole clearance |
| Via hole to hole | 0.2 mm | 0.25 mm |
| Copper to routed edge or slot | ≥ 0.2 mm | 0.30 mm |
| Non-plated slot | ≥ 1.0 mm wide | 1.2 mm slot under U600 |
| Soldermask | 1:1 opening; bridge ≥ 0.10 mm (green) | 0 mm expansion; 0.10 mm minimum web |
| Legend | Line ≥ 0.15 mm, text ≥ 1.0 mm, 0.15 mm to pads | Same |
| BGA pad | 0.2–0.25 mm needs ENIG; pad to trace ≥ 0.09 mm | ENIG |

Netclasses (`EEG_RevC.kicad_pro`, written by `pcb_place.py`):

| Class | Track | Clearance | Nets |
|---|---:|---:|---|
| Power | 0.80 mm | 0.20 mm | SYS, PACK_POS, PACK_IN, USB_5V, VBUS_CON, CHG_PMID, CHG_SW1, CHG_SW2, SW_DIG |
| Supply | 0.40 mm | 0.20 mm | +3V3, +5VA, +3V3_ADC, MCU_VBUS, USB_VPWR, REGN, CHG_BTST1/2 |
| USB_90R | 0.15 mm, 0.18 mm gap | 0.20 mm | USB_DP, USB_DM |
| Analog_in | 0.20 mm | 0.20 mm; 0.3 mm to other classes by rule | 84 electrode, REF, BIAS and ADC_IN nets |
| Trigger_iso | 0.30 mm | 8 mm to every other net by rule | TRIG_ISO_IN, TRIG_ISO_RTN, TRIG_LED_A, U600 NC pin |

Custom rules (`EEG_RevC.kicad_dru`; later rules take precedence):

- Pads of one land pattern may sit 0.09 mm apart. The TI FemtoFET (Q201, Q202) has 0.10 mm and the WCSP 0.175 mm.
- J310's GND pads may sit 0.19 mm from its NPTH pegs. The stock GCT USB4105 pattern places them 0.194 mm apart, 6 µm under the board's 0.20 mm.
- USB pair: 0.15 mm width, 0.18 mm gap, ≤ 0.15 mm skew.
- Analogue inputs: 0.3 mm to non-analogue copper.
- Trigger isolation: 8 mm clearance and 8 mm creepage to every other net (D36). KiCad's creepage check accounts for the slot.

Soldermask bridges are allowed inside footprints. The 0.4 mm pitch WCSP and X2QFN webs are below JLCPCB's 0.10 mm, so their openings will be ganged. That is normal for these packages, but the assembler must confirm it.

## 4. Floor plan (D58)

The plots are `hardware/checks/pcb_placement_top.pdf` (F.Cu, courtyards, assembly, silkscreen, edge and floor-plan outlines) and `hardware/checks/pcb_inner_planes.pdf` (In1, In2). They were inspected for this review. Coordinates are board-local, in mm from the top-left corner, with x to the right and y down.

| Zone | Area | Contents | Rationale |
|---|---|---|---|
| Analogue | x 0–62, y 29–85 | J500 on the left edge; eight channel networks; JP1–JP8; REF buffer; BIAS network; ADS1299; its decoupling; LT3045 +5VA below the ADC | Electrode inputs travel from the left edge straight to the ADC's input side (pins 1–16 face left). CH1 is at the bottom and CH8 at the top, in the same order on J500 (rotated 180°) and on the ADC. JP pin 3 forms a vertical REF_BUF bus. The LT3045 sits at the edge facing the power zone, so SYS enters the analogue zone over the shortest distance. |
| Event / isolated trigger | Top edge, x 18–50 | J600 BNC (body front on the edge), R600, D600, U600; photodiode J601 and its TIA top-left | The isolated area (x 26.25–41.75, y 0–20) has an 8 mm U-shaped barrier with no tracks, vias or pours. U600's LED pins face the BNC and its output pins sit 8.2 mm away beyond the barrier, with an 8 × 1.2 mm slot milled between the pad rows (D36). The trigger and photodiode are kept away from the electrode inputs and on a different face from the electrode harness. |
| Digital | x 46–95, y 0–62 | microSD (top edge, card outwards); RESET/RECOVERY/RECORD buttons (top edge); supervisors, reset logic, restart latch and service gates; ADC interface buffers and the 2.048 MHz clock beside the ADC's SPI side; TPS62162 buck at (86, 55) | Slow logic fills the middle; the SPI and clock run from the ADC's right side towards the module. The buck sits next to the module it mainly feeds and away from the ADC. |
| Module | Right edge, centred | NINA-B306 centred on the right edge (y = 42.5 of 85), antenna end 0.95 mm from the edge; J300 SWD beside it; J301 interlock on the right edge above | u-blox UBX-17056748 R15 3.3.3 for the B3x6: centre of an edge, antenna outwards; ground ≥ 10 mm both sides (In1 is continuous); full ground under the module with the 8 × 3.1 mm cut-out (in the footprint); no high or large metal within 10 mm of the antenna. That last rule is enforced as a rectangle (x ≥ 95.7, y 27.5–57.5) that no connector, switch, inductor, bulk electrolytic, oscillator or hole may enter. Small passives are allowed there. |
| Power | Bottom right | USB-C J310 (right edge, y = 72); U323 and C324 between J310 and the charger; TUSB320 and ESD at the connector; BQ25798 with L400 directly below its switch-node row; PMID, VBUS and SYS capacitors around it; C416 OS-CON; Q400 and J401 pack connector (bottom edge); POWER button (bottom edge) | TI SLUSDV2C layout: 100 nF parts at the PMID, SYS and VBUS pins (2.2–2.5 mm pad-to-pad), short SW1-L400-SW2 path (5.1 mm), BATP Kelvin to the pack side of Q400 (R400, 1.7 mm). The SYS bulk block sits on the side of L400 away from the ADC. The charger hot loop is ≥ 15.4 mm from the ADC courtyard and ≥ 13.5 mm from every analogue-front-end part. |

The BQ25798 is rotated 180°. In TI's land pattern the PMID/SW1/GND/SW2/SYS row is on the top. Rotation puts that row facing L400 and the VBUS pins facing the USB side. The first placement had assumed the opposite, which the SW-to-inductor rule caught (8.2 mm).

Planes:

- In1.Cu is GND over the whole board, 0.5 mm inside the rounded edge. It is broken only by the trigger barrier and the antenna cut-out.
- In2.Cu carries +5VA under the ADC and LT3045 (x 43–62, y 44–84), +3V3 under the digital zone, SYS under the power zone, and GND everywhere else. That includes under the electrode inputs and around the module.

## 5. Placement method and checks (D59, D60)

`scripts/pcb_place.py` runs under KiCad's own Python (pcbnew). It builds the board from `checks/netlist.xml`:

- **Footprints and paths.** Every footprint is the audited footprint from the netlist. It carries the symbol's sheet/symbol UUID path, so KiCad's "Update PCB from Schematic" matches every part without re-association.
- **Stable UUIDs.** Schematic sheet and symbol UUIDs are now derived from names (`schematic_helpers.py`), so these paths survive rebuilds.
- **Fixed positions.** Connectors, ICs, the channel networks and the converter power parts have fixed positions.
- **Capacitors at their pins.** Each decoupling capacitor goes at a specific pin. A pre-pass gives every IC supply pin a capacitor from its own sheet.
- **Other parts.** Remaining parts go next to the IC or connector they share a signal net with, preferring the same sheet. A 0.25 mm spiral search finds the nearest spot where courtyards keep 0.15 mm apart and the keep-outs are respected.
- **Outside their region.** Eight parts landed outside their preferred region: C412, R321, R345, R346, R348, R349, R362, R363. All are still within the rules below.

Placement rules (`checks/placement.json`, `checks/pcb_report.md`, 33 of 33 pass):

- **Decoupling.** Every IC supply pin has a GND capacitor on its net within 5 mm pad-to-pad. The NINA VCC/VCC_IO pads are 3.0 mm from theirs.
- **Converter loops and Kelvin connections:**
  - BQ25798 PMID, SYS and VBUS 100 nF at 2.5 / 2.5 / 2.2 mm;
  - TPS62162 VIN capacitor at 2.5 mm, L240 to SW at 3.8 mm;
  - L400 to SW1 and SW2 at 5.1 mm;
  - R400 BATP at the pack side of Q400, 1.7 mm;
  - LT3045 RSET at 2.4 mm, CSET at 3.4 mm, output capacitor at 2.6 mm from OUT/OUTS.
- **"Near ADC" series parts.** The 33 Ω SPI resistors, R330 and R331 (DOUT/DRDY) and R332 (reset) are within 6.9 mm of their ADS1299 pins. Y340 is 5.1 mm from CLK. The 220 pF differential capacitors sit at the ADC end of each channel.
- **OVP.** C324 is 2.6 mm from the VBUS_CON balls; U323 is 7.0 mm from the J310 VBUS contacts.
- **Zones and edges.** Analogue parts are all inside the analogue zone. The isolated area and barrier hold only the trigger parts. No large metal is within 10 mm of the antenna. Every edge connector is at its edge.

## 6. DRC result

`kicad-cli pcb drc --refill-zones --save-board --severity-all` with KiCad 10.0.8. The zones are filled with the final project rules, and the rebuild saves the filled board.

- 499 unrouted connections: expected before routing.
- No errors.

30 warnings, each accepted individually in `check_pcb.py`:

| Item | Count | Reason |
|---|---:|---|
| `isolated_copper`, In2 +5VA / +3V3 / SYS / GND fills | 4 | No vias exist yet. Each plane is joined to its pins by vias in Step 15. |
| `silk_edge_clearance`, J401, J601, J301 | 7 each | JST PH bodies overhang their edges by design (mating face outwards) |
| `silk_edge_clearance`, J600 | 3 | BNC body front on the top edge; its outline continues over the panel bushing |
| `silk_edge_clearance`, U600 | 2 | Package outline crosses the isolation slot under it |

The fabricator clips legend at edges and slots.

Problems found and fixed during the step:

- The analogue clearance was applied inside the ADC footprint (its pins are 0.2 mm apart). The pad-to-pad rule now handles footprint lands.
- U600's NC pin was outside the isolated netclass.
- Plane outlines did not follow the rounded corners.
- Zones were not refilled with the project rules (hole clearance to NPTH).
- Silk references overlapped. All designators moved to F.Fab, and the silkscreen carries free-standing connector and button labels placed clear of every courtyard.
- Neighbouring silk outlines touched; the courtyard gap rose to 0.15 mm.

The DRC also runs with `--schematic-parity`: 0 differences between board and schematic (footprints, nets, fields). Two parity faults were found and fixed. Sheet names containing "/" must appear as `{slash}` in board net names. The footprints also needed their MPN, Manufacturer and Description fields.

## 7. Sources read for this step

- **TI SLVSCF6F**, TPD1S514x (May 2019): ratings, OVP, timing, VBUS_POWER, application section 9, layout section 11, YZ0012 drawings 4221703/A.
- **TI SLVSAU0G**, TPD4S014 (December 2015): compared and rejected.
- **TI SBVS338H**, TPS7A20 (July 2024): ratings, accuracy, dropout, capacitors, active discharge and reverse current, DBV pinout, orderable list.
- **TI SLLSEN9F**, TUSB320: VBUS_DET resistor and ratings.
- **TI SLUSDV2C**, BQ25798: VBUS/VAC ratings, VAC_OVP options, PMID-VBUS limit, VBUS and PMID capacitor recommendations, pin descriptions of Q1 and Q3.
- **Nordic nRF52840 Product Specification** (docs.nordicsemi.com): absolute maximum ratings, recommended operating conditions, POWER chapter USB supply and VBUS detection, USBD electrical specification.
- **u-blox UBX-17056748 R15**, NINA-B3 system integration manual: 3.3.3 on-board antenna (B3x6), 3.4 supply.
- **JLCPCB** PCB capabilities page and controlled-impedance stack-up page.
- **DigiKey DE** pages for TPD1S514-1YZR, TPS7A2050PDBVR, GCM21BR71H105KA03L and GRM21BR71H105KA12L (the last is obsolete).
- **Earlier reviews**, for the TPS62162, LT3045 and ADS1299 layout notes. The LT3045 data sheet still could not be downloaded (ADI blocks automated access). The LT3045 Kelvin rules follow the Step 4 reading.

## 8. What routing (Step 15) must respect

1. **Freeze placement before routing.** `pcb_place.py` currently regenerates the whole board on every rebuild. Before the first track, switch it to update-from-netlist mode, or stop it from overwriting a routed board. Schematic UUIDs are already stable.
2. **USB pair.** Confirm the 90 Ω width with the JLCPCB calculator. Route USB_DP/USB_DM on F.Cu over unbroken In1 from J310 to module pads 54/55, about 27 mm, matched within 0.15 mm, with no vias if possible.
3. **VBUS_CON.** Keep it on the top layer and short between J310 and U323 (TI). Do not run unprotected traces beside protected ones.
4. **Electrode nets.** Route J500 to the ADC on F.Cu over In1 GND, symmetric per pair, at least 0.3 mm from other classes. No digital track may cross under the analogue zone on B.Cu.
5. **Converter loops.**
   - BQ25798: PMID and SYS capacitor returns straight to In1 with several vias at each GND pad; the SW1/SW2 copper as small as possible; BATP as a Kelvin trace from the pack side of Q400.
   - TPS62162: VIN-GND loop, SW-L240, and VOS sensed at the output capacitor.
6. **LT3045.** OUTS Kelvin at C203/C204; SET, CSET and RSET returned to the same ground point (Step 4).
7. **ADS1299.** One via per decoupling capacitor return, close to the pad. Keep CLK from Y340 short and away from the inputs. Keep DVDD/DGND and AVDD/AVSS returns on the single In1 plane (no split), as TI's EVM does.
8. **Trigger isolation.** No copper of any other net within 8 mm of the isolated side, on any layer. The rule areas and the 8 mm clearance and creepage rules enforce this.
9. **Antenna.** No tracks, vias or pours in the 8 × 3.1 mm cut-out (footprint keep-out). Keep In1 continuous ≥ 10 mm either side of the module.
10. **In2 planes.** Each needs vias to its pins; the isolated-copper warnings must then disappear. Stitch In1/In2 GND along the edges and around the barrier.
11. **Power I²C bus.** Below about 70 pF it can run at 400 kHz; otherwise 100 kHz (Step 13). Keep supervisor outputs ≤ 30 pF (Step 10).
12. **Physical checks.** Before release, compare the generated footprints 1:1 (D51), especially U323's WCSP and the GCT peg clearance.

## 9. Open risks

- **WCSP assembly.** U323 is a 0.4 mm WCSP with ganged mask openings and ENIG. Confirm with the assembler.
- **Thin margins.** U324 VIN is 10 mV inside its recommended maximum at the OVP ceiling. D312 leaks between 5.5 V and 6.15 V. Both arise only with non-compliant sources.
- **Assumed values.** The temperature drift of the OVP threshold and the hot RON are assumed. The TPD1S514 soft-start time is typical only. The 90 Ω width is an estimate.
- **C324 stock.** C324's MPN is on backorder at DigiKey; the KEMET alternative is in stock.
- **Placement is algorithmic.** It meets the stated rules but has not been reviewed by a second layout engineer. Expect local moves while routing.
- **Mechanical data still estimated.** BNC and connector heights and the BNC body-front position are taken from the footprint's F.Fab outline, not from Amphenol's drawing. The enclosure is not designed.
