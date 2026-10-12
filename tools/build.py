#!/usr/bin/env python3
"""Offline, exact-factory-dump patching. Never opens USB or writes a card."""
import argparse, hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(data):return hashlib.sha256(data).hexdigest()
def apply_stage(data,stage):
    if sha(data)!=stage['before_sha256']:raise ValueError('Baseline SHA256 mismatch')
    out=bytearray(data);end=0
    for start,value in stage['changes']:
        payload=bytes.fromhex(value)
        if not isinstance(start,int) or start<end or not payload or start+len(payload)>len(data):
            raise ValueError('Patch bounds, order or overlap invalid')
        out[start:start+len(payload)]=payload;end=start+len(payload)
    if sha(out)!=stage['after_sha256']:raise ValueError('Output SHA256 mismatch')
    return bytes(out)
def build(factory,bundle,root):
    if len(factory)!=bundle['size'] or sha(factory)!=bundle['factory_sha256']:
        raise ValueError('Unsupported factory dump: no relaxed compatibility mode exists')
    root=root.resolve();data=factory;products=[]
    # Validate every stage and path before writing any output.
    for stage in bundle['stages']:
        data=apply_stage(data,stage);dest=(root/stage['output']).resolve()
        if root not in dest.parents:raise ValueError('Output escapes build directory')
        if dest.exists() and dest.read_bytes()!=data:raise ValueError('Existing output differs: '+str(dest))
        products.append((dest,data))
    for dest,data in products:
        dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists():
            with dest.open('xb') as f:f.write(data)
        if sha(dest.read_bytes())!=sha(data):raise IOError('Output readback mismatch')
    return products[-1][0]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('factory',type=Path)
    p.add_argument('--lcd',required=True,choices=['replacement-st7735'],help='Only this physically tested replacement-panel family is supported')
    p.add_argument('--output-root',type=Path,default=ROOT)
    a=p.parse_args();bundle=json.loads((ROOT/'patches/sboy-0.9.json').read_text())
    dest=build(a.factory.read_bytes(),bundle,a.output_root)
    print(dest);print('SHA256',sha(dest.read_bytes()));print('Built offline. NOT installed on the camera.')
if __name__=='__main__':main()
