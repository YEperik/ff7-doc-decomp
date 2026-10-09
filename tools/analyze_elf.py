#!/usr/bin/env python3
"""Inspect a PS2 ELF32 little-endian executable and triage JAL opcode candidates."""
import argparse
import csv
import hashlib
import json
import struct
from pathlib import Path

def cstr(buf, off):
    if off < 0 or off >= len(buf):
        return ""
    end = buf.find(b"\0", off)
    if end < 0:
        end = len(buf)
    return buf[off:end].decode("ascii", "replace")

def parse_elf(data):
    if len(data) < 52 or data[:4] != b"\x7fELF":
        raise ValueError("File is not a complete ELF file.")
    if data[4] != 1 or data[5] != 1:
        raise ValueError("This helper currently supports ELF32 little-endian only.")
    h = struct.unpack_from("<16sHHIIIIIHHHHHH", data, 0)
    _, etype, machine, version, entry, phoff, shoff, flags, ehsize, phentsize, phnum, shentsize, shnum, shstrndx = h
    if phoff + phentsize * phnum > len(data):
        raise ValueError("Program-header table extends beyond file.")
    if shoff + shentsize * shnum > len(data):
        raise ValueError("Section-header table extends beyond file.")
    phs = [struct.unpack_from("<IIIIIIII", data, phoff + i * phentsize) for i in range(phnum)]
    shs = [struct.unpack_from("<IIIIIIIIII", data, shoff + i * shentsize) for i in range(shnum)]
    if shstrndx >= len(shs):
        raise ValueError("Invalid section-name string-table index.")
    names_sec = shs[shstrndx]
    if names_sec[4] + names_sec[5] > len(data):
        raise ValueError("Section-name string table extends beyond file.")
    names = data[names_sec[4]:names_sec[4] + names_sec[5]]
    sections = []
    for i, s in enumerate(shs):
        name = cstr(names, s[0])
        sections.append({
            "index": i, "name": name, "type": s[1], "flags": s[2],
            "addr": s[3], "offset": s[4], "size": s[5], "link": s[6],
            "info": s[7], "align": s[8], "entsize": s[9]
        })
    return {
        "elf_type": etype, "machine": machine, "entry": entry, "flags": flags,
        "program_headers": phs, "sections": sections
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("elf", type=Path, help="ELF file to inspect")
    parser.add_argument("--out", type=Path, default=Path("reports"), help="Output directory (default: reports)")
    args = parser.parse_args()
    if not args.elf.is_file():
        parser.error("input path is not a file")
    data = args.elf.read_bytes()
    try:
        info = parse_elf(data)
    except ValueError as exc:
        parser.error(str(exc))

    args.out.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(data).hexdigest()
    executable_ranges = []
    for ph in info["program_headers"]:
        p_type, p_off, vaddr, paddr, filesz, memsz, p_flags, align = ph
        # PT_LOAD = 1; PF_X = 1
        if p_type == 1 and p_flags & 1 and memsz:
            executable_ranges.append((vaddr, vaddr + memsz))

    def target_is_exec(address):
        return any(lo <= address < hi for lo, hi in executable_ranges)

    section_rows = []
    jal_rows = []
    for s in info["sections"]:
        flags, offset, size, addr = s["flags"], s["offset"], s["size"], s["addr"]
        if offset + size > len(data) and s["type"] != 8:  # SHT_NOBITS = 8
            section_rows.append({**s, "scan_note": "section exceeds file bounds"})
            continue
        if not (flags & 0x4) or size < 4 or s["type"] == 8:
            section_rows.append({**s, "scan_note": "not a file-backed executable section"})
            continue
        if addr == 0:
            section_rows.append({**s, "scan_note": "skipped: section has no virtual address (overlay may be runtime-mapped)"})
            continue
        count = outside = 0
        start = offset
        end = offset + size
        aligned_start = start + ((4 - start % 4) % 4)
        for file_off in range(aligned_start, end - 3, 4):
            word = struct.unpack_from("<I", data, file_off)[0]
            if (word >> 26) != 3:  # MIPS JAL opcode
                continue
            pc = addr + (file_off - start)
            target = ((pc + 4) & 0xF0000000) | ((word & 0x03FFFFFF) << 2)
            mapped = target_is_exec(target)
            count += 1
            if not mapped:
                outside += 1
            jal_rows.append({
                "section": s["name"], "virtual_address": f"0x{pc:08X}",
                "file_offset": f"0x{file_off:08X}", "word": f"0x{word:08X}",
                "static_j_target": f"0x{target:08X}",
                "target_in_executable_load_segment": "yes" if mapped else "no"
            })
        section_rows.append({**s, "jal_opcode_candidates": count,
                             "targets_outside_executable_load_segments": outside,
                             "scan_note": "heuristic 32-bit word scan; not proof every candidate is code"})

    section_csv = args.out / "sections.csv"
    with section_csv.open("w", newline="", encoding="utf-8") as f:
        cols = ["index","name","type","flags","addr","offset","size","link","info","align","entsize",
                "jal_opcode_candidates","targets_outside_executable_load_segments","scan_note"]
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(section_rows)
    jal_csv = args.out / "jal_candidates.csv"
    with jal_csv.open("w", newline="", encoding="utf-8") as f:
        cols = ["section","virtual_address","file_offset","word","static_j_target","target_in_executable_load_segment"]
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(jal_rows)

    type_names = {1:"REL", 2:"EXEC", 3:"DYN"}
    report = {
        "file_name": args.elf.name, "file_size": len(data), "sha256": digest,
        "elf_class": "ELF32", "endianness": "little-endian",
        "elf_type": type_names.get(info["elf_type"], str(info["elf_type"])),
        "machine_number": info["machine"], "machine_label": "MIPS" if info["machine"] == 8 else "unknown",
        "entry_point": f"0x{info['entry']:08X}", "elf_flags": f"0x{info['flags']:08X}",
        "program_header_count": len(info["program_headers"]), "section_header_count": len(info["sections"]),
        "executable_load_ranges": [{"start": f"0x{a:08X}", "end_exclusive": f"0x{b:08X}"} for a,b in executable_ranges],
        "jal_opcode_candidate_count": len(jal_rows),
        "warning": "JAL scan is heuristic. It may include data interpreted as instructions and cannot resolve runtime overlays or prove a bad instruction."
    }
    (args.out / "elf_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"File: {args.elf}")
    print(f"Size: {len(data):,} bytes")
    print(f"SHA-256: {digest}")
    print(f"ELF32 little-endian, type={report['elf_type']}, machine={report['machine_label']}, entry={report['entry_point']}")
    print(f"Section headers: {len(info['sections'])}")
    print(f"JAL opcode candidates (heuristic): {len(jal_rows):,}")
    print(f"Reports written to: {args.out.resolve()}")
    print("Caution: candidates are not proof of invalid instructions. Review in PS2-aware Ghidra.")

if __name__ == "__main__":
    main()
