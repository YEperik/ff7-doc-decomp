<p align="center"><img src="assets/banner.png" alt="FF7-DoC Decompilation"></p>

<p align="center">
  <b>Decompilation toolkit and symbol map for FF7 DoC (PS2, SLPM-66629)</b><br>
  <a href="README.id.md">Bahasa Indonesia</a> · <a href="docs/ANALYSIS.md">Analysis</a> · <a href="LEGAL.md">Legal</a>
</p>

---

## Status

| Item | Value |
|---|---|
| Game ID | SLPM-66629 (Japan) |
| Target | `SLPM_666.29`, MIPS R5900, ELF32 |
| Functions found | 12,909 |
| Named | 62 |
| C equivalents (verified, 100% of tests) | 12 libc functions |
| Byte-matching | 0 (needs `ee-gcc`) |

## Quick start

Requires Python 3.9+. No dependencies.

```sh
# 1. Put your own dump here (never committed)
cp /path/to/SLPM_666.29 game/

# 2. Check it is the right file
make verify

# 3. Test the C equivalents against the original code
make test

# 4. Analyze
python -m ps2an info game/SLPM_666.29
python -m ps2an functions game/SLPM_666.29 -o functions.csv
python -m ps2an disasm game/SLPM_666.29 sceGsSyncPath -n 20
```

## Tools

| Command | Purpose |
|---|---|
| `info` | Headers, segments, sections |
| `functions` | Detect functions to CSV |
| `strings` | ASCII strings in data sections |
| `xrefs <regex>` | Functions that reference matching strings |
| `sdk` | Kernel and SDK function names |
| `embedded` | Embedded IOP modules |
| `symbols` | Write `symbols/` |
| `disasm <addr\|name>` | Disassemble one function |
| `split` | Per-function `.s` into `build/asm` (local only) |
| `stubs` | C stubs using `INCLUDE_ASM` |
| `hubs` | Most-called functions: next decompilation targets |
| `ident` | Name libc-like functions by running them in the emulator |
| `ghidra <gzf>` | Compare against a Ghidra export |
| `verify` | Check ELF SHA-256 |

## Layout

```
ps2an/      analysis toolkit
symbols/    functions.csv, named.txt (addresses and names only)
src/        headers, stubs, libc C equivalents
tests/      differential test (C vs original)
config/     game identity (SHA-256)
docs/       ELF analysis
scripts/    banner, release, public-safety check
game/       your files, git-ignored
```

## Contributing

1. Pick a function from `symbols/functions.csv`.
2. Write C that matches the local asm.
3. Open a PR with C only. Never include asm, binaries, or assets.

## Legal

No game code or assets are included. You supply your own copy. See [LEGAL.md](LEGAL.md). Tooling is MIT.
