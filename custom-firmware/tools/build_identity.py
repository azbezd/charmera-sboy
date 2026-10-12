#!/usr/bin/env python3
"""Deterministic pixel typography and guarded native JPEG-resource update.

Run with the bundled Python (Pillow). Offline: never touches USB or the SD.
"""
from pathlib import Path
import hashlib, io, json, struct
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
BASE_SHA = '3ce337e9c67310770a4f0dcea722902e0d40f27301830d6eae256350a0cde644'
FONT = {
 'A':'01110/10001/10001/11111/10001/10001/10001',
 'B':'11110/10001/10001/11110/10001/10001/11110',
 'C':'01111/10000/10000/10000/10000/10000/01111',
 'D':'11110/10001/10001/10001/10001/10001/11110',
 'E':'11111/10000/10000/11110/10000/10000/11111',
 'F':'11111/10000/10000/11110/10000/10000/10000',
 'G':'01111/10000/10000/10111/10001/10001/01111',
 'H':'10001/10001/10001/11111/10001/10001/10001',
 'I':'111/010/010/010/010/010/111',
 'K':'10001/10010/10100/11000/10100/10010/10001',
 'L':'10000/10000/10000/10000/10000/10000/11111',
 'M':'10001/11011/10101/10101/10001/10001/10001',
 'N':'10001/11001/10101/10011/10001/10001/10001',
 'O':'01110/10001/10001/10001/10001/10001/01110',
 'P':'11110/10001/10001/11110/10000/10000/10000',
 'R':'11110/10001/10001/11110/10100/10010/10001',
 'S':'01111/10000/10000/01110/00001/00001/11110',
 'T':'11111/00100/00100/00100/00100/00100/00100',
 'U':'10001/10001/10001/10001/10001/10001/01110',
 'V':'10001/10001/10001/10001/10001/01010/00100',
 'W':'10001/10001/10001/10101/10101/11011/10001',
 'X':'10001/10001/01010/00100/01010/10001/10001',
 'Y':'10001/10001/01010/00100/00100/00100/00100',
 '0':'01110/10001/10011/10101/11001/10001/01110',
 '1':'010/110/010/010/010/010/111',
 '2':'11110/00001/00001/01110/10000/10000/11111',
 '.':'0/0/0/0/0/0/1', '/':'00001/00001/00010/00100/01000/10000/10000',
 ' ':'000/000/000/000/000/000/000', '-':'000/000/000/111/000/000/000',
}

def text_width(text, scale=1):
    return (sum(len(FONT[c].split('/')[0])+1 for c in text)-1)*scale

def text(im, pos, value, color, scale=1):
    d=ImageDraw.Draw(im);x,y=pos
    for c in value:
        rows=FONT[c].split('/')
        for yy,row in enumerate(rows):
            for xx,v in enumerate(row):
                if v=='1':d.rectangle((x+xx*scale,y+yy*scale,x+(xx+1)*scale-1,y+(yy+1)*scale-1),fill=color)
        x+=(len(rows[0])+1)*scale

def splash(shutdown=False, version="0.1"):
    bg=(8,9,15);fg=(244,241,225);acid=(217,255,79);pink=(255,65,121)
    im=Image.new('RGB',(160,80),bg);d=ImageDraw.Draw(im)
    text(im,(8,7),'CHARM//',acid)
    text(im,(116,7),'V'+version,fg)
    # A readable six-letter word, sliced along two scanlines at native pixels.
    word=Image.new('RGB',(160,22),bg)
    text(word,(8,3),'BREACH',fg,3)
    im.paste(word,(0,20))
    im.paste(word.crop((0,8,156,10)),(4,28))
    im.paste(word.crop((4,17,160,18)),(0,37))
    d=ImageDraw.Draw(im)
    d.rectangle((6,29,15,30),fill=pink);d.rectangle((137,38,151,39),fill=acid)
    text(im,(8,51),'SIGNAL LOST' if shutdown else 'REALITY UNLOCKED',fg)
    d.line((8,65,151,65),fill=(56,62,69))
    for x,w,c in ((8,44,pink if shutdown else acid),(56,17,fg),(78,6,acid),(88,3,pink)):
        d.rectangle((x,65,x+w,66),fill=c)
    text(im,(8,71),'OFFLINE' if shutdown else 'SENSOR ONLINE',pink if shutdown else acid)
    return im

