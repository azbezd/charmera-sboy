#!/usr/bin/env python3
"""Guarded offline 0.7 build, preserving verified LCD and video pipeline."""
import io,json,struct
from PIL import Image
from build_v03 import ROOT,sha,off,screen
import effects_v05 as effects
import mode_cycle,mode_hook,date_video_patch
import menu_v06
BASE_SHA='37caa8d5618e790b26c6100954685cbbfee1ce160f07a6ee63ef996c560b5342'
OUT=ROOT/'custom-firmware/builds/sboy-0.7'
LABELS=effects.LABELS[:-1]+('ЭХО',)
def patches():return {effects.NEW:effects.patches(echo=True)[effects.NEW],effects.DATA:menu_v06.menu_bits(LABELS)}
def build():
    base=(ROOT/'custom-firmware/builds/sboy-0.6/DestBin.bin').read_bytes()
    assert len(base)==0x100000 and sha(base)==BASE_SHA
    for a,b in menu_v06.patches().items():assert base[off(a):off(a)+len(b)]==b,hex(a)
    OUT.mkdir(exist_ok=True);image=bytearray(base);allowed=set();changes=[]
    def put(offset,data,role):
        span=set(range(offset,offset+len(data)));assert not allowed&span,role
        allowed.update(span);image[offset:offset+len(data)]=data
        changes.append(dict(role=role,offset=hex(offset),bytes=len(data),before_sha256=sha(base[offset:offset+len(data)]),after_sha256=sha(data)))
    for a,b in patches().items():put(off(a),b,'replace NEON with ECHO in both contrast presets')
    for rid,role in [(11,'startup'),(12,'shutdown')]:
        rel,n=struct.unpack_from('<II',base,0x8c200+8*rid);im=screen(role,version='0.7');im.save(OUT/(role+'.png'))
        buf=io.BytesIO();im.save(buf,'JPEG',quality=88,subsampling=2,progressive=False,optimize=False);data=buf.getvalue()
        assert len(data)<=n;check=Image.open(io.BytesIO(data));check.load();assert check.size==(160,80)
        (OUT/(role+'.jpg')).write_bytes(data);put(0x8c200+rel,data.ljust(n,b'\xff'),role+' version')
    assert base[0x8c030:0x8c038]==b'14:48:03';put(0x8c030,b'14:48:04','native update ID')
    # MADCTL D3 selects RGB/BGR, independently from inversion and geometry.
    init=base[0x88484:0x8888c];rows=list(struct.iter_unpack('<II',init))
    hits=[i for i,r in enumerate(rows[:-1]) if r==(2,0x36) and rows[i+1]==(2,0x100)]
    assert len(hits)==1
    color_offset=0x88484+(hits[0]+1)*8+4
    put(color_offset,struct.pack('<I',0x108),'LCD RGB/BGR selector only: MADCTL 00 -> 08')
    assert sum(a!=b for a,b in zip(init,image[0x88484:0x8888c]))==1
    for lo,hi in [(0,0x2400),(0x8c200,0x8c290),(0xc20bb,0xd0fa3),(off(0x2014388),off(0x20148a0)),(off(0x200084c),off(0x2000ac8)),(off(effects.END),off(0x2053100))]:assert base[lo:hi]==image[lo:hi]
    for a,b in date_video_patch.patches().items():assert image[off(a):off(a)+len(b)]==b
    diffs={i for i,(a,b) in enumerate(zip(base,image)) if a!=b};assert diffs<=allowed
    manifest=dict(version='СБОЙ 0.7',sha256=sha(image),baseline_sha256=BASE_SHA,bytes=len(image),changed_bytes=len(diffs),changes=changes,status='offline built, not installed',styles=list(LABELS),presets=12,strength='I normal / II stronger luma contrast; cycle all six I then all six II with existing effect buttons',display_color='MADCTL D3 set: 00->08; original photos look natural on Mac but blue on LCD; physical validation pending',preview_selector=dict(x=32,y=18,width=96,height=16,frame=[160,80],persistent=False,timeout_ms=2000,hide_on_shutter=True,arrows="up/down",saved_media=False),clock='call existing TIME.txt routine after native updater during app startup; TIME.txt fresh Moscow time staged separately',hardware_validation='pending: RGB/BGR correction on actual LCD and ECHO aesthetic/performance')
    (OUT/'DestBin.bin').write_bytes(image);(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:manifest[k] for k in ('version','sha256','bytes','changed_bytes','status')},ensure_ascii=False))
if __name__=='__main__':build()
