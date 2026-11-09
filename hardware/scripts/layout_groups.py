"""Functional groups for every sub-sheet: frame title, purpose note and member references (regular expressions).

Each part must belong to exactly one group on its sheet; layout.py fails the build if one is left over.
Groups are placed in the order listed (left to right, then down). 'width' is the target row width in mm for
packing the group's parts; 'min_width' widens a frame so a long note stays readable.
"""

def g(title, note, refs, **kw):
    return dict(title=title, note=note, refs=refs, **kw)

def channel(n, j, r, d, jp):
    return g(f'Channel {n} input network',
             f'CH{n}+ and CH{n}- each pass 2 x 47k, the TVS clamp, then 4.7k into the ADC; 220 pF C0G across the pair. '
             f'JP{n} selects bipolar (1-2) or the buffered shared REF, REF_BUF (2-3), for the negative leg.',
             [f'J{j}', f'J{j+1}', f'JP{n}', f'R{n}[1-4]', f'R{r}', f'R{r+1}', f'C{n}', f'D{d}'], width=175)

GROUPS = {
 'ads1299_core': {'heading': 'ADS1299 CORE - all 64 package pins accounted for', 'notes': ['External 2.048 MHz clock (CLKSEL low, adc_interface sheet); internal 4.5 V reference; per-channel REF selection on the input sheets. DC-coupled inputs.', 'SRB1/SRB2 unused and open; their internal switches must stay off. BIASIN and BIASREF pins tied to AVSS: firmware must set BIASREF_INT = 1.', 'C121 needs >= 10 uF effective at 4.5 V after tolerance and DC bias. C116 (tantalum) positive terminal to VCAP1.'], 'groups': [
  g('ADS1299 analogue front end', 'Eight differential inputs, BIAS amplifier and SRB pins (unit A), SPI and control (unit B), supplies and reference (unit C).', ['U1'], width=400),
  g('AVDD decoupling', '+5VA: one 1 uF + 100 nF pair per AVDD pin (19, 21, 22, 56, 59) plus 10 uF bulk. Place each pair at its pin, return to AVSS.', ['C10[0-9]', 'C123'], width=190),
  g('AVDD1 star feed', 'R100 isolates the AVDD1 (charge-pump) pin 54 from the shared +5VA rail; its 1 uF + 100 nF pair sits at the pin.', ['R100', 'C11[01]', 'C125', '#FLG01']),
  g('DVDD feed and decoupling', 'R101 feeds +3V3_ADC (ADC DVDD, clock oscillator) from +3V3; one 1 uF + 100 nF pair at DVDD pins 48 and 50, plus 10 uF bulk.', ['R101', 'C11[2-5]', 'C124', '#FLG02']),
  g('Internal regulator and reference capacitors', 'VCAP1-4 are internal bypass nodes, not supplies. VREFP decoupling to AVSS sets reference noise and settling.', ['C11[6-9]', 'C12[0-2]'], width=190),
 ]},
 'charger': {'heading': 'BQ25798 2S CHARGER, POWER PATH, SHIP FET AND PACK CONNECTOR - CHARGE ONLY WITH ELECTRODES DISCONNECTED', 'notes': [
  'On battery the BQ25798 does not switch: its battery FET connects the pack to SYS. With USB present it powers SYS and charges the pack; SERVICE_OK keeps the ADC off.',
  'Firmware: read TUSB320 advertised current, then set EN_EXTILIM = 0 and IINDPM to the allowed budget; disable AUTO_INDET_EN (D+/D- not connected); set ICHG 0.5 A, VREG 8.4 V, JEITA limits from the pack data sheet; service or disable the 40 s watchdog (on expiry the hardware ceiling returns).',
  'Soft-off: firmware writes SDRV_CTRL = 10 (ship mode); Q400 opens and the whole board, supervisor dividers included, loses power. Hold POWER 1 s or plug USB to wake. Holding POWER 10 s forces a system power reset.',
  'Layout: follow the TI layout guide - VBUS/PMID/SYS/BAT capacitors and the 100 nF parts at the pins, short SW1/SW2 loop, BATP Kelvin to the pack side of Q400. Keep the converter away from the electrode inputs.'],
  'groups': [
  g('BQ25798 buck-boost charger', 'Single input on VBUS: VAC1/VAC2 tied to VBUS and ACDRV1/2 to GND (no input FETs). D+/D- unconnected: USB data stays with the MCU.', ['U400'], width=230),
  g('Input and PMID capacitors', 'VBUS: 2 x 10 uF + 100 nF as TI recommends (Step 14: the OVP soft start, not the connector, charges this bulk). PMID: 3 x 10 uF + 100 nF. 100 nF parts at the pins.', ['C40[0-6]'], width=160),
  g('Converter: inductor and bootstrap', '1.0 uH for the 1.5 MHz setting (TI: 1.5 MHz requires 1 uH). Isat must exceed the input or charge current plus half ripple.', ['L400', 'C40[789]'], width=160),
  g('SYS capacitance and hold-up', '5 x 22 uF X7R + 100 uF OS-CON + 100 nF. Step 10 needs >= 24 uF effective at average load (aim 127 uF) so SYS_OK resets the ADC before AVDD leaves regulation.', ['C41[0-6]'], width=210),
  g('Battery side and ship FET', 'Q400 between pack and BAT, source on the charger side: its body diode blocks pack discharge in ship mode. BATP senses the pack side through 100R.', ['J401', 'Q400', 'R400', 'C41[78]'], width=200),
  g('Configuration straps', 'PROG 6.04k: 2S, 1.5 MHz. ILIM_HIZ = REGN x 10/37: hardware input ceiling about 0.37 A (max 0.44 A), below the 500 mA USB default. TS: 5.23k/30.1k window for a 103AT NTC (charge 0-60 C, JEITA).', ['R40[1-5]'], width=200),
  g('Charge enable', 'CE low enables charging. R406 holds CE high from REGN; Q401 pulls it low only while CHARGE_REQUEST is high, so charging stays off whenever the MCU is not running.', ['R406', 'Q401'], width=150),
  g('Charge LED, power button', 'STAT LED lit from REGN (USB present): on while charging, 1 Hz blink on fault. POWER drives QON; BAT54 gives the MCU a 3.3 V-safe copy (QON idles near 3.2 V).', ['R407', 'D401', 'SW400', 'D402', 'R408'], width=190),
 ]},
 'analog': {'heading': 'ANALOGUE SUPPLY - LT3045 +5VA FOR THE ADS1299 AND REF BUFFER (5.090 V), BACKFEED CLAMP (Rev C10)', 'notes': ['SYS comes from the BQ25798 power path (charger sheet): the pack through the battery FET when on battery. Bench only; no human connection.', 'Layout: OUTS Kelvin-sensed at the output capacitors; SET node, CSET and RSET return Kelvin to the same ground. ILIM (~100 mA) is not patient protection.', 'Reverse-current protection does not stop back-powering through signal pins. Q201 now holds +5VA down whenever ANA_ENABLE is low, powered or not (Step 12). ADC I/O gating is on the adc_interface sheet.'], 'groups': [
  g('LT3045 analogue regulator', 'SYS in, +5VA out (5.090 V). EN/UV driven by ANA_ENABLE with 100k default-off; RILIM sets about 100 mA. PG unused.', ['U201', 'C202', 'R202', 'R206'], width=200),
  g('Output voltage set', 'RSET = R201 49.9k + R207 1.00k = 50.9k (E96, Step 13) with SET current 100 uA. CSET filters reference noise and sets soft start. Kelvin to OUTS/GND.', ['R201', 'R207', 'C201'], width=150),
  g('Fast start-up (PGFB)', 'Divider ends the fast-charge of CSET near 4.5 V. Not used for reset.', ['R203', 'R204']),
  g('Output capacitors and bleeder', 'At least 10 uF effective total required for stability (26 uF worst case at 5.25 V from the Murata DC-bias curve); bleeder keeps load >= 1 mA with the ADC absent.', ['C203', 'C204', 'R205']),
  g('Power flags', 'ERC declarations for supplies that enter from other sheets.', ['#FLG40[1-3]']),
  g('AVDD backfeed clamp (Step 12)', 'Rail off: Q201 gate follows +5VA through R209, so current pushed into +5VA by the input clamp diodes turns Q201 on and R208 sinks it (<= 1.3 V modelled at 30-100 V faults). Rail on: Q202 grounds the gate (5 uA in R209). Also discharges +5VA after a stop.', ['Q20[12]', 'R20[89]'], width=200),
 ]},
 'supervision': {'heading': 'SUPPLY AND PACK SUPERVISION - TPS389001, OPEN-DRAIN, LOW = FAULT', 'notes': ['Monitor PACK_POS at the protected pack terminals and SYS at the charger output. 0.1 % dividers; no filter capacitor on SENSE.', '4.7k pull-ups keep edges <= 118 ns/V at 30 pF for the Schmitt-input AUP gates (Step 10). Keep each output net <= 30 pF.'], 'groups': [
  g('ANALOG_OK: +5VA monitor', 'Asserts below 4.83 V nominal (31.6k/9.88k, Step 13); 100 nF C0G gives ~107 ms release delay after AVDD is valid. Holds the ADC in reset.', ['U210', 'R21[0-2]', 'C21[01]'], width=165),
  g('DIGITAL_OK: +3V3 monitor', 'Asserts below 3.15 V; ~107 ms release. Also the MCU reset line (with button and SWD reset).', ['U211', 'R21[3-5]', 'C21[23]'], width=165),
  g('SYS_OK: system rail monitor', 'Asserts below 5.77 V, above LT3045 dropout, so the analogue rail is switched off while still in regulation.', ['U212', 'R21[6-8]', 'C21[45]'], width=165),
  g('PACK_OK: pack cutoff', 'Asserts below 6.23 V (44.2k/10k) at the protected pack terminals; inhibits analogue power and clears the restart latch.', ['U213', 'R219', 'R22[01]', 'C21[67]'], width=165),
  g('BAT_WARN_OK: early warning', 'Low below 6.61 V: firmware stops capture and syncs files. No guaranteed shutdown time.', ['U214', 'R22[2-4]', 'C21[89]'], width=165),
 ]},
 'reset_logic': {'heading': 'HARDWARE ANALOGUE ENABLE AND ADC RESET GATING', 'notes': ['PACK_OK gates the analogue rail only; the digital rail stays up for shutdown and service. Pack cell protection remains independent.', 'Restart after a fault needs a new RUN_REQUEST edge: see the restart_latch sheet (Step 10).'], 'groups': [
  g('Analogue enable chain', 'POWER_OK = SYS_OK . PACK_OK; MODE_OK = RUN_LATCHED . SERVICE_OK; ANA_ENABLE = POWER_OK . MODE_OK. Schmitt-input AUP gates.', ['U22[012]', 'C23[012]'], width=390),
  g('ADC reset gate', 'ADS_RESET_N = ANALOG_OK . DIGITAL_OK . ADC_RESET_REQUEST . ANA_ENABLE. Any monitored fault resets the ADC without firmware.', ['U22[345]', 'C23[345]'], width=390),
  g('Default-low pull-downs', 'Requests and permits read low (off) while the MCU is in reset or unpowered.', ['R23[0-3]'], width=390),
 ]},
 'restart_latch': {'heading': 'PERSISTENT ANALOGUE RESTART LATCH (Step 10)', 'notes': ['ANA_ENABLE = SYS_OK . PACK_OK . SERVICE_OK . RUN_REQUEST . RUN_ARMED. Battery rebound cannot restart analogue power.', 'Power-up: supervisors hold POWER_OK low through their release delay, so U227 starts cleared.', 'Firmware: on any stop drive RUN_REQUEST low; to start, confirm SYS_OK and PACK_OK, hold RUN_REQUEST low >= 1 us, then high. Drive it directly from the GPIO (clock edge <= 10 ns/V, no RC).'], 'groups': [
  g('Run permit', 'RUN_PERMIT = POWER_OK . SERVICE_OK. Low on any SYS, pack or service fault.', ['U226', 'C226']),
  g('Restart flip-flop', 'RUN_PERMIT low clears RUN_ARMED and holds it clear. A new RUN_REQUEST rising edge re-arms only while permitted. TP230 for bench checks.', ['U227', 'C227', 'TP230'], min_width=120),
  g('Latched run output', 'RUN_LATCHED = RUN_REQUEST . RUN_ARMED; replaces RUN_REQUEST in the analogue enable chain.', ['U228', 'C228']),
 ]},
 'digital_power': {'heading': 'DIGITAL 3.3 V RAIL FROM SYS', 'notes': ['TPS62162 runs whenever SYS is up: from the pack, or from USB through the charger. Soft-off is the BQ25798 ship mode (charger sheet), which removes SYS entirely.'], 'groups': [
  g('3.3 V buck regulator', 'TPS62162 from SYS. Supplies module, logic, microSD and ADC DVDD. BUCK_PG is informational; DIGITAL_OK supervises.', ['U240', 'L240', 'C24[0-2]', 'R240'], width=230),
  g('Reserved control defaults', 'Pull-downs keep reserved MCU outputs (charge request, power hold, LED, SD power) defined until those circuits exist.', ['R38[0-3]'], width=200),
 ]},
 'controller': {'heading': 'CONTROLLER - u-blox NINA-B306 (nRF52840), GPIO MAP PER NINA-B3 R15 TABLE 7', 'notes': ['microSD on the storage sheet; trigger and photodiode on the event_inputs sheet; BQ25798 charger on the charger sheet.', 'Footprint EEG:u-blox_NINA-B306 (Step 13) carries the 12 EGP and 4 EAGP ground pads and the 8 x 3.1 mm antenna copper cut-out. Place at a board edge, antenna outwards.'], 'groups': [
  g('NINA-B306 module (nRF52840)', 'Units A-C split the 55 pads. Pad map verified against NINA-B3 Table 7. EGP/EAGP ground groups on the project footprint.', ['U300'], width=400),
  g('Module decoupling', '10 uF bulk and 100 nF at VCC/VCC_IO; C303 at the VBUS pad 31 (MCU_VBUS from U324, Step 14). Place at the pads.', ['C30[0-3]'], width=200),
  g('Power I2C pull-ups', 'Shared bus for TUSB320 CC controller, photodiode threshold DAC (0x60) and the BQ25798 charger (0x6B); TUSB320 at 0x47.', ['R30[01]']),
  g('Input defaults', 'Provisional 100k pulls so event, monitor and interrupt inputs never float.', ['R30[2-7]'], width=200),
 ]},
 'adc_interface': {'heading': 'ADC INTERFACE - MCU CONTROL LINES FORCED LOW UNTIL ADC_IO_READY', 'notes': ["Place series resistors marked 'near ADC' at the ADS1299. Route CLK short and away from the electrode inputs."], 'groups': [
  g('Gated ADC control buffers', 'SN74LVC1G126 per control line: outputs tri-state and 10k pulls hold ADC pins low until ADC_IO_READY; 33R series near the ADC; 100k MCU-side defaults.', ['U31[0-4]', 'R31[0-9]', 'R32[0-4]', 'C31[0-4]'], width=360),
  g('ADC outputs and reset', 'DOUT and DRDY return through series resistors near the ADC. ADS_RESET_N from the reset gate, 100k default low at the pin.', ['R33[0-3]'], width=180),
  g('ADC mode straps', 'CLKSEL low selects the external clock; DAISY and GPIO1-4 held low.', ['R34[0-6]'], width=180),
  g('2.048 MHz ADC clock', 'SiT8008 +/-20 ppm on +3V3_ADC so the clock cannot drive an unpowered ADC. Route short, away from inputs.', ['Y340', 'R34[89]', 'C340']),
 ]},
 'debug_service': {'heading': 'SWD PROGRAMMING AND USB SERVICE: DISCONNECT ALL ELECTRODES', 'notes': ['A mechanical interlock is still required: an unpowered USB cable can join grounds without VBUS detection.', 'J300 pin 9 detection works only with adapters that ground it. SWD has no target-power input; 3V3 is a voltage reference only. No USB bootloader is assumed.'], 'groups': [
  g('SWD programming header', 'Cortex 10-pin; 100R series on each line. Pin 9 grounded by a compatible adapter gives SWD_ABSENT low. No target power.', ['J300', 'R35[0-4]'], width=170),
  g('Buttons', 'RESET pulls the supervised reset line; RECOVERY and RECORD are active-low GPIO with 10k pull-ups.', ['SW30[0-2]', 'R35[67]'], width=170),
  g('Service interlock', 'Closed only in the recording position; open blocks acquisition through SERVICE_OK. Mechanical interlock not yet designed.', ['J301', 'R358'], min_width=90),
  g('Service and ADC I/O gating', 'SERVICE_OK = USB absent . SWD absent . interlock closed. ADC_IO_READY = ANALOG_OK . DIGITAL_OK . ANA_ENABLE enables the ADC buffers.', ['U33[0-3]', 'C33[0-3]'], width=260),
 ]},
 'usb_c': {'heading': 'USB-C 5 V SINK - NO PD, DATA TO MODULE, VBUS OVERVOLTAGE CUT-OFF, VBUS TO THE BQ25798 CHARGER', 'notes': ['Step 14: U323 TPD1S514-1 disconnects USB_5V from the connector above 5.99 V within 100 ns; VBUS_CON is rated 30 V DC. No duplicate Rd: the CC controller contains the sink terminations.', 'Route the USB 2.0 pair short and matched, directly to the module. Place U323 and C324 next to J310; keep VBUS_CON copper short and on the top layer (TI layout guide).'], 'groups': [
  g('USB-C receptacle and ESD', 'USB 2.0 data to the module; duplicate contacts joined. TPD2E2U06 on D+/D-, CC and USB_5V is ESD only. J310 VBUS contacts are VBUS_CON, before the overvoltage switch.', ['J310', 'D31[0-2]', 'C321', '#FLG500'], width=260),
  g('VBUS overvoltage switch (Step 14)', 'TPD1S514-1: OVP 5.90-5.99 V, off in 100 ns, 30 V DC and 100 V surge on VBUS_CON, 39 mOhm. 20 ms delay + 3.5 ms soft start at plug-in, so the source sees only C324 at attach. EN low: always enabled. VBUS_POWER (USB_VPWR, <= 5.5 V) feeds the USB-sense divider.', ['U323', 'C32[45]'], width=230, min_width=140),
  g('Module VBUS regulator (Step 14)', 'TPS7A2050: 5.0 V +/-1.5 % to module pad 31, because the nRF52840 VBUS pin is rated 5.5 V (5.8 V absolute) and the OVP ceiling is 5.99 V. D324 BAT54 carries reverse current to USB_5V after unplug (TI: <= 15 mA through the LDO).', ['U324', 'C32[67]', 'D324'], width=200, min_width=120),
  g('CC sink controller', 'TUSB320LAI presents sink terminations and reports advertised current over I2C. No PD. VBUS_DET through 887k from the connector side (TI: system VBUS up to 28 V).', ['U320', 'R36[01]', 'C320'], width=200),
  g('VBUS presence logic', 'Divider from USB_VPWR and Schmitt inverters give USB_ABSENT (gates SERVICE_OK) and USB_PRESENT (to MCU), also while U323 blocks an overvoltage source.', ['R36[23]', 'U32[12]', 'C32[23]'], width=260),
 ]},
 'storage': {'heading': 'microSD STORAGE (SPI, 3V3) - REMOVE CARD ONLY WITH BOARD POWER OFF', 'notes': ['No load switch or hold-up reservoir; SD_POWER_EN is reserved. All card pull-ups use the shared 3V3 rail.', 'BAT_WARN_OK low: stop capture, drain queue, wait for card ready, sync best effort. No guaranteed flush interval.'], 'groups': [
  g('microSD socket and supply', 'DM3AT socket on the shared 3V3 rail; 22 uF bulk plus 100 nF. Remove the card only with power off.', ['J420', 'C42[01]'], width=170),
  g('SPI series resistors', '33R damping between module and card; 100k keeps SCLK low at reset.', ['R42[0-3]', 'R429'], width=170),
  g('Card line pull-ups', '10k on CMD/DAT lines as required by the SD SPI-mode start-up.', ['R42[4-8]'], width=170),
  g('Card detect', 'Switch to GND, 10k pull-up and 100R/10 nF filter to SD_DETECT_N; software debounce.', ['R43[01]', 'C422']),
  g('Card-side ESD', 'TPD2E2U06 pairs at the socket on every card line and card detect.', ['D42[0-3]'], width=200),
  g('Supply and status test points', 'Bench access to rails and supervisor outputs for shutdown testing.', ['TP42[0-5]'], width=200),
 ]},
 'event_inputs': {'heading': 'EVENT INPUTS - EDGES TIMESTAMPED BY THE MCU TIMER (GPIOTE + PPI), SAME PATH AS ADC DRDY', 'notes': ['ISOLATION BARRIER: J600, R600, D600 and U600 pins 1-3 are the isolated side. Keep >= 8 mm creepage and clearance to all other copper (slot under U600). J600 shell is not board GND.', 'Trigger input 3.0-5.0 V logic, active high, 2-6 mA LED current. U600 inverts: trigger high gives TRIGGER_ISO low; firmware captures both edges.', 'Photodiode: passive sensor only (e.g. BPW34). Not isolated: treat as participant-side like the electrodes. TIA Vout = 50 mV + Iph x 33k; DAC POR code 0 = no edges until calibrated.'], 'groups': [
  g('Isolated trigger input', '3.0-5.0 V logic lights the TLP2761 LED through 620R; D600 clamps reverse polarity. Output to TRIGGER_ISO for timer capture.', ['J600', 'R60[01]', 'D600', 'U600', 'C600'], width=200),
  g('Photodiode transimpedance amplifier', 'Passive photodiode into TLV9061, 33k || 15 pF feedback; output also to SAADC (PHOTO_MONITOR) for threshold calibration.', ['J601', 'D601', 'R61[0-3]', 'U610', 'C61[0-2]'], width=200),
  g('Edge comparator', 'TLV7011 with 1M hysteresis feedback drives PHOTO_EDGE for timer capture.', ['U611', 'R61[4-6]', 'C613'], width=200),
  g('Threshold DAC', 'MCP4725 on the power I2C bus (0x60) sets the comparator threshold through a 1k/100 nF filter.', ['U612', 'R617', 'C61[45]'], width=200),
 ]},
 'inputs_1_4': {'heading': 'ELECTRODE INPUTS CH1-CH4 - 94k BEFORE CLAMP, 4.7k AFTER CLAMP. NO HUMAN CONNECTION', 'notes': ['TPD2E2U06 leakage limit applies at 2.5 V. The ground clamp is not isolation. Fit one shunt per JP; change it with power off.', 'JP pin 3 is REF_BUF, the buffered REF electrode; it passes through the same negative-leg network as a bipolar electrode. No extra capacitors from inputs to GND.'], 'groups': [channel(1, 1, 501, 501, 1), channel(2, 3, 503, 502, 2), channel(3, 5, 505, 503, 3), channel(4, 7, 507, 504, 4)]},
 'inputs_5_8': {'heading': 'ELECTRODE INPUTS CH5-CH8 - 94k BEFORE CLAMP, 4.7k AFTER CLAMP. NO HUMAN CONNECTION', 'notes': ['TPD2E2U06 leakage limit applies at 2.5 V. The ground clamp is not isolation. Fit one shunt per JP; change it with power off.', 'JP pin 3 is REF_BUF, the buffered REF electrode; it passes through the same negative-leg network as a bipolar electrode. No extra capacitors from inputs to GND.'], 'groups': [channel(5, 9, 509, 505, 5), channel(6, 11, 511, 506, 6), channel(7, 13, 513, 507, 7), channel(8, 15, 515, 508, 8)]},
 'ref_bias': {'heading': 'REFERENCE BUFFER AND BIAS ELECTRODES - STEP 12 BUFFERED REF, STEP 8 BIAS LOOP, BENCH ONLY', 'notes': ['REF is an electrode, not the ADC reference and not GND. It now drives only the U500 follower: channels on REF share no electrode impedance, and the REF electrode carries one leg of leakage instead of up to eight.', 'Firmware: set BIASREF_INT = 1 in the same CONFIG3 write that sets PD_BIAS = 1; monitor BIAS_STAT.', 'Do not inject sustained overvoltage or connect a person. RB1/RB2 need pulse- and voltage-rated parts. +5VA backfeed is clamped by Q201 (analog sheet).'], 'groups': [
  g('REF electrode and buffer (Step 12)', 'REF electrode -> 2 x 47k -> D510 clamp -> 4.7k -> OPA376 unity follower. REF_BUF feeds JP1-JP8 pin 3; each selected channel keeps its own 94k / clamp / 4.7k. U500 on +5VA, so it is off and clamped with the ADC.', ['JREF1', 'R51[789]', 'D510', 'U500', 'C50[01]'], width=230),
  g('BIAS output network', 'RB1 + RB2 (2 x 499k) limit body current; D509 clamps the midpoint to GND.', ['RB[12]', 'D509', 'JBIAS1'], width=200),
  g('Electrode harness J500 (Step 13)', 'J500 2x10 keyed box header: pins 1-16 CH1+ to CH8- (odd +, even -), 17 REF, 18 BIAS, 19-20 unused. The electrode symbols J1-J16, JREF1 and JBIAS1 are the off-board leads.', ['J500'], width=200, min_width=125),
  g('Electrode impedance test links (Rev C12)', 'Normally open. JP9 puts the REF electrode on CH8- (set JP8 1-2, no CH8- electrode); JP10 puts the BIAS electrode on CH7- (set JP7 1-2, no CH7- electrode). The ADS1299 lead-off source then measures it through the channel\'s own 94k network.', ['JP9', 'JP10'], width=200, min_width=125),
  g('BIAS loop compensation', 'Lead-lag feedback 1M || (100k + 10 nF C0G) between BIASOUT and BIASINV for >= 47 deg modelled phase margin.', ['RFB1', 'CFB1', 'RZB1'], width=200),
 ]},
}
