# Step 9: event timing, ADC clock, trigger and photodiode inputs

2026-11-08 · Rev C6 · Bench schematic candidate, not released for fabrication or human connection.

## Summary

Rev C6 replaces the ADS1299 internal oscillator with an external 2.048 MHz MEMS oscillator specified at ±20 ppm. It adds an optically isolated trigger input and a photodiode front end, and defines how firmware timestamps every DRDY, trigger and photodiode edge on one MCU timer so that events can be placed on the ADC sample timeline to a fraction of a sample. The internal oscillator was rejected because its specified accuracy (±0.5 % at 25 °C, ±2.5 % over temperature) misplaces an event 1 s into an epoch by 5–25 ms if the nominal rate is assumed, against a proposed 0.1 ms target. All figures are datasheet-derived estimates; nothing has been measured.

## Timing requirements (proposed)

The project targets visual ERP work, but no numerical timing requirement had been recorded. The following targets are proposed for board-attributable timing and should be confirmed against the experimental protocol. Display latency is excluded because the photodiode measures it directly.

| ID | Requirement | Target |
|---|---|---|
| T1 | Alignment of a captured event with the ADC sample timeline | ≤ 100 µs (0.1 sample) |
| T2 | Accumulated timing error across a 1 s epoch when the nominal sample rate is assumed | ≤ 100 µs (≤ 100 ppm) |
| T3 | Session drift against wall-clock time without external synchronisation | ≤ 10 s per 24 h (annotation only; triggers carry precise synchronisation) |

## Clock comparison

`hardware/scripts/analyze_timing.py` writes `hardware/checks/timing_analysis.json`.

| Clock | Frequency error | Error over a 1 s epoch | Drift per 24 h | T2 | T3 |
|---|---:|---:|---:|:---:|:---:|
| ADS1299 internal, 25 °C | ±0.5 % | 5 ms | 432 s | fails | fails |
| ADS1299 internal, −40 to 85 °C | ±2.5 % | 25 ms | 2160 s | fails | fails |
| SiT8008 external (selected) | ±20 ppm | 20 µs | 1.7 s | meets | meets |
| nRF52840 HFXO (MCU timebase) | assumed ±50 ppm | 50 µs | 4.3 s | meets | meets |

The internal oscillator could in principle be used if every analysis applied a per-session sample rate measured from DRDY timestamps against the MCU crystal. That makes every result depend on a firmware-measured clock record, leaves frequency-domain labels uncertain by up to 2.5 % whenever the record is absent and offers no protection against temperature change within a session. The external oscillator meets T2 and T3 without correction and costs one 2.5 × 2.0 mm part. DRDY timestamps are kept regardless, so that the two clocks verify each other and missed samples are detected.

The MCU crystal tolerance is not stated in the NINA-B3 data sheet text. The ±50 ppm figure is an assumption based on the Bluetooth LE carrier-accuracy requirement and must be confirmed. Event alignment (T1) does not depend on it, because DRDY and event edges share the same timer.

## Implemented

### External ADC clock (`adc_interface` sheet)

| Ref | Part | Connection |
|---|---|---|
| Y340 | SiTime SIT8008BIF11-33E-2.048000 (rev B, industrial, 2.5 × 2.0 mm, ±20 ppm, 3.3 V, output enable) | VDD and OE (via R348 10 kΩ) on +3V3_ADC; OUT through R349 33 Ω to ADS1299 CLK (pin 37) |
| R340 | 10 kΩ | CLKSEL (pin 52) now to GND, selecting the external clock (SBAS499C Table 6) |
| R341 | 100 kΩ (was 10 kΩ) | CLK pull-down, keeps the pin defined if Y340 is not fitted |
| C340 | 100 nF | Y340 local bypass |

Y340 is powered from the same rail as the ADC digital supply, so the clock cannot drive the CLK pin of an unpowered ADC. Reverting to the internal oscillator needs only R340 moved to +3V3_ADC and Y340 unfitted.

### Isolated trigger input (`event_inputs` sheet)

