#!/usr/bin/env python3
"""Streaming ELF32 little-endian/MIPS scanner for PS2 ELF triage.

This is a heuristic opcode scanner, not a disassembler or patcher. It uses mmap
and chunked CSV output so large files do not require all bytes/rows in RAM.
"""
import argparse
import csv
import hashlib
import json
import mmap
import struct
import sys
from pathlib import Path

PT_LOAD, PF_X, SHF_EXECINSTR, SHT_NOBITS = 1, 1, 0x4, 8


def cstr(buf, off):
    if off < 0 or off >= len(buf):
        return ""
    end = buf.find(b"\0", off)
    if end < 0:
        end = len(buf)
    return bytes(buf[off:end]).decode("ascii", "replace")


def parse_elf(data):
    if len(data) < 52 or data[:4] != b"\x7fELF":
        raise ValueError("File is not a complete ELF file.")
    if data[4] != 1 or data[5] != 1:
        raise ValueError("Only ELF32 little-endian is supported by this helper.")
    h = struct.unpack_from("<16sHHIIIIIHHHHHH", data, 0)
    _, etype, machine, version, entry, phoff, shoff, flags, ehsize, phentsize, phnum, shentsize, shnum, shstrndx = h
    if phentsize < 32 and phnum:
        raise ValueError("Program-header entry size is invalid.")
    if shentsize < 40 and shnum:
        raise ValueError("Section-header entry size is invalid.")
    if phoff + phentsize * phnum > len(data):
        raise ValueError("Program-header table extends beyond file.")
    if shoff + shentsize * shnum > len(data):
        raise ValueError("Section-header table extends beyond file.")
    phs = [struct.unpack_from("<IIIIIIII", data, phoff + i * phentsize) for i in range(phnum)]
    shs = [struct.unpack_from("<IIIIIIIIII", data, shoff + i * shentsize) for i in range(shnum)]
    if shnum and shstrndx >= len(shs):
        raise ValueError("Invalid section-name string-table index.")
    names = b""
    if shnum:
        ns = shs[shstrndx]
        if ns[4] + ns[5] > len(data):
            raise ValueError("Section-name string table extends beyond file.")
        names = data[ns[4]:ns[4] + ns[5]]
    sections = []
    for i, s in enumerate(shs):
        sections.append({"index": i, "name": cstr(names, s[0]), "type": s[1], "flags": s[2],
                         "addr": s[3], "offset": s[4], "size": s[5], "link": s[6],
                         "info": s[7], "align": s[8], "entsize": s[9]})
    return {"elf_type": etype, "machine": machine, "entry": entry, "flags": flags,
            "program_headers": phs, "sections": sections}


