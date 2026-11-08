# EEG PCB decision log

Last updated: 2026-11-08 • Documentation revision 7 • Current schematic: Rev C4 (Step 7)

This is the engineering decision record: decisions, supporting rationale, tradeoffs, evidence and conditions for revisiting them. It is maintained alongside [project.md](project.md), which describes the design as it stands. The [README](../README.md) carries the current status and open release gates. Detailed calculations and sources for each step are in [reviews/](reviews/).

## How to maintain this record

At each design milestone, read this log and project.md before changing the project. Update both in the same revision as the affected schematic, firmware or analysis, and rerun `hardware/rebuild.sh`. Give every new decision the next free D number, add it to the current register below and append its detailed entry at the end of the chronological section. Preserve superseded decisions with a replacement reference rather than rewriting historical conclusions. Record measured results separately from calculations. A new component, battery architecture, channel count, safety boundary or acquisition format warrants a new decision entry.

Status meanings: **requirement** = agreed user target; **implemented** = drawn in the current schematic, not physically validated; **provisional** = working choice awaiting evidence; **planned** = selected but not drawn; **open** = undecided; **superseded** = replaced; **policy** = review or documentation rule.

## Current direction

Finish a reliable battery-operated eight-channel acquisition system for long-term electrode research. Rev C4 integrates the ADC, protected electrode inputs, power and supervision, controller, USB-C, SWD and microSD at schematic level. Next validate the BIAS network (Step 8), close the deferred Step 4 power review, integrate the charger and design event timing, then review the complete BOM and footprints before layout. Reliability and signal integrity take priority over size or cost.

## Current register

One line per decision, with its status in Rev C4. The detailed entry for each is in the chronological section below.

| ID | Status in Rev C4 | Decision | Superseded by / next evidence |
|---|---|---|---|
| D01 | Requirement | 8 differential channels, 24 bit, 1 kS/s, 0.1–100 Hz analysis band | Revisit only with changed experimental requirement |
| D02 | Implemented | ADS1299IPAGR as the ADC | Measured noise, offset and timing |
| D03 | Implemented | Per-channel bipolar or shared-REF jumper; internal SRB switches off | Shared-REF coupling (D33) may force a redesign |
| D04 | Superseded | 2 × 47 kΩ per leg and 220 pF differential | D33 |
| D05 | Implemented | DC-coupled acquisition, digital high-pass, initial gain 12 | Measured electrode offsets and common-mode margin |
| D06 | Provisional | Internal 4.5 V reference and internal oscillator | Drift and timing budget (Rev B finding R10) |
| D07 | Provisional | BIAS: 1 MΩ ∥ 1.5 nF feedback, 2 × 499 kΩ output | Step 8 stability and protection review |
| D08 | Superseded (pack kept) | Protected 2S pack, external charging | D23 onboard charging; 2S pack retained |
| D09 | Superseded | TPS7A4901 analogue LDO at 5.086 V | Step 4: LT3045 at 5.050 V |
| D10 | Implemented, revised | TPS62162 3.3 V digital buck | D28: fed from SYS; recheck around BQ25798 |
| D11 | Superseded | TPS3700 UVLO and power-good supervision | Step 4: TPS389001 supervisors |
| D12 | Refined | nRF52840 BLE plus microSD, 24 h simultaneous | D22/D24 module, D29 storage |
| D13 | Provisional | 232-byte BLE packet, 29 kB/s | Peripheral firmware and Mac throughput test |
| D14 | Requirement, not designed | Isolated trigger and photodiode timing | Barrier specification and latency plan |
| D15 | Requirement | 4-layer board, ≈ 100 × 70 × 30 mm, €500 budget | Stack-up, fit and full costed BOM |
| D16 | Requirement | Barebones software; documented binary data, BrainVision/CSV export | Host codec exists; exporters not written |
| D17 | Policy | Keep editable sources, renders, BOM, checks and rationale together | Implemented by `hardware/rebuild.sh` |
| D18 | Policy | Release gates: no fabrication or human use until gates close | See README open items |
| D19 | Implemented | SWD programming and recovery, USB updates after bootloader | Hardware via D24; firmware open |
| D20 | Superseded | Reopen charging scope | D23 |
| D21 | Implemented in part | Record on battery only; service with electrodes disconnected | Mechanical interlock not designed |
| D22 | Implemented | NINA-B306-00B; separate ADC and SD SPI | Land pattern and antenna keepout audit |
| D23 | Planned | 5 V USB-C sink, TUSB320LAI, BQ25798, 0.5 A at 8.4 V | Charger sheet not drawn |
| Step 4 | Implemented, review deferred | LT3045 5.050 V, TPS389001 supervisors, AND-gated reset | Startup margin, dynamics, restart latch |
| D24 | Implemented | Integrate module, SWD and USB pins | Footprint audit; firmware |
| D25 | Implemented | Gate ADC control outputs until power valid | Partial-power behaviour measurement |
| D26 | Implemented | USB-C connector and CC detection before charger | VBUS fault protection belongs to charger |
| D27 | Implemented | SERVICE_OK hardware inhibit | Not isolation; interlock unfinished |
| D28 | Implemented | 3.3 V from SYS; J400 bench-only input | Replace with BQ25798 SYS |
| D29 | Implemented | microSD on dedicated SPI (DM3AT socket) | Card MPN qualification; KiCad 10 shell-pad naming |
| D30 | Implemented | Card on shared 3.3 V rail, no load switch | Standby and recovery measurement |
| D31 | Policy | Low-battery shutdown is best effort | Repeated real power cuts |
| D32 | Implemented (host side) | Recoverable 4096-byte records with CRC32 | MCU firmware; 24 h run |
| D33 | Implemented | Input protection: 94 kΩ → TPD2E2U06 → 4.7 kΩ; 220 pF C0G kept | Leakage, coupling, backfeed and ESD tests |

