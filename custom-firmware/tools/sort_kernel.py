"""Bounded in-place 2x2 YUV block sorting for still frames, no allocations."""
from effect_kernel import Asm,SLOTS,ENTRY
SORT=0x0205195c
SORT_END=ENTRY

def sorter(live=False):
    a=Asm(SORT)
    # The native effect dispatcher supplied even height and padded stride.
    for reg,lo,hi in [(5,32 if live else 352,4096),(6,2,4096)]:
        a.sfi(4,reg,lo);a.bf('return');a.sfi(2,reg,hi);a.bf('return')
    a.mask(11,5,31);a.sfi(1,11,0);a.bf('return')
    a.mask(11,6,1);a.sfi(1,11,0);a.bf('return')
    for reg in (3,4):a.sfi(0,reg,0);a.bf('return')
    saved=(2,14,16,18,20,22,24,26,28,30)
    for i,r in enumerate(saved):a.store(0x35,1,r,-4*(i+1))
    a.addi(1,1,-40)
    a.mov(14,3);a.add(16,3,5);a.mov(18,4);a.li(20,0)
    if live:
        a.li(28,255);a.sfi(2,5,640);a.bf('window_ready');a.li(28,31);a.label('window_ready')
    a.label('row');a.sf(3,20,6);a.bf('restore');a.li(22,2)
    a.mask(30,20,32)
    a.label('column');a.sf(3,22,5);a.bf('nextrow');a.mov(24,22)
    a.label('insert')
    if live:a.alu(3,11,24,28)
    else:a.mask(11,24,127)
    a.sfi(0,11,0);a.bf('nextcol')
    # Compare the two top-row luma samples, without splitting chroma blocks.
    a.add(26,14,24)
    a.load(0x23,11,26);a.load(0x23,12,26,1);a.add(11,11,12)
    a.sfi(4,11,48 if live else 96);a.bf('nextcol');a.sfi(2,11,464 if live else 416);a.bf('nextcol')
    a.load(0x23,13,26,-2);a.load(0x23,15,26,-1);a.add(13,13,15)
    a.sfi(4,13,48 if live else 96);a.bf('nextcol');a.sfi(2,13,464 if live else 416);a.bf('nextcol')
    a.sfi(1,30,0);a.bf('descending')
    a.sf(3,11,13);a.bf('nextcol');a.j('swap')
    a.label('descending');a.sf(5,11,13);a.bf('nextcol')
    a.label('swap')
    for row in (14,16,18):
        a.add(26,row,24);a.load(0x25,11,26);a.load(0x25,13,26,-2)
        a.store(0x37,26,13);a.store(0x37,26,11,-2)
    a.addi(24,24,-2);a.j('insert')
    a.label('nextcol');a.addi(22,22,2);a.j('column')
    a.label('nextrow');a.add(14,14,5);a.add(14,14,5);a.add(16,16,5);a.add(16,16,5);a.add(18,18,5);a.addi(20,20,2);a.j('row')
    a.label('restore');a.addi(1,1,40)
    for i,r in enumerate(saved):a.load(0x21,r,1,-4*(i+1))
    a.label('return')
    if live:
        from preview_badge import BADGE
        a.j(BADGE)
    else:a.ret()
    code=a.finish()
    if SORT+len(code)>SORT_END:raise ValueError('Sorting function overflow')
    s=Asm(SLOTS[1]);s.li(7,1)
    if not live:s.sfi(5,5,320);s.bf(ENTRY+4)
    s.j(SORT)
    return {SORT:code,SLOTS[1]:s.finish()}
