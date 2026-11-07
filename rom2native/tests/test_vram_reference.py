import hashlib
import io
import json
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path
from rom2native.romtool import png_rgb
from rom2native.vram_reference import (
    VRAM_BYTES,CGRAM_BYTES,OAM_BYTES,load_capture,render_capture,diff_vram,
    atlas_tile_bytes,decode_cgram,decode_oam,palette_preview
)
ROM_SHA="a"*64

def make_capture(vram=None,rom_sha=ROM_SHA,cgram=None,oam=None,version=2):
    if vram is None: vram=bytes(VRAM_BYTES)
    if cgram is None:cgram=bytes(CGRAM_BYTES)
    if oam is None:oam=bytes(OAM_BYTES)
    picture=png_rgb(8,8,bytes([100,150,200])*64)
    h=lambda value:hashlib.sha256(value).hexdigest()
    meta={"format":"rom2native-ppu-capture-v2" if version==2 else "rom2native-vram-capture-v1",
          "rom_sha256":rom_sha,"frame":3,"frame_width":8,"frame_height":8,
          "vram_bytes":VRAM_BYTES,"vram_sha256":h(vram),"frame_png_sha256":h(picture)}
    if version==2:
        meta.update(cgram_bytes=CGRAM_BYTES,cgram_sha256=h(cgram),
                    oam_bytes=OAM_BYTES,oam_sha256=h(oam))
    dst=io.BytesIO()
    with zipfile.ZipFile(dst,"w",compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json",json.dumps(meta))
        z.writestr("vram.bin",vram)
        if version==2:
            z.writestr("cgram.bin",cgram)
            z.writestr("oam.bin",oam)
        z.writestr("frame.png",picture)
    return dst.getvalue()

class PpuCaptureTests(unittest.TestCase):
    def test_v2_read_palettes_and_oam(self):
        cgram=bytearray(CGRAM_BYTES)
        cgram[0]=31  # red (BGR555)
        cgram[2]=0xe0;cgram[3]=3 # green
        oam=bytearray(OAM_BYTES)
        oam[0]=4; oam[1]=18; oam[2]=45; oam[3]=0b11011111
        oam[512]=0b00000011 # x high and large size
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"source.zip"
            path.write_bytes(make_capture(cgram=cgram,oam=oam))
            capture=load_capture(path)
            self.assertEqual(len(capture.vram),65536)
            self.assertEqual(decode_cgram(capture.cgram)[0],(255,0,0))
            self.assertEqual(decode_cgram(capture.cgram)[1],(0,255,0))
            self.assertEqual(struct.unpack_from(">II",palette_preview(capture.cgram),16),(192,192))
            sprite=decode_oam(capture.oam)[0]
            self.assertEqual(sprite["x"],-252)
            self.assertEqual(sprite["y"],18)
            self.assertEqual(sprite["tile"],301)
            self.assertTrue(sprite["large"])
            self.assertTrue(sprite["vflip"])
            index=render_capture(capture,Path(tmp)/"out",bpp=(4,))
            self.assertEqual(len(index["tiles"]),16)  # gray+one chosen palette
            self.assertTrue((Path(tmp)/"out"/"oam-sprites.json").exists())
            self.assertTrue((Path(tmp)/"out"/"cgram-palette.png").exists())
    def test_v1_still_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"old.zip"
            path.write_bytes(make_capture(version=1))
            cap=load_capture(path)
            self.assertIsNone(cap.cgram)
            idx=render_capture(cap,Path(tmp)/"out",bpp=(4,))
            self.assertEqual(len(idx["tiles"]),8)
    def test_diff_ppu_and_integrity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            c=bytearray(CGRAM_BYTES)
            a=root/"a.zip";b=root/"b.zip"
            a.write_bytes(make_capture())
            vram=bytearray(VRAM_BYTES)
            vram[32]=10;vram[33]=12
            c[8]=31
            oam=bytearray(OAM_BYTES);oam[3]=1
            b.write_bytes(make_capture(vram=vram,cgram=c,oam=oam))
            result=diff_vram(load_capture(a),load_capture(b))
            self.assertEqual(result["changed_bytes"],2)
            self.assertEqual(result["changed_4bpp_tiles"],[1])
            self.assertEqual(result["changed_2bpp_tiles"],[2])
            self.assertEqual(result["changed_palette_entries"],[4])
            self.assertEqual(result["changed_oam_sprite_indices"],[0])
            different=root/"different.zip"
            different.write_bytes(make_capture(rom_sha="b"*64))
            with self.assertRaises(ValueError):
                diff_vram(load_capture(a),load_capture(different))
    def test_invalid_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"broken.zip"
            p.write_bytes(make_capture(version=2))
            with zipfile.ZipFile(p) as z:
                meta=json.loads(z.read("manifest.json"))
                vram=z.read("vram.bin")
                cgram=z.read("cgram.bin")
                oam=z.read("oam.bin")
                frame=z.read("frame.png")
            meta["cgram_sha256"]="0"*64
            with zipfile.ZipFile(p,"w") as z:
                for name,data in {"manifest.json":json.dumps(meta),
                                  "vram.bin":vram,"cgram.bin":cgram,"oam.bin":oam,
                                  "frame.png":frame}.items():
                    z.writestr(name,data)
            with self.assertRaises(ValueError):load_capture(p)
    def test_invalid_depth(self):
        with self.assertRaises(ValueError):atlas_tile_bytes(bytes(VRAM_BYTES),3,0,1)
        with self.assertRaises(ValueError):decode_cgram(b"short")
        with self.assertRaises(ValueError):decode_oam(b"short")

if __name__=="__main__":
    unittest.main()
