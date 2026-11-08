# Step 10: closing the deferred Step 4 power review (Rev C7)

2026-11-08. Status: schematic and calculation changes, checked by netlist assertions and `hardware/scripts/analyze_power.py`. Nothing here has been simulated at transistor level or measured. Rev C7 is a bench schematic candidate and is not released for fabrication or for connection to a person.

Step 4 left four items open: the ≈ 11 mV analogue reset release margin, behaviour while a rail collapses, the missing persistent restart latch, and capacitor qualification. Each is now closed at calculation level, or turned into a stated requirement on a later step. Working through them also turned up a fifth problem that was already present: slow edges into the reset logic.

## 1. Analogue rail and reset release margin

**Problem.** At 5.050 V the LT3045's worst-case minimum output only just exceeded the worst-case release threshold of the analogue supervisor. Recomputing with the same limits plus the CSET leakage term (below) gives 8.5 mV, not 11 mV. A board at that corner could hold the ADC in reset indefinitely. The fault is detectable but not acceptable.

**Fixed budget.** The ADS1299 needs AVDD between 4.75 and 5.25 V. The LT3045 output spread (ISET 98–102 µA over the full temperature range, ±2 mV offset, ±0.2 % resistors) takes ≈ 230 mV of that 500 mV window. The supervisor spread from assertion minimum to release maximum (±1 % threshold, 0.325–0.825 % hysteresis, ±100 nA sense current) takes ≈ 162 mV. Only ≈ 110 mV is left, to share between three margins:

- M1: rail minimum above the release maximum (startup)
- M2: assertion minimum above 4.75 V (fault detection)
- M3: rail maximum below 5.25 V (ADC operating ceiling)

At C6 the shares were 8.5 / 14.0 / 86.7 mV. M2 is already small and cannot be reduced without letting the ADC run below 4.75 V before reset. M3 has the spare. Equal M1 and M3 occur at 5.088 V.

**Change.** RSET = R201 50.5 kΩ + R207 383 Ω (both 0.1 %, ≤ 10 ppm/K) = 50.883 kΩ, giving 5.088 V nominal. The supervisor divider is unchanged.

| Margin | C6 (5.050 V) | C7 (5.088 V) |
|---|---:|---:|
| Rail envelope | 4.935–5.163 V | 4.972–5.202 V |
| M1 release margin | 8.5 mV | **45.9 mV** |
| M2 assertion above 4.75 V | 14.0 mV | 14.0 mV |
| M3 below 5.25 V | 86.7 mV | **47.6 mV** |
| SYS inhibit above LDO dropout (50 mA) | 199.7 mV | 160.6 mV |

**CSET leakage.** The 100 µA SET current flows through RSET, so leakage into CSET lowers the output. Murata's class-II insulation rule (≥ 500 Ω·F, rated voltage, room temperature) bounds a 4.7 µF part to ≤ 48 nA at 5.1 V, which is 2.4 mV. Insulation resistance falls steeply with temperature, so a hot board may lose noticeably more. This is included in the C7 envelope at room temperature only. Measure output against temperature on the bench.

**Not changed.** RILIM (≈ 100 mA), PGFB (fast start ends near 4.5 V), the 4.7 kΩ bleeder (now 1.08 mA) and the supervisor thresholds. SYS cutoff, pack cutoff and warning thresholds are unchanged and listed in `checks/power_analysis.json`.

## 2. Rail-collapse behaviour

There are two independent routes by which a collapsing supply puts the ADC into reset.

**Path A, via SYS_OK.** SYS_OK asserts at ≥ 5.693 V. The LT3045 stays in regulation down to rail maximum + 330 mV dropout ≈ 5.532 V. If SYS_OK responds while SYS falls through this 161 mV window, ANA_ENABLE goes low. That forces ADS_RESET_N low through U224/U225 within gate delays (nanoseconds), while AVDD is still in regulation. TPS3890 gives only a typical tPD(f) (18 µs at VDD 3.3 V, 5 % overdrive). Allowing 3× that for small overdrive, SYS must fall no faster than ≈ 3.0 mV/µs. That needs ≈ 24 µF of effective SYS capacitance at average load (≈ 70 mA from SYS), or ≈ 127 µF at the 480 mA digital peak. The current SYS capacitance (C202, C240) does not meet the peak figure.

**Path B, via ANALOG_OK.** If path A loses the race, the LT3045 drops out. Its reverse-current blocking keeps AVDD from discharging back into SYS, so AVDD decays on its own output capacitance. ANALOG_OK then asserts above 4.764 V, and after the response time the ADC has seen at worst:

