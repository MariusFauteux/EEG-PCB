# Step 11: BQ25798 charger, power path, ship FET and pack connector (Rev C8)

2026-11-08. Status: drawn on a new `charger` sheet and checked by netlist assertions and `hardware/scripts/analyze_power.py`. Nothing has been simulated or measured. Rev C8 is a bench schematic candidate and is not released for fabrication or for connection to a person.

Step 11 replaces the J400 bench input with the charger chosen in D23: a 5 V-only USB-C sink feeding a TI BQ25798 buck-boost charger and power path, with a protected 2S Li-ion pack. It also meets the SYS hold-up requirement from Step 10 (D39) and adds a real soft-off, which the board did not have before.

## 1. How power now flows

| Condition | What powers SYS | Charger converter | Analogue rail |
|---|---|---|---|
| Battery only (recording) | Pack through Q400 (ship FET) and the BQ25798's internal battery FET (11 mΩ) | Not switching | Allowed (SERVICE_OK can be high) |
| USB present | BQ25798 buck-boost from VBUS; pack charged if CE is enabled | Switching at 1.5 MHz | Off: USB presence holds SERVICE_OK low |
| USB, no pack | BQ25798 regulates SYS at VSYSMIN (7.2 V nominal for 2S) | Switching | Off (USB present) |
| Ship mode (soft-off) | Nothing: Q400 is open | Off | Off |

Because the converter switches only while USB is attached, and the service rule (D21) already requires the electrodes to be disconnected then, charger switching noise cannot reach an EEG recording. This is also why the 1.5 MHz / 1.0 µH setting chosen in the architecture review (PROG = 6.04 kΩ) is kept: there is no acquisition-time reason to prefer 750 kHz.

## 2. Pin-level implementation (TI SLUSDV2C)

| Pins | Connection | Basis |
|---|---|---|
| VBUS, VAC1, VAC2 | All on USB_5V | "VBUS input only": no ACFET/RBFET, so VAC1 and VAC2 tie to VBUS (Table 7-5) |
| ACDRV1, ACDRV2 | GND | Required for the single-input configuration |
| D+, D- | Not connected | USB data belongs to the MCU (architecture review). Without D+/D-, BC1.2 detection cannot be relied on and an "unknown adapter" result would allow 3 A. The hardware ILIM ceiling below covers this. |
| PROG | 6.04 kΩ 1 % | 2S, 1.5 MHz (Table 7-1): ICHG 1 A, VREG 8.4 V, VSYSMIN 7 V POR defaults |
| ILIM_HIZ | REGN × 10.0k/(27.0k + 10.0k) | Hardware input-current ceiling (section 3) |
| TS | 5.23 kΩ REGN–TS, 30.1 kΩ TS–GND, pack NTC on J401 pin 3 | TI 103AT window (section 4) |
| CE | 100 kΩ pull-up to REGN; Q401 (BSS138) to GND, gate on CHARGE_REQUEST | Charging is off unless the running MCU asks for it (section 5) |
| QON | POWER button SW400 to GND; BAT54 to POWER_BUTTON_N (module pad 37) | Wake from ship mode and an MCU-readable button (section 6) |
| SDRV | Gate of Q400 (CSD17571Q2) | Ship FET between BAT and the pack (section 6) |
| BATP | 100 Ω to the pack side of Q400 | TI: 100 Ω series to the pack positive terminal |
| SCL, SDA, INT | POWER_SCL/SDA (4.7 kΩ pull-ups on the controller sheet), CHARGER_INT_N (100 kΩ pull-up, pad 45) | 7-bit address 0x6B; no conflict with TUSB320LAI (0x47) or MCP4725 (0x60) |
| STAT | Green LED and 2.2 kΩ from REGN | Lit only with USB present: on while charging, 1 Hz blink on a fault |
| BTST1, BTST2 | 47 nF 25 V to SW1 and SW2 | TI: ≥ 10 V, 47 nF |
| REGN | 4.7 µF 10 V | TI: 10 V, 4.7 µF. REGN biases only ILIM, TS, CE and the LED, as TI permits |

**Capacitors.**
- VBUS: one 10 µF + 100 nF. TI's example uses two 10 µF, but its stated minimum is 2 µF effective. With C321 (1 µF at the connector), one part keeps VBUS bulk near the USB Type-C limit of 10 µF for a sink, which bounds inrush current into a Mac port. A check asserts the parts on USB_5V.
- PMID: 3 × 10 µF + 100 nF.
- BAT: 2 × 10 µF, on the charger side of Q400.
- SYS: section 7.