def sha256_stream(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("elf", type=Path, help="Input ELF")
    ap.add_argument("--out", type=Path, default=Path("reports"), help="Output directory")
    ap.add_argument("--chunk-rows", type=int, default=100000,
                    help="Maximum data rows per CSV part (default: 100000; 0 disables splitting)")
    ap.add_argument("--include-jalr", action="store_true", help="Also list opcode 0 JALR candidates (heuristic)")
    ap.add_argument("--section", action="append", default=[], help="Scan only section(s) by exact name; repeatable")
    ap.add_argument("--max-candidates", type=int, default=0, help="Stop after N candidates (0 = no limit)")
    args = ap.parse_args()
    if not args.elf.is_file():
        ap.error("input path is not a file")
    if args.chunk_rows < 0 or args.max_candidates < 0:
        ap.error("chunk/max values cannot be negative")
    args.out.mkdir(parents=True, exist_ok=True)
    size = args.elf.stat().st_size
    digest = sha256_stream(args.elf)
    try:
        with args.elf.open("rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as data:
            info = parse_elf(data)
            exec_ranges = []
            for ph in info["program_headers"]:
                p_type, p_off, vaddr, paddr, filesz, memsz, p_flags, align = ph
                if p_type == PT_LOAD and p_flags & PF_X and memsz:
                    exec_ranges.append((vaddr, vaddr + memsz))

            def target_is_exec(addr):
                return any(lo <= addr < hi for lo, hi in exec_ranges)

            section_rows, total, outside_total = [], 0, 0
            part_no, part_count, writer, out_handle = 0, 0, None, None
            cols = ["section", "virtual_address", "file_offset", "opcode", "word", "static_target",
                    "target_in_executable_load_segment", "scan_note"]

            def open_part():
                nonlocal part_no, part_count, writer, out_handle
                if out_handle:
                    out_handle.close()
                part_no += 1
                name = "jal_candidates.csv" if args.chunk_rows == 0 else "jal_candidates_%03d.csv" % part_no
                out_handle = (args.out / name).open("w", newline="", encoding="utf-8")
                writer = csv.DictWriter(out_handle, fieldnames=cols)
                writer.writeheader()
                part_count = 0

            def emit(row):
                nonlocal part_count
                if writer is None or (args.chunk_rows and part_count >= args.chunk_rows):
                    open_part()
                writer.writerow(row)
                part_count += 1

            selected = set(args.section)
            try:
                for si, s in enumerate(info["sections"]):
                    flags, off, secsize, addr = s["flags"], s["offset"], s["size"], s["addr"]
                    note = ""
                    count = outside = 0
                    if selected and s["name"] not in selected:
                        note = "not selected by --section"
                    elif s["type"] == SHT_NOBITS or not (flags & SHF_EXECINSTR) or secsize < 4:
                        note = "not a file-backed executable section"
                    elif off + secsize > len(data):
                        note = "section exceeds file bounds"
                    elif addr == 0:
                        note = "skipped: no virtual address; overlay/runtime mapping may apply"
                    else:
                        # Align by virtual address, not by file offset.
                        delta = (-addr) % 4
                        for rel in range(delta, secsize - 3, 4):
                            word = struct.unpack_from("<I", data, off + rel)[0]
                            opcode = word >> 26
                            is_jal = opcode == 3
                            is_jalr = args.include_jalr and opcode == 0 and ((word >> 21) & 31) != 0 and ((word >> 11) & 31) == 31 and ((word >> 6) & 31) == 0 and (word & 63) == 9
                            if not (is_jal or is_jalr):
                                continue
                            pc = addr + rel
                            target = (((pc + 4) & 0xF0000000) | ((word & 0x03FFFFFF) << 2)) if is_jal else 0
                            mapped = target_is_exec(target) if is_jal else False
                            count += 1
                            total += 1
                            if is_jal and not mapped:
                                outside += 1
                                outside_total += 1
                            emit({"section": s["name"], "virtual_address": "0x%08X" % pc,
                                  "file_offset": "0x%08X" % (off + rel),
                                  "opcode": "JAL" if is_jal else "JALR",
                                  "word": "0x%08X" % word,
                                  "static_target": ("0x%08X" % target) if is_jal else "indirect",
                                  "target_in_executable_load_segment": ("yes" if mapped else "no") if is_jal else "unknown",
                                  "scan_note": "heuristic word scan; inspect in Ghidra"})
                            if args.max_candidates and total >= args.max_candidates:
                                note = "stopped early at --max-candidates limit"
                                break
                    section_rows.append({**s, "jal_opcode_candidates": count,
                                         "targets_outside_executable_load_segments": outside,
                                         "scan_note": note or "heuristic scan; not proof of code/invalid instruction"})
                    print("[%d/%d] %-48s candidates=%d" % (si + 1, len(info["sections"]), s["name"][:48], count))
                    if args.max_candidates and total >= args.max_candidates:
                        break
            finally:
                if out_handle:
                    out_handle.close()

        sec_cols = ["index", "name", "type", "flags", "addr", "offset", "size", "link", "info", "align", "entsize",
                    "jal_opcode_candidates", "targets_outside_executable_load_segments", "scan_note"]
        with (args.out / "sections.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=sec_cols, extrasaction="ignore")
            w.writeheader(); w.writerows(section_rows)
        type_names = {1: "REL", 2: "EXEC", 3: "DYN"}
        report = {"tool_version": "2.0", "file_name": args.elf.name, "file_size": size, "sha256": digest,
                  "elf_class": "ELF32", "endianness": "little-endian", "elf_type": type_names.get(info["elf_type"], str(info["elf_type"])),
                  "machine_number": info["machine"], "machine_label": "MIPS" if info["machine"] == 8 else "unknown",
                  "entry_point": "0x%08X" % info["entry"], "elf_flags": "0x%08X" % info["flags"],
                  "program_header_count": len(info["program_headers"]), "section_header_count": len(info["sections"]),
                  "executable_load_ranges": [{"start": "0x%08X" % a, "end_exclusive": "0x%08X" % b} for a,b in exec_ranges],
                  "jal_and_optional_jalr_candidates_written": total, "jal_targets_outside_executable_load_segments": outside_total,
                  "chunk_rows": args.chunk_rows, "include_jalr": args.include_jalr,
                  "warning": "Heuristic scan only. It may interpret embedded data as instructions and cannot prove a JAL is invalid or resolve runtime overlays."}
        (args.out / "elf_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print("\nDone. File size: %s bytes | SHA-256: %s" % (format(size, ","), digest))
        print("Candidates: %s | output: %s" % (format(total, ","), args.out.resolve()))
        print("CSV is split into parts to limit memory and make large results easier to inspect.")
    except (ValueError, OSError, struct.error) as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 2
    return 0

if __name__ == "__main__":
    sys.exit(main())
