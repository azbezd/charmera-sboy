import unittest,struct,random
from red_port import *
from test_effect_kernel import Machine
from test_red_effects import expected
STOP=0xf0000000;Y=0x2100000;UV=0x2200000;STACK=0x2800000
class PortTests(unittest.TestCase):
 def make(self,w=160,h=80,mode=1):
  p,_,layout=build_patches();rng=random.Random(77)
  y=bytearray(rng.randrange(256) for _ in range(w*h));uv=bytearray(rng.randrange(256) for _ in range(w*h//2))
  m=Machine(p,[(Y,y),(UV,uv),(UI,bytearray(256)),(TICK,bytearray(4)),(layout['STATE'],bytearray(32)),(STACK,bytearray(1024)),(ENC,bytearray(512)),(REC,bytearray(256))]);m.r[1]=STACK+1024;m.r[3:7]=[Y,UV,w,h];m.r[9]=STOP;m.mem(UI+0x5e,1,mode);return m,layout,y,uv
 def test_master_actual_code_all_modes_and_disjoint_flush(self):
  for mode in range(1,13):
   m,l,y,uv=self.make(160,80,mode);old=(bytes(y),bytes(uv));before=m.r.copy();flush=[]
   def cb(v):
    flush.append(tuple(v.r[3:5]));v.r[3:8]=[0xdead]*5 # native flush really clobbers these
   m.calls={FLUSH:cb};m.run(l['MASTER'],2_000_000)
   self.assertEqual(flush,[(Y,12800),(UV,6400)])
   for r in (1,2,3,4,5,6,9,14,16,18,20,22,24,26,28,30):self.assertEqual(m.r[r],before[r],(mode,r))
   if mode!=3:self.assertEqual((y,uv),expected(*old,160,80,mode))
   else:self.assertEqual(sorted(y),sorted(old[0]));self.assertEqual(sorted(uv),sorted(old[1]))
 def test_menu_deadline_wrap_and_not_saved(self):
  for w,h,elapsed in ((160,80,0),(160,80,1999),(160,80,2000),(160,80,2001),(320,240,1)):
   m,l,y,uv=self.make(w,h);before=bytes(y+uv);m.mem(l['STATE'],4,1);m.mem(l['STATE']+4,4,0xffffff00);m.mem(TICK,4,(0xffffff00+elapsed)&0xffffffff)
   m.run(l['MENU'],100000);self.assertEqual(bytes(y+uv)!=before,w==160 and elapsed<2000)
 def test_key_cycles_all_bounds(self):
  for site,exit,step in ((0x2016d7c,0x2016e14,1),(0x2016e8c,0x2016fb4,-1),(0x201841c,0x2018480,1),(0x20184fc,0x2018600,-1)):
   for mode in range(1,13):
    m,l,_,_=self.make(mode=mode);m.r[2]=UI;m.r[9]=exit;m.mem(TICK,4,1234);seen=[]
    def setter(v):seen.append(v.r[3])
    m.calls={SETTER:setter};m.run(site,1000);n=(mode-1+step)%12+1
    self.assertEqual(seen,[n]);self.assertEqual(m.mem(UI+0x5e,1),n);self.assertEqual(m.mem(l['STATE'],4),1);self.assertEqual(m.mem(l['STATE']+4,4),1234)
 def test_setter_replays_native_and_preserves_light(self):
  for mode in (0,1,12,13):
   m,l,_,_=self.make();m.r[3]=mode;m.r[9]=SETTER+4;m.mem(UI+0x5d,1,2)
   m.run(SETTER,1000);self.assertEqual(m.mem(m.r[1]-12,4),m.r[2]);self.assertEqual(m.mem(UI+0x5d,1),2 if 1<=mode<=12 else 0);self.assertEqual(m.r[3],0 if 1<=mode<=12 else mode)
 def test_shutter_hides_and_replays(self):
  m,l,_,_=self.make();m.mem(l['STATE'],4,1);m.r[9]=0x2008504;m.run(0x2008500,100)
  self.assertEqual(m.mem(l['STATE'],4),0);self.assertEqual(m.mem(m.r[1]-36,4),m.r[2])
 def test_video_deferred_order_and_no_pixels_in_irq(self):
  m,l,y,uv=self.make(160,80,11);before=bytes(y+uv);events=[];m.mem(REC,1,1);m.mem(ENC+0x10,4,Y);m.mem(ENC+0x14,4,UV);m.mem(ENC+0x48,4,200000);m.mem(l['STATE']+12,4,160);m.mem(l['STATE']+16,4,80)
  def allocation(v):events.append('allocate');v.r[11]=0x2500000
  def capture(v):events.append(('capture',v.r[3]))
  m.calls={0x202c684:capture,0x203a5a4:allocation,0x2052420:lambda v:None}
  m.run(l['V_DEFER'],1000);self.assertEqual(bytes(y+uv),before);self.assertEqual(m.mem(l['STATE']+8,4),1);self.assertEqual(events,[('capture',0),'allocate'])
  def record(name):return lambda v:events.append(name)
  m.calls.update({FLUSH:record('flush'),0x202e428:record('source'),0x202df94:record('destination'),0x202e67c:record('encode'),0x20219f4:record('irq'),0x204849c:record('writer')})
  m.run(l['V_WORK'],2_000_000);self.assertEqual(events[-7:],['flush','flush','source','destination','encode','irq','writer']);self.assertEqual(m.mem(l['STATE']+8,4),2);self.assertNotEqual(bytes(y+uv),before)
  m.r[2]=0;m.r[14]=ENC;m.r[9]=0x20377f8;m.run(l['V_IRQ'],2_001_000)
  self.assertEqual(events[-1],('capture',1));self.assertEqual(m.mem(ENC+0x40,4),0);self.assertEqual(m.mem(l['STATE']+8,4),0)
 def test_video_preview_handshake_real_menu_and_filter(self):
  m,l,y,uv=self.make(mode=8);frame=bytearray(40);struct.pack_into('<II',frame,4,Y,UV);struct.pack_into('<HH',frame,32,160,80);m.regions.append((0x2900000,frame));events=[]
  def get(v):v.r[11]=0x2900000
  def copy(v):self.assertEqual(v.r[3],0x2900000);events.append('copy')
  m.calls={0x201b0e0:get,FLUSH:lambda v:None,0x2030fec:copy,0x2031b18:lambda v:events.append('refresh')}
  before=bytes(y+uv);m.run(0x2052420,2_000_000);self.assertNotEqual(bytes(y+uv),before);self.assertEqual(events,['copy','refresh']);self.assertEqual(m.mem(UI+0x60,1),2)
  m.run(0x2052420,2_001_000);self.assertEqual(events,['copy','refresh'])
 def test_stop_disables_capture_before_free(self):
  m,l,_,_=self.make();events=[];m.mem(l['STATE']+8,4,2)
  def capture(v):self.assertEqual(v.r[3],0);events.append('capture off')
  def unregister(v):self.assertEqual(v.r[3:5],[0,0]);events.append('frame IRQ cleared')
  m.calls={0x202c684:capture,0x202b9c8:unregister,0x2037fd4:lambda v:events.append('native free')};m.run(0x2052500,1000);self.assertEqual(events,['capture off','frame IRQ cleared','native free']);self.assertEqual(m.mem(l['STATE']+8,4),0)
 def test_video_exit_releases_preview_without_losing_mode(self):
  m,l,_,_=self.make(mode=11);m.r[9]=0x200c51c;m.mem(UI+0x5c,1,1);m.mem(UI+0x5d,1,2);m.mem(UI+0x60,1,2);m.run(0x200c518,1000)
  self.assertEqual([m.mem(UI+o,1) for o in (0x5c,0x5d,0x60)],[0,0,0]);self.assertEqual(m.mem(UI+0x5e,1),11)
 def test_video_inactive_no_encode(self):
  m,l,_,_=self.make();m.mem(l['STATE']+8,4,1);seen=[];m.calls={0x204849c:lambda v:seen.append('writer'),0x2052420:lambda v:None};m.run(l['V_WORK'],1000);self.assertEqual(seen,['writer']);self.assertEqual(m.mem(l['STATE']+8,4),0)
if __name__=='__main__':unittest.main()
