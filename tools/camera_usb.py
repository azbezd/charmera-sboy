#!/usr/bin/env python3
"""Bounded USB diagnostics for camera, using libusb on macOS.

Default: only USB descriptors + standard SCSI INQUIRY.
--sdk-table: additionally try ONE documented AX327X/AX328X SDK debug read
            (0xCD, helper 0x118, 512 bytes at 0x100). This profile is experimental
            on this board and may hang it; it is not a validated firmware dumper.
No data-out payloads, flash writes, erase, loader entry or arbitrary execution API.
See docs/protocol.md for protocol sources and limits.
"""
import argparse
import ctypes as C
import ctypes.util
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import plistlib
import struct
import subprocess
import sys

VID, PID, INTERFACE, EP_IN, EP_OUT = 0x0219, 0x3280, 4, 0x81, 0x01
INQUIRY = bytes.fromhex('120000002400')
SDK_TABLE = bytes.fromhex('cd1801000000010000ffffffffffffff')
LIBRARY = C.util.find_library('usb-1.0') or '/opt/homebrew/opt/libusb/lib/libusb-1.0.dylib'
CARD_DEVICE = None
CARD_BYTES = None

class ProbeError(Exception):
    pass


def decode_csw(raw, tag, requested, received):
    if len(raw) != 13:
        raise ProbeError(f'Invalid CSW length: {len(raw)}')
    magic, response_tag, residue, status = struct.unpack('<IIIB', raw)
    if magic != 0x53425355 or response_tag != tag:
        raise ProbeError('CSW signature/tag mismatch')
    if status not in (0, 1, 2) or residue > requested:
        raise ProbeError('Invalid CSW status/residue')
    if status != 0:
        raise ProbeError(f'Device rejected command: CSW status={status}, residue={residue}')
    if residue != 0 or received != requested:
        raise ProbeError(f'Short read: received={received}, requested={requested}, residue={residue}')
    return {'tag': tag, 'residue': residue, 'status': status}


def memory_cdb(address):
    return b'\xcd' + struct.pack('<III', 0x118, address, 0xffffffff) + b'\xff\xff\xff'


def allowed(cdb, size):
    if cdb == INQUIRY and size == 36: return True
    if cdb == SDK_TABLE and size == 512: return True
    # Used only after a real SDK jump table has been validated in this process.
    if len(cdb) != 16 or not 1 <= size <= 4096: return False
    address = struct.unpack_from('<I', cdb, 5)[0]
    in_memory = any(lo <= address and address + size <= hi for lo,hi in
                    [(0x100,0x8000),(0x100000,0x118000),(0x2000000,0x2200000)])
    return in_memory and cdb == memory_cdb(address)


def validate_table(data):
    if len(data)!=512: raise ProbeError('Short SDK table')
    # The fixed read entry at 0x118 must be an OpenRISC relative jump.
    word = struct.unpack_from('<I', data, 0x18)[0]
    if word >> 26 != 0: raise ProbeError('Read entry is not an OpenRISC jump; memory profile unverified')
    rel = word & 0x3ffffff
    if rel & 0x2000000: rel -= 0x4000000
    target = (0x118 + rel*4) & 0xffffffff
    if not any(lo <= target < hi for lo,hi in [(0x200,0x8000),(0x100000,0x118000),(0x2000000,0x2200000)]):
        raise ProbeError(f'Implausible SDK read jump target: {target:#x}')
    return target


def cbw(cdb, size, tag):
    if not allowed(cdb, size):
        raise ProbeError('Command rejected by strict allowlist')
    return struct.pack('<IIIBBB', 0x43425355, tag, size, 0x80, 0, len(cdb)) + cdb.ljust(16, b'\0')


