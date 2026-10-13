import json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from build import build,sha
from identify import read_metadata

class RedReleaseTests(unittest.TestCase):
 def setUp(self):
  self.bundle=json.loads((ROOT/'patches/sboy-red-1.0-rc7.json').read_text())
  self.red=json.loads((ROOT/'profiles/ax3295b-red-b.json').read_text())
 def test_exact_profile_and_output(self):
  b=self.bundle;self.assertEqual(b['factory_sha256'],self.red['factory_sha256']);self.assertEqual(b['size'],0x100000)
  s=b['stages'][0];self.assertEqual(s['before_sha256'],b['factory_sha256']);self.assertEqual(s['after_sha256'],self.red['releases']['red-1.0-rc7'])
  self.assertEqual(s['output'],'custom-firmware/red/builds/sboy-red-1.0-rc7/DestBin.bin')
  end=0
  for offset,value in s['changes']:
   data=bytes.fromhex(value);self.assertTrue(data);self.assertGreaterEqual(offset,end);self.assertLessEqual(offset+len(data),b['size']);end=offset+len(data)
   for lo,hi in ((0,0x2400),(0x78c00,0x7f890)):
    self.assertTrue(end<=lo or offset>=hi)
 def test_unknown_input_no_outputs(self):
  for data in (bytes(0x100000),bytes(8)):
   with tempfile.TemporaryDirectory() as folder:
    with self.assertRaises(ValueError):build(data,self.bundle,Path(folder))
    self.assertEqual(list(Path(folder).iterdir()),[])
 def test_red_custom_metadata_uses_red_addresses(self):
  yellow=json.loads((ROOT/'profiles/ax3295b-yellow-a.json').read_text());data=bytearray(0x100000)
  data[0xbde9d:0xbdea9]=b'SBOY-B-1.6\0\0';data[0x64b72:0x64b80]=b'20260704-V3.0\0'
  result=read_metadata(data,self.red['releases']['red-1.0-rc7'],yellow,self.red)
  self.assertEqual(result['variant'],'red-b');self.assertEqual(result['update_identity'],'SBOY-B-1.6');self.assertIsNone(result['build_time'])
 def test_13_unique_labels_and_separate_families(self):
  self.assertEqual(len(set(self.red['labels'])),13)
  self.assertNotIn('РАЗРЫВ',self.red['labels']);self.assertNotIn('РИЗО',self.red['labels'])
  yellow=json.loads((ROOT/'patches/sboy-0.9.json').read_text());self.assertNotEqual(yellow['factory_sha256'],self.bundle['factory_sha256']);self.assertNotEqual(yellow['profile'],self.bundle['profile'])
if __name__=='__main__':unittest.main()
