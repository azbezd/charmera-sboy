import struct, unittest
from mode_hook import patches, SETTER, HOOK, STATE, ORIGINAL_WORD
from test_effect_kernel import Machine

class ModeHookTests(unittest.TestCase):
    def test_all_modes_and_previous_categories(self):
        # Stop precisely at the native setter continuation and inspect ABI.
        for mode in (0,1,2,3,4,5,255,256,257):
            for category in range(4):
                state=bytearray([0xa7]*0x70);state[0x65]=category
                stack=bytearray(16)
                m=Machine(patches(),[(STATE,state),(0x2800000,stack)])
                m.r[1]=0x2800010;m.r[3]=mode;m.r[9]=SETTER+4
                before=m.r.copy();m.run(SETTER,100)
                custom=1<=(mode&255)<=3
                self.assertEqual(m.r[3],0 if custom else mode)
                self.assertEqual(state[0x65],2 if custom else (0 if category==2 else category))
                self.assertEqual(state[0x69],(mode&255)+4 if custom else 0xa7)
                self.assertEqual(state[0x64],1 if custom else 0xa7)
                self.assertEqual(int.from_bytes(stack[4:8],'little'),before[2])
                for r in range(32):
                    if r not in (3,11,12,13):self.assertEqual(m.r[r],before[r])
                for i,v in enumerate(state):
                    if i not in (0x64,0x65,0x69):self.assertEqual(v,0xa7)
    def test_displaced_word_is_replayed(self):
        self.assertEqual(struct.unpack_from('<I',patches()[HOOK])[0],ORIGINAL_WORD)

if __name__=='__main__':unittest.main()
