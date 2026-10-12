"""Execute generated words in a bounded, no-delay-slot OR1K interpreter.

This is offline validation, NOT evidence of hardware execution or performance.
"""
import random, struct, unittest
from effect_kernel import kernel, SLOTS, Asm

MASK=0xffffffff
def signed(x):return (x&0x7fffffff)-(x&0x80000000)
def sx(x,n):return (x&((1<<(n-1))-1))-(x&(1<<(n-1)))

class Machine:
    def __init__(self,patches,regions):
        self.code={a+i:struct.unpack_from('<I',b,i)[0] for a,b in patches.items() for i in range(0,len(b),4)}
        self.regions=regions;self.r=[(i*0x1234567)&MASK for i in range(32)];self.r[0]=0
        self.flag=False;self.steps=0;self.writes=0
    def mem(self,address,size,data=None):
        for base,buf in self.regions:
            if base<=address and address+size<=base+len(buf):
                off=address-base
                if data is None:return int.from_bytes(buf[off:off+size],'little')
                buf[off:off+size]=(data&((1<<(size*8))-1)).to_bytes(size,'little');self.writes+=1;return
        if data is None and all(((address+i)&~3) in self.code for i in range(size)):
            return int.from_bytes(bytes((self.code[(address+i)&~3] >> (8*((address+i)&3)))&255 for i in range(size)),'little')
        raise AssertionError('Out-of-bounds memory access: %#x / %d'%(address,size))
    def condition(self,c,a,b):
        return {0:lambda:a==b,1:lambda:a!=b,2:lambda:a>b,3:lambda:a>=b,4:lambda:a<b,5:lambda:a<=b,
                10:lambda:signed(a)>signed(b),11:lambda:signed(a)>=signed(b),12:lambda:signed(a)<signed(b),13:lambda:signed(a)<=signed(b)}[c]()
    def run(self,pc,limit):
        stop=self.r[9]
        while pc!=stop:
            if self.steps>=limit:raise AssertionError('Instruction limit exceeded')
            if pc in getattr(self,'calls',{}):
                self.calls[pc](self);pc=self.r[9];continue
            w=self.code[pc];op=w>>26;d=w>>21&31;a=w>>16&31;b=w>>11&31;k=w&65535
            nextpc=pc+4;v=None;self.steps+=1;r=self.r
            if op==1:
                r[9]=pc+4;nextpc=pc+sx(w,26)*4
            elif op in (0,3,4):
                if op==0 or (op==3 and not self.flag) or (op==4 and self.flag):nextpc=pc+sx(w,26)*4
            elif op==5:pass # l.nop
            elif op==0x11:nextpc=r[b]
            elif op==6:v=k<<16
            elif op==0x27:v=r[a]+sx(k,16)
            elif op==0x29:v=r[a]&k
            elif op==0x2a:v=r[a]|k
            elif op==0x2e:
                v=r[a]>>(k&63) if k&0xc0==0x40 else r[a]<<(k&63)
            elif op==0x2f:self.flag=self.condition(d,r[a],sx(k,16)&MASK)
            elif op==0x39:self.flag=self.condition(d,r[a],r[b])
            elif op==0x38:
                sub=w&0x7ff
                if sub==0:v=r[a]+r[b]
                elif sub==2:v=r[a]-r[b]
                elif sub==3:v=r[a]&r[b]
                elif sub==0x306:v=r[a]*r[b]
                elif sub==0x30a:v=r[a]//r[b]
                else:raise AssertionError('Unknown ALU word %#x'%w)
            elif op in (0x21,0x23,0x25):v=self.mem((r[a]+sx(k,16))&MASK,{0x21:4,0x23:1,0x25:2}[op])
            elif op in (0x35,0x36,0x37):
                off=sx((w&0x7ff)|((w>>10)&0xf800),16)
                self.mem((r[a]+off)&MASK,{0x35:4,0x36:1,0x37:2}[op],r[b])
            else:raise AssertionError('Unknown word %#x'%w)
            if v is not None and d:r[d]=v&MASK
            assert r[0]==0
            pc=nextpc
        return self.steps

def reference(y,uv,w,h,mode):
    """Algorithm oracle using immutable input, separate from instruction code."""
    old=bytes(y);out=bytearray(len(y));chroma=bytearray(len(uv))
    for row in range(h):
        band=(row*32//h)&15
        displacement=((w>>4)&~1) if mode and w>320 and 5<=band<=7 else 0
        for x in range(w):
            source=min(x+displacement,w-1)
            if mode==2 and displacement:source&=~7
            v=old[row*w+source]
            out[row*w+x]=(v&0xe0)+16 if mode==1 else (v&0xc0)+32
    palette=((157,143),(105,182),(91,120),(117,134))
    for row in range(h//2):
        band=(row*64//h)&7
        shift=((w>>4)&~1) if mode==1 and 2<=band<=4 else 0
        for x in range(0,w,2):
            if mode==0:pair=palette[out[row*2*w+x]//64]
            elif mode==2:pair=(137,154) if out[row*2*w+x]<128 else (110,115)
            else:
                src=row*w+min(x+shift,w-2)
                pair=tuple((v&0xe0)+16 for v in uv[src:src+2])
            chroma[row*w+x:row*w+x+2]=bytes(pair)
    return out,chroma

def execute(y,uv,w,h,mode):
    y=bytearray(y);uv=bytearray(uv);stack=bytearray(40)
    m=Machine(kernel(),[(0x2100000,y),(0x2400000,uv),(0x2800000,stack)])
    m.r[1]=0x2800028;m.r[3]=0x2100000;m.r[4]=0x2400000;m.r[5]=w;m.r[6]=h;m.r[9]=0xf0000000
    before=m.r.copy();m.run(SLOTS[mode],max(4096,w*h*70))
    for i in (1,2,9,10,14,16,18,20,22,24,26,28,30):
        if before[i]!=m.r[i]:raise AssertionError('Callee/stack register r%d changed'%i)
    return y,uv,m.steps

class KernelTests(unittest.TestCase):
    def test_known_instruction_encodings_from_resident_firmware(self):
        a=Asm(0);a.store(0x35,1,2,-4);a.load(0x21,2,1,-4);a.mul(3,3,4);a.li(3,11);a.divu(3,26,3)
        self.assertEqual(struct.unpack('<5I',a.finish()),(0xd7e117fc,0x8441fffc,0xe0632306,0x9c60000b,0xe07a1b0a))
    def test_reference_and_abi_with_guarded_memory(self):
        rng=random.Random(731)
        for w,h in ((32,2),(96,160),(160,80),(352,34),(640,480)):
            y=bytes(rng.randrange(256) for _ in range(w*h));uv=bytes(rng.randrange(256) for _ in range(w*h//2))
            for mode in range(3):
                with self.subTest(w=w,h=h,mode=mode):
                    actual=execute(y,uv,w,h,mode);expected=reference(y,uv,w,h,mode)
                    self.assertEqual(actual[:2],expected)
    def test_invalid_dimensions_exit_without_writes(self):
        for w,h in ((0,2),(31,4),(33,4),(8192,4),(32,0),(32,1),(32,3),(32,8192)):
            m=Machine(kernel(),[]);m.r[3]=1;m.r[4]=2;m.r[5]=w;m.r[6]=h;m.r[9]=0xf0000000
            m.run(SLOTS[0],100);self.assertEqual(m.writes,0)

if __name__=='__main__':unittest.main()
