import unittest,struct,hashlib,json,io,tempfile
from pathlib import Path
from PIL import Image
from build_red import BASE,BASE_SHA,OUT,build,off
from red_port import build_patches,START,END
class ImageTests(unittest.TestCase):
 def test_final_image_reproducible_and_payload_exact(self):
  b=(OUT/'DestBin.bin').read_bytes();m=json.loads((OUT/'manifest.json').read_text());self.assertEqual(hashlib.sha256(b).hexdigest(),m['sha256']);self.assertEqual(len(b),0x100000)
  p,_,_=build_patches()
  for a,v in p.items():self.assertEqual(b[off(a):off(a)+len(v)],v)
  with tempfile.TemporaryDirectory() as d:self.assertEqual(build(out=Path(d))['sha256'],m['sha256'])
 def test_boot_hardware_helpers_light_and_directories_unchanged(self):
  a=BASE.read_bytes();b=(OUT/'DestBin.bin').read_bytes()
  for lo,hi in ((0,0x2400),(0x78c00,0x7f890),(0x95288,0x95474),(off(0x2021d30),off(0x2021dac)),(off(0x2016f28),off(0x2016fb4)),(off(0x2018550),off(0x2018600))):self.assertEqual(a[lo:hi],b[lo:hi])
  # All remaining application instructions outside explicit patch intervals match.
  p,_,_=build_patches();allowed={o for addr,data in p.items() for o in range(off(addr),off(addr)+len(data))}
  for addr in (0x20129b4,0x20129e4,0x20129f8,0x2012a2c,0x2012a70):allowed.update(range(off(addr),off(addr)+4))
  self.assertTrue(all(i in allowed for i in range(0x2400,0x78c00) if a[i]!=b[i]))
 def test_jpeg_slots_and_icons_readable_geometry(self):
  a=BASE.read_bytes();b=(OUT/'DestBin.bin').read_bytes()
  for rid in (11,12,16):
   rel,n=struct.unpack_from('<II',b,0x7f800+8*rid);im=Image.open(io.BytesIO(b[0x7f800+rel:0x7f800+rel+n]));im.load();self.assertEqual(im.size,(160,80))
  for i in range(41):
   w,h,rel=struct.unpack_from('<III',b,0x95288+12*i);v=b[0x95288+rel:0x95288+rel+w*h];self.assertEqual(len(v),w*h);self.assertGreater(sum(x!=0 for x in v),10);self.assertTrue(set(v)<={0,240,251})
  self.assertEqual(b[0xbde9d:0xbdea9],b'SBOY-B-1.0\0\0')
 def test_reject_other_camera_before_output(self):
  with tempfile.TemporaryDirectory() as d:
   d=Path(d);bad=d/'wrong.bin';bad.write_bytes(bytes(0x100000))
   with self.assertRaises(ValueError):build(bad,d/'out')
   self.assertFalse((d/'out').exists())
 def test_no_unpatched_entry_into_replaced_instruction_interior(self):
  b=BASE.read_bytes();p,_,_=build_patches();ranges=[(a,a+len(v)) for a,v in p.items()]
  dead=[(START,END),(0x2032eb0,0x2032fc4),(0x2016d7c,0x2016e14),(0x2016e8c,0x2016f28),(0x201841c,0x2018480),(0x20184fc,0x2018550)]
  for o in range(0x2400,0x64b00,4):
   a=o-0x2400+0x2000000;w=struct.unpack_from('<I',b,o)[0]
   if w>>26 not in (0,1,3,4) or any(lo<=a<hi for lo,hi in ranges+dead):continue
   n=w&0x3ffffff;n=n-(1<<26) if n&(1<<25) else n;t=a+n*4
   self.assertFalse(any(lo<t<hi for lo,hi in ranges),(hex(a),hex(t)))
if __name__=='__main__':unittest.main()
