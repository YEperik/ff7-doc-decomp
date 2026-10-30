## 2026-10-30 - Fast Instruction Support Checks via Bitwise Opcodes
**Learning:** Calling full disassembly/string formatting (`decode()`) just to check if an opcode is supported by the emulator introduces heavy string creation and formatting overhead during candidate function scans. Direct bitwise extraction (`w >> 26`, `w & 63`) and set lookups preserve exact semantics while executing ~5x faster.
**Action:** Use pre-computed integer/bitwise lookup sets instead of string formatting when validating opcode capabilities or instruction classifications.