**Inductor.** 1.0 µH Coilcraft XFL4020-102ME, footprint `L_Coilcraft_XxL4020`. TI says 1.5 MHz works only with 1 µH. Saturation current must exceed the larger of input current and charge current plus half the ripple. With the input limited to ≤ 1.5 A, a rating of ≥ 3 A is ample. Confirm the exact suffix and rating against the Coilcraft data sheet.

## 3. Input-current ceiling

The ILIM_HIZ pin sets an upper clamp on input current, read at power-up: V = 1 V + 0.8 Ω × ILIM. While EN_EXTILIM = 1 (the reset default), the register cannot exceed it. The divider from REGN (4.6–5.0 V at VBUS = 5 V) with 1 % resistors gives:

| | Ceiling |
|---|---:|
| Nominal (REGN 4.8 V) | 0.372 A |
| Minimum corner | 0.281 A |
| Maximum corner | 0.464 A |

The maximum is below the 500 mA USB default, so an unconfigured board, a crashed MCU or a watchdog reset can never draw more than a default port allows. TI also specifies that a 500 mA setting regulates at 415–500 mA, so regulation sits below the setting. At the ceiling, charging is limited to about 0.17 A, which is enough for the board to start from a flat pack.

After start-up, firmware reads the TUSB320LAI advertisement (1.5 A or 3 A Type-C current), sets EN_EXTILIM = 0, and programs IINDPM to the allowed budget. The 0.5 A charge target needs about 1.0 A at 5 V. A watchdog expiry resets the registers, so the hardware ceiling returns automatically.

## 4. Pack temperature window

The TS divider uses E96 values (5.23 kΩ, 30.1 kΩ) in place of TI's calculated 5.24 kΩ / 30.31 kΩ. A beta model of the 103AT-2 (10 kΩ, B = 3435 K) against the comparator thresholds reproduces TI's own window, which validates the model:

| Network | Charge suspended below | Charge suspended above |
|---|---:|---:|
| TI example | 1.0 °C | 59.9 °C |
| Selected E96 | 1.0 °C | 59.9 °C (shift 0.06 °C) |

The 60 °C upper limit, with JEITA reductions above T3, is the charger default and is higher than many cell specifications allow for charging (often 45 °C). Firmware must set JEITA_VSET/ISETH (or T3) from the chosen pack's data sheet. The pack must contain a 10 kΩ 103AT-type NTC on its third wire. If the thermistor is missing, TS reads as cold and charging is suspended, which is the safe direction.

## 5. Charge enable defaults

CE is active-low and must never float. R406 pulls it to REGN, so it is high (charging disabled) whenever USB is present. It only goes low when Q401 conducts, which requires the MCU to be running and driving CHARGE_REQUEST high (R380 holds it low otherwise). This meets the architecture rule that charging stays inactive until the pack, temperature, source and configuration checks pass. Charging stops whenever the MCU is in reset, unprogrammed or crashed. Without USB, REGN is off and CE has no effect.

## 6. Soft-off and power button

**Ship FET.** Q400 (CSD17571Q2, 30 V, 29 mΩ max at VGS 4.5 V, SON 2 × 2) sits between the charger BAT pins and the pack. Its source is on the charger side, so the body diode blocks the pack from discharging into the board when the FET is off. SDRV drives the gate to about VBAT + 5 V. The gate leakage limit (100 nA at 20 V) is of the same order as the 100 nA SDRV drive, but the gate sits at only ~5 V, so this is not expected to matter. Confirm on the bench that the gate reaches full enhancement.

**Turning off.** Firmware writes SDRV_CTRL = 10 (ship mode), for example after a long press of POWER. Q400 opens and SYS, 3.3 V and both supervisor dividers on PACK_POS lose power. The pack then supplies only the BQ25798 BATP quiescent current (≤ 16 µA) plus Q400 leakage (≤ 1 µA). The supervisor dividers deliberately moved behind the ship FET: on the pack side they would have drawn about 0.3 mA.

**Turning on.** Hold POWER for 1 s (tSM_EXIT, default) or plug in USB. Holding POWER for 10 s forces a system power reset (Q400 off for 350 ms), a hardware recovery for a hung MCU.

**Button sense.** QON idles near 3.2 V on its internal 200 kΩ pull-up, close to the nRF52840's I/O limit, so it does not go to the module directly. BAT54 (anode on POWER_BUTTON_N with a 10 kΩ pull-up to 3.3 V, cathode on QON) gives the MCU a low (about 0.3 V) when the button is pressed, and blocks QON from feeding 3.3 V when the board is off. Module pad 37, previously the reserved POWER_HOLD output (R381 removed), becomes the POWER_BUTTON_N input.

