#!/usr/bin/env python3
"""Exact rc4 delta: ASCII character scale only, offline builder."""
import json,struct
from pathlib import Path
import red_port as r
from red_effects_rc5 import kernels
from build_red import ROOT,off,sha
OLD=ROOT/'custom-firmware/red/builds/sboy-red-1.0-rc4'
OUT=ROOT/'custom-firmware/red/builds/sboy-red-1.0-rc5'
OLD_SHA='30ce2bbb8fbd6d40316f389963476e9170100a9749f887b49813fe9435c8251b'
def patches():
 p=kernels(r.START,r.START+1160,r.START+1352,r.TICK)
 assert len(p[r.START])<=1160
 p[r.START]+=struct.pack('<I',0x15000000)*((1160-len(p[r.START]))//4)
 base=(OLD/'DestBin.bin').read_bytes()
 if len(base)!=0x100000 or sha(base)!=OLD_SHA:raise ValueError('Wrong red rc4 baseline')
 return {a:v for a,v in p.items() if base[off(a):off(a)+len(v)]!=v}
def build(out=OUT):
 base=(OLD/'DestBin.bin').read_bytes();p=patches();out.mkdir(parents=True,exist_ok=True);im=bytearray(base);allowed=set();changes=[]
 def put(o,data,role):
  span=set(range(o,o+len(data)));assert not span&allowed;allowed.update(span);im[o:o+len(data)]=data;changes.append(dict(offset=hex(o),bytes=len(data),role=role))
 for a,v in p.items():put(off(a),v,'half-size ASCII cells, preserved1x preview')
 put(0xbde9d,b'SBOY-B-1.4\0\0','distinct native update identity')
 diffs={i for i,(x,y) in enumerate(zip(base,im)) if x!=y};assert diffs<=allowed and len(im)==len(base)
 (out/'DestBin.bin').write_bytes(im)
 m=dict(version='СБОЙ КРАСНАЯ 1.0-rc5',sha256=sha(im),baseline_rc4_sha256=OLD_SHA,native_update_identity='SBOY-B-1.4',changed_bytes=len(diffs),changes=changes,status='offline candidate; hardware pending',ascii_cells={'width_up_to320':'4x8 unchanged','width321_to640':'8x16 ->4x8','width_above640':'16x32 ->8x16'},preserved='Other14 modes pixel-identical;15-mode menu, LCD/sensor/light/control/video code unchanged')
 (out/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n');print(json.dumps(m,ensure_ascii=False,indent=2));return m
if __name__=='__main__':build()
