"""Final-image timer, key callbacks, shutter trampoline and overlay isolation."""
import struct,unittest
from build_v06 import OUT,ROOT,off,patches
from menu_v06 import EVENT,GATE,STATE,SHUTTER,TICK,SELECT_CALLS,SHUTTER_SITE,menu_bits
from effects_v05 import MENU,MASTER
from mode_hook import SETTER,STATE as UI
from test_effect_kernel import Machine

class V06Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.b=(OUT/'DestBin.bin').read_bytes()
    def code(self):
        return {0x205179c:self.b[off(0x205179c):off(0x20530c4)],**{a:self.b[off(a):off(a)+4] for a in SELECT_CALLS+(SHUTTER_SITE,)}}
    def machine(self,now=0,active=0,start=0,index=1,w=160,h=80):
        self.state=bytearray(struct.pack('<II',active,start));self.tick=bytearray(struct.pack('<I',now));self.ui=bytearray(128);self.ui[0x66]=index
        self.y=bytearray([80])*(w*h);self.uv=bytearray([110])*(w*h//2)
        m=Machine(self.code(),[(STATE,self.state),(TICK,self.tick),(UI,self.ui),(0x2100000,self.y),(0x2400000,self.uv),(0x2800000,bytearray(256))])
        m.r[1]=0x2800100;m.r[3]=0x2100000;m.r[4]=0x2400000;m.r[5]=w;m.r[6]=h;m.r[9]=0xf0000000
        return m
    def tick_to(self,now):self.tick[:]=struct.pack('<I',now)
    def test_timeout_boundaries_and_wrap(self):
        for start in (0,1200,0xffffff00):
            for elapsed in (0,10,1990,1999,2000,2001,100000):
                m=self.machine((start+elapsed)&0xffffffff,1,start);before=m.r.copy();m.run(MENU,30000)
                self.assertEqual(self.y!=bytes([80])*12800,elapsed<2000)
                self.assertEqual(struct.unpack_from('<I',self.state)[0],int(elapsed<2000))
                for r in (1,2,3,4,5,6,9,10,14,16,18,20,22,24,26,28,30):self.assertEqual(m.r[r],before[r])
    def test_hidden_boot_no_frame_access(self):
        m=self.machine(now=100);m.run(MENU,40);self.assertEqual(m.writes,0)
        # Hidden state is enough to return: invalid/null frame not accessed.
        m.r[3]=0;m.r[4]=0;m.run(MENU,80);self.assertEqual(m.writes,0)
    def test_all_four_key_sites_reset_timeout_and_tail_call_setter(self):
        for addr in SELECT_CALLS:
            m=self.machine(now=100);m.r[3]=7;m.r[9]=addr+4;calls=[]
            m.calls={SETTER:lambda m:calls.append(m.r[3])};m.run(addr,40)
            self.assertEqual(calls,[7]);self.assertEqual(self.state,struct.pack('<II',1,100))
            self.tick_to(1800);m.r[9]=addr+4;m.run(addr,80)
            self.assertEqual(self.state,struct.pack('<II',1,1800))
            m.r[3]=0x2100000;m.r[9]=0xf0000000;self.tick_to(3790);m.run(MENU,40000)
            self.assertNotEqual(self.y,bytes([80])*12800)
            self.tick_to(3800);self.y[:]=bytes([80])*12800;m.run(MENU,50000)
            self.assertEqual(self.y,bytes([80])*12800)
    def test_shutter_hides_and_replays_original_without_changing_inputs(self):
        m=self.machine(now=500,active=1,start=400);m.r[9]=SHUTTER_SITE+4;before=m.r.copy();m.run(SHUTTER_SITE,20)
        self.assertEqual(self.state[:4],bytes(4));self.assertEqual(m.r[2],0x2080000)
        for r in range(32):
            if r not in (2,11):self.assertEqual(m.r[r],before[r])
        m.r[9]=0xf0000000;m.run(MENU,100);self.assertEqual(self.y,bytes([80])*12800)
    def test_visible_menu_pixels_and_fullsize_exclusion(self):
        for index in range(1,13):
            m=self.machine(now=500,active=1,start=400,index=index);m.run(MENU,30000);bits=menu_bits()[(index-1)*192:index*192]
            expected=bytearray([80])*12800;uv=bytearray([110])*6400
            for row in range(16):
                for x in range(96):expected[(row+18)*160+x+32]=235 if bits[row*12+x//8]&(128>>(x%8)) else 16
            for row in range(8):uv[(row+9)*160+32:(row+9)*160+128]=bytes([128])*96
            self.assertEqual(self.y,expected);self.assertEqual(self.uv,uv)
        m=self.machine(now=500,active=1,start=400,w=640,h=480);m.run(MENU,100);self.assertEqual(m.writes,0)
    def test_filters_equal_v05_when_menu_hidden(self):
        from test_v05 import oracle
        for index in range(1,13):
            m=self.machine(now=500,active=0,index=index,w=32,h=4);expected=oracle(self.y,self.uv,32,4,index)
            m.run(MASTER,100000);self.assertEqual((self.y,self.uv),expected)
    def test_exact_patch_and_untouched_code(self):
        old=(ROOT/'custom-firmware/builds/sboy-0.5/DestBin.bin').read_bytes()
        for a,b in patches().items():self.assertEqual(self.b[off(a):off(a)+len(b)],b)
        for lo,hi in [(0,0x2400),(0x88484,0x8888c),(off(0x2014388),off(0x20148a0)),(off(0x2015f4c),off(0x2016058)),(off(0x2034b40),off(0x2034c04)),(off(0x2051954),off(0x2052600))]:self.assertEqual(self.b[lo:hi],old[lo:hi])
if __name__=='__main__':unittest.main()
