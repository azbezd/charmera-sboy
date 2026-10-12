#!/usr/bin/env python3
"""Restore light-status icons; preserve original photo/video light behavior."""
import io,json,struct
from PIL import Image,ImageDraw
from build_v03 import ROOT,sha,off,screen
BASE_SHA='be9bcef13eb48d5feca12bc37604abe9a8593ccd08efa115c4a5f0f074d39d48'
OUT=ROOT/'custom-firmware/builds/sboy-0.9'
def light_icon(w,h,on):
    if (w,h)!=(16,16):raise ValueError('Unexpected light icon dimensions')
    im=Image.new('L',(w,h),0);d=ImageDraw.Draw(im)
    bolt=[(8,1),(3,9),(7,9),(6,14),(13,5),(9,5),(11,1)]
    if on:d.polygon(bolt,fill=251)
    else:
        d.polygon(bolt,outline=251)
        d.line((2,2,13,13),fill=0,width=3)
        d.line((2,2,13,13),fill=251,width=1)
    return im

def build():
    base=(ROOT/'custom-firmware/builds/sboy-0.8/DestBin.bin').read_bytes()
    if len(base)!=0x100000 or sha(base)!=BASE_SHA:raise ValueError('Wrong 0.8 baseline')
    OUT.mkdir(exist_ok=True);out=bytearray(base);allowed=set();changes=[]
    def put(offset,data,role):
        span=set(range(offset,offset+len(data)))
        if allowed&span:raise ValueError('Overlapping writes')
        allowed.update(span);out[offset:offset+len(data)]=data
        changes.append(dict(role=role,offset=hex(offset),bytes=len(data)))
    for rid,on in [(20,False),(21,True)]:
        w,h,rel=struct.unpack_from('<III',base,0xc20bb+rid*12)
        im=light_icon(w,h,on);put(0xc20bb+rel,im.tobytes(),'light on' if on else 'light off')
        rgb=Image.new('RGB',(w,h));rgb.putdata([(242,241,225) if v else (0,0,0) for v in im.tobytes()]);rgb.resize((128,128),Image.Resampling.NEAREST).save(OUT/('light-on.png' if on else 'light-off.png'))
    for rid,role in [(11,'startup'),(12,'shutdown')]:
        rel,n=struct.unpack_from('<II',base,0x8c200+8*rid);im=screen(role,version='0.9');buf=io.BytesIO()
        im.save(buf,'JPEG',quality=88,subsampling=2,progressive=False,optimize=False);data=buf.getvalue()
        if len(data)>n:raise ValueError('Resource overflow')
        put(0x8c200+rel,data.ljust(n,b'\xff'),role+' version')
    if base[0x8c030:0x8c038]!=b'14:48:05':raise ValueError('Unexpected update ID')
    put(0x8c030,b'14:48:06','native update ID')
    if out[:0x88200]!=base[:0x88200]:raise ValueError('Executable code changed')
    if out[0x88484:0x8888c]!=base[0x88484:0x8888c]:raise ValueError('LCD table changed')
    if any(i not in allowed for i,(a,b) in enumerate(zip(base,out)) if a!=b):raise ValueError('Unexpected difference')
    (OUT/'DestBin.bin').write_bytes(out)
    report=dict(version='СБОЙ 0.9',sha256=sha(out),baseline_sha256=BASE_SHA,changes=changes,executable_code_unchanged=True,light_behavior='Original manual continuous light toggled by long DOWN in photo/video; native setting and callbacks preserved',light_hardware='Owner confirmed white continuous light on long DOWN, before 0.9',status='offline built; not installed')
    (OUT/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':build()
