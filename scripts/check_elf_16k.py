#!/usr/bin/env python3
"""Check that every arm64 .so in an APK has >=16-KiB ELF PT_LOAD alignment."""
import argparse
import struct
import sys
import zipfile
from pathlib import Path

PAGE = 16384


def validate_arm64_elf(data: bytes, filename: str = "native.so") -> list[str]:
    issues = []
    if len(data) < 64 or data[:4] != b"\x7fELF" or data[4] != 2:
        return [f"{filename}: not ELF64"]
    endian = "<" if data[5] == 1 else ">" if data[5] == 2 else None
    if endian is None:
        return [f"{filename}: invalid ELF byte order"]
    (machine,) = struct.unpack_from(endian + "H", data, 18)
    if machine != 183:
        issues.append(f"{filename}: expected AArch64, got architecture {machine}")
    (phoff,) = struct.unpack_from(endian + "Q", data, 32)
    phentsize, phnum = struct.unpack_from(endian + "HH", data, 54)
    if phentsize < 56 or phnum == 0 or phoff + phentsize * phnum > len(data):
        return issues + [f"{filename}: invalid program header table"]
    loads = 0
    for i in range(phnum):
        p_type, _, p_offset, p_vaddr, _, _, _, p_align = struct.unpack_from(
            endian + "IIQQQQQQ", data, phoff + i*phentsize
        )
        if p_type != 1:
            continue
        loads += 1
        if p_align < PAGE or p_align % PAGE:
            issues.append(f"{filename}: segment {i} p_align={p_align}")
        if (p_offset - p_vaddr) % PAGE:
            issues.append(f"{filename}: segment {i} offset/address mismatch")
    if not loads:
        issues.append(f"{filename}: missing PT_LOAD segments")
    return issues


def check(path: Path) -> list[str]:
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if n.startswith("lib/arm64-v8a/") and n.endswith(".so")]
            required = {"lib/arm64-v8a/libdesert_bridge.so", "lib/arm64-v8a/libsnes9x_libretro.so"}
            errors = [f"missing: {n}" for n in sorted(required - set(names))]
            for name in names:
                errors.extend(validate_arm64_elf(z.read(name), name))
            return errors
    return validate_arm64_elf(path.read_bytes(), path.name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    issues = check(args.path)
    for issue in issues:
        print("FAIL:", issue, file=sys.stderr)
    if not issues:
        print("PASS: arm64 ELF PT_LOAD segments are 16-KiB aligned")
    sys.exit(bool(issues))
