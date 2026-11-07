#!/usr/bin/env python3
"""Reconstruct SNES OBJ sprites from *captured* VRAM, CGRAM, and OAM.

For Desert Strike (USA) SHA 606abf..., the opening-sequence OBJSEL was
determined by comparing all five user-provided PPU v2 captures against
independent screenshot masks: base=0, name-select=0, size-mode=0.
For any other ROM, these settings MUST be provided explicitly. OAM
priority/windowing and color math are not fully emulated by this tool.
No commercial pixels or ROM bytes are committed to the source repository.
"""
import argparse
import hashlib
import json
import struct
import zlib
from pathlib import Path

from rom2native.vram_reference import load_capture, decode_oam, decode_cgram
from rom2native.romtool import load_rom
from rom2native.visual_pack import make_pack

KNOWN_SHA="606abf536440173ae36466db360c7db6b474beb7a105c8a62bc74a54cbe1c38b"
# SNES OBSEL small/large dimensions (width, height), source: pinned Snes9x gfx.cpp.
SIZES=(
    ((8,8),(16,16)),((8,8),(32,32)),((8,8),(64,64)),
    ((16,16),(32,32)),((16,16),(64,64)),((32,32),(64,64)),
    ((16,32),(32,64)),((16,32),(32,32)),
)

def pack_rgba_png(width,height,pixels):
    if width<1 or height<1 or width>512 or height>512 or len(pixels)!=width*height*4:
        raise ValueError("Invalid RGBA pixels")
    def chunk(tag,payload):
        return struct.pack(">I",len(payload))+tag+payload+struct.pack(">I",zlib.crc32(tag+payload)&0xffffffff)
    stride=width*4
    scanlines=b"".join(b"\x00"+pixels[y*stride:(y+1)*stride] for y in range(height))
    return b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",width,height,8,6,0,0,0)) + \
        chunk(b"IDAT",zlib.compress(scanlines,9))+chunk(b"IEND",b"")

