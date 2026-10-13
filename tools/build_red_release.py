#!/usr/bin/env python3
"""Build red B rc7 offline from its exact factory dump; no USB or card writes."""
import argparse,json
from pathlib import Path
from build import build,sha,ROOT

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('factory',type=Path)
 p.add_argument('--lcd',required=True,choices=['original-red-b-jd9850'])
 p.add_argument('--output-root',type=Path,default=ROOT)
 a=p.parse_args();bundle=json.loads((ROOT/'patches/sboy-red-1.0-rc7.json').read_text())
 dest=build(a.factory.read_bytes(),bundle,a.output_root)
 print(dest);print('SHA256',sha(dest.read_bytes()));print('Built offline. NOT installed on the camera.')
if __name__=='__main__':main()
