# Step 6 — microSD storage and shutdown provisions

2026-11-08 · Rev C3 · 12-sheet KiCad schematic · bench integration draft

Step 6 of the original remediation plan adds storage connections and defines shutdown/data-integrity requirements. The new `storage.kicad_sch` connects microSD to the dedicated controller SPI allocation. It adds local capacitance, pull-ups, series resistors, ESD parts, card detection and physical test pads. Existing Step 4 power circuits are preserved, as requested. This milestone does not implement MCU firmware or prove card durability.

## 1. Hardware changes

| Reference | Selection / value | Function |
|---|---|---|
| J420 | Hirose DM3AT-SF-PEJM5 | microSD socket, push-push, card detect |
| R420–R423 | 33 Ω each | SPI edge damping; final values need signal-integrity measurements |
| R424–R428 | 10 kΩ, 1% | CMD and DAT0–DAT3 pull-ups, including unused DAT1/DAT2 |
| R429 | 100 kΩ | Clock idle-low default |
| R430 / R431 / C422 | 10 kΩ / 100 Ω / 10 nF | Card-detect pull-up and small input filter; firmware debounce still needed |
| C420 / C421 | 22 µF, 10 V X7R / 100 nF | Local card decoupling; 1206 footprint for C420, exact MPN/DC-bias qualification open |
| D420–D423 | TPD2E2U06DCKR | Eight ESD channels for card data/clock/detect/VDD; no sustained-overvoltage or current-limit function |
| TP420–TP425 | 1 mm PCB pads | 3V3, GND, BAT_WARN_OK, SYS_OK, PACK_OK and DIGITAL_OK |

Superseded placeholder resistors R305 and R384–R387 are removed. The ADC SPI bus and retained Step 5 pin-net assignments are unchanged. `SD_POWER_EN` remains a reserved GPIO with its existing pulldown, not a working card power control.

### Socket mapping

| J420 pad | Card signal / connection | MCU connection |
|---|---|---|
| 1 | DAT2; 10 kΩ pull-up | Unused in SPI |
| 2 | DAT3 / CS_N | R422 → module 51, P0.17 |
| 3 | CMD / DI | R421 → module 50, P0.20 |
| 4 | 3.3 V | Shared digital rail |
| 5 | CLK | R420 → module 52, P0.19 |
| 6 | VSS | Ground |
| 7 | DAT0 / DO | R423 → module 48, P0.21 |
| 8 | DAT1; 10 kΩ pull-up | Unused in SPI |
| 9 / 10 | Detect B / detect A | Pad 9 → R431 → module 47, P0.23; pad 10 grounded |
| 11 | Four shield pads in KiCad footprint | Ground |

The Hirose drawing was visually inspected: the detect switch is **open without a card and closed with a card**, so `SD_DETECT_N` is low when inserted. Pads 9/10/11 are the KiCad footprint's numbering for the manufacturer's A/B switch contacts and shell; the card itself has eight contacts. Pad coverage, signal pitch/order and four shell pads were inspected. This is not a complete dimensional/manufacturing audit.

Place R420–R422 near the MCU source; R423 near the card's DO source. Place ESD parts and bypass capacitors at the socket, with short ground returns. Keep SD clocks and current loops away from electrode/reference circuitry. The card slot belongs behind the service cover; card handling requires electrodes disconnected and board power removed.

## 2. Why there is no card power switch yet

The card and MCU I/O use the same 3.3 V supply. An independently switched card would need a verified sequence or isolation for **all** I/O and pull-ups to avoid feeding an unpowered card through its signal pins. Step 6 therefore uses the optional non-switched architecture: no separate SD supply domain, no card load switch and no firmware promise of power cycling.

Consequences: standby current remains in the runtime budget; a hung card may require a full board power cycle. Live insertion/removal is unsupported. Card inrush and the extra 22 µF load must be checked against digital-supply startup and transient behavior. This choice does not establish safe hot-plug behavior or replace the deferred system shutdown design.

## 3. Card candidate and load budget

Working qualification candidate: **16 GB Swissbit S-56u industrial microSDHC**, not an approved procurement MPN. The manufacturer's public fact sheet explicitly lists SPI support and 2.7–3.6 V operation [1]. Its advertised UHS throughput is not an SPI throughput guarantee. Obtain the exact ordering code, current specification and firmware revision before procurement release; qualify a controlled card model rather than assuming all microSD cards behave alike.

The following are engineering allocations, **not measured loads or card datasheet maxima**:

| 3.3 V branch | Peak allocation |
|---|---:|
| Card, including internal activity | 350 mA |
| MCU/radio | 100 mA |
| ADC digital supply, logic and other digital loads | 30 mA |
| Total | **480 mA / 1.584 W** |

