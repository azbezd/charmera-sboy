"""Red rc6: fixed4x4 micro-ASCII with retained fine luma,14 modes without Riso.

rc1 implementation is retained unchanged in red_effects.py for reproducibility.
"""
from red_effects import Asm,ptr,BAYER,RAMPS as OLD_RAMPS,yuv,LABELS as OLD_LABELS
RAMPS={k:v for k,v in OLD_RAMPS.items() if k!=9}
RAMPS[9]=((27,32,54),(101,56,68),(192,114,100),(246,225,192))
RAMPS[11]=((14,28,38),(40,91,99),(133,183,163),(241,229,197))
def palettes():
 result=bytearray(192)
 for mode,colors in RAMPS.items():
  for i in range(4):
   result[(mode-1)*16+i*4:(mode-1)*16+i*4+4]=bytes((*yuv(colors[i if len(colors)==4 else i//2]),0))
 return bytes(result)
LABELS=('ВХС','ЧЕРНИЛА','ГРАВЮРА','ПРИЗРАК','РАЗРЫВ','РАСТР','ПИКСЕЛИ','ДИЗЕР','ЧБ ДИЗЕР','ТЕРМО','БУМАГА','АСКИИ','ЛИНИИ','РЕЛЬЕФ')
DETAIL=0x2052588
RISO=0x2052310
ASCII=0x2051e88
GLYPHS=ASCII+128
MASKS=GLYPHS+64
RELIEF=ASCII+196
ART=0x20512f8
PAPER=0x2052630

def kernels(base,palette,bayer,tick):
 a=Asm(base)
 for reg,lo,hi in ((5,32,4096),(6,2,4096),(7,1,14)):
  a.sfi(4,reg,lo);a.bf('return');a.sfi(2,reg,hi);a.bf('return')
 a.mask(11,5,31);a.sfi(1,11,0);a.bf('return');a.mask(11,6,1);a.sfi(1,11,0);a.bf('return')
 for r in (3,4):a.sfi(0,r,0);a.bf('return')
 saved=(2,14,16,18,20,22,24,26,28,30)
 for i,r in enumerate(saved):a.store(0x35,1,r,-4*(i+1))
 a.addi(1,1,-40);a.mov(14,3);a.mov(16,4);a.li(24,0)
 ptr(a,26,tick);a.load(0x21,26,26);a.shr(26,26,7);a.mask(26,26,31)
 # Block size scales with image width: 2 in viewfinder, 4 at 640, 8 at 1280.
 a.li(28,1);a.sfi(5,5,320);a.bf('size');a.li(28,3);a.sfi(5,5,640);a.bf('size');a.li(28,7)
 a.label('size');a.li(30,0xffff);a.sub(30,30,28)
 a.label('row');a.sf(3,24,6);a.bf('restore');a.li(22,0)
 a.label('pixel');a.sf(3,22,5);a.bf('nextrow')
 a.mov(18,22);a.mov(20,24)
 # Choose future/current source pixels only. Clamping retains 2x2 alignment.
 for mode,label in ((1,'vhs_source'),(4,'ghost_source'),(5,'tear_source'),(7,'mosaic_source'),(12,'ascii_source')):
  a.sfi(0,7,mode);a.bf(label)
 a.j('source')
 a.label('vhs_source');a.add(11,24,26);a.mask(11,11,31);a.sfi(2,11,1);a.bf('source');a.shr(11,5,5);a.mask(11,11,0xfffe);a.add(18,18,11);a.j('clamp')
 a.label('ghost_source');a.shr(11,24,3);a.mask(11,11,7);a.sfi(4,11,5);a.bf('source');a.shr(11,5,5);a.mask(11,11,0xfffe);a.add(18,18,11);a.j('clamp')
 a.label('tear_source');a.shr(11,24,3);a.mask(11,11,3);a.sfi(1,11,1);a.bf('source');a.shr(11,5,4);a.mask(11,11,0xfffe);a.add(18,18,11);a.j('clamp')
 a.label('mosaic_source');a.alu(3,18,22,30);a.add(18,18,28);a.addi(18,18,-1);a.alu(3,20,24,30);a.add(20,20,28);a.addi(20,20,-1);a.j('clamp')
 a.label('ascii_source');a.mask(18,22,0xfffc);a.addi(18,18,2);a.mask(20,24,0xfffc);a.addi(20,20,2);a.j('clamp')
 a.label('clamp');a.addi(11,5,-2);a.sf(5,18,11);a.bf('clamp_y');a.mov(18,11)
 a.label('clamp_y');a.addi(11,6,-2);a.sf(5,20,11);a.bf('source');a.mov(20,11)
 a.label('source');a.mul(2,20,5);a.add(2,2,18);a.add(2,2,3)
 a.load(0x23,11,2);a.load(0x23,12,2,1);a.add(2,2,5);a.load(0x23,13,2);a.load(0x23,15,2,1)
 a.shr(2,20,1);a.mul(2,2,5);a.add(2,2,18);a.add(2,2,4);a.load(0x23,19,2);a.load(0x23,21,2,1)
 a.sfi(0,7,1);a.bf('vhs');a.sfi(0,7,5);a.bf('tear');a.sfi(0,7,7);a.bf('mosaic');a.sfi(0,7,3);a.bf(ART);a.sfi(0,7,9);a.bf(ART);a.sfi(3,7,11);a.bf(ART)
 # Live-only palette rendering preserves fine luma structure.
 a.sfi(1,5,160);a.bf('full_palette');a.sfi(0,6,80);a.bf(DETAIL);a.label('full_palette')
 # Full-size photos/video retain original palette/dither algorithms.
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
 a.add(2,16,22);a.store(0x36,2,19);a.store(0x36,2,21,1);a.label('advance');a.addi(22,22,2);a.j('pixel')
 a.label('nextrow');a.add(14,14,5);a.add(14,14,5);a.add(16,16,5);a.addi(24,24,2);a.j('row')
 a.label('restore');a.addi(1,1,40)
 for i,r in enumerate(saved):a.load(0x21,r,1,-4*(i+1))
 a.label('return');a.ret()
 main=a.finish();write=a.labels['write'];a_main_advance=a.labels['advance']
 assert len(main)<=1160,len(main)
 # UV420 chroma stays shared by each 2x2 cell, but each of its four Y samples
 # retains 75% of its own original luminance. No frame buffer or heap needed.
 a=Asm(DETAIL)
 a.add(17,11,12);a.add(17,17,13);a.add(17,17,15);a.shr(17,17,8)
 a.shl(17,17,2);a.addi(2,7,-1);a.shl(2,2,4);a.add(17,17,2);ptr(a,2,palette);a.add(17,17,2)
 a.load(0x23,18,17);a.load(0x23,19,17,1);a.load(0x23,21,17,2)
 for reg in (11,12,13,15):
  a.shl(17,reg,1);a.add(reg,reg,17);a.add(reg,reg,18);a.shr(reg,reg,2)
 # Single-pixel, low-amplitude ordered texture for the three dither styles.
 a.sfi(0,7,6);a.bf('texture');a.sfi(0,7,8);a.bf('texture');a.sfi(1,7,9);a.bf(write)
 a.label('texture');a.addi(11,11,-4);a.addi(12,12,4);a.addi(13,13,4);a.addi(15,15,-4);a.j(write)
 detail=a.finish()
 return {base:main,DETAIL:detail,**art(k=bayer,palette=palette,advance=a_main_advance)}

def art(k,palette,advance):
 a=Asm(ART)
 # Reuse the four loaded original Y values to select shared chroma.
 a.mov(8,7)
 a.label('selected');a.li(19,128);a.li(21,128)
 a.sfi(0,8,11);a.bf('paper_uv');a.sfi(1,8,15);a.bf('chroma_ready');a.li(19,8*16);a.j('palette_uv')
 a.label('paper_uv');a.li(19,10*16);a.label('palette_uv')
 a.add(17,11,12);a.add(17,17,13);a.add(17,17,15);a.shr(17,17,8);a.shl(17,17,2)
 ptr(a,2,palette);a.add(2,2,19);a.add(17,17,2);a.load(0x23,19,17,1);a.load(0x23,21,17,2)
 a.label('chroma_ready');a.add(2,16,22);a.store(0x36,2,19);a.store(0x36,2,21,1)
 # Shared glyph chosen once per output2x2 from the sampled character cell.
 a.add(19,11,12);a.add(19,19,13);a.add(19,19,15);a.shr(19,19,7);a.shl(19,19,3);ptr(a,17,GLYPHS);a.add(19,19,17);a.li(18,0)
 a.label('sample');a.mask(20,18,1);a.add(20,20,22);a.shr(21,18,1);a.add(21,21,24)
 a.mul(2,21,5);a.add(2,2,20);a.add(2,2,3);a.load(0x23,11,2)
 a.sfi(0,8,11);a.bf(PAPER);a.sfi(0,8,12);a.bf(ASCII);a.sfi(0,8,14);a.bf(RELIEF);a.sfi(0,8,15);a.bf(RISO)
 a.sfi(0,8,13);a.bf('lines')
 a.sfi(0,8,3);a.bf('engrave')
 # Bayer is single-pixel (not 2x2), with thresholds in video-range Y.
 a.mask(13,21,3);a.shl(13,13,2);a.mask(17,20,3);a.add(13,13,17);ptr(a,17,k);a.add(13,13,17);a.load(0x23,13,13)
 a.li(17,14);a.mul(13,13,17);a.addi(13,13,23);a.j('threshold')
 # Integer analogue of luminance-warped engraving lines in Patch Lab.
 a.label('engrave');a.shr(13,11,4);a.add(13,13,20);a.add(13,13,21);a.mask(13,13,7);a.li(17,28);a.mul(13,13,17);a.addi(13,13,26)
 a.label('lines');a.sfi(1,8,13);a.bf('threshold');a.mask(13,21,7);a.li(17,28);a.mul(13,13,17);a.addi(13,13,26)
 a.label('threshold');a.sf(2,11,13);a.li(12,16);a.bnf('tone');a.li(12,235)
 a.label('tone');a.sfi(1,5,160);a.bf('store');a.sfi(1,6,80);a.bf('store')
 # Readable monochrome viewfinder, exact 1-bit output in saved frames.
 a.shl(17,11,1);a.add(17,17,11);a.add(12,12,17);a.shr(12,12,2)
 a.label('store');a.store(0x36,2,12);a.addi(18,18,1);a.sfi(4,18,4);a.bf('sample');a.j(advance)
 code=a.finish();selected=a.labels['selected'];tone=a.labels['tone']
 assert len(code)<=448,len(code)
 a=Asm(PAPER)
 # Four paper tones, without displaced blocks, noise or extra frame storage.
 a.shr(13,11,6);a.shl(13,13,2);ptr(a,17,palette+10*16);a.add(13,13,17);a.load(0x23,12,13);a.j(tone)
 paper=a.finish();assert PAPER+len(paper)<=0x20526c8
 return {ART:code,PAPER:paper,**extras(tone)}

# Four-pixel-tall microglyphs, padded to retain the existing8-byte stride.
DOT=(0,0,6,0)
COLON=(6,0,6,0)
PLUS=(2,7,2,2)
GLYPH_ROWS=tuple(tuple(rows)+(0,0,0,0) for rows in ((0,0,0,0),DOT,COLON,PLUS,tuple(v^15 for v in PLUS),tuple(v^15 for v in COLON),tuple(v^15 for v in DOT),(15,15,15,15)))

def extras(tone):
 a=Asm(ASCII)
 a.mask(12,21,3);a.add(12,12,19);a.load(0x23,12,12)
 a.mask(17,20,3);ptr(a,13,MASKS);a.add(17,17,13);a.load(0x23,17,17);a.alu(3,12,12,17)
 a.sfi(0,12,0);a.li(12,16);a.bf('out');a.li(12,235);a.label('out')
 # Full-size output keeps25% original local luma, revealing structure inside cells.
 a.sfi(1,5,160);a.bf('blend');a.sfi(0,6,80);a.bf(tone)
 a.label('blend');a.shl(13,12,1);a.add(12,12,13);a.add(12,12,11);a.shr(12,12,2);a.j(tone)
 ascii_code=a.finish();assert len(ascii_code)<=128
 a=Asm(RELIEF)
 # Forward-only derivative, horizontal edge guards; no additional frame buffer.
 a.addi(13,5,-2);a.sf(3,20,13);a.li(12,128);a.bf('out')
 a.load(0x23,17,2,2);a.sub(12,11,17);a.shl(12,12,1);a.addi(12,12,128)
 a.sfi(12,12,16);a.bnf('high');a.li(12,16);a.label('high');a.sfi(10,12,235);a.bnf('out');a.li(12,235);a.label('out');a.j(tone)
 relief=a.finish();assert RELIEF+len(relief)<=0x2052008
 a=Asm(RISO)
 # Deterministic dry-ink grain, subtle luminance texture, separate warm palette.
 a.li(13,13);a.mul(13,13,20);a.li(17,7);a.mul(17,17,21);a.add(13,13,17);a.mask(13,13,15)
 a.add(12,11,13);a.addi(12,12,-7);a.sfi(12,12,16);a.bnf('high');a.li(12,16)
 a.label('high');a.sfi(10,12,235);a.bnf('out');a.li(12,235);a.label('out');a.j(tone)
 riso=a.finish();assert len(riso)<=104
 return {ASCII:ascii_code,GLYPHS:bytes(v for rows in GLYPH_ROWS for v in rows),MASKS:bytes((1,2,4,8)),RELIEF:relief,RISO:riso}
