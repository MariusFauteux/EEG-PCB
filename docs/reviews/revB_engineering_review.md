# Rev B — external-style engineering review

Date: 2026-11-08. Reviewed baseline: EEG_ADS1299_RevB, five schematic sheets and exported netlist. This is a critical desk review by the same assistant that drafted the design, not an independent professional certification.

## Verdict

**Hold fabrication and human-connected use.** Rev B is an ADC/power subsystem draft, not a complete EEG recorder. It contains sensible building blocks and passes connectivity checks, but significant system functions and electrical qualification are missing. Earlier “complete ADS1299 and power” wording means the pins and candidate supply circuits were drawn; it must not be read as a validated or production-ready design.

Repeated checks: KiCad ERC returned zero violations; existing netlist assertions passed for all 64 ADC pin identities and key input, BIAS, supply and host connections. Reviewed the rendered core, digital-interface and power sheets, the BOM, startup instructions and calculations. These checks establish consistency with the intended drawing. They are not independent evidence that the intended circuit meets every datasheet requirement. No simulation, prototype, PCB routing, EMC, leakage or endurance test is available.

## Practical answers

| Question | Rev B today | What the finished design needs |
|---|---|---|
| Can I configure the controller? | No controller is fitted in this design. nRF52840 is planned, with no exact module selected. | Module, complete power/clock connections, pin map, SWD and firmware. |
| Can I configure the ADS1299? | The physical SPI/control interface is available on J100. No acquisition firmware is delivered. | An appropriately powered 3.3 V host and firmware implementing the startup/register/readout sequence. |
| Can I plug it into my Mac through USB-C? | No USB connector or USB circuitry exists. J100 is not USB. | USB-C connector, CC handling, protection, D+/D− routing, VBUS interface and USB firmware. |
| Can USB-C charge the battery? | No. Rev B assumes a removable protected 2S pack charged externally. | A charger matched to the exact pack, input-current control, temperature monitoring and power-path circuitry. |
| Can I record to microSD or stream over BLE? | Those are requirements, not implemented board functions. | Controller, socket, firmware, buffering and measured simultaneous throughput. |
| Can I connect electrodes to a person while USB/SWD is attached? | Not within the present design boundary. Neither connection is isolated. | Disconnect electrodes for service/charging, or design and qualify a complete isolation system before allowing that mode. |

### Programming and connection plan

Provide a keyed 10-pin Cortex debug connector or suitable Tag-Connect footprint with SWDIO, SWCLK, target-voltage reference, ground and reset. SWO is optional. Confirm reset pin and all signals against the selected module. A compatible J-Link or Nordic development kit can serve as the external SWD programmer [5]. Target-voltage reference is a voltage sense connection, not permission to parallel two power supplies.

First program through SWD. USB updates require a bootloader already installed and a recovery-entry mechanism, such as a button or accessible test pad; an arbitrary bare nRF52840 module does not acquire USB programming merely by adding a connector. Keep SWD accessible for recovery. Nordic's USB-programmable dongle explicitly includes a bootloader [6].

Use native USB for a configuration console and later firmware updates, with BLE for normal untethered recording. An nRF52840 USB interface needs its specified VBUS supply/detection arrangement and USB clock configuration [7]. If USB PD is used for charging, negotiated high voltage must **never** be routed directly to a pin specified for 5 V VBUS. The final circuit must handle that distinction.

J100 currently exposes pins 3/4/5/6 as SCLK/MOSI/MISO/CS, 7 as DRDY, 8 as START, 9 as RESET, 10 as PWDN; pins 1/14 are ground, 2 is the board's 3.3 V output, and 11–13 are monitor signals. It is a bench host interface, not a programmer connector. Do not inject USB 5 V or an external 3.3 V supply into pin 2. A separately powered host also needs a verified power-sequencing/back-powering solution; tying its GPIOs directly to an unpowered ADC is not a safe default.

### USB-C charging plan

For conventional 4.2 V/cell Li-ion chemistry, the present 2S pack requires an 8.4 V charge endpoint. A normal 5 V USB source cannot be wired directly to it. A boost-capable/buck-boost **battery charger** can charge 2S from 5 V within the available source power. Alternatively, USB PD can negotiate a higher supply for a compatible charger. A PD trigger, voltage regulator or connector alone does not implement battery charge control.

