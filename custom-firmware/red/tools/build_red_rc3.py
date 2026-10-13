#!/usr/bin/env python3
"""Exact rc2 delta for red B. Offline only; native control/video paths retained."""
import struct,json
from pathlib import Path
import red_port as r
from red_effects_rc3 import kernels,palettes,LABELS,DETAIL,ART,PATCH,PAPER
from build_red import ROOT,off,sha
OLD=ROOT/'custom-firmware/red/builds/sboy-red-1.0-rc2'
OUT=ROOT/'custom-firmware/red/builds/sboy-red-1.0-rc3'
OLD_SHA='0834409f78d532772eeb64502ece4a6fb38cd8d8fb7977610f7b16b2308ad657'

def patches():
 old,_,l=r.build_patches();k=l['K'];p=kernels(k,k+1160,k+1352,r.TICK)
 p[k]+=struct.pack('<I',0x15000000)*((1160-len(p[k]))//4)
 p[k+1160]=palettes()
 p[ART]+=struct.pack('<I',0x15000000)*((448-len(p[ART]))//4)
 # The deleted sorter no longer has an entry path: all modes use the kernel.
 a=r.Asm(l['MASTER']);r.save(a,(9,3,4,5,6));r.ptr(a,11,r.UI);a.load(0x23,7,11,0x5e);r.call(a,k)
 a.mul(4,5,6);r.call(a,r.FLUSH)
 a.load(0x21,3,1,8);a.load(0x21,5,1,4);a.load(0x21,6,1,0);a.mul(4,5,6);a.shr(4,4,1);r.call(a,r.FLUSH)
 r.restore(a,(9,3,4,5,6));a.ret();data=a.finish();assert len(data)<=len(old[l['MASTER']]);p[l['MASTER']]=data+struct.pack('<I',0x15000000)*((len(old[l['MASTER']])-len(data))//4)
 saved=r.LABELS
 try:r.LABELS=LABELS;p[l['DATA']]=r.menu_bits()
 finally:r.LABELS=saved
 intervals=sorted((a,a+len(v)) for a,v in p.items())
 for (a,b),(c,d) in zip(intervals,intervals[1:]):assert b<=c,(hex(a),hex(c))
 for a,b in intervals:
  assert r.START<=a<b<=r.END
  for olda,v in old.items():
   if olda in (k,k+1160,l['SORT'],l['MASTER'],l['DATA']):continue
   assert b<=olda or olda+len(v)<=a,('native integration overlap',hex(a),hex(olda))
 return p,l

def build(out=OUT):
 base=(OLD/'DestBin.bin').read_bytes()
 if len(base)!=0x100000 or sha(base)!=OLD_SHA:raise ValueError('Wrong rc2 baseline')
 out.mkdir(parents=True,exist_ok=True);im=bytearray(base);allowed=set();changes=[]
 def put(o,b,role):
  span=set(range(o,o+len(b)));assert not allowed&span;allowed.update(span);im[o:o+len(b)]=b;changes.append(dict(offset=hex(o),bytes=len(b),role=role,before_sha256=sha(base[o:o+len(b)]),after_sha256=sha(b)))
 p,l=patches()
 for a,b in p.items():put(off(a),b,'four replacements / finer pixels / labels')
 put(0xbde9d,b'SBOY-B-1.2\0\0','native update identity')
 diffs={i for i,(x,y) in enumerate(zip(base,im)) if x!=y};assert diffs<=allowed and len(im)==len(base)
 (out/'DestBin.bin').write_bytes(im)
 m=dict(version='СБОЙ КРАСНАЯ 1.0-rc3',sha256=sha(im),baseline_rc2_sha256=OLD_SHA,changed_bytes=len(diffs),bytes=len(im),changes=changes,labels=LABELS,removed={'PHO00009':'СОРТ','PHO00015':'ДУОТОН','PHO00017':'ОСКОЛКИ','PHO00018':'ХРОМА'},native_update_identity='SBOY-B-1.2',status='offline candidate; hardware pending',preserved='Native LCD/sensor, light control, CSI/JPEG/AVI/audio, keys, 2-second menu',adaptations='Patch Lab-inspired integer engraving, paper quantization, five rectangular patches; Bayer B&W instead of plugin Floyd-Steinberg; 75% source luma in exact160x80 art preview; half-sized mosaic blocks')
 (out/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:m[k] for k in ('version','sha256','changed_bytes','status')},ensure_ascii=False,indent=2));return m
if __name__=='__main__':build()
