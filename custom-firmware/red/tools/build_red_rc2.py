#!/usr/bin/env python3
"""Narrow delta from reviewed rc1. No video/control/LCD relocation or changes."""
import struct,json,hashlib
from pathlib import Path
import red_port
from red_effects_rc2 import kernels,LABELS,DETAIL,CHROMA
from build_red import ROOT,off,sha
OLD=ROOT/'custom-firmware/red/builds/sboy-red-1.0-rc1'
OUT=ROOT/'custom-firmware/red/builds/sboy-red-1.0-rc2'
OLD_SHA='72c8d6ad4b54164c3dd06bd64d46a355ae71b8abaa20df503a26c45142dbd4da'

def patches():
 old,_,l=red_port.build_patches();k=l['K'];p=kernels(k,k+1160,k+1160+192,red_port.TICK)
 # Padding removes obsolete rc1 instructions, while every other address stays.
 p[k]+=struct.pack('<I',0x15000000)*((1160-len(p[k]))//4)
 saved=red_port.LABELS
 try:red_port.LABELS=LABELS;p[l['DATA']]=red_port.menu_bits()
 finally:red_port.LABELS=saved
 for a in (DETAIL,CHROMA):
  for olda,data in old.items():assert a+len(p[a])<=olda or olda+len(data)<=a,('Occupied cave',hex(a),hex(olda))
 return p,l

def build(out=OUT):
 base=(OLD/'DestBin.bin').read_bytes()
 if len(base)!=0x100000 or sha(base)!=OLD_SHA:raise ValueError('Wrong rc1 baseline')
 out.mkdir(parents=True,exist_ok=True);image=bytearray(base);changes=[];allowed=set();p,l=patches()
 def put(o,b,role):
  span=set(range(o,o+len(b)));assert not span&allowed;allowed.update(span);image[o:o+len(b)]=b
  changes.append(dict(offset=hex(o),bytes=len(b),role=role,before_sha256=sha(base[o:o+len(b)]),after_sha256=sha(b)))
 for a,b in p.items():put(off(a),b,'preview detail / CHROMA / label')
 put(0xbde9d,b'SBOY-B-1.1\0\0','distinct native update identity')
 diffs={i for i,(x,y) in enumerate(zip(base,image)) if x!=y};assert diffs<=allowed;assert len(image)==len(base)
 (out/'DestBin.bin').write_bytes(image)
 m=dict(version='СБОЙ КРАСНАЯ 1.0-rc2',native_update_identity='SBOY-B-1.1',sha256=sha(image),baseline_rc1_sha256=OLD_SHA,bytes=len(image),changed_bytes=len(diffs),changes=changes,status='offline candidate, not installed',preview='Only exact160x80 palette styles: 75% original per-pixel luma; fine +/-4 single-pixel texture in modes6/8/9; original2x2 UV geometry',saved_media='All rc1 modes except12 byte-equivalent algorithm for non160x80 frames;12 nowCHROMA',unmodified='LCD, UI timers, key handlers, CSI/JPEG/AVI/audio code and all their addresses')
 (out/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:m[k] for k in ('version','sha256','changed_bytes','status')},ensure_ascii=False,indent=2));return m
if __name__=='__main__':build()
