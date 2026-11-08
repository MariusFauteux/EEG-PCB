# Step 12: reference distribution and powered-off backfeed (Rev C9)

2026-11-08. Status: drawn on the `ref_bias` and `analog` sheets and checked by netlist assertions, `hardware/scripts/analyze_inputs.py` and the new `hardware/scripts/analyze_backfeed.py`. Nothing has been simulated in SPICE or measured. Rev C9 is a bench schematic candidate and is not released for fabrication or for connection to a person.

Step 12 closes README open items 5 (shared-REF channel coupling) and 6 (powered-off backfeed) at schematic and calculation level. It adds two small circuits:

- **D46: buffered REF.** The REF electrode now drives only an OPA376 unity follower (U500) through its own copy of the leg protection (2 × 47 kΩ, TPD2E2U06, 4.7 kΩ). The follower's output, REF_BUF, feeds pin 3 of JP1–JP8. Every channel that selects REF keeps its own 94 kΩ / clamp / 4.7 kΩ network after the jumper.
- **D47: +5VA backfeed clamp.** Q201 (CSD17381F4) with R208 (100 Ω) pulls +5VA down whenever the analogue rail is commanded off or the board is unpowered. Its gate is held up from +5VA itself through R209 (1 MΩ), so it needs no other supply. Q202 grounds the gate while ANA_ENABLE is high.

## 1. Shared-REF coupling (item 5)

### The problem

When several channels select REF, their negative inputs all hang on one electrode impedance. A signal on one channel's positive electrode drives current through that channel's 220 pF differential capacitor into its negative leg. That current returns through the shared REF electrode, and the voltage it develops there appears on every other channel's negative input. The Step 7 model gives −37.3 dB at 100 Hz for eight channels on a 100 kΩ REF electrode. This is electrical, not physiological. It biases exactly the cross-channel measures (coherence, correlation, crosstalk between neighbouring PEDOT:PSS and Ag/AgCl sites) that an electrode comparison relies on. It also grows with REF impedance, which is the very quantity that differs between the electrode types under test.

The coupling is not the only effect of a passive shared REF:
- **DC current in the REF electrode.** All selected branches draw their TVS and ADC leakage through it: up to 8 × (10 nA + 0.3 nA) = 82.4 nA, an 8.2 mV shift on 100 kΩ. A polarisable electrode carrying a DC current drifts electrochemically, which matters in a long-term electrode study.
- **Loading.** Each selected channel adds its input capacitance to the REF node, so REF's effective impedance differs from that of every positive electrode. This converts body common mode into a differential error even with equal electrodes.

### Options compared

All figures use the Step 7 nodal model, extended in `analyze_inputs.py` (resistive electrodes, 1.5 pF per TVS pin, 20 pF per ADC pin, 300 K). "Coupling" is the voltage on channel 2 relative to channel 1 when only channel 1's positive electrode is driven.

| Option | 10 kΩ REF | 100 kΩ REF | 1 MΩ REF | Notes |
|---|---:|---:|---:|---|
| Passive shared REF (Rev C4–C8) | −57.2 dB | −37.3 dB | −20.7 dB | 8 channels, 100 Hz. With two channels on REF and 1 MΩ: −17.4 dB |
| ADS1299 SRB1 route | −36.6 dB | −31.5 dB | −20.3 dB | REF through one protection network to SRB1, MISC1.SRB1 = 1 |
| **REF buffer (selected)** | −157 dB | −157 dB | −157 dB | Limited by the assumed 0.1 Ω of REF_BUF copper |
| Bipolar only | none | none | none | No shared node; loses the referential montage |
| Passive, C_diff removed | — | −204 dB | −184 dB | Model artefact: see below |

**SRB1.** The ADS1299 can route SRB1 to all inverting inputs through internal switches (SBAS499C §9.6.1.15, Figure 18). The data sheet gives no switch resistance, so 10 Ω to 1 kΩ was swept; the result does not change (−31.47 dB at 100 Hz, 100 kΩ). SRB1 is worse than the passive network, because the shared impedance is now the REF electrode plus a whole 98.7 kΩ protection network, not the electrode alone. It also switches all eight channels together, so mixed bipolar and referential montages become impossible, and the unused external negative-leg networks still hang on the inputs. Rejected.

**Bipolar only.** No electrical coupling, and the jumpers already provide it. It is kept as an option on every channel, but a common reference is needed for referential montages, for re-referencing in analysis and for comparing many sites against one reference. Removing the choice was not adopted.

