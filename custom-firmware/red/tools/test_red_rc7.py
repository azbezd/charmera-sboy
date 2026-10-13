import unittest, random, struct, tempfile, io
from pathlib import Path
from PIL import Image
import test_red_rc6 as previous
import red_port as r
from build_red_rc7 import patches,build,OLD,OUT,COUNT,LABELS,menu_bits,off,sha
P,L=patches()

def make(*args,**kwargs):
 m,y,uv=previous.make(*args,**kwargs)
 # Machine stores generated code as instruction words, rebuild with final map.
 from test_effect_kernel import Machine
 w=kwargs.get('w',args[0] if args else 160);h=kwargs.get('h',args[1] if len(args)>1 else 80)
 mode=kwargs.get('mode',1);ui=bytearray(256);ui[0x5e]=mode
 p=previous.all_patches();p.update(P)
 m=Machine(p,[(0x2100000,y),(0x2400000,uv),(r.TICK,bytearray(4)),(r.UI,ui),(L['STATE'],bytearray(32)),(0x2800000,bytearray(512))]);m.r[1]=0x2800200;m.r[3:7]=[0x2100000,0x2400000,w,h];m.r[9]=0xf0000000
 return m,y,uv

def run(y,uv,w,h,mode):
 m,y,uv=make(w=w,h=h,mode=mode,y=y,uv=uv);before=m.r.copy();flush=[]
 def cb(m):flush.append(tuple(m.r[3:5]));m.r[3:8]=[0xdead]*5
 m.calls={r.FLUSH:cb};m.run(L['MASTER'],max(2000,w*h*160))
 for reg in (1,2,3,4,5,6,9,14,16,18,20,22,24,26,28,30):assert m.r[reg]==before[reg],reg
 assert flush==[(0x2100000,w*h),(0x2400000,w*h//2)]
 return y,uv

class RC7Tests(unittest.TestCase):
 def test_all13_mapping_oracle_abi_memory_bounds(self):
  rng=random.Random(707)
  for w,h in ((32,2),(160,80),(160,82),(320,18),(640,18),(1280,2),(2048,2),(4096,2)):
   y=bytes(rng.randrange(256) for _ in range(w*h));uv=bytes(rng.randrange(256) for _ in range(w*h//2))
   for mode in range(1,14):
    with self.subTest(w=w,h=h,mode=mode):self.assertEqual(run(y,uv,w,h,mode),previous.oracle(y,uv,w,h,mode if mode<5 else mode+1))
 def test_ui_rejects_outside_range(self):
  for mode in (0,14,15,255):
   y=bytes([93])*160*80;uv=bytes([128])*160*40
   self.assertEqual(run(y,uv,160,80,mode),(y,uv))
 def test_menu_all13_timeout(self):
  bits=menu_bits();self.assertEqual(len(bits),13*128)
  for mode in range(1,14):
   m,y,uv=make(mode=mode);m.mem(L['STATE'],4,1);m.mem(r.TICK,4,500);before=bytes(y);m.run(L['MENU'],100000)
   for yy in range(80):
    for xx in range(160):
     expected=before[yy*160+xx]
     if 18<=yy<34 and 48<=xx<112:
      b=bits[(mode-1)*128+(yy-18)*8+(xx-48)//8];expected=235 if b&(128>>((xx-48)%8)) else 16
     self.assertEqual(y[yy*160+xx],expected)
  for elapsed in (1999,2000,2001):
   m,y,uv=make(mode=13);old=bytes(y);m.mem(L['STATE'],4,1);m.mem(L['STATE']+4,4,0xffffff00);m.mem(r.TICK,4,(0xffffff00+elapsed)&0xffffffff);m.run(L['MENU'],100000);self.assertEqual(bytes(y)!=old,elapsed<2000)
 def test_photo_video_cycles_setter(self):
  for site,end,step in ((0x2016d7c,0x2016e14,1),(0x2016e8c,0x2016fb4,-1),(0x201841c,0x2018480,1),(0x20184fc,0x2018600,-1)):
   for mode in range(1,14):
    m,_,_=make(mode=mode);m.r[2]=r.UI;m.r[9]=end;m.mem(r.TICK,4,1534);seen=[];m.calls={r.SETTER:lambda m:seen.append(m.r[3])};m.run(site,1000);n=(mode-1+step)%13+1
    self.assertEqual(seen,[n]);self.assertEqual(m.mem(r.UI+0x5e,1),n);self.assertEqual(m.mem(L['STATE']+4,4),1534)
  for mode in (0,1,12,13,14,15):
   m,_,_=make();m.r[3]=mode;m.r[9]=r.SETTER+4;m.mem(r.UI+0x5d,1,2);m.run(r.SETTER,1000);self.assertEqual(m.mem(r.UI+0x5d,1),2 if 1<=mode<=13 else 0)
 @unittest.skipUnless((OLD/'DestBin.bin').exists() and (OUT/'DestBin.bin').exists(), 'Full image verification requires source rebuild from your own factory dump')
 def test_shutdown_delta_protected_paths_rebuild(self):
  a=(OLD/'DestBin.bin').read_bytes();b=(OUT/'DestBin.bin').read_bytes();allowed=set(range(0xbde9d,0xbdea9))|set(range(0x99674,0x9a20d))
  for addr,data in P.items():self.assertEqual(b[off(addr):off(addr)+len(data)],data);allowed.update(range(off(addr),off(addr)+len(data)))
  self.assertTrue(all(i in allowed for i,(x,y) in enumerate(zip(a,b)) if x!=y));self.assertEqual(len(b),0x100000);self.assertEqual(b[0xbde9d:0xbdea9],b'SBOY-B-1.6\0\0')
  for lo,hi in ((0,0x2400),(0x78c00,0x7f890)):
   self.assertEqual(a[lo:hi],b[lo:hi])
  for lo,hi in ((0x20169c0,0x2016be4),(0x2016fd0,0x20170bc),(0x2018620,0x2018720)):
   self.assertEqual(a[off(lo):off(hi)],b[off(lo):off(hi)])
  for key in ('PREVIEW','STATE','EVENT','HIDE','V_MODE','V_GEOM','V_DEFER','V_WORK','V_IRQ'):
   addr=L[key];data=previous.all_patches()[addr];self.assertEqual(a[off(addr):off(addr)+len(data)],b[off(addr):off(addr)+len(data)])
  rel,n=struct.unpack_from('<II',b,0x7f800+10*8);jpeg=b[0x7f800+rel:0x7f800+rel+n];self.assertEqual(Image.open(io.BytesIO(jpeg)).size,(160,80));self.assertNotEqual(jpeg,a[0x7f800+rel:0x7f800+rel+n])
  self.assertNotIn('РАЗРЫВ',LABELS);self.assertNotIn('РИЗО',LABELS);self.assertEqual(COUNT,13)
  with tempfile.TemporaryDirectory() as d:self.assertEqual(build(Path(d))['sha256'],sha(b))
if __name__=='__main__':unittest.main()