The Step 4 decisions were recorded without a D number and are listed by step name.

## Next actions

| Priority | Work | Evidence needed before closing |
|---:|---|---|
| 1 | Step 8: BIAS stability and protection | Loop analysis with realistic electrode and cable models; fault currents; drive headroom |
| 2 | Close the deferred Step 4 review | Startup release margin, rail-collapse behaviour, restart latch, capacitor selection |
| 3 | Integrate BQ25798 charger and pack connector | Pack choice, temperature sensing, input current limit, SYS power path |
| 4 | Design isolated trigger and photodiode input | Barrier specification, timing path, latency calibration plan |
| 5 | Resolve reference distribution and powered-off backfeed | Coupling decision for electrode comparisons; rail-injection analysis |
| 6 | Complete schematic review and procurement | Exact BOM, footprint dimensional audit, corner and transient review, cost and mechanical fit |
| 7 | Layout and prototype | Return-current and antenna review, DRC, assembly outputs, bench bring-up |
| 8 | Qualify acquisition performance | Noise, offset and load tests; event timing; 24 h local plus BLE endurance; power-loss recovery |

## Entry template

### Dxx: descriptive title

- Date and affected revision:
- Status and requirement addressed:
- Decision:
- Concise rationale and evidence:
- Alternatives and material tradeoffs:
- Assumptions and unresolved risks:
- Validation needed / result:
- Revisit trigger:
- Replaces / replaced by:

## Chronological entries

The entries below are preserved as written at each milestone. Where they describe the hardware as it was at that time (for example "drawn in Rev B"), the current register above takes precedence.

### Rev B decision register (D01–D17)

