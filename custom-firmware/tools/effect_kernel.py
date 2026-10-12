"""Offline OpenRISC effect kernel builder. Does NOT install or execute on USB.

Reuses the ABI observed at native effects 5, 6, 7: r3=Y, r4=interleaved
chroma, r5=padded width, r6=height. No allocation, calls, or MMIO.
The kernel occupies only the existing effect-7 function allocation.
"""
import struct

ENTRY = 0x02051c74
END = 0x020520a8
SLOTS = (0x0205179c, 0x02051948, ENTRY)

class Asm:
    def __init__(self,base):self.base=base;self.words=[];self.labels={};self.fix=[]
    def emit(self,w):self.words.append(w)
    def label(self,n):
        if n in self.labels:raise ValueError(n)
        self.labels[n]=self.base+4*len(self.words)
    def imm(self,op,d,a,k):self.emit(op<<26|d<<21|a<<16|(k&65535))
    def li(self,d,k):self.imm(0x27,d,0,k)
    def mov(self,d,a):self.imm(0x2a,d,a,0)
    def addi(self,d,a,k):self.imm(0x27,d,a,k)
    def mask(self,d,a,k):self.imm(0x29,d,a,k)
    def alu(self,sub,d,a,b):self.emit(0x38<<26|d<<21|a<<16|b<<11|sub)
    def add(self,d,a,b):self.alu(0,d,a,b)
    def sub(self,d,a,b):self.alu(2,d,a,b)
    def mul(self,d,a,b):self.alu(0x306,d,a,b)
    def divu(self,d,a,b):self.alu(0x30a,d,a,b)
    def shr(self,d,a,k):self.imm(0x2e,d,a,64|k)
    def shl(self,d,a,k):self.imm(0x2e,d,a,k)
    def sf(self,cond,a,b):self.emit(0x39<<26|cond<<21|a<<16|b<<11)
    def sfi(self,cond,a,k):self.imm(0x2f,cond,a,k)
    def branch(self,kind,label):self.fix.append((len(self.words),kind,label));self.emit(0)
    def j(self,label):self.branch(0,label)
    def bf(self,label):self.branch(4,label)
    def bnf(self,label):self.branch(3,label)
    def load(self,op,d,a,k=0):self.imm(op,d,a,k)
    def store(self,op,a,b,k=0):
        k&=65535;self.emit(op<<26|((k>>11)&31)<<21|a<<16|b<<11|(k&2047))
    def ret(self):self.emit(0x44004800)
    def finish(self):
        words=self.words.copy()
        for i,op,label in self.fix:
            target=self.labels[label] if isinstance(label,str) else label
            disp=target-(self.base+4*i)
            if disp%4 or not -(1<<27)<=disp<(1<<27):raise ValueError('Branch overflow')
            words[i]=op<<26|((disp//4)&0x3ffffff)
        return struct.pack('<%dI'%len(words),*words)

def kernel():
    a=Asm(ENTRY)
    a.li(7,2)  # native effect 7 selects GHOST; stubs enter after this instruction
    a.label('common')
    # Reject invalid geometry before touching a frame. Caller supplies padded
    # stride; native dispatcher rounded width up to a multiple of 32.
    a.sfi(4,5,32);a.bf('return')
    a.sfi(2,5,4096);a.bf('return')
    a.sfi(4,6,2);a.bf('return')
    a.sfi(2,6,4096);a.bf('return')
    a.mask(11,5,31);a.sfi(1,11,0);a.bf('return')
    a.mask(11,6,1);a.sfi(1,11,0);a.bf('return')
    a.sfi(0,3,0);a.bf('return');a.sfi(0,4,0);a.bf('return')
    saved=(2,14,16,18,20,22,24,26,28,30)
    for i,r in enumerate(saved):a.store(0x35,1,r,-4*(i+1))
    a.addi(1,1,-40)
    # r14=Y row, r16=UV row, r18=row, r20=UV rows, r22=shift,
    # r24=source offset, r26=row band, r28=Y row for chroma palette.
    a.mov(14,3);a.mov(16,4);a.li(18,0);a.shr(20,6,1)
    a.label('yrow')
    a.sf(3,18,6);a.bf('uv_begin')
    a.shl(26,18,5);a.divu(26,26,6);a.li(22,0)
    a.sfi(0,7,0);a.bf('ypixels_begin')
    a.sfi(5,5,320);a.bf('ypixels_begin')  # simplified live view
    a.mask(11,26,15);a.sfi(4,11,5);a.bf('ypixels_begin')
    a.sfi(2,11,7);a.bf('ypixels_begin')
    a.shr(22,5,4);a.mask(22,22,0xfffe)
    a.label('ypixels_begin');a.li(12,0)
    a.label('ypixel')
    a.sf(3,12,5);a.bf('ynext')
    a.add(24,12,22);a.sf(4,24,5);a.bf('source_ok');a.addi(24,5,-1)
    a.label('source_ok')
    a.sfi(1,7,2);a.bf('load_y')
    a.sfi(0,22,0);a.bf('load_y')
    a.mask(24,24,0xfff8)  # held blocks in displacement bands
    a.label('load_y');a.add(13,14,24);a.load(0x23,15,13)
    a.sfi(0,7,1);a.bf('tear_y')
    a.mask(15,15,0xc0);a.addi(15,15,32);a.j('write_y')
    a.label('tear_y');a.mask(15,15,0xe0);a.addi(15,15,16)
    a.label('write_y');a.add(13,14,12);a.store(0x36,13,15)
    a.addi(12,12,1);a.j('ypixel')
    a.label('ynext');a.add(14,14,5);a.addi(18,18,1);a.j('yrow')
    a.label('uv_begin');a.li(18,0);a.mov(28,3)
    a.label('uvrow');a.sf(3,18,20);a.bf('restore')
    a.li(12,0);a.shl(26,18,6);a.divu(26,26,6);a.li(22,0)
    a.sfi(1,7,1);a.bf('uvpixel')
    a.mask(11,26,7);a.sfi(4,11,2);a.bf('uvpixel')
    a.sfi(2,11,4);a.bf('uvpixel')
    a.shr(22,5,4);a.mask(22,22,0xfffe)
    a.label('uvpixel');a.sf(3,12,5);a.bf('uvnext')
    a.sfi(0,7,1);a.bf('tear_uv')
    a.add(13,28,12);a.load(0x23,15,13)
    a.sfi(0,7,2);a.bf('ghost_uv')
    # INK: violet shadows, coral middle, cream highlights. Luma is four
    # levels and chroma follows the corresponding 2x2 luminance block.
    a.li(24,157);a.li(30,143)
    a.sfi(4,15,64);a.bf('write_uv')
    a.li(24,105);a.li(30,182)
    a.sfi(4,15,128);a.bf('write_uv')
    a.li(24,91);a.li(30,120)
    a.sfi(4,15,192);a.bf('write_uv')
    a.li(24,117);a.li(30,134);a.j('write_uv')
    a.label('ghost_uv')
    a.li(24,137);a.li(30,154)
    a.sfi(4,15,128);a.bf('write_uv')
    a.li(24,110);a.li(30,115);a.j('write_uv')
    a.label('tear_uv')
    a.add(24,12,22);a.sf(4,24,5);a.bf('uvsource_ok');a.addi(24,5,-2)
    a.label('uvsource_ok');a.add(13,16,24);a.load(0x23,24,13);a.load(0x23,30,13,1)
    a.mask(24,24,0xe0);a.addi(24,24,16);a.mask(30,30,0xe0);a.addi(30,30,16)
    a.label('write_uv');a.add(13,16,12);a.store(0x36,13,24);a.store(0x36,13,30,1)
    a.addi(12,12,2);a.j('uvpixel')
    a.label('uvnext');a.add(16,16,5);a.add(28,28,5);a.add(28,28,5);a.addi(18,18,1);a.j('uvrow')
    a.label('restore');a.addi(1,1,40)
    for i,r in enumerate(saved):a.load(0x21,r,1,-4*(i+1))
    a.label('return');a.ret()
    code=a.finish()
    if len(code)>END-ENTRY:raise ValueError('Kernel exceeds inspected function allocation')
    patches={ENTRY:code}
    for mode,addr in enumerate(SLOTS[:2]):
        stub=Asm(addr);stub.li(7,mode);stub.j(ENTRY+4);patches[addr]=stub.finish()
    return patches

if __name__=='__main__':
    for addr,blob in kernel().items():print(hex(addr),len(blob))
