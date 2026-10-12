#!/usr/bin/env python3
"""Reproduce the verified USB RAM/ROM dump on Ax3295B-V3.0 camera.

Usage: sudo /usr/bin/python3 dump_camera.py
Requires the camera with microSD connected. No flash write/erase or RAM payload
upload is implemented. Outputs are live memory snapshots, NOT an SPI flash image
and NOT files suitable for flashing. Physically reconnect USB if macOS fails to
restore its mass-storage driver after capture.
"""
import hashlib
import json
import os
from pathlib import Path
import sys
from datetime import datetime, timezone
from camera_usb import Camera, ProbeError, INQUIRY, SDK_TABLE, memory_cdb, validate_table

PROFILE_HELPER = 0x020420f4
PROFILE_HELPER_SHA256 = '824f550191db877f6622b62b440f2abd0bc25ddd72513f0535dc1c62af2db572'
PROFILE_CODE_HEAD_SHA256 = '733add78a35122aec6db1568d551f4d35e4d19997d3f658b65832cf08b3c6128'
# Exact known 0.5-0.9 boot wrapper (TIME parser call), not a wildcard.
PROFILE_CODE_HEAD_HASHES = {PROFILE_CODE_HEAD_SHA256, '57103be145cf98d49c25d7429bcb1a616dce6b04b97b1169c54d573107f811c7'}
RAM_BASE,RAM_SIZE = 0x02000000,0x200000
ROM_BASE,ROM_SIZE = 0x00100000,0x18000
CODE_SIZE = 0x6b000


def sha(data):return hashlib.sha256(data).hexdigest()


def read_memory(cam,address,length):
    data=bytearray()
    for off in range(0,length,64):
        data.extend(cam.read(memory_cdb(address+off),min(64,length-off)))
        if length>=32768 and off%262144==0:
            print(f'{address:#010x}: {off}/{length}',flush=True)
    if len(data)!=length:raise ProbeError('Incomplete memory read')
    return bytes(data)


def profile_check(cam):
    table=cam.read(SDK_TABLE,512)
    if cam.read(SDK_TABLE,512)!=table:raise ProbeError('SDK table not stable')
    if validate_table(table)!=PROFILE_HELPER:raise ProbeError('Camera has a different memory helper')
    cam.memory_verified=True
    if sha(read_memory(cam,PROFILE_HELPER,256))!=PROFILE_HELPER_SHA256:
        cam.memory_verified=False
        raise ProbeError('Read-helper fingerprint mismatch')
    if sha(read_memory(cam,RAM_BASE,4096)) not in PROFILE_CODE_HEAD_HASHES:
        cam.memory_verified=False
        raise ProbeError('Firmware profile fingerprint mismatch')
    return table


def main():
    base=Path(__file__).resolve().parent.parent/'camera-dumps'
    out=base/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    out.mkdir(parents=True)
    log={'started':datetime.now(timezone.utc).isoformat(),'profile':'Ax3295B-V3.0','success':False,'spi_flash_backup':False,'flash_writes':False,'ram_code_upload':False}
    cam=None;rc=1
    try:
        cam=Camera(log);cam.verify();cam.claim(detach=True)
        iq=cam.read(INQUIRY,36)
        identity=[iq[8:16].decode('ascii','replace').strip(),iq[16:32].decode('ascii','replace').strip(),iq[32:36].decode('ascii','replace').strip()]
        if identity!=['Buildwin','Media-Player','1.00']:raise ProbeError('SCSI identity mismatch')
        log['inquiry']=identity
        table=profile_check(cam);(out/'sdk-table.bin').write_bytes(table)
        rom=read_memory(cam,ROM_BASE,ROM_SIZE);(out/'boot-rom-window-96KiB.bin').write_bytes(rom)
        ram=read_memory(cam,RAM_BASE,RAM_SIZE);(out/'running-memory-2MiB.bin').write_bytes(ram)
        rom_repeat=read_memory(cam,ROM_BASE,ROM_SIZE);(out/'boot-rom-repeat.bin').write_bytes(rom_repeat)
        code_repeat=read_memory(cam,RAM_BASE,CODE_SIZE);(out/'code-repeat.bin').write_bytes(code_repeat)
        log['validation']={'rom_identical':rom==rom_repeat,'rom_compared_bytes':ROM_SIZE,'code_identical':ram[:CODE_SIZE]==code_repeat,'code_compared_bytes':CODE_SIZE}
        if not all([log['validation']['rom_identical'],log['validation']['code_identical']]):
            raise ProbeError('Repeat verification failed; preserve evidence, do not use as validated snapshot')
        log['files']={f.name:{'bytes':f.stat().st_size,'sha256':sha(f.read_bytes())} for f in out.glob('*.bin')}
        log['success']=True;rc=0
        print('SUCCESS: real RAM/ROM snapshots saved and repeated reads matched.',flush=True)
        print('These files are not an external SPI flash backup and must not be flashed.',flush=True)
    except Exception as e:
        log['error']=f'{type(e).__name__}: {e}';print(log['error'],file=sys.stderr,flush=True)
    finally:
        if cam:cam.close()
        log['finished']=datetime.now(timezone.utc).isoformat()
        (out/'manifest.json').write_text(json.dumps(log,indent=2)+'\n')
        if os.geteuid()==0 and 'SUDO_UID' in os.environ:
            uid,gid=int(os.environ['SUDO_UID']),int(os.environ['SUDO_GID'])
            for f in [base,out,*out.iterdir()]:os.chown(f,uid,gid)
        print('Output:',out,flush=True)
    return rc

if __name__=='__main__':sys.exit(main())
