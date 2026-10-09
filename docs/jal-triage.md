# Triage guide: Ghidra reports “Bad instruction (JAL)”

A `JAL` opcode being displayed as a bad instruction does **not** automatically mean the machine code is corrupt. Check these in order:

1. **Correct processor language:** use the Emotion Engine / R5900 language from Ghidra Emotion Engine: Reloaded, not a generic MIPS language if the extension provides the right language.
2. **Correct import/load address:** this ELF reports entry point `0x00100000`. Confirm Ghidra did not import the code at an incorrect base address.
3. **Code versus data:** a raw scan can find words that resemble instructions inside tables, embedded data, or overlays.
4. **Delay slots:** MIPS branch/jump instructions have delay-slot behavior; the following instruction can affect disassembly interpretation.
5. **Overlay sections:** the ELF contains `.DVP.overlay...` sections whose section virtual address is zero. They may be loaded at runtime by game-specific code. Do not judge their jump targets as ordinary static addresses without understanding the overlay loader.
6. **Function boundaries and references:** inspect the instruction bytes, surrounding instructions, incoming references, and Ghidra's language/analysis logs.
7. **Cross-check:** compare with another PS2-aware disassembler or PCSX2 runtime debugging if possible.

## Included reports

`tools/analyze_elf.py` scans words matching the `JAL` opcode in sections marked executable and exports:
- section name
- virtual address
- file offset
- raw 32-bit word
- computed static J target
- whether that target falls within a file-backed executable load segment

This is deliberately a **heuristic**. It does not emulate the CPU, resolve dynamic overlays, identify every `JALR`, or prove an instruction is valid/invalid. Review candidates manually before patching.
