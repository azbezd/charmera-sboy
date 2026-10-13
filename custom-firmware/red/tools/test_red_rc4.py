import unittest,random,struct,tempfile
from pathlib import Path
import red_port as r
from build_red_rc4 import patches,build,OLD,OUT,COUNT,menu_bits,off,sha
from build_red_rc3 import patches as rc3_patches
from test_red_rc3 import oracle as rc3_oracle,run as rc3_run
from red_effects_rc4 import LABELS,RAMPS,GLYPH_ROWS,yuv
from test_effect_kernel import Machine
P,L=patches()

def all_patches():
 p,_,_=r.build_patches();p.update(rc3_patches()[0]);p.update(P);return p

def make(w=160,h=80,mode=1,y=None,uv=None):
 y=bytearray(y if y is not None else bytes([94])*(w*h));uv=bytearray(uv if uv is not None else bytes([128])*(w*h//2));ui=bytearray(256);ui[0x5e]=mode
 m=Machine(all_patches(),[(0x2100000,y),(0x2400000,uv),(r.TICK,bytearray(4)),(r.UI,ui),(L['STATE'],bytearray(32)),(0x2800000,bytearray(512))]);m.r[1]=0x2800200;m.r[3:7]=[0x2100000,0x2400000,w,h];m.r[9]=0xf0000000
 return m,y,uv

def run(y,uv,w,h,mode,stats=False):
 m,y,uv=make(w,h,mode,y,uv);before=m.r.copy();flush=[]
 def cb(m):flush.append(tuple(m.r[3:5]));m.r[3:8]=[0xdead]*5
 m.calls={r.FLUSH:cb};m.run(L['MASTER'],max(2000,w*h*160))
 for reg in (1,2,3,4,5,6,9,14,16,18,20,22,24,26,28,30):assert m.r[reg]==before[reg],reg
 assert flush==[(0x2100000,w*h),(0x2400000,w*h//2)]
 return (y,uv,m.steps) if stats else (y,uv)

def oracle(y,uv,w,h,mode):
 if mode<=11:return rc3_oracle(y,uv,w,h,mode)
 out=bytearray(y);c=bytearray(uv);scale=1 if w<=320 else 2 if w<=640 else 4
 for row in range(0,h,2):
  for x in range(0,w,2):
   mean=sum(y[yy*w+xx] for yy in (row,row+1) for xx in (x,x+1))//4
   pair=yuv(RAMPS[9][mean//64])[1:] if mode==15 else (128,128);c[row//2*w+x:row//2*w+x+2]=bytes(pair)
   if mode==12:
    sx=min(x//(scale*4)*(scale*4)+scale*4-2,w-2);sy=min(row//(scale*8)*(scale*8)+scale*8-2,h-2)
    avg=sum(y[yy*w+xx] for yy in (sy,sy+1) for xx in (sx,sx+1))//4;glyph=GLYPH_ROWS[avg//32]
   for yy in (row,row+1):
    for xx in (x,x+1):
     v=y[yy*w+xx]
     if mode==12:q=235 if glyph[(yy//scale)%8] & (1<<((xx//scale)%4)) else 16
     elif mode==13:q=235 if v>26+28*(yy%8) else 16
     elif mode==14:q=128 if xx>=w-2 else max(16,min(235,128+2*(v-y[yy*w+xx+2])))
     else:q=max(16,min(235,v+(xx*13+yy*7)%16-7))
     if (w,h)==(160,80):q=(3*v+q)//4
     out[yy*w+xx]=q
 return out,c

class RC4Tests(unittest.TestCase):
 def test_all15_reference_abi_and_bounds(self):
  rng=random.Random(404)
  for w,h in ((32,2),(160,80),(160,82),(320,18),(640,18),(1280,2),(2048,2),(4096,2)):
   y=bytes(rng.randrange(256) for _ in range(w*h));uv=bytes(rng.randrange(256) for _ in range(w*h//2))
   for mode in range(1,16):
    with self.subTest(w=w,h=h,mode=mode):self.assertEqual(run(y,uv,w,h,mode),oracle(y,uv,w,h,mode))
 def test_existing11_modes_pixel_identical(self):
  w,h=160,80;rng=random.Random(504);y=bytes(rng.randrange(256) for _ in range(w*h));uv=bytes(rng.randrange(256) for _ in range(w*h//2))
  for mode in range(1,12):self.assertEqual(run(y,uv,w,h,mode),rc3_run(y,uv,w,h,mode),mode)
 def test_ascii_glyphs_repeat_coherently_and_neutral(self):
  w,h=128,32
  for tone in (16,48,80,112,144,176,208,235):
   out,c=run(bytes([tone])*w*h,bytes([60,200])*(w*h//4),w,h,12);self.assertEqual(set(c),{128})
   for yy in range(h):self.assertEqual(out[yy*w:(yy+1)*w],bytes(235 if GLYPH_ROWS[tone//32][yy%8] & (1<<(xx%4)) else 16 for xx in range(w)))
  counts=[sum(row.bit_count() for row in rows) for rows in GLYPH_ROWS];self.assertEqual(counts,sorted(counts))
 def test_menu_bitmap_all15_exact_bounds_and_timeout(self):
  bits=menu_bits();self.assertEqual(len(bits),1920)
  for mode in range(1,16):
   m,y,uv=make(mode=mode);m.mem(L['STATE'],4,1);m.mem(L['STATE']+4,4,0xffffff00);m.mem(r.TICK,4,0x100);before=bytes(y);m.run(L['MENU'],100000)
   for yy in range(80):
    for xx in range(160):
     expected=before[yy*160+xx]
     if 18<=yy<34 and 48<=xx<112:
      b=bits[(mode-1)*128+(yy-18)*8+(xx-48)//8];expected=235 if b&(128>>((xx-48)%8)) else 16
     self.assertEqual(y[yy*160+xx],expected)
   self.assertEqual(set(uv),{128})
  for elapsed in (1999,2000,2001):
   m,y,uv=make(mode=15);old=bytes(y);m.mem(L['STATE'],4,1);m.mem(L['STATE']+4,4,0xffffff00);m.mem(r.TICK,4,(0xffffff00+elapsed)&0xffffffff);m.run(L['MENU'],100000);self.assertEqual(bytes(y)!=old,elapsed<2000)
  m,y,uv=make(320,180,15);old=bytes(y+uv);m.mem(L['STATE'],4,1);m.run(L['MENU'],100000);self.assertEqual(bytes(y+uv),old)
 def test_all_photo_video_key_cycles_and_setter_bounds(self):
  for site,end,step in ((0x2016d7c,0x2016e14,1),(0x2016e8c,0x2016fb4,-1),(0x201841c,0x2018480,1),(0x20184fc,0x2018600,-1)):
   for mode in range(1,16):
    m,_,_=make(mode=mode);m.r[2]=r.UI;m.r[9]=end;m.mem(r.TICK,4,1534);seen=[];m.calls={r.SETTER:lambda m:seen.append(m.r[3])};m.run(site,1000);n=(mode-1+step)%15+1
    self.assertEqual(seen,[n]);self.assertEqual(m.mem(r.UI+0x5e,1),n);self.assertEqual(m.mem(L['STATE'],4),1);self.assertEqual(m.mem(L['STATE']+4,4),1534)
  for mode in (0,1,12,13,14,15,16):
   m,_,_=make();m.r[3]=mode;m.r[9]=r.SETTER+4;m.mem(r.UI+0x5d,1,2);m.run(r.SETTER,1000);self.assertEqual(m.mem(r.UI+0x5d,1),2 if 1<=mode<=15 else 0);self.assertEqual(m.r[3],0 if 1<=mode<=15 else mode)
 def test_final_image_exact_delta_protected_paths_and_rebuild(self):
  a=(OLD/'DestBin.bin').read_bytes();b=(OUT/'DestBin.bin').read_bytes();allowed=set(range(0xbde9d,0xbdea9))
  for addr,data in P.items():self.assertEqual(b[off(addr):off(addr)+len(data)],data);allowed.update(range(off(addr),off(addr)+len(data)))
  self.assertTrue(all(i in allowed for i,(x,y) in enumerate(zip(a,b)) if x!=y));self.assertEqual(len(a),len(b));self.assertEqual(b[0xbde9d:0xbdea9],b'SBOY-B-1.3\0\0')
  for key in ('MASTER','PREVIEW','STATE','EVENT','HIDE','V_MODE','V_GEOM','V_DEFER','V_WORK','V_IRQ'):
   addr=L[key];data=all_patches()[addr];self.assertEqual(a[off(addr):off(addr)+len(data)],b[off(addr):off(addr)+len(data)])
  for lo,hi in ((0x20169c0,0x2016be4),(0x2016fd0,0x20170bc),(0x2018620,0x2018720),(0x2000000,0x2001000)):
   self.assertEqual(a[off(lo):off(hi)],b[off(lo):off(hi)])
  self.assertEqual(a[0x78c00:0x7f890],b[0x78c00:0x7f890]);self.assertNotIn('ЗАПЛАТКИ',LABELS)
  with tempfile.TemporaryDirectory() as d:self.assertEqual(build(Path(d))['sha256'],sha(b))
if __name__=='__main__':unittest.main()