def camera_disk():
    """Locate only the already-observed external camera card; do not guess disk number."""
    tree = plistlib.loads(subprocess.check_output(['/usr/sbin/ioreg', '-r', '-c', 'IOSCSIPeripheralDeviceNub', '-l', '-a']))
    matches = []
    def walk(n, target=False):
        if isinstance(n, list):
            for v in n: walk(v, target)
        elif isinstance(n, dict):
            target = target or (n.get('Vendor Identification') == 'Buildwin' and n.get('Product Identification') == 'Media-Player' and n.get('Product Revision Level') == '1.00')
            if target and n.get('Whole') and n.get('BSD Name'): matches.append(n['BSD Name'])
            walk(n.get('IORegistryEntryChildren', []), target)
    walk(tree)
    if len(matches) != 1: raise ProbeError(f'Expected one Buildwin card, got {matches}')
    info = plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil', 'info', '-plist', matches[0]]))
    if CARD_DEVICE is None or CARD_BYTES is None or matches[0] != CARD_DEVICE:
        raise ProbeError('Use backup.py with explicitly selected --disk and --card-bytes')
    if info.get('Internal') is not False or info.get('BusProtocol') != 'USB' or not info.get('WholeDisk') or info.get('Size') != CARD_BYTES:
        raise ProbeError('External camera card guard rejected disk')
    return matches[0]


