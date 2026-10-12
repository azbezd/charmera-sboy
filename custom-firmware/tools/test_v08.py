"""Final image paired routing, VHS pixels, timer phases, ABI and video path."""
import random,struct,unittest
from build_v08 import OUT,ROOT,off,patches,LABELS
from effects_v05 import MASTER,NEW,FINISH,MENU,DATA
from menu_v06 import STATE,TICK,menu_bits
from mode_hook import STATE as UI
from test_effect_kernel import Machine
from test_v05 import oracle as old_oracle
import menu_v06,date_video_patch

def expected(y,uv,w,h,index,tick=0):
    if index>2:
        old=(index-1)//2+(6 if index%2==0 else 0)
        return old_oracle(y,uv,w,h,old)
    phase=(tick>>7)&31;out=bytearray(len(y));c=bytearray(len(uv))
    for row in range(h):
        shift=w//32 if (row+phase)%32<=1 else 0
        for x in range(w):
            source=min(x+shift,w-1);v=(y[row*w+source]+y[row*w+min(source+1,w-1)])//2
            v=v*3//4+28
            if row%4==0:v-=v//16
            out[row*w+x]=v
    for row in range(h//2):
        for x in range(0,w,2):
            src=min(((x+7)&~7)+((w//128)&~1),w-2)
            for channel in range(2):c[row*w+x+channel]=(uv[row*w+src+channel]+128)//2
    if index==2:out=bytearray(max(16,min(235,128+(v-128)*3//2)) for v in out)
    return out,c

def code():
    b=(OUT/'DestBin.bin').read_bytes()
    return {0x205179c:b[off(0x205179c):off(0x20530c4)],0x2018088:b[off(0x2018088):off(0x2018588)]}

def execute(y,uv,w,h,index,tick=0):
    a,c=bytearray(y),bytearray(uv);ui=bytearray(128);ui[0x66]=index
    m=Machine(code(),[(UI,ui),(STATE,bytearray(8)),(TICK,bytearray(struct.pack('<I',tick))),(0x2100000,a),(0x2400000,c),(0x2800000,bytearray(256))])
    m.r[1]=0x2800100;m.r[3]=0x2100000;m.r[4]=0x2400000;m.r[5]=w;m.r[6]=h;m.r[9]=0xf0000000;before=m.r.copy();m.run(MASTER,max(2000,w*h*2400))
    for r in (1,2,3,4,5,6,9,10,14,16,18,20,22,24,26,28,30):assert m.r[r]==before[r],r
    return a,c,m.steps

class V08Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.b=(OUT/'DestBin.bin').read_bytes();cls.old=(ROOT/'custom-firmware/builds/sboy-0.7/DestBin.bin').read_bytes()
    def test_all_pair_routes_and_pixels(self):
        rng=random.Random(801)
        for w,h in [(32,4),(160,78),(352,34),(4096,2)]:
            y=bytes(rng.randrange(256) for _ in range(w*h));uv=bytes(rng.randrange(256) for _ in range(w*h//2))
            for index in range(1,13):
                with self.subTest(w=w,index=index):self.assertEqual(execute(y,uv,w,h,index,384)[:2],expected(y,uv,w,h,index,384))
    def test_vhs_preview_phase_and_wrap(self):
        w,h=160,80;y=bytes(i%256 for i in range(w*h));uv=bytes((i*19)%256 for i in range(w*h//2))
        for tick in (0,127,128,4095,4096,0xffffffff):
            for index in (1,2):self.assertEqual(execute(y,uv,w,h,index,tick)[:2],expected(y,uv,w,h,index,tick))
        self.assertNotEqual(execute(y,uv,w,h,1,0)[0],execute(y,uv,w,h,1,128)[0])
    def test_invalid_geometry(self):
        for w,h in [(31,80),(160,81),(8192,2),(32,0)]:
            for index in range(1,13):self.assertEqual(execute(b'',b'',w,h,index)[:2],(b'',b''))
    def test_labels_gate_and_preserved_regions(self):
        from test_v06 import V06Tests
        helper=V06Tests();helper.b=self.b
        for index in range(1,13):
            m=helper.machine(now=500,active=1,start=400,index=index);m.run(MENU,30000)
            bits=menu_bits(LABELS,paired=True)[(index-1)*192:index*192]
            for y in range(16):
                for x in range(96):self.assertEqual(helper.y[(y+18)*160+x+32],235 if bits[y*12+x//8]&(128>>(x%8)) else 16)
        for a,v in {**menu_v06.patches(),**date_video_patch.patches()}.items():
            if a!=DATA:self.assertEqual(self.b[off(a):off(a)+len(v)],v,hex(a))
        for a,v in patches().items():self.assertEqual(self.b[off(a):off(a)+len(v)],v)
        for lo,hi in [(0,0x2400),(0x88484,0x8888c),(off(0x2014388),off(0x20148a0)),(0xc20bb,0xd0fa3)]:self.assertEqual(self.b[lo:hi],self.old[lo:hi])
    def test_video_pairs_before_stamp_jpeg(self):
        from date_video_patch import STATE as ENC,READY,WORKER
        for index in range(1,13):
            w,h=32,4;y=bytearray((i*17)%256 for i in range(w*h));uv=bytearray((i*7)%256 for i in range(w*h//2));expect=expected(y,uv,w,h,index,384)
            enc=bytearray(128);ui=bytearray(128);ui[0x65]=2;ui[0x66]=index;ui[0x69]=5;enc[2]=1
            struct.pack_into('<HH',enc,12,w,h);struct.pack_into('<II',enc,24,0x2100000,0x2100000+w*h);struct.pack_into('<I',enc,0x48,0x2140000);struct.pack_into('<I',enc,0x50,0x10000)
            flag=bytearray(b'\1\0\0\0');events=[]
            m=Machine(code(),[(ENC,enc),(UI,ui),(STATE,bytearray(8)),(TICK,bytearray(struct.pack('<I',384))),(READY,flag),(0x208fb1c,bytearray([1])),(0x2100000,y),(0x2100000+w*h,uv),(0x2800000,bytearray(256))])
            def stamp(m):self.assertEqual((y,uv),expect);events.append('stamp')
            m.calls={0x2020004:lambda m:events.append('flush'),0x203ac24:stamp,0x202bf60:lambda m:events.append('buffer'),0x202c698:lambda m:events.append('jpeg'),0x201fcc8:lambda m:events.append('irq'),0x20468e8:lambda m:events.append('audio_writer')}
            m.r[1]=0x2800100;m.r[9]=0xf0000000;m.run(WORKER,100000)
            self.assertEqual(events,['flush','stamp','buffer','jpeg','irq','audio_writer'])
if __name__=='__main__':unittest.main()
