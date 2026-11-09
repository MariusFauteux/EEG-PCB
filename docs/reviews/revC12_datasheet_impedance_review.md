# Rev C12: datasheet review of the EEG signal path and electrode impedance test links

Date: 2026-11-09 • Revision: C11 → C12 • Status: drawn, placed and checked by script; nothing built or measured

## 1. Scope

The electrode signal path was checked pin by pin against the manufacturers' data sheets, for the purpose of low-noise EEG and electrode impedance capture. It covers the ADS1299 and its supply, reference and clock pins, the electrode input networks, the REF buffer and the BIAS drive. The power, USB, controller, storage and trigger sheets were not part of this review.

| Part | Source read | Result |
|---|---|---|
| ADS1299IPAGR | TI SBAS499C (January 2017) | All 64 pins match the pin table and section 10.1.1 |
| OPA376AIDBVR | TI SBOS406G (December 2015) | Pinout, supply, input range and capacitive load within limits |
| TPD2E2U06DCKR | TI SLLSEG9C | Pinout, working voltage, capacitance and leakage as recorded in Step 7 |
| LT3045 | Not read: the Analog Devices download was blocked again | Values agree with the limits recorded in the Step 4 review; DFN-10 pinout still to confirm against the data sheet |

## 2. ADS1299 against SBAS499C

| Pin or item | Data sheet | Design | Result |
|---|---|---|---|
| VCAP1 (28) | 100 µF to AVSS | C116 100 µF tantalum | Pass |
| VCAP2 (30), VCAP4 (26) | 1 µF to AVSS | C117, C120 1 µF | Pass |
| VCAP3 (55) | 1 µF ∥ 0.1 µF to AVSS | C118 1 µF + C119 100 nF | Pass |
| VREFP (24) | ≥ 10 µF to VREFN | C121 22 µF (14 µF effective at 4.5 V, D50) + C122 100 nF | Pass |
| VREFN (25) | Negative reference | GND (AVSS) | Pass |
| AVDD1 (54), AVDD (59) | 1 µF to AVSS1 / to AVSS pin 58 | 1 µF + 100 nF pairs on every AVDD pin; placement at the pin is a layout matter | Pass (layout) |
| DVDD (48, 50) | 1 µF to DGND | C112–C115 | Pass |
| RESV1 (31) | Connect directly to DGND | GND | Pass |
| NC (27, 29), Reserved (64) | Leave open | Open | Pass |
| CLKSEL, GPIO1–4, DAISY_IN | Two-state pins through ≥ 10 kΩ; unused GPIO to DGND through ≥ 10 kΩ | 10 kΩ to GND | Pass |
| SRB1, SRB2 | May float if unused | Open | Pass |
| BIASIN | May float or tie to AVSS if unused | GND | Pass |
| BIASREF | Tie to AVSS or float if unused; BIASREF_INT selects internal (AVDD + AVSS)/2 | GND; firmware sets BIASREF_INT = 1 | Pass (firmware rule kept) |
| AVDD – AVSS | 4.75–5.25 V | 5.090 V nominal (D49) | Pass |
| External fCLK | 1.5–2.25 MHz | 2.048 MHz ±20 ppm | Pass |
| Input current | ≤ 10 mA continuous beyond the rails | 4.7 kΩ after the TVS node | Pass |

**Power-up order (minor).** SBAS499C section 11.1 asks for the clock to start once the supplies are stable, and for the reset after tPOR and once VCAP1 exceeds 1.1 V. Y340's OE is pulled to +3V3_ADC, so the clock runs before AVDD exists. DVDD is present, so no absolute maximum is exceeded, and the hardware holds RESET low until ANALOG_OK. Firmware must therefore reset the ADC only after AVDD is good and VCAP1 has charged. Gating Y340 OE from ANA_ENABLE would follow the data sheet literally. Not changed.

## 3. OPA376 and TPD2E2U06

- OPA376: SOT-23-5 pins 1 OUT, 2 V−, 3 +IN, 4 −IN, 5 V+ match U500. 5.09 V is inside the 2.2–5.5 V supply range. The body sits near mid-supply (≈ 2.55 V), below (V+) − 1.3 V = 3.79 V, so the input stays in the region where TI specifies 76 dB minimum CMRR. TI allows up to 250 pF of pure capacitive load at unity gain; every REF_BUF branch is isolated by 98.7 kΩ, leaving only track and jumper capacitance.
- TPD2E2U06 (DCK): pins 1 IO1, 2 IO2, 3 GND match D501–D510. VRWM 5.5 V is above AVDD. Line capacitance 1.5 pF typical, leakage 10 nA maximum at 2.5 V.

## 4. Noise floor

