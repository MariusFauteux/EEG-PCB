# Step 5 — Controller, programming and USB-C

2026-11-08 · Rev C2 · schematic integration draft, bench only

Step 5 now adds the NINA-B306-00B controller, SWD access, reset/recovery/record buttons, USB-C data and CC detection, service inhibit, and ADC startup buffers. The 11-page KiCad project integrates the previous ADC/input sheets with the Step 4 power module. The original Rev B and standalone Step 4 packages remain separate historical baselines.

**This is not a fabrication release. USB charging, USB-only board power, firmware and human-connected operation are not implemented or validated.** Step 4’s remaining review items are carried forward at the user's request.

## 1. What is connected

| Circuit | Implementation | Remaining qualification |
|---|---|---|
| Controller | U300 NINA-B306-00B, VCC and VCC_IO at 3.3 V, local bypassing | Custom B306 footprint, antenna keepout and firmware |
| ADC | Dedicated SPI GPIOs, buffered outgoing controls, DRDY input, hardware-gated reset | Startup/collapse timing and signal integrity on a prototype |
| Programming | J300 10-pin SWD, target voltage sense, SWCLK/SWDIO/SWO/reset, 100 Ω series resistors | Exact connector and probe compatibility; initial firmware |
| User controls | Reset, recovery and record buttons | Firmware behavior and debounce |
| USB-C | J310 USB4105-GF-A, USB 2.0 pair to MCU, separate CC1/CC2, ESD protection | PCB routing, connector drawing audit and USB compliance |
| CC detection | TUSB320LAI in sink mode, I²C at address 0x47, interrupt to MCU | Firmware source-current handling and charger bootstrap |
| Service inhibit | VBUS presence, compatible SWD adapter presence and interlock input gate SERVICE_OK | Physical interlock mechanism; fault/restart behavior |
| Digital supply | TPS62162 fixed 3.3 V from SYS | Capacitor derating, inductor footprint, power budget and measurements |
| Future peripherals | Separate SD SPI and trigger/photodiode/charger GPIO allocations | Peripheral circuits are not present |

The new package is self-contained. Open `EEG_RevC_Step5.kicad_pro` in KiCad 9. The `preview` directory contains SVGs of all pages; `bom.csv` and `controller_pinmap.csv` expose component and GPIO assignments.

## 2. Programming and connection guide

Use SWD to install initial firmware and recover failed firmware. Native USB hardware does not establish that a USB bootloader is installed. The module’s reset function must be configured appropriately in the nRF52840 UICR; recovery/record buttons only acquire meaning after firmware is written.

| J300 pin | Function | Note |
|---|---|---|
| 1 | 3.3 V target reference | Probe voltage sense; do not use as a probe power output |
| 2 | SWDIO | Through R350, 100 Ω |
| 3, 5 | Ground | Common debug reference |
| 4 | SWCLK | Through R351, 100 Ω |
| 6 | SWO | Through R352, 100 Ω; optional trace |
| 7 | Key / no connection | Connector keying still to be selected |
| 8 | No connection | No JTAG TDI function |
| 9 | SWD_ABSENT | Compatible adapter must ground this to assert debug presence |
| 10 | MCU reset | Through R353, 100 Ω; also supervised by DIGITAL_OK |

Pin 9 detection is not universal: verify the chosen probe/cable. J300 pin 9 must not be treated as an independently reliable safety detector. SWD and USB share board ground.

For eventual bench bring-up: disconnect all electrodes, use a current-limited simulator at J400 (SYS, PACK_SENSE, GND; 6.8–8.4 V nominal test range), verify the rails, connect a compatible SWD probe, and program the initial firmware. PACK_SENSE is a separate supervisor input for fault simulation, not a charger port. These are proposed bench steps, not tests already performed.

USB-C later carries configuration/data once suitable firmware enumerates. In this schematic USB supplies the dedicated module VBUS pin, the CC detection input and service detector, **not SYS or the MCU's VCC rail**. External bench power is therefore required. No USB-only startup claim is made.

## 3. Why the ADC interface changed

