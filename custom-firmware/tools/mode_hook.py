"""Connect color slots 1..3 to bounded software kernels; offline assembler."""
from effect_kernel import Asm

SETTER = 0x02049964
HOOK = 0x020517a4  # after the replacement effect-5 entry stub
HOOK_END = 0x02051948
STATE = 0x0208d08c
ORIGINAL_WORD = 0xd7e117f4

def patches(maximum=3, master=False):
    assert 1 <= maximum <= 255
    a=Asm(HOOK)
    # Replay the sole displaced instruction before using caller-save scratch.
    a.emit(ORIGINAL_WORD)
    a.imm(6,11,0,STATE>>16);a.imm(0x2a,11,11,STATE&65535)
    a.mask(12,3,255)
    a.sfi(4,12,1);a.bf('native')
    a.sfi(2,12,maximum);a.bf('native')
    # Publish selector before category, then enable the native frame handshake.
    (a.li(13,5) if master else a.addi(13,12,4));a.store(0x36,11,13,0x69)
    a.li(13,2);a.store(0x36,11,13,0x65)
    a.li(13,1);a.store(0x36,11,13,0x64)
    # Run the ORIGINAL sensor/matrix programming with its neutral argument.
    a.li(3,0);a.j('resume')
    a.label('native')
    a.load(0x23,13,11,0x65);a.sfi(1,13,2);a.bf('resume')
    # Keep unrelated frame-overlay state; clear only our software category.
    a.li(13,0);a.store(0x36,11,13,0x65)
    a.label('resume');a.j(SETTER+4)
    code=a.finish()
    if len(code)>HOOK_END-HOOK:raise ValueError('Hook allocation overflow')
    stub=Asm(SETTER);stub.j(HOOK)
    return {SETTER:stub.finish(),HOOK:code}
