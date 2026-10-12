import hashlib,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from build import apply_stage,build,sha
from identify import inspect
from camera_usb import ProbeError
from dump_spi import spi_cdb,SpiCamera
class ReleaseTests(unittest.TestCase):
    def stage(self):return {'before_sha256':sha(b'abcdef'),'after_sha256':sha(b'abXYef'),'changes':[[2,b'XY'.hex()]]}
    def test_apply_and_reject_wrong_baseline(self):
        self.assertEqual(apply_stage(b'abcdef',self.stage()),b'abXYef')
        with self.assertRaises(ValueError):apply_stage(b'abcdeg',self.stage())
    def test_malformed_patches_rejected(self):
        for changes in [[[-1,'aa']],[[6,'aa']],[[2,'aa'],[2,'bb']],[[1,'']],[[2,'aa']]]:
            s=self.stage();s['changes']=changes
            with self.assertRaises(ValueError):apply_stage(b'abcdef',s)
    def test_unknown_dump_refused_before_outputs(self):
        bundle=json.loads((ROOT/'patches/sboy-0.9.json').read_text())
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(ValueError):build(bytes(bundle['size']),bundle,Path(t))
            self.assertEqual(list(Path(t).iterdir()),[])
        self.assertFalse(inspect(bytes(0x100000))['factory_patch_compatible'])
    def test_path_escape_rejected(self):
        s=self.stage();s['output']='../outside.bin';b=dict(size=6,factory_sha256=sha(b'abcdef'),stages=[s])
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(ValueError):build(b'abcdef',b,Path(t))
    def test_spi_boundaries_and_guard(self):
        self.assertEqual(len(spi_cdb(0xfffff,1)),16)
        for offset,n in [(-1,1),(0x100000,1),(0xfffff,2),(0,513),(0,0)]:
            with self.assertRaises(ProbeError):spi_cdb(offset,n)
        with self.assertRaises(ProbeError):object.__new__(SpiCamera).read_spi(0)
    def test_release_chain(self):
        b=json.loads((ROOT/'patches/sboy-0.9.json').read_text());digest=b['factory_sha256']
        for s in b['stages']:
            self.assertEqual(s['before_sha256'],digest);digest=s['after_sha256'];end=0
            for off,value in s['changes']:
                self.assertGreaterEqual(off,end);self.assertLessEqual(off+len(bytes.fromhex(value)),b['size']);end=off+len(bytes.fromhex(value))
        self.assertEqual(digest,'3c67c73acb5d34c85da6bd28c6edfef9179c0884505eabe53e99089624cea010')
if __name__=='__main__':unittest.main()
