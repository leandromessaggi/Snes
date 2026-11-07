#!/usr/bin/env python3
"""Validate user-authored ROM2Native combat missions without a ROM or APK.

These are demonstration mission files, not scripts or maps recovered from SNES.
The Android importer and C++ runtime revalidate all gameplay-critical fields.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROM_SHA="606abf536440173ae36466db360c7db6b474beb7a105c8a62bc74a54cbe1c38b"
FORMAT="rom2native-mission-v1"

def unique_object_pairs(pairs):
    out={}
    for key,value in pairs:
        if key in out:raise ValueError("Duplicate JSON object key: "+key)
        out[key]=value
    return out

def validate_bytes(data,expected_sha=ROM_SHA):
    if not 1<=len(data)<=32768:
        raise ValueError("Mission JSON must be between 1 byte and 32 KiB")
    raw=json.loads(data.decode("utf-8"),object_pairs_hook=unique_object_pairs)
    if not isinstance(raw,dict):raise ValueError("Mission root must be an object")
    if raw.get("format")!=FORMAT:raise ValueError("Unsupported mission format")
    if raw.get("rom_sha256")!=expected_sha:raise ValueError("ROM SHA-256 differs")
    if raw.get("goal")!="destroy_all":raise ValueError("Only destroy_all goal is supported")
    title=raw.get("title")
    if not isinstance(title,str) or not 1<=len(title.strip())<=70:
        raise ValueError("Invalid mission title")
    targets=raw.get("targets")
    if not isinstance(targets,list) or not 1<=len(targets)<=12:
        raise ValueError("Mission requires 1..12 targets")
    ids=set()
    for index,obj in enumerate(targets):
        if not isinstance(obj,dict):raise ValueError("Target must be an object")
        tid=obj.get("id")
        if not isinstance(tid,str) or not re.fullmatch("[A-Za-z0-9_-]{1,24}",tid) or tid in ids:
            raise ValueError("Invalid or duplicate target ID")
        ids.add(tid)
        kind=obj.get("type")
        if kind not in ("depot","turret","patrol"):
            raise ValueError("Invalid target type "+str(kind))
        x,y,hp=(obj.get(k) for k in ("x","y","hp"))
        radius=obj.get("patrol_range",0)
        if any(type(v) is not int for v in (x,y,hp,radius)):
            raise ValueError("Target numbers must be integers")
        if not (22<=x<=298 and 34<=y<=218 and 1<=hp<=9):
            raise ValueError("Target out of bounds or invalid hit points")
        if kind=="patrol":
            if not 8<=radius<=32:raise ValueError("Patrol radius must be 8..32")
        elif radius!=0:raise ValueError("Only patrol targets may have range")
        if not (18<=x-radius and x+radius<=302):
            raise ValueError("Patrol path exceeds screen")
        for other in targets[:index]:
            dx=x-other["x"];dy=y-other["y"]
            if dx*dx+dy*dy<26*26:
                raise ValueError("Target positions overlap")
    return {"title":title.strip(),"target_count":len(targets),
            "types":{kind:sum(t["type"]==kind for t in targets)
                     for kind in ("depot","turret","patrol")}}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("file",type=Path)
    args=p.parse_args()
    result=validate_bytes(args.file.read_bytes())
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=="__main__":
    main()
