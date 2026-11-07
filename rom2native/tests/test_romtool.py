import hashlib
import json
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path
from rom2native.romtool import load_rom,rom_info,tile_pixels,make_atlas,extract,KNOWN_SHA256

class RomToolTests(unittest.TestCase):
    def test_header_and_zip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            rom=bytearray(0x20000);rom[0x7fc0:0x7fc4]=b"DEMO"
            (root/"x.smc").write_bytes(b"x"*512+rom)
            self.assertEqual(load_rom(root/"x.smc"),rom)
            with zipfile.ZipFile(root/"r.zip","w") as z:z.writestr("r.sfc",rom)
            self.assertEqual(load_rom(root/"r.zip"),rom)
            self.assertEqual(rom_info(rom)["snes_title_guess"],"DEMO")
    def test_planar_2bpp(self):
        tile=bytearray(16)
        tile[0]=0x80;tile[1]=0x40
        p=tile_pixels(tile,2)
        self.assertEqual(p[0][:3],[1,2,0])
    def test_planar_4bpp(self):
        tile=bytearray(32)
        tile[0]=tile[1]=tile[16]=tile[17]=0x80
        self.assertEqual(tile_pixels(tile,4)[0][0],15)
        self.assertEqual(tile_pixels(tile,4)[0][1],0)
    def test_png_and_manifest(self):
        rom=bytearray(0x20000)
        with tempfile.TemporaryDirectory() as tmp:
            png,size=make_atlas(rom,0x10000,17,4,8)
            self.assertEqual(size,(64,24))
            self.assertTrue(png.startswith(b"\x89PNG\r\n\x1a\n"))
            self.assertEqual(struct.unpack(">II",png[16:24]),(64,24))
            manifest=extract(rom,Path(tmp),0x10000,17,4,8)
            self.assertEqual(manifest["graphics"]["count"],17)
            self.assertTrue((Path(tmp)/"ai_jobs.json").exists())
    def test_bad_bounds(self):
        with self.assertRaises(ValueError):tile_pixels(b"short",4)
        with self.assertRaises(ValueError):make_atlas(bytes(0x20000),0x1fff0,10,4,8)

if __name__=="__main__":unittest.main()
