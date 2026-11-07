#!/usr/bin/env python3
"""Package a user-approved transparent helicopter PNG for ROM2Native Android.

The commercial ROM is used only to confirm identity and is never embedded.
The resulting ZIP has exactly two entries: manifest.json and helicopter.png.
"""
import argparse
import hashlib
import io
import json
import struct
import zipfile
import zlib
from pathlib import Path

from rom2native.romtool import load_rom

FORMAT="rom2native-visual-v1"
ANIMATED_FORMAT="rom2native-visual-v2"
SCENE_FORMAT="rom2native-visual-v3"
DIRECTIONS=("N","NE","E","SE","S","SW","W","NW")
MAX_PNG=2*1024*1024
MAX_PACK=5*1024*1024
SCENE_WIDTH=320
SCENE_HEIGHT=240
MAX_SIDE=128
PNG_SIGNATURE=b"\x89PNG\r\n\x1a\n"

def png_rgba_info(data,max_width=MAX_SIDE,max_height=MAX_SIDE):
    if len(data)>MAX_PNG or len(data)<57 or data[:8]!=PNG_SIGNATURE:
        raise ValueError("PNG inválido ou maior que 512 KiB")
    pos=8
    width=height=None
    idat=False
    ended=False
    while pos<len(data):
        if pos+12>len(data):raise ValueError("Chunk PNG truncado")
        size=struct.unpack_from(">I",data,pos)[0]
        if size>MAX_PNG or pos+12+size>len(data):raise ValueError("Tamanho de chunk PNG inválido")
        kind=data[pos+4:pos+8]
        payload=data[pos+8:pos+8+size]
        expected=struct.unpack_from(">I",data,pos+8+size)[0]
        if zlib.crc32(kind+payload)&0xffffffff!=expected:
            raise ValueError("CRC de chunk PNG incorreto")
        if pos==8:
            if kind!=b"IHDR" or size!=13:raise ValueError("IHDR PNG ausente")
            width,height,depth,color,comp,filter_,interlace=struct.unpack(">IIBBBBB",payload)
            if not (1<=width<=max_width and 1<=height<=max_height):
                raise ValueError("Sprite precisa ter dimensões de até 128x128")
            if (depth,color,comp,filter_,interlace)!=(8,6,0,0,0):
                raise ValueError("Sprite deve ser PNG RGBA 8 bits sem entrelaçamento")
        if kind==b"IDAT":idat=True
        if kind==b"IEND":
            if size!=0 or pos+12!=len(data):raise ValueError("PNG com dados extras")
            ended=True
            break
        pos+=12+size
    if not idat or not ended:raise ValueError("PNG sem IDAT/IEND")
    return width,height

def make_pack(rom,png,frames=1,background=None):
    if frames not in (1,8):raise ValueError("Somente 1 ou 8 quadros são suportados")
    width,height=png_rgba_info(png,max_width=MAX_SIDE*frames)
    if width%frames or not 1<=width//frames<=MAX_SIDE:
        raise ValueError("Largura do atlas não é múltipla do número de quadros")
    if background is not None:
        sw,sh=png_rgba_info(background,max_width=SCENE_WIDTH,max_height=SCENE_HEIGHT)
        if (sw,sh)!=(SCENE_WIDTH,SCENE_HEIGHT):
            raise ValueError("Background must be exactly 320x240 RGBA PNG")
    rom_digest=hashlib.sha256(rom).hexdigest()
    image_digest=hashlib.sha256(png).hexdigest()
    manifest={
        "format":SCENE_FORMAT if background is not None else FORMAT if frames==1 else ANIMATED_FORMAT,
        "rom_sha256":rom_digest,
        "asset":{
            "id":"helicopter",
            "file":"helicopter.png",
            "sha256":image_digest,
            "width":width,
            "height":height,
            "style":"cgi_ps1_prerender",
            "provenance":"user_supplied_unverified"
        }
    }
    if frames==8:
        manifest["asset"].update({
            "frames":8,"frame_width":width//8,"frame_height":height,
            "layout":"horizontal",
            "directions":list(DIRECTIONS),
        })
    if background is not None:
        manifest["scene"]={
            "id":"background", "file":"background.png",
            "sha256":hashlib.sha256(background).hexdigest(),
            "width":SCENE_WIDTH,"height":SCENE_HEIGHT,
            "purpose":"visual_demo_only_not_game_map"
        }
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=8) as archive:
        archive.writestr("manifest.json",json.dumps(manifest,sort_keys=True,indent=2)+"\n")
        archive.writestr("helicopter.png",png)
        if background is not None:
            archive.writestr("background.png",background)
    return buf.getvalue()

