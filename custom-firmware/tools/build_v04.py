#!/usr/bin/env python3
"""Offline guarded 0.4 build from the fully readback-verified first-camera 0.3."""
import io,json,struct
from PIL import Image
from build_v03 import ROOT,sha,off,screen
from sort_kernel import sorter
from preview_badge import badge
from mode_cycle import patches,expected_original
import date_video_patch as video
BASE_SHA='edb5dee1d9dc5589a6235072e87430b7fe97d5a4a86f8bf221e8e8a02c368440'
OUT=ROOT/'custom-firmware/builds/sboy-0.4'
def build():
    base=(ROOT/'custom-firmware/builds/sboy-0.3/DestBin.bin').read_bytes()
    assert len(base)==0x100000 and sha(base)==BASE_SHA,'Wrong verified baseline'
    OUT.mkdir(exist_ok=True);image=bytearray(base);allowed=set();changes=[]
    def put(offset,data,role):
        span=set(range(offset,offset+len(data)));assert not allowed&span,role
        allowed.update(span);image[offset:offset+len(data)]=data
        changes.append(dict(role=role,offset=hex(offset),bytes=len(data),before_sha256=sha(base[offset:offset+len(data)]),after_sha256=sha(data)))
    for a,b in {**expected_original(),**video.expected_original()}.items():assert base[off(a):off(a)+len(b)]==b,hex(a)
    for a,b in {**sorter(live=True),**badge(top=18),**patches(),**video.patches()}.items():put(off(a),b,'live effects, top caption, three-mode cycle')
    for rid,role in [(11,'startup'),(12,'shutdown')]:
        rel,n=struct.unpack_from('<II',base,0x8c200+8*rid);im=screen(role,version='0.4');im.save(OUT/(role+'.png'))
        buf=io.BytesIO();im.save(buf,'JPEG',quality=88,subsampling=2,progressive=False,optimize=False);data=buf.getvalue()
        assert len(data)<=n;check=Image.open(io.BytesIO(data));check.load();assert check.size==(160,80)
        (OUT/(role+'.jpg')).write_bytes(data);put(0x8c200+rel,data.ljust(n,b'\xff'),role+' version')
    assert base[0x8c030:0x8c038]==b'14:48:00';put(0x8c030,b'14:48:01','native update ID')
    for lo,hi in [(0,0x2400),(0x88484,0x8888c),(0x8c200,0x8c290),(0xc20bb,0xc2343),(off(0x2014388),off(0x20148a0))]:assert base[lo:hi]==image[lo:hi]
    diffs={i for i,(a,b) in enumerate(zip(base,image)) if a!=b};assert diffs<=allowed
    manifest=dict(version='СБОЙ 0.4',sha256=sha(image),baseline_sha256=BASE_SHA,bytes=len(image),changed_bytes=len(diffs),changes=changes,status='offline built, not installed',modes=['ЧЕРНИЛА','СОРТ','ПРИЗРАК'],default_mode='ЧЕРНИЛА',preview_caption=dict(x=56,y=18,width=48,height=10,frame=[160,80]),sorting='true block sorting in live preview/video source through width640 (32px windows) and larger photos (256px windows), wider luma range 24..232; preserves paired YUV blocks',date_display='YYYY/MM/DD only; RTC still maintains full time',video='native buffered path; defer processing out of capture interrupt, apply current effect before timestamp/JPEG, retain native audio writer',hardware_validation='pending; video effects, throughput, audio synchronization and overlay placement require camera observation')
    (OUT/'DestBin.bin').write_bytes(image);(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:manifest[k] for k in ('version','sha256','bytes','changed_bytes','status')},ensure_ascii=False))
if __name__=='__main__':build()
