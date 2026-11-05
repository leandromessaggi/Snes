#!/usr/bin/env python3
"""Decode captured SNES VRAM into exploratory tile atlases.

Input must be an explicitly exported VRAM reference ZIP from the research app.
Output includes actual VRAM-derived grayscale tile sheets, with NO false claim
about CGRAM palette, OAM sprite locations, map layout or decompilation.
"""
import argparse
import hashlib
import json
import struct
import zipfile
from dataclasses import dataclass
from pathlib import Path
from rom2native.romtool import png_rgb, tile_pixels

VRAM_BYTES=64*1024
MAX_FRAME_PNG=4*1024*1024
MAX_ZIP=5*1024*1024
EXPECTED_FILES={"manifest.json","vram.bin","frame.png"}
PNG_SIG=b"\x89PNG\r\n\x1a\n"

@dataclass
class Capture:
    manifest:dict
    vram:bytes
    frame_png:bytes

def digest(data):
    return hashlib.sha256(data).hexdigest()

def load_capture(path):
    path=Path(path)
    if not 1<=path.stat().st_size<=MAX_ZIP:
        raise ValueError("Capture ZIP too large")
    with zipfile.ZipFile(path) as z:
        infos=z.infolist()
        if len(infos)!=3 or {i.filename for i in infos}!=EXPECTED_FILES:
            raise ValueError("Expected manifest.json, vram.bin and frame.png, once each")
        for info in infos:
            if info.is_dir() or info.file_size>(VRAM_BYTES if info.filename=="vram.bin" else
                MAX_FRAME_PNG if info.filename=="frame.png" else 8192):
                raise ValueError("Invalid ZIP entry size")
        manifest=json.loads(z.read("manifest.json"))
        vram=z.read("vram.bin")
        frame=z.read("frame.png")
    if manifest.get("format")!="rom2native-vram-capture-v1":
        raise ValueError("Unknown capture format")
    sha=manifest.get("rom_sha256")
    if not isinstance(sha,str) or len(sha)!=64:
        raise ValueError("ROM SHA-256 missing")
    if len(vram)!=VRAM_BYTES or manifest.get("vram_bytes")!=VRAM_BYTES or \
            manifest.get("vram_sha256")!=digest(vram):
        raise ValueError("VRAM snapshot malformed or corrupted")
    if manifest.get("frame_png_sha256")!=digest(frame):
        raise ValueError("Screenshot hash mismatch")
    if len(frame)<24 or frame[:8]!=PNG_SIG:
        raise ValueError("Frame is not PNG")
    width,height=struct.unpack_from(">II",frame,16)
    if not (1<=width<=512 and 1<=height<=512) or \
            [width,height]!=[manifest.get("frame_width"),manifest.get("frame_height")]:
        raise ValueError("Screenshot dimensions inconsistent")
    return Capture(manifest,vram,frame)

def atlas_tile_bytes(vram,bpp,first,count,columns=16):
    per_tile=bpp*8
    if bpp not in (2,4) or first<0 or count<1 or columns<1 or columns>64 or \
        (first+count)*per_tile>len(vram):
        raise ValueError("Tile region out of VRAM")
    width=columns*8
    height=((count+columns-1)//columns)*8
    rgb=bytearray(width*height*3)
    for tile in range(count):
        start=(first+tile)*per_tile
        indices=tile_pixels(vram[start:start+per_tile],bpp)
        left=(tile%columns)*8
        top=(tile//columns)*8
        for y in range(8):
            for x in range(8):
                value=indices[y][x]*255//((1<<bpp)-1)
                offset=((top+y)*width+left+x)*3
                rgb[offset:offset+3]=bytes((value,value,value))
    return png_rgb(width,height,bytes(rgb))

def render_capture(capture,outdir,bpp=(2,4),tiles_per_page=256):
    if not 1<=tiles_per_page<=512:
        raise ValueError("Invalid tile count per page")
    dest=Path(outdir)
    dest.mkdir(parents=True,exist_ok=True)
    (dest/"reference-frame.png").write_bytes(capture.frame_png)
    images=[]
    for depth in bpp:
        if depth not in (2,4): raise ValueError("Unknown tile format")
        total=VRAM_BYTES//(depth*8)
        for first in range(0,total,tiles_per_page):
            count=min(tiles_per_page,total-first)
            png=atlas_tile_bytes(capture.vram,depth,first,count)
            filename=f"vram_{depth}bpp_tiles_{first:04d}_{first+count-1:04d}.png"
            (dest/filename).write_bytes(png)
            images.append({"file":filename,"bpp":depth,"first_tile":first,
                           "count":count,"vram_byte_offset":first*depth*8})
    index={"format":"rom2native-vram-atlases-v1",
           "reference_rom_sha256":capture.manifest["rom_sha256"],
           "frame":capture.manifest.get("frame"),
           "reference_frame":"reference-frame.png",
           "tiles":images,
           "warning":"Raw VRAM interpreted as 2/4bpp; graphics mode, palette, OAM and tilemap not yet identified."}
    (dest/"atlas-index.json").write_text(json.dumps(index,indent=2)+"\n",encoding="utf-8")
    return index

def diff_vram(before,after):
    if before.manifest["rom_sha256"]!=after.manifest["rom_sha256"]:
        raise ValueError("Cannot compare captures from different ROM revisions")
    changed=[i for i,(a,b) in enumerate(zip(before.vram,after.vram)) if a!=b]
    return {"format":"rom2native-vram-diff-v1",
            "rom_sha256":before.manifest["rom_sha256"],
            "changed_bytes":len(changed),
            "changed_2bpp_tiles":sorted({i//16 for i in changed}),
            "changed_4bpp_tiles":sorted({i//32 for i in changed}),
            "note":"Changes identify rewritten VRAM regions, not necessarily moving sprites."}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture",type=Path)
    parser.add_argument("--out",type=Path,default=Path("private-output/vram"))
    parser.add_argument("--compare",type=Path,help="A second VRAM export to compare")
    parser.add_argument("--bpp",type=int,choices=(2,4),help="Decode only one planar mode")
    args=parser.parse_args()
    first=load_capture(args.capture)
    report=render_capture(first,args.out,(args.bpp,) if args.bpp else (2,4))
    if args.compare:
        next_frame=load_capture(args.compare)
        diff=diff_vram(first,next_frame)
        (args.out/"vram-diff.json").write_text(json.dumps(diff,indent=2)+"\n",encoding="utf-8")
        print(json.dumps({"atlases":len(report["tiles"]),"changed_bytes":diff["changed_bytes"],
                          "changed_4bpp_tiles":len(diff["changed_4bpp_tiles"])},indent=2))
    else:
        print(json.dumps({"atlases":len(report["tiles"]),"out":str(args.out)},indent=2))

if __name__=="__main__":
    main()
