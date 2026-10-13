import sys,struct,random,unittest
from pathlib import Path
from red_effects import kernel,palettes,BAYER,RAMPS,yuv
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from test_effect_kernel import Machine
BASE=0x2051000;PAL=0x2052400;BAY=PAL+192;TICK=0x207edb8

def expected(y,uv,w,h,mode,tick=0):
 out=bytearray(len(y));chroma=bytearray(len(uv));block=4 if w<=320 else 8 if w<=640 else 16
 for row in range(0,h,2):
  for x in range(0,w,2):
   sx,sy=x,row
   if mode==1 and (row+((tick>>7)&31))%32<=1:sx+=w//32&~1
   if mode==4 and (row>>3)&7>=5:sx+=w//32&~1
   if mode==5 and (row>>3)&3==1:sx+=w//16&~1
   if mode==7:sx=(x&~(block-1))+block-2;sy=(row&~(block-1))+block-2
   if mode==11:
    v=((x>>3)*13+(row>>3)*7)&7
    if v<=2:
     sx+=w//16&~1
     if v==0:sy+=6
   if mode==12 and (((x>>2)*13+(row>>4)*3)&7)<=2:sy=(row&~31)+30
   sx=min(sx,w-2);sy=min(sy,h-2)
   vals=[y[sy*w+sx],y[sy*w+sx+1],y[(sy+1)*w+sx],y[(sy+1)*w+sx+1]]
   pair=uv[(sy//2)*w+sx:(sy//2)*w+sx+2]
   if mode==1:
    top=((vals[0]+vals[1])//2)*3//4+28;bottom=((vals[2]+vals[3])//2)*3//4+28
    if row&2==0:top-=top//16;bottom-=bottom//16
    vals=[top,top,bottom,bottom];pair=bytes((v+128)//2 for v in pair)
   elif mode==5:vals=[(v&224)+16 for v in vals];pair=bytes((v&224)+16 for v in pair)
   elif mode==7:vals=[vals[3]]*4
   elif mode in RAMPS:
    avg=sum(vals)//4
    threshold=BAYER[((row//2)&3)*4+((x//2)&3)]
    if mode in (6,9):avg=255 if avg>threshold*16+8 else 0
    elif mode==8:avg=max(0,min(255,avg+threshold*4-30))
    colors=RAMPS[mode];v=avg//64
    triplet=yuv(colors[v if len(colors)==4 else v//2]);vals=[triplet[0]]*4;pair=bytes(triplet[1:])
   for d,v in zip((row*w+x,row*w+x+1,(row+1)*w+x,(row+1)*w+x+1),vals):out[d]=v
   chroma[row//2*w+x:row//2*w+x+2]=pair
 return out,chroma

def execute(y,uv,w,h,mode,tick=0):
 a,c=bytearray(y),bytearray(uv)
 m=Machine({BASE:kernel(BASE,PAL,BAY,TICK),PAL:palettes()+bytes(BAYER)},[(0x2100000,a),(0x2400000,c),(TICK,bytearray(struct.pack('<I',tick))),(0x2800000,bytearray(128))])
 m.r[1]=0x2800080;m.r[3]=0x2100000;m.r[4]=0x2400000;m.r[5]=w;m.r[6]=h;m.r[7]=mode;m.r[9]=0xf0000000;before=m.r.copy()
 m.run(BASE,max(1000,w*h*120))
 for r in (1,2,3,4,5,6,7,9,10,14,16,18,20,22,24,26,28,30):assert m.r[r]==before[r],r
 return a,c,m.steps

class RedEffectsTests(unittest.TestCase):
 def test_pixels_bounds_and_abi(self):
  rng=random.Random(1310)
  for w,h in ((32,2),(160,80),(352,18),(640,34),(1280,2),(4096,2)):
   y=bytes(rng.randrange(256) for _ in range(w*h));uv=bytes(rng.randrange(256) for _ in range(w*h//2))
   for mode in (1,2,4,5,6,7,8,9,10,11,12):
    with self.subTest(w=w,h=h,mode=mode):self.assertEqual(execute(y,uv,w,h,mode,384)[:2],expected(y,uv,w,h,mode,384))
 def test_invalid_geometry(self):
  for w,h in ((0,2),(31,2),(32,1),(32,4097),(4128,2)):
   for mode in (1,8,12):self.assertEqual(execute(b'',b'',w,h,mode)[:2],(b'',b''))
 def test_vhs_tick_wrap(self):
  y=bytes(i%256 for i in range(160*80));uv=bytes([100,150])*3200
  for tick in (0,127,128,4095,4096,0xffffffff):self.assertEqual(execute(y,uv,160,80,1,tick)[:2],expected(y,uv,160,80,1,tick))
 def test_modes_are_distinct(self):
  rng=random.Random(12);y=bytes(rng.randrange(256) for _ in range(160*80));uv=bytes(rng.randrange(256) for _ in range(6400))
  outputs={bytes(execute(y,uv,160,80,m)[0])+bytes(execute(y,uv,160,80,m)[1]) for m in (1,2,4,5,6,7,8,9,10,11,12)}
  self.assertEqual(len(outputs),11)
if __name__=='__main__':unittest.main()
