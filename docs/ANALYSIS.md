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

- **12,916 functions** found (jal targets, prologue-after-return, and 7 manual boundaries).
- **74 functions named**, each with an evidence tag in `symbols/named.txt`:
  `syscall` (39) · `sdk-string` (5) · `behavior-verified` (15) · `thunk` (1) · `manual` (2) · `decomp-verified` (12).
- **19 functions reconstructed in C** (`src/game/`), plus the 12 libc functions in `src/libc/`.
- **SDK libraries present:** libgs, libpad, libmc, libcdvd, libsif, libscf, libdma, libat3dec.
- **2 embedded IOP modules** (ELF type `0xff80`) inside the executable.
- **Runtime-loaded modules** (`polmem0:*.erx`) and data-file path formats exist in `.rodata`; see the dev package for the full strings.

## libc cluster

Identified by **behaviour**, not by name: each small leaf function runs in the built-in emulator (integer core, `lq`/`sq`, and the MMI subset it needs) on randomized inputs, and must agree with reference libc semantics.

| Function | Address |
|---|---|
| `strlen` | `0x00423028` `0x0042f7f0` `0x004484ec` |
| `bzero` | `0x00423360` `0x004423e8` |
| `memcmp` `memcpy` `memmove` `memset` `memchr` | `0x00447be8` `0x00447c7c` `0x00447d2c` `0x00447e30` `0x0044b660` |
| `strchr` `strcmp` `strcpy` `strncmp` `strncpy` | `0x004480e0` `0x00448284` `0x004483d0` `0x00448638` `0x00448800` |
| `memcpy_alias` | `0x00422f70` (`j memcpy`) |
| `setjmp` `longjmp` | `0x00447ef0` `0x00447f48` (manual, disassembly) |

**Evidence rule.** A name is `behavior-verified` only if every instruction is executable by the emulator **and** the tests executed at least 90% of the function's instructions. Anything weaker is not named. The coverage gate caught a thunk and a SIMD path the first tests never reached.

**Observation.** In `strncpy` the first-quad NUL check computes `~x - 1` instead of `x - 1`, so 7-bit text always falls back to the byte loop. The result is still correct. Only data with bytes >= 0x80 reaches the 16-byte loop.

`src/libc/libc.c` holds C equivalents. `tests/diff_test.py` runs them on the host and compares result and memory with the original (400 random inputs per function, SIMD paths included). Current result: all pass. These are behavioural matches, not byte matches (no `ee-gcc` here).

## Call graph

`symbols/hubs.csv` lists the 300 most-called functions with `leaf` and `emulatable` flags (100 are both). They are the next decompilation targets: small, heavily used, and testable with the same method.

## Decompiled functions

C reconstructions in `src/game/`. `tests/game_test.py` maps guest memory at identical host addresses, runs the C and the original (emulated) on the same random memory, and compares the return value and **all** memory afterwards: 500 trials per function and 100% instruction coverage of the original. Injecting a bug into the C makes the test fail (checked).

| Function | Address | Behaviour | Callers |
|---|---|---|---|
| `cstack_pop` | `0x003aa140` | pop the top 8-byte cell of the stack at `ctx+0xF014` | 295 |
| `cstack_push_int` | `0x003aa0c0` | push a cell with type 1 and an integer | 179 |
| `cstack_drop` | `0x003aa108` | discard the top cell, optionally copying it out | 93 |
| `copy16` | `0x00444eb8` | copy one aligned quadword | 151 |
| `get_flag_004b8cc8` `has_flag_004b8b80` | `0x002419d8` `0x002413c0` | bit tests on global flag words | 149, 75 |
| `get_/set_gvar_*` (6) | various | global variable accessors | |
| `FUN_003cb2f8` | `0x003cb2f8` | find a list node by id byte | 165 |
| `FUN_002533b0` | `0x002533b0` | table lookup, value if flag bit 0 set | 128 |
| `FUN_002533f0` | `0x002533f0` | 1 if any element starts before the previous one ends | |
| `FUN_00340bf8` | `0x00340bf8` | set/clear flag bit 1 and a byte | 107 |
| `FUN_0055a570` `FUN_00316d38` `FUN_002535e0` | | field getter, zero test, `x < 0 ? x : x >> 16` | |

The cell stack has hundreds of callers, which suggests a script or VM stack. That is an inference. Names stay neutral (`FUN_*`) where the purpose is unclear.

Global accesses use `GV(type, address)` placeholders until `.data`/`.bss` are split into real symbols.

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
- Adjacent tiny functions without a `jal` caller can be merged. `ps2an tail` lists 2,469 candidates, but they are **unverified** (only 133 are known to Ghidra) and are not part of the default list.
