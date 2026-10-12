#!/usr/bin/env python3
"""Render a synthetic test scene through actual 0.8/0.9 OR1K effect instructions.
Requires locally built images, Pillow and numpy. No personal camera media used.
"""
from pathlib import Path
import sys
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'custom-firmware/tools'))
from test_v08 import execute
fontpaths=['/System/Library/Fonts/Supplemental/Arial.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']
fontpath=next((p for p in fontpaths if Path(p).exists()),None)
if not fontpath:raise SystemExit('Install a Cyrillic Arial or DejaVuSans font; see fontpaths in this script.')
def font(n):return ImageFont.truetype(fontpath,n)
w,h=160,80
# A purpose-built calibration scene: no photograph or proprietary test chart.
im=Image.new('RGB',(w,h));d=ImageDraw.Draw(im)
for x in range(w):
 for y in range(h):
  im.putpixel((x,y),(int(24+x*.75),int(28+y*.65),int(46+x*.22)))
d.rectangle((0,60,159,79),fill=(167,148,110))
d.rectangle((13,17,47,61),fill=(237,181,48));d.polygon([(13,17),(21,10),(55,10),(47,17)],fill=(252,211,91));d.polygon([(47,17),(55,10),(55,55),(47,61)],fill=(128,81,33))
d.ellipse((82,15,128,61),fill=(52,132,156));d.ellipse((90,19,116,43),fill=(102,190,195));d.ellipse((117,41,145,69),fill=(209,78,56))
d.line((65,66,69,19),fill=(180,195,156),width=2)
for y in (25,35,45):
 d.polygon([(69,y+5),(58,y-1),(60,y-6),(68,y)],fill=(107,151,72));d.polygon([(68,y+9),(78,y+1),(80,y-5),(70,y+2)],fill=(147,181,97))
for x,c in enumerate([(225,54,48),(238,174,47),(92,155,81),(40,127,166),(173,92,133),(218,215,195)]):d.rectangle((5+x*25,73,26+x*25,77),fill=c)
a=np.array(im,dtype=float);r,g,b=a[:,:,0],a[:,:,1],a[:,:,2]
y=np.clip(16+.257*r+.504*g+.098*b,0,255).astype('uint8');u=np.clip(128-.148*r-.291*g+.439*b,0,255);v=np.clip(128+.439*r-.368*g-.071*b,0,255)
uv=np.empty((40,160),dtype='uint8');uv[:,0::2]=u.reshape(40,2,80,2).mean(axis=(1,3));uv[:,1::2]=v.reshape(40,2,80,2).mean(axis=(1,3))
def rgb(yo,uvo):
 yy=np.frombuffer(yo,dtype='uint8').reshape(h,w).astype(float)-16;cc=np.frombuffer(uvo,dtype='uint8').reshape(h//2,w//2,2).astype(float)-128
 uu=np.repeat(np.repeat(cc[:,:,0],2,0),2,1);vv=np.repeat(np.repeat(cc[:,:,1],2,0),2,1)
 return Image.fromarray(np.clip(np.stack((1.164*yy+1.596*vv,1.164*yy-.392*uu-.813*vv,1.164*yy+2.017*uu),2),0,255).astype('uint8'))
board=Image.new('RGB',(1440,662),(15,17,19));draw=ImageDraw.Draw(board)
draw.text((40,26),'ОДНА СЦЕНА. ШЕСТЬ ХАРАКТЕРОВ.',font=font(32),fill=(238,237,223))
labels=[('ИСХОДНИК',None),('VHS I',1),('ЧЕРНИЛА I',3),('СОРТ I',5),('ПРИЗРАК I',7),('РАЗРЫВ I',9),('РАСТР I',11)]
for n,(label,index) in enumerate(labels):
 x=40+(n%4)*350;top=102+(n//4)*240
 if index:
  yo,uvo,steps=execute(y.tobytes(),uv.tobytes(),w,h,index,384);frame=rgb(yo,uvo)
 else:frame=rgb(y.tobytes(),uv.tobytes())
 board.paste(frame.resize((320,160),Image.Resampling.NEAREST),(x,top));draw.text((x,top+176),label,font=font(21),fill=(238,237,223))
 print('Rendered',label,flush=True)
draw.text((1090,366),'КОД ПРОШИВКИ\nВ ЭМУЛЯТОРЕ',font=font(24),fill=(232,187,75),spacing=10)
draw.text((1090,444),'Тестовая сцена 160 × 80\nНе снимки с камеры',font=font(19),fill=(152,158,163),spacing=8)
draw.line((40,589,1400,589),fill=(56,60,63));draw.text((40,612),'Вариант II усиливает контраст. Скорость работы на камере здесь не измеряется.',font=font(21),fill=(152,158,163))
board.save(ROOT/'assets/effects.webp',quality=92,method=6)
print(ROOT/'assets/effects.webp')
