import json
import struct
import unittest
from types import SimpleNamespace
from rom2native.obj_reconstruct import pack_rgba_png,tile_4bpp,obj_tile_address,render_obj_group,resolve_objsel

class OBJReconstructionTests(unittest.TestCase):
    def test_planar_4bpp_pixel_and_wrap(self):
        data=bytearray(65536)
        data[0]=0x80;data[1]=0x80;data[16]=0x80;data[17]=0x80
        self.assertEqual(tile_4bpp(bytes(data),0)[0],15)
        self.assertEqual(tile_4bpp(bytes(data),0)[1],0)
        self.assertEqual(obj_tile_address(0x10f,7,0,0,0),0x2000+15*32)
        self.assertEqual(obj_tile_address(0x10f,8,8,0,0),0x2000+0*32)
        self.assertEqual(obj_tile_address(0x00f,8,8,0x4000,0),0x4000)
    def test_png_rgba_structure(self):
        result=pack_rgba_png(1,1,bytes([255,0,0,255]))
        self.assertTrue(result.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertEqual(struct.unpack_from(">II",result,16),(1,1))
        self.assertEqual(result[25],6) # RGBA
    def test_exact_sprite_from_captured_vram(self):
        mem=bytearray(65536)
        # Tile #2: set red palette index 1 at the left pixel.
        mem[2*32]=0x80
        cg=bytearray(512)
        cg[(128+1)*2]=31 # OBJ pal0 index1, pure red in BGR555
        oam=bytearray(bytes([226,226,226,226])*128 + bytes(32))
        oam[0:4]=bytes([12,20,2,0x30])
        cap=SimpleNamespace(vram=bytes(mem),cgram=bytes(cg),oam=bytes(oam),
                            manifest={"frame_width":256,"frame_height":224,"rom_sha256":"a"*64})
        png,bbox,count=render_obj_group(cap,0)
        self.assertEqual(bbox,[12,20,13,21])
        self.assertEqual(count,1)
        self.assertEqual(struct.unpack_from(">II",png,16),(1,1))
        # Horizontal flip moves the pixel to the right edge.
        oam[3]|=0x40
        cap.oam=bytes(oam)
        _,bbox,_=render_obj_group(cap,0)
        self.assertEqual(bbox,[19,20,20,21])
    def test_requires_proven_parameters_for_unknown_rom(self):
        cap=SimpleNamespace(manifest={"rom_sha256":"b"*64})
        with self.assertRaises(ValueError): resolve_objsel(cap,None,None,None)
        self.assertEqual(resolve_objsel(cap,0,0,0)[0],(0,0,0))
        known=SimpleNamespace(manifest={"rom_sha256":"606abf536440173ae36466db360c7db6b474beb7a105c8a62bc74a54cbe1c38b"})
        self.assertEqual(resolve_objsel(known,None,None,None)[0],(0,0,0))

if __name__=="__main__":
    unittest.main()