The existing TPS62162 is rated for up to 1 A [4]; the socket contacts are rated 0.5 A [2]. These ratings provide planning headroom, not proof of adequate rail transients or thermal performance. Qualification must reject/rebudget any card exceeding the 350 mA envelope, including startup and background activity. The shared rail must stay within every device's operating range and avoid unintended supervisor resets during simultaneous SD/BLE activity. Charger input/source limits remain a separate unfinished issue.

For an initial energy allocation, target card average current at or below 25 mA: 82.5 mW on 3.3 V, approximately 97 mW at the battery if conversion efficiency is 85%. Both current and efficiency are assumptions to measure. This is a contribution within the system budget, not an addition to an already card-inclusive load estimate. The earlier 24 h requirement is not verified by capacity arithmetic.

## 4. Throughput, storage and buffering

Eight channels plus ADS status require 27 bytes/frame at 1 kS/s = 27,000 B/s. The proposed format stores 148 frames per 4096-byte record, giving 27,675.7 B/s for full DATA records, or approximately 2.391 GB per 24 h. Reserve **32,000 B/s total** for data and bounded metadata/events; event rates exceeding this allocation require a revised budget. At that allocation, 24 h uses 2.765 GB.

Use a FAT32 SDHC card for the first implementation. Before recording, allocate and sync four 1 GiB files and a small session manifest. Each file stays below FAT32's individual file-size limit. Keep allocated file lengths fixed while recording; valid record headers and CRCs identify meaningful contents. Preallocation must finish successfully before enabling acquisition, with enough free space confirmed. Do not allocate or resize segments on the critical capture path.

The initial SD transfer target is at most 8 MHz after initialization; 250 kHz is the proposed initialization clock. The 1 MB/s raw wire rate at 8 MHz is ample on average, but card busy intervals dominate buffering requirements. Use a supported SDHC driver with CMD0/CMD8/ACMD41/CMD58 and block-addressing handling, CRC/error handling and bounded timeouts; do not implement only a naive SPI byte writer. A reset MCU must handle a still-powered card and any unfinished write safely.

Reserve 64 KiB of RAM for 16 records. Reserving two slots for assembly/in-flight work leaves 14 × 4096 / 32,000 = **1.792 s** of queue capacity at the budgeted rate. This is a planning calculation, not an established maximum card stall. Target worst observed combined stall below 1 s with margin in qualification; prove the RAM/linker budget with BLE and USB software. ADC capture must not block on storage. Queue overflow produces an explicit gap/error and stops the session if needed; it must never silently overwrite old samples.

## 5. Shutdown state requirements

The existing low-battery warning already reaches module pad 20/P0.31 as `BAT_WARN_OK`. No new warning comparator is needed in this step. Its nominal warning is 6.6125 V; the Step 4 pack inhibit is nominally 6.1985 V. **The voltage difference cannot be converted into a guaranteed time interval without the selected pack, load, tolerances and discharge measurements.** A pack disconnect/protection trip can remove power immediately. Guaranteed available graceful-shutdown time remains **0 ms** for arbitrary power loss.

Required firmware behavior (not implemented here):

1. On battery warning, user stop, service insertion or interlock opening, latch a stop reason. Clear RUN_REQUEST and ADC_RESET_REQUEST, stop scheduling new acquisition, and preserve already captured samples/counters. USB/interlock also retain their existing hardware analog inhibit.
2. Give storage priority over BLE and display work. Drain queued data while DIGITAL_OK remains high; never wait indefinitely for a card. Use driver timeouts and record errors.
3. For a normal stop with stable power, wait for the card to finish each accepted write, append an END record containing final counters/stop reason, then sync/close. Verify all return values and only report “saved” after success. A successful host write is not itself proof against subsequent flash power loss.
4. For low battery, target completion within 2 s under measured normal-discharge conditions, but do not treat this target as available energy. If the card fails or the rail collapses, leave the session marked unclean; recover surviving records on the next service session.
5. Enter a non-recording low-power state. Keep the SD rail present until board power is removed; the existing always-enabled buck does not implement full system soft-off. POWER_HOLD has no active power-path function yet. Do not automatically resume acquisition after battery rebound or cable removal.

The hardware persistent restart latch remains deferred with Step 4. Firmware requirements do not close that hardware finding. Card detection uses 20 ms software debounce as an initial target; removal during a write is an error, not a trigger for a guaranteed final flush.

### Decoupling is not hold-up energy

