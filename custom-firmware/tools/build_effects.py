#!/usr/bin/env python3
"""Guarded offline first-camera CHARM//BREACH 0.2 experimental build."""
import hashlib,io,json,struct
from pathlib import Path
from PIL import Image
from effect_kernel import kernel, SLOTS, END
from mode_hook import patches as mode_patches, SETTER, ORIGINAL_WORD
from build_identity import splash

ROOT=Path(__file__).resolve().parents[2]
BASE_SHA='62273b3990a3562334ba8c01f0e4da8243749849ce3fd839c9f77205428ac84d'

def sha(b):return hashlib.sha256(b).hexdigest()
def offset(addr):return addr-0x02000000+0x2400

def audit_inbound(base):
    """Reject direct branches into the middle of a replaced native routine.

Direct calls to its entry are the inspected native effect dispatcher. This
check cannot prove the absence of dynamically computed targets.
"""
    spans=((SLOTS[0],SLOTS[1]),(SLOTS[1],SLOTS[2]),(SLOTS[2],END))
    expected={SLOTS[0]:0x020184bc,SLOTS[1]:0x020184dc,SLOTS[2]:0x020184fc}
    found=[]
    code=base[0x2400:0x88200]
    for pos in range(0,len(code),4):
        w=struct.unpack_from('<I',code,pos)[0];op=w>>26
        if op not in (0,1,3,4):continue
        pc=0x02000000+pos;disp=w&0x3ffffff
        if disp&0x2000000:disp-=0x4000000
        target=pc+disp*4
        for lo,hi in spans:
            if lo<=target<hi and not lo<=pc<hi:
                if target!=lo or pc!=expected[lo] or op!=1:
                    raise ValueError('Unexpected inbound branch %#x -> %#x'%(pc,target))
                found.append((pc,target))
    if len(found)!=3:raise ValueError('Native entry call count changed')
    # No literal pointers to function interiors in image outside their code.
    for lo,hi in spans:
        for pos in range(0,len(base)-3,4):
            value=struct.unpack_from('<I',base,pos)[0]
            if lo<value<hi and not offset(lo)<=pos<offset(hi):
                raise ValueError('Potential interior pointer %#x at %#x'%(value,pos))
    return found

def build():
    base=(ROOT/'custom-firmware/builds/charm-breach-0.1-identity/DestBin.bin').read_bytes()
    if len(base)!=0x100000 or sha(base)!=BASE_SHA:raise ValueError('Wrong first-camera identity baseline')
    if struct.unpack_from('<I',base,offset(SETTER))[0]!=ORIGINAL_WORD:raise ValueError('Native setter prologue changed')
    calls=audit_inbound(base)
    patches={**kernel(),**mode_patches()};image=bytearray(base);allowed={0x8c037};report=[]
    for addr,payload in sorted(patches.items()):
        off=offset(addr);span=set(range(off,off+len(payload)))
        if span&allowed:raise ValueError('Patches overlap')
        allowed.update(span);image[off:off+len(payload)]=payload
        report.append({'ram_address':hex(addr),'file_offset':hex(off),'bytes':len(payload),'before_sha256':sha(base[off:off+len(payload)]),'after_sha256':sha(payload)})
    out=ROOT/'custom-firmware/builds/charm-breach-0.2-effects';out.mkdir(exist_ok=True)
    for rid,label,shutdown in [(11,'startup',False),(12,'shutdown',True)]:
        rel,n=struct.unpack_from('<II',base,0x8c200+rid*8);off=0x8c200+rel
        im=splash(shutdown,'0.2');stream=io.BytesIO();im.save(stream,'JPEG',quality=88,subsampling=2,progressive=False,optimize=False)
        payload=stream.getvalue()
        if len(payload)>n:raise ValueError('Splash allocation overflow')
        image[off:off+n]=payload.ljust(n,b'\xff');allowed.update(range(off,off+n))
        im.save(out/(label+'.png'))
        decoded=Image.open(io.BytesIO(payload));decoded.load()
        if decoded.size!=(160,80):raise ValueError('JPEG geometry changed')
    if base[0x8c030:0x8c039]!=b'14:47:56\0':raise ValueError('Update identity changed')
    image[0x8c037]=ord('7')
    changes=[i for i,(a,b) in enumerate(zip(base,image)) if a!=b]
    if not set(changes)<=allowed:raise ValueError('Unexpected change')
    for lo,hi in [(0,0x2400),(0x88484,0x8888c),(0x8c200,0x8c290),(0xf1659,0xf4cc7)]:
        if image[lo:hi]!=base[lo:hi]:raise ValueError('Protected boot/LCD/directory/USB range changed')
    manifest={'name':'CHARM//BREACH','version':'0.2 experimental effects','baseline_sha256':BASE_SHA,'sha256':sha(image),'bytes':len(image),'changed_bytes':len(changes),'patches':report,'native_effect_calls':[[hex(x),hex(y)] for x,y in calls],
      'mode_slots':{'0':'native normal','1':'INK','2':'TEAR','3':'GHOST','4':'native color 4','5':'native color 5'},
      'boot_header_and_bootstrap_unchanged':True,'lcd_v3_unchanged':True,'usb_code_unchanged':True,'updater_unchanged':True,
      'status':'offline built; NOT installed or hardware tested','known_limits':['Hardware frame rate and chroma ordering unverified','Existing still-review timing unchanged','Video uses the native effect path; throughput and audio synchronisation require actual recording','Native UI color icons/labels unchanged','Frame overlays not yet tested together with new effects']}
    (out/'DestBin.bin').write_bytes(image);(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest,indent=2))

if __name__=='__main__':build()
