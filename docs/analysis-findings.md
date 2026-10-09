# Findings from the supplied ELF

## Identity and integrity

- Original uploaded filename: `SLPM_666.29`
- Size: 4,760,568 bytes
- SHA-256: `d715531d0713700ae1c7f9133cf98ee106d600c0a702f07c2f88705faf866d99`
- ELF magic: valid
- ELF class: ELF32
- Endianness: little-endian
- ELF type: `ET_EXEC`
- `e_machine`: 8 (MIPS)
- Entry point: `0x00100000`
- ELF flags: `0x20924001`
- Program headers: 5
- Section headers: 40

## Observations

1. This is a MIPS little-endian ELF executable. The ELF flags contain the MIPS 5900 marker, consistent with a PS2 Emotion Engine target, even though generic binutils displays the machine as “MIPS R3000”.
2. The file is stripped in the inspected metadata, so meaningful original function names are not available from a conventional symbol table.
3. It contains PS2-specific-looking sections such as `.vutext`, `.DVP.ovlytab`, `.DVP.overlay...`, and `.kel_*`. Some DVP overlay sections have no virtual address in the ELF section table; their actual runtime mapping may depend on the game's overlay loader.
4. The executable entry point is `0x00100000`.
5. A raw opcode scan sees many 32-bit words matching the MIPS `JAL` opcode in executable-flagged sections. This is only a candidate list, not proof every word is a real instruction: code/data boundaries, embedded tables, overlays, and runtime mappings matter.

## JAL scan counts

The local heuristic scan found the following candidates in sections that have a virtual address:

| Section | JAL opcode candidates | Targets outside executable PT_LOAD ranges |
|---|---:|---:|
| `.text` | 34454 | 2500 |
| `.vutext` | 5 | 4 |
| `.kel_us_overwrap_extended_program_section` | 225 | 52 |
| `.kel_extended_program_section` | 8476 | 0 |
| `.kel_draw_section` | 615 | 0 |
| `.kel_title` | 615 | 60 |
| `.kel_net` | 2993 | 0 |

The table is a triage aid. A target outside an executable PT_LOAD range can be a false positive, a call to a separately loaded overlay, a bad load mapping, or a real issue; it must be checked in Ghidra/runtime context. Do not automatically rewrite these instructions.

## What is not established

- The ELF alone does not confirm the exact disc serial/version.
- This analysis does not prove a particular JAL instruction is invalid.
- No binary patches were made.
- No source code or matching recompilation build has been produced.
