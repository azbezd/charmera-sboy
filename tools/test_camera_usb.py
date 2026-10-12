import importlib.util
from pathlib import Path
import struct
import unittest
spec=importlib.util.spec_from_file_location('camera_usb',Path(__file__).with_name('camera_usb.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class ProtocolTests(unittest.TestCase):
    def test_rejects_writes_and_arbitrary_pointers(self):
        for opcode in [0x2a,0x3b,0x04,0xda,0xcb,0xcd]:
            with self.assertRaises(m.ProbeError):m.cbw(bytes([opcode])+b'\0'*15,512,1)
        changed=bytearray(m.SDK_TABLE);changed[1]=0x10
        with self.assertRaises(m.ProbeError):m.cbw(bytes(changed),512,1)
        for n in [0,-1,4097]:
            with self.assertRaises(m.ProbeError):m.cbw(m.SDK_TABLE,n,1)
    def test_memory_is_blocked_until_verified(self):
        fake=object.__new__(m.Camera);fake.memory_verified=False
        with self.assertRaisesRegex(m.ProbeError,'not validated'):
            fake.read(m.memory_cdb(0x100000),64)
        for address in [0,0x10000000,0xffffffff,0x118000,0x2200000]:
            with self.assertRaises(m.ProbeError):m.cbw(m.memory_cdb(address),64,1)
    def test_table_validation_rejects_stubs(self):
        for data in [b'\x00'*512,b'\xff'*512,b'\x0a\x00'*256,b'\x00'*511]:
            with self.assertRaises(m.ProbeError):m.validate_table(data)
    def test_exact_sdk_wire_layout(self):
        packet=m.cbw(m.SDK_TABLE,512,0x12345678)
        self.assertEqual(len(packet),31)
        self.assertEqual(packet.hex(),'555342437856341200020000800010cd1801000000010000ffffffffffffff')
        self.assertEqual(struct.unpack('<I',packet[16:20])[0],0x118)
        self.assertEqual(struct.unpack('<I',packet[20:24])[0],0x100)
    def test_csw_checks(self):
        good=struct.pack('<IIIB',0x53425355,7,0,0)
        self.assertEqual(m.decode_csw(good,7,512,512)['status'],0)
        for bad in [good[:-1],struct.pack('<IIIB',0,7,0,0),struct.pack('<IIIB',0x53425355,8,0,0),struct.pack('<IIIB',0x53425355,7,512,0),struct.pack('<IIIB',0x53425355,7,0,1),struct.pack('<IIIB',0x53425355,7,0,2)]:
            with self.assertRaises(m.ProbeError):m.decode_csw(bad,7,512,512)
        with self.assertRaises(m.ProbeError):m.decode_csw(good,7,512,511)
    def test_inquiry_always_data_in(self):
        packet=m.cbw(m.INQUIRY,36,1)
        self.assertEqual(packet[12],0x80)
        self.assertEqual(packet[14],6)
    def test_early_csw_no_payload_is_rejected(self):
        fake=object.__new__(m.Camera);fake.log={};fake.tag=0
        responses=iter([b'',struct.pack('<IIIB',0x53425355,1,36,1)])
        fake.transfer=lambda *args:next(responses)
        with self.assertRaisesRegex(m.ProbeError,'Device rejected'):fake.read(m.INQUIRY,36)
    def test_short_response_is_not_saved_as_success(self):
        fake=object.__new__(m.Camera);fake.log={};fake.tag=0
        responses=iter([b'',b'X'*30,struct.pack('<IIIB',0x53425355,1,6,0)])
        fake.transfer=lambda *args:next(responses)
        with self.assertRaisesRegex(m.ProbeError,'Short read'):fake.read(m.INQUIRY,36)

if __name__=='__main__':unittest.main()
