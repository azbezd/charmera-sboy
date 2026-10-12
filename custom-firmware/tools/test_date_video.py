import unittest,struct,random
from build_v04 import OUT,off
from date_video_patch import patches,DATE,READY,DEFER,WORKER,STATE,UI
from test_effect_kernel import Machine,reference
from effect_kernel import kernel
from sort_kernel import sorter
from preview_badge import badge
from test_sort_kernel import sorted_reference

class DateVideoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.b=(OUT/'DestBin.bin').read_bytes()
    def readcode(self,start,n):return self.b[off(start):off(start)+n]
    def test_final_generated_instructions(self):
        for a,v in patches().items():self.assertEqual(self.readcode(a,len(v)),v)
    def test_date_only_and_rtc_unchanged(self):
        # Run the native formatter with the actual replacement words, including
        # date-change dirty flags and null pointer behavior.
        data=bytearray(64);state=0x0208a63c;rtc=0x0208a654
        for year,month,day,hour,minute,sec in [(2026,10,13,3,4,5),(2028,2,29,23,59,59),(2027,1,1,0,0,0)]:
            data[1]=255;data[rtc-state:rtc-state+7]=struct.pack('<H5B',year,month,day,hour,minute,sec)
            before=bytes(data[rtc-state:rtc-state+12]);m=Machine({0x203094c:self.readcode(0x203094c,0x2b4)},[(state,data),(0x2800000,bytearray(8))])
            m.r[1]=0x2800008;m.r[3]=rtc;m.r[9]=0xf0000000;reg=m.r.copy();m.run(0x203094c,1000)
            self.assertEqual(bytes(data[4:15]),f'{year:04}/{month:02}/{day:02}'.encode()+b'\0')
            self.assertEqual(bytes(data[rtc-state:rtc-state+12]),before)
            self.assertEqual(m.r[11],0x208a640)
            for r in (1,2,9):self.assertEqual(m.r[r],reg[r])
        # Seconds advance without a new date: the date remains intact.
        data[1]=1;data[rtc-state+6]=1
        m.r[3]=rtc;m.r[9]=0xf0000000;m.run(0x203094c,2000)
        self.assertEqual(bytes(data[4:15]),b'2027/01/01\0')
    def test_capture_callback_only_schedules_work(self):
        encoder=bytearray(0x80);struct.pack_into('<I',encoder,0x48,0x2140000);struct.pack_into('<I',encoder,0x50,0x10000)
        struct.pack_into('<H',encoder,0xc,32);struct.pack_into('<H',encoder,0x10,64)
        flag=bytearray(4);stack=bytearray(64);events=[]
        code={0x2034b40:self.readcode(0x2034b40,0xc4),DEFER:self.readcode(DEFER,len(patches()[DEFER]))}
        m=Machine(code,[(STATE,encoder),(READY,flag),(0x2800000,stack)])
        m.calls={0x202aa9c:lambda m:events.append('pause_capture')}
        m.r[1]=0x2800040;m.r[9]=0xf0000000;before=m.r.copy();m.run(0x2034b40,200)
        self.assertEqual(events,['pause_capture']);self.assertEqual(flag,b'\1\0\0\0');self.assertEqual(m.r[11],1)
        for r in (1,2,9):self.assertEqual(m.r[r],before[r])
    def test_video_frame_effect_then_date_then_jpeg_and_audio(self):
        for mode in (0,1,2):
            w,h=32,4;src=bytes((i*17)%256 for i in range(w*h));uvsrc=bytes((i*7)%256 for i in range(w*h//2))
            y=bytearray(src);uv=bytearray(uvsrc);encoder=bytearray(0x80);ui=bytearray(0x80);active=bytearray([1]);flag=bytearray(b'\1\0\0\0');events=[]
            ui[0x65]=2;ui[0x69]=mode+5;encoder[2]=1
            struct.pack_into('<HH',encoder,0xc,w,h);struct.pack_into('<II',encoder,0x18,0x2100000,0x2100000+w*h);struct.pack_into('<I',encoder,0x48,0x2140000);struct.pack_into('<I',encoder,0x50,0x10000)
            blocks={**kernel(),**sorter(live=True),**badge(top=18),**patches()}
            code={a:self.readcode(a,len(v)) for a,v in blocks.items()};code[0x2018088]=self.readcode(0x2018088,0x500)
            m=Machine(code,[(STATE,encoder),(UI,ui),(0x208fb1c,active),(READY,flag),(0x2100000,y),(0x2100000+w*h,uv),(0x2800000,bytearray(256))])
            expected=sorted_reference(src,uvsrc,w,h,live=True) if mode==1 else reference(src,uvsrc,w,h,mode)
            def stamp(m):
                self.assertEqual((y,uv),expected);self.assertEqual(m.r[3],0x2100000);events.append('stamp')
            def jpeg_buffer(m):
                self.assertEqual(m.r[3:5],[0x2140000,0x2150000]);events.append('jpeg_buffer')
            m.calls={0x2020004:lambda m:events.append('flush'),0x203ac24:stamp,0x202bf60:jpeg_buffer,0x202c698:lambda m:events.append('jpeg_start'),0x201fcc8:lambda m:events.append('irq_enable'),0x20468e8:lambda m:events.append('native_av_writer')}
            m.r[1]=0x2800100;m.r[9]=0xf0000000;before=m.r.copy();m.run(WORKER,100000)
            self.assertEqual(events,['flush','stamp','jpeg_buffer','jpeg_start','irq_enable','native_av_writer']);self.assertEqual(flag,bytes(4))
            for r in (1,2,9,14,16,18,20,22,24,26,28,30):self.assertEqual(m.r[r],before[r])
            events.clear();m.run(WORKER,200000);self.assertEqual(events,['native_av_writer'])
    def test_stopped_recording_discards_stale_frame(self):
        flag=bytearray(b'\1\0\0\0');m=Machine({WORKER:self.readcode(WORKER,len(patches()[WORKER]))},[(READY,flag),(0x208fb1c,bytearray([0])),(0x2800000,bytearray(8))]);events=[]
        m.r[1]=0x2800008;m.r[9]=0xf0000000;m.calls={0x20468e8:lambda m:events.append('native_av_writer')};m.run(WORKER,100)
        self.assertEqual(flag,bytes(4));self.assertEqual(events,['native_av_writer'])
if __name__=='__main__':unittest.main()
