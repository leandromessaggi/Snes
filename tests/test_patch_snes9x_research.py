import unittest
from scripts.patch_snes9x_research import patch_text,CGRAM_ID,OAM_ID

SOURCE='''#include "memmap.h"
void* retro_get_memory_data(unsigned type)
{
    switch(type)
    {
        case RETRO_MEMORY_VIDEO_RAM:
        data = Memory.VRAM;
        break;
    }
}
size_t retro_get_memory_size(unsigned type)
{
    switch(type) {
        case RETRO_MEMORY_VIDEO_RAM:
            size = 64 * 1024;
            break;
    }
}
'''

class Snes9xResearchPatchTests(unittest.TestCase):
    def test_instruments_ppu_memory_without_other_changes(self):
        code=patch_text(SOURCE)
        self.assertIn('#include "ppu.h"',code)
        self.assertIn("data = PPU.CGDATA;",code)
        self.assertIn("data = PPU.OAMData;",code)
        self.assertIn("size = sizeof(PPU.CGDATA);",code)
        self.assertIn("size = sizeof(PPU.OAMData);",code)
        self.assertEqual(patch_text(code),code)
        self.assertEqual(CGRAM_ID,0x524e0001)
        self.assertEqual(OAM_ID,0x524e0002)
    def test_refuses_unrecognized_upstream(self):
        with self.assertRaises(ValueError):patch_text("void retro_get_memory_data() {}")
        with self.assertRaises(ValueError):patch_text(SOURCE.replace('data = Memory.VRAM','data = other'))
        with self.assertRaises(ValueError):patch_text("ROM2NATIVE_CGRAM_MEMORY")

if __name__=="__main__":
    unittest.main()
