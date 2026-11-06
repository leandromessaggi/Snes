import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from rom2native.romtool import png_rgb
from rom2native.capture_series import analyze

def fixture(path,frame,tile,x,cgram_change=False):
    vram=bytes(65536)
    cgram=bytearray(512)
    if cgram_change:cgram[88]=0xff
    oam=bytearray(bytes([226,226,226,226])*128+bytes(32))
    oam[0:4]=bytes((x,40,tile,0x30)) # palette0, priority3
    oam[4:8]=bytes((x,80,50,0x28)) # palette4, shadow
    oam[8:12]=bytes((226,226,226,226)) # inactive slot
    image=png_rgb(8,8,bytes([0,100,100])*64)
    h=lambda b:hashlib.sha256(b).hexdigest()
    meta={
      "format":"rom2native-ppu-capture-v2",
      "rom_sha256":"f"*64,
      "frame":frame,"vram_bytes":len(vram),"vram_sha256":h(vram),
      "cgram_bytes":len(cgram),"cgram_sha256":h(cgram),
      "oam_bytes":len(oam),"oam_sha256":h(oam),
      "frame_width":8,"frame_height":8,"frame_png_sha256":h(image)
    }
    with zipfile.ZipFile(path,"w") as z:
        z.writestr("manifest.json",json.dumps(meta))
        z.writestr("vram.bin",vram)
        z.writestr("cgram.bin",cgram)
        z.writestr("oam.bin",oam)
        z.writestr("frame.png",image)

class CaptureSeriesTests(unittest.TestCase):
    def test_groups_and_order(self):
        with tempfile.TemporaryDirectory() as temp:
            paths=[Path(temp)/f"{n}.zip" for n in (12,4,8)]
            fixture(paths[0],12,98,30,cgram_change=True)
            fixture(paths[1],4,98,12)
            fixture(paths[2],8,103,22)
            report=analyze(paths)
            self.assertEqual([f["frame"] for f in report["frames"]],[4,8,12])
            self.assertEqual([f["tile_family"] for f in report["frames"]],[1,2,1])
            self.assertEqual([f["candidate_helicopter_oam_count"] for f in report["frames"]],[1,1,1])
            self.assertEqual([f["candidate_shadow_oam_count"] for f in report["frames"]],[1,1,1])
            self.assertEqual(report["changes"][1]["changed_palette_entries"],[44])
            self.assertEqual(len(report["families"]),2)
    def test_requires_multiple_v2_captures(self):
        with self.assertRaises(ValueError):analyze([])
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"one.zip"
            fixture(path,10,22,100)
            with self.assertRaises(ValueError):analyze([path])
            with self.assertRaises(ValueError):analyze([path,path])

if __name__=="__main__":
    unittest.main()
