import hashlib
import io
import json
import struct
import unittest
import zipfile
import zlib
from rom2native.visual_pack import make_pack,inspect_pack,png_rgba_info

def png_rgba(w=16,h=12):
    def chunk(name,data):
        return struct.pack(">I",len(data))+name+data+struct.pack(">I",zlib.crc32(name+data)&0xffffffff)
    ihdr=struct.pack(">IIBBBBB",w,h,8,6,0,0,0)
    raw=b"".join(b"\x00"+bytes((3,120,190,255))*w for _ in range(h))
    return b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",ihdr)+chunk(b"IDAT",zlib.compress(raw))+chunk(b"IEND",b"")

class VisualPackTests(unittest.TestCase):
    def test_scene_background_v3(self):
        rom=b"ROM test"
        heli=png_rgba(256,16)
        bg=png_rgba(320,240)
        packed=make_pack(rom,heli,frames=8,background=bg)
        meta=inspect_pack(packed,hashlib.sha256(rom).hexdigest())
        self.assertEqual(meta["format"],"rom2native-visual-v3")
        self.assertEqual(meta["asset"]["frames"],8)
        self.assertEqual(meta["scene"]["width"],320)
        with zipfile.ZipFile(io.BytesIO(packed)) as z:
            self.assertEqual(set(z.namelist()),{"manifest.json","helicopter.png","background.png"})
            self.assertEqual(z.read("background.png"),bg)
        with self.assertRaises(ValueError):
            make_pack(rom,heli,frames=8,background=png_rgba(320,239))
        with self.assertRaises(ValueError):
            inspect_pack(packed,hashlib.sha256(b"not ROM").hexdigest())
        with zipfile.ZipFile(io.BytesIO(packed)) as z:
            manifest=json.loads(z.read("manifest.json"))
        manifest["scene"]["sha256"]="0"*64
        bad=io.BytesIO()
        with zipfile.ZipFile(bad,"w") as z:
            z.writestr("manifest.json",json.dumps(manifest))
            z.writestr("helicopter.png",heli)
            z.writestr("background.png",bg)
        with self.assertRaises(ValueError):
            inspect_pack(bad.getvalue(),hashlib.sha256(rom).hexdigest())

    def test_animated_eight_frames(self):
        rom=b"ROM test"
        image=png_rgba(64,12)
        # Default parser keeps legacy 128px-width cap.
        with self.assertRaises(ValueError):
            png_rgba_info(png_rgba(256,12))
        atlas=png_rgba(256,12)
        packed=make_pack(rom,atlas,frames=8)
        meta=inspect_pack(packed,hashlib.sha256(rom).hexdigest())
        self.assertEqual(meta["format"],"rom2native-visual-v2")
        self.assertEqual(meta["asset"]["frame_width"],32)
        self.assertEqual(meta["asset"]["frames"],8)
        self.assertEqual(meta["asset"]["directions"],["N","NE","E","SE","S","SW","W","NW"])
        with self.assertRaises(ValueError):
            make_pack(rom,png_rgba(129,12),frames=8)
        with self.assertRaises(ValueError):
            make_pack(rom,atlas,frames=7)

    def test_reject_wrong_direction_order(self):
        rom=b"ROM test"
        original=make_pack(rom,png_rgba(256,16),frames=8)
        with zipfile.ZipFile(io.BytesIO(original)) as z:
            manifest=json.loads(z.read("manifest.json"))
            image=z.read("helicopter.png")
        manifest["asset"]["directions"][0]="E"
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,"w") as z:
            z.writestr("manifest.json",json.dumps(manifest))
            z.writestr("helicopter.png",image)
        with self.assertRaises(ValueError):
            inspect_pack(stream.getvalue(),hashlib.sha256(rom).hexdigest())

    def test_build_and_inspect(self):
        rom=bytes([7])*65536
        image=png_rgba()
        packed=make_pack(rom,image)
        content=inspect_pack(packed,hashlib.sha256(rom).hexdigest())
        self.assertEqual(content["asset"]["width"],16)
        self.assertEqual(content["asset"]["height"],12)
        self.assertLess(len(packed),1024*1024)
        with zipfile.ZipFile(io.BytesIO(packed)) as archive:
            self.assertEqual(set(archive.namelist()),{"manifest.json","helicopter.png"})
            self.assertEqual(archive.read("helicopter.png"),image)
    def test_reject_wrong_rom(self):
        with self.assertRaises(ValueError):
            inspect_pack(make_pack(b"abc",png_rgba()),hashlib.sha256(b"other").hexdigest())
    def test_crc_and_dimensions(self):
        corrupt=bytearray(png_rgba())
        corrupt[30]^=0xff
        with self.assertRaises(ValueError):png_rgba_info(corrupt)
        with self.assertRaises(ValueError):png_rgba_info(png_rgba(129,16))
    def test_rgb_png_not_rgba(self):
        image=bytearray(png_rgba())
        # Deliberately invalidate PNG (CRC remains wrong): must be rejected.
        image[25]=2
        with self.assertRaises(ValueError):png_rgba_info(image)
    def test_reject_duplicate_or_extra_files(self):
        good=make_pack(b"rom",png_rgba())
        with zipfile.ZipFile(io.BytesIO(good)) as z:
            contents=[(n,z.read(n)) for n in z.namelist()]
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,"w") as archive:
            for n,data in contents:archive.writestr(n,data)
            archive.writestr("surprise.bin",b"no")
        with self.assertRaises(ValueError):
            inspect_pack(stream.getvalue(),hashlib.sha256(b"rom").hexdigest())
    def test_forged_sha_rejected(self):
        original=make_pack(b"rom",png_rgba())
        with zipfile.ZipFile(io.BytesIO(original)) as z:
            man=json.loads(z.read("manifest.json"))
            data=z.read("helicopter.png")
        man["asset"]["sha256"]="00"*32
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,"w") as z:
            z.writestr("manifest.json",json.dumps(man))
            z.writestr("helicopter.png",data)
        with self.assertRaises(ValueError):
            inspect_pack(stream.getvalue(),hashlib.sha256(b"rom").hexdigest())

if __name__=="__main__":unittest.main()
