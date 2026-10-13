"""Exact red-B OR1K integration. No hardware or filesystem mutation on import."""
import struct
from red_effects import Asm,ptr,kernel,palettes,BAYER,LABELS
UI=0x2082334;TICK=0x207edb8;ENC=0x2086c18;REC=0x2085eb0
START=0x2050da0;END=0x20526c8;SETTER=0x204aa7c;FLUSH=0x2021d30

def jump(site,target,link=False):
 a=Asm(site);a.branch(int(link),target);return a.finish()
def save(a,regs):
 for i,r in enumerate(regs):a.store(0x35,1,r,-4*(i+1))
 a.addi(1,1,-4*len(regs))
def restore(a,regs):
 a.addi(1,1,4*len(regs))
 for i,r in enumerate(regs):a.load(0x21,r,1,-4*(i+1))
def call(a,target):a.branch(1,target)

def menu_bits():
 from PIL import Image,ImageDraw
 from ru_pixels import text,text_width
 result=bytearray()
 for i,label in enumerate(LABELS):
  im=Image.new('RGB',(96,16));d=ImageDraw.Draw(im)
  text(im,((96-text_width(label))//2,1),label,'white')
  text(im,((96-text_width(f'{i+1:02}/12'))//2,9),f'{i+1:02}/12','white')
  d.line([(3,5),(6,2),(9,5)],fill='white');d.line((6,2,6,8),fill='white')
  d.line([(86,5),(89,8),(92,5)],fill='white');d.line((89,2,89,8),fill='white')
  for y in range(16):
   for x in range(0,96,8):result.append(sum(bool(im.getpixel((x+j,y))[0])<<(7-j) for j in range(8)))
 return bytes(result)

def build_patches(video=True):
 # Compact fixed allocation. Every interval checked below; no legacy A offsets.
 K=START;PAL=K+1160;BAY=PAL+192;SORT=BAY+16;MASTER=SORT+448
 PREVIEW=MASTER+144;MENU=PREVIEW+96;DATA=MENU+352
 STATE=DATA+2304;HOOK=STATE+32;EVENT=HOOK+120;HIDE=EVENT+40
 V_MODE=HIDE+32;V_GEOM=V_MODE+64;V_DEFER=V_GEOM+80;V_WORK=V_DEFER+240;V_IRQ=V_WORK+272
 out={};roles={}
 def put(addr,data,role):
  assert not any(addr<a+len(v) and a<addr+len(data) for a,v in out.items()),role
  out[addr]=data;roles[addr]=role
 put(K,kernel(K,PAL,BAY,TICK),'twelve distinct YUV styles')
 put(PAL,palettes(),'YUV palettes');put(BAY,bytes(BAYER),'Bayer thresholds')
 import sort_kernel,preview_badge
 old=(sort_kernel.SORT,sort_kernel.SORT_END,preview_badge.BADGE)
 sort_kernel.SORT=SORT;sort_kernel.SORT_END=MASTER;preview_badge.BADGE=MASTER
 try:s=bytearray(sort_kernel.sorter(live=True)[SORT])
 finally:sort_kernel.SORT,sort_kernel.SORT_END,preview_badge.BADGE=old
 # Plain leaf return, no yellow badge; shorter still windows cap work.
 s[-4:]=struct.pack('<I',0x44004800)
 aa=Asm(0);aa.li(28,127);oldword=struct.pack('<I',0x9f8000ff)
 assert s.count(oldword)==1;s=s.replace(oldword,aa.finish())
 put(SORT,bytes(s),'bounded pixel sort, 32/128-pixel runs')
 a=Asm(MASTER);save(a,(9,3,4,5,6));ptr(a,11,UI);a.load(0x23,7,11,0x5e)
 a.sfi(0,7,3);a.bf('sort');call(a,K);a.j('flush')
 a.label('sort');call(a,SORT)
 a.label('flush');a.mul(4,5,6);call(a,FLUSH)
 # Restore original UV and dimensions from our frame, flush disjoint plane.
 a.load(0x21,3,1,8);a.load(0x21,5,1,4);a.load(0x21,6,1,0);a.mul(4,5,6);a.shr(4,4,1);call(a,FLUSH)
 restore(a,(9,3,4,5,6));a.ret();put(MASTER,a.finish(),'effect dispatch and separate plane cache flush')
 a=Asm(PREVIEW);save(a,(9,3,4,5,6));call(a,MASTER);call(a,MENU)
 a.mul(4,5,6);a.shr(11,4,1);a.add(4,4,11);call(a,FLUSH);restore(a,(9,3,4,5,6));a.ret();put(PREVIEW,a.finish(),'preview effects then transient menu')
 a=Asm(MENU)
 for r,n in ((5,160),(6,80)):a.sfi(1,r,n);a.bf('return')
 ptr(a,11,STATE);a.load(0x21,12,11);a.sfi(0,12,0);a.bf('return');a.load(0x21,12,11,4)
 ptr(a,13,TICK);a.load(0x21,13,13);a.sub(13,13,12);a.sfi(3,13,2000);a.bf('hide')
 ptr(a,11,UI);a.load(0x23,11,11,0x5e);a.addi(11,11,-1);a.sfi(2,11,11);a.bf('return')
 a.li(13,192);a.mul(11,11,13);ptr(a,8,DATA);a.add(8,8,11);a.addi(11,3,18*160+32);a.li(12,16)
 a.label('row');a.li(15,12)
 a.label('byte');a.load(0x23,13,8);a.addi(8,8,1);a.li(17,8)
 a.label('bit');a.mask(21,13,128);a.li(19,16);a.sfi(0,21,0);a.bf('pixel');a.li(19,235)
 a.label('pixel');a.store(0x36,11,19);a.addi(11,11,1);a.shl(13,13,1);a.addi(17,17,-1);a.sfi(1,17,0);a.bf('bit')
 a.addi(15,15,-1);a.sfi(1,15,0);a.bf('byte');a.addi(11,11,64);a.addi(12,12,-1);a.sfi(1,12,0);a.bf('row')
 a.addi(11,4,9*160+32);a.li(12,8);a.li(19,128)
 a.label('uvrow');a.li(15,96)
 a.label('uvpixel');a.store(0x36,11,19);a.addi(11,11,1);a.addi(15,15,-1);a.sfi(1,15,0);a.bf('uvpixel')
 a.addi(11,11,64);a.addi(12,12,-1);a.sfi(1,12,0);a.bf('uvrow');a.ret()
 a.label('hide');a.store(0x35,11,0);a.label('return');a.ret();put(MENU,a.finish(),'preview menu with unsigned 2-second timeout')
 put(DATA,menu_bits(),'Cyrillic labels and vertical arrows');put(STATE,bytes(32),'volatile menu/video state')
 a=Asm(HOOK);a.emit(0xd7e117f4);ptr(a,11,UI);a.mask(12,3,255)
 a.sfi(4,12,1);a.bf('native');a.sfi(2,12,12);a.bf('native')
 a.li(13,2);a.store(0x36,11,13,0x5d);a.li(13,1);a.store(0x36,11,13,0x5c);a.li(3,0);a.j('resume')
 a.label('native');a.load(0x23,13,11,0x5d);a.sfi(1,13,2);a.bf('resume');a.store(0x36,11,0,0x5d)
 a.label('resume');a.j(SETTER+4);put(HOOK,a.finish(),'neutral native sensor setter, custom frame category')
 a=Asm(EVENT);ptr(a,11,TICK);a.load(0x21,12,11);ptr(a,11,STATE);a.store(0x35,11,12,4);a.li(12,1);a.store(0x35,11,12);a.j(SETTER);put(EVENT,a.finish(),'accepted key restarts menu timeout')
 # Both native photo entry points share this wrapper; no input handler changes.
 a=Asm(HIDE);ptr(a,11,STATE);a.store(0x35,11,0);a.emit(0xd7e117dc);a.j(0x2008504);put(HIDE,a.finish(),'capture entry hides menu')
 # Site-specific patches, kept separate from payload allocations.
 for site,target,link in ((0x2008500,HIDE,False),(SETTER,HOOK,False),(0x20080fc,PREVIEW,True),(0x2038220,MASTER,True)):
  put(site,jump(site,target,link),'native hook')
 # Preserve other native call targets into replaced effect block.
 for site in (0x201b328,0x201b340,0x201b358):put(site,jump(site,MASTER,True),'legacy dispatcher call redirect')
 for site,end,forward in ((0x2016d7c,0x2016df8,True),(0x2016e8c,0x2016f08,False),(0x201841c,0x2018464,True),(0x20184fc,0x2018530,False)):
  finish={0x2016d7c:0x2016e14,0x2016e8c:0x2016fb4,0x201841c:0x2018480,0x20184fc:0x2018600}[site]
  a=Asm(site);a.load(0x23,3,2,0x5e)
  a.addi(3,3,1 if forward else -1);a.sfi(4,3,1);a.bf('wrap');a.sfi(5,3,12);a.bf('store')
  a.label('wrap');a.li(3,1 if forward else 12);a.label('store');a.store(0x36,2,3,0x5e);call(a,EVENT);a.j(finish)
  code=a.finish();assert site+len(code)<=end;put(site,code,'short-key cycle, long-key branches untouched')
 # Photo default, neutral exit, preserve selection in video.
 for site,reg,value in ((0x2007f34,3,1),(0x2007f6c,3,2),(0x2007fe0,3,0)):
  a=Asm(site);a.li(reg,value);put(site,a.finish(),'mode lifecycle')
 # Category 2, handshake 1 at photo mode entry.
 a=Asm(0x2007f74);a.li(11,1);a.store(0x36,2,11,0x5c);put(0x2007f74,a.finish(),'photo handshake/category')
 # Above overwrites 7f78 category store, publish category separately at 7f7c.
 a=Asm(0x2007f7c);a.store(0x36,2,3,0x5d);a.store(0x36,2,0,0x5f);put(a.base,a.finish(),'photo custom category')
 put(0x200d04c,struct.pack('<I',0x15000000),'retain selected video effect')
 a=Asm(0x200d050);a.load(0x23,3,2,0x5e);put(a.base,a.finish(),'video uses retained selector')
 # Date formatter: leave RTC untouched, terminate visible date at ten chars.
 a=Asm(0x2032eb0);a.li(2,0);a.store(0x36,4,2,10);a.store(0x36,7,2);ptr(a,11,0x207f7dc);a.j(0x2032fc4);put(a.base,a.finish(),'date only')
 if video:
  READY=STATE+8;DIMS=STATE+12
  a=Asm(V_MODE);save(a,(9,));a.li(3,1);a.li(4,0);call(a,0x202e444);ptr(a,11,READY);a.store(0x35,11,0);restore(a,(9,));a.ret();put(V_MODE,a.finish(),'RAM-fed JPEG mode')
  a=Asm(V_GEOM);save(a,(9,));ptr(a,11,DIMS);a.store(0x35,11,24);a.store(0x35,11,14,4);call(a,0x202e1c0);restore(a,(9,));a.ret();put(V_GEOM,a.finish(),'remember native cropped source geometry')
  # Frame-complete IRQ: stop capture, defer all pixel work to main loop.
  a=Asm(V_DEFER);save(a,(9,2));ptr(a,11,REC);a.load(0x23,11,11);a.sfi(1,11,1);a.bf('return');ptr(a,2,READY);a.load(0x21,11,2);a.sfi(1,11,0);a.bf('return');a.li(3,0);call(a,0x202c684)
  ptr(a,2,ENC);a.load(0x21,11,2,0x40);a.sfi(1,11,0);a.bf('ready');a.addi(3,2,0x4c);a.load(0x21,4,2,0x48);call(a,0x203a5a4);a.store(0x35,2,11,0x40);a.sfi(1,11,0);a.bf('ready')
  a.li(3,1);call(a,0x202c684);a.j('return')
  a.label('ready');ptr(a,2,READY);a.li(11,1);a.store(0x35,2,11)
  a.label('return');restore(a,(9,2));a.li(11,1);a.ret();put(V_DEFER,a.finish(),'pause CSI and queue CPU work, no pixel loop in IRQ')
  a=Asm(V_WORK);save(a,(9,2));call(a,0x2052420);ptr(a,2,READY);a.load(0x21,11,2);a.sfi(1,11,1);a.bf('done');ptr(a,11,REC);a.load(0x23,11,11);a.sfi(1,11,1);a.bf('cancel');a.li(11,2);a.store(0x35,2,11)
  ptr(a,2,ENC);a.load(0x21,3,2,0x10);a.load(0x21,4,2,0x14);ptr(a,11,DIMS);a.load(0x21,5,11);a.load(0x21,6,11,4);call(a,MASTER)
  a.load(0x21,3,2,0x10);a.load(0x21,4,2,0x14);call(a,0x202e428)
  a.load(0x21,3,2,0x40);a.load(0x21,4,2,0x48);a.add(4,4,3);call(a,0x202df94);call(a,0x202e67c);a.li(3,16);a.li(4,1);call(a,0x20219f4);a.j('done')
  a.label('cancel');a.store(0x35,2,0)
  a.label('done');restore(a,(9,2));a.j(0x204849c);put(V_WORK,a.finish(),'main-loop effects before JPEG and native AVI/audio writer')
  a=Asm(V_IRQ);ptr(a,11,READY);a.load(0x21,12,11);a.sfi(1,12,2);a.bf('done');a.store(0x35,11,0);ptr(a,11,REC);a.load(0x23,11,11);a.sfi(1,11,1);a.bf('done');a.li(3,1);call(a,0x202c684)
  a.label('done');a.j(0x20377f8);put(V_IRQ,a.finish(),'JPEG completion restarts capture')
  for site,target,link in ((0x2038d48,0x2038e68,False),(0x2038f10,V_MODE,True),(0x2038f50,V_GEOM,True),(0x200c4f4,V_WORK,True),(0x20377f4,V_IRQ,False)):
   # 377f4 clears output pointer; do so before branching via own wrapper below.
   put(site,jump(site,target,link),'video integration')
  # IRQ completion replaces only sw state+40 with trampoline; replay mandatory.
  del out[V_IRQ];del roles[V_IRQ]
  a=Asm(V_IRQ);a.emit(0xd40e1040);ptr(a,11,READY);a.load(0x21,12,11);a.sfi(1,12,2);a.bf('done');a.store(0x35,11,0);ptr(a,11,REC);a.load(0x23,11,11);a.sfi(1,11,1);a.bf('done');a.li(3,1);call(a,0x202c684);a.label('done');a.j(0x20377f8);put(V_IRQ,a.finish(),'replay JPEG completion and restart CSI')
  # Callback 0 is full frame completion, already used by native RAM still path.
  a=Asm(0x2038ff4);a.li(3,0);ptr(a,4,V_DEFER);call(a,0x202b9c8);a.li(3,3);a.li(4,0);call(a,0x202b9c8);a.li(3,9);a.li(4,0);call(a,0x202b9c8);ptr(a,3,0x20376ac);call(a,0x202df08);a.store(0x36,14,0,1);a.j(0x2039030)
  # Room ends 39030; compact using callback pointer movhi shared high.
  assert len(a.finish())<=0x3c, len(a.finish())
  put(a.base,a.finish(),'register RAM frame and JPEG callbacks')
  # Start CSI frame callback mask using removed hour formatting storage.
  arm=0x2032ed0;a=Asm(arm);save(a,(9,));ptr(a,3,0x80000);a.li(4,1);call(a,0x202c648);a.li(3,1);call(a,0x202c684);restore(a,(9,));a.li(2,0);a.j(0x2039034);put(arm,a.finish(),'arm full-frame capture after video init')
  put(0x2039030,jump(0x2039030,arm),'video capture arm')
 a=Asm(0x2052400);ptr(a,11,STATE);a.store(0x35,11,0);a.emit(0xd7e117dc);a.j(0x20087b8);put(a.base,a.finish(),'second native photo entry hides menu')
 put(0x20087b4,jump(0x20087b4,0x2052400),'second photo entry hook')
 if video:
  # Consume the same native preview handshake in video mode's own main loop.
  a=Asm(0x2052420);save(a,(9,2,14));ptr(a,2,UI);a.load(0x23,11,2,0x60);a.sfi(1,11,0);a.bf('done');a.li(11,1);a.store(0x36,2,11,0x60);call(a,0x201b0e0);a.sfi(0,11,0);a.bf('done');a.mov(14,11)
  a.load(0x21,3,14,4);a.load(0x21,4,14,8);a.load(0x25,5,14,0x20);a.load(0x25,6,14,0x22);call(a,PREVIEW);a.li(11,2);a.store(0x36,2,11,0x60);a.mov(3,14);call(a,0x2030fec);call(a,0x2031b18)
  a.label('done');restore(a,(9,2,14));a.ret();put(a.base,a.finish(),'video viewfinder shares photo frame handshake')
  a=Asm(0x2052500);save(a,(9,));ptr(a,11,READY);a.store(0x35,11,0);a.li(3,0);call(a,0x202c684);a.li(3,0);a.li(4,0);call(a,0x202b9c8);restore(a,(9,));a.j(0x2037fd4);put(a.base,a.finish(),'stop CSI before native video buffer free')
  put(0x20481d0,jump(0x20481d0,0x2052500,True),'safe video stop')
  a=Asm(0x2052560);a.emit(0xd7e117f0);ptr(a,11,UI);a.store(0x36,11,0,0x5c);a.store(0x36,11,0,0x5d);a.store(0x36,11,0,0x60);ptr(a,11,STATE);a.store(0x35,11,0);a.j(0x200c51c);put(a.base,a.finish(),'video mode exit releases software preview')
  put(0x200c518,jump(0x200c518,0x2052560),'video exit hook')
 # Check all allocated code, including the end of video payload.
 assert max(a+len(v) for a,v in out.items() if START<=a<END)<=END
 return out,roles,dict(K=K,SORT=SORT,MASTER=MASTER,PREVIEW=PREVIEW,MENU=MENU,DATA=DATA,STATE=STATE,HOOK=HOOK,EVENT=EVENT,HIDE=HIDE,V_MODE=V_MODE,V_GEOM=V_GEOM,V_DEFER=V_DEFER,V_WORK=V_WORK,V_IRQ=V_IRQ,END=END)
