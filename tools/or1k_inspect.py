"""Small offline OpenRISC decoder for inspecting the captured camera code.
Unknown encodings stay .word; this is not a general disassembler.
"""
import struct,sys
from pathlib import Path

def sx(x,n):return (x&((1<<(n-1))-1))-(x&(1<<(n-1)))
def decode(w,pc):
 op=w>>26;d=(w>>21)&31;a=(w>>16)&31;b=(w>>11)&31;k=w&65535
 if op in [0,1,3,4]:return f'{["j","jal","?","bnf","bf"][op]} {(pc+sx(w,26)*4)&0xffffffff:#010x}'
 if op==5:return f'nop {k}'
 if op==6:return f'movhi r{d}, {k:#x}'
 if op in [0x11,0x12]:return f'{"jr" if op==0x11 else "jalr"} r{b}'
 if 0x20<=op<=0x26:return f'{["ld","lwz","lws","lbz","lbs","lhz","lhs"][op-0x20]} r{d}, {sx(k,16):#x}(r{a})'
 if 0x27<=op<=0x2d:return f'{["addi","addic","andi","ori","xori","muli","mfspr"][op-0x27]} r{d}, r{a}, {(sx(k,16) if op in [0x27,0x28,0x2c] else k):#x}'
 if op==0x2e:return f'{["slli","srli","srai","rori"][(w>>6)&3]} r{d}, r{a}, {w&63}'
 cond={0:'eq',1:'ne',2:'gtu',3:'geu',4:'ltu',5:'leu',10:'gts',11:'ges',12:'lts',13:'les'}
 if op==0x2f:return f'sf{cond.get(d,str(d))}i r{a}, {sx(k,16):#x}'
 if op==0x39:return f'sf{cond.get(d,str(d))} r{a}, r{b}'
 if 0x33<=op<=0x37:return f'{["swa","sd","sw","sb","sh"][op-0x33]} {sx((w&0x7ff)|((w>>10)&0xf800),16):#x}(r{a}), r{b}'
 if op==0x38:
  sub=w&15
  if sub==8:return f'{["sll","srl","sra","ror"][(w>>6)&3]} r{d}, r{a}, r{b}'
  name={0:'add',1:'addc',2:'sub',3:'and',4:'or',5:'xor',6:'mul',9:'div',10:'divu',11:'mulu',14:'cmov'}.get(sub)
  if name:return f'{name} r{d}, r{a}, r{b}'
 return f'.word {w:#010x}'

def listing(data,base,start,length):
 lines=[]
 for pc in range(start,start+length,4):
  off=pc-base
  if off<0 or off+4>len(data):break
  w=struct.unpack_from('<I',data,off)[0]
  lines.append(f'{pc:08x}: {w:08x}  {decode(w,pc)}')
 return '\n'.join(lines)
if __name__=='__main__':
 b=Path(sys.argv[1]).read_bytes();base,start,length=map(lambda s:int(s,0),sys.argv[2:5]);print(listing(b,base,start,length))
