#!/usr/bin/env python3
"""Guarded offline 0.8 build, preserving verified LCD and video pipeline."""
import io,json,struct
from PIL import Image
from build_v03 import ROOT,sha,off,screen
import effects_v05 as effects
import mode_cycle,mode_hook,date_video_patch
import menu_v06
BASE_SHA='bd39dba3379bb3a8bdcc888510917bcf12226b8ec48cc2ed0d3614a4a1c1ac76'
OUT=ROOT/'custom-firmware/builds/sboy-0.8'
LABELS=('VHS','ЧЕРНИЛА','СОРТ','ПРИЗРАК','РАЗРЫВ','РАСТР')
def patches():
    p=effects.patches(paired=True,vhs=True)
    return {**{a:p[a] for a in (effects.MASTER,effects.NEW,effects.FINISH)},effects.DATA:menu_v06.menu_bits(LABELS,paired=True)}
def build():
    base=(ROOT/'custom-firmware/builds/sboy-0.7/DestBin.bin').read_bytes()
    assert len(base)==0x100000 and sha(base)==BASE_SHA
    OUT.mkdir(exist_ok=True);image=bytearray(base);allowed=set();changes=[]
    def put(offset,data,role):
        span=set(range(offset,offset+len(data)));assert not allowed&span,role
        allowed.update(span);image[offset:offset+len(data)]=data
        changes.append(dict(role=role,offset=hex(offset),bytes=len(data),before_sha256=sha(base[offset:offset+len(data)]),after_sha256=sha(data)))
    for a,b in patches().items():put(off(a),b,'paired styles with VHS first')
    for rid,role in [(11,'startup'),(12,'shutdown')]:
        rel,n=struct.unpack_from('<II',base,0x8c200+8*rid);im=screen(role,version='0.8');im.save(OUT/(role+'.png'))
        buf=io.BytesIO();im.save(buf,'JPEG',quality=88,subsampling=2,progressive=False,optimize=False);data=buf.getvalue()
        assert len(data)<=n;check=Image.open(io.BytesIO(data));check.load();assert check.size==(160,80)
        (OUT/(role+'.jpg')).write_bytes(data);put(0x8c200+rel,data.ljust(n,b'\xff'),role+' version')
    assert base[0x8c030:0x8c038]==b'14:48:04';put(0x8c030,b'14:48:05','native update ID')
    for lo,hi in [(0,0x2400),(0x88484,0x8888c),(0x8c200,0x8c290),(0xc20bb,0xd0fa3),(off(0x2014388),off(0x20148a0)),(off(0x200084c),off(0x2000ac8)),(off(effects.END),off(0x2053100))]:assert base[lo:hi]==image[lo:hi]
    for a,b in date_video_patch.patches().items():assert image[off(a):off(a)+len(b)]==b
    diffs={i for i,(a,b) in enumerate(zip(base,image)) if a!=b};assert diffs<=allowed
    manifest=dict(version='СБОЙ 0.8',sha256=sha(image),baseline_sha256=BASE_SHA,bytes=len(image),changed_bytes=len(diffs),changes=changes,status='offline built, not installed',styles=list(LABELS),presets=12,strength='I normal / II stronger luma contrast; each style I immediately followed by II; VHS first with existing effect buttons',preview_selector=dict(x=32,y=18,width=96,height=16,frame=[160,80],persistent=False,timeout_ms=2000,hide_on_shutter=True,arrows="up/down",saved_media=False),clock='call existing TIME.txt routine after native updater during app startup; TIME.txt fresh Moscow time staged separately',hardware_validation='pending: VHS appearance and video cadence; prior RGB/BGR correction not yet physically confirmed')
    (OUT/'DestBin.bin').write_bytes(image);(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:manifest[k] for k in ('version','sha256','bytes','changed_bytes','status')},ensure_ascii=False))
if __name__=='__main__':build()
