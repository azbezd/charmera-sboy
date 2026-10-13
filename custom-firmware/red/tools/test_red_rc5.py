import unittest,random,tempfile
from pathlib import Path
import red_port as r
from build_red_rc5 import patches,build,OLD,OUT,off,sha
from test_red_rc4 import all_patches,run as old_run,oracle as old_oracle,L
from red_effects_rc4 import GLYPH_ROWS
from test_effect_kernel import Machine
P=patches()
def run(y,uv,w,h,mode):
 p=all_patches();p.update(P);y=bytearray(y);uv=bytearray(uv);ui=bytearray(256);ui[0x5e]=mode
 m=Machine(p,[(0x2100000,y),(0x2400000,uv),(r.TICK,bytearray(4)),(r.UI,ui),(0x2800000,bytearray(512))]);m.r[1]=0x2800200;m.r[3:7]=[0x2100000,0x2400000,w,h];m.r[9]=0xf0000000;before=m.r.copy();flush=[]
 def cb(m):flush.append(tuple(m.r[3:5]));m.r[3:8]=[0xdead]*5
 m.calls={r.FLUSH:cb};m.run(L['MASTER'],max(2000,w*h*160))
 for reg in (1,2,3,4,5,6,9,14,16,18,20,22,24,26,28,30):assert m.r[reg]==before[reg],reg
 assert flush==[(0x2100000,w*h),(0x2400000,w*h//2)]
 return y,uv

def ascii_oracle(y,uv,w,h):
 out=bytearray(y);scale=1 if w<=640 else 2
 for row in range(0,h,2):
  for x in range(0,w,2):
   sx=min(x//(scale*4)*(scale*4)+scale*4-2,w-2);sy=min(row//(scale*8)*(scale*8)+scale*8-2,h-2)
   avg=sum(y[yy*w+xx] for yy in (sy,sy+1) for xx in (sx,sx+1))//4;glyph=GLYPH_ROWS[avg//32]
   for yy in (row,row+1):
    for xx in (x,x+1):
     q=235 if glyph[(yy//scale)%8]&(1<<((xx//scale)%4)) else 16
     if (w,h)==(160,80):q=(3*y[yy*w+xx]+q)//4
     out[yy*w+xx]=q
 return out,bytearray([128])*(w*h//2)

class RC5Tests(unittest.TestCase):
 def test_ascii_reference_bounds_and_abi(self):
  rng=random.Random(505)
  for w,h in ((32,2),(160,80),(320,34),(352,34),(640,34),(672,34),(1280,34),(2048,2),(4096,2)):
   y=bytes(rng.randrange(256) for _ in range(w*h));uv=bytes(rng.randrange(256) for _ in range(w*h//2))
   with self.subTest(w=w,h=h):self.assertEqual(run(y,uv,w,h,12),ascii_oracle(y,uv,w,h))
 def test_other14_styles_and_preview_unchanged(self):
  rng=random.Random(5)
  for w,h in ((160,80),(640,10),(1280,2)):
   y=bytes(rng.randrange(256) for _ in range(w*h));uv=bytes(rng.randrange(256) for _ in range(w*h//2))
   for mode in range(1,16):
    if mode==12 and w>320:continue
    with self.subTest(w=w,h=h,mode=mode):self.assertEqual(run(y,uv,w,h,mode),old_oracle(y,uv,w,h,mode))
 def test_finer_cells_are_coherent(self):
  for w,h,scale in ((640,32,1),(1280,32,2)):
   y=bytes([112])*w*h;uv=bytes([128])*(w*h//2);new,c=run(y,uv,w,h,12);old,_=old_run(y,uv,w,h,12)
   self.assertNotEqual(new,old);self.assertEqual(set(c),{128})
   for yy in range(h):
    self.assertEqual(new[yy*w:(yy+1)*w],bytes(235 if GLYPH_ROWS[3][yy//scale%8]&(1<<(xx//scale%4)) else 16 for xx in range(w)))
 def test_exact_delta_rebuild_and_native_paths(self):
  a=(OLD/'DestBin.bin').read_bytes();b=(OUT/'DestBin.bin').read_bytes();allowed=set(range(0xbde9d,0xbdea9))
  for addr,data in P.items():self.assertEqual(b[off(addr):off(addr)+len(data)],data);allowed.update(range(off(addr),off(addr)+len(data)))
  self.assertEqual(len(a),len(b));self.assertTrue(all(i in allowed for i,(x,y) in enumerate(zip(a,b)) if x!=y));self.assertEqual(b[0xbde9d:0xbdea9],b'SBOY-B-1.4\0\0')
  self.assertEqual(set(P),{r.START,0x2052588,0x20512f8})
  with tempfile.TemporaryDirectory() as d:self.assertEqual(build(Path(d))['sha256'],sha(b))
if __name__=='__main__':unittest.main()