| ID | Status | Decision and rationale | Tradeoff / revisit condition |
|---|---|---|---|
| D01 | Requirement | Eight simultaneous differential channels, 24-bit acquisition at 1 kS/s; 0.1–100 Hz analysis band. Supports electrode comparisons and event-related recordings on a common timebase. | Data rate and energy exceed a slower, fewer-channel system. Revisit only with a changed experimental requirement. |
| D02 | Implemented | ADS1299IPAGR combines simultaneous conversion, programmable gain, reference and BIAS functions. | Integrated features still require correct routing, firmware and characterization. Revisit if measured noise, offsets or timing fail requirements. |
| D03 | Implemented | Independent physical bipolar/shared-REF selection for each negative input; internal SRB switches remain off. | Requires careful jumper configuration. This preserves mixed montages without relying on an all-channel reference switch. Revisit for electronically selectable montages. |
| D04 | Provisional | Two 47 kΩ resistors per input leg and a 220 pF differential capacitor. Provides series impedance and differential filtering. | Approximately 0.558 µV RMS resistor noise over 0.1–100 Hz; electrode impedance changes the filter. This is not finalized transient protection. Select final values after noise, leakage and fault analysis. |
| D05 | Implemented | DC-coupled acquisition; analysis high-pass performed digitally. Retains raw slow changes for research. Initial gain target 12. | Electrode DC offset can saturate the hardware before filtering. Validate offset/common-mode margins; lower gain if necessary. |
| D06 | Provisional | Internal 4.5 V ADC reference and internal oscillator for the first implementation. | Reduces parts but does not provide a calibrated sample clock. Measure drift and reference settling; consider an external clock if ERP timing requires it. |
| D07 | Provisional | BIAS feedback 1 MΩ parallel with 1.5 nF, with two 499 kΩ output resistors. | Electrode/cable loading affects loop stability. Verify on a simulator; resistor values alone do not establish participant safety. |
| D08 | Provisional, implemented | Removable protected 2S battery, external charging; analog LDO and separate digital buck converter. | This is a design assumption introduced in Rev B, not a separately confirmed battery purchase. It gives LDO headroom but adds pack size, diode loss and cutoff constraints. Revisit after energy/fit measurements. |
| D09 | Implemented | TPS7A4901 analog supply: 79.0 kΩ / 24.0 kΩ divider, approximately 5.086 V nominal. | Calculated static corners approximately 4.951–5.221 V; transient headroom still needs measurement. Revisit for overshoot, noise or monitor-threshold problems. |
| D10 | Implemented | TPS62162 fixed 3.3 V digital converter. Reserve a preliminary 500 mA peak board-load budget. | Buck switching and SD current bursts may contaminate EEG. Exact module/card load and compensation behavior remain unverified. |
| D11 | Implemented | TPS3700 supervision: UVLO with added hysteresis, early battery warning and separate analog-power-good. | Nominal thresholds are not qualified limits. Warning voltage does not guarantee enough time to commit a file. Test pack rebound and abrupt disconnects. |
| D12 | Requirement / planned | nRF52840 BLE module plus microSD; simultaneous local recording and streaming for 24 h. | Exact module, antenna clearance and SD device are open. Local recording must not depend on BLE keeping up. |
| D13 | Provisional | Packet proposal: 16-byte header plus eight 27-byte ADC frames = 232 bytes. At 1 kS/s, 29 kB/s. | Requires adequate negotiated notification size and sustained Mac throughput. Receiver parser tested; radio and matching peripheral firmware untested. |
| D14 | Requirement / planned | Isolated trigger input and photodiode timing, primarily for visual ERP. | A software stimulus timestamp does not identify actual screen onset. Barrier parts, latency calibration and event encoding remain open. |
| D15 | Requirement / planned | Four-layer KiCad board, approximate 100 × 70 × 30 mm enclosure; €500 includes VAT, assembly, enclosure and storage, excludes batteries/shipping. | Stack-up, fit, prices and full assembled BOM have not been validated. |
| D16 | Requirement | Barebones setup/test software first; documented binary data with BrainVision/CSV export. | Recording integrity, counters and recovery take precedence over a polished interface. Exporters remain unimplemented. |
| D17 | Implemented documentation policy | Preserve editable native schematics, PDF, BOM, checks and human-readable rationale together. | ERC is evidence of schematic consistency, not proof of correct electronics or safety. |

### Rev B corrections and superseded assumptions

