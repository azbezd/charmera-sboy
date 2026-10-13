"""Independent bounded YUV420 effects for red B; no USB/device access."""
import sys,struct
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from effect_kernel import Asm
from date_video_patch import ptr
LABELS=('ВХС','ЧЕРНИЛА','СОРТ','ПРИЗРАК','РАЗРЫВ','РАСТР','МОЗАИКА','ДИЗЕР','ДУОТОН','ТЕРМО','ОСКОЛКИ','ШЛЕЙФ')
# Artist-selected RGB ramps, converted offline to the camera's YUV order.
RAMPS={
 2:((31,24,55),(144,53,82),(222,141,114),(247,227,186)),
 4:((25,39,43),(74,111,108),(175,190,162),(245,227,194)),
 6:((28,28,35),(240,220,183)),
 8:((29,30,61),(78,104,126),(209,131,121),(244,220,177)),
 9:((23,33,62),(248,161,119)),
 10:((37,20,74),(102,67,178),(236,77,107),(255,219,104)),
}
BAYER=(0,8,2,10,12,4,14,6,3,11,1,9,15,7,13,5)
def yuv(rgb):
 r,g,b=rgb
 return (max(16,min(235,16+((66*r+129*g+25*b+128)>>8))),max(16,min(240,128+((-38*r-74*g+112*b+128)>>8))),max(16,min(240,128+((112*r-94*g-18*b+128)>>8))))
