# ELF analysis

Target: `SLPM_666.29` (ELF32 LE, MIPS R5900, statically linked, stripped).
Identity is pinned by SHA-256 in [`config/game.json`](../config/game.json).

## Memory map

| Section | Address | Size | Functions |
|---|---|---|---|
| `.text` | `0x00100000` | `0x360914` | 9,639 |
| `.vutext` | `0x00460920` | `0x00a8f0` | VU1 microcode (not MIPS) |
| `.data` | `0x0046b280` | `0x02cf00` | |
| `.rodata` | `0x00498180` | `0x019b30` | |
| `.bss` | `0x004b1d00` | `0x05cfc0` | |
| `.kel_us_overwrap_extended_program_section` | `0x005185c0` | `0x0079c0` | 12 |
| `.kel_extended_program_section` | `0x00528780` | `0x07e780` | 1,864 |
| `.kel_draw_section` | `0x005a6f00` | `0x00cf30` | 211 |
| `.kel_title` | `0x00aa0000` | `0x008600` | 82 |
| `.kel_net` | `0x00bbff00` | `0x033d00` | 1,101 |

The `.kel_*` sections are code overlays: several share the `0x00528780` and `0x00780000` ranges with the main image, so addresses are only unique **per section**. The `.DVP.overlay.*` blobs (20, about 34 KB) are VU overlay data.

## Findings

- **12,909 functions** found (jal targets plus prologue-after-return).
- **44 functions named** automatically: 39 EE kernel syscall wrappers and 5 `sceGs*` library functions (from their error strings).
- **SDK libraries present:** libgs, libpad, libmc, libcdvd, libsif, libscf, libdma, libat3dec.
- **2 embedded IOP modules** (ELF type `0xff80`) inside the executable.
- **Runtime-loaded modules** (`polmem0:*.erx`) and data-file path formats exist in `.rodata`; see the dev package for the full strings.

## Tool accuracy

Compared with a Ghidra auto-analysis of the same ELF (13,090 functions):

| Metric | Result |
|---|---|
| Recall | 98.1% |
| Precision | 99.5% |

Reproduce: `make ghidra-check` (needs your own `.gzf`).

## Limits

- Leaf functions without a `jal` caller (indirect calls only) can be missed.
- `ps2an` decodes the core MIPS set; R5900 MMI and COP2 appear as `.word`.
- Names are only assigned where evidence is strong; everything else stays `FUN_<addr>`.
