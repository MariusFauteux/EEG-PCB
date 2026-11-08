# Step 8: BIAS drive stability and protection

2026-11-08 · Rev C5 · Bench schematic candidate, not released for fabrication or human connection.

## Summary

The Rev C4 BIAS feedback network used the values printed in the ADS1299 data sheet figures (1 MΩ ∥ 1.5 nF), which TI labels as examples. A linear model of the complete common-mode loop, including the 998 kΩ series output resistance and the capacitance that the body sees to circuit ground, gives that network ≈ 14° phase margin in the nominal case and an unstable loop in some plausible corners. Rev C5 adds a 100 kΩ resistor in series with a 10 nF feedback capacitor (lead-lag compensation), which raises the modelled phase margin to ≈ 84° nominal and at least 47° across all 324 swept cases, at the cost of ≈ 10 dB less 50 Hz common-mode attenuation in the nominal case. A TPD2E2U06 clamp is added at the midpoint of the two 499 kΩ output resistors. All results are model estimates; none has been measured.

## Implemented

| Ref | Rev C4 | Rev C5 |
|---|---|---|
| RFB1 | 1 MΩ, BIASOUT to BIASINV | Unchanged |
| CFB1 | 1.5 nF C0G, BIASOUT to BIASINV | 10 nF C0G 5 % 50 V, BIASOUT to BIAS_COMP |
| RZB1 | none | 100 kΩ 0.1 %, BIAS_COMP to BIASINV |
| RB1, RB2 | 2 × 499 kΩ in series to JBIAS1 | Unchanged; midpoint named BIAS_MID |
| D509 | none | TPD2E2U06DCKR, both I/O pins on BIAS_MID, pin 3 to GND |

The feedback impedance is now Z_f = R_FB ∥ (R_Z + 1/sC_F). BIASREF (pin 60) and BIASIN (pin 62) remain tied to AVSS; this is permitted by data sheet §10.1.1, but makes a firmware setting mandatory (see below). The REF electrode wiring is unchanged.

## Manufacturer evidence checked online

