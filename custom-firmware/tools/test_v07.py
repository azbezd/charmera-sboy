"""Final-image echo effect, RGB/BGR-only LCD edit and unchanged menu/video."""
import random,struct,unittest
from build_v07 import OUT,ROOT,off,patches,LABELS
from effects_v05 import MASTER,NEW,FINISH,MENU,DATA
from menu_v06 import STATE,TICK,menu_bits
from mode_hook import STATE as UI
from test_effect_kernel import Machine
from test_v05 import oracle as old_oracle
import menu_v06,date_video_patch

def expected(y,uv,w,h,index):
    if index not in (6,12):return old_oracle(y,uv,w,h,index)
    out=bytearray((y[r*w+x]+y[r*w+min(x+w//32,w-1)])//2 for r in range(h) for x in range(w))
    c=bytearray(len(uv))
    for row in range(h//2):
        for x in range(0,w,2):
            c[row*w+x]=uv[row*w+min(x+((w//16)&~1),w-2)]
            c[row*w+x+1]=uv[row*w+min(x+((w//32)&~1),w-2)+1]
    if index==12:out=bytearray(max(16,min(235,128+(v-128)*3//2)) for v in out)
    return out,c

def execute(y,uv,w,h,index):
    b=(OUT/'DestBin.bin').read_bytes();a,c=bytearray(y),bytearray(uv);ui=bytearray(128);ui[0x66]=index
    code={0x205179c:b[off(0x205179c):off(0x20530c4)]}
    m=Machine(code,[(UI,ui),(STATE,bytearray(8)),(0x2100000,a),(0x2400000,c),(0x2800000,bytearray(256))])
    m.r[1]=0x2800100;m.r[3]=0x2100000;m.r[4]=0x2400000;m.r[5]=w;m.r[6]=h;m.r[9]=0xf0000000;before=m.r.copy();m.run(MASTER,max(2000,w*h*2400))
    for r in (1,2,3,4,5,6,9,10,14,16,18,20,22,24,26,28,30):assert m.r[r]==before[r],r
    return a,c,m.steps

class V07Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.b=(OUT/'DestBin.bin').read_bytes();cls.old=(ROOT/'custom-firmware/builds/sboy-0.6/DestBin.bin').read_bytes()
    def test_new_echo_and_existing_modes_pixels_and_abi(self):
        rng=random.Random(701)
        for w,h in [(32,4),(160,78),(352,34),(4096,2)]:
            y=bytes(rng.randrange(256) for _ in range(w*h));uv=bytes(rng.randrange(256) for _ in range(w*h//2))
            for index in range(1,13):
                with self.subTest(w=w,index=index):self.assertEqual(execute(y,uv,w,h,index)[:2],expected(y,uv,w,h,index))
        # Observed preview geometry, hidden menu. New effect retains continuous Y.
        w,h=160,80;y=bytes(rng.randrange(256) for _ in range(w*h));uv=bytes(rng.randrange(256) for _ in range(w*h//2))
        for index in (6,12):self.assertEqual(execute(y,uv,w,h,index)[:2],expected(y,uv,w,h,index))
    def test_invalid_geometry_no_frame_access(self):
        for w,h in [(31,80),(160,81),(8192,2),(32,0)]:
            for index in (6,12):self.assertEqual(execute(b'',b'',w,h,index)[:2],(b'',b''))
    def test_single_lcd_color_bit_and_unchanged_orientation_inversion(self):
        old=self.old[0x88484:0x8888c];new=self.b[0x88484:0x8888c]
        changes=[i for i in range(len(old)) if old[i]!=new[i]];self.assertEqual(len(changes),1)
        i=changes[0];self.assertEqual((old[i],new[i]),(0,8));self.assertEqual(struct.unpack_from('<II',new,i-12),(2,0x36))
        self.assertEqual(struct.unpack_from('<II',new,i-4),(2,0x108))
    def test_preserved_menu_timing_video_and_other_kernels(self):
        for a,v in {**menu_v06.patches(),**date_video_patch.patches()}.items():
            if a==DATA:continue
            self.assertEqual(self.b[off(a):off(a)+len(v)],v,hex(a))
        for lo,hi in [(0,0x2400),(off(0x2014388),off(0x20148a0)),(off(0x2051954),off(NEW)),(off(FINISH),off(DATA)),(0xc20bb,0xd0fa3)]:self.assertEqual(self.old[lo:hi],self.b[lo:hi])
        for a,v in patches().items():self.assertEqual(self.b[off(a):off(a)+len(v)],v)
    def test_new_label_renders_under_existing_gate(self):
        from test_v06 import V06Tests
        helper=V06Tests();helper.b=self.b
        for index in (6,12):
            m=helper.machine(now=500,active=1,start=400,index=index);m.run(MENU,30000)
            bits=menu_bits(LABELS)[(index-1)*192:index*192]
            for y in range(16):
                for x in range(96):self.assertEqual(helper.y[(y+18)*160+x+32],235 if bits[y*12+x//8]&(128>>(x%8)) else 16)
        self.assertEqual(LABELS[-1],'ЭХО');self.assertNotIn('НЕОН',LABELS)
if __name__=='__main__':unittest.main()
