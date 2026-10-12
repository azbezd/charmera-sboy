"""0.9 restores light UI only; all executable behavior remains 0.8."""
import unittest,struct
from build_v09 import ROOT,OUT,sha
class V09Tests(unittest.TestCase):
    def test_code_lcd_and_icon_descriptors_preserved(self):
        a=(ROOT/'custom-firmware/builds/sboy-0.8/DestBin.bin').read_bytes();b=(OUT/'DestBin.bin').read_bytes()
        self.assertEqual(sha(b),'3c67c73acb5d34c85da6bd28c6edfef9179c0884505eabe53e99089624cea010')
        self.assertEqual(a[:0x88200],b[:0x88200]);self.assertEqual(a[0x88484:0x8888c],b[0x88484:0x8888c])
        self.assertEqual(a[0xc20bb:0xc2343],b[0xc20bb:0xc2343]);icons=[]
        for rid in (20,21):
            w,h,rel=struct.unpack_from('<III',b,0xc20bb+rid*12);self.assertEqual((w,h),(16,16));pixels=b[0xc20bb+rel:0xc20bb+rel+w*h]
            self.assertEqual(set(pixels),{0,251});icons.append(pixels)
        self.assertNotEqual(*icons)
        # Only two icon slots, boot/shutdown JPEG allocations and build ID may change.
        spans=[(0xc3a83,0xc3c83),(0xd0fa3,0xd474d),(0x8c030,0x8c038)]
        self.assertTrue(all(any(lo<=i<hi for lo,hi in spans) for i,(x,y) in enumerate(zip(a,b)) if x!=y))
if __name__=='__main__':unittest.main()