SBAS499C Table 1 gives 0.32 µV rms at gain 12 and 0.28 µV rms at gain 24 (1 kSPS, 262 Hz bandwidth); scaled to 100 Hz as white noise this is ≈ 0.2 µV and ≈ 0.17 µV. The thermal noise of the 2 × 98.7 kΩ series resistance is ≈ 0.57 µV rms over 0.1–100 Hz (Step 7), so the protection resistors, not the ADC, set the board's own floor. This is the accepted trade for limiting fault current to ≈ 51 µA at 5 V. Halving them would save ≈ 0.17 µV, which is small next to the thermal noise of 100 kΩ-class electrodes. Not changed. Gain 12 costs only ≈ 0.04 µV rms against gain 24.

## 5. Electrode impedance: finding and change

**Finding.** SBAS499C section 9.3.2.4.3 applies lead-off excitation at the INxP and INxN pins only. In Rev C11 the REF electrode reached nothing but the OPA376 input, and the BIAS electrode reached nothing but RB2; neither impedance could be measured. A channel's negative input on REF_BUF sends its lead-off current into the buffer output, not the electrode. BIASIN could be digitised through the input multiplexer but cannot be excited by the lead-off sources, so wiring BIASIN to the BIAS electrode would not give an impedance either.

**Change (D61).** Two normally open 2-pin links on the electrode side of the networks:

| Link | Joins | Use |
|---|---|---|
| JP9 | REF_RAW (J500 pin 17) to E8N (J500 pin 16, JP8 pin 1) | JP8 at 1–2, no CH8− electrode on the harness: the REF electrode becomes CH8− through CH8's own 94 kΩ / clamp / 4.7 kΩ |
| JP10 | BIAS_ELEC (J500 pin 18) to E7N (J500 pin 14, JP7 pin 1) | JP7 at 1–2, no CH7− electrode on the harness: the BIAS electrode becomes CH7− through CH7's own network |

Every shunt combination was checked. No combination connects REF_RAW to REF_BUF or bypasses a 94 kΩ network; the worst misuse (a link fitted with a CH7− or CH8− electrode still on the harness) shorts two electrode leads together, which spoils that measurement but adds no current path. With JP10 fitted and JP7 at 2–3, a CH7− electrode on the harness would become a second BIAS electrode, still behind 998 kΩ. The REF electrode with JP9 fitted carries one more leg of leakage (≤ 10 nA) while the link is in place.

The links sit beside the REF and BIAS networks above J500 (placement.json: JP9 at 9.5, 32.7 mm; JP10 at 5.75, 32.7 mm). The E7N and E8N stubs to them are electrode-side nets; keep them short and inside the analogue guard when routing.

## 6. Measurement procedure (firmware and bench)

1. Use AC lead-off at 7.8 Hz or 31.2 Hz (FLEAD_OFF = 01 or 10), not fDR/4. At 250 Hz the 220 pF differential capacitor is ≈ 2.9 MΩ across the pair, an error of tens of percent with 1 MΩ-class dry or PEDOT:PSS electrodes; at 31.2 Hz it is ≈ 23 MΩ.
2. Use 6 nA or 24 nA only. 6 µA × 98.7 kΩ = 0.59 V and 24 µA would leave the input range. Treat the DC comparators as unreliable: TVS leakage (up to 10 nA) is as large as the 6 nA source.
3. Subtract the fixed series resistance: 98.7 kΩ per excited leg (0.1 % parts). TI gives the source accuracy as ±20 %; calibrate each channel against known resistors on an electrode simulator.
4. Referential channels and REF (JP9): run the BIAS loop, excite one leg at a time, and remove the excited channel from BIAS_SENSP/N. Otherwise the loop senses the excitation as common mode and partly cancels it. This follows from the loop topology; it is not stated in the data sheet and must be confirmed on the bench.
5. BIAS (JP10): power the BIAS amplifier down and measure CH7 as a bipolar pair with lead-off on both legs. The result is Z(E7P) + Z(BIAS) + 197.4 kΩ; separate the two with a second pair that includes E7P (three-electrode method).
6. Remove JP9 and JP10 and restore JP7/JP8 before recording.

## 7. Evidence

`hardware/rebuild.sh`, 2026-11-09: 486 netlist assertions (477 at Step 14), including a comparison with the Step 14 netlist (`hardware/baseline/step14_netlist.xml`) showing that only JP9 and JP10 were added, that every Step 14 net keeps exactly its members, and that the links join only REF_RAW, E8N, BIAS_ELEC and E7N. ERC 0 errors, 0 warnings. Footprint audit passes for 377 parts. Board DRC: schematic parity 0 differences, 30 accepted items, 0 not accepted, 33 of 33 placement rules. All OVP, corner, input, backfeed and power rules unchanged and passing.

## 8. Still open

- LT3045 DFN-10 pinout and limits against the Analog Devices data sheet (the PDF needs to be added to the project by hand).
- Datasheet review of the remaining sheets (charger, buck, USB and OVP, supervisors, controller, microSD, trigger), including whether the TPS62162 enters a light-load burst mode whose ripple falls in the EEG band.
- Bench confirmation of the impedance procedure in section 6.
