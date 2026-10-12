"""Six styles, two contrast strengths, preview-only live selector. Offline only."""
from effect_kernel import Asm,ENTRY
from sort_kernel import SORT
from preview_badge import BADGE
from date_video_patch import ptr,call,UI
from ru_pixels import FONT,text_width
from PIL import Image,ImageDraw
MASTER=0x20520a8;NEW=0x2052120;FINISH=0x2052480;MENU=0x2052600;DATA=0x2052700;CLOCK=0x2053000;END=0x20530c4;AUX=0x2051f00
LABELS=('ЧЕРНИЛА','СОРТ','ПРИЗРАК','РАЗРЫВ','РАСТР','НЕОН')

def guards(a,done):
    for reg,lo,hi in ((5,32,4096),(6,2,4096)):
        a.sfi(4,reg,lo);a.bf(done);a.sfi(2,reg,hi);a.bf(done)
    for reg,mask in ((5,31),(6,1)):
        a.mask(11,reg,mask);a.sfi(1,11,0);a.bf(done)
    for r in (3,4):a.sfi(0,r,0);a.bf(done)

def menu_bits():
    # 12 actual selectable presets: six styles at normal and strong contrast.
    from ru_pixels import text
    out=bytearray()
    for i in range(12):
        im=Image.new('RGB',(96,16));label=LABELS[i%6]
        text(im,((96-text_width(label))//2,0),label,(255,255,255))
        sub=f'{i+1:02}/12  '+('СИЛА II' if i>=6 else 'СИЛА I')
        text(im,((96-text_width(sub))//2,9),sub,(255,255,255))
        d=ImageDraw.Draw(im);d.line([(4,1),(1,3),(4,5)],fill='white');d.line([(91,1),(94,3),(91,5)],fill='white')
        for row in range(16):
            for x in range(0,96,8):out.append(sum((im.getpixel((x+j,row))[0]>0)<<(7-j) for j in range(8)))
    return bytes(out)

def patches(echo=False, paired=False, vhs=False):
    out={}
    a=Asm(MASTER);ptr(a,11,UI);a.load(0x23,7,11,0x66)
    a.sfi(4,7,1);a.bf('default');a.sfi(2,7,12);a.bf('default')
    if paired:
        a.j('index');a.label('default');a.li(7,1)
        a.label('index');a.addi(7,7,-1);a.shr(7,7,1)
        a.sfi(0,7,0);a.bnf('oldstyle');a.li(7,5);a.j(NEW)
        a.label('oldstyle');a.addi(7,7,-1)
    else:
        a.sfi(5,7,6);a.bf('index');a.addi(7,7,-6);a.j('index')
        a.label('default');a.li(7,1)
        a.label('index');a.addi(7,7,-1)
    a.sfi(0,7,1);a.bf(SORT);a.sfi(5,7,2);a.bf(ENTRY+4);a.j(NEW)
    out[MASTER]=a.finish();assert MASTER+len(out[MASTER])<=NEW
    a=Asm(NEW);guards(a,'return')
    saved=(2,14,16,18,20,22,24,26,28,30)
    for i,r in enumerate(saved):a.store(0x35,1,r,-4*(i+1))
    a.addi(1,1,-40);a.mov(14,3);a.mov(16,4);a.li(18,0)
    if vhs:
        ptr(a,26,0x208a35c);a.load(0x21,26,26);a.shr(26,26,7);a.mask(26,26,31)
    a.label('yrow');a.sf(3,18,6);a.bf('uvbegin');a.li(22,0)
    if vhs:
        a.sfi(1,7,5);a.bf('regular_row');a.add(11,18,26);a.mask(11,11,31);a.sfi(2,11,1);a.bf('yinit');a.shr(22,5,5);a.j('yinit');a.label('regular_row')
    a.sfi(1,7,3);a.bf('yinit');a.shr(11,18,3);a.mask(11,11,3);a.sfi(0,11,1);a.bnf('yinit')
    a.shr(22,5,4);a.mask(22,22,0xfffe)
    a.label('yinit');a.li(12,0);a.load(0x23,28,14)
    a.label('ypixel');a.sf(3,12,5);a.bf('ynext');a.add(24,12,22);a.sf(4,24,5);a.bf('source');a.addi(24,5,-1)
    a.label('source');a.add(13,14,24);a.load(0x23,15,13)
    a.sfi(0,7,4);a.bf('raster');a.sfi(0,7,5);a.bf('edge')
    a.mask(15,15,0xe0);a.addi(15,15,16);a.j('write')
    a.label('raster');a.mask(11,12,1);a.mask(13,18,1);a.shl(13,13,1);a.add(11,11,13)
    ptr(a,13,AUX);a.add(11,11,13);a.load(0x23,11,11);a.sf(2,15,11);a.li(15,32);a.bnf('write');a.li(15,224);a.j('write')
    a.label('edge')
    if vhs:
        # Small horizontal blur, lifted blacks and mild row modulation.
        a.addi(11,24,1);a.sf(4,11,5);a.bf('vhs_y');a.addi(11,5,-1)
        a.label('vhs_y');a.add(13,14,11);a.load(0x23,11,13);a.add(15,15,11);a.shr(15,15,1)
        a.shl(11,15,1);a.add(15,15,11);a.shr(15,15,2);a.addi(15,15,28)
        a.mask(11,18,3);a.sfi(1,11,0);a.bf('write');a.shr(11,15,4);a.sub(15,15,11)
    elif echo:
        # Both reads are from this pixel or future pixels, never overwritten Y.
        a.shr(11,5,5);a.add(11,11,12);a.sf(4,11,5);a.bf('echo_y');a.addi(11,5,-1)
        a.label('echo_y');a.add(13,14,11);a.load(0x23,11,13);a.add(15,15,11);a.shr(15,15,1)
    else:
        a.sub(11,15,28);a.mov(28,15);a.sfi(12,11,0);a.bnf('positive');a.sub(11,0,11)
        a.label('positive');a.li(15,16);a.sfi(5,11,8);a.bf('write');a.li(15,128);a.sfi(5,11,24);a.bf('write');a.li(15,235)
    a.label('write');a.add(13,14,12);a.store(0x36,13,15);a.addi(12,12,1);a.j('ypixel')
    a.label('ynext');a.add(14,14,5);a.addi(18,18,1);a.j('yrow')
    a.label('uvbegin');a.li(18,0);a.shr(20,6,1);a.mov(14,3)
    a.label('uvrow');a.sf(3,18,20);a.bf('restore');a.li(12,0);a.li(22,0)
    a.sfi(1,7,3);a.bf('uvpixel');a.shr(11,18,2);a.mask(11,11,3);a.sfi(1,11,2);a.bf('uvpixel');a.shr(22,5,5);a.mask(22,22,0xfffe)
    a.label('uvpixel');a.sf(3,12,5);a.bf('uvnext');a.sfi(0,7,3);a.bf('shift')
    a.li(24,145);a.li(30,155);a.sfi(0,7,5);a.bf('neonuv')
    a.add(13,14,12);a.load(0x23,15,13);a.sfi(4,15,128);a.bf('uvwrite');a.li(24,108);a.li(30,125);a.j('uvwrite')
    a.label('neonuv')
    if vhs:
        # Chroma holds in coarse 8-pixel groups, with small color delay.
        # Round upward so in-place reads never consume previous writes.
        a.addi(11,12,7);a.mask(11,11,0xfff8);a.shr(13,5,7);a.mask(13,13,0xfffe);a.add(11,11,13)
        a.sf(4,11,5);a.bf('vhs_uv');a.addi(11,5,-2)
        a.label('vhs_uv');a.add(13,16,11);a.load(0x23,24,13);a.load(0x23,30,13,1)
        a.addi(24,24,128);a.shr(24,24,1);a.addi(30,30,128);a.shr(30,30,1);a.j('uvwrite')
    elif echo:
        for shift,dst,label,offset in [(4,24,'echo_u',0),(5,30,'echo_v',1)]:
            a.shr(11,5,shift);a.mask(11,11,0xfffe);a.add(11,11,12)
            a.sf(4,11,5);a.bf(label);a.addi(11,5,-2)
            a.label(label);a.add(13,16,11);a.load(0x23,dst,13,offset)
        a.j('uvwrite')
    else:
        a.mask(11,18,16);a.sfi(0,11,0);a.bf('uvwrite');a.li(24,98);a.li(30,107);a.j('uvwrite')
    a.label('shift');a.add(24,12,22);a.sf(4,24,5);a.bf('uvsource');a.addi(24,5,-2)
    a.label('uvsource');a.add(13,16,24);a.load(0x23,24,13);a.load(0x23,30,13,1)
    a.label('uvwrite');a.add(13,16,12);a.store(0x36,13,24);a.store(0x36,13,30,1);a.addi(12,12,2);a.j('uvpixel')
    a.label('uvnext');a.add(16,16,5);a.add(14,14,5);a.add(14,14,5);a.addi(18,18,1);a.j('uvrow')
    a.label('restore');a.addi(1,1,40)
    for i,r in enumerate(saved):a.load(0x21,r,1,-4*(i+1))
    a.label('return');a.j(FINISH)
    out[NEW]=a.finish();assert NEW+len(out[NEW])<=FINISH,len(out[NEW])
    a=Asm(FINISH);guards(a,'menu');ptr(a,11,UI);a.load(0x23,11,11,0x66);a.sfi(4,11,1 if paired else 7);a.bf('menu');a.sfi(2,11,12);a.bf('menu')
    if paired:a.mask(11,11,1);a.sfi(1,11,0);a.bf('menu')
    a.mul(12,5,6);a.mov(11,3);ptr(a,13,AUX+4)
    a.label('contrast');a.load(0x23,15,11);a.add(15,15,13);a.load(0x23,15,15);a.store(0x36,11,15);a.addi(11,11,1);a.addi(12,12,-1);a.sfi(1,12,0);a.bf('contrast')
    a.label('menu');a.j(MENU);out[FINISH]=a.finish();assert FINISH+len(out[FINISH])<=MENU
    a=Asm(MENU)
    a.sfi(1,5,160);a.bf('return');a.sfi(1,6,80);a.bf('return')
    for r in (3,4):a.sfi(0,r,0);a.bf('return')
    ptr(a,11,UI);a.load(0x23,11,11,0x66);a.addi(11,11,-1);a.sfi(2,11,11);a.bf('return')
    a.li(13,192);a.mul(11,11,13);ptr(a,8,DATA);a.add(8,8,11);a.addi(11,3,18*160+32);a.li(12,16)
    a.label('row');a.li(15,12)
    a.label('byte');a.load(0x23,13,8);a.addi(8,8,1);a.li(17,8)
    a.label('bit');a.mask(21,13,128);a.li(19,16);a.sfi(0,21,0);a.bf('pixel');a.li(19,235)
    a.label('pixel');a.store(0x36,11,19);a.addi(11,11,1);a.shl(13,13,1);a.addi(17,17,-1);a.sfi(1,17,0);a.bf('bit')
    a.addi(15,15,-1);a.sfi(1,15,0);a.bf('byte');a.addi(11,11,64);a.addi(12,12,-1);a.sfi(1,12,0);a.bf('row')
    a.addi(11,4,9*160+32);a.li(12,8);a.li(19,128)
    a.label('uvrow');a.li(15,96)
    a.label('uvpixel');a.store(0x36,11,19);a.addi(11,11,1);a.addi(15,15,-1);a.sfi(1,15,0);a.bf('uvpixel')
    a.addi(11,11,64);a.addi(12,12,-1);a.sfi(1,12,0);a.bf('uvrow');a.label('return');a.ret()
    out[MENU]=a.finish();assert MENU+len(out[MENU])<=DATA,len(out[MENU])
    out[DATA]=menu_bits()
    out[AUX]=bytes([32,160,224,96])+bytes(max(16,min(235,128+(v-128)*3//2)) for v in range(256))
    assert AUX+len(out[AUX])<=MASTER
    assert DATA+len(out[DATA])<=CLOCK
    a=Asm(CLOCK);a.store(0x35,1,9,-4);a.addi(1,1,-4);call(a,0x2014388);call(a,0x200084c);a.addi(1,1,4);a.load(0x21,9,1,-4);a.ret();out[CLOCK]=a.finish();assert CLOCK+len(out[CLOCK])<=END
    for address,target,jal in [(0x205179c,MASTER,False),(BADGE,FINISH,False),(0x201853c,MASTER,True),(0x2000ae8,CLOCK,True)]:
        a=Asm(address);a.branch(1 if jal else 0,target);out[address]=a.finish()
    return out
