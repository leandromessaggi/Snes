#!/usr/bin/env python3
"""Explore VRAM+CGRAM+OAM snapshots exported from the research APK.

Supports both the old VRAM-only v1 ZIP and the research-only PPU v2 ZIP.
CGRAM gives real SNES palette colors; OAM provides raw object attributes,
not identified game entity names or a guaranteed accurate reconstructed scene.
"""
import argparse
import hashlib
import json
import re
import struct
import zipfile
from dataclasses import dataclass
from pathlib import Path

from rom2native.romtool import png_rgb, tile_pixels

VRAM_BYTES=65536
CGRAM_BYTES=512
OAM_BYTES=544
MAX_FRAME_PNG=4*1024*1024
MAX_ZIP=5*1024*1024
FILES_V1={"manifest.json","vram.bin","frame.png"}
FILES_V2=FILES_V1|{"cgram.bin","oam.bin"}
PNG_SIG=b"\x89PNG\r\n\x1a\n"

@dataclass
class Capture:
    manifest:dict
    vram:bytes
    frame_png:bytes
    cgram:bytes|None=None
    oam:bytes|None=None

def digest(data):
    return hashlib.sha256(data).hexdigest()

def load_capture(path):
    path=Path(path)
    if not 1<=path.stat().st_size<=MAX_ZIP:
        raise ValueError("PPU capture ZIP too large")
    with zipfile.ZipFile(path) as z:
        entries=z.infolist()
        if not entries or len(entries)!=len({i.filename for i in entries}):
            raise ValueError("Duplicate ZIP entries")
        names={i.filename for i in entries}
        if names not in (FILES_V1,FILES_V2):
            raise ValueError("Unsupported capture entries")
        limits={"manifest.json":8192,"vram.bin":VRAM_BYTES,
                "cgram.bin":CGRAM_BYTES,"oam.bin":OAM_BYTES,
                "frame.png":MAX_FRAME_PNG}
        if any(i.is_dir() or i.file_size>limits[i.filename] for i in entries):
            raise ValueError("Unexpected capture entry size")
        meta=json.loads(z.read("manifest.json"))
        vram=z.read("vram.bin")
        frame=z.read("frame.png")
        cgram=z.read("cgram.bin") if "cgram.bin" in names else None
        oam=z.read("oam.bin") if "oam.bin" in names else None
    is_v2=meta.get("format")=="rom2native-ppu-capture-v2"
    if meta.get("format") not in ("rom2native-vram-capture-v1","rom2native-ppu-capture-v2"):
        raise ValueError("Unknown PPU capture format")
    if (is_v2 and names!=FILES_V2) or (not is_v2 and names!=FILES_V1):
        raise ValueError("Capture version does not match ZIP entries")
    if not isinstance(meta.get("rom_sha256"),str) or not re.fullmatch(r"[0-9a-fA-F]{64}",meta["rom_sha256"]):
        raise ValueError("Missing valid ROM SHA-256")
    if len(vram)!=VRAM_BYTES or meta.get("vram_bytes")!=VRAM_BYTES or meta.get("vram_sha256")!=digest(vram):
        raise ValueError("VRAM corruption or invalid length")
    if meta.get("frame_png_sha256")!=digest(frame):
        raise ValueError("Screenshot SHA mismatch")
    if len(frame)<24 or frame[:8]!=PNG_SIG:
        raise ValueError("Screenshot must be PNG")
    width,height=struct.unpack_from(">II",frame,16)
    if not (1<=width<=512 and 1<=height<=512) or (width,height)!=(meta.get("frame_width"),meta.get("frame_height")):
        raise ValueError("Screenshot dimensions mismatch")
    if is_v2:
        if (len(cgram)!=CGRAM_BYTES or meta.get("cgram_bytes")!=CGRAM_BYTES or
                meta.get("cgram_sha256")!=digest(cgram)):
            raise ValueError("CGRAM corruption or invalid length")
        if (len(oam)!=OAM_BYTES or meta.get("oam_bytes")!=OAM_BYTES or
                meta.get("oam_sha256")!=digest(oam)):
            raise ValueError("OAM corruption or invalid length")
    return Capture(meta,vram,frame,cgram,oam)

