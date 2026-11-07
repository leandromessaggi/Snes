#!/usr/bin/env python3
"""Patch only the pinned Snes9x research core to expose CGRAM and OAM read-only.

This extension is intentionally not added to the native app. IDs are private
and outside the official Libretro memory enum.
"""
import argparse
from pathlib import Path

CGRAM_ID=0x524E0001
OAM_ID=0x524E0002

def patch_text(source):
    marker="ROM2NATIVE_CGRAM_MEMORY"
    if marker in source:
        if "ROM2NATIVE_OAM_MEMORY" not in source:
            raise ValueError("Partial research patch detected")
        return source
    includes='#include "memmap.h"\n'
    read_marker=("        case RETRO_MEMORY_VIDEO_RAM:\n"
                 "        data = Memory.VRAM;\n"
                 "        break;")
    size_marker=("        case RETRO_MEMORY_VIDEO_RAM:\n"
                 "            size = 64 * 1024;\n"
                 "            break;")
    for text in (includes,read_marker,size_marker):
        if source.count(text)!=1:
            raise ValueError("Pinned Snes9x source shape changed; refusing to patch")
    source=source.replace(includes,includes+'#include "ppu.h"\n'
        '#define ROM2NATIVE_CGRAM_MEMORY 0x524E0001u\n'
        '#define ROM2NATIVE_OAM_MEMORY 0x524E0002u\n',1)
    source=source.replace(read_marker,read_marker+
        "\n        case ROM2NATIVE_CGRAM_MEMORY:\n"
        "            data = PPU.CGDATA;\n"
        "            break;\n"
        "        case ROM2NATIVE_OAM_MEMORY:\n"
        "            data = PPU.OAMData;\n"
        "            break;",1)
    source=source.replace(size_marker,size_marker+
        "\n        case ROM2NATIVE_CGRAM_MEMORY:\n"
        "            size = sizeof(PPU.CGDATA);\n"
        "            break;\n"
        "        case ROM2NATIVE_OAM_MEMORY:\n"
        "            size = sizeof(PPU.OAMData);\n"
        "            break;",1)
    return source

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("libretro_cpp",type=Path)
    args=parser.parse_args()
    original=args.libretro_cpp.read_text(encoding="utf-8")
    patched=patch_text(original)
    if original!=patched:
        args.libretro_cpp.write_text(patched,encoding="utf-8")
    print("ROM2Native research extension: CGRAM 512 bytes, OAM 544 bytes")

if __name__=="__main__":
    main()
