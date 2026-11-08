# Step 4 — Rev C power and supervision replacement

2026-11-08. Status: C1 standalone schematic module, not integrated into the Rev B recorder. Open RevC_Step4_Power.kicad_pro. Three child sheets implement analog regulation, five voltage monitors, and hardware enable/reset gating. External SYS/3.3 V supplies and control signals are declared module interfaces; their sources are not implemented here. Rev B is preserved.

## Changes and rationale

Replace TPS7A4901 and its D201 discharge diode with LT3045IDD#PBF. The selected device provides reverse-current protection rather than relying on a Schottky to enforce the old regulator's 0.3 V reverse differential limit. This does not protect other ICs or signal pins against back-powering. Remove the old feedback/NR components when integrating; do not connect the two regulators in parallel.

RSET=50.5 kΩ gives 5.050 V nominal. CSET=4.7 µF supports noise reduction. The two nominal 22 µF output capacitors must retain at least 10 µF effective capacitance; exact capacitor MPNs remain pending. The 4.7 kΩ bleeder establishes more than 1 mA load for the specified accuracy conditions even with ADC load absent. RILIM=1.50 kΩ sets approximately 100 mA current limit, not a patient-protection limit. PGFB uses 140 kΩ/10 kΩ for fast startup near 4.5 V; its PG output is deliberately unused for ADC reset. OUTS must Kelvin-sense the output capacitor. Footprints for the regulator and supervisors remain unassigned pending dimensional audit.

Use TPS389001DSET supervisors for analog, digital, SYS, pack cutoff and warning. The TPS3808G01 candidate was rejected: its full-range accuracy and hysteresis would not provide adequate threshold separation here. Keep monitor dividers at modest impedance to limit sense-current error. No added SENSE capacitors delay detection. Each supervisor has its own 100 nF bypass.

## Static calculation envelope

The script check_step4.py produces calculations.json and checks selected exported-netlist connections. Resistors are budgeted at ±0.2% each: ±0.1% initial and ≤10 ppm/K over a 100 K excursion from 25°C. LT3045 full-range SET current is treated as 98–102 µA, with ±2 mV output offset. Supervisor threshold accuracy is ±1%; conservative ±100 nA sense-current contribution is included. Aging, board leakage and transients are not included.

| Quantity | Nominal | Calculated envelope |
|---|---:|---:|
| Analog rail | 5.050 V | 4.937–5.163 V |
| Analog reset assertion | 4.830 V | 4.764–4.896 V |
| Analog reset release threshold | 4.859 V | Maximum 4.926 V |
| Digital reset assertion | 3.151 V | 3.110–3.192 V |
| SYS analog inhibit | 5.773 V | 5.693–5.853 V |
| Pack analog inhibit | 6.1985 V | 6.112–6.285 V |
| Pack early warning | 6.6125 V | 6.520–6.705 V |

The rail upper static margin below the ADC's 5.25 V operating ceiling improves to about 87 mV. The minimum regulator output exceeds the maximum supervisor release threshold by only about 11 mV: this passes the defined static calculation but remains a narrow startup margin. Confirm the actual resistor specifications and measured behavior before release; do not extend the claim beyond the stated envelope. At the lowest calculated analog reset threshold, only about 14 mV remains above 4.75 V. Comparator delay means a rapidly collapsing supply can cross the ADC operating limit before reset asserts. Samples near rail faults must be marked invalid; this circuit does not promise uninterrupted valid acquisition during faults.

SYS cutoff's lower corner exceeds the regulator's upper corner plus the 330 mV maximum dropout listed for loads up to 50 mA. This supports the current analog-load budget, not the entire 100 mA current-limit range. Recalculate if analog loads grow. Pack thresholds now reference the protected pack directly, not the old diode output or charger SYS. A charger can hold SYS up while pack voltage is low, so those signals are not interchangeable.

Warning minimum exceeds cutoff maximum by about 235 mV. That voltage difference does not guarantee an SD flush time. Cell-level protection and balancing remain pack responsibilities. The lower cutoff is a functional analog-inhibit threshold, not a guaranteed per-cell discharge-protection limit.

## Hardware equations and startup sequence

- ANA_ENABLE = SYS_OK AND PACK_OK AND RUN_REQUEST AND SERVICE_OK.
- ADS_RESET_N = ANALOG_OK AND DIGITAL_OK AND ADC_RESET_REQUEST AND ANA_ENABLE.
- Every request/permit defaults low through a resistor. Gate power comes from the ADC/controller 3.3 V domain. Supervisors use open-drain outputs with 100 kΩ pull-ups.
- ANALOG_OK and DIGITAL_OK use 100 nF timing capacitors, approximately 107 ms nominal release delay. Other monitors use 10 nF, approximately 10.7 ms. These are nominal, not guaranteed minimum delays.

