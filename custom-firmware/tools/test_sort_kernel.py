import random,unittest
from sort_kernel import sorter,SORT
from effect_kernel import kernel,SLOTS
from preview_badge import badge,bitmaps,BADGE
from test_effect_kernel import Machine,reference

def sorted_reference(y,uv,w,h,live=False):
    window=(32 if w<=640 else 256) if live else 128
    low,high=(48,464) if live else (96,416)
    y=bytearray(y);uv=bytearray(uv)
    for row in range(0,h,2):
        for start in range(0,w,window):
            blocks=[(bytes(y[row*w+x:row*w+x+2])+bytes(y[(row+1)*w+x:(row+1)*w+x+2]),bytes(uv[row//2*w+x:row//2*w+x+2])) for x in range(start,min(start+window,w),2)]
            pos=0
            while pos<len(blocks):
                if not low<=sum(blocks[pos][0][:2])<=high:pos+=1;continue
                end=pos+1
                while end<len(blocks) and low<=sum(blocks[end][0][:2])<=high:end+=1
                blocks[pos:end]=sorted(blocks[pos:end],key=lambda v:sum(v[0][:2]),reverse=bool(row&32));pos=end
            for i,(lum,chroma) in enumerate(blocks):
                x=start+i*2;y[row*w+x:row*w+x+2]=lum[:2];y[(row+1)*w+x:(row+1)*w+x+2]=lum[2:];uv[row//2*w+x:row//2*w+x+2]=chroma
    return y,uv

def execute_new(y,uv,w,h,mode):
    y=bytearray(y);uv=bytearray(uv)
    m=Machine({**kernel(),**sorter(),**badge()},[(0x2100000,y),(0x2400000,uv),(0x2800000,bytearray(40))])
    m.r[1]=0x2800028;m.r[3]=0x2100000;m.r[4]=0x2400000;m.r[5]=w;m.r[6]=h;m.r[9]=0xf0000000
    before=m.r.copy();m.run(SLOTS[mode],max(4096,w*h*2200))
    for reg in (1,2,9,10,14,16,18,20,22,24,26,28,30):assert m.r[reg]==before[reg],reg
    return y,uv,m.steps

class SortTests(unittest.TestCase):
    def test_block_sort_oracle_and_abi(self):
        rng=random.Random(931)
        for w,h in [(352,4),(352,34),(640,2),(4096,2)]:
            y=bytes(rng.randrange(256) for _ in range(w*h));uv=bytes(rng.randrange(256) for _ in range(w*h//2))
            self.assertEqual(execute_new(y,uv,w,h,1)[:2],sorted_reference(y,uv,w,h))
    def test_preview_badge_and_no_photo_watermark(self):
        for w,h in [(160,80),(96,160),(352,2)]:
            y=bytes((i*17)%256 for i in range(w*h));uv=bytes((i*7)%256 for i in range(w*h//2))
            for mode in range(3):
                if mode==1 and w>320:expected=sorted_reference(y,uv,w,h)
                else:expected=reference(y,uv,w,h,mode)
                if (w,h)==(160,80):
                    bits=bitmaps()[mode*60:(mode+1)*60]
                    for row in range(10):
                        for col in range(48):expected[0][(row+70)*w+56+col]=235 if bits[row*6+col//8]&(128>>(col%8)) else 16
                    for row in range(5):expected[1][(row+35)*w+56:(row+35)*w+104]=bytes([128])*48
                self.assertEqual(execute_new(y,uv,w,h,mode)[:2],expected)
    def test_invalid_sort_frames(self):
        for w,h in [(320,80),(352,3),(4097,2),(352,0),(352,4097)]:
            m=Machine(sorter(),[]);m.r[3]=1;m.r[4]=2;m.r[5]=w;m.r[6]=h;m.r[9]=0xf0000000;m.run(SORT,100);self.assertEqual(m.writes,0)

if __name__=='__main__':unittest.main()