def sha(b):return hashlib.sha256(b).hexdigest()

def usb_screen():
    im=Image.new('RGB',(160,80),(8,9,15));d=ImageDraw.Draw(im)
    text(im,(8,7),'CHARM//BREACH', (217,255,79))
    text(im,(8,25),'USB LINK',(244,241,225),2)
    d.line((8,45,151,45),fill=(56,62,69));d.rectangle((8,45,56,46),fill=(217,255,79))
    text(im,(8,54),'STORAGE MODE',(244,241,225))
    text(im,(8,69),'UNPLUG TO SHOOT',(217,255,79))
    # Match the stock resource dimensions; the existing renderer scales it
    # to this particular LCD. Preserve native slot rather than altering code.
    return im.resize((320,240),Image.Resampling.NEAREST)

def build():
    base=(ROOT/'firmware/st7735-v3/DestBin.bin').read_bytes()
    if len(base)!=0x100000 or sha(base)!=BASE_SHA:raise ValueError('Wrong verified v3 baseline')
    art=ROOT/'custom-firmware/artwork';art.mkdir(exist_ok=True)
    out=ROOT/'custom-firmware/builds/charm-breach-0.1-identity';out.mkdir(exist_ok=True)
    image=bytearray(base);allowed={0x8c037};resources=[]
    for rid,label,shut,expected_off,capacity in [(11,'startup',False,0xd0fa3,0x1ae8),(12,'shutdown',True,0xd2a8b,0x1cc2),(16,'usb',False,0xf1659,0x366e)]:
        rel,n=struct.unpack_from('<II',base,0x8c200+rid*8);off=0x8c200+rel
        if (off,n)!=(expected_off,capacity):raise ValueError('Resource layout changed')
        old=Image.open(io.BytesIO(base[off:off+n]));old.load()
        dimensions=(320,240) if rid==16 else (160,80)
        if old.size!=dimensions:raise ValueError('Unexpected stock resource size')
        im=usb_screen() if rid==16 else splash(shut);im.save(art/(label+'.png'))
        stream=io.BytesIO();im.save(stream,'JPEG',quality=75 if rid==16 else 88,subsampling=2,progressive=False,optimize=False)
        payload=stream.getvalue()
        if len(payload)>capacity:raise ValueError('JPEG exceeds existing allocation')
        # Keep resource table and every following offset intact. The native
        # JPEG decoder consumes EOI; unused bytes remain FF inside old slot.
        image[off:off+n]=payload.ljust(n,b'\xff')
        allowed.update(range(off,off+n))
        (art/(label+'.jpg')).write_bytes(payload)
        resources.append({'id':rid,'role':label,'offset':hex(off),'capacity':n,'jpeg_bytes':len(payload),'sha256':sha(payload)})
    if base[0x8c030:0x8c039]!=b'14:47:55\0':raise ValueError('Unexpected update ID')
    image[0x8c037]=ord('6')
    changed=[i for i,(a,b) in enumerate(zip(base,image)) if a!=b]
    if any(i not in allowed for i in changed):raise ValueError('Unapproved difference')
    assert image[:0x88200]==base[:0x88200]  # all boot and application code
    assert image[0x88484:0x8888c]==base[0x88484:0x8888c]  # working LCD
    assert image[0x8c200:0x8c290]==base[0x8c200:0x8c290]  # entire resource directory
    report={'name':'CHARM//BREACH','version':'0.1 identity','baseline_sha256':BASE_SHA,'sha256':sha(image),'bytes':len(image),'changed_bytes':len(changed),'resources':resources,'program_code_unchanged':True,'lcd_v3_unchanged':True,'effect_algorithms_included':False,'installation':'not staged','user_visible_text':{'startup':['CHARM//BREACH V0.1','REALITY UNLOCKED','SENSOR ONLINE'],'shutdown':['CHARM//BREACH V0.1','SIGNAL LOST','OFFLINE']}}
    (out/'DestBin.bin').write_bytes(image);(out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    sheet=Image.new('RGB',(984,180),(17,18,22))
    for i,label in enumerate(('startup','shutdown','usb')):
        decoded=Image.open(art/(label+'.jpg'))
        sheet.paste(decoded.resize((320,160),Image.Resampling.NEAREST),(8+i*328,10))
    sheet.save(art/'identity-preview.png')
    print(json.dumps(report,indent=2))

if __name__=='__main__':build()
