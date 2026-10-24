#!/usr/bin/env python3
"""Find possible 65C816 absolute memory references in a LoROM (not a disassembler)."""
import argparse
import hashlib
import json
from pathlib import Path

TARGETS = (0x202A, 0x202C, 0x202E, 0x2030, 0x20E6, 0x20E8)
OPS = {0x8D: ("STA","write"), 0x8E: ("STX","write"), 0x8C: ("STY","write"),
       0x9C: ("STZ","write"), 0xAD: ("LDA","read"), 0xAE: ("LDX","read"),
       0xAC: ("LDY","read"), 0x0C: ("TSB","read-write"), 0x1C: ("TRB","read-write"),
       0x2C: ("BIT","read"), 0xEE: ("INC","read-write"), 0xCE: ("DEC","read-write")}

def normalize(data):
    if len(data) % 1024 == 512:
        data = data[512:]
    if not data or len(data) % 0x8000:
        raise ValueError("Nonempty LoROM bank-aligned binary required")
    return data

def lorom_address(offset):
    if offset < 0:
        raise ValueError("Negative ROM offset")
    return "$%02X:%04X" % (offset // 0x8000, 0x8000 + offset % 0x8000)

def scan(image, targets=TARGETS):
    data = normalize(image)
    found = []
    for offset in range(len(data)-2):
        if offset % 0x8000 > 0x7FFD:
            continue
        opcode = data[offset]
        if opcode not in OPS:
            continue
        operand = data[offset+1] | (data[offset+2] << 8)
        if operand not in targets:
            continue
        mnemonic, access = OPS[opcode]
        found.append({"pc_offset": offset, "lorom_candidate": lorom_address(offset),
                      "bytes": data[offset:offset+3].hex().upper(),
                      "mnemonic": mnemonic, "access": access,
                      "operand": "$%04X" % operand})
    return found

def report(image):
    data = normalize(image)
    refs = scan(data)
    return {"schema": "desert-lorom-xrefs-v1",
            "rom_sha256": hashlib.sha256(data).hexdigest(),
            "references_found": len(refs), "references": refs,
            "warnings": ["Byte matches are not proven executed instructions.",
                         "The CPU data-bank register (DBR) is unknown.",
                         "No flight, combat, or mission variable has been confirmed."]}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=Path)
    parser.add_argument("--expected-sha256", default=None)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    result = report(args.rom.read_bytes())
    if args.expected_sha256 and result["rom_sha256"] != args.expected_sha256.lower():
        parser.error("ROM SHA-256 does not match")
    output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.write_text(output, encoding="utf-8")
    else:
        print(output, end="")

if __name__ == "__main__":
    main()