[TI ADS1299 data sheet, SBAS499C](https://www.ti.com/lit/ds/symlink/ads1299.pdf):

- §7.5, patient bias amplifier: gain-bandwidth product 100 kHz and slew rate 0.07 V/µs (typical, 50 kΩ ∥ 10 pF load, gain 1); common-mode input range AVSS + 0.3 V to AVDD − 0.3 V; short-circuit current 1.1 mA typical. No open-loop DC gain or output-swing limit is specified.
- §9.3.2.4.5 and Equation 11: the DC common-mode gain is R_F·N/330 kΩ, where N is the number of inputs enabled in BIAS_SENSP and BIAS_SENSN. Figure 38 draws the internal summing resistors as 220 kΩ; both values are swept because the two statements disagree.
- Figures 33, 34 and 38: the 1 MΩ and 1.5 nF values are marked "typical values for example only". The BIASREF pin and the internal (AVDD + AVSS)/2 source are alternative inputs selected by BIASREF_INT.
- §10.1.1: BIASREF may be tied directly to AVSS or left floating when unused; BIASIN may float or be tied to AVSS.
- CONFIG3 (03h) resets to 60h, so the amplifier is powered down and BIASREF_INT = 0 (external) after reset.
- §9.3.2.4.4: with the amplifier powered, the lead-off comparator can still sense BIASOUT and report it in BIAS_STAT.

## Loop model

`hardware/scripts/analyze_bias.py` writes `hardware/checks/bias_analysis.json`. The loop is broken at the low-impedance PGA outputs that drive the internal summing resistors, so the return ratio is exact for the model:

\[
L(s)=G_{inner}(s)\,H_{out}(s)\,H_{leg}(s)
\]

- G_inner is the inverting bias stage, Z_f/(R_int/N), including a single-pole amplifier with 100 kHz gain-bandwidth and an assumed 100 dB DC gain.
- H_out is the transfer from BIASOUT to the body through 998 kΩ, the BIAS lead capacitance and the BIAS electrode, loaded by the body's capacitance to circuit ground and by all 16 input legs.
- H_leg is the transfer from the body to an ADC pin through an input electrode, the input lead capacitance, 94 kΩ, the TVS (1.5 pF), 4.7 kΩ and the ADC pin (20 pF, a modelling assumption carried over from Step 7). The PGA common-mode gain is taken as 1.

The sweep covers R_int 220 kΩ and 330 kΩ; N = 8 and 16; electrode impedances 10 kΩ, 100 kΩ and 1 MΩ (resistive, applied equally to the BIAS and input electrodes); BIAS lead and input lead capacitance to GND of 0, 50 and 200 pF; and body-to-circuit-ground capacitance of 10, 47 and 220 pF, giving 324 cases. The nominal case is R_int 330 kΩ, N = 16, 100 kΩ electrodes, 50 pF leads and 47 pF body coupling. Purely resistive electrodes are conservative for phase, since a real interface capacitance lowers the high-frequency impedance.

## Results

| Network | Worst phase margin | Cases < 45° | Nominal crossover | Nominal phase margin | Nominal 50 Hz attenuation | Range of 50 Hz attenuation |
|---|---:|---:|---:|---:|---:|---:|
| C4: 1 MΩ ∥ 1.5 nF | −16.7° | 324 of 324 | 749 Hz | 14.4° | 32.2 dB | 18.3–36.3 dB |
| 1 MΩ ∥ 10 nF | 6.3° | 303 | 288 Hz | 24.4° | 22.5 dB | 6.3–26.8 dB |
| 1 MΩ ∥ 22 nF | 11.0° | 240 | 186 Hz | 33.9° | 15.8 dB | −3.9–20.3 dB |
| **C5: 1 MΩ ∥ (100 kΩ + 10 nF)** | **47.4°** | **0** | **522 Hz** | **84.4°** | **22.4 dB** | **6.9–26.6 dB** |
| 1 MΩ ∥ (100 kΩ + 15 nF) | 54.5° | 0 | 511 Hz | 89.5° | 19.6 dB | 4.0–23.8 dB |
| 1 MΩ ∥ (100 kΩ + 22 nF) | 61.1° | 0 | 506 Hz | 92.9° | 17.4 dB | 2.4–21.6 dB |

The C4 network is marginal even without any cable capacitance: with 10 kΩ electrodes, N = 8 and 10 pF body coupling, its phase margin is ≈ 29°, and in the nominal case without cables ≈ 19°. The cause is the 998 kΩ output resistance driving the body's capacitance to circuit ground. Sixteen input legs at ≈ 21.5 pF each already contribute ≈ 340 pF, which places a second pole in the hundreds of hertz, close to the 106 Hz feedback pole. Increasing C_F alone moves the crossover down but leaves both poles in the loop, so the margin remains poor and mains attenuation is lost. The series zero resistor flattens the bias-stage gain above ≈ 160 Hz to R_Z·N/R_int ≈ 4.8 (N = 16, 330 kΩ), which restores phase at crossover. The closed-loop peaking in the nominal case falls from 12.4 dB to 0.4 dB, and to at most 3.3 dB anywhere in the sweep.

The worst C5 case for both phase margin and mains attenuation combines 1 MΩ electrodes, 200 pF on every lead, 220 pF body coupling and N = 8. There the loop gives only ≈ 6.9 dB at 50 Hz with an 88 Hz crossover. The 15 nF and 22 nF variants trade further attenuation for margin; 10 nF was chosen because it keeps every swept case above 45° whilst retaining the most mains attenuation.

The DC loop gain is unchanged, because R_F remains 1 MΩ: ≈ 48 with N = 16, or ≈ 24 with N = 8 (330 kΩ interpretation).

## DC behaviour and fault currents

| Quantity | Estimate | Basis |
|---|---:|---|
| Maximum DC current from BIASOUT into the electrode, normal condition | 5.18 µA | 5.163 V (upper analogue-rail corner) across 998 kΩ −0.1 %, body at circuit GND |
| One of RB1/RB2 shorted | 10.36 µA | 5.163 V across 499 kΩ −0.1 % |
| Both RB1 and RB2 shorted | Up to ≈ 1.1 mA | BIASOUT short-circuit current, typical, not guaranteed |
| D509 shorted to GND | ≤ 10.4 µA from BIASOUT; electrode sees 499 kΩ to GND | RB1 and RB2 on either side of the clamp |
| TVS leakage drawn from the body, 16 legs | ≤ 160 nA | 10 nA maximum per TPD2E2U06 channel at 2.5 V |
| Drop across 998 kΩ from that leakage | ≈ 0.16 V | Within BIAS output range; loop corrects body voltage to within ≈ 3.2 mV (N = 16) |
| Mains displacement current, 2 pF from 230 V 50 Hz | ≈ 0.145 µA RMS | Assumed body-to-mains coupling |
| BIASOUT swing to sink that current, 1 MΩ BIAS electrode | ≈ 0.41 V peak | Well inside the rails at mid-supply |

These are circuit currents, not an assessment against a standard. Commonly quoted IEC 60601-1 DC limits for patient currents are of the order of 10 µA in normal condition and 50 µA under single fault, but the applicable values, current category and applied-part classification for this device have not been confirmed against the published standard and must be established by a qualified reviewer. The two-resistor arrangement exists so that a single resistor short does not remove the current limit; a double fault does.

D509 limits the voltage at BIAS_MID during transients. Its leakage flows through RB1 inside the loop and its 1.5 pF adds a pole near 210 kHz, both negligible. The 499 kΩ resistors carry nearly the full transient voltage between the electrode and the clamp, so they need pulse-rated or high-voltage parts, possibly in a larger package; 0805 footprints remain provisional. The ADC's internal clamps on BIASOUT now see the clamp voltage through 499 kΩ.

## Firmware requirements arising from this step

1. **Set BIASREF_INT = 1 in the same CONFIG3 write that sets PD_BIAS = 1** (for example CONFIG3 = 0xEC with the internal reference buffer on). Because BIASREF is tied to AVSS, enabling the amplifier with the reset value BIASREF_INT = 0 would drive the body towards 0 V, outside the PGA common-mode range.
2. Choose BIAS_SENSP/BIAS_SENSN deliberately and record the choice in the session metadata. N changes the loop gain and therefore the stability and mains attenuation; the analysis covers N = 8 and 16 only. Exclude channels with a disconnected or saturated electrode from the sense set, since an open input injects its drifting voltage into the common-mode estimate.
3. Monitor BIAS_STAT with BIAS_LOFF_SENS enabled to detect BIASOUT saturation, for example a disconnected BIAS electrode. Mark affected samples rather than discarding them.
4. BIAS_MEAS can route BIASIN to a channel for diagnostics, but BIASIN is tied to AVSS in this design, so that path measures ground and is not useful as built. Measuring BIASOUT directly would need a hardware change.

## What this step does not establish

- The model is linear and small-signal. Saturation and recovery after an electrode disconnects, slew limiting, start-up from a discharged body and large mains pickup were not simulated.
- The 20 pF ADC pin capacitance, the internal summing resistance (220 or 330 kΩ), the amplifier's DC gain and every electrode, cable and body coupling value are assumptions. The real body-to-circuit coupling of a battery-powered device worn on the head is not known.
- Electrodes were modelled as equal resistors; real electrodes have mismatched impedances and interface capacitance.
- No transient, ESD or surge behaviour of D509, RB1 or RB2 was simulated or tested.
- Shared-REF montages, in which REF carries up to eight N legs, were not modelled separately.
- No compliance with IEC 60601-1, IEC 60601-2-26 or any other standard is claimed.

## Acceptance tests before the network is accepted

1. With an electrode simulator (resistor and capacitor per electrode, adjustable lead capacitance and a 2 pF coupling from a 50 Hz source to the body node), measure the BIASOUT and body-node step response for N = 8 and N = 16. Overshoot and ringing give the margin directly; compare with the model.
2. Sweep electrode impedance from 10 kΩ to 1 MΩ and lead capacitance from 0 to 200 pF, and record mains common-mode amplitude at the ADC inputs with the BIAS loop on and off.
3. Disconnect and reconnect the BIAS electrode during acquisition; record saturation, BIAS_STAT behaviour and recovery time.
4. Confirm the firmware CONFIG3 sequence on hardware by measuring the body node at mid-supply after enabling the amplifier.
5. Verify RB1, RB2 and D509 survive the intended ESD qualification, together with the input networks from Step 7.

## Verification at schematic level

`hardware/rebuild.sh`: 287 netlist assertions passed and zero ERC errors (ERC warnings are the local footprint-library configuration only). The new assertions cover the RFB1, CFB1, RZB1, RB1 and RB2 values; the BIASOUT, BIASINV, BIAS_COMP and BIAS_MID connections; D509's pin mapping; the single path to JBIAS1; and the BIASREF and BIASIN ties. A pin-membership comparison against the Step 7 netlist (`hardware/baseline/step7_netlist.xml`) confirms that only RZB1 and D509 were added and that every connection outside the BIAS network is unchanged. No hardware has been built or tested.