During startup or faults, a running MCU could otherwise drive signals into an ADC whose analog supply is invalid. Five SN74LVC1G126 buffers gate SCLK, DIN, CS, START and PWDN. Their active-high enable is:

`ADC_IO_READY = ANALOG_OK AND DIGITAL_OK AND ANA_ENABLE`

Each ADC-side control has a 10 kΩ pulldown; each MCU-side signal has a 100 kΩ pulldown. The buffer outputs become high impedance when disabled and the ADC control nodes go low. Series resistors are 33 Ω, provisional for edge damping, not level shifting. DOUT uses 33 Ω and DRDY uses 100 Ω to the MCU. ADC reset retains the Step 4 hardware logic and adds a 33 Ω series resistor plus a local 100 kΩ pulldown.

DVDD remains powered from the digital rail while AVDD is inhibited. This circuit is a startup-control measure, not a proof of safe behavior under every partial-power condition. Firmware must set CS high, hold START low, release PWDN/reset in the required order, observe ADS1299 startup delays, and verify registers before conversion. Timing, transients and powered/unpowered I/O currents require bench validation. The existing Step 4 reset-release margin and missing restart latch remain open.

## 4. USB-C and charging boundary

A USB-C connector does not perform battery charging. The planned BQ25798 buck-boost stage is still required to charge an 8.4 V 2S pack from 5 V USB. It must include current-limited startup, source-current policy, pack temperature sensing, pack protection/balancing and a power path. None of those charger functions are represented by the USB connector alone.

TUSB320LAI supplies sink CC terminations internally; adding parallel external 5.1 kΩ Rd resistors would change the termination. PORT and ADDR are grounded; EN_N is low. The VBUS_DET connection uses 887 kΩ, within the datasheet's stated 855–920 kΩ range. The MCU receives CC interrupts and can read source advertisement over I²C. Charger firmware must not assume 3 A availability, and legacy/default-current sources need appropriate handling.

A6/B6 are joined as D+, A7/B7 as D−; CC1 and CC2 remain distinct. USB data goes to dedicated module USB pins, not ordinary GPIO. No external USB pullup or data series resistor was added to the module interface. Route the pair over a continuous reference plane with impedance and geometry determined by the PCB stack-up; put ESD parts near the connector.

TPD2E2U06DCKR arrays protect data, CC and VBUS. The DCK pin map is **1 = IO1, 2 = IO2, 3 = GND**. D312 has both I/O pins on VBUS. It is an ESD suppressor, not a DC overvoltage cutoff or a current limiter. USB input fault protection remains part of power-entry/charger integration.

The VBUS service detector uses a 10 kΩ/100 kΩ divider and two SN74LVC1G14 inverters. Nominal input is 0.909 × VBUS (4.55 V at 5 V); the first inverter produces USB_ABSENT. The part permits inputs up to 5.5 V in its recommended range and has partial-power-down protection. This does not protect against an arbitrary overvoltage source. Verify insertion/removal thresholds and unpowered behavior on the assembled system.

## 5. Hardware inhibit is not isolation

`SERVICE_OK = USB_ABSENT AND SWD_ABSENT AND INTERLOCK_CLOSED`

SERVICE_OK feeds the Step 4 analog-enable path. The J301 interlock input defaults low and must be closed only in the recording position. The physical electrode/service interlock is not designed yet. An unpowered USB cable can connect board ground without asserting VBUS; a debug cable can fail to assert pin 9. Therefore these detectors supplement the electrode-disconnection boundary and do not create galvanic isolation.

No persistent restart latch was added. If RUN_REQUEST stays high, removing the inhibiting condition can permit restart. Firmware should clear the run request on a fault, but the deferred hardware latch remains a separate requirement. Do not mark the overall safety finding closed.

## 6. Pin allocation and firmware notes

The 33 previously allocated GPIOs are retained with names clarified to match the integrated netlist. Pads 38/P1.10 and 39/P1.11 now add SYS_OK and PACK_OK, bringing the allocation to 35 unique GPIOs. SWO uses fixed module pad 8. Fast ADC/SD clocks stay off the module's radio-sensitive GPIO group; slow status/control functions occupy those pads.

