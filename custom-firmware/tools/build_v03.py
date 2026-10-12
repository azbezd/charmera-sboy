#!/usr/bin/env python3
"""First-camera 0.3: Russian resources, readable icons, bounded pixel sorting."""
import io,json,hashlib,struct
from pathlib import Path
from PIL import Image,ImageDraw
from ru_pixels import centered
from effect_kernel import Asm
from sort_kernel import sorter
from preview_badge import badge
ROOT=Path(__file__).resolve().parents[2]
BASE_SHA='d8ae47e1ffec88e711918cae5955b9249924836334f3b9b11bceb5635ee04faf'
OUT=ROOT/'custom-firmware/builds/sboy-0.3'
YELLOW=(255,219,64);WHITE=(242,241,225);BG=(0,0,0)
def sha(b):return hashlib.sha256(b).hexdigest()
def off(a):return a-0x02000000+0x2400

def screen(role,version="0.3"):
    im=Image.new('RGB',(160,80),BG)
    title='СВЯЗЬ С ПК' if role=='usb' else 'СБОЙ '+version
    centered(im,24,title,WHITE,2)
    # One thin displaced scanline; keep every small letter readable.
    strip=im.crop((14,30,145,31));im.paste(BG,(14,30,145,31));im.paste(strip,(16,30))
    d=ImageDraw.Draw(im);d.rectangle((68,16,91,17),fill=YELLOW)
    if role=='startup':centered(im,47,'КАМЕРА СВОБОДНА',YELLOW)
    elif role=='shutdown':centered(im,47,'ДО СЛЕДУЮЩЕГО СБОЯ',YELLOW)
    else:
        centered(im,46,'КАРТА ДОСТУПНА',YELLOW)
        centered(im,59,'ОТСОЕДИНИ ДЛЯ СЪЁМКИ',WHITE)
    return im

def icon(rid,w,h):
    im=Image.new('L',(w,h),0);d=ImageDraw.Draw(im)
    white,red,yellow=251,252,240
    if rid in (19,20,21):return im  # no unsupported flash status
    if rid==25:  # still camera, lens + shutter shoulder
        d.rounded_rectangle((1,4,14,13),radius=2,outline=white,width=1)
        d.rectangle((4,2,8,4),fill=white);d.ellipse((5,6,10,11),outline=white);d.point((12,6),fill=yellow)
    elif rid==37:
        d.rounded_rectangle((1,4,10,12),radius=1,outline=white)
        d.polygon([(11,7),(14,4),(14,12),(11,10)],outline=white)
        d.rectangle((3,6,5,8),fill=red)
    elif rid in (4,45,50):
        d.polygon([(3,1),(10,1),(13,4),(13,14),(2,14),(2,2)],outline=white)
        for x in (5,7,9):d.line((x,3,x,5),fill=white)
        if rid==50:
            d.line((5,8,10,12),fill=red,width=2);d.line((10,8,5,12),fill=red,width=2)
        else:d.line([(4,10),(6,12),(11,7)],fill=yellow,width=2)
    else:raise ValueError('Unexpected icon')
    return im

