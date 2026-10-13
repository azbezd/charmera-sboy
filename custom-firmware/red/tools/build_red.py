#!/usr/bin/env python3
"""Offline exact-base red B candidate builder. Never stages or writes a camera."""
import hashlib,json,struct,sys
from pathlib import Path
from red_port import build_patches,START,END
from red_resources import resources
ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'camera-dumps/20261012T234128-second-camera/spi-flash-1MiB.bin'
OUT=ROOT/'custom-firmware/red/builds/sboy-red-1.0-rc1'
BASE_SHA='3a6fa4735a7bb5a6f302a011ca8332d11121d64a930404533eedd59cb3eb6c2b'
def sha(b):return hashlib.sha256(b).hexdigest()
def off(a):return a-0x2000000+0x2400

def build(base_path=BASE,out=OUT):
 base=Path(base_path).read_bytes()
 if len(base)!=0x100000 or sha(base)!=BASE_SHA:raise ValueError('Requires exact factory RED B image; rejects yellow and modified images')
 out.mkdir(parents=True,exist_ok=True);image=bytearray(base);allowed=set();changes=[]
 def put(o,data,role):
  span=set(range(o,o+len(data)))
  assert 0<=o<=o+len(data)<=len(base) and not allowed&span,role
  allowed.update(span);image[o:o+len(data)]=data
  changes.append(dict(offset=hex(o),bytes=len(data),role=role,before_sha256=sha(base[o:o+len(data)]),after_sha256=sha(data)))
 p,roles,layout=build_patches()
 for a,b in p.items():put(off(a),b,roles[a])
 for o,(b,role) in resources(base,out).items():put(o,b,role)
 put(0xbde9d,b'SBOY-B-1.0\0\0','red-only native updater identity')
 # UI colors only; original erase/program/verify instructions unchanged.
 for a,old,new,reg in ((0x20129b4,246,250,4),(0x20129e4,252,240,4),(0x20129f8,241,250,4),(0x2012a2c,252,240,6),(0x2012a70,252,240,6)):
  word=0x27<<26|reg<<21|old
  assert struct.unpack_from('<I',base,off(a))[0]==word
  put(off(a),struct.pack('<I',0x27<<26|reg<<21|new),'updater display color')
 for lo,hi in ((0,0x2400),(0x78c00,0x7f890),(0x95288,0x95474)):
  assert image[lo:hi]==base[lo:hi],('protected bootstrap, LCD/sensor/config or directory',hex(lo))
 assert len(image)==len(base)
 diffs={i for i,(x,y) in enumerate(zip(base,image)) if x!=y};assert diffs<=allowed
 (out/'DestBin.bin').write_bytes(image)
 manifest=dict(version='СБОЙ КРАСНАЯ 1.0-rc1',baseline_sha256=BASE_SHA,sha256=sha(image),bytes=len(image),changed_bytes=len(diffs),changes=changes,layout={k:hex(v) for k,v in layout.items()},status='OFFLINE EXPERIMENTAL CANDIDATE; not installed or hardware validated',video='RAM-fed CPU effects with deferred frame IRQ, native AVI/audio writer; hardware test required',lcd='exact original red B JD9850 configuration',menu='12 distinct styles; up/down; timeout 2000ms; hide at photo entry')
 (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:manifest[k] for k in ('version','sha256','changed_bytes','status')},ensure_ascii=False,indent=2));return manifest
if __name__=='__main__':build()