## 7. SYS hold-up (Step 10, D39)

SYS now has 5 × 22 µF 25 V X7R 1210, a 100 µF 16 V OS-CON (16SVP100M) and 100 nF. Both the 1210 retention at 8.4 V (taken as 40 %) and the OS-CON tolerance (−20 %) are assumptions. On that basis the effective capacitance is about 124 µF:

| Requirement (D39) | Needed | Estimated |
|---|---:|---:|
| Average load (≈ 70 mA from SYS) | 24 µF | 124 µF (5×) |
| Peak digital load (≈ 377 mA) | 127 µF | 124 µF (≈ 98 %) |

So the SYS_OK path resets the ADC while AVDD is still regulated at average load with wide margin, and very nearly at peak load. The ANALOG_OK backstop and the five-sample invalidation rule from D39 still apply. The OS-CON's leakage current adds a small drain while recording and needs checking against the data sheet. In ship mode it has no effect, because Q400 isolates it.

## 8. Other effects

- **J400 removed.** Bench work now uses the pack connector J401 with a current-limited supply set to 6.8–8.4 V, plus a 10 kΩ resistor in place of the NTC. Never connect two sources.
- **PACK_POS** is now the charger BAT node (Q400 source). While Q400 is on, it equals the pack voltage minus I × 29 mΩ, so the PACK_OK and BAT_WARN_OK thresholds are unchanged.
- **USB without a pack.** BAT may see detection pulses, so PACK_OK can toggle. The analogue rail is already held off by SERVICE_OK.
- **Ground and noise.** The converter's hot loops (VBUS/PMID capacitors, SW1, SW2, the inductor, SYS capacitors) belong in a compact island away from the electrode inputs and the ADC. Charging happens only with the electrodes disconnected.

## 9. Firmware requirements added

1. At start-up, read the TUSB320LAI advertisement, then set EN_EXTILIM = 0 and IINDPM within the allowed budget. Disable AUTO_INDET_EN and HVDCP.
2. Set ICHG = 0.5 A, VREG = 8.4 V and the JEITA limits from the pack data sheet. Drive CHARGE_REQUEST high only after the pack, temperature, source and configuration checks pass.
3. Service the BQ25798 watchdog (40 s default) or disable it deliberately, knowing that expiry restores the hardware ceiling.
4. Keep the BQ25798 ADC disabled when not needed: about 540 µA with it enabled versus 17–24 µA without.
5. Soft-off: on a long POWER press, finish the SD shutdown sequence (D31), then write SDRV_CTRL = 10.

## 10. Verification

- `hardware/rebuild.sh`: 387 netlist assertions pass (348 at Step 10). KiCad ERC: 0 errors, 0 warnings.
- New assertions cover every BQ25798 pin, the strap networks, the ship FET orientation, the CE default, the BAT54 polarity and the VBUS bulk limit.
- A pin-membership comparison with the Step 10 netlist (`baseline/step10_netlist.xml`) confirms the scope: only the 35 charger, pack and button parts were added; only J400 and R381 were removed; every other pin connection is unchanged.
- `analyze_power.py` adds four rules, all passing: ceiling ≤ 500 mA at all corners; ceiling ≥ 200 mA for start-up; TS window within 1 °C of TI's; SYS hold-up ≥ 3 × the average requirement.

**Not done and still required.**
- A footprint for the BQ25798 VQFN-HR (RQM), which KiCad does not stock.
- A pad audit of Q400's Texas_DQK footprint.
- DC-bias curves for the 1206 and 1210 capacitors.
- Choosing the actual pack and its connector.
- Thermal design during charging.

**Bench tests:** start-up from USB with a flat pack, a missing pack and a missing NTC; input current against the ceiling on a 500 mA port; charge to termination; ship-mode entry, wake by button and by USB, and leakage; the 10 s POWER reset; pack-disconnect captures of SYS, AVDD and ADS_RESET_N, repeating the Step 10 test with the real SYS capacitance.

## Sources

- TI BQ25798, SLUSDV2C (revised June 2026): pin functions, PROG table, ILIM_HIZ equation, REGN limits, IINDPM accuracy, quiescent currents, ship FET control, QON thresholds, JEITA thresholds, recommended and minimum capacitances, inductor rule, address 0x6B. Downloaded and read for this step.
- TI CSD17571Q2, SLPS393A: ratings, RDS(on), gate leakage, pinout.
- Murata GRM32ER71E226KE15L and Panasonic 16SVP100M distributor listings (Step 10 and this step). Effective capacitance still to be read from the manufacturer curves.