The trigger source (for example the stimulus computer's TTL output) drives the LED of a TLP2761 optocoupler directly, so no power is needed on the isolated side: J600 (BNC, part to be chosen) → R600 620 Ω → LED anode, with a 1N4148WS (D600) across the LED as a reverse clamp. The TLP2761 output, powered from +3V3, drives TRIGGER_ISO (module pad 32, P0.11) through R601 100 Ω. The output is inverting: a high trigger gives a low TRIGGER_ISO.

| Source voltage | LED current (V_F 1.65–1.35 V) | TLP2761 recommended I_F(ON) 2–6 mA |
|---:|---:|:---:|
| 3.0 V | 2.18–2.66 mA | within |
| 3.3 V | 2.66–3.15 mA | within |
| 5.0 V | 5.40–5.89 mA | within |
| 5.5 V | 6.21–6.69 mA | above recommended, below the 10 mA absolute maximum |

The TLP2761 specifies 49 ns typical and 80 ns maximum propagation delay, at most 25 ns pulse-width distortion, a 1.3 mA maximum threshold current at 105 °C, 5000 Vrms isolation and 8.0 mm creepage and clearance in the SO6L package. The board must preserve that separation: J600, R600, D600 and U600 pins 1–3 form the isolated side, need at least 8 mm to all other copper (a slot under U600) and J600's shell must not connect to board ground. Whether this isolation is adequate for a participant-connected device, and what rating the standard requires, has not been assessed.

### Photodiode front end (`event_inputs` sheet)

A passive photodiode (for example a Vishay BPW34 taped to the screen corner) connects through J601. It is on the participant side of the system, like the electrodes, and must remain a passive sensor.

| Stage | Parts | Design values |
|---|---|---|
| Protection | D601 TPD2E2U06 on the cathode line; R610 1 kΩ series | Leakage 10 nA max at 2.5 V gives ≈ 0.33 mV at the TIA output |
| Transimpedance | U610 TLV9061 (10 MHz, 0.5 pA bias); R611 33 kΩ ∥ C610 15 pF; IN+ at ≈ 50 mV (R612/R613) | V_out = 50 mV + I_ph × 33 kΩ; bandwidth ≈ 320 kHz; C_F ≥ 9.1 pF needed for stability with 170 pF source capacitance |
| Threshold | U612 MCP4725A0T DAC on the existing power I²C bus (address 0x60); R617/C614 filter | Firmware sets the threshold after measuring dark and bright levels on PHOTO_MONITOR with the SAADC |
| Comparator | U611 TLV7011 (260 ns, 5 µA); R614 10 kΩ / R615 1 MΩ positive feedback | ≈ 33 mV hysteresis plus 1.2–14 mV internal; output to PHOTO_EDGE (pad 33, P1.09) through R616 |

TIA output (PHOTO_MONITOR) also reaches module pad 25 (P0.04, AIN2). At power-on the DAC outputs code 0, so the comparator stays high and produces no edges until firmware sets a threshold.

The expected signal is an estimate. A Lambertian screen of luminance L gives ≈ πL lux at the sensor, and the BPW34 delivers 70 µA at 1 klx of illuminant A. LCD white has less near-infrared than illuminant A, so a spectral factor of 0.3–1.0 was assumed. Across 50–350 cd/m² this gives 3.3–77 µA and a TIA output of 0.16–2.59 V, inside the 3.3 V swing. The real photocurrent depends on the sensor, the display and its backlight and must be measured.

PWM-dimmed backlights modulate light at 0.2–25 kHz and can produce several comparator edges per screen transition. Running the display at full brightness avoids most of these; firmware must also apply a hold-off and record the first edge of each burst.

## Timestamp capture and synchronisation

Firmware requirements; no firmware exists yet.

1. Start the HFXO before acquisition and keep it running. The nRF52840 timers otherwise run from the internal RC oscillator.
2. Run TIMER3 at 16 MHz (62.5 ns resolution). TIMER3 has six capture/compare registers, unlike TIMER0–2 with four; this replaces the TIMER2 reservation in the Rev C architecture document. CC0 captures DRDY falling edges, CC1 TRIGGER_ISO edges and CC2 PHOTO_EDGE edges, each through a GPIOTE IN channel (not PORT events) and a PPI channel. CC3 at 0 detects wrap-around and, through PPI, increments TIMER4 in counter mode, giving a 64-bit tick count without software race conditions.
3. Count DRDY edges from the START command so that the DRDY count equals the ADC sample index used in DATA records. A gap of more than 1.5 sample periods between DRDY captures flags a missed sample.
4. For each event edge, write an EVENT record with schema `event/1` (defined in [recording_format_v1.md](../recording_format_v1.md)) holding the event tick, the index and tick of the last DRDY at or before it and, once known, the tick of the next DRDY.
5. Every 1000 samples, write a `clock_sync` EVENT pairing a DRDY index with its tick, so that the ADC sample rate can be fitted against the MCU timebase over the session.

The host helper [host/event_timing.py](../../host/event_timing.py) converts an event into a fractional sample position:

\[
x = k + \frac{t_e - L - t_k}{T} + D
\]

where k and t_k are the reference DRDY index and tick, T the measured sample period in ticks, L the fixed input-path latency and D the ADC group delay in samples. D = 1.5 follows from the sinc³ filter's 3-period settling (SBAS499C §9.3.2.1.3) and is a derivation, not a datasheet figure; it must be replaced by a bench calibration. Seven tests cover the mapping, latency subtraction, clock fitting to 0.01 ppm, fallback to the fitted period, and schema rejection.

## Latency budget

| Contribution | Value | Type |
|---|---:|---|
| Timer resolution | 62.5 ns | random, ±½ tick |
| TLP2761 propagation delay | 49 ns typical, 80 ns maximum | fixed per unit, subtract as L |
| TLP2761 pulse-width distortion | ≤ 25 ns | edge-dependent |
| TLV9061 + TLV7011 path | ≈ 1–5 µs, light-level dependent | estimate; calibrate |
| GPIOTE → PPI → capture | same for DRDY and events | cancels in the difference |
| ADC group delay | ≈ 1.5 ms | fixed; calibrate |
| Clock error over 1 s, external oscillator | ≤ 20 µs | removed by the session clock fit |

Board-attributable error before calibration is dominated by the group-delay assumption and the photodiode threshold, not by the clocks. After a loopback calibration, the remaining electronic contributions are well below T1.

## What this step does not establish

- No firmware exists; GPIOTE/PPI latency, TIMER3/TIMER4 chaining and BLE coexistence are unverified.
- The ADC group delay of 1.5 samples is derived, not specified or measured.
- The MCU crystal tolerance and the SiT8008 current at 2.048 MHz were not confirmed. The data sheet gives 4.5 mA maximum at 20 MHz; the lower current at 2.048 MHz is shown only graphically.
- The SiT8008 was checked against the mature SiT8008 data sheet; the rev B ordering code was decoded from that document and a distributor listing, so the exact part should be confirmed against the current SiT8008B data sheet before ordering.
- The trigger isolation's adequacy for participant use, connector parts (J600, J601) and footprints are open.
- Photodiode signal levels, backlight PWM behaviour and the comparator threshold strategy are estimates.

## Acceptance tests

1. Loopback calibration: drive the trigger input and one electrode input (through an attenuator) from the same pulse generator. The difference between the trigger's computed sample position and the waveform's measured onset gives D and L for the trigger path.
2. Repeat with an LED driven by the same pulse and seen by the photodiode to calibrate the photodiode path at several brightness levels.
3. Log `clock_sync` records for 24 h at room temperature and in a warm enclosure; confirm the fitted ADC rate stays within ±20 ppm of nominal against a reference counter.
4. Inject trigger pulses at random times relative to DRDY; confirm the computed fractional positions are uniformly distributed and that no DRDY is missed.
5. Measure the timing jitter of 1000 trigger events against a reference timestamp and confirm T1.
6. Verify creepage and clearance on the laid-out board and test the trigger barrier as required by the safety review.

## Verification at schematic level

`hardware/rebuild.sh`: 310 netlist assertions passed and zero ERC errors (all 300 ERC warnings are the local footprint-library configuration). New assertions cover the CLKSEL and CLK wiring, Y340 supply and enable, the trigger signal path, that no isolated-side net touches any other net, the full photodiode chain, the DAC address strap and part values. A pin-membership comparison against the Step 8 netlist (`hardware/baseline/step8_netlist.xml`) confirms that only the 29 Step 9 parts were added, that only R340 changed connection and that every other connection is unchanged. No hardware has been built or tested.

## Manufacturer sources checked online

- [TI ADS1299, SBAS499C](https://www.ti.com/lit/ds/symlink/ads1299.pdf): §7.5 internal clock accuracy, external f_CLK 1.5–2.25 MHz, §9.3.2.2 Table 6, §9.3.2.1.3 filter settling, Table 7 settling times.
- [SiTime SiT8008](https://www.sitime.com/sites/default/files/mature-datasheets/SiT8008-datasheet.pdf): ±20 ppm total stability, pin map, OE behaviour, start-up time, ordering code structure.
- [Toshiba TLP2761, Rev 10.0](https://toshiba.semicon-storage.com/info/TLP2761_datasheet_en_20260511.pdf?did=28819&prodName=TLP2761): pinout, truth table, creepage and clearance, recommended I_F(ON), V_F, threshold current, propagation delay.
- [Vishay BPW34](https://www.vishay.com/docs/81521/bpw34.pdf): 70 µA at 1 klx, 70 pF at 0 V.
- [TI TLV9061](https://www.ti.com/lit/ds/symlink/tlv9061.pdf): DBV pinout, 10 MHz GBW, 0.5 pA bias current.
- [TI TLV7011](https://www.ti.com/lit/ds/symlink/tlv7011.pdf): SC70 pinout, 260 ns, 5 µA, internal hysteresis.
- [Microchip MCP4725, DS22039D](https://ww1.microchip.com/downloads/en/DeviceDoc/22039d.pdf): SOT-23-6 pinout, address byte 1100 A2 A1 A0 with A0 variant A2A1 = 00.
- [u-blox NINA-B3 data sheet](https://content.u-blox.com/sites/default/files/NINA-B3_DataSheet_UBX-17052099.pdf): 32.768 kHz crystal included in NINA-B306-00B; pad functions for P0.04, P0.11 and P1.09.
