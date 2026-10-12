import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from identify import inspect,read_metadata


class MetadataTests(unittest.TestCase):
    profile={'factory_sha256':'yellow','releases':{'custom':'custom'},'second_sample':{'sha256':'red'}}

    def test_unknown_image_does_not_claim_yellow_metadata(self):
        data=bytearray(0x100000)
        data[0x8c030:0x8c038]=b'12:34:56'
        data[0x8c044:0x8c04f]=b'Oct 13 2026'
        result=inspect(data)
        self.assertIsNone(result['variant'])
        self.assertIsNone(result['build_time'])
        self.assertIsNone(result['build_date'])
        self.assertFalse(result['factory_patch_compatible'])

    def test_recognized_red_uses_resource_identity(self):
        data=bytearray(b'\xff'*0x100000)
        data[0xbde9d:0xbdea9]=b'AX3295B-V2.1\0'
        data[0x64b72:0x64b80]=b'20260704-V3.0\0'
        result=read_metadata(data,'red',self.profile)
        self.assertEqual(result['variant'],'red-b')
        self.assertEqual(result['update_identity'],'AX3295B-V2.1')
        self.assertEqual(result['firmware_build'],'20260704-V3.0')
        self.assertIsNone(result['build_time'])

    def test_recognized_yellow_retains_timestamp(self):
        data=bytearray(0x100000)
        data[0x8c030:0x8c038]=b'14:48:06'
        data[0x8c044:0x8c04f]=b'Oct 13 2026'
        for digest in ('yellow','custom'):
            result=read_metadata(data,digest,self.profile)
            self.assertEqual(result['build_time'],'14:48:06')
            self.assertEqual(result['build_date'],'Oct 13 2026')
            self.assertIsNone(result['update_identity'])

    def test_truncated_known_image_is_rejected(self):
        with self.assertRaises(ValueError):read_metadata(b'BLDR','red',self.profile)


if __name__=='__main__':unittest.main()
