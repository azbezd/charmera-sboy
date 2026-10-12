#!/usr/bin/env python3
"""Read GD25Q80C using the camera's resident SPI READ (03h) wrapper.

Only for the fingerprinted Ax3295B-V3.0 firmware. No uploaded code,
flash writes, erase, or general callback interface. All payload transfers are IN.
"""
import json, os, struct, sys
from pathlib import Path
from datetime import datetime, timezone
from camera_usb import Camera, ProbeError, INQUIRY, EP_IN, EP_OUT, decode_csw
from dump_camera import profile_check, read_memory, sha

SIZE = 0x100000
WRAPPER = 0x02040078
FINGERPRINTS = [
    (WRAPPER, 0x34, 'dfe8945abb160d3d23a85ead685985d2b85c8d0356ecf35955bc6a3ca5709476'),
    (0x02032104, 0x2bc, 'e696378ce82f3c7fe6c5f5cf9b83a2df2ea412162685af4b95868dad367015e7'),
    (0x02022c74, 0x250, '3e2c2cb03700e445b1a9904f015f4967ef510bec4813fcd0ebcf142ccafb0cb4'),
]

def spi_cdb(offset, size):
    if not isinstance(offset,int) or not isinstance(size,int) or not (0 <= offset < SIZE and 1 <= size <= 512 and offset+size <= SIZE):
        raise ProbeError('SPI read outside flash or USB TX buffer')
    return b'\xcd' + struct.pack('<III', 0x118, 0xffffffff, WRAPPER) + offset.to_bytes(3,'little')

class SpiCamera(Camera):
    spi_verified = False
    def check_spi(self):
        profile_check(self)
        for address,size,digest in FINGERPRINTS:
            if sha(read_memory(self,address,size)) != digest:
                raise ProbeError(f'SPI function fingerprint mismatch at {address:#x}')
        pointers=struct.unpack('<II',read_memory(self,0x0208fa84,8))
        if pointers != (0x8040,0x8250):
            raise ProbeError(f'Unexpected USB buffer layout: {pointers}')
        self.spi_verified=True

    def read_spi(self,offset,size=512):
        if not self.spi_verified: raise ProbeError('SPI profile has not been verified')
        cdb=spi_cdb(offset,size)
        self.tag+=1
        request={'cdb':cdb.hex(),'flash_offset':offset,'length':size,'direction':'IN'}
        self.log.setdefault('commands',[]).append(request)
        packet=struct.pack('<IIIBBB',0x43425355,self.tag,size,0x80,0,16)+cdb
        self.transfer(EP_OUT,packet)
        data=self.transfer(EP_IN,size)
        if len(data)==13 and data[:4]==b'USBS':
            decode_csw(data,self.tag,size,0)
            raise ProbeError('No SPI data returned')
        request['csw']=decode_csw(self.transfer(EP_IN,13),self.tag,size,len(data))
        request['sha256']=sha(data)
        return data

def main():
    out=Path(__file__).resolve().parents[1]/'camera-dumps'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-spi')
    out.mkdir(parents=True)
    log={'profile':'Ax3295B-V3.0','flash_size':SIZE,'flash_writes':False,'ram_code_upload':False,'success':False}
    cam=None;rc=1
    try:
        cam=SpiCamera(log);cam.verify();cam.claim(True)
        iq=cam.read(INQUIRY,36)
        if [iq[8:16].strip(),iq[16:32].strip(),iq[32:36].strip()] != [b'Buildwin',b'Media-Player',b'1.00']:
            raise ProbeError('SCSI identity mismatch')
        cam.check_spi()
        head=cam.read_spi(0,64)
        (out/'flash-header.bin').write_bytes(head)
        print('Flash header:',head.hex(),flush=True)
        if head[4:8]!=b'BLDR' or cam.read_spi(0,64)!=head:
            raise ProbeError('Flash header signature or repeat mismatch')
        for name in ['spi-flash-1MiB.bin','spi-flash-repeat.bin']:
            with (out/name).open('wb') as f:
                for off in range(0,SIZE,512):
                    f.write(cam.read_spi(off,512))
                    if off%0x20000==0: print(name,hex(off),'/',hex(SIZE),flush=True)
            print(name,sha((out/name).read_bytes()),flush=True)
        first=(out/'spi-flash-1MiB.bin').read_bytes()
        second=(out/'spi-flash-repeat.bin').read_bytes()
        log['repeat_identical']=first==second
        if first!=second or first[:64]!=head: raise ProbeError('Full flash verification failed')
        log['success']=True;rc=0
        print('SUCCESS: full 1 MiB SPI flash read twice, identical.',flush=True)
        print('Output:',out,flush=True)
        if '--hold' in sys.argv:
            print('HOLD: read HEX_ADDRESS DECIMAL_LENGTH or quit',flush=True)
            for line in sys.stdin:
                parts=line.strip().split()
                if parts==['quit']: break
                if len(parts)==3 and parts[0]=='read':
                    address,length=int(parts[1],16),int(parts[2])
                    if not 1<=length<=0x200000: raise ProbeError('Read length rejected')
                    data=read_memory(cam,address,length)
                    dest=out/f'memory-{address:08x}-{length:x}.bin'
                    with dest.open('xb') as f:f.write(data)
                    print('READ',dest,sha(data),flush=True)
                else:print('Expected read HEX_ADDRESS DECIMAL_LENGTH or quit',flush=True)
    except Exception as e:
        log['error']=f'{type(e).__name__}: {e}';print(log['error'],flush=True)
    finally:
        if cam:cam.close()
        log['files']={f.name:{'bytes':f.stat().st_size,'sha256':sha(f.read_bytes())} for f in out.glob('*.bin')}
        (out/'manifest.json').write_text(json.dumps(log,indent=2)+'\n')
        if os.geteuid()==0 and 'SUDO_UID' in os.environ:
            for f in [out,*out.iterdir()]:os.chown(f,int(os.environ['SUDO_UID']),int(os.environ['SUDO_GID']))
        print('Output:',out,flush=True)
    return rc

if __name__=='__main__':sys.exit(main())