- Rev A was an external analog network. Rev B connects it to the physical ADS1299 pins and battery regulators. Do not describe Rev B as an ADC-free circuit.
- Preliminary analog-rail arithmetic using a 1.194 V figure was replaced by the selected regulator's 1.185 V feedback value. The final divider is **79.0 kΩ / 24.0 kΩ** and nominal output **5.085625 V**. Earlier draft values are not the released Rev B BOM.
- The initial narrow-hysteresis UVLO candidate was replaced by external positive feedback. Current nominal VIN_SYS thresholds are **6.749 V on / 6.212 V off**. These are after the series diode, not battery-terminal thresholds.
- Raw divided battery monitoring at the host was replaced by a 3.3 V-pulled comparator output to avoid placing a battery-derived voltage on an unpowered host ADC input.
- Unused SRB1/2 pins are left open in Rev B, with their switches disabled. BIASIN and unused external BIASREF are grounded.

### Evidence at Rev B

Rev B reports zero KiCad 9.0.2 ERC errors/warnings without exclusions. Exported-netlist tests cover all 64 ADC pin identities and key input, BIAS, decoupling, host, regulator and supervisor connections. Assigned footprints exist; IC pad coverage was checked. The PDF was visually reviewed. BLE packet-parser tests pass.

There is no physical noise, stability, BLE throughput, power, endurance or safety measurement, and no circuit simulation. There is no PCB layout. These limits must remain visible when reporting progress.

### Next decisions at Rev B (historical; see Next actions above)

| Priority | Work | Evidence needed before closing |
|---:|---|---|
| 1 | Choose exact nRF52840 module and SD implementation | Pin allocation, antenna/layout requirements, supply peaks and supported data path |
| 2 | Exercise synthetic BLE traffic on the M2 Mac | Sustained throughput, counters, disconnect behavior; repeat with SD writes |
| 3 | Design isolated trigger and photodiode input | Barrier specification, timing path and measured/calibrated latency plan |
| 4 | Finalize electrode protection and connectors | Leakage/noise/capacitance assessment, fault paths, physical connector selection |
| 5 | Review complete schematic and procurement | Exact BOM, footprint dimensional audit, corner/transient review, cost and mechanical envelope |
| 6 | Layout and prototype | Return-current/antenna review, DRC, assembly outputs, bench bring-up results |
| 7 | Qualify acquisition performance | Noise/offset/load tests, event timing, 24h local+BLE endurance and power-loss recovery |

### Rev B change history

- 2026-11-08: Created the decision register from the delivered Rev A/Rev B design and agreed project targets. No hardware changes in this documentation update.


### Review update, 2026-11-08 (D18–D20)

The [Rev B engineering review](reviews/revB_engineering_review.md) supersedes any interpretation that ERC success establishes fabrication readiness. Hardware is unchanged. Findings R01–R12 remain open.

#### D18: Release gates after critical desk review

- Status: adopted review policy; Rev B remains a subsystem draft.
- Decision: hold fabrication pending complete system integration, analog-supply margin/reverse-discharge resolution, protection review and a complete BOM/footprint audit. Human-connected use additionally requires system safety qualification.
- Evidence: repeated ERC returned zero violations and existing netlist assertions passed; no physical validation exists. Approximate analog high corner is 5.2208 V versus the ADC's 5.25 V operating maximum. U2's OUT−IN absolute maximum is +0.3 V, not guaranteed by the generic D201 choice.
- Closure: address review R01–R12 with design evidence and measured results where required. Existing D17 remains applicable.

#### D19: Programming and USB service architecture

- Status: proposed next revision, not implemented.
- Direction: select the nRF52840 module; add SWD/reset/target-voltage access and a recovery mechanism. Initial programming uses SWD; USB updates require installed bootloader firmware. USB-C is also a candidate configuration interface.
- Rationale: native USB does not remove initial programming and recovery needs. J100 is ADC SPI/control, not USB or SWD.
- Boundary: service/USB/debug with electrodes disconnected unless a separately qualified isolation architecture is developed. Firmware acquisition disable is not galvanic isolation.