The ADC and SD buses are separately allocated. SD, trigger, photodiode, charge-control and status-LED pins currently terminate in provisional defaults; they do not imply populated peripherals. Keep unused outputs disabled until those circuits exist. BAT_WARN_OK is active high for a healthy pack and low for a warning, as changed in Step 4.

## 7. Checks completed and release limits

- KiCad 9.0.2 ERC: **zero errors and zero warnings**, with no exclusions in the generated project.
- 100 assertions pass on the KiCad-exported XML netlist: all module connections, 35 unique GPIO allocations, ADC paths, reset/service logic, connector orientation contacts, CC/ESD pin mapping and separation of power nets.
- New schematic pages were rendered and visually checked; parts that overlapped page/title boundaries were repositioned, followed by fresh export/ERC/checks.
- No simulation, physical prototype, firmware execution, USB enumeration, radio test or charge test was performed.

ERC uses the symbol definitions supplied here; it is not an independent manufacturer pin-map audit or compliance assessment. The pin map was checked against the manufacturer documents listed below, while the automated checks verify that the intended map reached the exported schematic.

The BOM contains 256 references, with 32 missing footprints and 224 without exact MPNs, largely generic passives and unfinished connectors. NINA-B306 and TUSB320 require exact footprint review; symbolic EGP/EAGP ground groups must be translated to the module land pattern. Do not substitute the installed NINA-B111 footprint. Capacitor effective values, connectors, antenna keepout and mechanical interlock need completion before layout release. All assigned footprints also require audit.

Step 4's narrow supervisor-release margin, collapse dynamics, restart latching and power-component qualification remain unresolved. Input protection/BIAS validation, SD, event circuitry, charger implementation and the complete 12-finding closure review are still outstanding. This milestone establishes the controller/service schematic, not closure of all review findings.

## 8. Online manufacturer references checked

Accessed 2026-11-08. These are primary references for pin identities and electrical requirements; engineering choices such as damping resistor values remain provisional.

1. [u-blox NINA-B3 datasheet, UBX-17052099 R15](https://content.u-blox.com/sites/default/files/NINA-B3_DataSheet_UBX-17052099.pdf): NINA-B306 selection, Table 7 pin map, power and radio-sensitive GPIO restrictions.
2. [u-blox NINA-B3 system integration manual, UBX-17056748 R15](https://content.u-blox.com/sites/default/files/NINA-B3_SIM_UBX-17056748.pdf): open-CPU programming, USB/power and integration requirements.
3. [TI TUSB320LAI, SLLSEQ8D](https://www.ti.com/lit/ds/symlink/tusb320lai.pdf): sink straps, integrated termination, VBUS resistor and I²C interface.
4. [TI TPD2E2U06](https://www.ti.com/lit/ds/symlink/tpd2e2u06.pdf): DCK package pinout and protection limits.
5. [TI SN74LVC1G14](https://www.ti.com/lit/ds/symlink/sn74lvc1g14.pdf): Schmitt input, input-voltage range and Ioff.
6. [TI SN74LVC1G126](https://www.ti.com/lit/ds/symlink/sn74lvc1g126.pdf): active-high output enable and tri-state behavior.
7. [GCT USB4105](https://gct.co/connector/usb4105): connector family; exact drawing-to-footprint audit remains required.

## 9. Reproducing the electrical checks

Use Python with `sexpdata` for generation and KiCad 9 for export. The generator intentionally assigns fresh UUIDs; semantic connectivity is the validation target.

```bash
python build_step5.py
kicad-cli sch export netlist --format kicadxml -o netlist.xml EEG_RevC_Step5.kicad_sch
kicad-cli sch erc -o erc.rpt EEG_RevC_Step5.kicad_sch
python validate_step5.py
kicad-cli sch export svg -o preview/ EEG_RevC_Step5.kicad_sch
```

The immutable `baseline` directory and baseline pin map allow regeneration without older packages. `Step4_Power_Review.md` is included for the deferred power-review context.