1. Establish the digital rail from the charger/system power path; hold ADC_RESET_REQUEST and RUN_REQUEST low. Hardware SERVICE_OK must remain low during USB/debug service.
2. Confirm pack/SYS status, then assert RUN_REQUEST only in an allowed recording mode. The analog rail rises; the independent monitor waits for its threshold and delay.
3. Firmware still waits for ADS1299 power-on timing, VCAP1 and reference settling requirements. The 107 ms nominal supervisor delay does not replace the ADC startup sequence or establish a maximum settling time.
4. Set ADC_RESET_REQUEST high only after those conditions; apply any required reset pulse through the request signal. Then configure/read back the ADC and start acquisition.
5. A monitored fault pulls reset low independently of firmware. A pack fault also inhibits analog power. Digital power stays available for fault handling and shutdown.
6. Firmware must latch RUN_REQUEST low on a pack fault and require explicit restart. The current hardware has no persistent restart latch: with a stuck-high request it can cycle after battery rebound. A hardware latch belongs in the forthcoming RUN/soft-off control and remains an open integration requirement.

The six AND gates are SN74LVC1G08DBVR; partial-power-down protection helps at zero supply but does not guarantee logic behavior throughout a collapsing supply. Check all rail-sequencing cases on the integrated system. The acquisition inhibit is not body isolation.

## Integration changes required in step 5

Replace Rev B U2/D201 and their control connections; replace the analog monitor and old after-diode UVLO/warning arrangement. Connect SYS to the charger power-path output, PACK_POS to protected pack terminals, and preserve independent pack protection. Feed the revised digital converter from SYS, with shutdown controlled by the service/RUN architecture rather than PACK_OK alone. Connect ADS_RESET_N to U1 reset through its intended series resistor and remove the previous direct host reset driver. Never parallel a push-pull MCU reset output with this gate output. MCU drives ADC_RESET_REQUEST instead.

Map ANALOG_OK to existing analog status; DIGITAL_OK replaces reliance on buck PG alone for reset supervision. BAT_WARN_OK is LOW on warning: the old BAT_OK_N was HIGH on warning, so firmware and net naming must change explicitly. Add SYS/PACK status inputs or provide the required hardware aggregation; the step-3 pinmap is not silently assumed sufficient. Implement SERVICE_OK from actual USB/debug detection and interlock circuitry, not a firmware-only assertion. Complete GPIO isolation/default-state handling for the ADC-off state.

## Verification and outstanding evidence

KiCad 9.0.2: hierarchical export succeeded; ERC zero errors/warnings, no exclusions. Supply flags represent external module supplies only. Static envelope assertions and selected netlist-path assertions pass. Rendered child sheets inspected. No circuit simulation or hardware test performed. ERC does not establish footprint completeness.

R03/R04: replacement topology drawn and calculated, awaiting integration and transient tests. R05: hardware reset logic drawn; complete startup/IO behavior awaits integration. R06: thresholds recalculated; pack qualification, restart latch and storage recovery remain open. No review finding is declared physically verified.

Bench plan: supply ramps and fast input collapse; output load steps/release; repeated enable cycling; measured supervisor assertion/release across temperature; VCAP/reference settling; battery rebound and abrupt disconnect; USB insertion during attempted acquisition; I/O back-power checks. Probe rails at ADC pins. Recalculate endurance: regulator quiescent current and bleeder add consumption; reserve roughly 3–6 mA additional input-current planning margin until measured. This is a provisional allowance, not a guaranteed maximum.

## Manufacturer sources checked online

- ADI LT3045 Rev D, electrical characteristics, pin functions and reverse-current discussion: https://www.analog.com/media/en/technical-documentation/data-sheets/3045fa.pdf
- TI TPS3890 Rev A, pin assignment, threshold accuracy, sense current and timing: https://www.ti.com/lit/ds/symlink/tps3890.pdf
- TI SN74LVC1G08 Rev AA, DBV pin assignment and partial-power-down behavior: https://www.ti.com/lit/ds/symlink/sn74lvc1g08.pdf
- TI TPS3808 Rev N, rejected candidate's accuracy/hysteresis: https://www.ti.com/lit/ds/symlink/tps3808.pdf

This package is a reviewable replacement module, not a manufacturing release or a complete Rev C system schematic.