#### D20: Reopen charging scope

- Status: open; The existing external-charging baseline remains the drawn hardware.
- Direction: evaluate onboard USB-C charging for a protected 2S pack using a compatible buck-boost charger and source-current detection; PD is optional for higher-power operation. No charger IC or pack has been selected.
- Rationale: the user asked whether USB-C charging is supported. It is absent, and a 5 V connector cannot directly charge an 8.4 V pack. Add temperature sensing, charge control, power-path management and independent cell protection/balancing provisions.
- Tradeoff: more components, heat, switching noise and qualification; a 1S alternative would require redesign of the analog supply. Revisit connector, switch, enclosure, power budget and acquisition/charging operating modes together.

Change history addition: 2026-11-08 — recorded external-style review, release blockers and proposed programming/charging direction. No hardware revision or validation status was advanced.


### D21–D23: Rev C architecture selection, 2026-11-08

Status: selected for implementation; Rev B unchanged. See RevC_Architecture_Steps1-3.md and controller_pinmap.csv.

- D21: Battery recording with all conductive service cables absent; USB charging/configuration and SWD require all electrodes disconnected. Prefer a mechanical service/electrode interlock. Hardware acquisition inhibit is supplemental, not isolation.
- D22: Select NINA-B306-00B. Reserve separate ADC and SD SPI controllers, native USB, SWD recovery and hardware event capture. Manufacturer Table 7 checked for 33 unique GPIO assignments; fast clocks avoid radio-sensitive pads. This refines D12 and D19.
- D23: Select 5 V-only USB-C sink using TUSB320LAI plus BQ25798 and protected 2S pack. Initial charge target 0.5 A at 8.4 V subject to source, pack and temperature limits. No PD/OTG. SYS supplies board loads; charger remains available with recording off. This replaces D20's open architecture choice and D08's external-charging direction for future Rev C, not the existing Rev B circuit. Exact pack/connector and bootstrap/current-limit implementation remain open.
- Evidence: u-blox UBX-17052099 R15; TI SLUSDV2C and SLLSEQ8D retrieved online. Source links, power estimates and remaining implementation gates are in the architecture document.
- User requirement: confirm future component parameters using online manufacturer documentation whenever available; explicitly label unverified assumptions.
- Validation: pin allocation uniqueness checked; no new electrical test or schematic change. Review R01–R12 remains open.


### Step 4: power and supervision, 2026-11-08

A standalone C1 power/supervision replacement module is now drawn, not yet merged into Rev B. See Step4_Power_Review.md in EEG_RevC_Step4_Power.zip. Select LT3045IDD#PBF at 5.050 V and TPS389001DSET voltage supervisors, with hardware AND-gated ADC reset and analog enable. Calculated rail envelope 4.937–5.163 V; nominal pack warning 6.6125 V and analog inhibit 6.1985 V. These supersede D09/D11 for the proposed Rev C circuit, not the preserved Rev B files.

Online manufacturer limits were checked, including full-temperature accuracy and leakage. ERC and selected netlist/static checks pass. Narrow supervisor-release margin, dynamic collapse behavior, restart latching, capacitor/footprint selection, charger/MCU integration and bench testing remain open. D10 digital regulator integration must be revisited around charger SYS. BAT_WARN_OK polarity differs from the former BAT_OK_N; firmware must change. No finding is declared physically verified.


### D24–D28: Step 5 integration, 2026-11-08

Status: drawn and checked at schematic level. Earlier decisions remain historical unless superseded below. Step 4 revisions are deferred at the user's explicit request; acceptance for continuation is not electrical closure.

