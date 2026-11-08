"""Deterministic byte-level fault tests; no claims about real flash behavior."""
import io
import unittest
import uuid
import record_format as f

SID=uuid.UUID('54be8999-7715-4c8e-884c-858400f3b525')
def block(seq=0, first=0):
    return f.encode(SID,seq,first,f.DATA,bytes(range(27))*148,148)
class FormatTests(unittest.TestCase):
    def test_round_trip(self):
        r=f.decode(block());self.assertEqual(r['frame_count'],148);self.assertEqual(len(r['payload']),3996)
    def test_all_truncation_positions(self):
        good=block();tail=block(1,148)
        for cut in range(f.BLOCK):
            records=list(f.scan(io.BytesIO(good+tail[:cut]),SID))
            self.assertEqual(sum(r['valid'] for r in records),1)
    def test_every_byte_corruption(self):
        for pos in range(f.BLOCK):
            b=bytearray(block());b[pos]^=1
            with self.assertRaises(ValueError):f.decode(b)
    def test_recover_after_corrupt_record_with_gaps(self):
        b=bytearray(block(1,148));b[200]^=1
        rr=list(f.scan(io.BytesIO(block()+b+block(2,296)),SID))
        self.assertEqual([x['valid'] for x in rr],[True,False,True])
        self.assertEqual(rr[2]['sample_gap'],[148,296]);self.assertEqual(rr[2]['sequence_gap'],[1,2])
    def test_stale_other_session(self):
        b=f.encode(uuid.uuid4(),1,148,f.DATA,bytes(27),1)
        rr=list(f.scan(io.BytesIO(block()+b),SID));self.assertFalse(rr[1]['valid'])
    def test_duplicate_and_overlap(self):
        rr=list(f.scan(io.BytesIO(block()+block()+block(1,0)),SID))
        self.assertEqual([x['valid'] for x in rr],[True,False,False])
    def test_empty_preallocation_rejected(self):
        self.assertFalse(next(f.scan(io.BytesIO(bytes(4096)),SID))['valid'])
    def test_record_types_and_limits(self):
        for kind in (f.METADATA,f.EVENT,f.END):
            self.assertEqual(f.decode(f.encode(SID,0,0,kind,b'{}'))['kind'],kind)
        with self.assertRaises(ValueError):f.encode(SID,0,0,f.DATA,bytes(27*149),149)
        with self.assertRaises(ValueError):f.encode(SID,0,0,f.EVENT,bytes(4029))

if __name__=='__main__':unittest.main()
