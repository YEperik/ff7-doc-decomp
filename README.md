<p align="center"><img src="assets/banner.png" alt="FF7-DoC Decompilation"></p>

<p align="center">
  <img src="assets/badge-decompiled.svg" alt="decompiled"> <img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT">
  <img src="https://img.shields.io/badge/target-PS2%20%7C%20MIPS%20R5900-informational" alt="target">
</p>

<p align="center">
  <b>Decompilation of FF7 DoC (PS2, SLPM-66629)</b><br>
  <a href="README.id.md">Bahasa Indonesia</a> · <a href="docs/PROGRESS.md">Progress</a> · <a href="docs/ANALYSIS.md">Analysis</a> · <a href="LEGAL.md">Legal</a>
</p>

---

## Progress

<!-- PROGRESS:START -->
<p align="center"><img src="assets/progress.svg" alt="Decompilation progress" width="760"></p>

| | Done | Total |
|---|---:|---:|
| Functions | 51 (0.39%) | 12932 |
| Code bytes | 0.12% | 4,390,020 |
| Byte-exact | 18 (0.01% of bytes) | 12932 |
| Most-called 300 | 36 (12.0%) | 300 |

Details and history: [docs/PROGRESS.md](docs/PROGRESS.md)
<!-- PROGRESS:END -->

A function counts as **decompiled** when its C passes differential tests against the original code (`make test`).

## Target

| | |
|---|---|
| Game ID | SLPM-66629 (Japan) |
| Executable | `SLPM_666.29`, MIPS R5900, ELF32 |
| Language | C, plus Python tooling |

## Setup

Requires Python 3.9+ and `gcc`. You must provide your own copy of the executable from a disc you own.

```sh
cp /path/to/SLPM_666.29 game/
make verify      # checks the SHA-256 in config/game.json
make test        # runs every C function against the original code
```

## Tools

```sh
python -m ps2an info game/SLPM_666.29
python -m ps2an disasm game/SLPM_666.29 lock_acquire -n 20
```

| Command | Purpose |
|---|---|
| `info` `functions` `strings` `xrefs` `embedded` | Inspect the executable |
| `sdk` `ident` | Name syscall wrappers, SDK and libc functions by evidence |
| `hubs` | Most-called functions: next targets |
| `disasm` `split` `stubs` | Disassemble, write local asm, generate C stubs |
| `match` | Compile reconstructed C with the built-in compiler and compare with the original bytes |
| `progress` | Update progress files (`--check` for CI) |
| `verify` | Check the executable's SHA-256 |

## How a function is verified

1. Write C in `src/game/` and add it to `tests/game_test.py`.
2. The test runs the C and the original (in the built-in emulator) on the same random memory.
3. Return value, all memory and the sequence of calls to other functions must match, and the original must be fully covered.
4. `make match` compiles the C with the built-in compiler (`ps2an cc`); functions that reproduce the original instructions exactly are listed in `src/game/matched.txt` and counted as **byte-exact**.
5. Run `make progress` to update the numbers above.

## Layout

```
ps2an/      analysis toolkit, emulator, assembler, C compiler
symbols/    functions.csv, named.txt, hubs.csv
src/        game/ libc/ include/ stubs/  (game/matched.txt = byte-exact list)
tests/      differential tests
progress/   progress.json, history.csv
docs/       ANALYSIS.md, PROGRESS.md
```

## Contributing

Pick a function from `symbols/hubs.csv`, reconstruct it in C, make `make test` pass, run `make progress`, and open a pull request with C and tests only.

## License

Tooling and reconstructed code: MIT. See [LEGAL.md](LEGAL.md).
