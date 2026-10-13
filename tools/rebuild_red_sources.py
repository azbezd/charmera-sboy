#!/usr/bin/env python3
"""Reproduce red rc1..rc7 from source. Pillow required; never accesses USB."""
import argparse,importlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'custom-firmware/red/tools'))

def rebuild(factory,output_root):
 import build_red
 output_root=Path(output_root)
 previous=output_root/'sboy-red-1.0-rc1'
 build_red.build(Path(factory),previous)
 for n in range(2,8):
  module=importlib.import_module(f'build_red_rc{n}')
  module.OLD=previous
  target=output_root/f'sboy-red-1.0-rc{n}'
  # Each historic source builder checks its precise input hash. Differences in
  # image encoders or source dependencies fail closed rather than drift silently.
  module.build(target);previous=target
 result=previous/'DestBin.bin'
 expected=json.loads((ROOT/'profiles/ax3295b-red-b.json').read_text())['releases']['red-1.0-rc7']
 if build_red.sha(result.read_bytes())!=expected:raise ValueError('Source rebuild does not match published rc7')
 return result

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('factory',type=Path)
 p.add_argument('--output-root',type=Path,default=ROOT/'custom-firmware/red/builds')
 a=p.parse_args();print(rebuild(a.factory,a.output_root))
if __name__=='__main__':main()
