import struct,unittest
from pathlib import Path
from sort_kernel import sorter
from preview_badge import badge
ROOT=Path(__file__).resolve().parents[2]
class ImageTests(unittest.TestCase):
    def test_built_executable_matches_emulated_sources(self):
        b=(ROOT/'custom-firmware/builds/sboy-0.3/DestBin.bin').read_bytes()
        self.assertEqual(len(b),0x100000)
        for addr,blob in {**sorter(),**badge()}.items():
            off=addr-0x2000000+0x2400;self.assertEqual(b[off:off+len(blob)],blob)
        self.assertEqual(b[0x8c030:0x8c038],b'14:48:00')
        old=(ROOT/'custom-firmware/builds/charm-breach-0.2-effects/DestBin.bin').read_bytes()
        for lo,hi in [(0,0x2400),(0x88484,0x8888c),(0x8c200,0x8c290),(0xc20bb,0xc2343)]:self.assertEqual(b[lo:hi],old[lo:hi])
        for i in (19,20,21):
            w,h,off=struct.unpack_from('<III',b,0xc20bb+i*12)
            self.assertEqual(b[0xc20bb+off:0xc20bb+off+w*h],bytes(w*h))
if __name__=='__main__':unittest.main()
