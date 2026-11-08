# Step 13: pre-layout schematic review, exact BOM and footprint audit (Rev C10)

2026-11-08. Status: every fitted part has an exact manufacturer part number and a footprint whose pads match its symbol pins, checked by `hardware/scripts/check_footprints.py`. A whole-netlist corner review (`review_corners.py`) and a costed BOM (`bom_cost.py`) now run on every rebuild. Nothing has been built or measured, and no PCB layout exists. Rev C10 is a bench schematic candidate and is not released for fabrication or for connection to a person.

Step 13 closes README open items 8 (BOM and footprints) and 9 (microSD shell pads) at schematic and documentation level, and the footprint parts of items 3 (BQ25798 VQFN-HR) and 6 (CSD17381F4 YJC). Connectivity is unchanged from Rev C9 except for the exceptions listed in section 6; the changes are values, footprints, part numbers and BOM fields.

## 1. Summary

| | Rev C9 | Rev C10 |
|---|---:|---:|
| References in the BOM | 384 | 385 (J500 added) |
| Fitted parts | 384 (all marked FIT) | 360 fitted, 7 bare test pads, 18 off-board electrode leads |
| Fitted parts without a footprint | 36 | 0 |
| Fitted parts without an exact MPN | 296 | 0 |
| Unique MPNs | — | 81 (plus jumper shunts) |
| Project footprints | 0 | 5, generated into `hardware/EEG.pretty` |
| Netlist assertions | 408 | 441 |
| Parts cost, 5 boards (excl. VAT) | — | €937.64 (€187.53 per board) |

Findings (section 2) that changed the schematic: three resistor values that cannot be bought in the chosen precision series, four bulk capacitors with no confirmed effective capacitance at their rail voltage, a non-existent comparator part number, several Murata parts at end of life, two connectors whose KiCad 10 shell pads were left unconnected, the ship FET's exposed pads left unconnected by the stock footprint, and the absence of any electrode connector. One new open finding matters before layout: USB VBUS has no overvoltage cut-off (F01).

## 2. Findings

Severity: **High** = would produce a faulty board; **Medium** = a real risk or a procurement block; **Low** = margin, cost or documentation.

