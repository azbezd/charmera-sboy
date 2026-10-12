"""Execute final 0.4 image words; compare pixels, bounds, selectors and ABI."""
import random,struct,unittest
from build_v04 import ROOT,OUT,off
from effect_kernel import kernel,SLOTS
from sort_kernel import sorter,SORT
from preview_badge import badge,bitmaps
from mode_cycle import patches,FORWARD,REVERSE
from mode_hook import STATE
from test_effect_kernel import Machine,reference
from test_sort_kernel import sorted_reference

class V04Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b=(OUT/'DestBin.bin').read_bytes()
        cls.code={a:cls.b[off(a):off(a)+len(v)] for a,v in {**kernel(),**sorter(live=True),**badge(top=18)}.items()}
    def test_final_image_and_preserved_regions(self):
        old=(ROOT/'custom-firmware/builds/sboy-0.3/DestBin.bin').read_bytes()
        self.assertEqual(len(self.b),0x100000)
        self.assertEqual(self.b[0x8c030:0x8c038],b'14:48:01')
        for a,v in {**sorter(live=True),**badge(top=18),**patches()}.items():self.assertEqual(self.b[off(a):off(a)+len(v)],v)
        for lo,hi in [(0,0x2400),(0x88484,0x8888c),(0x8c200,0x8c290),(0xc20bb,0xd0fa3),(off(0x2014388),off(0x20148a0))]:self.assertEqual(old[lo:hi],self.b[lo:hi])
    def test_selector_cycles_and_abi(self):
        for start in FORWARD+REVERSE:
            n=32 if start in FORWARD else 36
            code={start:self.b[off(start):off(start)+n]}
            for old in range(256):
                state=bytearray([0xa7]*112);state[0x66]=old
                m=Machine(code,[(STATE,state)]);m.r[3]=STATE;m.r[9]=start+n;before=m.r.copy();m.run(start,12)
                expected=(old+1 if old<3 else 1) if start in FORWARD else (old-1 if old in (2,3) else 3)
                self.assertEqual(m.r[3],expected);self.assertEqual(state[0x66],expected)
                for r in range(32):
                    if r not in (3,4):self.assertEqual(m.r[r],before[r])
                self.assertEqual(state[:0x66]+state[0x67:],bytes([0xa7])*111)
    def test_startup_and_cleanup_state_edits(self):
        # Native default color setup and category reset sites, independent of UI calls.
        state=bytearray(112);state[0x65]=2
        for a in (0x02006e68,0x02006e70,0x02006ea0,0x02006f20):
            m=Machine({a:self.b[off(a):off(a)+4]},[(STATE,state)]);m.r[2]=0;m.r[3]=1;m.r[4]=0;m.r[14]=STATE;m.r[9]=a+4;m.run(a,2)
        self.assertEqual(state[0x66],1);self.assertEqual(state[0x65],2)
    def test_pixels_and_caption_in_final_image(self):
        rng=random.Random(1204)
        for w,h,modes in [(32,4,[1]),(160,80,[0,1,2]),(352,34,[1]),(640,2,[1]),(4096,2,[1])]:
            y=bytearray(rng.randrange(256) for _ in range(w*h));uv=bytearray(rng.randrange(256) for _ in range(w*h//2))
            for mode in modes:
                expected=sorted_reference(y,uv,w,h,live=True) if mode==1 else reference(y,uv,w,h,mode)
                if (w,h)==(160,80):
                    bits=bitmaps()[mode*60:mode*60+60]
                    for row in range(10):
                        for col in range(48):expected[0][(18+row)*w+56+col]=235 if bits[row*6+col//8]&(128>>(col%8)) else 16
                    for row in range(5):expected[1][(9+row)*w+56:(9+row)*w+104]=bytes([128])*48
                actualy=y.copy();actualuv=uv.copy();m=Machine(self.code,[(0x2100000,actualy),(0x2400000,actualuv),(0x2800000,bytearray(40))])
                m.r[1]=0x2800028;m.r[3]=0x2100000;m.r[4]=0x2400000;m.r[5]=w;m.r[6]=h;m.r[9]=0xf0000000;before=m.r.copy()
                m.run(SLOTS[mode],w*h*2400)
                self.assertEqual((actualy,actualuv),expected)
                for r in (1,2,3,4,5,6,9,10,14,16,18,20,22,24,26,28,30):self.assertEqual(m.r[r],before[r],r)
                if (w,h,mode)==(160,80,1):print('160x80 SORT instructions:',m.steps)
    def test_invalid_geometry_and_null_pointers(self):
        for w,h,y,uv in [(31,80,1,2),(160,81,1,2),(4097,2,1,2),(32,0,1,2),(160,80,0,2),(160,80,1,0)]:
            m=Machine(self.code,[]);m.r[3]=y;m.r[4]=uv;m.r[5]=w;m.r[6]=h;m.r[9]=0xf0000000;m.run(SLOTS[1],100);self.assertEqual(m.writes,0)
if __name__=='__main__':unittest.main()
