#!/usr/bin/env python3
"""ROM->asset-pack experiment. Standard-library-only, no commercial data in repo."""
import argparse
import hashlib
import json
import struct
import zlib
import zipfile
from pathlib import Path

MAX_ROM=12*1024*1024
KNOWN_SHA256="606abf536440173ae36466db360c7db6b474beb7a105c8a62bc74a54cbe1c38b"

def load_rom(path):
    path=Path(path)
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            entries=[i for i in z.infolist() if not i.is_dir() and i.filename.lower().endswith((".smc",".sfc"))]
            if len(entries)!=1:
                raise ValueError("ZIP must contain exactly one .smc or .sfc file")
            if entries[0].file_size>MAX_ROM+512:
                raise ValueError("ROM inside ZIP exceeds limit")
            with z.open(entries[0]) as stream:
                data=stream.read(MAX_ROM+514)
    else:
        with path.open("rb") as stream:
            data=stream.read(MAX_ROM+514)
    if len(data)>MAX_ROM+512:
        raise ValueError("ROM exceeds size limit")
    if len(data)%1024==512:
        data=data[512:]
    if len(data)<128*1024 or len(data)%0x8000:
        raise ValueError("Invalid bank-aligned SNES ROM")
    return data

def rom_info(data):
    if len(data)<0x7fe0:raise ValueError("Insufficient LoROM header data")
    header=data[0x7fc0:0x7fe0]
    title=header[:21].split(b"\0",1)[0].decode("ascii",errors="replace").strip()
    return {
        "sha256":hashlib.sha256(data).hexdigest(),
        "size":len(data),
        "snes_title_guess":title,
        "mapper_byte":data[0x7fd5],
        "rom_header_offset":"0x7FC0",
        "known_desert_strike_revision":hashlib.sha256(data).hexdigest()==KNOWN_SHA256,
    }

def tile_pixels(tile,bpp=4):
    if bpp not in (2,4):raise ValueError("Only 2bpp/4bpp SNES planar tiles supported")
    if len(tile)!=(8*bpp):raise ValueError("Wrong SNES tile length")
    result=[]
    for row in range(8):
        rowcolors=[]
        for x in range(8):
            index=0
            for plane in range(bpp):
                source=(plane//2)*16+row*2+(plane%2)
                index|=((tile[source]>>(7-x))&1)<<plane
            rowcolors.append(index)
        result.append(rowcolors)
    return result

def snes_palette(rom,offset,n):
    if offset is None:
        return [(round(i*255/max(1,n-1)),)*3 for i in range(n)]
    if offset<0 or offset+2*n>len(rom):
        raise ValueError("Palette offset out of ROM")
    colors=[]
    for i in range(n):
        bgr=int.from_bytes(rom[offset+2*i:offset+2*i+2],"little")
        r=bgr&31;g=(bgr>>5)&31;b=(bgr>>10)&31
        colors.append(((r*255+15)//31,(g*255+15)//31,(b*255+15)//31))
    return colors

def png_rgb(width,height,rgb):
    if width<=0 or height<=0 or len(rgb)!=width*height*3:
        raise ValueError("Invalid RGB image dimensions")
    def chunk(tag,payload):
        return struct.pack(">I",len(payload))+tag+payload+struct.pack(">I",zlib.crc32(tag+payload)&0xffffffff)
    stride=width*3
    raw=b"".join(b"\x00"+rgb[row*stride:(row+1)*stride] for row in range(height))
    return (b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",width,height,8,2,0,0,0))+
        chunk(b"IDAT",zlib.compress(raw,9))+chunk(b"IEND",b""))

def make_atlas(rom,offset,count,bpp,columns,palette_offset=None):
    if offset<0 or count<1 or count>4096 or columns<1 or columns>128:
        raise ValueError("Invalid tile extraction dimensions")
    per_tile=bpp*8
    if bpp not in (2,4) or offset+count*per_tile>len(rom):
        raise ValueError("Tile region outside ROM")
    rows=(count+columns-1)//columns
    width=columns*8;height=rows*8
    pixels=bytearray(width*height*3)
    palette=snes_palette(rom,palette_offset,1<<bpp)
    for index in range(count):
        tile=tile_pixels(rom[offset+index*per_tile:offset+(index+1)*per_tile],bpp)
        dx=(index%columns)*8;dy=(index//columns)*8
        for row in range(8):
            for x in range(8):
                target=((dy+row)*width+dx+x)*3
                pixels[target:target+3]=bytes(palette[tile[row][x]])
    return png_rgb(width,height,bytes(pixels)),(width,height)

def extract(rom,out,offset,count,bpp,columns,palette_offset=None):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    png,(width,height)=make_atlas(rom,offset,count,bpp,columns,palette_offset)
    (out/"candidate_atlas.png").write_bytes(png)
    manifest={
        "format":"rom2native-assets-v0.1",
        "rom":rom_info(rom),
        "graphics":{
            "source":"candidate, unverified uncompressed ROM bytes",
            "offset":offset,"bpp":bpp,"count":count,"columns":columns,
            "palette_offset":palette_offset,
            "atlas":"candidate_atlas.png","size":[width,height]
        },
        "warnings":["These bytes may be compressed code/data rather than game sprites.",
                    "Palette and sprite boundaries must be confirmed by reverse engineering.",
                    "No level/gameplay has been decompiled."]
    }
    (out/"manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    job={"source":"candidate_atlas.png","style":"1997 low-poly CGI prerender, detailed painted textures, dramatic but restrained lighting, bird's-eye military desert game, 4:3 perspective, coherent object silhouettes","constraints":{
        "preserve_layout":True,"same_cell_boundaries":True,"tile_size":8,
        "do_not_change_object_identity":True,"approval_required":True
    }}
    (out/"ai_jobs.json").write_text(json.dumps({"jobs":[job]},indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return manifest

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("rom",type=Path)
    ap.add_argument("--out",type=Path,default=Path("private-output"))
    ap.add_argument("--offset",type=lambda x:int(x,0),default=0x10000)
    ap.add_argument("--tiles",type=int,default=128)
    ap.add_argument("--bpp",type=int,choices=[2,4],default=4)
    ap.add_argument("--columns",type=int,default=16)
    ap.add_argument("--palette-offset",type=lambda x:int(x,0),default=None)
    ap.add_argument("--inspect",action="store_true")
    args=ap.parse_args()
    rom=load_rom(args.rom)
    if args.inspect:
        print(json.dumps(rom_info(rom),indent=2,ensure_ascii=False))
    else:
        print(json.dumps(extract(rom,args.out,args.offset,args.tiles,args.bpp,args.columns,args.palette_offset),indent=2,ensure_ascii=False))

if __name__=="__main__":
    main()