**Removing C_diff.** In this model the coupling flows only through the differential capacitor, so removing it removes the coupling. That result depends on the 20 pF-per-pin approximation, which Step 7 already marked as unvalidated, and the capacitor is the differential RF filter for a sampled input. Trading a modelled coupling for unmodelled RF rectification was not adopted. C_diff stays at 220 pF.

**REF buffer.** A follower presents the REF electrode with one leg of loading and drives the jumpers from a low impedance. With the OPA376's minimum 120 dB open-loop gain and 5.5 MHz bandwidth, and an assumed (pessimistic) 1 kΩ open-loop output resistance, the closed-loop output impedance at 100 Hz is about 18 mΩ. The 0.1 Ω assumed for the copper to sixteen header pins dominates, so the modelled coupling falls to −157 dB for any REF impedance up to 1 MΩ. In practice layout, ground return and the ADC's own input structure will set the floor; the model only shows that the shared electrode impedance is no longer the limit.

### What the buffer costs

| Quantity (0.1–100 Hz) | Passive | Buffered | Comment |
|---|---:|---:|---|
| Common-mode noise added to every REF channel, 10 kΩ REF | 0.13 µV rms | 0.45 µV rms | Electrode thermal noise, plus 98.7 kΩ front network and OPA376 |
| Same, 100 kΩ REF | 0.41 µV rms | 0.60 µV rms | Adds 0.44 µV rms in quadrature (rule: ≤ 0.5 µV) |
| Same, 1 MΩ REF | 1.29 µV rms | 1.36 µV rms | |
| Independent negative-leg resistor noise per channel | 0.40 µV rms | 0.40 µV rms | Unchanged |
| DC current from the REF electrode | ≤ 82.4 nA (8 channels) | ≤ 10.0 nA | TVS 10 nA max at 2.5 V plus OPA376 10 pA max at 25 °C |
| DC shift on a 100 kΩ REF electrode | 8.2 mV | 2.0 mV | Buffered figure through 100 kΩ + 98.7 kΩ |
| 50 Hz common mode to differential, 8 channels, equal 10 kΩ / 100 kΩ / 1 MΩ electrodes | −66.5 / −46.5 / −28.2 dB | −83.4 / −63.4 / −43.4 dB | Before any BIAS-loop rejection |

The extra noise is mostly the 98.7 kΩ protection network in front of the buffer, which is kept deliberately: the REF electrode faces the same series resistance and clamp as every other electrode. The OPA376 contributes about 0.16 µV rms (from 0.8 µVpp in 0.1–10 Hz and 7.5 nV/√Hz at 1 kHz; the 1/f corner of ≈ 55 Hz is fitted, not specified). The common-mode conversion improves because REF no longer carries the input capacitance of up to eight channels. With a buffered REF every negative leg sees a near-zero source, so the remaining conversion comes from the positive electrode's own impedance, as it would for any channel.

OPA376 was chosen over the zero-drift OPA388 (0.14 µVpp, 7 nV/√Hz) because the OPA388's bias current is up to ±350 pA at 25 °C against 10 pA, its current noise is 100 fA/√Hz against 2 fA/√Hz and it draws 1.9 mA against 0.76 mA. A chopper also puts switching artefacts on the input, which then pass through 94 kΩ into a high-impedance electrode. The OPA376's input and output reach both rails, it runs from 2.2–5.5 V and so sits directly on +5VA (5.088 V nominal, 5.202 V maximum), and it drives 250 pF directly at unity gain, so the REF_BUF copper and headers need no isolation resistor.

### Consequences

- **Lead-off on REF.** The ADS1299 lead-off current on a referential channel's negative input now flows into the buffer output, not the REF electrode, so the ADC can no longer detect a detached REF electrode on its own. A detached REF leaves the follower input on 10 pA of bias current, so every referential channel drifts or saturates together. Firmware must treat that pattern as REF lead-off.
- **BIAS loop.** Referential negative legs now connect to the follower, not to the body, so the body sees less input capacitance than the 16 × 21.5 pF assumed in `analyze_bias.py`. That model is therefore conservative for referential montages; it was not rerun with the new topology.
- **Power.** The analogue rail carries about 0.76 mA typical, 0.95 mA maximum more. U500 is off whenever the ADC is off.

## 2. Powered-off backfeed (item 6)

### Mechanism

