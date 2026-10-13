#!/usr/bin/env python3
"""Red-only rc3 delta:14 effects, microASCII, compact64px menu, no hardware I/O."""
import struct,json
from pathlib import Path
import red_port as r
from red_effects_rc6 import kernels,palettes,LABELS,ART
from build_red import ROOT,off,sha
OLD=ROOT/'custom-firmware/red/builds/sboy-red-1.0-rc5'
OUT=ROOT/'custom-firmware/red/builds/sboy-red-1.0-rc6'
OLD_SHA='dac7ce7652f36fd406350ca8e5fd99de68602b9acc09d0609a23317fe61f0c4a'
COUNT=len(LABELS)

def menu_bits():
 from PIL import Image,ImageDraw
 from ru_pixels import text,text_width
 data=bytearray()
 for i,label in enumerate(LABELS):
  assert text_width(label)<=64
  im=Image.new('L',(64,16));d=ImageDraw.Draw(im);text(im,((64-text_width(label))//2,0),label,255)
  number=f'{i+1:02}/{COUNT}';text(im,((64-text_width(number))//2,9),number,255)
  d.line([(2,13),(5,10),(8,13)],fill=255);d.line((5,10,5,15),fill=255)
  d.line([(55,11),(58,14),(61,11)],fill=255);d.line((58,9,58,14),fill=255)
  for y in range(16):
   for x in range(0,64,8):data.append(sum(bool(im.getpixel((x+j,y)))<<(7-j) for j in range(8)))
 return bytes(data)

def menu(l):
 a=r.Asm(l['MENU'])
 for reg,n in ((5,160),(6,80)):a.sfi(1,reg,n);a.bf('return')
 r.ptr(a,11,l['STATE']);a.load(0x21,12,11);a.sfi(0,12,0);a.bf('return');a.load(0x21,12,11,4)
 r.ptr(a,13,r.TICK);a.load(0x21,13,13);a.sub(13,13,12);a.sfi(3,13,2000);a.bf('hide')
 r.ptr(a,11,r.UI);a.load(0x23,11,11,0x5e);a.addi(11,11,-1);a.sfi(2,11,COUNT-1);a.bf('return')
 a.shl(11,11,7);r.ptr(a,8,l['DATA']);a.add(8,8,11);a.addi(11,3,18*160+48);a.li(12,16)
 a.label('row');a.li(15,8)
 a.label('byte');a.load(0x23,13,8);a.addi(8,8,1);a.li(17,8)
 a.label('bit');a.mask(21,13,128);a.li(19,16);a.sfi(0,21,0);a.bf('pixel');a.li(19,235)
 a.label('pixel');a.store(0x36,11,19);a.addi(11,11,1);a.shl(13,13,1);a.addi(17,17,-1);a.sfi(1,17,0);a.bf('bit')
 a.addi(15,15,-1);a.sfi(1,15,0);a.bf('byte');a.addi(11,11,96);a.addi(12,12,-1);a.sfi(1,12,0);a.bf('row')
 a.addi(11,4,9*160+48);a.li(12,8);a.li(19,128)
 a.label('uvrow');a.li(15,64)
 a.label('uvpixel');a.store(0x36,11,19);a.addi(11,11,1);a.addi(15,15,-1);a.sfi(1,15,0);a.bf('uvpixel')
 a.addi(11,11,96);a.addi(12,12,-1);a.sfi(1,12,0);a.bf('uvrow');a.ret()
 a.label('hide');a.store(0x35,11,0);a.label('return');a.ret();return a.finish()

def patches():
 old,_,l=r.build_patches();k=l['K'];p=kernels(k,k+1160,k+1352,r.TICK)
 p[k]+=struct.pack('<I',0x15000000)*((1160-len(p[k]))//4);p[k+1160]=palettes()
 p[ART]+=struct.pack('<I',0x15000000)*((448-len(p[ART]))//4)
 p[l['DATA']]=menu_bits()+bytes(128);assert len(p[l['DATA']])==1920 # clear removed Riso bitmap
 new=menu(l);assert len(new)<=len(old[l['MENU']]);p[l['MENU']]=new+struct.pack('<I',0x15000000)*((len(old[l['MENU']])-len(new))//4)
 # Only expand the validated custom-effect limit in the existing setter hook.
 oldword=struct.pack('<I',0x2f<<26|2<<21|12<<16|12);newword=struct.pack('<I',0x2f<<26|2<<21|12<<16|COUNT)
 code=old[l['HOOK']];assert code.count(oldword)==1;p[l['HOOK']]=code.replace(oldword,newword)
 for site,finish,forward in ((0x2016d7c,0x2016e14,True),(0x2016e8c,0x2016fb4,False),(0x201841c,0x2018480,True),(0x20184fc,0x2018600,False)):
  a=r.Asm(site);a.load(0x23,3,2,0x5e);a.addi(3,3,1 if forward else -1);a.sfi(4,3,1);a.bf('wrap');a.sfi(5,3,COUNT);a.bf('store')
  a.label('wrap');a.li(3,1 if forward else COUNT);a.label('store');a.store(0x36,2,3,0x5e);r.call(a,l['EVENT']);a.j(finish);p[site]=a.finish();assert len(p[site])==len(old[site])
 intervals=sorted((a,a+len(v)) for a,v in p.items())
 for (a,b),(c,d) in zip(intervals,intervals[1:]):assert b<=c,(hex(a),hex(c))
 replaced={k,k+1160,l['SORT'],l['DATA'],l['MENU'],l['HOOK'],0x2016d7c,0x2016e8c,0x201841c,0x20184fc}
 for a,b in intervals:
  for olda,v in old.items():
   if olda in replaced:continue
   assert b<=olda or olda+len(v)<=a,('occupied code',hex(a),hex(olda))
 return p,l

def build(out=OUT):
 base=(OLD/'DestBin.bin').read_bytes()
 if len(base)!=0x100000 or sha(base)!=OLD_SHA:raise ValueError('Wrong rc5 baseline')
 out.mkdir(parents=True,exist_ok=True);im=bytearray(base);allowed=set();changes=[]
 def put(o,b,role):
  span=set(range(o,o+len(b)));assert not span&allowed;allowed.update(span);im[o:o+len(b)]=b;changes.append(dict(offset=hex(o),bytes=len(b),role=role,before_sha256=sha(base[o:o+len(b)]),after_sha256=sha(b)))
 p,l=patches()
 for a,b in p.items():put(off(a),b,'14 effects and microASCII')
 put(0xbde9d,b'SBOY-B-1.5\0\0','native update identity')
 diffs={i for i,(x,y) in enumerate(zip(base,im)) if x!=y};assert diffs<=allowed and len(im)==len(base)
 (out/'DestBin.bin').write_bytes(im)
 m=dict(version='СБОЙ КРАСНАЯ 1.0-rc6',sha256=sha(im),baseline_rc5_sha256=OLD_SHA,changed_bytes=len(diffs),bytes=len(im),changes=changes,labels=LABELS,native_update_identity='SBOY-B-1.5',status='offline candidate; hardware pending',removed='РИЗО',ascii='Fixed4x4 cells at all sizes, full-size75% glyph+25% original luma; preview25% glyph+75% original',preserved='Other13 styles pixel-identical; nativeLCD/light/video untouched;14-mode menu with same2s timeout')
 (out/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:m[k] for k in ('version','sha256','changed_bytes','status')},ensure_ascii=False,indent=2));return m
if __name__=='__main__':build()