The recommended next design study is to retain 2S initially and evaluate a buck-boost charger plus proper USB-C sink/current detection. TI's BQ25798 family and USB-PD-CHG-EVM-01 illustrate this architecture [8,9]; these are reference candidates, not a selected BOM. PD is optional for a 5 V-only solution, but current limits still must follow source capability. A simple USB-C sink uses separate CC1 and CC2 pull-downs, typically 5.1 kΩ, unless incorporated in the chosen port controller [10].

Include pack temperature sensing, correct CC/CV settings, charge termination, reverse-current blocking, input protection, and a power path that prevents system load from invalidating termination. Select an independently protected pack with suitable cell balancing; a charger does not automatically replace cell protection or balancing. J200 presently has only two contacts and provides no temperature-sense connection. The pack connector and switch placement must therefore be revisited for onboard charging. Budget charger heat, inrush and noise. Charging/programming remains a service mode with electrodes disconnected; merely stopping ADC conversion does not remove an electrical path through electrodes.

A 1S battery would simplify charging but requires redesigning the analog supply to generate approximately 5 V. Do not silently substitute it into the present 2S supply.

## Findings and required actions

| ID / priority | Evidence and concern | Required closure |
|---|---|---|
| R01 — blocker | Missing MCU/module, SWD, USB-C, charger, microSD, isolated trigger and photodiode circuitry. | Complete system sheets, exact module and pin allocation, including recovery and test access. |
| R02 — blocker for human use | Input clamps are unresolved. Series resistors and battery operation do not establish patient protection. J100 shares ground; future USB/debug/trigger connections can create external current paths. | Define every operating/service connection, fault-current paths, input protection and isolation boundary; qualified system review and tests before participant use. |
| R03 — high | U2/R205/R206 yield 5.0856 V nominal. Existing approximate tolerance calculation reaches 5.2208 V, only about 29 mV below ADS1299's 5.25 V operating ceiling [1,2]. | Rework regulator accuracy/setpoint and power-good thresholds together. Include tolerances, effective capacitance, startup overshoot and load release; do not rely on nominal voltages. |
| R04 — high | D201 offers reverse discharge, but U2 permits OUT−IN only up to +0.3 V [2]. A generic SS14 does not establish a guaranteed 0.3 V clamp under all relevant conditions. | Calculate discharge currents and diode limits and test input collapse; select a guaranteed solution or regulator architecture with suitable reverse-current behavior. This is an unresolved protection risk, not a demonstrated failure. |
| R05 — high | Analog power-good is a host status input; it does not directly hold ADC reset. Firmware-only supervision depends on a functioning controller. Startup straps also pull CS low. | Design reset/brownout behavior, GPIO states and hardware gating as one system. Ensure no unintended SPI transactions or back-powering during boot, reset, debug or rail collapse. |
| R06 — high | UVLO is approximately 6.75 V on/6.21 V off after D200. Battery-terminal thresholds are higher by its load-dependent drop. Low-battery warning does not guarantee time to flush SD. | Full comparator/resistor/diode corners, pack discharge curves, restart tests, controlled shutdown and power-loss-tolerant file format. Verify 24 h using usable energy above cutoff. |
| R07 — high for EEG performance | Each input has 94 kΩ series resistance. Two legs contribute about 0.56 µV RMS thermal noise over a rectangular 0.1–100 Hz band at 300 K, before electrode/ADC noise. 220 pF gives a zero-source-impedance differential pole near 3.85 kHz. | Quantify total input noise, impedance-dependent transfer, RF/common-mode rejection, ADC digital-filter response and alias rejection. Optimize resistance/protection jointly; do not simply lower resistance without fault analysis. |
| R08 — high | BIAS feedback is 1 MΩ parallel with 1.5 nF, driving an electrode through 998 kΩ. The simple RC corner is not the closed-loop stability margin. | Simulate and measure with representative electrode impedances/cable capacitance; verify output headroom, disconnect recovery and BIAS channel selection. |
| R09 — high | SD/radio load steps and simultaneous supply startup are untested. Nominal capacitors and regulator current ratings do not establish board performance. | Select actual capacitor/inductor MPNs; check effective capacitance, saturation, loop/layout requirements and rail transients with realistic loads [3,4]. |
| R10 — medium | Internal ADC clock and independent host/event timing have no long-duration drift budget. | Budget sample-rate accuracy and event alignment; evaluate an external precision clock and hardware event timestamps. Document calibration if retaining internal clock. |
| R11 — release blocker | Switch/connector/inductor footprint work and passive procurement remain incomplete. C116 is described as tantalum but uses a generic capacitor graphic, with polarity relegated to a note. | Complete BOM/footprints and pin-1 checks; use an explicit polarized symbol and assembly polarity marks. Add physical test points for rails, reference, VCAP1, reset, clock and DRDY. |
| R12 — medium | Sheets rely heavily on disconnected net-label stubs; regulator feedback and power loops are difficult to follow visually. | Draw short local feedback/power paths with wires, group bypass parts by function, label connector directions and add cross-sheet references. This improves reviewability; net labels themselves are valid. |

