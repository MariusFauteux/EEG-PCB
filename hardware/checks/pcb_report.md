# PCB placement and DRC (Rev C11, Step 14)

Board 110 x 85 mm, 375 parts and 4 mounting holes placed on the top side; no tracks.
KiCad 10.0.8 DRC: 499 unrouted connections (expected before routing), 30 other items, 30 accepted with a reason, 0 not accepted. Schematic parity: 0 differences.

## DRC items by type

| Type | Severity | Count |
|---|---|---:|
| silk_edge_clearance | warning | 26 |
| isolated_copper | warning | 4 |

## Accepted items

- 1 x `isolated_copper`: In2 +5VA plane has no via yet: it is joined to the LT3045 output and ADS1299 AVDD pins by vias in Step 15.
- 1 x `isolated_copper`: In2 GND fill has no via yet: stitched to In1 GND and the GND pads by vias in Step 15.
- 1 x `isolated_copper`: In2 +3V3 plane has no via yet: joined to the TPS62162 output and digital supply pins by vias in Step 15.
- 1 x `isolated_copper`: In2 SYS plane has no via yet: joined to the BQ25798 SYS pin and hold-up capacitors by vias in Step 15.
- 7 x `silk_edge_clearance`: J601: photodiode JST PH body overhangs the top edge by design; the fabricator clips legend at board edges and slots.
- 2 x `silk_edge_clearance`: U600: TLP2761 outline crosses the 8 x 1.2 mm isolation slot milled under the package (D36); the fabricator clips legend at board edges and slots.
- 3 x `silk_edge_clearance`: J600: BNC body front sits on the top edge; its outline continues over the panel bushing; the fabricator clips legend at board edges and slots.
- 7 x `silk_edge_clearance`: J401: pack JST PH body overhangs the bottom edge by design (mating face at the edge); the fabricator clips legend at board edges and slots.
- 7 x `silk_edge_clearance`: J301: interlock JST PH body overhangs the right edge by design; the fabricator clips legend at board edges and slots.

## Not accepted

- none

## Placement rules

- PASS Every IC supply pin has a GND-referenced capacitor pad on its net within 5 mm (0 exceptions: [])
- PASS NINA-B306 VCC/VCC_IO pads 9/10: nearest capacitor 3.0 mm (<= 4)
- PASS BQ25798 PMID 100 nF (C406) at pin 29: 2.51 mm to C406 (<= 3.0)
- PASS BQ25798 SYS 100 nF (C415) at pin 25: 2.51 mm to C415 (<= 3.0)
- PASS BQ25798 VBUS 100 nF (C402) at pins 2-3: 2.17 mm to C402 (<= 3.0)
- PASS TPS62162 VIN capacitor (C240) at pin 2: 2.45 mm to C240 (<= 3.0)
- PASS L400 to BQ25798 SW1 (pin 28): 5.07 mm (<= 6.0)
- PASS L400 to BQ25798 SW2 (pin 26): 5.07 mm (<= 6.0)
- PASS L240 to TPS62162 SW (pin 7): 3.83 mm (<= 4.0)
- PASS BATP sense R400 at the pack side of Q400 (Kelvin): 1.67 mm (<= 3.0)
- PASS RSET (R201) at the LT3045 SET pin: 2.41 mm (<= 4.0)
- PASS CSET (C201) at the LT3045 SET pin: 3.36 mm (<= 4.0)
- PASS LT3045 output capacitor C203 at OUT/OUTS: 2.56 mm (<= 5.0)
- PASS C324 at the TPD1S514 VBUS_CON balls: 2.58 mm (<= 3.0)
- PASS TPD1S514 within 8 mm of the J310 VBUS contacts: 7.04 mm (<= 8.0)
- PASS ADC clock oscillator within 12 mm of CLK (pin 37): 5.10 mm (<= 12.0)
- PASS 'Near ADC' series resistors and straps within 7 mm of their ADS1299 pins (worst R322 6.9 mm)
- PASS Differential 220 pF capacitors C1-C8 sit at the end of each channel network, nearest the ADC
- PASS Electrode inputs, REF/BIAS and ADS1299 parts inside the analogue zone ([])
- PASS Charger hot loop and TPS62162 at least 15 mm from the ADS1299 courtyard (15.4 mm, C412)
- PASS Charger hot loop and TPS62162 at least 10 mm from every analogue-front-end part (13.5 mm, C414 to C124)
- PASS Nothing but the isolated trigger parts inside the isolation area plus 8 mm barrier ([])
- PASS J600, R600 and D600 inside the isolated area
- PASS No connector, switch, inductor, bulk electrolytic, oscillator or mounting hole within 10 mm of the antenna ([])
- PASS NINA-B306 at the centre of the right edge (y 42.5 of 42.5), antenna pads 0.95 mm from the edge
- PASS J500 at the left edge (courtyard 3.25 mm from it)
- PASS J600 at the top edge (courtyard -21.17 mm from it)
- PASS J601 at the top edge (courtyard -0.48 mm from it)
- PASS J420 at the top edge (courtyard -0.10 mm from it)
- PASS J310 at the right edge (courtyard -0.47 mm from it)
- PASS J401 at the bottom edge (courtyard -0.48 mm from it)
- PASS J301 at the right edge (courtyard -0.48 mm from it)
- PASS Silkscreen warning and isolation labels placed clear of every part ((25.0, 82.0), (22.25, 14.0))

Parts placed outside their preferred region by the legaliser: C412, R321, R345, R346, R348, R349, R362, R363.
