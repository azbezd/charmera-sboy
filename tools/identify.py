#!/usr/bin/env python3
"""Inspect a local dump without accessing USB. A USB ID alone is not compatibility."""
import argparse,hashlib,json,re,subprocess,sys,plistlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def inspect(data):
    profile=json.loads((ROOT/'profiles/ax3295b-yellow-a.json').read_text())
    red=json.loads((ROOT/'profiles/ax3295b-red-b.json').read_text())
    digest=hashlib.sha256(data).hexdigest();known={profile['factory_sha256']:'yellow-a factory',profile['second_sample']['sha256']:'red-b factory: separate RED patch family'}
    known.update({v:k for k,v in profile['releases'].items()});known.update({v:k for k,v in red['releases'].items()})
    strings=[m.group().decode('ascii') for m in re.finditer(rb'[\x20-\x7e]{6,}',data) if re.search(rb'(?i)(ax329|st7735|jd9850)',m.group())]
    metadata=read_metadata(data,digest,profile,red)
    return dict(bytes=len(data),sha256=digest,match=known.get(digest,'UNKNOWN: do not flash these patches'),factory_patch_compatible=digest in (profile['factory_sha256'],red['factory_sha256']),patch_profile=('ax3295b-yellow-a' if digest==profile['factory_sha256'] else 'ax3295b-red-b' if digest==red['factory_sha256'] else None),bldr_signature=data[4:8]==b'BLDR',**metadata,profile_strings=strings[:30],note='Strings describe firmware configuration, not physical chip identification.')

def read_metadata(data,digest,profile,red_profile=None):
    """Use offsets only after recognizing the complete image, never its USB ID."""
    result=dict(variant=None,build_time=None,build_date=None,update_identity=None,firmware_build=None)
    def ascii_at(offset,length):
        field=data[offset:offset+length]
        if len(field)!=length:raise ValueError('Truncated known firmware metadata')
        return field.split(b'\0',1)[0].decode('ascii')
    if digest==profile['factory_sha256'] or digest in profile['releases'].values():
        result.update(variant='yellow-a',build_time=ascii_at(0x8c030,8),build_date=ascii_at(0x8c044,11))
    elif digest==profile['second_sample']['sha256'] or (red_profile and digest in red_profile['releases'].values()):
        # Red B compares resource 15, not the yellow build timestamp. The yellow
        # offsets fall inside unrelated binary data in this image.
        result.update(variant='red-b',update_identity=ascii_at(0xbde9d,12),firmware_build=ascii_at(0x64b72,14))
    return result
def inventory():
    if sys.platform!='darwin':raise SystemExit('USB inventory currently supports macOS only')
    tree=plistlib.loads(subprocess.check_output(['/usr/sbin/ioreg','-p','IOUSB','-l','-a']));found=[]
    def walk(node):
        if isinstance(node,list):
            for x in node:walk(x)
        elif isinstance(node,dict):
            if 'idVendor' in node and 'idProduct' in node:
                found.append(dict(vid_pid='%04x:%04x'%(node['idVendor'],node['idProduct']),name=node.get('USB Product Name',node.get('IORegistryEntryName',''))))
            walk(node.get('IORegistryEntryChildren',[]))
    walk(tree);return found
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('dump',nargs='?',type=Path);p.add_argument('--usb',action='store_true');a=p.parse_args()
    if a.usb:result=inventory()
    elif a.dump:result=inspect(a.dump.read_bytes())
    else:p.error('Provide a dump path or --usb')
    print(json.dumps(result,ensure_ascii=False,indent=2))