def palettes():
 result=bytearray(12*16)
 for mode,colors in RAMPS.items():
  for k in range(4):
   triplet=yuv(colors[k if len(colors)==4 else k//2])
   result[(mode-1)*16+k*4:(mode-1)*16+k*4+4]=bytes((*triplet,0))
 return bytes(result)

def kernel(base,palette,bayer,tick):
 a=Asm(base)
 for reg,lo,hi in ((5,32,4096),(6,2,4096),(7,1,12)):
  a.sfi(4,reg,lo);a.bf('return');a.sfi(2,reg,hi);a.bf('return')
 a.mask(11,5,31);a.sfi(1,11,0);a.bf('return');a.mask(11,6,1);a.sfi(1,11,0);a.bf('return')
 for r in (3,4):a.sfi(0,r,0);a.bf('return')
 saved=(2,14,16,18,20,22,24,26,28,30)
 for i,r in enumerate(saved):a.store(0x35,1,r,-4*(i+1))
 a.addi(1,1,-40);a.mov(14,3);a.mov(16,4);a.li(24,0)
 ptr(a,26,tick);a.load(0x21,26,26);a.shr(26,26,7);a.mask(26,26,31)
 # Block size scales with image width: 4 in viewfinder, 8 at 640, 16 at 1280.
 a.li(28,3);a.sfi(5,5,320);a.bf('size');a.li(28,7);a.sfi(5,5,640);a.bf('size');a.li(28,15)
 a.label('size');a.li(30,0xffff);a.sub(30,30,28)
 a.label('row');a.sf(3,24,6);a.bf('restore');a.li(22,0)
 a.label('pixel');a.sf(3,22,5);a.bf('nextrow')
 a.mov(18,22);a.mov(20,24)
 # Choose future/current source pixels only. Clamping retains 2x2 alignment.
 for mode,label in ((1,'vhs_source'),(4,'ghost_source'),(5,'tear_source'),(7,'mosaic_source'),(11,'shards_source'),(12,'trail_source')):
  a.sfi(0,7,mode);a.bf(label)
 a.j('source')
 a.label('vhs_source');a.add(11,24,26);a.mask(11,11,31);a.sfi(2,11,1);a.bf('source');a.shr(11,5,5);a.mask(11,11,0xfffe);a.add(18,18,11);a.j('clamp')
 a.label('ghost_source');a.shr(11,24,3);a.mask(11,11,7);a.sfi(4,11,5);a.bf('source');a.shr(11,5,5);a.mask(11,11,0xfffe);a.add(18,18,11);a.j('clamp')
 a.label('tear_source');a.shr(11,24,3);a.mask(11,11,3);a.sfi(1,11,1);a.bf('source');a.shr(11,5,4);a.mask(11,11,0xfffe);a.add(18,18,11);a.j('clamp')
 a.label('mosaic_source');a.alu(3,18,22,30);a.add(18,18,28);a.addi(18,18,-1);a.alu(3,20,24,30);a.add(20,20,28);a.addi(20,20,-1);a.j('clamp')
 a.label('shards_source')
 # Stable sparse grid hash, independent of frames/time: restrained blocks.
 a.shr(11,22,3);a.li(12,13);a.mul(11,11,12);a.shr(12,24,3);a.li(13,7);a.mul(12,12,13);a.add(11,11,12);a.mask(11,11,7)
 a.sfi(2,11,2);a.bf('source');a.shr(12,5,4);a.mask(12,12,0xfffe);a.add(18,18,12);a.sfi(1,11,0);a.bf('clamp');a.addi(20,20,6);a.j('clamp')
 a.label('trail_source');a.shr(11,22,2);a.li(12,13);a.mul(11,11,12);a.shr(12,24,4);a.li(13,3);a.mul(12,12,13);a.add(11,11,12);a.mask(11,11,7);a.sfi(2,11,2);a.bf('source')
 a.mask(20,24,0xffe0);a.addi(20,20,30)
 a.label('clamp');a.addi(11,5,-2);a.sf(5,18,11);a.bf('clamp_y');a.mov(18,11)
 a.label('clamp_y');a.addi(11,6,-2);a.sf(5,20,11);a.bf('source');a.mov(20,11)
 a.label('source');a.mul(2,20,5);a.add(2,2,18);a.add(2,2,3)
 a.load(0x23,11,2);a.load(0x23,12,2,1);a.add(2,2,5);a.load(0x23,13,2);a.load(0x23,15,2,1)
 a.shr(2,20,1);a.mul(2,2,5);a.add(2,2,18);a.add(2,2,4);a.load(0x23,19,2);a.load(0x23,21,2,1)
 a.sfi(0,7,1);a.bf('vhs');a.sfi(0,7,5);a.bf('tear');a.sfi(0,7,7);a.bf('mosaic');a.sfi(3,7,11);a.bf('write')
 # Four-level palettes; ordered dither resolves tonal transitions.
 a.add(17,11,12);a.add(17,17,13);a.add(17,17,15);a.shr(17,17,2)
 a.sfi(0,7,6);a.bf('dither');a.sfi(0,7,8);a.bf('dither');a.sfi(0,7,9);a.bf('dither');a.j('quantize')
 a.label('dither');a.shr(2,24,1);a.mask(2,2,3);a.shl(2,2,2);a.shr(18,22,1);a.mask(18,18,3);a.add(2,2,18);ptr(a,18,bayer);a.add(2,2,18);a.load(0x23,2,2)
 a.sfi(0,7,6);a.bf('binary');a.sfi(0,7,9);a.bf('binary');a.shl(2,2,2);a.add(17,17,2);a.addi(17,17,-30);a.sfi(12,17,0);a.bnf('notnegative');a.li(17,0)
 a.label('notnegative');a.sfi(5,17,255);a.bf('quantize');a.li(17,255);a.j('quantize')
 a.label('binary');a.shl(2,2,4);a.addi(2,2,8);a.sf(2,17,2);a.li(17,0);a.bnf('quantize');a.li(17,255)
 a.label('quantize');a.shr(17,17,6);a.shl(17,17,2);a.addi(2,7,-1);a.shl(2,2,4);a.add(17,17,2);ptr(a,2,palette);a.add(17,17,2)
 a.load(0x23,11,17);a.load(0x23,19,17,1);a.load(0x23,21,17,2);a.mov(12,11);a.mov(13,11);a.mov(15,11);a.j('write')
 a.label('vhs')
 for dst,other in ((11,12),(13,15)):
  a.add(dst,dst,other);a.shr(dst,dst,1);a.shl(17,dst,1);a.add(dst,dst,17);a.shr(dst,dst,2);a.addi(dst,dst,28);a.mov(other,dst)
 a.mask(17,24,2);a.sfi(1,17,0);a.bf('vhs_uv')
 for reg in (11,12,13,15):a.shr(17,reg,4);a.sub(reg,reg,17)
 a.label('vhs_uv');a.addi(19,19,128);a.shr(19,19,1);a.addi(21,21,128);a.shr(21,21,1);a.j('write')
 a.label('tear')
 for reg in (11,12,13,15,19,21):a.mask(reg,reg,0xe0);a.addi(reg,reg,16)
 a.j('write')
 a.label('mosaic');a.mov(11,15);a.mov(12,15);a.mov(13,15)
 a.label('write');a.add(2,14,22);a.store(0x36,2,11);a.store(0x36,2,12,1);a.add(2,2,5);a.store(0x36,2,13);a.store(0x36,2,15,1)
 a.add(2,16,22);a.store(0x36,2,19);a.store(0x36,2,21,1);a.addi(22,22,2);a.j('pixel')
 a.label('nextrow');a.add(14,14,5);a.add(14,14,5);a.add(16,16,5);a.addi(24,24,2);a.j('row')
 a.label('restore');a.addi(1,1,40)
 for i,r in enumerate(saved):a.load(0x21,r,1,-4*(i+1))
 a.label('return');a.ret()
 return a.finish()
