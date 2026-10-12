#!/usr/bin/env python3
"""Inspect a local dump without accessing USB. A USB ID alone is not compatibility."""
import argparse,hashlib,json,re,subprocess,sys,plistlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def inspect(data):
    profile=json.loads((ROOT/'profiles/ax3295b-yellow-a.json').read_text())
    digest=hashlib.sha256(data).hexdigest();known={profile['factory_sha256']:'yellow-a factory',profile['second_sample']['sha256']:'second sample: NOT patch compatible'}
    known.update({v:k for k,v in profile['releases'].items()})
    strings=[m.group().decode('ascii') for m in re.finditer(rb'[\x20-\x7e]{6,}',data) if re.search(rb'(?i)(ax329|st7735|jd9850)',m.group())]
    return dict(bytes=len(data),sha256=digest,match=known.get(digest,'UNKNOWN: do not flash these patches'),factory_patch_compatible=digest==profile['factory_sha256'],bldr_signature=data[4:8]==b'BLDR',build_time=data[0x8c030:0x8c038].decode('ascii','replace'),build_date=data[0x8c044:0x8c04f].decode('ascii','replace'),profile_strings=strings[:30],note='Strings describe firmware configuration, not physical chip identification.')
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
