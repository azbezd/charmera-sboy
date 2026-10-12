"""Russian mode caption only on the observed 160x80 preview, never stills."""
import struct
from effect_kernel import Asm,kernel,ENTRY,END
from ru_pixels import FONT,text_width
BADGE=ENTRY+len(kernel()[ENTRY])
LABELS=('ЧЕРНИЛА','СОРТ','ПРИЗРАК')
def bitmaps():
    out=bytearray()
    for label in LABELS:
        rows=[[0]*48 for _ in range(10)];x=(48-text_width(label))//2
        for ch in label:
            glyph=FONT[ch].split('/')
            for y,row in enumerate(glyph):
                for dx,v in enumerate(row):rows[y+1][x+dx]=int(v)
            x+=len(glyph[0])+1
        for row in rows:
            for i in range(0,48,8):out.append(sum(row[i+j]<<(7-j) for j in range(8)))
    return bytes(out)
def badge(top=70):
    if top%2 or not 0<=top<=70:raise ValueError("Caption top must be even and in frame")
    a=Asm(BADGE)
    a.sfi(1,5,160);a.bf('return');a.sfi(1,6,80);a.bf('return')
    a.sfi(2,7,2);a.bf('return')
    for reg in (3,4):a.sfi(0,reg,0);a.bf('return')
    a.shl(13,7,6);a.shl(15,7,2);a.sub(13,13,15)
    a.imm(6,8,0,0x0205);ptr_index=len(a.words);a.emit(0)
    a.add(8,8,13);a.addi(11,3,top*160+56);a.li(12,10)
    a.label('row');a.li(15,6)
    a.label('byte');a.load(0x23,13,8);a.addi(8,8,1);a.li(17,8)
    a.label('bit');a.mask(21,13,128);a.li(19,16);a.sfi(0,21,0);a.bf('pixel');a.li(19,235)
    a.label('pixel');a.store(0x36,11,19);a.addi(11,11,1);a.shl(13,13,1);a.addi(17,17,-1);a.sfi(1,17,0);a.bf('bit')
    a.addi(15,15,-1);a.sfi(1,15,0);a.bf('byte')
    a.addi(11,11,112);a.addi(12,12,-1);a.sfi(1,12,0);a.bf('row')
    a.addi(11,4,top*80+56);a.li(12,5);a.li(19,128)
    a.label('uvrow');a.li(15,48)
    a.label('uvpixel');a.store(0x36,11,19);a.addi(11,11,1);a.addi(15,15,-1);a.sfi(1,15,0);a.bf('uvpixel')
    a.addi(11,11,112);a.addi(12,12,-1);a.sfi(1,12,0);a.bf('uvrow')
    a.label('return');a.ret()
    data_address=BADGE+4*len(a.words)
    a.words[ptr_index]=0x2a<<26|8<<21|8<<16|(data_address&65535)
    blob=a.finish()+bitmaps()
    if BADGE+len(blob)>END:raise ValueError('Badge exceeds effect-7 slot: %d remaining %d'%(len(blob),END-BADGE))
    # Kernel argument registers survive, so tail-call after its stack restore.
    ret=ENTRY+len(kernel()[ENTRY])-4;tail=Asm(ret);tail.j(BADGE)
    return {BADGE:blob,ret:tail.finish()}
