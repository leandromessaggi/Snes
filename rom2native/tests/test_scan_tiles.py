import unittest
from rom2native.scan_tiles import candidate, ranked, contact_sheet

class TileScannerTests(unittest.TestCase):
    def test_synthetic_raw_tiles(self):
        data=bytearray(0x10000)
        for tile in range(128):
            offset=tile*16
            for row in range(8):
                data[offset+row*2]=0xF0
                data[offset+row*2+1]=0x0F
        info,pixels=candidate(bytes(data),0,2)
        self.assertGreater(info["neighbor_similarity"],.9)
        self.assertLess(info["blank_tile_ratio"],.5)
        self.assertEqual(len(pixels),128*64)
        entries=ranked(bytes(data),step=0x4000,max_results=3)
        self.assertEqual(len(entries),3)
        self.assertTrue(contact_sheet(bytes(data),entries).startswith(b"\x89PNG\r\n\x1a\n"))
    def test_rejections(self):
        with self.assertRaises(ValueError):candidate(bytes(20),0,4)
        with self.assertRaises(ValueError):ranked(bytes(40000),step=1)
        with self.assertRaises(ValueError):contact_sheet(bytes(40000),[])

if __name__=="__main__":unittest.main()
