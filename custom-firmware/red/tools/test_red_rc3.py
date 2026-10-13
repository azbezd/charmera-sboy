import unittest,random,struct,tempfile
from pathlib import Path
import red_port as r
from build_red_rc3 import patches,build,OLD,OUT,off,sha
from red_effects_rc3 import LABELS,RAMPS,BAYER,yuv
from test_red_rc2 import oracle as rc2_oracle,run as rc2_run
from test_effect_kernel import Machine

P,L=patches()

def run(y,uv,w,h,mode,stats=False):
 p,_,_=r.build_patches();p.update(P);y=bytearray(y);uv=bytearray(uv);ui=bytearray(256);ui[0x5e]=mode
 m=Machine(p,[(0x2100000,y),(0x2400000,uv),(r.TICK,bytearray(4)),(r.UI,ui),(0x2800000,bytearray(512))]);m.r[1]=0x2800200;m.r[3:7]=[0x2100000,0x2400000,w,h];m.r[9]=0xf0000000
 before=m.r.copy();flush=[];m.calls={r.FLUSH:lambda m:flush.append((m.r[3],m.r[4]))};m.run(L['MASTER'],max(2000,w*h*150))
 for reg in (1,2,3,4,5,6,9,14,16,18,20,22,24,26,28,30):assert m.r[reg]==before[reg],reg
 assert flush==[(0x2100000,w*h),(0x2400000,w*h//2)]
 return (y,uv,m.steps) if stats else (y,uv)

def oracle(y,uv,w,h,mode):
 if mode not in (3,7,9,11,12):return rc2_oracle(y,uv,w,h,mode)
 out=bytearray(y);c=bytearray(uv)
 if mode==7:
  n=2 if w<=320 else 4 if w<=640 else 8
  for row in range(0,h,2):
   for x in range(0,w,2):
    sx=min(x//n*n+n-2,w-2);sy=min(row//n*n+n-2,h-2);v=y[(sy+1)*w+sx+1]
    out[row*w+x:row*w+x+2]=bytes([v,v]);out[(row+1)*w+x:(row+1)*w+x+2]=bytes([v,v]);c[row//2*w+x:row//2*w+x+2]=uv[sy//2*w+sx:sy//2*w+sx+2]
  return out,c
 for row in range(0,h,2):
  for x in range(0,w,2):
   style=mode
   if mode==12:
    style=(3 if row<h//2 else 11) if x<(w//8)*3 else (9 if row<h//4 else 11 if row<(h//4)*3 else 3)
   src=[y[row*w+x],y[row*w+x+1],y[(row+1)*w+x],y[(row+1)*w+x+1]]
   pair=yuv(RAMPS[11][sum(src)//256])[1:] if style==11 else (128,128)
   c[row//2*w+x:row//2*w+x+2]=bytes(pair)
   for yy in (row,row+1):
    for xx in (x,x+1):
     v=y[yy*w+xx]
     if style==11:q=yuv(RAMPS[11][v//64])[0]
     else:
      threshold=26+28*((xx+yy+v//16)%8) if style==3 else 23+14*BAYER[(yy%4)*4+xx%4]
      q=235 if v>threshold else 16
     if (w,h)==(160,80):q=(3*v+q)//4
     out[yy*w+xx]=q
 return out,c

class RC3Tests(unittest.TestCase):
 def test_all_modes_reference_abi_and_bounds(self):
  rng=random.Random(301)
  for w,h in ((32,2),(160,80),(160,82),(320,18),(640,18),(1280,2),(2048,2),(4096,2)):
   y=bytes(rng.randrange(256) for _ in range(w*h));c=bytes(rng.randrange(256) for _ in range(w*h//2))
   for mode in range(1,13):
    with self.subTest(w=w,h=h,mode=mode):self.assertEqual(run(y,c,w,h,mode),oracle(y,c,w,h,mode))
 def test_monochrome_is_binary_before_jpeg(self):
  w,h=256,16;y=bytes(range(256))*h;c=bytes([54,223])*(w*h//4)
  a,b=run(y,c,w,h,9);self.assertEqual(set(a),{16,235});self.assertEqual(set(b),{128})
  # Flat tonal ramps grow monotonically in white dot coverage.
  coverage=[]
  for level in (16,48,80,112,144,176,208,235):
   a,b=run(bytes([level])*w*h,c,w,h,9);coverage.append(a.count(235))
  self.assertEqual(coverage,sorted(coverage));self.assertEqual(coverage[0],0);self.assertEqual(coverage[-1],w*h)
 def test_new_preview_preserves_detail(self):
  w,h=160,80;y=bytes([32,96]*80+[160,224]*80)*40;c=bytes([128])*(w*h//2)
  for mode in (3,9,11,12):
   a,b=run(y,c,w,h,mode);self.assertGreater(a[w+1]-a[0],90)
   if mode in (3,9):self.assertEqual(set(b),{128})
 def test_unmodified_modes_equal_rc2(self):
  rng=random.Random(304);w,h=320,18;y=bytes(rng.randrange(256) for _ in range(w*h));uv=bytes(rng.randrange(256) for _ in range(w*h//2))
  for mode in (1,2,4,5,6,8,10):self.assertEqual(run(y,uv,w,h,mode),rc2_run(y,uv,w,h,mode),mode)
 def test_mosaic_halves_block_width_and_preserves_geometry(self):
  w,h=640,16;y=bytes((x//4*3+row)%256 for row in range(h) for x in range(w));c=bytes([128])*(w*h//2)
  new,_=run(y,c,w,h,7);old,_=rc2_run(y,c,w,h,7)
  self.assertNotEqual(new,old);self.assertEqual(len(set(new[:4])),1);self.assertNotEqual(new[0],new[4])
 def test_final_image_delta_and_reproducibility(self):
  a=(OLD/'DestBin.bin').read_bytes();b=(OUT/'DestBin.bin').read_bytes();allowed=set(range(0xbde9d,0xbdea9))
  for addr,data in P.items():self.assertEqual(b[off(addr):off(addr)+len(data)],data);allowed.update(range(off(addr),off(addr)+len(data)))
  self.assertEqual(len(a),len(b));self.assertTrue(all(i in allowed for i,(x,y) in enumerate(zip(a,b)) if x!=y));self.assertEqual(b[0xbde9d:0xbdea9],b'SBOY-B-1.2\0\0')
  for forbidden in ('СОРТ','ДУОТОН','ОСКОЛКИ','ХРОМА'):self.assertNotIn(forbidden,LABELS)
  with tempfile.TemporaryDirectory() as d:self.assertEqual(build(Path(d))['sha256'],sha(b))
 def test_native_paths_unchanged(self):
  a=(OLD/'DestBin.bin').read_bytes();b=(OUT/'DestBin.bin').read_bytes();p,_,l=r.build_patches()
  for addr,data in p.items():
   if addr in (l['K'],l['K']+1160,l['SORT'],l['MASTER'],l['DATA']):continue
   self.assertEqual(a[off(addr):off(addr)+len(data)],b[off(addr):off(addr)+len(data)],hex(addr))
  for lo,hi in ((0,0x2400),(0x78c00,0x7f890)):
   self.assertEqual(a[lo:hi],b[lo:hi])
  for lo,hi in ((0x20169c0,0x2016be4),(0x2016fd0,0x20170bc),(0x2018620,0x2018720)):
   self.assertEqual(a[off(lo):off(hi)],b[off(lo):off(hi)])
if __name__=='__main__':unittest.main()
