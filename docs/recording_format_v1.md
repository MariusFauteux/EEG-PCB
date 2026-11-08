# EEG recording format v1 — reference proposal

Rev C3, 2026-11-08; EVENT payload schema added for Rev C6 (Step 9). This is a firmware interface requirement and tested host-side codec, not an installed recorder implementation.

## Record layout

Every record is 4096 bytes, aligned to an eight-sector boundary within its segment file. Integers are unsigned little-endian. Each data frame preserves the ADS1299 wire bytes (three status bytes followed by eight signed 24-bit channel words in their original byte order); do not reinterpret those words as little-endian integers.

| Byte offset | Size | Field |
|---:|---:|---|
| 0 | 8 | ASCII `EEGLOG01` |
| 8 | 2 | Format version = 1 |
| 10 | 2 | Type: 1 DATA, 2 METADATA, 3 EVENT, 4 END |
| 12 | 16 | Session UUID bytes in standard UUID byte order |
| 28 | 8 | Record sequence, monotonically increasing across segment files |
| 36 | 8 | First ADC sample index; for non-DATA, the associated index |
| 44 | 4 | Payload length, maximum 4028 |
| 48 | 2 | Number of ADC frames: 1–148 for DATA; 0 otherwise |
| 50 | 2 | Flags; bit 0 denotes known preceding capture loss, other bits reserved for later definition |
| 52 | 4 | Nominal sample rate, initially 1000 Hz; not a clock calibration |
| 56 | 4 | Reserved, zero |
| 60 | 4 | CRC32 of bytes 0–59 |
| 64 | variable | Payload |
| after payload | variable | Zero padding through byte 4091 |
| 4092 | 4 | CRC32 of bytes 0–4091 |

Use standard CRC-32/ISO-HDLC, equivalent to Python `zlib.crc32(data)` with default initialization. The check vector ASCII `123456789` yields 0xCBF43926. CRC is error detection, not authentication or durability assurance.

DATA contains exactly 27 × frame_count bytes. Normal records contain 148 frames = 3996 payload bytes and 32 zero-padding bytes. A short final DATA record is allowed. All sample indices count acquisition opportunities from session start; dropped samples create a real gap and are never hidden by renumbering the survivors.

METADATA, EVENT and END payloads are bounded UTF-8 JSON objects. Required metadata includes format/firmware revision, board serial/revision, ADC registers/gain/reference configuration, channel map/electrode labels, nominal clock/rate, calibration identifier, UTC start with synchronization quality, session UUID and card CID/model. Metadata larger than 4028 bytes must be split into explicitly numbered metadata records; reassembly belongs to future firmware/export code, not the codec supplied here.

EVENT payloads follow schema `event/1` (Step 9, Rev C6). The header's associated sample index equals `drdy_index`. All ticks come from one free-running 64-bit MCU timer that also captures every ADC DRDY edge.

| Field | Type | Meaning |
|---|---|---|
| `schema` | string | `"event/1"` |
| `kind` | string | `"edge"` for a captured input edge; `"clock_sync"` for a periodic DRDY time pair (every 1000 samples) |
| `source` | string, edge only | `"trigger"`, `"photodiode"` or `"record_button"` |
| `level_after` | 0 or 1, edge only | Logic level at the MCU pin after the edge; TRIGGER_ISO is inverted, so 0 means trigger asserted |
| `tick` | integer | Timer tick of the edge (for `clock_sync`, equal to `drdy_tick`) |
| `tick_hz` | integer | Timer frequency, 16000000 |
| `drdy_index` | integer | ADC sample index of the last DRDY at or before `tick` |
| `drdy_tick` | integer | Timer tick of that DRDY |
| `drdy_next_tick` | integer or null, edge only | Tick of the following DRDY; null if the record was written before it occurred |
| `flags` | integer, optional | Bit 0: capture overflow or hold-off suppressed further edges; others reserved |

`host/event_timing.py` validates these fields, fits the session sample rate from `clock_sync` records and converts an edge into a fractional sample position, correcting for the ADC group delay and a calibrated input latency. END records contain stop reason, next expected sample index, written sample count, drop/error counts and whether driver sync reported success. An END record is useful evidence, not proof of complete flash persistence. The current reference encoder does not validate JSON schemas or reserved flag meanings.

## Segment and recovery rules

Preallocate four 1 GiB FAT32 segment files before capture and synchronize the allocation/manifest. A segment holds 262144 record slots. Do not erase or rewrite old sessions in place during acquisition. Use a new session UUID. Record sequence continues across segments; normal recording never changes allocated file lengths. Keep the session UUID and ordered segment names in the manifest and also in initial metadata.

Recovery scans fixed offsets, validates header and complete-record CRC, session identity, data shape and sequence order. Invalid blocks do not hide later valid blocks. Every recovered DATA record retains its original first-sample index. The scanner rejects duplicate/out-of-order sequences and overlapping sample ranges and reports gaps between surviving records. Missing leading or trailing samples require the session manifest/expected counters to quantify; the scanner does not invent them.

The scanner operates on accessible files, not a damaged FAT allocation map. Do not write to an unclean card before taking a read-only image for forensic recovery if necessary. It cannot restore a sector that the card can no longer read. Corruption can affect more than the last record through internal flash translation behavior; this design does not assert bounded loss on real power cuts.

## Reference tooling

`record_format.py` (in `host/`; run the commands below from that folder) supplies encoding/decoding and streaming recovery using Python's standard library. It never changes the input and exclusively creates output files. Run separately for each segment in manifest order; combine results by session and sequence, checking boundaries between segments as well as within them. Cross-file de-duplication/continuity is not automated in this version.

```bash
python record_format.py session_000.bin \
  --session 54be8999-7715-4c8e-884c-858400f3b525 \
  --raw-out recovered_000.adc27 \
  --report-out recovered_000.jsonl
```

The UUID above is an example, not a real recording. The `.adc27` output concatenates surviving raw frames; it has no placeholders for lost data. **Always retain the JSONL report to reconstruct sample time and gaps.** Each valid entry includes file offset, sample index, count, record sequence and nominal sample rate. Do not analyse the raw file alone as a gap-free time series. The report includes non-DATA payload text; the scanner does not interpret it as commands.

Tests: `python -m unittest discover -s . -p test_record_format.py -v`. Eight methods cover round-trip data, all 4096 truncation positions, flipped bits at each of 4096 byte positions, stale-session records, duplicate/overlapping data, preallocation zeros, type/length limits and recovery across an invalid middle block. These synthetic tests do not model a card controller, filesystem or power supply.