- **D24 — Integrate controller and debug.** Use NINA-B306-00B with VCC/VCC_IO at 3.3 V, dedicated USB pins and J300 SWD/reset access. Initial programming uses SWD; USB bootloader availability is not assumed. This implements the hardware portion of D19/D22. Manufacturer Table 7 was checked; 35 unique GPIO allocations now include SYS_OK/PACK_OK. The B306 land pattern and antenna keepout remain to be audited; EGP/EAGP are symbolic ground groups.
- **D25 — Gate outgoing ADC controls.** Five SN74LVC1G126 buffers require ANALOG_OK AND DIGITAL_OK AND ANA_ENABLE. ADC-side pulldowns establish low defaults when disabled. Series resistors are provisional damping values, not level shifting. This reduces unintended startup drive; partial-power behavior and timing still require measurement. DOUT/DRDY return directly through series resistors on the shared digital supply domain.
- **D26 — Implement USB connector and source detection before charger.** USB4105-GF-A, TUSB320LAI sink mode, 887 kΩ VBUS detection resistor, TPD2E2U06 ESD arrays and dedicated MCU USB wiring are drawn. CC sink terminations are internal; no duplicate external Rd. The arrays do not provide sustained DC overvoltage/current protection. D23 charger selection remains unchanged but unimplemented. USB VBUS has no connection to SYS or the pack.
- **D27 — Supplement the service boundary with hardware gating.** SERVICE_OK requires USB absent, compatible SWD adapter absent and interlock closed. This feeds the existing Step 4 inhibit. An unpowered USB cable or incompatible probe can escape detection, so physical electrode disconnection remains necessary. No galvanic isolation or persistent fault/restart latch is claimed. The mechanical interlock is unfinished.
- **D28 — Make the power boundary explicit.** Restore the fixed 3.3 V TPS62162 digital converter from SYS and expose a bench-only SYS/PACK-sense/GND header until BQ25798 integration. The converter is enabled from SYS; complete system shutdown is not implemented. USB alone cannot power the board VCC. This is an integration boundary, not a final battery connector or charge solution.

Evidence: KiCad 9.0.2 ERC has zero errors/warnings; 100 exported-netlist checks pass; new sheet renders inspected. The checks validate intended connections, not noise, USB compliance, firmware or safety. Online primary references and exact limitations are in Step5_Controller_USB_Review.md. No bench tests performed.

Release constraints: Step 4 static-release margin, dynamics, restart latching and capacitor qualification remain open. Complete charger/SD/event circuits, protection review, firmware and physical validation are still required. BOM has 256 references, 32 missing footprints and 224 missing exact MPNs; assigned footprints also need audit. Do not close R01–R12 solely from this milestone.


### D29–D32: Step 6 storage and shutdown, 2026-11-08

Status: schematic and requirements implemented; physical qualification and MCU firmware open. See Step6_Storage_Shutdown_Review.md and Recording_Format_v1.md. The original Step 6 scope is storage and shutdown; Step 7 remains input protection/filtering.

- **D29 — Add microSD on dedicated SPI.** Select DM3AT-SF-PEJM5 socket, four 33 Ω series resistors, five 10 kΩ CMD/DAT pull-ups, local bypassing, ESD and card detection. Verify the manufacturer's contact state visually: open absent, closed inserted. Keep the existing MCU pin allocation. Remove R305/R384–R387 placeholders so they cannot conflict with card defaults. A 16 GB Swissbit S-56u is a card qualification candidate, not an approved exact MPN.
- **D30 — Keep card and MCU on the shared digital rail.** No optional load switch in C3; SD_POWER_EN is reserved. This avoids an independently unpowered card I/O domain but costs standby current and software power-cycle capability. Card handling requires power off and electrodes disconnected. Revisit if measured standby power or recovery requirements justify adding an isolated/sequenced switch. Allocate card peak 350 mA and total digital peak 480 mA pending actual measurements/specification.
- **D31 — Treat low-battery shutdown as best effort.** Existing BAT_WARN_OK initiates capture stop and queue draining. No guaranteed minimum flush interval is available; arbitrary disconnect gives 0 ms. Shared digital power remains available after analog inhibit while its source remains valid. Do not mistake decoupling for energy reserve or POWER_HOLD for a connected power latch. Full soft-off and Step 4 hardware restart latching remain open.
- **D32 — Make records independently recoverable.** Use 4096-byte records, 148 frames per full DATA record, session UUID, sample indices, sequences and CRC32. Preallocate fixed-length 1 GiB FAT32 files before capture; recover without relying on a final END record. Reference codec/scanner and synthetic corruption tests are supplied. Filesystem/card mapping failures can still destroy earlier data, so no durability or finite loss bound is claimed. Preserve gap reports with recovered raw frames.