| Analogue load | C_out effective | AVDD slew | AVDD when reset asserts (worst) |
|---|---:|---:|---:|
| 10 mA | 20 µF | 0.5 mV/µs | 4.737 V |
| 50 mA | 20 µF | 2.5 mV/µs | 4.629 V |
| 50 mA | 10 µF | 5.0 mV/µs | 4.494 V |

So the ADC can run briefly (tens of µs) below its 4.75 V minimum before reset. This is outside the recommended operating range but far from the absolute maximum, and it cannot damage the device. The samples involved may be wrong.

**Decision.**
- Accept path B as the backstop. Firmware and host software treat the last 5 samples before any supervisor-initiated stop (ANALOG_OK, SYS_OK or PACK_OK falling) as invalid. With 1 kS/s and the ADC's digital filter delay, this covers the window above.
- Make path A the normal route by sizing SYS hold-up capacitance at the charger step. BQ25798 integration must give ≥ 30 µF effective on SYS at average load, and should aim for ≥ 130 µF effective if path A is to win at peak digital load. This becomes a requirement on Step 11, not a change here.
- Digital collapse: SYS reaches the analogue cutoff long before the 3.3 V buck drops out, so analogue power and the ADC reset are already off when DIGITAL_OK asserts. The logic and supervisors keep working down to ≈ 1.5 V (TPS3890 VDD minimum; AUP gates operate from 0.8 V).

## 3. Persistent restart latch

**Problem.** TPS3890 hysteresis is only 0.325–0.825 %, about 36 mV at the pack threshold. Removing 50 mA of analogue load, plus chemical relaxation, can lift the pack by more than that. If RUN_REQUEST stayed high (firmware bug, MCU in reset with a pin floating high, a debugger halt), analogue power could cycle on and off around the cutoff.

**Change (new sheet `restart_latch`).**
- U226 (SN74AUP1G08): RUN_PERMIT = POWER_OK · SERVICE_OK, where POWER_OK = SYS_OK · PACK_OK from U220. POWER_OK is now a global net.
- U227 (SN74LVC1G74DCUR): D flip-flop with D and PRE̅ high, clocked by RUN_REQUEST. CLR̅ = RUN_PERMIT, so any SYS, pack or service fault clears RUN_ARMED asynchronously.
- U228 (SN74AUP1G08): RUN_LATCHED = RUN_REQUEST · RUN_ARMED. This replaces RUN_REQUEST at U221 pin 1.
- TP230 brings out RUN_ARMED for bench work.

The result is ANA_ENABLE = SYS_OK · PACK_OK · SERVICE_OK · RUN_REQUEST · RUN_ARMED. Behaviour:

- Stop: RUN_REQUEST low removes analogue power at once, as before.
- Fault: RUN_ARMED clears and stays clear after the fault goes away (battery rebound, USB unplugged, interlock re-closed), even with RUN_REQUEST held high.
- Restart: firmware confirms SYS_OK and PACK_OK, drives RUN_REQUEST low for ≥ 1 µs, then high. The rising edge sets RUN_ARMED only while RUN_PERMIT is high.
- Power-up: the supervisors hold SYS_OK and PACK_OK low for at least 8.2 ms after 3.3 V is valid, so CLR̅ is low as soon as U227 is powered (≥ 1.65 V) and the latch starts cleared. A random power-up state cannot enable the analogue rail.

**Constraints.** The SN74LVC1G74 clock needs input edges of ≤ 10 ns/V, so RUN_REQUEST must come straight from the GPIO with no RC filter. D = 1, so extra clock edges are harmless. A noise edge on RUN_REQUEST can re-arm the latch only while RUN_REQUEST is already high, which is the "run" state anyway. RUN_REQUEST keeps its R230 100 kΩ pull-down. Firmware learns that a fault cleared the latch from ANALOG_OK and the SYS_OK/PACK_OK inputs, so no new MCU pin is used.

## 4. Edge rates into the reset logic (new finding)

The supervisor outputs are open-drain with 100 kΩ pull-ups, and they drove SN74LVC1G08 inputs specified for transitions of ≤ 10 ns/V. With 10–30 pF of node capacitance, the rising edges were 0.8–2.5 µs/V, two orders of magnitude too slow. A non-Schmitt CMOS input that sits near threshold can oscillate, so the ADC reset release and the analogue enable could chatter. SWD_ABSENT (100 kΩ) and INTERLOCK_CLOSED (10 kΩ pull-down, mechanical contact) had the same problem.

