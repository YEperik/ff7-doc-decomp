## 2026-10-30 - Fast Instruction Support Checks via Bitwise Opcodes
**Learning:** Calling full disassembly/string formatting (`decode()`) just to check if an opcode is supported by the emulator introduces heavy string creation and formatting overhead during candidate function scans. Direct bitwise extraction (`w >> 26`, `w & 63`) and set lookups preserve exact semantics while executing ~5x faster.
**Action:** Use pre-computed integer/bitwise lookup sets instead of string formatting when validating opcode capabilities or instruction classifications.

## 2026-11-03 - Fast Substring Pre-Filter for Multi-Branch Disassembly Regexes
**Learning:** Multi-branch regular expressions with multiline flags (`re.M`) and non-anchored patterns (like `LISTING`) suffer massive backtracking overhead when evaluated over multi-megabyte CSV and report text files. Because all branches in the pattern require distinguishing character literals (such as `.word`, `/*`, or `:`), checking substring presence (`in`) in CPython first executes orders of magnitude faster than invoking the regex engine.
**Action:** Guard expensive, multi-branch inspection regexes across repository files with simple substring checks (`in`) for mandatory anchor characters before invoking regex matching.
