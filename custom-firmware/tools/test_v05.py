"""Execute final-image instructions, bounded RAM, independent pixel oracles."""
import random,struct,unittest
from build_v05 import OUT,ROOT,off,patches
from effects_v05 import MASTER,NEW,FINISH,MENU,DATA,CLOCK,LABELS,menu_bits
from mode_hook import STATE,SETTER,HOOK
from mode_cycle import FORWARD,REVERSE
from test_effect_kernel import Machine,reference
from test_sort_kernel import sorted_reference
from date_video_patch import WORKER,READY,STATE as ENC,UI

def oracle(y,uv,w,h,index):
    style=(index-1)%6
    if style<3:
        result=sorted_reference(y,uv,w,h,live=True) if style==1 else reference(y,uv,w,h,style)
        a,b=map(bytearray,result)
    else:
        a=bytearray(len(y));b=bytearray(len(uv))
        for row in range(h):
            for x in range(w):
                if style==3:
                    dx=(w//16)&~1 if (row//8)%4==1 else 0
                    v=(y[row*w+min(x+dx,w-1)]&224)+16
                elif style==4:v=224 if y[row*w+x]>((32,160),(224,96))[row%2][x%2] else 32
                else:
                    delta=abs(y[row*w+x]-y[row*w+max(0,x-1)])
                    v=16 if delta<=8 else 128 if delta<=24 else 235
                a[row*w+x]=v
        for row in range(h//2):
            for x in range(0,w,2):
                if style==3:
                    dx=(w//32)&~1 if (row//4)%4==2 else 0
                    p=row*w+min(x+dx,w-2);pair=uv[p:p+2]
                elif style==4:pair=(145,155) if a[row*2*w+x]<128 else (108,125)
                else:pair=(98,107) if row&16 else (145,155)
                b[row*w+x:row*w+x+2]=bytes(pair)
    if index>=7:a=bytearray(max(16,min(235,128+(v-128)*3//2)) for v in a)
    if (w,h)==(160,80):
        bits=menu_bits()[(index-1)*192:index*192]
        for row in range(16):
            for x in range(96):a[(row+18)*w+x+32]=235 if bits[row*12+x//8]&(128>>(x%8)) else 16
        for row in range(8):b[(row+9)*w+32:(row+9)*w+128]=bytes([128])*96
    return a,b

def code_image():
    b=(OUT/'DestBin.bin').read_bytes()
    return {0x205179c:b[off(0x205179c):off(0x20530c4)],0x2018088:b[off(0x2018088):off(0x2018588)]}

def execute(y,uv,w,h,index):
    a,b=bytearray(y),bytearray(uv);state=bytearray(128);state[0x66]=index
    m=Machine(code_image(),[(0x2100000,a),(0x2400000,b),(STATE,state),(0x2800000,bytearray(256))])
    m.r[1]=0x2800100;m.r[3]=0x2100000;m.r[4]=0x2400000;m.r[5]=w;m.r[6]=h;m.r[9]=0xf0000000;before=m.r.copy()
    m.run(MASTER,max(10000,w*h*2400))
    for r in (1,2,3,4,5,6,9,10,14,16,18,20,22,24,26,28,30):assert m.r[r]==before[r],r
    return a,b,m.steps

class V05Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.b=(OUT/'DestBin.bin').read_bytes()
    def test_pixels_all_presets_and_abi(self):
        rng=random.Random(5005)
        for w,h in [(32,4),(160,80),(352,34),(640,2),(4096,2)]:
            y=bytes(rng.randrange(256) for _ in range(w*h));uv=bytes(rng.randrange(256) for _ in range(w*h//2))
            for index in range(1,13):
                with self.subTest(w=w,h=h,index=index):
                    actual=execute(y,uv,w,h,index)
                    self.assertEqual(actual[:2],oracle(y,uv,w,h,index))
                    if (w,h)==(160,80):print('preview preset',index,'instructions',actual[2])
    def test_invalid_geometry(self):
        for index in range(1,13):
            for w,h,y,uv in [(31,80,1,2),(160,81,1,2),(4097,2,1,2),(32,0,1,2),(160,80,0,2),(160,80,1,0)]:
                state=bytearray(128);state[0x66]=index;m=Machine(code_image(),[(STATE,state)])
                m.r[3]=y;m.r[4]=uv;m.r[5]=w;m.r[6]=h;m.r[9]=0xf0000000;m.run(MASTER,200);self.assertEqual(m.writes,0)
    def test_cycles_all_bytes(self):
        for start in FORWARD+REVERSE:
            n=32 if start in FORWARD else 36
            for old in range(256):
                state=bytearray(128);state[0x66]=old
                m=Machine({start:self.b[off(start):off(start)+n]},[(STATE,state)]);m.r[3]=STATE;m.r[9]=start+n;m.run(start,12)
                expected=(old+1 if old<12 else 1) if start in FORWARD else (old-1 if 2<=old<=12 else 12)
                self.assertEqual(m.r[3],expected);self.assertEqual(state[0x66],expected)
    def test_setter_maps_all_custom_modes_and_preserves_cleanup(self):
        for index in range(256):
            state=bytearray(128);state[0x65]=2
            n=len(patches()[HOOK]);m=Machine({HOOK:self.b[off(HOOK):off(HOOK)+n]},[(STATE,state),(0x2800000,bytearray(32))])
            m.r[1]=0x2800020;m.r[3]=index;m.r[9]=SETTER+4;before=m.r.copy();m.run(HOOK,40)
            if 1<=index<=12:self.assertEqual((state[0x64],state[0x65],state[0x69],m.r[3]),(1,2,5,0))
            else:self.assertEqual((state[0x65],m.r[3]),(0,index))
            for r in (1,2,9,14,16,18,20,22,24,26,28,30):self.assertEqual(m.r[r],before[r])
    def test_clock_wrapper_and_protected_regions(self):
        m=Machine({CLOCK:self.b[off(CLOCK):off(CLOCK)+28]},[(0x2800000,bytearray(32))]);events=[]
        m.r[1]=0x2800020;m.r[9]=0xf0000000;m.calls={0x2014388:lambda m:events.append('native_update'),0x200084c:lambda m:events.append('native_time_file')}
        before=m.r.copy();m.run(CLOCK,20);self.assertEqual(events,['native_update','native_time_file']);self.assertEqual(m.r[1],before[1]);self.assertEqual(m.r[9],before[9])
        old=(ROOT/'custom-firmware/builds/sboy-0.4/DestBin.bin').read_bytes()
        for a,v in patches().items():self.assertEqual(self.b[off(a):off(a)+len(v)],v)
        for lo,hi in [(0,0x2400),(0x88484,0x8888c),(0x8c200,0x8c290),(off(0x2014388),off(0x20148a0)),(off(0x200084c),off(0x2000ac8)),(off(0x20530c4),off(0x2053200))]:self.assertEqual(self.b[lo:hi],old[lo:hi])
    def test_video_all_presets_before_stamp_jpeg_and_audio(self):
        for index in range(1,13):
            w,h=32,4;y=bytearray((i*17)%256 for i in range(w*h));uv=bytearray((i*7)%256 for i in range(w*h//2));expected=oracle(y,uv,w,h,index)
            encoder=bytearray(128);state=bytearray(128);state[0x65]=2;state[0x66]=index;state[0x69]=5;encoder[2]=1
            struct.pack_into('<HH',encoder,12,w,h);struct.pack_into('<II',encoder,24,0x2100000,0x2100000+w*h);struct.pack_into('<I',encoder,0x48,0x2140000);struct.pack_into('<I',encoder,0x50,0x10000)
            flag=bytearray(b'\1\0\0\0');events=[]
            m=Machine(code_image(),[(ENC,encoder),(UI,state),(READY,flag),(0x208fb1c,bytearray([1])),(0x2100000,y),(0x2100000+w*h,uv),(0x2800000,bytearray(256))])
            def stamp(m):self.assertEqual((y,uv),expected);events.append('stamp')
            m.calls={0x2020004:lambda m:events.append('flush'),0x203ac24:stamp,0x202bf60:lambda m:events.append('buffer'),0x202c698:lambda m:events.append('jpeg'),0x201fcc8:lambda m:events.append('irq'),0x20468e8:lambda m:events.append('audio_writer')}
            m.r[1]=0x2800100;m.r[9]=0xf0000000;m.run(WORKER,100000)
            self.assertEqual(events,['flush','stamp','buffer','jpeg','irq','audio_writer']);self.assertEqual(flag,bytes(4))
if __name__=='__main__':unittest.main()
