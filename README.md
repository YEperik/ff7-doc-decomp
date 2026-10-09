# Dirge of Cerberus PS2 

Research workspace for **Dirge of Cerberus: Final Fantasy VII International — Ultimate Hits**, target label supplied as `SLPM-66629`.

## Analysis of the uploaded ELF

SHA-256 is:

`d715531d0713700ae1c7f9133cf98ee106d600c0a702f07c2f88705faf866d99`

Key metadata:
- File size: 4,760,568 bytes (4.54 MiB)
- ELF class / byte order: ELF32, little-endian
- ELF type: executable (`ET_EXEC`)
- ELF machine field: MIPS (`e_machine=8`; generic `readelf` labels it MIPS R3000)
- ELF flags: `0x20924001`; flags include the MIPS 5900 marker and MIPS III / EABI64-related bits
- Entry point: `0x00100000`
- Program headers: 5
- Section headers: 40
- The ELF is stripped according to the local `file`/`readelf` inspection; no regular symbol table entries were reported.
- Special sections include `.vutext`, `.DVP.ovlytab`, multiple `.DVP.overlay...` sections, and `.kel_*` sections.

**Important:** ELF metadata alone cannot prove the disc serial or game identity. The supplied filename is `SLPM_666.29`, while the requested product code is `SLPM-66629`; verify the serial from the disc/dump metadata if exact build identity matters.

## What this project does

- Inspects ELF metadata and section/program headers.
- Calculates SHA-256 for your local files.
- Scans executable sections for MIPS `JAL` opcode candidates and exports a CSV.
- Includes a Ghidra script to export `JAL` instruction references from the program after you import it.
- Documents community tools and a safe Windows workflow.

This is **not** a completed decompiler or recompilation system. It does not yet reconstruct C source, fix every Ghidra disassembly issue, or create a matching game executable.

## Windows 10 quick start

1. Install Python 3.10+ from https://www.python.org/downloads/windows/ (enable **Add Python to PATH**).
2. Extract this ZIP to a writable folder, such as `C:\Projects\dirge-of-cerberus-ps2`.
3. Run `check-windows.bat`.
4. To analyze your own ELF, run:

```bat
py tools\analyze_elf.py "D:\path\to\SLPM_666.29" --out reports
```

This produces `reports/elf_report.json`, `reports/sections.csv`, and `reports/jal_candidates.csv`.
You can drag an ELF onto `analyze-elf.bat` for a quick report.

## Recommended next step for the reported “Bad instruction (JAL)” issue

Import the ELF into Ghidra with the PS2 Emotion Engine language supplied by **Ghidra Emotion Engine: Reloaded**. The generic ELF machine field can be misleading for a PS2 Emotion Engine file; the ELF flags include a 5900 marker. Do not patch `JAL` words merely because a tool labels them bad. First determine whether the selected processor language, load address, delay slots, overlay mapping, and code/data boundaries are correct.

Read `docs/jal-triage.md` before using the heuristic CSV.

## Layout

- `tools/` — local analysis helpers (Python standard library only)
- `ghidra_scripts/` — script to export JAL call candidates from a Ghidra program
- `reports/` — place reports generated locally; the uploaded game ELF is not included
- `docs/` — findings, tool references, Windows instructions
- `src/` — place only code you authored or may legally redistribute

## License

Review the license of every external tool before redistributing it.
