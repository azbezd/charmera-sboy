#!/usr/bin/env python3
"""Guarded offline 0.6 build, preserving verified LCD and video pipeline."""
import io,json,struct
from PIL import Image
from build_v03 import ROOT,sha,off,screen
import effects_v05 as effects
import mode_cycle,mode_hook,date_video_patch
import menu_v06
BASE_SHA='2e0bbbf6cc4efa06c1f7df77cb786c1b1ddf81d023007c1beff8c3a0fc238ad9'
OUT=ROOT/'custom-firmware/builds/sboy-0.6'
def patches():return menu_v06.patches()
def build():
    base=(ROOT/'custom-firmware/builds/sboy-0.5/DestBin.bin').read_bytes()
    assert len(base)==0x100000 and sha(base)==BASE_SHA
    for a,b in menu_v06.expected_original().items():assert base[off(a):off(a)+len(b)]==b,hex(a)
    OUT.mkdir(exist_ok=True);image=bytearray(base);allowed=set();changes=[]
    def put(offset,data,role):
        span=set(range(offset,offset+len(data)));assert not allowed&span,role
        allowed.update(span);image[offset:offset+len(data)]=data
        changes.append(dict(role=role,offset=hex(offset),bytes=len(data),before_sha256=sha(base[offset:offset+len(data)]),after_sha256=sha(data)))
    for a,b in patches().items():put(off(a),b,'transient menu / physical key directions')
    for rid,role in [(11,'startup'),(12,'shutdown')]:
        rel,n=struct.unpack_from('<II',base,0x8c200+8*rid);im=screen(role,version='0.6');im.save(OUT/(role+'.png'))
        buf=io.BytesIO();im.save(buf,'JPEG',quality=88,subsampling=2,progressive=False,optimize=False);data=buf.getvalue()
        assert len(data)<=n;check=Image.open(io.BytesIO(data));check.load();assert check.size==(160,80)
        (OUT/(role+'.jpg')).write_bytes(data);put(0x8c200+rel,data.ljust(n,b'\xff'),role+' version')
    assert base[0x8c030:0x8c038]==b'14:48:02';put(0x8c030,b'14:48:03','native update ID')
    for lo,hi in [(0,0x2400),(0x88484,0x8888c),(0x8c200,0x8c290),(0xc20bb,0xd0fa3),(off(0x2014388),off(0x20148a0)),(off(0x200084c),off(0x2000ac8)),(off(effects.END),off(0x2053100))]:assert base[lo:hi]==image[lo:hi]
    for a,b in date_video_patch.patches().items():assert image[off(a):off(a)+len(b)]==b
    diffs={i for i,(a,b) in enumerate(zip(base,image)) if a!=b};assert diffs<=allowed
    manifest=dict(version='СБОЙ 0.6',sha256=sha(image),baseline_sha256=BASE_SHA,bytes=len(image),changed_bytes=len(diffs),changes=changes,status='offline built, not installed',styles=list(effects.LABELS),presets=12,strength='I normal / II stronger luma contrast; cycle all six I then all six II with existing effect buttons',preview_selector=dict(x=32,y=18,width=96,height=16,frame=[160,80],persistent=False,timeout_ms=2000,hide_on_shutter=True,arrows="up/down",saved_media=False),clock='call existing TIME.txt routine after native updater during app startup; TIME.txt fresh Moscow time staged separately',hardware_validation='pending: native two-second timeout and shutter hiding on camera')
    (OUT/'DestBin.bin').write_bytes(image);(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:manifest[k] for k in ('version','sha256','bytes','changed_bytes','status')},ensure_ascii=False))
if __name__=='__main__':build()
