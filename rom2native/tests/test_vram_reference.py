import hashlib
import io
import json
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path
from rom2native.romtool import png_rgb
from rom2native.vram_reference import VRAM_BYTES,load_capture,render_capture,diff_vram,atlas_tile_bytes

ROM_SHA="a"*64

def capture_bytes(vram=None,rom_sha=ROM_SHA):
    if vram is None: vram=bytes(VRAM_BYTES)
    picture=png_rgb(8,8,bytes([100,150,200])*(8*8))
    h=lambda b:hashlib.sha256(b).hexdigest()
    info={
       "format":"rom2native-vram-capture-v1",
       "rom_sha256":rom_sha,
       "frame":3,"frame_width":8,"frame_height":8,
       "vram_bytes":VRAM_BYTES,"vram_sha256":h(vram),
       "frame_png_sha256":h(picture),
       "coherence":"paused_near_same_frame_not_atomic",
    }
    out=io.BytesIO()
    with zipfile.ZipFile(out,"w",compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json",json.dumps(info))
        z.writestr("vram.bin",vram)
        z.writestr("frame.png",picture)
    return out.getvalue()

class VramCaptureTests(unittest.TestCase):
    def test_read_and_reconstruct(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"capture.zip"
            path.write_bytes(capture_bytes())
            c=load_capture(path)
            self.assertEqual(len(c.vram),65536)
            preview=atlas_tile_bytes(c.vram,4,0,16)
            self.assertTrue(preview.startswith(b"\x89PNG\r\n\x1a\n"))
            self.assertEqual(struct.unpack_from(">II",preview,16),(128,8))
            output=Path(temp)/"out"
            result=render_capture(c,output,bpp=(4,),tiles_per_page=256)
            self.assertEqual(len(result["tiles"]),8)
            self.assertTrue((output/"reference-frame.png").exists())
            self.assertTrue((output/"atlas-index.json").exists())
    def test_compare_two_frames(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            a=root/"a.zip"; b=root/"b.zip"
            a.write_bytes(capture_bytes())
            changed=bytearray(VRAM_BYTES)
            changed[32]=0x8a
            changed[33]=1
            b.write_bytes(capture_bytes(changed))
            diff=diff_vram(load_capture(a),load_capture(b))
            self.assertEqual(diff["changed_bytes"],2)
            self.assertEqual(diff["changed_4bpp_tiles"],[1])
            self.assertEqual(diff["changed_2bpp_tiles"],[2])
    def test_invalid_archive_and_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"bad.zip"
            with zipfile.ZipFile(path,"w") as z:
                z.writestr("vram.bin",b"bad")
            with self.assertRaises(ValueError):load_capture(path)
            good=io.BytesIO(capture_bytes())
            with zipfile.ZipFile(good) as archive:
                info=json.loads(archive.read("manifest.json"))
                vram=archive.read("vram.bin")
                screen=archive.read("frame.png")
            info["vram_sha256"]="0"*64
            with zipfile.ZipFile(path,"w") as z:
                z.writestr("manifest.json",json.dumps(info))
                z.writestr("vram.bin",vram)
                z.writestr("frame.png",screen)
            with self.assertRaises(ValueError):load_capture(path)
    def test_bad_modes(self):
        with self.assertRaises(ValueError):atlas_tile_bytes(bytes(VRAM_BYTES),4,2048,1)
        with self.assertRaises(ValueError):atlas_tile_bytes(bytes(VRAM_BYTES),3,0,1)
if __name__=="__main__":
    unittest.main()
