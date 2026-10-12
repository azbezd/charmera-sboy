#!/usr/bin/env python3
"""Read the supported first-camera SPI twice using fingerprinted resident code (macOS)."""
import argparse, re, sys
import camera_usb, dump_spi
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--disk',required=True,help='Whole Buildwin disk from diskutil, e.g. disk4; never a partition')
    p.add_argument('--card-bytes',required=True,type=int,help='Exact whole-card size from diskutil info')
    a=p.parse_args()
    if sys.platform!='darwin':p.error('This USB capture implementation supports macOS only')
    if not re.fullmatch(r'disk[0-9]+',a.disk) or a.card_bytes<=0:p.error('Invalid whole disk or capacity')
    camera_usb.CARD_DEVICE=a.disk;camera_usb.CARD_BYTES=a.card_bytes
    return dump_spi.main()
if __name__=='__main__':sys.exit(main())
