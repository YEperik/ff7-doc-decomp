"""Builds two archives in dist/:
   *-public.zip  safe for GitHub (tooling, docs, symbol metadata only)
   *-dev.zip     private working copy (public + your ELF, Ghidra project, local analysis output)
"""
import os, shutil, subprocess, sys, zipfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ROOT)
from scripts.verify_public import check
NAME = "ff7-doc-decomp"; DIST = os.path.join(ROOT, "dist"); STAGE = os.path.join(DIST, "_stage")
PUBLIC = ["README.md", "README.id.md", "LICENSE", "LEGAL.md", "Makefile", ".gitignore", ".github", "config", "docs",
          "assets", "ps2an", "scripts", "symbols", "src"]
ELF = os.path.join(ROOT, "game", "SLPM_666.29"); GZF = os.path.join(ROOT, "ghidra", "SLPM_666_29.gzf")

def run(*a): subprocess.run([sys.executable, "-m", "ps2an", *a], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
def copy(rel, dst):
    s = os.path.join(ROOT, rel); d = os.path.join(dst, rel)
    if os.path.isdir(s): shutil.copytree(s, d, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    else: os.makedirs(os.path.dirname(d), exist_ok=True); shutil.copy2(s, d)
def pack(stage, out):
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, 9) as z:
        for d, _, fs in os.walk(stage):
            for f in sorted(fs): p = os.path.join(d, f); z.write(p, os.path.join(NAME, os.path.relpath(p, stage)))
    print("%-34s %6.1f MB" % (os.path.basename(out), os.path.getsize(out) / 1e6))

def main():
    shutil.rmtree(DIST, ignore_errors=True); os.makedirs(STAGE)
    if os.path.exists(ELF):
        run("symbols", ELF); run("stubs", ELF)            # refresh public metadata
    for r in PUBLIC: copy(r, STAGE)
    bad = check(STAGE)
    if bad: sys.exit("public package blocked: %s" % bad)
    pack(STAGE, os.path.join(DIST, "%s-public.zip" % NAME))
    # ---- dev ----
    if not os.path.exists(ELF): print("no ELF in game/, dev package skipped"); return
    os.makedirs(os.path.join(STAGE, "game")); shutil.copy2(ELF, os.path.join(STAGE, "game"))
    if os.path.exists(GZF): os.makedirs(os.path.join(STAGE, "ghidra")); shutil.copy2(GZF, os.path.join(STAGE, "ghidra"))
    pv = os.path.join(STAGE, "private"); os.makedirs(pv)
    def out(name, *a):
        with open(os.path.join(pv, name), "w") as fh: subprocess.run([sys.executable, "-m", "ps2an", *a], cwd=ROOT, check=True, stdout=fh)
    out("strings.txt", "strings", ELF); out("embedded_modules.txt", "embedded", ELF)
    out("xrefs_sdk_libs.txt", "xrefs", ELF, r"lib[a-z0-9]+|sce[A-Z]|sq[A-Z]|\.irx|\.erx")
    out("xrefs_asset_paths.txt", "xrefs", ELF, r"^data/")
    if os.path.exists(GZF): out("ghidra_compare.txt", "ghidra", ELF, GZF)
    run("split", ELF, "-o", os.path.join(pv, "asm"))
    open(os.path.join(STAGE, "DEV_README.md"), "w").write(
        "# DEV PACKAGE - PRIVATE\n\nContains the game ELF, a Ghidra project and generated disassembly.\n"
        "**Never upload, push or share this archive.**\n\n"
        "- `game/` the ELF (git-ignored)\n- `ghidra/` .gzf project\n"
        "- `private/` strings, xrefs, per-function asm (`private/asm`, same layout as `make split`)\n\n"
        "Use: `make split` writes to `build/asm`; `INCLUDE_ASM` in `src/` reads from there.\n"
        "Publish only the *-public.zip content.\n")
    pack(STAGE, os.path.join(DIST, "%s-dev.zip" % NAME)); shutil.rmtree(STAGE)

if __name__ == "__main__": main()
