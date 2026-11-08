# Step 7 — electrode inputs and filtering

2026-11-08 · Rev C4 · Bench schematic candidate, not released for fabrication or human connection.

## Implemented

All 16 input legs now use electrode → 47 kΩ → 47 kΩ → TVS node → 4.7 kΩ → ADS1299 input. D501–D508 are TPD2E2U06DCKR, with pins 1/2 on the two clamp nodes and pin 3 at GND. R501–R516 are the added 4.7 kΩ resistors. Each channel retains a 220 pF differential capacitor (C0G, 5%, 50 V). Resistors are 0.1%, 0805; pulse-rated exact parts remain to be selected. Two four-channel sheets replace the original input sheet, with a separate reference/BIAS sheet. No extra common-mode capacitors were added.

JP1–JP8 retain 1–2 bipolar / 2–3 shared REF selection. Fit only one shunt and change it with board power off. REF_RAW is an electrode signal, not ground or the ADC voltage-reference output. Every selected REF branch traverses its own input protection network. BIAS feedback and its two 499 kΩ series resistors are unchanged; Step 8 owns their validation.

## Manufacturer evidence checked online

- [TI ADS1299 datasheet, Rev C](https://www.ti.com/lit/ds/symlink/ads1299.pdf), absolute maximum ratings, electrical characteristics, digital filter and input common-mode sections: input absolute range AVSS−0.3 V to AVDD+0.3 V; outside-rail input current must be limited to 10 mA. This absolute limit is neither a normal operating allowance nor a participant current limit. Input bias 300 pA and input capacitance 20 pF are typical. The sinc³ response repeats at the modulator rate; at a 2.048 MHz clock, fMOD is 1.024 MHz. Common-mode and differential headroom must both be respected.
- [TI TPD2E2U06 datasheet, Rev C](https://www.ti.com/lit/ds/symlink/tpd2e2u06.pdf), pin configuration and electrical characteristics: DCK pins 1/2 I/O, 3 GND; recommended I/O 0–5.5 V. Leakage is 10 nA maximum **at 2.5 V**. Capacitance is 1.5 pF typical/1.9 pF maximum at the specified 2.5 V, 1 MHz, 25°C test condition. The 12.4 V clamp value at 5 A TLP is **typical**, not a guaranteed maximum. Component ESD ratings do not establish board-level immunity.
- [Nexperia PESD5V0U1UA/UB/UL datasheet](https://assets.nexperia.com/documents/data-sheet/PESD5V0U1UA_UB_UL.pdf), characteristics: headline 1 nA leakage is typical; guaranteed maximum is 100 nA at 5 V, 25°C. Not selected. These test voltages differ from the TI part, so this is not a direct equal-bias comparison.

## Quantitative design rationale

The TVS is deliberately after 94 kΩ, retaining series impedance between electrodes and a possible ground-shunt fault. The final 4.7 kΩ reduces current into ADC internal clamps when the external clamp voltage exceeds the ADC rails. This is a candidate protection arrangement, not demonstrated ESD or sustained overvoltage survival.

For independent differential inputs, the simple pole is f = 1/[2π(197.4 kΩ + ZP + ZN) Cdiff]. This ignores input/TVS capacitance and electrode phase; the supplied linear nodal model includes approximate shunt capacitances.

| Resistance of each electrode | Simple pole with 220 pF | Analog gain at 100 Hz |
|---|---:|---:|
| 0 | 3665 Hz | −0.0032 dB |
| 10 kΩ | 3328 Hz | −0.0039 dB |
| 100 kΩ | 1820 Hz | −0.0131 dB |
| 1 MΩ | 329 Hz | −0.3833 dB |

This is an RF/input filter, not a 100 Hz brick-wall anti-alias filter. The ADC sinc³ alone gives −0.430 dB at 100 Hz and −11.77 dB at 500 Hz at 1 kSPS. At fMOD + 100 Hz its response repeats at −0.430 dB, so the external network and layout must reject high-frequency interference. The ideal 220 pF RC contributes about −48.9 dB at fMOD with zero electrode impedance; parasitic bypass and common-mode interference can invalidate that estimate. A 0.1% resistor and 5% capacitor tolerance gives approximately −4.86%/+5.37% pole variation before electrode effects. No measured alias rejection is claimed.

Using sqrt(4 k T R B), 300 K and a rectangular 0.1–100 Hz bandwidth, resistor-only differential noise rises from 0.558 to 0.572 µV RMS (+2.47%). This excludes electrodes, ADC, TVS noise, digital weighting and alias folding. TVS low-frequency noise is not specified and must be measured.

### Shared reference is a material limitation

With eight channels using one 100 kΩ reference electrode, 100 kΩ positive electrodes, ideal sources, 20 pF assumed per ADC pin and 1.5 pF per TVS pin, a signal on one channel couples into another at approximately −57.2/−43.2/−37.3 dB at 10/50/100 Hz. This is electrical reference coupling, not physiological correlation. Increasing Cdiff to 470 pF worsens the 100 Hz result to −31.0 dB. Therefore the original 220 pF is retained. The 20 pF per-pin interpretation is a modeling approximation, not a validated input equivalent circuit. Resistive electrodes are also an approximation.

At 50 Hz, a 10 kΩ versus 100 kΩ source imbalance converts common mode to differential at about −64.3 dB in the same model, before intrinsic ADC CMRR, capacitance mismatch or layout effects. Do not infer assembled-system CMRR from the ADC specification. Measure actual electrode impedances, cable capacitance and REF loading. For comparisons requiring independently measured signals, evaluate bipolar selection or redesign the reference distribution before finalizing the architecture.

### Leakage and offset

At the specified 2.5 V test point, 10 nA through 94 kΩ + a 100 kΩ electrode gives 1.94 mV per-leg input shift; a conservative sum-of-magnitudes differential bound is 3.88 mV. Eight REF branches can draw 80 nA total, shifting a 100 kΩ shared reference by 8 mV, plus each branch's resistor drop. The ADC's typical 300 pA adds about 59.6 µV through 198.7 kΩ. These are not guaranteed total offset limits. A 10 pA leakage change across 194 kΩ already gives 1.94 µV: removing DC does not remove drift or noise. Verify leakage over actual common-mode voltage, temperature, humidity and cleaning conditions; the 10 nA guarantee is not extrapolated to other voltages.

At gain 12 and 4.5 V reference, nominal full scale is ±375 mV differential; electrode DC offsets, protection offsets and transients consume that range. Respect PGA common-mode headroom as well, approximately 0.2 V plus half the amplified differential swing from each analog rail.

## Fault review — unresolved release gates

| Condition | Consequence / required action |
|---|---|
| TVS short to ground | Electrode sees 94 kΩ series path; at 5.163 V and −0.1% resistance, about 55 µA. One 47 kΩ short raises this to about 110 µA. These are illustrative circuit currents, not accepted participant limits. |
| Eight shared REF branches | Fault paths/leakage sum; eight equal 94 kΩ paths give 11.75 kΩ, approximately 440 µA for the same illustrative voltage. Analyze the complete system and single faults. |
| TVS open | Added transient shunting is lost; internal ADC diodes remain. Detect/qualify with controlled bench tests. |
| Series resistor open/short | Open loses the signal; short removes some impedance. Select pulse-qualified resistors and verify spacing/voltage stress. |
| Differential capacitor short | Inputs are shorted together after the resistors; acquisition invalid. Firmware must detect faults; no firmware implementation supplied. |
| Both jumper links fitted | Local negative electrode and REF become connected before resistors. Mechanically constrain to one shunt and document assembly inspection. |
| ADC powered off or sustained external voltage | Internal clamps may back-power AVDD. The LDO cannot be assumed to sink current. Rail back-power protection remains unresolved. |
| ESD event | External TVS clamp exceeds ADC rails. At a typical 12.4 V clamp, 4.7 kΩ would give about 2.58 mA into a hypothetical unpowered 0.3 V internal clamp. This is only illustrative: no maximum clamp guarantee, pulse qualification or parasitic proof. |
| ±12 V sustained input | A crude 12 V/98.7 kΩ bound is 0.122 mA, but rail charging can still damage circuitry. Not an approved fault rating or test without a separate current-limited bench procedure. |
| USB/SWD/charger attached | Existing interlocks are not galvanic isolation or a medical safety certification. No human connection. Charger integration remains unfinished. |

Before accepting the network: measure noise and leakage with electrode emulators, then sweep impedance/common-mode and reference selection; verify gain/phase, channel coupling and overload recovery. Complete powered-off rail-injection analysis before fault testing. Qualify resistor pulses and assembled ESD with appropriate equipment. Establish applicable electrical safety requirements with a qualified reviewer; this step does not demonstrate IEC 60601 conformity, mains protection or defibrillator protection.

## Verification and scope

Fresh KiCad export: 276 netlist assertions passed; zero ERC errors/warnings. Assertions cover each protection path, component values, jumper mapping, retained non-input connectivity and BIAS topology. New sheet renders inspected. `analyze_inputs.py` regenerates `input_analysis.json`. Neither ERC nor these estimates establish physical safety/performance. No PCB, firmware acquisition test, transient simulation or hardware test was performed.

Step 7 schematic implementation is complete as a bench candidate; hardware acceptance remains open. Step 8 is BIAS stability/protection validation. Deferred Step 4 review, charger, event timing, exact BOM/footprints and release review remain open.
