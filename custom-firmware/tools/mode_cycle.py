"""Bounded photo/video selector edits: 1 INK, 2 SORT, 3 GHOST only."""
import struct
from effect_kernel import Asm
FORWARD=(0x02009094,0x0200e3e0)
REVERSE=(0x020090f8,0x0200e444)
NOP=0x15000000

def patches(maximum=3):
    assert 2 <= maximum <= 255
    out={}
    for address in FORWARD:
        a=Asm(address);a.load(0x23,4,3,0x66);a.addi(4,4,1)
        a.sfi(2,4,maximum);a.bnf('store');a.li(4,1)
        a.label('store');a.store(0x36,3,4,0x66);a.mov(3,4);a.emit(NOP)
        out[address]=a.finish();assert len(out[address])==32
    for address in REVERSE:
        a=Asm(address);a.load(0x23,4,3,0x66);a.addi(4,4,-2)
        a.sfi(2,4,maximum-2);a.bf('wrap');a.addi(4,4,1);a.j('store')
        a.label('wrap');a.li(4,maximum);a.label('store');a.store(0x36,3,4,0x66);a.mov(3,4)
        out[address]=a.finish();assert len(out[address])==36
    a=Asm(0x02006e68);a.li(3,1);out[a.base]=a.finish()
    a=Asm(0x02006e70);a.store(0x36,14,3,0x66);out[a.base]=a.finish()
    # Do not clear the custom category after the default setter initialized it.
    out[0x02006ea0]=struct.pack('<I',NOP)
    # Keep selected index for video entry; setter(0) still performs exit cleanup.
    out[0x02006f20]=struct.pack('<I',NOP)
    return out

def expected_original():
    out={}
    for p in FORWARD:
        out[p]=struct.pack('<8I',0x8c830066,0xbc240005,0x10000003,0xd8032866,0x00000003,0x9c840001,0xd8032066,0x8c630066)
    for p in REVERSE:
        out[p]=struct.pack('<9I',0x8c830066,0xbc240000,0x10000004,0x9c400005,0xd8031066,0x00000003,0x9c84ffff,0xd8032066,0x8c630066)
    for p,w in [(0x02006e68,0xa8620000),(0x02006e70,0xd80e1066),(0x02006ea0,0xd80e1065),(0x02006f20,0xd8022066)]:out[p]=struct.pack('<I',w)
    return out