**Change.**
- All twelve 2-input AND gates (U220–U226, U228, U330–U333) become SN74AUP1G08DBVR. This part has Schmitt-trigger inputs (typically 250 mV hysteresis at 3.3 V), is specified for ≤ 200 ns/V and has the same SOT-23-5 pinout.
- Pull-ups R212, R215, R218, R221 and R224, and the defaults R354 and R358, become 4.7 kΩ. That gives ≤ 118 ns/V at up to 30 pF, so layout must keep each of these nets ≤ 30 pF. The cost is 0.70 mA from 3.3 V for each asserted monitor; ANALOG_OK is asserted whenever the analogue rail is off.
- The LVC buffers U310–U314 and the LVC1G14 Schmitt inverters are unchanged. Their inputs come from gate outputs or MCU pins.

The AUP gates drive about 4 mA at 3.3 V. Their loads are logic inputs, the LT3045 EN/UV pin with its 100 kΩ pull-down, and ADS_RESET_N through 33 Ω, so 4 mA is ample. The DBVR variant is rated −40 to 85 °C.

## 5. Capacitor selection

| Ref | Function | Selected | Basis | Still to confirm |
|---|---|---|---|---|
| C203, C204 | LT3045 output | 22 µF 25 V X7R 1210, Murata GRM32ER71E226KE15L | Was 22 µF 16 V 0805, which loses most of its capacitance at 5 V. A 25 V 1210 part keeps far more. | ≥ 10 µF total effective at 5.25 V and 85 °C, read from Murata's DC-bias curve, including ageing |
| C201 | CSET (noise and soft start) | 4.7 µF 16 V X7R 0805, GRM21BR71C475KE51L | Leakage bound above (≤ 48 nA at room temperature) | Hot leakage; measure VOUT against temperature |
| C211, C213 | 100 nF release delay (ANALOG_OK, DIGITAL_OK) | 100 nF C0G 5 % 50 V 1206, GRM31C5C1H104JA01L | Delay 82–150 ms over VCT, ICT and capacitor tolerance (78–158 ms with the old X7R) | None beyond the footprint audit |
| C215, C217, C219 | 10 nF release delay (SYS, PACK, warning) | 10 nF C0G 5 % 50 V 0603, GRM1885C1H103JA01D | Delay 8.2–15.1 ms | Same |

C202 (SYS input), C240 and C241 (digital buck) are left for the charger step, where the SYS hold-up requirement in section 2 sets their size. All exact MPNs above were found in distributor listings. Their DC-bias and insulation figures still have to be read from the Murata datasheets or SimSurfing; nothing here claims a measured effective value.

## 6. Firmware requirements added

1. To start acquisition: check SYS_OK and PACK_OK, drive RUN_REQUEST low for ≥ 1 µs, then high. Never assume the latch survives a fault.
2. After any falling ANALOG_OK, SYS_OK or PACK_OK, mark the final 5 samples before the stop invalid in the record stream.
3. Drive RUN_REQUEST as a plain push-pull GPIO with no software PWM and no external RC.

## 7. Verification

- `hardware/rebuild.sh`: 348 netlist assertions pass (310 at Step 9). KiCad ERC reports zero errors and 308 warnings, all of them local footprint-library configuration warnings.
- A pin-membership comparison against the Step 9 netlist (`baseline/step9_netlist.xml`) confirms the scope: only R207, U226–U228, C226–C228 and TP230 were added; only R201 pin 2 and U221 pin 1 changed connection; every other pin connection is unchanged.
- `analyze_power.py` fails the build if the release margin or the ceiling margin drops below 40 mV, if the analogue reset asserts at or below 4.75 V, if the SYS inhibit falls into LDO dropout, or if the chosen pull-up breaks the AUP edge limit at 30 pF.

**Bench tests that would close this step physically:** VOUT at −10, 25 and 60 °C; supervisor assertion and release thresholds on ramped supplies; repeated pack-disconnect captures of SYS, AVDD, ANA_ENABLE and ADS_RESET_N on one time base; a battery-rebound test with RUN_REQUEST held high (analogue power must stay off); supervisor-output rise times on the assembled board.

## Sources

- TI TPS3890 data sheet, SLVSD65A: thresholds, accuracy, hysteresis, ISENSE, ICT, VCT, tPD, VPOR. Downloaded and read for this step.
- TI SN74LVC1G74 data sheet, SCES794G: pinout, function table, Δt/Δv ≤ 10 ns/V at 3.3 V.
- TI SN74AUP1G08 data sheet, SCES502Q: Schmitt-trigger inputs, Δt/Δv ≤ 200 ns/V, DBV pinout.
- TI SN74LVC1G11 data sheet: checked as an alternative 3-input gate; not used.
- ADI LT3045: limits as recorded in the [Step 4 review](step4_power_review.md). The data sheet could not be downloaded again during this step.
- Murata MLCC catalogue listings for the MPNs above; class-II insulation-resistance rule from the Murata specification tables.
