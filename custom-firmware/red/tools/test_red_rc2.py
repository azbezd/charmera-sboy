import unittest,struct,random,hashlib,json,tempfile
from pathlib import Path
import red_port
from red_effects_rc2 import kernels,LABELS,RAMPS,yuv
from red_effects import LABELS as ORIGINAL_LABELS
from build_red_rc2 import patches,build,OUT,OLD,off,sha
from test_effect_kernel import Machine
from test_red_effects import expected as rc1_expected

def oracle(y,uv,w,h,mode,tick=0):
 if mode==12:
  c=bytearray(len(uv))
  for row in range(h//2):
   for x in range(0,w,2):
    c[row*w+x]=uv[row*w+min(x+(w//32&~1),w-2)]
    c[row*w+x+1]=uv[row*w+min(x+(w//64&~1),w-2)+1]
  return bytearray(y),c
 if (w,h)!=(160,80) or mode not in RAMPS:return rc1_expected(y,uv,w,h,mode,tick)
 result=bytearray(y);chroma=bytearray(uv)
 for row in range(0,h,2):
  for x in range(0,w,2):
   sx=x
   if mode==4 and (row>>3)&7>=5:sx=min(x+(w//32&~1),w-2)
   pos=[row*w+sx,row*w+sx+1,(row+1)*w+sx,(row+1)*w+sx+1];old=[y[k] for k in pos];index=sum(old)//256
   colors=RAMPS[mode];target=yuv(colors[index if len(colors)==4 else index//2]);vals=[(3*v+target[0])//4 for v in old]
   if mode in (6,8,9):vals=[v+t for v,t in zip(vals,(-4,4,4,-4))]
   for p,v in zip((row*w+x,row*w+x+1,(row+1)*w+x,(row+1)*w+x+1),vals):result[p]=v
   chroma[row//2*w+x:row//2*w+x+2]=bytes(target[1:])
 return result,chroma

def run(y,uv,w,h,mode,which='new'):
 p,_,l=red_port.build_patches()
 if which=='new':p.update(patches()[0])
 y=bytearray(y);uv=bytearray(uv);ui=bytearray(256);ui[0x5e]=mode
 m=Machine(p,[(0x2100000,y),(0x2400000,uv),(red_port.TICK,bytearray(4)),(red_port.UI,ui),(0x2800000,bytearray(512))]);m.r[1]=0x2800200;m.r[3:7]=[0x2100000,0x2400000,w,h];m.r[9]=0xf0000000
 before=m.r.copy();m.calls={red_port.FLUSH:lambda m:None};m.run(l['MASTER'],max(2000,w*h*130))
 for r in (1,2,3,4,5,6,9,14,16,18,20,22,24,26,28,30):assert m.r[r]==before[r],r
 return y,uv

class RC2Tests(unittest.TestCase):
 def test_pixels_abi_and_bounds(self):
  r=random.Random(113)
  for w,h in ((32,2),(160,80),(160,82),(320,34),(640,34),(1280,2),(4096,2)):
   y=bytes(r.randrange(256) for _ in range(w*h));uv=bytes(r.randrange(256) for _ in range(w*h//2))
   for mode in (1,2,4,5,6,7,8,9,10,11,12):
    with self.subTest(w=w,h=h,mode=mode):self.assertEqual(run(y,uv,w,h,mode),oracle(y,uv,w,h,mode))
 def test_saved_photo_video_unchanged_except_replaced_mode(self):
  r=random.Random(12);w,h=640,34;y=bytes(r.randrange(256) for _ in range(w*h));uv=bytes(r.randrange(256) for _ in range(w*h//2))
  for mode in range(1,12):self.assertEqual(run(y,uv,w,h,mode),run(y,uv,w,h,mode,'old'),mode)
 def test_fine_subject_structure_survives_in_every_palette_preview(self):
  w,h=160,80;y=bytes((32 if row%2==0 else 160)+(64 if x%2 else 0) for row in range(h) for x in range(w));uv=bytes([128])*(w*h//2)
  for mode in RAMPS:
   out,_=run(y,uv,w,h,mode);four=[out[0],out[1],out[w],out[w+1]]
   self.assertEqual(len(set(four)),4);self.assertGreater(max(four)-min(four),130)
   old,_=run(y,uv,w,h,mode,'old');self.assertEqual(len({old[0],old[1],old[w],old[w+1]}),1)
 def test_chroma_never_warps_luma(self):
  w,h=160,80;y=bytes(i%256 for i in range(w*h));uv=bytes(i%255 for i in range(w*h//2));out,c=run(y,uv,w,h,12);self.assertEqual(out,y);self.assertNotEqual(c,uv)
 def test_exact_delta_and_original_reproducibility(self):
  p,l=patches();a=(OLD/'DestBin.bin').read_bytes();b=(OUT/'DestBin.bin').read_bytes();allowed=set(range(0xbde9d,0xbdea9))
  for addr,data in p.items():self.assertEqual(b[off(addr):off(addr)+len(data)],data);allowed.update(range(off(addr),off(addr)+len(data)))
  self.assertEqual(len(a),len(b));self.assertTrue(all(i in allowed for i,(x,y) in enumerate(zip(a,b)) if x!=y));self.assertEqual(ORIGINAL_LABELS[-1],'ШЛЕЙФ');self.assertEqual(LABELS[-1],'ХРОМА')
  self.assertEqual(b[0xbde9d:0xbdea9],b'SBOY-B-1.1\0\0')
  with tempfile.TemporaryDirectory() as d:self.assertEqual(build(Path(d))['sha256'],sha(b))
 def test_menu_timer_and_device_control_bytes_identical(self):
  a=(OLD/'DestBin.bin').read_bytes();b=(OUT/'DestBin.bin').read_bytes();p,r,l=red_port.build_patches()
  for addr,data in p.items():
   if addr in (l['K'],l['DATA']):continue
   self.assertEqual(a[off(addr):off(addr)+len(data)],b[off(addr):off(addr)+len(data)],r[addr])
if __name__=='__main__':unittest.main()