def build():
    base=(ROOT/'custom-firmware/builds/charm-breach-0.2-effects/DestBin.bin').read_bytes()
    if len(base)!=0x100000 or sha(base)!=BASE_SHA:raise ValueError('Wrong verified 0.2 baseline')
    OUT.mkdir(exist_ok=True);image=bytearray(base);allowed=set();changes=[]
    def put(offset,payload,role):
        span=set(range(offset,offset+len(payload)))
        if allowed&span:raise ValueError('Overlapping writes: '+role)
        allowed.update(span);image[offset:offset+len(payload)]=payload
        changes.append({'role':role,'offset':hex(offset),'bytes':len(payload),'before_sha256':sha(base[offset:offset+len(payload)]),'after_sha256':sha(payload)})
    for addr,data in sorted({**sorter(),**badge()}.items()):put(off(addr),data,'effect executable / preview caption')
    for rid,role in [(11,'startup'),(12,'shutdown'),(16,'usb')]:
        rel,n=struct.unpack_from('<II',base,0x8c200+8*rid);offset=0x8c200+rel
        im=screen(role);im.save(OUT/(role+'.png'))
        if rid==16:im=im.resize((320,240),Image.Resampling.NEAREST)
        buf=io.BytesIO();im.save(buf,'JPEG',quality=85 if rid==16 else 88,subsampling=2,progressive=False,optimize=False)
        data=buf.getvalue()
        if len(data)>n:raise ValueError('JPEG slot overflow: '+role)
        decoded=Image.open(io.BytesIO(data));decoded.load()
        if decoded.size!=im.size:raise ValueError('JPEG geometry mismatch')
        (OUT/(role+'.jpg')).write_bytes(data);put(offset,data.ljust(n,b'\xff'),'Russian '+role)
    # OSD palette uses BGR565 on this panel: stock 0x001f is observed red.
    # Reserved index 240 becomes yellow (B+G in conventional RGB565).
    p=0xd07a3+240*4
    if base[p:p+4]!=bytes(4):raise ValueError('Reserved OSD palette slot not blank')
    put(p,struct.pack('<HH',0x07ff,31),'yellow OSD color (BGR565)')
    iconids=(4,19,20,21,25,37,45,50)
    atlas=Image.new('RGB',(len(iconids)*80,92),(30,30,30));draw=ImageDraw.Draw(atlas)
    for j,rid in enumerate(iconids):
        w,h,rel=struct.unpack_from('<III',base,0xc20bb+rid*12)
        im=icon(rid,w,h);put(0xc20bb+rel,im.tobytes(),'native icon '+str(rid))
        rgb=Image.new('RGB',(w,h),(30,30,30));rgb.putdata([{0:(30,30,30),251:WHITE,252:(255,70,65),240:YELLOW}[v] for v in im.tobytes()])
        atlas.paste(rgb.resize((w*4,h*4),Image.Resampling.NEAREST),(j*80+8,20));draw.text((j*80+8,3),str(rid),fill='white')
    atlas.save(OUT/'icons-preview.png')
    # Only widget color immediate values in updater UI; erase/program logic untouched.
    for addr,old,new,reg,role in [
        (0x020145bc,0xf6,0xfa,4,'update background black'),
        (0x020145ec,0xfc,0xf0,4,'update progress yellow'),
        (0x02014600,0xf1,0xfa,4,'update progress track black'),
        (0x02014630,0xfc,0xf0,6,'update text yellow')]:
        expect=0x27<<26|reg<<21|old
        if struct.unpack_from('<I',base,off(addr))[0]!=expect:raise ValueError('Updater UI instruction changed')
        put(off(addr),struct.pack('<I',0x27<<26|reg<<21|new),role)
    if base[0x8c030:0x8c038]!=b'14:47:57':raise ValueError('Old update ID mismatch')
    put(0x8c030,b'14:48:00','native update ID')
    for lo,hi in [(0,0x2400),(0x88484,0x8888c),(0x8c200,0x8c290),(0xc20bb,0xc2343)]:
        if base[lo:hi]!=image[lo:hi]:raise ValueError('Protected bootstrap/LCD/resource descriptor changed')
    diffs={i for i,(a,b) in enumerate(zip(base,image)) if a!=b}
    if not diffs<=allowed:raise ValueError('Unexpected write')
    # Full updater must remain identical except the four declared display immediates.
    for i in range(off(0x2014388),off(0x20148a0)):
        if base[i]!=image[i] and not any(off(a)<=i<off(a)+4 for a in (0x20145bc,0x20145ec,0x2014600,0x2014630)):
            raise ValueError('Updater logic changed')
    (OUT/'DestBin.bin').write_bytes(image)
    manifest={'version':'СБОЙ 0.3','sha256':sha(image),'baseline_sha256':BASE_SHA,'bytes':len(image),'changed_bytes':len(diffs),'changes':changes,'status':'offline built, not installed','mode_slots':{'0':'обычный','1':'ЧЕРНИЛА','2':'СОРТ','3':'ПРИЗРАК','4':'native color 4','5':'native color 5'},'preview_badge':'only observed 160x80 frame; no caption in saved photographs','sorting':'stable 2x2 YUV-block brightness sorting inside threshold-separated runs and 128-pixel windows, alternating direction each 32 rows; stills wider than 320 pixels only','new_updater_colors_visible':'on updates launched by this version, not the initial installation from 0.2','still_review_duration':'unchanged','hardware_validation':'pending'}
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    sheet=Image.new('RGB',(984,180),(16,16,16))
    for j,role in enumerate(('startup','shutdown','usb')):
        im=Image.open(OUT/(role+'.jpg'));sheet.paste(im.resize((320,160),Image.Resampling.NEAREST),(j*328+8,10))
    sheet.save(OUT/'screens-preview.png')
    print(json.dumps({k:manifest[k] for k in ['version','sha256','bytes','changed_bytes','status']},ensure_ascii=False,indent=2))
if __name__=='__main__':build()
