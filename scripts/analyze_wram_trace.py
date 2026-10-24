#!/usr/bin/env python3
"""Summarize exported Desert Strike WRAM traces. No ROM data is required."""
import argparse
import json
from pathlib import Path

SUPPORTED = {"desert-wram-diff-v1", "desert-wram-diff-v2"}
MAX_BYTES = 8 * 1024 * 1024


def summarize(trace, button=6, top=12):
    schema = trace.get("schema")
    if schema not in SUPPORTED:
        raise ValueError("Unsupported WRAM trace schema")
    if button not in range(12):
        raise ValueError("Button must be 0..11")
    if top not in range(1, 25):
        raise ValueError("Top must be 1..24")
    frames = trace.get("frames", [])
    if not isinstance(frames, list) or len(frames) > 600:
        raise ValueError("Invalid frame list")
    changes = sum(int(frame.get("changed_total", 0)) for frame in frames)
    preview = sum(len(frame.get("changes", [])) for frame in frames)
    output = {
        "schema": schema,
        "frames": len(frames),
        "changed_events": changes,
        "preview_events": preview,
        "not_in_preview": max(0, changes - preview),
        "button": button,
        "candidates": [],
    }
    if schema == "desert-wram-diff-v1":
        output["warning"] = "Legacy trace: only first 32 changes per frame were exported."
        return output
    ranking = next((x for x in trace.get("rankings", [])
                    if x.get("button") == button), None)
    if ranking is None:
        output["warning"] = "No ranking available for the requested button."
        return output
    on = int(ranking["frames_on"])
    off = int(ranking["frames_off"])
    output["frames_button_on"] = on
    output["frames_button_off"] = off
    if on < 2 or off < 2:
        output["warning"] = "Record at least two frames with and without this button."
    for item in ranking.get("top", [])[:top]:
        address, hits_on, hits_off, score = item
        output["candidates"].append({
            "ram_offset_hex": f"0x{int(address):05X}",
            "changes_with_button": int(hits_on),
            "changes_without_button": int(hits_off),
            "rate_difference": round(int(hits_on) / on - int(hits_off) / off, 4)
                if on and off else None,
            "raw_score": int(score),
        })
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path, help="JSON trace exported by the Android app")
    parser.add_argument("--button", type=int, default=6,
                        help="Libretro button index: 6=left, 7=right, 0=B, 8=A")
    parser.add_argument("--top", type=int, default=12)
    args = parser.parse_args()
    if args.trace.stat().st_size > MAX_BYTES:
        parser.error("Trace exceeds 8 MiB")
    with args.trace.open(encoding="utf-8") as f:
        trace = json.load(f)
    print(json.dumps(summarize(trace, args.button, args.top),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
