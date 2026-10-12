#!/usr/bin/env python3
"""Guarded offline 0.5 build, preserving verified LCD and video pipeline."""
import io,json,struct
from PIL import Image
from build_v03 import ROOT,sha,off,screen
import effects_v05 as effects
import mode_cycle,mode_hook,date_video_patch
BASE_SHA='43f28bbcd158cead7a239213b6b14a03f48256e5631f4582ca36847725e1ded3'
OUT=ROOT/'custom-firmware/builds/sboy-0.5'
def patches():return {**effects.patches(),**mode_cycle.patches(12),**mode_hook.patches(12,master=True)}
def build():
    base=(ROOT/'custom-firmware/builds/sboy-0.4/DestBin.bin').read_bytes()
    assert len(base)==0x100000 and sha(base)==BASE_SHA
    assert struct.unpack_from('<I',base,off(0x2000ae8))[0]==0x04004e28
    # Native effect 8/9 direct entry references: only the dispatcher. No raw
    # function pointer references exist in the image for either entry.
    for target,expected in [(0x20520a8,[0x201851c]),(0x205278c,[0x201853c])]:
        calls=[]
        for offset in range(0x2400,0x88200,4):
            pc=offset-0x2400+0x2000000;w=struct.unpack_from('<I',base,offset)[0]
            imm=w&0x3ffffff;imm=imm-(1<<26) if imm&(1<<25) else imm
            if w>>26 in (0,1) and pc+4*imm==target:calls.append(pc)
        assert calls==expected,(hex(target),calls)
        assert struct.pack('<I',target) not in base
    OUT.mkdir(exist_ok=True);image=bytearray(base);allowed=set();changes=[]
    def put(offset,data,role):
        span=set(range(offset,offset+len(data)));assert not allowed&span,role
        allowed.update(span);image[offset:offset+len(data)]=data
        changes.append(dict(role=role,offset=hex(offset),bytes=len(data),before_sha256=sha(base[offset:offset+len(data)]),after_sha256=sha(data)))
    for a,b in patches().items():put(off(a),b,'six styles / contrast / live selector / clock startup')
    for rid,role in [(11,'startup'),(12,'shutdown')]:
        rel,n=struct.unpack_from('<II',base,0x8c200+8*rid);im=screen(role,version='0.5');im.save(OUT/(role+'.png'))
        buf=io.BytesIO();im.save(buf,'JPEG',quality=88,subsampling=2,progressive=False,optimize=False);data=buf.getvalue()
        assert len(data)<=n;check=Image.open(io.BytesIO(data));check.load();assert check.size==(160,80)
        (OUT/(role+'.jpg')).write_bytes(data);put(0x8c200+rel,data.ljust(n,b'\xff'),role+' version')
    assert base[0x8c030:0x8c038]==b'14:48:01';put(0x8c030,b'14:48:02','native update ID')
    for lo,hi in [(0,0x2400),(0x88484,0x8888c),(0x8c200,0x8c290),(0xc20bb,0xd0fa3),(off(0x2014388),off(0x20148a0)),(off(0x200084c),off(0x2000ac8)),(off(effects.END),off(0x2053100))]:assert base[lo:hi]==image[lo:hi]
    for a,b in date_video_patch.patches().items():assert image[off(a):off(a)+len(b)]==b
    diffs={i for i,(a,b) in enumerate(zip(base,image)) if a!=b};assert diffs<=allowed
    manifest=dict(version='СБОЙ 0.5',sha256=sha(image),baseline_sha256=BASE_SHA,bytes=len(image),changed_bytes=len(diffs),changes=changes,status='offline built, not installed',styles=list(effects.LABELS),presets=12,strength='I normal / II stronger luma contrast; cycle all six I then all six II with existing effect buttons',preview_selector=dict(x=32,y=18,width=96,height=16,frame=[160,80],persistent=True,saved_media=False),clock='call existing TIME.txt routine after native updater during app startup; TIME.txt fresh Moscow time staged separately',hardware_validation='pending: new effects, menu readability, clock, video throughput')
    (OUT/'DestBin.bin').write_bytes(image);(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:manifest[k] for k in ('version','sha256','bytes','changed_bytes','status')},ensure_ascii=False))
if __name__=='__main__':build()