def inspect_pack(packed,expected_rom_sha):
    if len(packed)>MAX_PACK:raise ValueError("Visual pack larger than 5 MiB")
    with zipfile.ZipFile(io.BytesIO(packed)) as archive:
        names=archive.namelist()
        if len(names)!=len(set(names)) or set(names) not in (
            {"helicopter.png","manifest.json"},
            {"helicopter.png","manifest.json","background.png"},
        ):
            raise ValueError("Unexpected files or duplicate filenames in visual pack")
        if (archive.getinfo("manifest.json").file_size>8192 or
            archive.getinfo("helicopter.png").file_size>MAX_PNG or
            ("background.png" in names and archive.getinfo("background.png").file_size>MAX_PNG)):
            raise ValueError("Arquivo grande demais no pacote")
        manifest=json.loads(archive.read("manifest.json"))
        image=archive.read("helicopter.png")
        scene_bytes=archive.read("background.png") if "background.png" in names else None
    asset=manifest["asset"]
    fmt=manifest.get("format")
    if fmt not in (FORMAT,ANIMATED_FORMAT,SCENE_FORMAT):
        raise ValueError("Tipo de pacote incompatível")
    frames=asset.get("frames",1) if fmt==SCENE_FORMAT else 8 if fmt==ANIMATED_FORMAT else 1
    if frames not in (1,8): raise ValueError("Only one frame or eight directional frames are supported")
    w,h=png_rgba_info(image,max_width=MAX_SIDE*frames)
    if w%frames or not 1<=w//frames<=MAX_SIDE:
        raise ValueError("Dimensões do atlas inválidas")
    if fmt in (ANIMATED_FORMAT,SCENE_FORMAT) and frames==8:
        if (asset.get("frames")!=8 or asset.get("layout")!="horizontal" or
            asset.get("frame_width")!=w//8 or asset.get("frame_height")!=h or
            asset.get("directions")!=list(DIRECTIONS)):
            raise ValueError("Metadados de animação incompatíveis")
    if (fmt==FORMAT or (fmt==SCENE_FORMAT and frames==1)) and "frames" in asset and asset["frames"]!=1:
        raise ValueError("Versão v1 só aceita um quadro")
    if manifest.get("rom_sha256")!=expected_rom_sha:
        raise ValueError("Tipo de pacote ou ROM incompatível")
    if asset.get("id")!="helicopter" or asset.get("file")!="helicopter.png":
        raise ValueError("O pacote deve conter apenas o helicóptero")
    if asset.get("width")!=w or asset.get("height")!=h:
        raise ValueError("Dimensões diferentes do manifesto")
    if asset.get("sha256")!=hashlib.sha256(image).hexdigest():
        raise ValueError("SHA-256 do sprite inválido")
    if (fmt==SCENE_FORMAT)!=(scene_bytes is not None):
        raise ValueError("Scene file and manifest version must match")
    if fmt==SCENE_FORMAT:
        scene=manifest.get("scene",{})
        if (scene.get("id")!="background" or scene.get("file")!="background.png" or
            scene.get("width")!=SCENE_WIDTH or scene.get("height")!=SCENE_HEIGHT or
            scene.get("sha256")!=hashlib.sha256(scene_bytes).hexdigest()):
            raise ValueError("Scene metadata or hash mismatch")
        if png_rgba_info(scene_bytes,max_width=SCENE_WIDTH,max_height=SCENE_HEIGHT)!=(SCENE_WIDTH,SCENE_HEIGHT):
            raise ValueError("Scene resolution mismatch")
    return manifest

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom",required=True,type=Path,help="Your local SMC/SFC/ZIP; not embedded")
    parser.add_argument("--sprite",required=True,type=Path,help="Approved PNG RGBA ≤128x128")
    parser.add_argument("--out",required=True,type=Path)
    parser.add_argument("--frames",type=int,choices=[1,8],default=1,help="One sprite or eight directions")
    parser.add_argument("--background",type=Path,help="Optional 320x240 RGBA scene concept PNG, produces v3")
    args=parser.parse_args()
    rom=load_rom(args.rom)
    png=args.sprite.read_bytes()
    background=args.background.read_bytes() if args.background else None
    packaged=make_pack(rom,png,frames=args.frames,background=background)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_bytes(packaged)
    info=inspect_pack(packaged,hashlib.sha256(rom).hexdigest())
    print(json.dumps({"saved":str(args.out),"bytes":len(packaged),"manifest":info},indent=2,ensure_ascii=False))

if __name__=="__main__":
    main()