Evidence: online Hirose, Swissbit, TI, Espressif and FatFs author documentation checked; links and assumptions in the review. KiCad ERC zero errors/warnings, 147 assertions passed; all retained Step 5 pin-net assignments preserved. Eight format tests passed, including exhaustive byte-position corruption and record truncation checks. No physical write/current/power-cut/endurance tests or MCU firmware execution performed.

Revisit/closure: qualify exact card MPN/firmware/current and stall behavior; prove RAM scheduling with BLE; measure rail transients and EEG noise; perform repeated real power cuts and a 24 h run. Review experimental tolerance for missing data. Step 4 revisions are still deferred at the user's request. R01/R06/R09 gain implemented storage connections and explicit requirements but are not closed by this desk validation.

### D33: Step 7 input protection (Rev C4), 2026-11-08

**Decision:** retain two 47 kΩ per input leg; add TPD2E2U06DCKR after them and 4.7 kΩ between the clamp and ADC. Retain 220 pF differential capacitors, explicitly C0G 5% 50 V. Keep selectable local-negative/shared REF topology and unchanged BIAS network. Split input drawings into two four-channel sheets and a reference/BIAS sheet.

**Rationale and alternatives:** protection leakage matters at EEG amplitudes. TI specifies 10 nA maximum at 2.5 V; the considered Nexperia alternative's 1 nA headline is typical, with 100 nA maximum at a different 5 V test point. Neither should be treated as leakage-free or guaranteed at every operating bias. The extra resistor increases resistor noise by 2.47% but limits internal ADC clamp current. A 470 pF capacitor was evaluated and rejected because it worsens modeled shared-reference coupling; 220 pF remains provisional pending electrode/cable measurements.

**Evidence:** primary manufacturer datasheets linked in Step7_Input_Protection_Review.md. Reproducible linear estimates in analyze_inputs.py/input_analysis.json. Zero KiCad ERC violations; 276 exported-netlist assertions passed, including retention of other circuits and BIAS topology. Drawings inspected. No hardware tests.

**Open consequences:** leakage drift/noise, high-impedance reference coupling, powered-off backfeeding, pulse-rated resistor selection and assembled ESD qualification prevent release. REF paths sum under faults. No medical safety conformity is established. Step 8 must validate BIAS stability/protection; Step 4 remains deferred, not closed. Charger and final BOM/layout/firmware work remain open.

### Documentation and repository restructure, 2026-11-08

No hardware change. The working folder was reorganised into `docs/`, `hardware/` and `host/`; superseded top-level copies of project.md, decision_log.md and the pin map were removed (each was an earlier subset of the current file). The KiCad project was renamed from EEG_RevC_Step7 to EEG_RevC so that its name does not change with each step, and the build and validation scripts were renamed to `build.py`, `validate.py` and `validate_controller.py`. `validate_step6.py` was removed because `validate.py` contains all of its checks. `hardware/rebuild.sh` now regenerates every output; the rebuilt netlist is identical in connectivity, values and footprints to the Step 7 export, and the BOM and pin map are byte-identical. project.md was rewritten to describe Rev C4 directly rather than through dated updates appended to the Rev B text, and this log gained a current register. The Step 7 entry was numbered D33.

The validation report now states the ERC result actually produced rather than a fixed claim. Running under KiCad 10.0.8 exposed one new finding: the stock microSD footprint names its shell pads `SH`, whereas the schematic symbol uses pin 11, so the shield-to-GND connection would not transfer to a KiCad 10 layout. This is recorded as an open item and flagged by `validate.py`; the schematic is unchanged. The netlist assertion count is 275 rather than 276 because that shell-pad check is now reported as a warning.
