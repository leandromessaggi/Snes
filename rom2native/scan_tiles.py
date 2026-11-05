#!/usr/bin/env python3
"""Heuristic scan for uncompressed SNES 2bpp/4bpp tiles. Candidates are unverified."""
import argparse
import json
from pathlib import Path
from rom2native.romtool import load_rom, rom_info, tile_pixels, png_rgb

TILES=128
AW=128
AH=64

def candidate(rom,offset,bpp):
    size=TILES*bpp*8
    if offset<0 or offset+size>len(rom) or bpp not in (2,4):
        raise ValueError("Bad tile offset or bpp")
    pixels=bytearray(AW*AH)
    agree=pairs=blanks=0
    for tile in range(TILES):
        pos=offset+tile*bpp*8
        image=tile_pixels(rom[pos:pos+bpp*8],bpp)
        if len(set(p for row in image for p in row))==1:blanks+=1
        for y in range(8):
            for x in range(8):
                v=image[y][x]
                pixels[((tile//16)*8+y)*AW+(tile%16)*8+x]=v
                if x<7:
                    agree+=v==image[y][x+1]
                    pairs+=1
                if y<7:
                    agree+=v==image[y+1][x]
                    pairs+=1
    similarity=agree/max(1,pairs)
    blank_ratio=blanks/TILES
    return {"offset":offset,"bpp":bpp,"neighbor_similarity":round(similarity,6),
            "blank_tile_ratio":round(blank_ratio,6),
            "score":round(similarity-.3*max(0,blank_ratio-.20),6)},bytes(pixels)

def ranked(rom,step=0x2000,max_results=24):
    if not (0x400<=step<=0x8000) or not (1<=max_results<=64):
        raise ValueError("Invalid scan step or limit")
    items=[]
    for offset in range(0,len(rom),step):
        for bpp in (2,4):
            if offset+TILES*bpp*8<=len(rom):
                info,_=candidate(rom,offset,bpp)
                items.append(info)
    items.sort(key=lambda x:(-x["score"],x["offset"],x["bpp"]))
    return items[:max_results]

def contact_sheet(rom,items,columns=4,enlargement=2):
    if not items or columns not in (1,2,3,4,5,6,7,8) or enlargement not in (1,2,3,4):
        raise ValueError("Invalid contact sheet")
    w=columns*(AW*enlargement+8)
    h=((len(items)+columns-1)//columns)*(AH*enlargement+8)
    rgb=bytearray(w*h*3)
    for index,info in enumerate(items):
        _,pixels=candidate(rom,info["offset"],info["bpp"])
        left=(index%columns)*(AW*enlargement+8)+4
        top=(index//columns)*(AH*enlargement+8)+4
        palette_size=(1<<info["bpp"])-1
        for y in range(AH):
            for x in range(AW):
                v=pixels[y*AW+x]*255//palette_size
                for oy in range(enlargement):
                    for ox in range(enlargement):
                        at=((top+y*enlargement+oy)*w+left+x*enlargement+ox)*3
                        rgb[at:at+3]=bytes((v,v,v))
    return png_rgb(w,h,bytes(rgb))

def run(rom_path,dest,step=0x2000,top=24):
    rom=load_rom(rom_path)
    dest=Path(dest)
    dest.mkdir(parents=True,exist_ok=True)
    results=ranked(rom,step,top)
    report={"format":"rom2native-tile-candidates-v1","rom":rom_info(rom),
            "scan_step":step,"contact_sheet":"candidate-contact.png",
            "columns":4,"candidates":results,
            "warning":"Heuristic raw byte interpretations, NOT confirmed game sprites."}
    (dest/"candidate-contact.png").write_bytes(contact_sheet(rom,results))
    (dest/"candidate-index.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    return report

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom",type=Path)
    parser.add_argument("--out",type=Path,default=Path("private-output/tile-candidates"))
    parser.add_argument("--step",type=lambda x:int(x,0),default=0x2000)
    parser.add_argument("--top",type=int,default=24)
    args=parser.parse_args()
    print(json.dumps(run(args.rom,args.out,args.step,args.top),indent=2))