def decode_cgram(cgram):
    if cgram is None or len(cgram)!=CGRAM_BYTES:
        raise ValueError("256 CGRAM colors require 512 bytes")
    colors=[]
    for i in range(256):
        raw=struct.unpack_from("<H",cgram,i*2)[0]
        r=raw&31
        g=(raw>>5)&31
        b=(raw>>10)&31
        colors.append(((r*255+15)//31,(g*255+15)//31,(b*255+15)//31))
    return colors

def decode_oam(oam):
    if oam is None or len(oam)!=OAM_BYTES:
        raise ValueError("OAM must be 544 bytes")
    result=[]
    for i in range(128):
        xlow,y,tile,attrs=oam[4*i:4*i+4]
        high=(oam[512+i//4]>>(2*(i%4)))&3
        xpos=xlow|((high&1)<<8)
        if xpos>=256:xpos-=512
        result.append({
            "index":i,
            "x":xpos,"y":y,
            "tile":tile|((attrs&1)<<8),
            "palette":(attrs>>1)&7,
            "priority":(attrs>>4)&3,
            "hflip":bool(attrs&0x40),
            "vflip":bool(attrs&0x80),
            "large":bool(high&2),
        })
    return result

def palette_preview(cgram,cell=12):
    colors=decode_cgram(cgram)
    rgb=bytearray((16*cell)*(16*cell)*3)
    for index,color in enumerate(colors):
        x=(index%16)*cell
        y=(index//16)*cell
        for yy in range(y,y+cell):
            for xx in range(x,x+cell):
                at=(yy*16*cell+xx)*3
                rgb[at:at+3]=bytes(color)
    return png_rgb(16*cell,16*cell,bytes(rgb))

def atlas_tile_bytes(vram,bpp,first,count,columns=16,palette=None):
    if bpp not in (2,4) or first<0 or count<1 or columns<1 or columns>64 or \
            (first+count)*(bpp*8)>len(vram):
        raise ValueError("Tile address outside VRAM")
    if palette is not None and len(palette)!=(1<<bpp):
        raise ValueError("Incorrect palette length")
    width=columns*8
    height=((count+columns-1)//columns)*8
    rgb=bytearray(width*height*3)
    for tile in range(count):
        offset=(first+tile)*bpp*8
        indices=tile_pixels(vram[offset:offset+bpp*8],bpp)
        left=(tile%columns)*8
        top=(tile//columns)*8
        for y in range(8):
            for x in range(8):
                index=indices[y][x]
                color=palette[index] if palette is not None else (index*255//((1<<bpp)-1),)*3
                at=((top+y)*width+left+x)*3
                rgb[at:at+3]=bytes(color)
    return png_rgb(width,height,bytes(rgb))

def render_capture(capture,outdir,bpp=(2,4),tiles_per_page=256,sprite_palette=0):
    if not 1<=tiles_per_page<=512 or not 0<=sprite_palette<=7:
        raise ValueError("Invalid tile or palette selection")
    dest=Path(outdir)
    dest.mkdir(parents=True,exist_ok=True)
    (dest/"reference-frame.png").write_bytes(capture.frame_png)
    items=[]
    sprite_colors=None
    if capture.cgram is not None:
        colors=decode_cgram(capture.cgram)
        base=128+sprite_palette*16
        sprite_colors=colors[base:base+16]
        (dest/"cgram-palette.png").write_bytes(palette_preview(capture.cgram))
        (dest/"oam-sprites.json").write_text(json.dumps({
            "format":"rom2native-oam-raw-v1",
            "warning":"Object sizes and tile bank depend on PPU registers; entries are not identified game objects.",
            "sprites":decode_oam(capture.oam)
        },indent=2)+"\n",encoding="utf-8")
    for depth in bpp:
        if depth not in (2,4): raise ValueError("Unsupported planar depth")
        total=VRAM_BYTES//(depth*8)
        for first in range(0,total,tiles_per_page):
            count=min(tiles_per_page,total-first)
            title=f"vram_{depth}bpp_tiles_{first:04d}_{first+count-1:04d}"
            output=title+".png"
            (dest/output).write_bytes(atlas_tile_bytes(capture.vram,depth,first,count))
            items.append({"file":output,"bpp":depth,"first_tile":first,
                          "count":count,"vram_byte_offset":first*depth*8,
                          "mode":"grayscale"})
            if depth==4 and sprite_colors:
                colored=title+f"_sprite_palette_{sprite_palette}.png"
                (dest/colored).write_bytes(atlas_tile_bytes(
                    capture.vram,depth,first,count,palette=sprite_colors))
                items.append({"file":colored,"bpp":4,"first_tile":first,
                              "count":count,"vram_byte_offset":first*32,
                              "mode":"cgram_sprite_palette",
                              "sprite_palette":sprite_palette})
    result={"format":"rom2native-ppu-atlases-v2",
            "reference_rom_sha256":capture.manifest["rom_sha256"],
            "source_capture_format":capture.manifest["format"],
            "frame":capture.manifest.get("frame"),
            "reference_frame":"reference-frame.png",
            "palette_sheet":"cgram-palette.png" if capture.cgram else None,
            "oam_sprites":"oam-sprites.json" if capture.oam else None,
            "tiles":items,
            "warning":"CGRAM provides authentic palette values, but BG/OBJ mode and OAM tile banks remain unverified."}
    (dest/"atlas-index.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    return result

def diff_vram(before,after):
    if before.manifest["rom_sha256"]!=after.manifest["rom_sha256"]:
        raise ValueError("Cannot compare different ROM revisions")
    changed=[i for i,(a,b) in enumerate(zip(before.vram,after.vram)) if a!=b]
    result={"format":"rom2native-ppu-diff-v2",
            "rom_sha256":before.manifest["rom_sha256"],
            "changed_bytes":len(changed),
            "changed_2bpp_tiles":sorted({i//16 for i in changed}),
            "changed_4bpp_tiles":sorted({i//32 for i in changed}),
            "note":"VRAM differences indicate modified tile bytes, not necessarily movement."}
    if before.cgram is not None and after.cgram is not None:
        result["changed_palette_entries"]=[
            i for i in range(256) if before.cgram[2*i:2*i+2]!=after.cgram[2*i:2*i+2]]
    if before.oam is not None and after.oam is not None:
        first=decode_oam(before.oam)
        second=decode_oam(after.oam)
        result["changed_oam_sprite_indices"]=[
            i for i in range(128) if first[i]!=second[i]]
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture",type=Path)
    parser.add_argument("--out",type=Path,default=Path("private-output/ppu"))
    parser.add_argument("--compare",type=Path,help="A second capture to compare")
    parser.add_argument("--bpp",type=int,choices=(2,4),help="Only decode one planar depth")
    parser.add_argument("--sprite-palette",type=int,choices=range(8),metavar="0..7",
                        default=0,help="Choose one of the eight OAM sprite palettes")
    args=parser.parse_args()
    capture=load_capture(args.capture)
    output=render_capture(capture,args.out,
                          (args.bpp,) if args.bpp else (2,4),
                          sprite_palette=args.sprite_palette)
    if args.compare:
        diff=diff_vram(capture,load_capture(args.compare))
        (args.out/"vram-diff.json").write_text(json.dumps(diff,indent=2)+"\n",encoding="utf-8")
        print(json.dumps({"pages":len(output["tiles"]),
            "changed_bytes":diff["changed_bytes"],
            "changed_oam_objects":len(diff.get("changed_oam_sprite_indices",[]))},indent=2))
    else:
        print(json.dumps({"pages":len(output["tiles"]),"folder":str(args.out)},indent=2))

if __name__=="__main__":
    main()