class Camera:
    def __init__(self, log):
        self.log = log
        self.L = C.CDLL(LIBRARY)
        p = C.c_void_p
        definitions = {
            'libusb_init': ([C.POINTER(p)], C.c_int),
            'libusb_exit': ([p], None),
            'libusb_get_device_list': ([p, C.POINTER(C.POINTER(p))], C.c_ssize_t),
            'libusb_free_device_list': ([C.POINTER(p), C.c_int], None),
            'libusb_get_device_descriptor': ([p, p], C.c_int),
            'libusb_open': ([p, C.POINTER(p)], C.c_int),
            'libusb_close': ([p], None),
            'libusb_control_transfer': ([p,C.c_uint8,C.c_uint8,C.c_uint16,C.c_uint16,p,C.c_uint16,C.c_uint],C.c_int),
            'libusb_claim_interface': ([p,C.c_int],C.c_int),
            'libusb_release_interface': ([p,C.c_int],C.c_int),
            'libusb_kernel_driver_active': ([p,C.c_int],C.c_int),
            'libusb_detach_kernel_driver': ([p,C.c_int],C.c_int),
            'libusb_attach_kernel_driver': ([p,C.c_int],C.c_int),
            'libusb_bulk_transfer': ([p,C.c_ubyte,p,C.c_int,C.POINTER(C.c_int),C.c_uint],C.c_int),
            'libusb_error_name': ([C.c_int],C.c_char_p),
        }
        for name,(args,result) in definitions.items():
            f=getattr(self.L,name); f.argtypes=args; f.restype=result
        self.ctx=p();self.h=p();self.claimed=False;self.detached=False;self.tag=0;self.memory_verified=False
        self.check(self.L.libusb_init(C.byref(self.ctx)), 'initialize libusb')
        devices=C.POINTER(p)()
        count=self.L.libusb_get_device_list(self.ctx,C.byref(devices))
        self.check(count,'list devices')
        try:
            matches=[]
            for i in range(count):
                d=(C.c_ubyte*18)()
                if self.L.libusb_get_device_descriptor(devices[i],d)==0:
                    raw=bytes(d)
                    if struct.unpack_from('<HH',raw,8)==(VID,PID):matches.append(devices[i])
            if len(matches)!=1:raise ProbeError(f'Expected exactly one {VID:04x}:{PID:04x}, found {len(matches)}')
            self.check(self.L.libusb_open(matches[0],C.byref(self.h)),'open camera')
        finally:self.L.libusb_free_device_list(devices,1)

    def check(self,rc,what):
        if rc<0:raise ProbeError(f'{what}: {self.L.libusb_error_name(rc).decode()} ({rc})')
        return rc

    def descriptor(self,kind,index,length,lang=0):
        data=(C.c_ubyte*length)()
        n=self.check(self.L.libusb_control_transfer(self.h,0x80,6,(kind<<8)|index,lang,data,length,3000),'GET_DESCRIPTOR')
        return bytes(data[:n])

    def verify(self):
        d=self.descriptor(1,0,18)
        if len(d)!=18 or struct.unpack_from('<HH',d,8)!=(VID,PID):raise ProbeError('USB identity changed')
        head=self.descriptor(2,0,9)
        if len(head)!=9:raise ProbeError('Short configuration header')
        total=struct.unpack_from('<H',head,2)[0]
        if total!=32:raise ProbeError('Unexpected USB configuration size')
        cfg=self.descriptor(2,0,total)
        # Compare against recorded descriptor, including all interfaces/endpoints.
        recorded=bytes.fromhex('0902200001010080320904040002080650000705810200020107050102000201')
        if cfg!=recorded:raise ProbeError('USB configuration differs from recorded camera')
        self.log['usb']={'vid_pid':f'{VID:04x}:{PID:04x}','device_hex':d.hex(),'configuration_hex':cfg.hex()}

    def claim(self,detach):
        active=self.L.libusb_kernel_driver_active(self.h,INTERFACE)
        self.log['kernel_driver_active']=active
        if active==1 and detach:
            if os.geteuid()!=0:raise ProbeError('macOS USB capture requires administrator execution (sudo)')
            disk=camera_disk();self.log['disk']=disk
            subprocess.run(['/usr/sbin/diskutil','unmountDisk',disk],check=True)
            self.check(self.L.libusb_detach_kernel_driver(self.h,INTERFACE),'detach camera storage driver')
            self.detached=True
        self.check(self.L.libusb_claim_interface(self.h,INTERFACE),'claim interface 4')
        self.claimed=True
        self.verify()

    def transfer(self,endpoint,data_or_size):
        incoming=bool(endpoint&0x80)
        n=data_or_size if incoming else len(data_or_size)
        data=(C.c_ubyte*n)()
        if not incoming:data[:]=data_or_size
        actual=C.c_int()
        rc=self.L.libusb_bulk_transfer(self.h,endpoint,data,n,C.byref(actual),3000)
        self.check(rc,f'bulk 0x{endpoint:02x}, actual={actual.value}')
        if not incoming and actual.value!=n:raise ProbeError('Short CBW transfer')
        return bytes(data[:actual.value])

    def read(self,cdb,size):
        if cdb not in (INQUIRY,SDK_TABLE) and not self.memory_verified:
            raise ProbeError('Memory reader not validated')
        self.tag+=1
        request={'cdb':cdb.hex(),'length':size,'direction':'IN'}
        self.log.setdefault('commands',[]).append(request)
        self.transfer(EP_OUT,cbw(cdb,size,self.tag))
        data=self.transfer(EP_IN,size)
        if len(data)==13 and data[:4]==b'USBS':
            decode_csw(data,self.tag,size,0)
            raise ProbeError('Device returned CSW without payload')
        status=self.transfer(EP_IN,13)
        request['csw']=decode_csw(status,self.tag,size,len(data))
        request['sha256']=hashlib.sha256(data).hexdigest()
        return data

    def close(self):
        if self.h:
            if self.claimed:self.log['release_result']=self.L.libusb_release_interface(self.h,INTERFACE)
            if self.detached:
                self.log['reattach_result']=self.L.libusb_attach_kernel_driver(self.h,INTERFACE)
                if self.log['reattach_result']!=0:
                    self.log['reconnect_required']=True
                    print('Driver restoration failed; physically reconnect camera USB. No firmware writes were performed.',flush=True)
            self.L.libusb_close(self.h);self.h=None
        if self.ctx:self.L.libusb_exit(self.ctx);self.ctx=None


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--detach',action='store_true',help='Unmount camera card and temporarily capture USB device; requires sudo on macOS')
    ap.add_argument('--sdk-table',action='store_true',help='Experimental SDK-profile 512-byte memory read; may hang unsupported camera')
    ap.add_argument('--hold',action='store_true',help='Keep the captured interface open after success until Enter; prevents repeated detach cycles during diagnosis')
    args=ap.parse_args()
    root=Path(__file__).resolve().parent
    out=root/'runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    out.mkdir(parents=True)
    log={'started':datetime.now(timezone.utc).isoformat(),'sdk_table_requested':args.sdk_table,'success':False,'firmware_dump':False}
    cam=None;rc=1
    try:
        cam=Camera(log);cam.verify();cam.claim(args.detach)
        iq=cam.read(INQUIRY,36);(out/'inquiry.bin').write_bytes(iq)
        identity=[iq[8:16].decode('ascii','replace').strip(),iq[16:32].decode('ascii','replace').strip(),iq[32:36].decode('ascii','replace').strip()]
        log['inquiry']=identity
        print('SCSI INQUIRY:',identity,flush=True)
        if identity!=['Buildwin','Media-Player','1.00']:raise ProbeError('SCSI identity guard rejected camera')
        if args.sdk_table:
            data=cam.read(SDK_TABLE,512);(out/'sdk-table-00000100.bin').write_bytes(data)
            log['sdk_table']={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'unique_bytes':len(set(data)),'first64_hex':data[:64].hex()}
            print('SDK table received:',log['sdk_table'],flush=True)
            if len(set(data))<8:raise ProbeError('SDK response looks blank/stubbed; not a validated memory read')
        log['success']=True;rc=0
        (out/'report.json').write_text(json.dumps(log,indent=2)+'\n')
        if args.hold:
            if args.sdk_table:
                repeat=cam.read(SDK_TABLE,512)
                if repeat != data: raise ProbeError('SDK table changed between reads')
                target=validate_table(data);cam.memory_verified=True
                log['validated_sdk_read_target']=hex(target)
                print(f'SDK read entry validated: 0x118 -> {target:#x}',flush=True)
            print('Captured interface held. Commands: read HEX_ADDRESS DECIMAL_BYTES; quit. Report:',out/'report.json',flush=True)
            for line in sys.stdin:
                parts=line.strip().split()
                if not parts or parts==['quit']: break
                if len(parts)!=3 or parts[0]!='read' or not cam.memory_verified:
                    print('Rejected session command',flush=True);continue
                address=int(parts[1],0);length=int(parts[2],0)
                if length<=0 or length>0x200000: raise ProbeError('Invalid bounded read size')
                if not any(lo<=address and address+length<=hi for lo,hi in [(0x100,0x8000),(0x100000,0x118000),(0x2000000,0x2200000)]):
                    raise ProbeError('Read range outside known SRAM/ROM/SDRAM')
                dest=out/f'memory-{address:08x}-{length:x}.bin'
                if dest.exists(): raise ProbeError('Output already exists')
                partial=dest.with_suffix('.partial')
                with partial.open('xb') as f:
                    for off in range(0,length,64):
                        f.write(cam.read(memory_cdb(address+off),min(64,length-off)))
                        if off%8192==0: print(f'Read {off}/{length}',flush=True)
                partial.rename(dest)
                print('Saved memory:',dest,'SHA256',hashlib.sha256(dest.read_bytes()).hexdigest(),flush=True)
                (out/'report.json').write_text(json.dumps(log,indent=2)+'\n')
    except Exception as e:
        log['error']=f'{type(e).__name__}: {e}';print(log['error'],file=sys.stderr,flush=True)
    finally:
        if cam:cam.close()
        log['finished']=datetime.now(timezone.utc).isoformat()
        (out/'report.json').write_text(json.dumps(log,indent=2)+'\n')
        if os.geteuid()==0 and 'SUDO_UID' in os.environ:
            uid,gid=int(os.environ['SUDO_UID']),int(os.environ['SUDO_GID'])
            for f in [out.parent,out,*out.iterdir()]:os.chown(f,uid,gid)
        print('Report:',out/'report.json',flush=True)
    return rc

if __name__=='__main__':sys.exit(main())