def tile_4bpp(vram,offset):
    """Decode exactly one 8x8 4bpp SNES planar tile (64 indices)."""
    if len(vram)!=65536:
        raise ValueError("VRAM must contain 64KiB")
    offset &= 65535
    data=vram[offset:offset+32] if offset+32<=65536 else vram[offset:]+vram[:(offset+32)%65536]
    result=bytearray(64)
    for y in range(8):
        for x in range(8):
            bit=7-x
            result[y*8+x]=sum(((data[(plane//2)*16+y*2+(plane%2)]>>bit)&1)<<plane
                              for plane in range(4))
    return bytes(result)

def obj_tile_address(name,src_x,src_y,obj_base=0,name_select=0):
    if not 0<=name<=511 or not 0<=obj_base<=65535 or not 0<=name_select<=0x6000:
        raise ValueError("Invalid OBJ tile mapping")
    low=name&255
    tx=src_x//8
    ty=src_y//8
    tile_number=((((low&0xf0)+(ty<<4))&0xf0) | (((low&0xf)+tx)&0xf))
    bank=(0x2000+name_select) if name&0x100 else 0
    return (obj_base+bank+tile_number*32)&65535

def render_obj_group(capture,palette,obj_base=0,name_select=0,size_mode=0):
    """Return PNG, screen-space bounding box, count for one observed OAM palette.

    OAM with y=226, x=226, tile=226 is a filler used in these captures.
    The resulting PNG is a standalone transparent sprite, without background.
    """
    if capture.oam is None or capture.cgram is None:
        raise ValueError("PPU capture v2 with CGRAM and OAM required")
    if palette not in range(8) or size_mode not in range(8):
        raise ValueError("Invalid palette or OBJ size mode")
    colors=decode_cgram(capture.cgram)
    objects=[o for o in decode_oam(capture.oam)
             if o["palette"]==palette and
             (o["x"],o["y"],o["tile"])!=(226,226,226)]
    if not objects:
        raise ValueError("No objects matching the requested palette")
    sw=capture.manifest["frame_width"]
    sh=capture.manifest["frame_height"]
    if sw>512 or sh>512:raise ValueError("Unsupported screen size")
    canvas=bytearray(sw*sh*4)
    cache={}
    # Higher-priority OAM slots win when object priorities are identical;
    # palette 0/4 series have uniform priority within each group.
    for obj in reversed(objects):
        width,height=SIZES[size_mode][int(obj["large"])]
        name=obj["tile"]
        for dy in range(height):
            yy=(obj["y"]+dy)&255
            if yy>=sh:continue
            sy=height-1-dy if obj["vflip"] else dy
            for dx in range(width):
                xx=obj["x"]+dx
                if not 0<=xx<sw:continue
                sx=width-1-dx if obj["hflip"] else dx
                address=obj_tile_address(name,sx,sy,obj_base,name_select)
                tile=cache.get(address)
                if tile is None:
                    tile=tile_4bpp(capture.vram,address)
                    cache[address]=tile
                index=tile[(sy%8)*8+sx%8]
                if index==0:continue  # SNES OBJ color 0 is transparent.
                color=colors[128+palette*16+index]
                off=(yy*sw+xx)*4
                canvas[off:off+4]=bytes((*color,255))
    xs=[];ys=[]
    for y in range(sh):
        for x in range(sw):
            if canvas[(y*sw+x)*4+3]:
                xs.append(x);ys.append(y)
    if not xs:
        raise ValueError("OBJ group contains no visible pixels")
    left,right=min(xs),max(xs)+1
    top,bottom=min(ys),max(ys)+1
    out=bytearray((right-left)*(bottom-top)*4)
    for y in range(top,bottom):
        source=(y*sw+left)*4
        dest=(y-top)*(right-left)*4
        out[dest:dest+(right-left)*4]=canvas[source:source+(right-left)*4]
    return pack_rgba_png(right-left,bottom-top,bytes(out)),[left,top,right,bottom],len(objects)

def resolve_objsel(capture,base,name_select,size_mode):
    """For other ROMs never pretend that OBSEL defaults are known."""
    if None not in (base,name_select,size_mode):
        return (base,name_select,size_mode),"user-supplied"
    # Capture v3 with known OBSEL register can be supported in the next step.
    if (capture.manifest["rom_sha256"]==KNOWN_SHA and
            capture.manifest.get("frame") in (2027,2244,2632,2751,3237)):
        return (0,0,0),"validated-five-captures-opening-sequence-only"
    raise ValueError("Unrecognized ROM: specify --obj-base, --name-select and --size-mode")

def export(capture_paths,outdir,obj_base=None,name_select=None,size_mode=None,rom_path=None):
    outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True)
    captures=[load_capture(p) for p in capture_paths]
    sha=captures[0].manifest["rom_sha256"]
    if any(c.manifest["rom_sha256"]!=sha for c in captures):
        raise ValueError("All captures must come from the same ROM")
    entries=[]
    for cap in sorted(captures,key=lambda c:c.manifest.get("frame",0)):
        (base,select,mode),provenance=resolve_objsel(cap,obj_base,name_select,size_mode)
        frame=cap.manifest["frame"]
        record={"frame":frame,"obj_base":base,"name_select":select,
                "size_mode":mode,"mapping_source":provenance}
        for kind,palette in (("helicopter",0),("shadow",4)):
            png,bbox,count=render_obj_group(cap,palette,base,select,mode)
            filename=f"{kind}_{frame}_from_vram.png"
            (outdir/filename).write_bytes(png)
            record[kind]={"file":filename,"bbox":bbox,
                          "width":bbox[2]-bbox[0],"height":bbox[3]-bbox[1],
                          "oam_count":count}
        entries.append(record)
    output={"format":"rom2native-reconstructed-obj-v1","rom_sha256":sha,"frames":entries,
            "warning":"Reconstructed from VRAM/CGRAM/OAM. Game color math and BG priority are not reproduced; heading identity still needs validation."}
    if rom_path:
        rom=load_rom(rom_path)
        if hashlib.sha256(rom).hexdigest()!=sha:
            raise ValueError("Supplied ROM does not match captured revision")
        if len(entries)!=1:
            raise ValueError("--rom visual-pack export requires a single capture")
        heli=entries[0]["helicopter"]
        if heli["width"]>128 or heli["height"]>128:
            raise ValueError("Sprite exceeds 128x128 limit for native-demo visual pack")
        pack=make_pack(rom,(outdir/heli["file"]).read_bytes())
        pack_name=f"ROM2Native_Original_Helicopter_Frame_{entries[0]['frame']}.zip"
        (outdir/pack_name).write_bytes(pack)
        output["native_demo_visual_pack"]=pack_name
    (outdir/"reconstruction.json").write_text(json.dumps(output,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return output

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("captures",type=Path,nargs="+")
    parser.add_argument("--out",type=Path,default=Path("private-output/obj"))
    parser.add_argument("--obj-base",type=lambda x:int(x,0))
    parser.add_argument("--name-select",type=lambda x:int(x,0))
    parser.add_argument("--size-mode",type=int,choices=range(8))
    parser.add_argument("--rom",type=Path,help="Optional local original ROM, only for 1-frame native-demo ZIP")
    args=parser.parse_args()
    result=export(args.captures,args.out,args.obj_base,args.name_select,args.size_mode,args.rom)
    print(json.dumps({"frames":len(result["frames"]),"out":str(args.out),
                      "native_demo_pack":result.get("native_demo_visual_pack")},ensure_ascii=False))

if __name__=="__main__":
    main()
