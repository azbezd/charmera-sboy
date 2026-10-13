"""Native-size red-B visual resources; preserve atlas geometry and palette."""
import io,struct
from PIL import Image,ImageDraw
from ru_pixels import centered,text,FONT
FONT['Z']='11111/00001/00010/00100/01000/10000/11111'
BG=(8,10,12);FG=(241,235,211);ACC=(255,203,72)
def screen(role):
 im=Image.new('RGB',(160,80),BG);d=ImageDraw.Draw(im)
 d.line((48,17,108,17),fill=ACC);d.line((109,19,115,19),fill=ACC)
 centered(im,26,'СБОЙ',FG,2)
 centered(im,45,{'startup':'ВХОД В РЕАЛЬНОСТЬ','shutdown':'СИГНАЛ ПОТЕРЯН','usb':'КАРТА ПОДКЛЮЧЕНА'}[role],ACC)
 centered(im,60,'КРАСНАЯ / 1.0',FG)
 return im

def icon(i,w,h):
 im=Image.new('L',(20,20));d=ImageDraw.Draw(im);W=251;A=240
 def line(points,color=W,width=1):d.line(points,fill=color,width=width)
 def box(b,color=W,width=1):d.rectangle(b,outline=color,width=width)
 if i in (18,19,20,21,22,23,24):
  box((5,3,14,18));d.rectangle((8,1,11,2),fill=W)
  if i in (20,21,22,23):d.rectangle((7,17-(i-19)*3,12,16),fill=W)
  if i==24:d.polygon([(10,5),(7,11),(10,11),(9,16),(13,9),(10,9)],fill=A)
 elif i in (26,27,28,40):
  d.polygon([(11,2),(5,11),(9,11),(7,18),(15,8),(11,8)],fill=W)
  if i in (27,40):line((2,2,17,17),0,3);line((2,2,17,17),W)
  if i==26:text(im,(13,12),'A',W)
 elif i in (3,29,37,38):
  d.polygon([(5,2),(12,2),(16,6),(16,18),(4,18),(4,3)],outline=W)
  for x in (7,9,11):line((x,4,x,7))
  if i in (29,38):line((6,10,13,16),W);line((13,10,6,16),W)
  else:line([(6,13),(9,15),(13,10)],A)
 elif i in (8,35):
  box((2,5,12,15));d.polygon([(13,8),(17,5),(17,15),(13,12)],outline=W)
  d.rectangle((5,8,7,10),fill=A)
 elif i in (31,32):
  box((2,5,17,16));d.rectangle((5,3,10,5),fill=W);box((7,8,12,13));d.point((15,8),fill=A)
  if i==32:line([(1,7),(0,7),(0,18),(15,18)])
 elif i in (30,33,34):
  d.polygon([(6,3),(16,10),(6,17)],outline=W,fill=W if i==33 else None)
  if i==34:line((3,3,3,17),A,2)
 elif i==36:d.ellipse((5,5,14,14),fill=A)
 elif i==25:
  line([(5,2),(14,2),(14,5),(6,15),(6,18),(14,18),(14,15),(5,5),(5,2)])
 elif i==0:
  box((7,2,12,12));line([(4,8),(4,12),(7,15),(12,15),(15,12),(15,8)]);line((9,15,9,18));line((6,18,13,18))
 elif i==1:
  box((3,3,16,16));line([(10,5),(10,10),(14,10)])
 elif i==2:
  line((4,5,10,5));line((7,2,7,8));line((10,14,16,14));line((4,17,17,4),A)
 elif i==4:text(im,(4,7),'HZ',W)
 elif i==5:
  line([(2,15),(7,7),(10,11),(13,5),(18,15),(2,15)]);d.point((5,4),fill=A)
 elif i==6:line([(3,14),(6,10),(6,5),(9,3),(12,5),(12,10),(16,14),(3,14)]);line((7,17,12,17))
 elif i in (7,39):
  box((3,3,16,16));box((6,6,13,13));d.rectangle((8,8,11,11),fill=A)
 elif i==9:line([(2,10),(6,6),(13,6),(17,10),(13,14),(6,14),(2,10)]);box((8,8,11,11))
 elif i==10:
  d.rectangle((9,2,11,4),fill=W);line([(4,7),(8,6),(13,10),(17,9)]);line([(8,6),(7,12),(3,17)]);line([(7,12),(12,13),(14,18)])
 elif i in (11,12):
  line([(15,5),(11,3),(6,4),(3,8),(4,14),(9,17),(14,15)]);line((15,2,15,6));line((11,6,15,6))
  if i==11:line((10,1,10,8),A)
 elif i==13:text(im,(4,7),'HD',W)
 elif i in (14,15):box((3,5,16,15));d.rectangle((6,8,13,12),fill=W if i==14 else 0)
 elif i==16:
  d.rectangle((9,3,10,4),fill=A);line((9,7,9,15));line((7,16,12,16))
 elif i==17:
  d.polygon([(3,8),(6,8),(11,4),(11,16),(6,12),(3,12)],outline=W);line([(14,6),(16,9),(16,12),(14,15)])
 else:raise ValueError(i)
 if i in range(18,25):
  im=Image.new('L',(w,h));d=ImageDraw.Draw(im);d.rectangle((2,2,9,15),outline=W);d.rectangle((4,0,7,1),fill=W)
  if i in (20,21,22,23):d.rectangle((4,14-(i-19)*2,7,13),fill=W)
  if i==24:d.polygon([(6,4),(3,10),(6,10),(5,14),(9,7),(6,7)],fill=A)
  return im
 if i==31:
  im=Image.new('L',(16,16));d=ImageDraw.Draw(im);d.rectangle((1,4,14,13),outline=W);d.rectangle((4,2,8,4),fill=W);d.rectangle((5,6,10,11),outline=W);d.point((12,6),fill=A);return im
 if i==35:
  im=Image.new('L',(16,16));d=ImageDraw.Draw(im);d.rectangle((1,4,10,12),outline=W);d.polygon([(11,7),(14,4),(14,12),(11,10)],outline=W);d.rectangle((3,6,5,8),fill=A);return im
 return im.resize((w,h),Image.Resampling.NEAREST)