| # | Severity | Finding | Resolution |
|---|---|---|---|
| F01 | Medium | USB_5V has no overvoltage cut-off. The BQ25798 stops its converter at VAC_OVP (26 V default, SLUSDV2C) but D312 (TPD2E2U06, breakdown 6.5–8.5 V), U321's input divider (reaches the SN74LVC1G14 6.5 V absolute maximum at VBUS = 7.15 V) and the NINA-B306 VBUS pad (no limit stated in UBX-17052099) see the source directly. A compliant 5 V sink source never exceeds 5.5 V, but a faulty charger or a PD source that mis-negotiates would damage the board. | **Open (D54).** Add a VBUS overvoltage switch at J310 before layout; candidate parts not yet read. Service only, with electrodes disconnected, so no participant risk. |
| F02 | High | The KiCad 10 GCT USB4105 footprint names its four shell pads `SH`; the symbol pin was `S1`. The USB shield-to-GND connection would not have reached the PCB. Found by the new footprint audit. | Fixed: symbol pin renamed `SH`. |
| F03 | High | The same mismatch on the microSD socket (README item 9): pads `SH`, symbol pin 11. | Fixed: symbol pin renamed `SH`; `validate.py` asserts four `SH` pads on GND. |
| F04 | Medium | R201 50.5 kΩ, R210 32.0 kΩ (both E192) and R219 43.9 kΩ (in no E series) cannot be bought in the chosen 0.1 %, 10 ppm/K series: Panasonic ERA-3ARB is offered in E24/E96 from 1 kΩ to 100 kΩ, E192 only on request (ERA-A data sheet, 24-Apr-2024). | Fixed (D49): RSET = 49.9 k + 1.00 k (5.090 V), ANALOG_OK 31.6 k / 9.88 k, PACK_OK 44.2 k. All Step 10 rules still pass (section 4). |
| F05 | High | The stock `Package_SON:Texas_DQK` footprint numbers Q400's exposed drain and source pads 7 and 8. The symbol has no such pins, so the ship FET's main drain pad and its exposed source pad would have been left unconnected. | Fixed: project footprint from TI SLPS393A with the exposed pads numbered 1 (drain) and 4 (source). |
| F06 | Medium | C202 and C240 (10 µF 16 V 0805 on SYS, up to 8.6 V), C300 (10 µF 0805), C241 ("22 µF 10 V, effective value TBD") and C420 (22 µF 10 V 1206 "qualify DC bias") had no confirmed effective capacitance. A 0805 X7R at half its rating keeps well under half its value. | Fixed (D50): all 10 µF become GRM31CR71E106KA12L (1206, 25 V) and all 22 µF GRM32ER71E226KE15L (1210, 25 V), with effective values from Murata curves (section 4). |
| F07 | Low | Murata lists GRM21BR71H104KA01 (100 nF 0805), GRM188R71H104KA93 (100 nF 0603), GRM21BR71E105KA99 (1 µF 0805) and GRM188R71H473KA61 (47 nF) as "to be discontinued", and GRM1885C1H221JA01 (220 pF C0G) and GCM1885C1H150JA16 (15 pF) as NRND (pim.murata.com, read 2026-11-08). | Fixed (D48): Murata GCM automotive-grade equivalents, all "In Production"; generic 100 nF moved from 0805 to 0603; C610 15 pF moved to 0402 (GCM1555C1H150JA16, Murata's stated replacement). |
| F08 | Low | L400 was specified as XFL4020-102MEB. Coilcraft has retired the B packaging code ("change the last letter from B to C"). | Fixed: XFL4020-102MEC and XFL4020-222MEC. Isat (10 % drop) 4.5 A and 3.1 A, DCR max 11.9 and 23.5 mΩ (coilcraft.com). |
| F09 | Medium | U611 was specified as TLV7011IDCKR. TI's data sheet (SLVSDM5F) lists only TLV7011DCKR, DCKT, DBVR and DPWR; DigiKey has no match for the old code. | Fixed: TLV7011DCKR. SC70 pin-out (1 OUT, 2 VEE, 3 IN+, 4 IN−, 5 VCC) matches the symbol. |
| F10 | High | The 18 electrode symbols (J1–J16, JREF1, JBIAS1) had no footprint and no physical connector existed. | Fixed, provisionally (D52): one keyed 2 × 10 box header J500; the electrode symbols are marked off-board. |
| F11 | Medium | A BNC footprint has three shell pads; the 2-pin J600 symbol would have left two unconnected, and the shell is the isolated trigger return. | Fixed (D53): J600 uses a 4-pin BNC symbol with all shell pins on TRIG_ISO_RTN. |
| F12 | Low | R208 (100 Ω, 0.25 W) would dissipate 0.28 W if Q201 conducted while the LT3045 held +5VA up. Q202 and the LT3045 enable share ANA_ENABLE, so this needs a component fault; the clamp is transient by design. | Open, accepted. A 0.5 W 1206 or 2010 part would remove it; revisit in layout. |
| F13 | Medium | Pulse rating of the electrode-input, REF and BIAS resistors (flagged in Steps 7, 8 and 12). | Partly closed (D48): ERJ-PB6B, 0.1 % thick film, 150 V limiting element voltage, 200 V overload, 0.25 W. Panasonic markets the series as anti-surge, but the data sheet read (Feb. 2016) gives no pulse curve. ESD and surge qualification on the assembled board remains open. |
| F14 | Low | BUCK_PG (TPS62162 power-good, open drain with R240 pull-up) is read by nothing. | Open, accepted: DIGITAL_OK supervises the rail. Add a test pad in layout if wanted. |
| F15 | Low | CNC Tech 3220-10-0300-00 (SWD header) is an SMD part, but J300 used a through-hole footprint. | Fixed: `PinHeader_2x05_P1.27mm_Vertical_SMD`. The shroud is larger than the courtyard (physical check). |
| F16 | Low | C201 (CSET, 4.7 µF 16 V 0805) keeps 3.2 µF typical, 2.4 µF worst case at 5.09 V; C409 (REGN) 3.2 µF at 5.0 V. The LT3045 noise corner and soft-start time move up by about 1.5×. | Open, accepted. A 1206 25 V part would restore the value; revisit with the bench noise measurement. |
| F17 | Medium | Courtyards alone fill 68 % of one side of the 100 × 70 mm target. | Open (D55): see section 7. |
| F18 | Medium | A 2S cylindrical pack (≈ 18.5 mm cells) cannot sit under the board inside 30 mm with 11–12.5 mm parts on top. | Open (D55): pack beside the board or a flat pack. |
| F19 | Info | I²C at 400 kHz meets the 300 ns rise time only up to about 70 pF of bus capacitance with the single 4.7 kΩ pull-ups. | Firmware note: use 100 kHz unless the layout keeps the bus short. |
| F20 | Info | Data not re-read: the LT3045 data sheet (Analog Devices blocks automated download); no VBUS absolute maximum in the NINA-B3 data sheet. | Recorded as assumptions; LT3045 footprint and pin map rest on the Step 4 reading. |

## 3. Part selection (D48)

Families were chosen so that a prototype order needs few lines and every price break is shared. Values from the earlier design reviews were kept except where a datasheet showed a problem (F04, F06, F09).

| Use | Series | Key ratings checked | Source |
|---|---|---|---|
| General resistors, 0603 | Panasonic ERJ-3EKF (1 %), ERJ-3GEY0R00V (0 Ω) | 0.1 W, 75 V, ±100 ppm/K | DigiKey product data, 2026-11-08 |
| 1206 resistors (R208, R600) | Panasonic ERJ-8ENF (1 %) | 0.25 W | Not separately read; ratings as series standard (estimate) |
| 0.1 % precision, supervisor dividers and RSET | Panasonic ERA-3ARB (±10 ppm/K), ERA-3AEB1403V for 140 k (±25 ppm/K, R203 is not threshold-critical) | 0.1 W, 75 V, 1 k–100 k E24/E96 | Panasonic ERA-A data sheet, 24-Apr-2024 |
| Electrode, REF and BIAS networks, BIAS feedback (0805, 0.1 %) | Panasonic ERJ-PB6B | 0.25 W at 70 °C, 150 V element, 200 V overload, ±50 ppm/K, 200 Ω–1 MΩ E24/E96 | Panasonic ERJ-PB3/PB6 data sheet, Feb. 2016 |
| Small MLCC (0402/0603/0805) | Murata GCM (C0G and X7R, 50 V or 25 V) | All "In Production" | pim.murata.com, 2026-11-08 |
| Bulk MLCC | Murata GRM31CR71E106KA12L (10 µF 1206 25 V), GRM32ER71E226KE15L (22 µF 1210 25 V), GRM21BR71C475KE51L (4.7 µF 0805 16 V) | In production; DC-bias curves read | pim.murata.com |
| Inductors | Coilcraft XFL4020-102MEC, -222MEC | Isat 4.5 A / 3.1 A at 10 % drop | coilcraft.com |

The electrode-input resistors move from an unspecified 0.1 % part to thick film because thin-film chips handle pulses poorly and have a lower element voltage (ERA-6A: 100 V). The ±50 ppm/K TCR is acceptable there: the 0.1 % matters only for matching between legs of one channel, and both legs sit side by side. At 100 V between two electrodes (the Step 12 stimulator case) each 47 kΩ sees ≈ 25 V and 13 mW.

Connectors and other parts without a previous choice (provisional, D52 and D53):

| Ref | Part | Note |
|---|---|---|
| J500 | Würth 61202021621, 2 × 10 box header 2.54 mm, keyed | Electrode harness: pins 1–16 CH1+ to CH8− (odd +, even −), 17 REF, 18 BIAS, 19–20 unused. No GND or supply on the electrode connector. |
| J600 | Amphenol RF 031-6575, right-angle PCB BNC | Body and pegs carry the isolated return; keep 8 mm to all other copper. |
| J301, J601 | JST S2B-PH-K-S | Interlock switch lead and photodiode lead |
| J300 | CNC Tech 3220-10-0300-00 (SMD, 1.27 mm, shrouded) | SWD |
| JP1–JP8 | Würth 61300311121 + shunt 60900213421 (not on the schematic) | REF selection |
| SW300–SW302 | E-Switch TL3342F160QG | Same as SW400 |
| D600 | Diodes Inc. 1N4148WS-7-F | |
| C116 | KEMET T491D107K010AT | 100 µF 10 V tantalum, case D; price read, data sheet not read |
| Q401 | onsemi BSS138 | |

The SiTime oscillator code SIT8008BIF11-33E-2.048000 is listed as active at DigiKey, which settles the D35 ordering-code question. The test points TP230 and TP420–TP425 are bare copper pads and are excluded from the BOM.

The full part list with manufacturer, MPN, description and population is `hardware/bom.csv`; the costed lines are in `hardware/bom_cost.csv`.

## 4. Corner and transient review

`review_corners.py` checks the whole netlist on every rebuild (26 rules, all passing):

- **Floating inputs.** No input pin shares a net only with other inputs or sits on an unconnected pin.
- **Decoupling.** Every IC and oscillator supply pin has a capacitor to GND on its net.
- **Capacitor ratings.** Every capacitor's rated voltage exceeds the highest steady voltage on its nets (SYS 8.6 V, pack 8.4 V, VBUS and PMID 5.5 V, REGN 5.2 V, +5VA 5.25 V, +3V3 3.6 V). None is below 1.5 × its working voltage.
- **I²C.** TUSB320LAI 0x47 (ADDR = GND), MCP4725A0 0x60 (A0 = GND), BQ25798 0x6B: no conflict. One 4.7 kΩ pull-up per line to +3V3, 0.62 mA at 0.4 V. All three devices tolerate the bus at 3.3 V (TUSB320 SDA/SCL absolute maximum VDD + 0.3 V).
- **Pin voltages at SYS 8.6 V.** Supervisor SENSE pins 1.46–1.71 V (TPS3890 recommended ≤ 5.5 V, absolute 7 V); TPS62162 VIN and EN at 8.6 V (VIN recommended ≤ 17 V, EN ≤ VIN + 0.3 V). At VBUS 5.5 V the USB-sense inverter input is 5.0 V (≤ 5.5 V). Above 5.5 V see F01.

DC-bias effective capacitance, from Murata 25 °C curves, with −10 % tolerance and −15 % X7R temperature change for the worst case:

| Bank | Requirement | Typical | Worst case |
|---|---|---:|---:|
| C203 + C204 at 5.25 V | LT3045 ≥ 10 µF | 34.0 µF | 26.0 µF |
| C121 at 4.5 V | ≥ 10 µF (ADS1299 sheet note) | 18.4 µF | 14.1 µF |
| C410–C414 at 8.4 V (−46.7 %) | — | 58.6 µF | 44.9 µF |
| SYS total with OS-CON (−20 %) | Step 10: 24 µF average, 127 µF peak | 138.6 µF | 124.8 µF |
| C417 + C418 at 8.4 V | TI C_BAT ≥ 3 µF effective | 10.1 µF | 7.7 µF |
| C400 + C321 at 5.0 V | USB Type-C sink ≤ 10 µF | 8.7 µF | — |

This replaces the Step 11 assumption of 40 % retention at 8.4 V with Murata's −46.7 % (53 % retention); the SYS hold-up now meets the peak-load target typically and the average-load target five times over in the worst case. It closes the "read DC-bias curves" items for C203/C204 (D41) and SYS (D45) at datasheet level; temperature behaviour of the real parts still needs the bench.

**Rail thresholds after F04.**

| | Rev C9 | Rev C10 |
|---|---:|---:|
| +5VA nominal (RSET) | 5.088 V (50.5 k + 383 Ω) | 5.090 V (49.9 k + 1.00 k) |
| +5VA envelope | 4.972–5.202 V | 4.974–5.204 V |
| Release margin (rail min − ANALOG_OK release max) | 45.9 mV | 49.6 mV |
| Below the 5.25 V ADC ceiling | 47.6 mV | 45.8 mV |
| ANALOG_OK assertion min above 4.75 V | 14.0 mV | 12.2 mV |
| ANALOG_OK nominal assertion | 4.830 V (32.0 k / 10 k) | 4.828 V (31.6 k / 9.88 k) |
| PACK_OK nominal assertion | 6.1985 V (43.9 k) | 6.233 V (44.2 k), 6.146–6.320 V; BAT_WARN_OK minimum 6.520 V |

**Dissipation.** LT3045 at SYS 8.4 V and the 50 mA budget: 0.17 W (≈ 6 °C at an assumed 34 °C/W). BQ25798 charging at 0.5 A into 8.4 V with an assumed 90 % efficiency: 0.47 W, ≈ 21 °C junction rise at the data-sheet 44.2 °C/W. Q400 at 0.5 A: 7 mW. All resistors stay below half their rating in normal operation; R208 is the exception only under a fault (F12).

## 5. Footprints (D51)

`check_footprints.py` loads every assigned footprint (KiCad 10 stock library or `hardware/EEG.pretty`) and requires that every symbol pin has a pad and every numbered pad belongs to a symbol pin, so that no shell or exposed pad is left floating. It passes for all 367 on-board parts on 40 footprints. It also checks project footprints for overlapping pads.

Project footprints are generated by `hardware/scripts/footprints.py` into `hardware/EEG.pretty`, registered in `hardware/fp-lib-table`:

| Footprint | Part | Source drawing | Notes |
|---|---|---|---|
| `Texas_RQM0029A_VQFN-HR-29_4x4mm` | BQ25798 (U400) | TI SLUSDV2C, RQM0029A outline and example board layout 4225253/A | 29 leads, 0.2 mm lands at 0.4/0.45 mm pitch; corner leads 1, 9, 16 and 24 are L-shaped (two overlapping rectangles); right-side lands 17–19 are 0.70/0.65/0.675 mm long as drawn |
| `Texas_RWB0012A_X2QFN-12_1.6x1.6mm_P0.4mm` | TUSB320LAI (U320) | TI SLLSEN9F, 4221631/B | KiCad has no RWB footprint |
| `Texas_YJC0003A_FemtoFET-3_1.0x0.6mm` | CSD17381F4 (Q201, Q202) | TI SLPS411G §7.1–7.3, 4220651/B | Solder-mask-defined: copper 0.05 mm beyond the 0.25 × 0.15 and 0.25 × 0.5 mm openings; separate paste apertures per §7.3. Pin 1 G, 2 S, 3 D from the top-view figure |
| `Texas_DQK_SON-6_2x2mm_CSD17571Q2` | CSD17571Q2 (Q400) | TI SLPS393A §7.1.1 | Exposed drain pad 1.1 × 1.05 mm numbered 1, exposed source pad 0.85 × 0.4 mm numbered 4 (F05) |
| `u-blox_NINA-B306` | NINA-B306 (U300) | UBX-17052099 R15 Table 28, Figures 4, 15, 16; UBX-17056748 R15 §3.8 and Figure 14 | 55 signal pads, 12 EGP and 4 EAGP ground pads; NSMD with mask 0.05 mm larger per side and paste equal to copper; 8 × 3.1 mm copper keep-out under the antenna on all layers |

The NINA land pattern was built from the bottom-view mechanical drawing and mirrored into the top view: pin 1 is 1.80 mm from the short edge and 0.875 mm from the long edge, the outer row (47–55) sits 1.15 mm above pin 1, the antenna ground pads at 10.0 and 12.55 mm from pin 1. The result matches the pin-assignment figure (Figure 4) row for row. The integration manual also requires: module centred on a board edge with the antenna facing out, ground plane extending ≥ 10 mm either side, solid ground under the module except the cut-out, and no tall metal parts within 10 mm of the antenna.

Stock footprints checked against package data read for this step: TPS389001 DSE (TI SLVSD65A land: lands 0.25 × 0.7 mm, pin 1 0.8 mm; the stock `WSON-6_1.5x1.5mm_P0.5mm` uses 0.28 × 0.75/0.85 mm, within 0.05 mm); USB-C and microSD shell pads (F02, F03); BNC shell pads (F11). The LT3045 DD package uses the stock `DFN-10-1EP_3x3mm_P0.5mm_EP1.65x2.38mm` (pad 11 = exposed GND pad), not re-read (F20).

**Needs a physical or 3D check before release:** all five project footprints (print 1:1 or compare with parts; the NINA pattern with a module or the EVK Gerbers); J600 (drawing and isolation spacing); J500 (pin 1 and key orientation); J300 (shroud outline); C416 (16SVP100M is 10 mm × 8.0 mm per DigiKey, matching `CP_Elec_10x7.9`); the LT3045 footprint against a current ADI drawing.

## 6. Schematic changes and the connectivity check

`validate.py` now compares against `baseline/step12_netlist.xml` and asserts that connectivity is unchanged except:

| Change | Why |
|---|---|
| J500 added (20 pins on the 16 electrode nets, REF_RAW and BIAS_ELEC; 19–20 unconnected) | F10 |
| J600 pins 3 and 4 added, on TRIG_ISO_RTN | F11 |
| J420 pin 11 → SH, J310 pin S1 → SH (compared under their new names) | F02, F03 |
| Electrode symbols J1–J16, JREF1, JBIAS1 marked off-board and out of the BOM; TP230, TP420–TP425 out of the BOM | Population |

All 1082 retained pin connections keep their net membership. Value changes are limited to R201, R207, R210, R211, R219 (F04), C202, C240, C300, C241, C420 (F06), C610 (F07), U611 (F09) and the J600 label. Footprint changes: generic 100 nF 0805 → 0603, CFB1 and C422 → 0603, C610 → 0402, the F06 capacitors, J300 → SMD, and the 36 parts that had none.

## 7. Mechanical fit (D55)

Courtyards sum to 4743 mm², 68 % of one side of 100 × 70 mm. The largest items are J600 (573 mm², of which part is the bayonet beyond the board edge), J500 (337 mm²), the microSD socket (278 mm²), the ADS1299 (177 mm²), the NINA-B306 (163 mm²) and the OS-CON (147 mm²). Resistors and capacitors together take 1680 mm².

Courtyards do not include routing, the 8 mm isolation band around the trigger input, the NINA antenna edge and its ground-plane margin, or mounting holes. Mixed-signal boards typically need 1.5–2 × the courtyard area, i.e. 7100–9500 mm², more than one side of 7000 mm². Two workable routes: passives on the bottom side (one more assembly side, ≈ 1700 mm² moved), or a board near 110 × 85 mm. The decision belongs to the layout step.

| Ref | Height (mm) | Basis |
|---|---:|---|
| J600 BNC | ≈ 12.5 | estimate; confirm from Amphenol drawing |
| JP1–JP8 with shunts | ≈ 11 | estimate |
| J500 box header | ≈ 8.9 | estimate |
| C416 OS-CON | 8.0 | DigiKey (16SVP100M) |
| J301, J401, J601 (JST PH, right angle) | ≈ 6 | estimate |
| J300 | ≈ 5 | estimate |

All are well below 30 mm on their own. The 30 mm envelope is set by the stack: 1.6 mm board, ≈ 12.5 mm parts and an 18.5 mm cylindrical 2S pack do not fit on top of each other, so the pack must sit beside the board or be a flat pouch pack (F18). The BNC, OS-CON and USB shell are metal and must stay ≥ 10 mm from the NINA antenna.

## 8. Cost at prototype quantity

Parts only for 5 boards, EUR excluding VAT, prices read on DigiKey Germany and coilcraft.com on 2026-11-08 (`hardware/bom_cost.csv`, `hardware/checks/bom_cost.md`):

| | EUR |
|---|---:|
| Total, 5 boards | 937.64 |
| Per board | 187.53 (≈ 223 with 19 % VAT) |
| Prices read for the exact MPN | 824.91 (88 %) |
| Same series, other value ("family") | 76.62 (8 %) |
| Not read ("estimate"): ERJ-8ENF, ERJ-3GEY0R00V, GCM21BR71E105KA56L, GRM31CR71E106KA12L, GRM21BR71C475KE51L, GRM31C5C1H104JA01L, TLV7011DCKR, jumper shunts | 36.10 (4 %) |

The ADS1299 is 42 % of the parts cost (€78.63 each at 1–9). NINA-B306-00B was listed at €8.81, lower than expected for the module; confirm before ordering. Not included: PCB fabrication, assembly, enclosure, microSD card, pack, electrode harness and shipping. On these figures the D15 budget of €500 per unit leaves ≈ €275 for the board, assembly and enclosure.

## 9. Verification

- `hardware/rebuild.sh`: 441 netlist assertions pass (408 at Step 12); KiCad 10.0.8 ERC 0 errors, 0 warnings; footprint audit passes; 26 of 26 corner rules pass; input, backfeed, BIAS, timing and power analyses pass; host tests pass.
- New assertions cover the Step 13 connectivity exceptions, J500 pin allocation, the off-board and bare-pad populations, an MPN, manufacturer and description on every fitted part, the ERJ-PB6B family on every electrode-path resistor, the absence of NRND Murata parts, the F04 values and the project footprints.
- The changed sheets (`ref_bias`, `storage`, `usb_c`, `event_inputs`, `analog`, `supervision`, `controller`) were exported with `kicad-cli sch export pdf` and inspected.

**Not done and still required.** VBUS overvoltage protection (F01); physical checks listed in section 5; ESD and surge tests of the input network (F13); a decision on board area and pack position (D55); confirmation of the estimated prices and heights.

## Sources

Read for this step unless stated:

- TI BQ25798, SLUSDV2C (rev. June 2026): RQM0029A package outline and board layout, pin functions, VAC_OVP thresholds and default, RθJA, C_BAT minimum.
- TI TUSB320, SLLSEN9F: RWB0012A board layout, pin functions, absolute maximum ratings.
- TI CSD17381F4, SLPS411G: mechanical dimensions, recommended land and stencil, top-view pin-out.
- TI CSD17571Q2, SLPS393A: recommended PCB pattern, top-view pin-out with exposed D and S pads.
- TI TPS3890, SLVSD65A: DSE pin-out, land pattern, SENSE and VDD limits.
- TI TPD2E2U06, SLLSEG9C: VRWM 5.5 V, breakdown 6.5–8.5 V.
- TI SN74LVC1G14 data sheet: input absolute maximum 6.5 V. TI TPS62162 data sheet: VIN and EN limits. TI TLV7011, SLVSDM5F: orderable codes and SC70 pin-out.
- u-blox NINA-B3 data sheet, UBX-17052099 R15: Table 28, Figures 4, 15, 16, absolute maximum ratings. NINA-B3 system integration manual, UBX-17056748 R15: §3.8, antenna placement and Figure 14.
- Panasonic ERA-A thin-film chip resistors (24-Apr-2024) and ERJ-PB3/PB6 high-precision thick-film chip resistors (Feb. 2016).
- Murata product pages (pim.murata.com), 2026-11-08: status and DC-bias curves for GRM31CR71E106KA12, GRM32ER71E226KE15, GRM21BR71C475KE51, GCM21BR71E105KA56; status of the GRM and GCM parts in F07.
- Coilcraft XFL4020 product page, 2026-11-08: ratings and ordering codes.
- DigiKey Germany product and search pages, 2026-11-08: prices, status, 16SVP100M size, 3220-10-0300-00 mounting type.
- ADI LT3045: not re-read (download blocked); see the Step 4 review.
