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

- **12,932 functions** found (jal targets, prologue-after-return, 61 exact syscall-wrapper patterns, and 8 manual boundaries).
- **103 functions named**, each with an evidence tag in `symbols/named.txt` (`syscall`, `sdk-string`, `behavior-verified`, `thunk`, `manual`, `decomp-verified`).
- **36 functions reconstructed in C** (`src/game/`), plus the 12 libc functions in `src/libc/`. Live numbers: [PROGRESS.md](PROGRESS.md).
- **SDK libraries present:** libgs, libpad, libmc, libcdvd, libsif, libscf, libdma, libat3dec.
- **2 embedded IOP modules** (ELF type `0xff80`) inside the executable.
- **Runtime-loaded modules** (`polmem0:*.erx`) and data-file path formats exist in `.rodata`.

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

`src/libc/libc.c` holds C equivalents. `tests/diff_test.py` runs them on the host and compares result and memory with the original (400 random inputs per function, SIMD paths included). Current result: all pass.

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
| `lock_acquire` | `0x0042d428` | FIFO lock: queue the current thread id, sleep unless first | 563 |
| `lock_release` | `0x0042d590` | pop the head of the lock queue, wake the next thread | 631 |
| `lock_acquire_004dfd00` `lock_release_004dfd00` | `0x00251e30` `0x00251e50` | lock a global queue at `0x4dfd00` (allocator guard) | |
| `FUN_002521f0` `FUN_00252160` `FUN_002521a8` | | allocator wrappers: free, and two identical allocate-with-caller-tag copies | 226, 115, 51 |
| `FUN_00376198` `FUN_003761e8` | `0x00376198` `0x003761e8` | per-object lock at `+0x3d4`, skipped for the owning thread | 200, 200 |
| `FUN_00241de8` | `0x00241de8` | is the current thread the stored thread? | |
| `FUN_0054a920` `FUN_005a3a48` `FUN_005a39e8` `FUN_002a8060` `FUN_002e14f8` `FUN_00326540` | | small non-leaf wrappers | |
| `FUN_0055a570` `FUN_00316d38` `FUN_002535e0` | | field getter, zero test, `x < 0 ? x : x >> 16` | |

The cell stack has hundreds of callers, which suggests a script or VM stack. That is an inference. Names stay neutral (`FUN_*`) where the purpose is unclear.

Both lock functions call out (`DIntr`, `EIntr`, `GetThreadId`, `SleepThread`, `WakeupThread`, an assertion helper and one wait helper). The test replaces every callee by the same deterministic mock on both sides (hooks in the emulator, `tests/shim.c` for the C) and compares the **sequence of calls and arguments** too. `DIntr` and `EIntr` read the COP0 Status register and execute `di`/`ei`.

Global accesses use `GV(type, address)` placeholders until `.data`/`.bss` are split into real symbols.

## Byte-exact matching

`ps2an cc` is a small C-subset compiler for the R5900 built on a C front end. It reproduces how the original compiler lays out small functions:

- absolute addresses become `lui` plus a 16-bit offset (high half rounded for negative low halves);
- offsets of 32 KB and more use a shared `base + 0x8000` register;
- instructions are list-scheduled by critical path (loads take 2 cycles, other instructions 1), ties in source order;
- the last scheduled instruction fills the delay slot of `jr ra`;
- the result chain lives in `$v0`, address temporaries in `$v1` (or `$v0` when nothing is returned), other temporaries in the first free register;
- calls: `addiu sp` and `sd ra` open the function and are scheduled first, arguments are computed straight into `$a0..$a3` (parameters that would be overwritten are copied first), the call's delay slot takes the last instruction that can move there (never one that reads `$ra`), and `addiu sp` fills the delay slot of `jr ra`;
- the scheduler is dual-issue: two instructions per cycle, at most one memory operation per cycle.

`make match` compiles every reconstructed function and compares the instructions with the original. 18 functions are byte-exact so far (`src/game/matched.txt`); the rest report what the compiler still lacks (branches, loops, values kept across calls). The assembler behind it is validated by `tests/asm_test.py` (disassemble then assemble reproduces 99.5% of the entry code of every detected function; the remainder is data misread as code).

## Tool accuracy

Compared with an independent auto-analysis of the same executable (13,090 functions; 13 exact syscall wrappers found here are missing there):

| Metric | Result |
|---|---|
| Recall | 98.2% |
| Precision | 99.4% |


## Limits

- Leaf functions without a `jal` caller (indirect calls only) can be missed.
- `ps2an` decodes the core MIPS set; R5900 MMI and COP2 appear as `.word`.
- Names are only assigned where evidence is strong; everything else stays `FUN_<addr>`.
- Adjacent tiny functions without a `jal` caller can be merged. `ps2an tail` lists 2,469 candidates, but they are **unverified** (only 133 are confirmed by the independent analysis) and are not part of the default list.
