"""Date-only display and deferred YUV processing for native buffered video.
No new hardware register operations; retain native capture/JPEG/audio routines.
"""
import struct
from effect_kernel import Asm,ENTRY
from sort_kernel import sorter,SORT
DATE=0x02030adc
READY=0x02051954
DEFER=0x02030af0
WORKER=0x02051b20
STATE=0x0208d120
UI=0x0208d08c

def ptr(a,r,v):a.imm(6,r,0,v>>16);a.imm(0x2a,r,r,v&65535)
def call(a,v):a.branch(1,v)
def patches():
    out={}
    a=Asm(DATE);a.li(2,0);a.store(0x36,4,2,10);a.store(0x36,7,2);a.mov(11,4);a.j(0x02030bf0);out[DATE]=a.finish()
    # Executed after native CSI pause, before stamp and JPEG. Return from IRQ
    # promptly; never run a pixel loop in the capture interrupt.
    a=Asm(DEFER);ptr(a,3,READY);a.li(4,1);a.store(0x35,3,4);a.li(11,1);a.j(0x02034bf0);out[DEFER]=a.finish()
    a=Asm(0x02034bac);a.j(DEFER);out[a.base]=a.finish()
    out[READY]=bytes(4)
    # Main video loop: consume one paused frame, process, stamp, then encode.
    a=Asm(WORKER)
    a.store(0x35,1,2,-8);a.store(0x35,1,9,-4);a.addi(1,1,-8)
    ptr(a,2,READY);a.load(0x21,3,2);a.sfi(0,3,0);a.bf('done')
    a.store(0x35,2,0)
    ptr(a,3,0x0208fb1c);a.load(0x23,3,3);a.sfi(1,3,1);a.bf('done')
    ptr(a,2,STATE);ptr(a,3,UI);a.load(0x23,3,3,0x65);a.sfi(1,3,2);a.bf('stamp')
    a.load(0x21,3,2,0x18);a.load(0x21,4,2,0x1c);a.load(0x25,5,2,0xc);a.load(0x25,6,2,0xe);call(a,0x02018088)
    a.label('stamp');a.load(0x23,3,2,2);a.sfi(1,3,1);a.bf('encode')
    a.load(0x21,3,2,0x18);call(a,0x0203ac24)
    a.label('encode');a.load(0x21,3,2,0x48);a.load(0x21,4,2,0x50);a.add(4,3,4);call(a,0x0202bf60)
    call(a,0x0202c698);a.li(3,16);a.li(4,1);call(a,0x0201fcc8)
    a.label('done');a.addi(1,1,8);a.load(0x21,9,1,-4);a.load(0x21,2,1,-8);a.j(0x020468e8)
    code=a.finish();assert SORT+len(sorter(live=True)[SORT])<=WORKER and WORKER+len(code)<=ENTRY
    out[WORKER]=code
    a=Asm(0x0200c82c);call(a,WORKER);out[a.base]=a.finish()
    # Select already existing buffered encoder path even with date stamp off.
    a=Asm(0x02037458);a.j(0x020375a4);out[a.base]=a.finish()
    out[0x020375bc]=struct.pack('<I',0x15000000)
    return out

def expected_original():
    values={DATE:0xa4a80004,0x02034bac:0x8c620002,0x0200c82c:0x0400e82f,0x02037458:0x10000004,0x020375bc:0x1000006a}
    return {a:struct.pack('<I',w) for a,w in values.items()}
