"""Host-side reference codec/recovery scanner; not MCU firmware or SD driver."""
import argparse
import json
from pathlib import Path
import struct
import uuid
import zlib

BLOCK = 4096
HEADER = struct.Struct('<8sHH16sQQIHHIII')
MAGIC = b'EEGLOG01'
DATA, METADATA, EVENT, END = 1, 2, 3, 4
PAYLOAD_MAX = BLOCK - HEADER.size - 4
FRAMES_MAX = 148  # Project format v1 policy; full data records leave 32 padding bytes.


def encode(session, sequence, first_sample, kind, payload, frame_count=0, flags=0, sample_rate=1000):
    """Return one full record. UUID and sequence must be unique for this session."""
    if kind not in (DATA, METADATA, EVENT, END):
        raise ValueError('unknown record type')
    if len(payload) > PAYLOAD_MAX:
        raise ValueError('payload too long')
    if kind == DATA and (not 1 <= frame_count <= FRAMES_MAX or len(payload) != 27*frame_count):
        raise ValueError('invalid data frame count')
    if kind != DATA and frame_count != 0:
        raise ValueError('non-data record has sample frames')
    h = HEADER.pack(MAGIC, 1, kind, uuid.UUID(str(session)).bytes, sequence,
                    first_sample, len(payload), frame_count, flags, sample_rate, 0, 0)
    h = h[:60] + struct.pack('<I', zlib.crc32(h[:60]))
    body = h + payload + bytes(PAYLOAD_MAX-len(payload))
    return body + struct.pack('<I', zlib.crc32(body))


def decode(block):
    if len(block) != BLOCK:
        raise ValueError('partial record')
    magic, version, kind, sid, seq, first, size, count, flags, rate, reserved, hcrc = HEADER.unpack(block[:64])
    if magic != MAGIC or version != 1 or kind not in (DATA, METADATA, EVENT, END):
        raise ValueError('unknown format')
    if reserved != 0 or hcrc != zlib.crc32(block[:60]):
        raise ValueError('header CRC or reserved field')
    if size > PAYLOAD_MAX or zlib.crc32(block[:-4]) != struct.unpack('<I',block[-4:])[0]:
        raise ValueError('record CRC or size')
    if kind == DATA and (not 1 <= count <= FRAMES_MAX or size != 27*count):
        raise ValueError('data shape')
    if kind != DATA and count != 0:
        raise ValueError('non-data shape')
    if any(block[64+size:-4]):
        raise ValueError('nonzero padding')
    return dict(session=str(uuid.UUID(bytes=sid)), sequence=seq, first_sample=first,
                kind=kind, frame_count=count, flags=flags, sample_rate=rate,
                payload=block[64:64+size])


def scan(stream, session):
    """Scan aligned blocks. Preserve gaps; never treat CRC as a durability guarantee."""
    wanted = str(uuid.UUID(str(session)))
    offset = 0
    last_seq = None
    next_sample = None
    while True:
        block = stream.read(BLOCK)
        if not block:
            return
        try:
            r = decode(block)
            if r['session'] != wanted:
                raise ValueError('different session')
            if last_seq is not None and r['sequence'] <= last_seq:
                raise ValueError('duplicate or out-of-order sequence')
            if r['kind']==DATA and next_sample is not None and r['first_sample'] < next_sample:
                raise ValueError('overlapping sample range')
            r['sequence_gap'] = None if last_seq is None else [last_seq+1,r['sequence']]
            if r['sequence_gap'] and r['sequence_gap'][0]==r['sequence_gap'][1]:
                r['sequence_gap'] = None
            r['sample_gap'] = None
            if r['kind']==DATA:
                if next_sample is not None and r['first_sample']>next_sample:
                    r['sample_gap'] = [next_sample,r['first_sample']]
                next_sample = r['first_sample']+r['frame_count']
            last_seq = r['sequence']
            yield dict(offset=offset, valid=True, **r)
        except ValueError as e:
            yield dict(offset=offset, valid=False, reason=str(e), bytes_read=len(block))
        offset += len(block)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('input',type=Path)
    p.add_argument('--session',required=True,help='UUID recorded in session manifest')
    p.add_argument('--raw-out',required=True,type=Path)
    p.add_argument('--report-out',required=True,type=Path,help='JSONL with record offsets and explicit gaps')
    a=p.parse_args()
    session=str(uuid.UUID(a.session))
    valid=invalid=frames=0
    # Exclusive creation protects existing files. Input is never modified.
    with a.input.open('rb') as source, a.raw_out.open('xb') as raw, a.report_out.open('x') as report:
        for r in scan(source,session):
            if r['valid']:
                valid+=1
                payload=r.pop('payload')
                if r['kind']==DATA:
                    raw.write(payload);frames+=r['frame_count']
                else:
                    r['payload_utf8']=payload.decode('utf-8',errors='replace')
            else:
                invalid+=1
            report.write(json.dumps(r)+'\n')
        report.write(json.dumps(dict(summary=True,valid_records=valid,rejected_records=invalid,frames=frames))+'\n')
    print(f'Recovered {frames} frames; inspect JSONL gaps before analysis.')

if __name__=='__main__': main()
