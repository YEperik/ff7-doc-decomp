# External tools and community projects

Tools are not bundled in this ZIP. Install them from upstream and check compatibility/licensing.

## Recommended first choice

- **Ghidra** — https://ghidra-sre.org/
- **Ghidra Emotion Engine: Reloaded** — https://github.com/chaoticgd/ghidra-emotionengine-reloaded
  Adds PS2/Emotion Engine instruction support, R5900 analysis, and several Ghidra utilities. Match the extension release to your installed Ghidra version. Releases: https://github.com/chaoticgd/ghidra-emotionengine-reloaded/releases
- **PCSX2** — https://pcsx2.net/ and https://github.com/PCSX2/pcsx2
- **ps2disSharp** — https://github.com/harryhardcastle/ps2disSharp
  Community PS2 disassembler/debugger. Its documented PCSX2 integration uses PINE and PCSX2-MCP; check its README and release assets before installing.
- **PS2 Decompiler Toolkit** — https://github.com/ismaelcaraballo-afk/ps2-decompiler
  Community workflow/toolkit worth reviewing, but compatibility with this particular ELF is not guaranteed. Review code, dependencies, and license before use.

## Important

- Do not assume a community tool supports this exact game merely because it supports PS2.
- Ghidra pseudocode is not original source code.
- This ELF is stripped in the inspected metadata; automatic symbol recovery may be limited unless additional debug/symbol data is available.
- Never redistribute external binaries or copyrighted game data without permission.