## Standards and layout assessment

The schematic uses recognizable symbols, reference designators, hierarchy, explicit no-connects and ERC checks. These are useful drafting practices. They do not justify saying that the device “meets engineering standards.” There is no routed PCB to inspect for clearances, impedance, return-current paths, antenna keepout or manufacturability.

For a clinical EEG product, relevant standards include general medical electrical safety/essential performance (IEC 60601-1), EMC (IEC 60601-1-2), and the EEG-specific IEC 80601-2-26 family; the ISO catalogue lists the 2019 publication and 2024 amendment [11]. Exact applicable editions, intended-use classification and national adoption require a formal assessment. This review did not obtain or audit the full normative clauses and makes no compliance claim. The research context does not by itself validate participant electrical safety.

On the intended four-layer PCB, preserve continuous return paths, separate noisy switch/SD/radio placement from input/reference circuitry, minimize converter switching loops, keep high-impedance inputs clean and short, and follow the selected module's antenna keepout. Do not create arbitrary split grounds that force signal returns around gaps. Protection parts and connector placement must be considered before routing.

## Next milestone and acceptance evidence

1. Freeze the service/charging architecture, exact MCU module, pack requirements and connector pin budget.
2. Draw controller/SWD/USB-C/charger/storage/event sheets and resolve R03–R06 before layout release.
3. Finish input protection, BOM, footprint audits and a design-wide fault/connection review.
4. Review the actual PCB and manufacture a bench prototype only after schematic release gates close.
5. Test rail transients, reset sequencing, shorted-input noise, common-mode/offset range and BIAS stability using simulated electrodes. Repeat noise tests with SD and BLE active.
6. Demonstrate 24 h concurrent recording/streaming, timestamp integrity, reconnect behavior and deliberate power-loss recovery. Complete the separate safety qualification before participant use.

## Primary references

1. TI ADS1299 datasheet: https://www.ti.com/lit/ds/symlink/ads1299.pdf
2. TI TPS7A49 datasheet, electrical characteristics and absolute maximum ratings: https://www.ti.com/lit/ds/symlink/tps7a49.pdf
3. TI TPS6216x datasheet: https://www.ti.com/lit/ds/symlink/tps62160.pdf
4. TI TPS3700 datasheet: https://www.ti.com/lit/ds/symlink/tps3700.pdf
5. Nordic external-board programming: https://docs.nordicsemi.com/r/bundle/ug_nrf52840_dk/page/ug/dk/ext_programming_support_p19.html
6. Nordic dongle programming/bootloader: https://docs.nordicsemi.com/r/bundle/ug_nrf52840_dongle/page/ug/nrf52840_dongle/programming.html
7. Nordic nRF52840 product specification v1.8: https://docs-be.nordicsemi.com/bundle/nRF52840_PS_v1.8/raw/resource/enus/nRF52840_PS_v1.8.pdf
8. TI BQ25798: https://www.ti.com/product/BQ25798
9. TI USB-PD-CHG-EVM-01: https://www.ti.com/tool/USB-PD-CHG-EVM-01
10. Espressif USB-C hardware design guide: https://docs.espressif.com/projects/esp-iot-solution/en/latest/usb/usb_overview/usb_typec_hardware_guide.html
11. ISO catalogue, IEC 80601-2-26:2019: https://www.iso.org/standard/77773.html

No schematic components were changed during this review. Recommendations remain open until implemented and verified.
