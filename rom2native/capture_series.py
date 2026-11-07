#!/usr/bin/env python3
"""Compare real PPU captures by OAM palette and 4bpp tile signatures.

This extracts *candidate* helicopter/shadow OAM groups from Desert Strike's
observed opening sequence, not a general-purpose semantic object detector.
No ROM, pixel graphics, or PPU dumps are written to the report.
"""
import argparse
import json
from pathlib import Path
from rom2native.vram_reference import load_capture, decode_oam

def visible_obj(obj):
    # The observed core uses this filler entry for unused OAM slots.
    return not (obj["x"] == 226 and obj["y"] == 226 and obj["tile"] == 226)

def group_objects(capture, palette):
    if capture.oam is None:
        raise ValueError("PPU v2 capture with OAM required")
    return [ob for ob in decode_oam(capture.oam)
            if visible_obj(ob) and ob["palette"] == palette]

def tile_fingerprint(objects):
    return tuple(sorted(set(obj["tile"] for obj in objects)))

def analyze(paths):
    if len(paths) < 2:
        raise ValueError("At least two PPU v2 snapshots required")
    captures = [load_capture(path) for path in paths]
    if any(c.oam is None or c.cgram is None for c in captures):
        raise ValueError("Only PPU v2 captures with CGRAM and OAM are supported")
    original = captures[0].manifest["rom_sha256"]
    if any(c.manifest["rom_sha256"] != original for c in captures):
        raise ValueError("Captures belong to different ROM revisions")
    frames = [c.manifest.get("frame") for c in captures]
    if any(not isinstance(n, int) or n < 0 for n in frames):
        raise ValueError("Missing frame numbers")
    pairs = sorted(zip(frames,captures), key=lambda p:p[0])
    if len(set(frames)) != len(frames):
        raise ValueError("Duplicate frame counters")
    fingerprints = {}
    series = []
    for frame,capture in pairs:
        primary = group_objects(capture,0)
        shadow = group_objects(capture,4)
        if not primary:
            raise ValueError("No palette-0 candidate objects found")
        signature=tile_fingerprint(primary)
        if signature not in fingerprints:
            fingerprints[signature] = len(fingerprints)+1
        series.append({
            "frame":frame,
            "candidate_helicopter_oam_count":len(primary),
            "candidate_shadow_oam_count":len(shadow),
            "candidate_helicopter_tile_ids":list(signature),
            "tile_family":fingerprints[signature],
            "candidate_origin":[min(o["x"] for o in primary),min(o["y"] for o in primary)],
            "candidate_objects":[
                {k:o[k] for k in ("index","x","y","tile","palette","large","hflip","vflip")}
                for o in primary
            ],
        })
    changes=[]
    for (first,a),(second,b) in zip(pairs,pairs[1:]):
        different=[i for i,(left,right) in enumerate(zip(a.vram,b.vram)) if left!=right]
        cg_entries=[j for j in range(256) if a.cgram[2*j:2*j+2]!=b.cgram[2*j:2*j+2]]
        oa=decode_oam(a.oam)
        ob=decode_oam(b.oam)
        changes.append({
            "before_frame":first,"after_frame":second,
            "vram_changed_bytes":len(different),
            "vram_changed_4bpp_tile_count":len({i//32 for i in different}),
            "changed_palette_entries":cg_entries,
            "changed_oam_object_indices":[i for i,(x,y) in enumerate(zip(oa,ob)) if x!=y],
        })
    families = [{"id":i,"frames":[x["frame"] for x in series if x["tile_family"]==i],
                 "tile_ids":list(sig)}
                for sig,i in fingerprints.items()]
    return {
        "format":"rom2native-ppu-motion-series-v1",
        "rom_sha256":original,
        "groups_are":"heuristic palette 0 candidate helicopter, palette 4 candidate shadow",
        "warnings":[
            "These palette groups are empirically supported only for the analyzed scene.",
            "Tile-family matching does not prove an exact heading or a full sprite reconstruction.",
            "CGRAM/OAM/VRAM can change for animation and scene events independently of player input."
        ],
        "frames":series,"families":families,"changes":changes,
    }

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("captures",nargs="+",type=Path)
    parser.add_argument("--out",type=Path,default=Path("private-output/ppu-motion-series.json"))
    args=parser.parse_args()
    report=analyze(args.captures)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Capture frames: {len(report['frames'])}; distinct tile families: {len(report['families'])}")
    print(f"Report written to: {args.out}")

if __name__=="__main__":
    main()