C420 adds 22 µF near the card; existing C241 is nominally 22 µF. Even optimistically treating both as fully effective, 44 µF with only 0.2 V allowable droop at 480 mA gives about **18.3 µs** from `t = C ΔV / I`. Actual DC bias, other loads and reset thresholds reduce usable time. Holding 480 mA for 0.5 s over 0.2 V would require about **1.2 F**, before losses and other design constraints. These capacitors address local transients, not flash commit time.

## 6. Recoverable format and what it cannot guarantee

`Recording_Format_v1.md` defines fixed 4096-byte records with a session UUID, record sequence, first sample index, frame count, type, header CRC32 and full-record CRC32. Metadata/event/end records use the same envelope. Recovery scans aligned records independently, rejects incomplete/corrupt/wrong-session records and reports missing sequences/sample ranges. It does not require a final END record or file-length update to recognize surviving data.

`record_format.py` is a host-side reference encoder/scanner, with an explicit session UUID required for recovery. It writes raw ADC frames plus a JSONL report identifying gaps and offsets; use both together for analysis. This is not acquisition firmware, a filesystem repair utility or a full BrainVision exporter.

FAT32 metadata and the card's internal flash translation layer can still be damaged by abrupt loss. CRCs detect many corruptions; they do not make writes atomic, force persistence or preserve inaccessible sectors. Preallocation reduces filesystem updates but does not establish power-fail safety [6]. If directory metadata is damaged, image the card read-only and use a separate filesystem/raw-sector recovery process. The reference scanner expects an accessible segment file with intact block alignment. Never auto-format or reuse an unclean session before recovery.

## 7. Validation and acceptance status

Completed:

- KiCad 9.0.2 ERC: **zero errors and zero warnings**.
- **147 connectivity/value assertions** pass, including the retained Step 5 checks, SD pin paths, pull-ups, ESD, detect filter, supply/test access and socket pad coverage.
- All retained Step 5 pin-net assignments match the frozen previous export; only the five superseded placeholder resistors are removed.
- Eight reference-format tests pass, including every one of 4096 record truncation offsets, every byte position with a flipped bit, stale UUIDs, duplicate/overlapping records and recovery after a damaged middle record.
- New storage and root schematic renders inspected. These are consistency/byte-format checks, not hardware tests.

Before storage is qualified, measure card current, insertion/startup transients, card-ready latency across fill levels/temperature/age, concurrent BLE+SD stalls and EEG noise. Run repeated deliberate power cuts at varying write phases, compare recovered counters/CRCs with the generated stream, inspect filesystem consistency and verify earlier records as well as the last record. Demonstrate a full 24 h session. Define acceptable loss in the experiment requirements; no finite worst-case sample-loss guarantee is claimed yet.

The full BOM now has 277 references, 32 unassigned footprints and 240 entries without exact MPNs. The microSD socket/ESD footprints are assigned; all assigned footprints still need release audit. Charger integration, firmware, Step 4 issues, electrode protection, BIAS/event circuitry and the other release findings remain open. **Step 6 is complete as a schematic-and-requirements milestone, not as a validated recorder.** Next planned step is Step 7, electrode input protection/filtering.

## 8. Primary documentation checked online

Accessed 2026-11-08. Source requirements are distinguished above from design allocations and unmeasured targets.

1. [Swissbit S-56u fact sheet, revision 1.05](https://www.swissbit.com/data/S-56u/S-56u_fact_sheet.pdf): SPI compatibility, capacities and voltage range; exact card current/ordering code still required.
2. [Hirose DM3AT-SF-PEJM5 product and drawings](https://www.hirose.com/en/product/p/CL0609-0031-0-00): connector rating; English DM3 catalog page 3 inspected for pin order and detect contact state.
3. [Espressif SD pull-up requirements](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-reference/peripherals/sd_pullup_requirements.html): CMD and DAT0–DAT3 host pull-ups in SPI mode. Only the card-side wiring guidance is used; ESP-specific pin restrictions do not apply to NINA.
4. [TI TPS62162, SLVSAM2E](https://www.ti.com/lit/ds/symlink/tps62162.pdf): converter output rating and supply design; no measured transient claim.
5. [TI TPD2E2U06, SLLSEG9C](https://www.ti.com/lit/ds/symlink/tpd2e2u06.pdf): DCK pin map 1/2 I/O, 3 GND; low-capacitance ESD protection.
6. [FatFs author’s application note](https://elm-chan.org/fsw/ff/doc/appnote.html): critical filesystem writes and interruption risk.
7. [TI SD/MMC SPI application report, SPRAAO7](https://www.ti.com/lit/an/spraao7/spraao7.pdf): SPI initialization and SDHC protocol background. Driver integration must use current maintained code and the selected card's requirements.
