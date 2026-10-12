"""Transient preview menu using native millisecond clock; offline assembler."""
from effect_kernel import Asm
from effects_v05 import MENU,DATA
from mode_hook import SETTER
from date_video_patch import ptr
from PIL import Image,ImageDraw
from ru_pixels import text,text_width
from effects_v05 import LABELS
import struct
EVENT=0x2051800;GATE=0x2051850;STATE=0x2051910;SHUTTER=0x2051920
TICK=0x208a35c
SELECT_CALLS=(0x20090b4,0x200911c,0x200e400,0x200e468)
SHUTTER_SITE=0x2009204

def menu_bits(labels=LABELS,paired=False):
    out=bytearray()
    for i in range(12):
        im=Image.new('RGB',(96,16));label=labels[i//2 if paired else i%6]
        text(im,((96-text_width(label))//2,0),label,(255,255,255))
        sub=f'{i+1:02}/12  '+('КОНТР II' if (i%2 if paired else i>=6) else 'КОНТР I')
        text(im,((96-text_width(sub))//2,9),sub,(255,255,255))
        d=ImageDraw.Draw(im)
        d.line([(1,4),(3,2),(5,4)],fill='white');d.line([(3,2),(3,6)],fill='white')
        d.line([(90,2),(92,4),(94,2)],fill='white');d.line([(92,0),(92,4)],fill='white')
        for row in range(16):
            for x in range(0,96,8):out.append(sum((im.getpixel((x+j,row))[0]>0)<<(7-j) for j in range(8)))
    return bytes(out)

def patches():
    out={DATA:menu_bits(),STATE:bytes(8)}
    # Only the four accepted photo/video effect-key callbacks restart visibility.
    # Other calls to the native setter (entry, cleanup) never reopen the menu.
    a=Asm(EVENT);ptr(a,11,TICK);a.load(0x21,12,11);ptr(a,11,STATE)
    a.store(0x35,11,12,4);a.li(12,1);a.store(0x35,11,12);a.j(SETTER)
    out[EVENT]=a.finish();assert EVENT+len(out[EVENT])<=GATE
    a=Asm(GATE);ptr(a,11,STATE);a.load(0x21,12,11);a.sfi(0,12,0);a.bf('return')
    a.load(0x21,12,11,4);ptr(a,13,TICK);a.load(0x21,13,13);a.sub(13,13,12)
    # Unsigned subtraction is correct across 32-bit wraparound.
    a.sfi(3,13,2000);a.bf('hide')
    a.sfi(1,5,160);a.j(MENU+4) # replay displaced menu instruction/condition
    a.label('hide');a.li(12,0);a.store(0x35,11,12)
    a.label('return');a.ret()
    out[GATE]=a.finish();assert GATE+len(out[GATE])<=STATE
    # At shutter callback after key-down and event-valid checks, before either
    # capture path. Replay original movhi r2,0x208, then continue unchanged.
    a=Asm(SHUTTER);ptr(a,11,STATE);a.store(0x35,11,0);a.imm(6,2,0,0x208);a.j(SHUTTER_SITE+4)
    out[SHUTTER]=a.finish();assert SHUTTER+len(out[SHUTTER])<=0x2051948
    for address,target,op in [(MENU,GATE,0),(SHUTTER_SITE,SHUTTER,0)]+[(x,EVENT,1) for x in SELECT_CALLS]:
        a=Asm(address);a.branch(op,target);out[address]=a.finish()
    return out

def expected_original():
    out={SHUTTER_SITE:struct.pack('<I',0x18400208)}
    a=Asm(MENU);a.sfi(1,5,160);out[MENU]=a.finish()
    for address in SELECT_CALLS:
        a=Asm(address);a.branch(1,SETTER);out[address]=a.finish()
    return out