def resources(base,out):
 result={};out.mkdir(parents=True,exist_ok=True)
 for rid,role in ((11,'startup'),(12,'shutdown'),(16,'usb')):
  rel,n=struct.unpack_from('<II',base,0x7f800+rid*8);im=screen(role);im.save(out/(role+'.png'))
  for q in range(91,39,-1):
   f=io.BytesIO();im.save(f,'JPEG',quality=q,subsampling=2,optimize=True);data=f.getvalue()
   if len(data)<=n:break
  assert len(data)<=n and Image.open(io.BytesIO(data)).size==(160,80)
  result[0x7f800+rel]=(data.ljust(n,b'\xff'),'Cyrillic '+role);(out/(role+'.jpg')).write_bytes(data)
 # Palette index240 unused by factory, standard Buildwin BGR565 yellow.
 assert base[0x99274+240*4:0x99274+241*4]==bytes(4)
 result[0x99274+240*4]=(struct.pack('<HH',0x07ff,31),'accent palette')
 sheet=Image.new('RGB',(700,600),(28,29,30));d=ImageDraw.Draw(sheet)
 for i in range(41):
  w,h,rel=struct.unpack_from('<III',base,0x95288+12*i);im=icon(i,w,h)
  result[0x95288+rel]=(im.tobytes(),f'icon {i}')
  rgb=Image.new('RGB',(w,h));rgb.putdata([{0:(28,29,30),251:FG,240:ACC}[v] for v in im.tobytes()]);x=i%7*100;y=i//7*100
  sheet.paste(rgb.resize((w*3,h*3),Image.Resampling.NEAREST),(x+5,y+20));d.text((x+5,y+2),str(i),fill=FG)
 sheet.save(out/'icons.png')
 return result