With the analogue rail off, a positive voltage on an electrode relative to board GND passes 94 kΩ, the TVS node and 4.7 kΩ to the ADS1299 input, where an internal diode clamps it to AVDD (SBAS499C §7.1 note 2: inputs are diode-clamped to the rails, 10 mA continuous limit). The OPA376 input behaves the same way (SBOS406G §6.1). The TPD2E2U06 does not intervene below its breakdown of 6.5–8.5 V at 1 mA (SLLSEG9C). The current returns to the body through the other electrodes' clamp diodes from GND. What reaches +5VA must leave through the rail's loads. In Rev C8 those are R205 (4.7 kΩ), the ANALOG_OK divider (42 kΩ) and the PGFB divider (150 kΩ), about 4.13 kΩ in all.

**LT3045 when unpowered.** The Step 4 review recorded that the LT3045 blocks reverse current from OUT to IN. Its data sheet could not be downloaded again in this step (Analog Devices blocks automated downloads), so the analysis assumes the regulator neither sinks nor passes any backfed current. That can only overstate the rail rise. The same goes for treating the unpowered ADS1299 and OPA376 as drawing nothing from AVDD.

Because the board floats on its battery, a voltage common to all electrodes (the participant's potential against earth) drives nothing through it. Only voltages *between* this board's electrodes matter.

### Sources and results

`analyze_backfeed.py` solves the DC operating point with 17 legs (16 ADC inputs and the REF buffer input). The clamp-diode saturation currents are not specified anywhere, so two corners are run (1e-15 A with n = 1.0, and 1e-9 A with n = 1.5) and the worse kept. TVS breakdown is taken at its 8.5 V maximum, which steers the most current towards AVDD. Q201 is modelled from the CSD17381F4 threshold of 0.65–1.10 V at 250 µA (SLPS411G) with an assumed 90 mV/decade below threshold and square law above. Against the data sheet's transfer curve this understates conduction, so the clamp voltage is overstated.

| Case | Rev C8 AVDD | Rev C9 AVDD | Into +5VA (C9) | Per IC pin (C9) |
|---|---:|---:|---:|---:|
| Half-cell or DC offset, 0.5 V, one electrode against 16 | 0.004 V | 0.004 V | 0.9 µA | 0.9 µA |
| Dissimilar electrodes, 1.0 V, 8 against 9 | 0.067 V | 0.067 V | 16 µA | 2.0 µA |
| Other instrument output, 15 V limited to 10 µA, one electrode | 0.037 V | 0.037 V | 9.0 µA | 9.0 µA |
| Same, single fault, limited to 50 µA | 0.144 V | 0.144 V | 35 µA | 35 µA |
| Stimulator field or contact, 10 V, 4 against 13 | 1.04 V | 0.98 V | 256 µA | 64 µA |
| Stimulator at 30 V compliance, 8 against 9 | **4.43 V** | 1.18 V | 1.22 mA | 152 µA |
| Abuse, 100 V, 8 against 9 | **6.87 V** | 1.31 V | 4.29 mA | 536 µA |

The 10 µA and 50 µA instrument limits are illustrative values for a current-limited instrument sharing the participant, not figures taken from a standard read for this step. The stimulator voltages are likewise illustrative. Electrode impedance is set to zero in the stimulator and abuse cases, which is the worst case.

**Findings.**
1. Half-cell potentials, DC offsets and current-limited instruments cannot raise AVDD meaningfully. Two forward diodes in series and the 4.13 kΩ rail load absorb them, with or without a clamp.
2. A stimulator or another source that can put tens of volts between electrodes lifts AVDD in Rev C8 to 4.4 V at 30 V: high enough to run parts of the ADS1299 and the OPA376 with DVDD absent, and close to the ANALOG_OK release threshold. At 100 V it reaches 6.9 V, above the ADS1299's 5.5 V absolute maximum. A hardware change is needed.
3. Input-pin currents stay at or below 0.54 mA in every case, far below the 10 mA limit of both ICs, because the 94 kΩ resistors carry the voltage.
4. **Isolated trigger.** The TLP2761 has no galvanic path: 0.4 pF typical across the barrier and at least 10¹² Ω (Toshiba data sheet). Mains at 230 V rms across it would pass about 29 nA rms, and 500 V DC about 0.5 nA, into board GND, never into +5VA. The photodiode input shares GND but connects to the +3V3 amplifier, not to +5VA, and the sensor is passive. The BIAS electrode reaches BIASOUT only through 998 kΩ.

### Options

| Option | Effect | Cost | Verdict |
|---|---|---|---|
| Lower the bleeder (R205) | AVDD ∝ load resistance; 1 kΩ gives about 1 V at 1 mA | 5 mA lost continuously from the battery for a fault-time benefit | Rejected |
| Series diode or switch in each input | Blocks the path | Leakage, noise and offset in every leg | Rejected |
| Zener or TVS on +5VA | Limits only above about 5.6 V | Does not stop partial powering at 1–5 V | Insufficient alone |
| Load switch with output discharge | Clamps only while its own supply is up | No action in ship mode | Rejected |
| **Self-biased NMOS clamp (selected)** | Holds AVDD ≤ 1.31 V up to 100 V | 5 µA in R209 while running, four parts | Adopted |

### The clamp

Q201's gate is tied to +5VA through R209, and its drain sinks +5VA through R208. While the rail is off, any voltage pushed onto +5VA also drives Q201's gate, so the clamp turns itself on at the rail's own expense and needs neither SYS nor +3V3. This covers ship mode, the BQ25798 off states, and the powered state with ANA_ENABLE low (before a recording, after a supervisor stop, during USB service). When ANA_ENABLE goes high, Q202 grounds the gate before the LT3045's soft start has raised +5VA, so the two never fight at start-up. Q202's gate sits on ANA_ENABLE, which already has a 100 kΩ pull-down (R206), so the clamp is active whenever the enable chain is unpowered.

- **Clamp level.** At most 1.31 V with 4.3 mA backfed at the high-threshold corner (25 °C). Below about 0.2 V the existing 4.13 kΩ load dominates. The threshold rises when cold (SLPS411G Figure 5-6), so the clamp level at 0 °C is somewhat higher; this is not quantified.
- **Running cost.** 5.25 µA in R209. Q201's drain leakage is ≤ 100 nA (at 24 V). Q202's gate adds 150–195 pF to the push-pull ANA_ENABLE net, which the SN74AUP1G08 drives at about 4 mA, so the edge stays near 160 ns. The ANA_ENABLE loads are Schmitt inputs and the LT3045 EN/UV pin.
- **Discharge after a stop.** When ANA_ENABLE falls, the ADC is already in reset through the enable chain. Q201 then discharges the ≈ 60 µF on +5VA (nominal, no DC-bias derating) to 1.0 V in 35 ms, 0.5 V in 0.20 s and 0.3 V in 0.33 s, against 0.69 s to 0.3 V on the loads alone. Peak current is limited by R208 to 52 mA; the energy is about 0.8 mJ per stop, so R208 is a 1206 0.25 W part. The faster, defined decay also helps the ADS1299 power-up rule that inputs and supplies start from low (SBAS499C §11.1).
- **Effect on Step 10 timing.** None on the reset path. ANA_ENABLE low already asserts ADS_RESET_N through gates; the clamp acts afterwards and only on the rail.

CSD17381F4 was chosen for its low threshold (0.65–1.10 V at 250 µA), 30 V drain rating, 12 V gate rating and integrated gate ESD diode. It is a 1.0 × 0.6 mm FemtoFET (PicoStar YJC). KiCad has no stock footprint for it, so a land pattern must be drawn from SLPS411G before layout. The pin numbering (1 gate, 2 source, 3 drain) follows the top-view drawing and must be checked against TI's land-pattern page.

## 3. Firmware requirements added

1. Referential montage: fit JPn 2–3 for each referential channel. Keep MISC1.SRB1 = 0 and every SRB2 bit clear; the internal SRB switches stay unused.
2. REF lead-off: the ADC cannot detect a detached REF electrode. Flag REF lead-off when all channels on REF drift towards a rail together, and check REF impedance at session start by a separate procedure (bench method to be defined).
3. After any analogue stop, keep RUN_REQUEST low for at least 1 s before re-arming, so that +5VA has fallen below 0.3 V and the ADS1299 starts from a defined power-up (D40 already requires a fresh rising edge).
4. Record in the session metadata which channels use the buffered REF, together with the montage.

## 4. Verification

- `hardware/rebuild.sh`: 408 netlist assertions pass (387 at Step 11). KiCad ERC: 0 errors, 0 warnings.
- New assertions cover the REF electrode reaching only R517, the 2 × 47 kΩ / D510 / 4.7 kΩ order, the follower wiring, REF_BUF reaching only U500 and pin 3 of JP1–JP8, U500 on +5VA, and every clamp connection including Q202 on ANA_ENABLE.
- A pin-membership comparison with the Step 11 netlist (`baseline/step11_netlist.xml`) confirms the scope: only the 11 Step 12 parts were added (U500, D510, R517–R519, C500, C501, Q201, Q202, R208, R209); nothing was removed; only pin 3 of JP1–JP8 and JREF1 pin 1 changed connection; all 1029 other retained pin connections are unchanged.
- `analyze_inputs.py` now exits non-zero on failure. Six rules pass, including reproduction of the Step 7 −37.3 dB figure, buffered coupling ≤ −100 dB, the noise and DC-current limits and better common-mode conversion than the passive network.
- `analyze_backfeed.py` passes six rules: AVDD ≤ 0.5 V for realistic sources, ≤ 1.5 V for stimulator cases up to 30 V, < 5.5 V at 100 V, IC pin current ≤ 2 mA, clamp running cost ≤ 10 µA and discharge to 0.3 V within 1 s.
- The changed sheets (`ref_bias`, `analog`, both input sheets) were exported with `kicad-cli sch export pdf` and inspected.

**Not done and still required.**
- A footprint for the CSD17381F4 (YJC) and a pin-number check against TI's land pattern.
- The LT3045 reverse-current figures, from its current data sheet.
- The `analyze_bias.py` model with the buffered-REF topology (expected to gain margin, not checked).
- Clamp-diode characteristics of the ADS1299 and OPA376 inputs, which no data sheet gives; the bench test replaces the two modelled corners.

**Bench tests.**
1. Crosstalk: drive one channel at 10, 50 and 100 Hz through 100 kΩ, with all others on REF through a 100 kΩ and a 1 MΩ REF emulator. Compare with the same channels in bipolar mode. Expect no measurable coupling above the ADC noise.
2. Noise with shorted positive inputs on REF through 0, 10 kΩ, 100 kΩ and 1 MΩ, 0.1–100 Hz, against the table above.
3. REF electrode DC current via the offset across 1 MΩ, at 25 °C and warm.
4. REF disconnect: detach the REF emulator during acquisition and record the drift pattern used by firmware.
5. Backfeed, in ship mode and with ANA_ENABLE low: from a current-limited supply through 1 kΩ, apply 1, 10 and 30 V between groups of electrode inputs. Measure +5VA, Q201 gate, the supply current and the ADS1299 and OPA376 pin temperatures. Repeat with Q201 removed to confirm the Rev C8 figures.
6. Discharge: capture +5VA, ANA_ENABLE and ADS_RESET_N on a supervisor stop and on a firmware stop; confirm < 0.3 V within 1 s and a clean restart after it.
7. Start-up: confirm LT3045 soft start, ANALOG_OK release and the AVDD envelope are unchanged with the clamp fitted.

## Sources

- TI ADS1299, SBAS499C: absolute maximum ratings and input clamp note (§7.1), input capacitance and bias current (§7.5), noise tables, SRB1 routing, MISC1 register and the referential-montage description (§9.3.1.1, §9.6.1.15 and the EEG application section), power-up sequencing (§11.1). The data sheet gives no SRB1 switch resistance. Read for this step.
- TI TPD2E2U06, SLLSEG9C: breakdown 6.5–8.5 V at 1 mA, 10 nA maximum leakage at 2.5 V, 1.5 pF, 5.5 V stand-off. Read for this step.
- TI OPA376, SBOS406G: pinout (DBV), supply 2.2–5.5 V, input clamp current 10 mA, bias current 10 pA maximum at 25 °C, noise, AOL ≥ 120 dB, 5.5 MHz GBW, 250 pF unity-gain capacitive load, 760/950 µA quiescent current, orderable OPA376AIDBVR. Read for this step.
- TI OPA388, SBOS777D: bias current, noise and quiescent current, for the comparison only. Read for this step.
- TI CSD17381F4, SLPS411G: VGS(th) 0.65–1.10 V at 250 µA, ratings, leakage, capacitance, transfer characteristics, package. CSD13381F4 (SLPS448F, 12 V drain rating) was read and not used. Read for this step.
- Toshiba TLP2761 data sheet: isolation capacitance and resistance (as read at Step 9).
- ADI LT3045: reverse-current protection as recorded in the [Step 4 review](step4_power_review.md); not re-read.
