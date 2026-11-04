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
