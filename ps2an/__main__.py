"""ps2an CLI:  python -m ps2an <command> <elf> [options]"""
import argparse, csv, json, os, sys
from .elf import Elf
from . import analyze as A, mips

OVERRIDES = "symbols/overrides.txt"
DECOMP = "src/game/decomp.txt"
def load(path):
    e = Elf(path); f = A.find_functions(e, A.load_overrides(OVERRIDES)); t = A.func_table(e, f); return e, t

def named(e, t):
    """{addr: (name, evidence)}"""
    from . import ident
    cache = os.path.join("build", "ident_%s.json" % e.sha256[:12])
    if os.path.exists(cache) and os.path.getmtime(cache) > os.path.getmtime(__file__): return {int(k): tuple(v) for k, v in json.load(open(cache)).items()}
    out = {a: (n, "syscall") for a, n in A.name_syscalls(e, t).items()}
    out.update({a: (n, "sdk-string") for a, n in A.name_sdk(e, t).items()})
    ver, lik = ident.identify(e, t); seen = {}
    def is_thunk(a):
        return e.read(a + 4, 4) == b"\0\0\0\0" and int.from_bytes(e.read(a, 4), "little") >> 26 == 2
    for grp in (ver, lik):
        for nm in list(grp): grp[nm] = [a for a in grp[nm] if not is_thunk(a)]
    for conf, grp in (("verified", ver), ("likely", lik)):
        for nm, addrs in grp.items():
            for a in addrs:
                seen[nm] = seen.get(nm, 0) + 1; out[a] = (nm if seen[nm] == 1 else "%s_%d" % (nm, seen[nm]), "behavior-" + conf)
    out.update({a: (n, "manual") for a, n in A.load_overrides(OVERRIDES).items() if not n.startswith("FUN_")})
    out.update({a: (n, "decomp-verified") for a, n in A.load_overrides(DECOMP).items() if not n.startswith("FUN_")})
    for a, size, _s, _sec in t:                      # `j target ; nop` where target is a named function
        if size >= 8 and (a not in out or out[a][1] in ('thunk',)):
            w0 = int.from_bytes(e.read(a, 4), "little"); w1 = int.from_bytes(e.read(a + 4, 4), "little")
            if w0 >> 26 == 2 and w1 == 0:
                tgt = ((a + 4) & 0xF0000000) | ((w0 & 0x3FFFFFF) << 2)
                if tgt in out and out[tgt][1] != "thunk": out[a] = (out[tgt][0] + "_alias", "thunk")
    os.makedirs("build", exist_ok=True); json.dump(out, open(cache, "w"))
    return out

def names(e, t): return {a: n for a, (n, _) in named(e, t).items()}

def cmd_info(a):
    e = Elf(a.elf)
    print("file    :", os.path.basename(a.elf), "(%d bytes)" % len(e.data))
    print("sha256  :", e.sha256)
    print("entry   : 0x%08x   flags: 0x%08x" % (e.entry, e.flags))
    print("\nsegments:")
    for s in e.segments:
        if s.type == 1: print("  LOAD 0x%08x  file 0x%06x  mem 0x%06x" % (s.vaddr, s.filesz, s.memsz))
    print("\nsections (loaded):")
    for s in e.sections:
        if s.alloc and s.addr:
            print("  %-42s 0x%08x  0x%06x  %s%s" % (s.name, s.addr, s.size, "X" if s.exec else "-", " bss" if s.nobits else ""))
    ov = [s for s in e.sections if s.name.startswith(".DVP")]
    print("\noverlay blobs: %d (%d bytes), embedded modules: %d" % (len(ov), sum(s.size for s in ov), len(A.find_embedded_elf(e))))

def cmd_functions(a):
    e, t = load(a.elf); n = names(e, t)
    w = csv.writer(open(a.o, "w", newline="") if a.o else sys.stdout, lineterminator="\n")
    w.writerow(["address", "size", "source", "section", "name"])
    for ad, sz, src, sec in t: w.writerow(["0x%08x" % ad, sz, src, sec, n.get(ad, "FUN_%08x" % ad)])
    if a.o: print("%d functions -> %s" % (len(t), a.o))

def cmd_strings(a):
    e = Elf(a.elf)
    for ad, s in A.find_strings(e, a.min):
        print("0x%08x  %s" % (ad, s.replace("\n", "\\n")))

def cmd_xrefs(a):
    import re
    e, t = load(a.elf); st = [x for x in A.find_strings(e) if re.search(a.pattern, x[1])]
    refs = A.find_xrefs(e, {x[0] for x in st}); starts = [x[0] for x in t]; by = {}
    for ad, s in st:
        for pc in refs.get(ad, []): by.setdefault(A.owner(starts, pc), []).append(s)
    for f, ss in sorted(by.items()): print("FUN_%08x  %s" % (f, " | ".join(x.strip()[:60] for x in ss[:3])))

def cmd_sdk(a):
    e, t = load(a.elf)
    for ad, n in sorted(names(e, t).items()): print("0x%08x  %s" % (ad, n))

def cmd_embedded(a):
    e = Elf(a.elf)
    for off, size, typ, mach in A.find_embedded_elf(e):
        print("file+0x%06x  size 0x%05x  e_type 0x%04x  machine %d" % (off, size, typ, mach))

def cmd_symbols(a):
    e, t = load(a.elf); nv = named(e, t); n = {k: v[0] for k, v in nv.items()}; os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "functions.csv"), "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n"); w.writerow(["address", "size", "section", "name"])
        for ad, sz, _s, sec in t: w.writerow(["0x%08x" % ad, sz, sec, n.get(ad, "FUN_%08x" % ad)])
    with open(os.path.join(a.out, "named.txt"), "w") as fh:
        for ad, (nm, ev) in sorted(nv.items()): fh.write("%s = 0x%08x; // %s\n" % (nm, ad, ev))
    print("%d functions, %d named -> %s/" % (len(t), len(n), a.out))

def cmd_disasm(a):
    e, t = load(a.elf); n = names(e, t); inv = {v: k for k, v in n.items()}
    ad = inv[a.target] if a.target in inv else int(a.target, 0)
    size = next((s for x, s, *_ in t if x == ad), a.n * 4)
    for i in range(min(size, a.n * 4) // 4):
        pc = ad + i * 4; w = int.from_bytes(e.read(pc, 4), "little")
        print("%08x:  %08x  %s" % (pc, w, mips.decode(w, pc)))

def cmd_split(a):
    e, t = load(a.elf); n = names(e, t)
    for ad, sz, _s, sec in t:
        d = os.path.join(a.out, sec.strip(".")); os.makedirs(d, exist_ok=True)
        nm = n.get(ad, "FUN_%08x" % ad)
        with open(os.path.join(d, nm + ".s"), "w") as fh:
            fh.write("# %s  0x%08x  size 0x%x\n.set noreorder\n.global %s\n%s:\n" % (nm, ad, sz, nm, nm))
            for i in range(sz // 4):
                pc = ad + i * 4; w = int.from_bytes(e.read(pc, 4), "little")
                fh.write("  /* %08x %08x */ %s\n" % (pc, w, mips.decode(w, pc)))
    print("asm written to", a.out)

def cmd_stubs(a):
    e, t = load(a.elf); n = names(e, t)
    done = set(A.load_overrides(DECOMP).values())          # these already have C in src/game/
    n = {a: nm for a, nm in n.items() if nm not in done}
    L = ['#include "ps2types.h"', "", "/* Auto-generated by `ps2an stubs`. Bodies come from your local asm/ (see `ps2an split`). */", ""]
    for ad, nm in sorted(n.items()):
        L.append("/* 0x%08x */\nINCLUDE_ASM(\"text\", %s);\n" % (ad, nm))
    open(a.o, "w").write("\n".join(L)); print("%d stubs -> %s" % (len(n), a.o))

def cmd_ident(a):
    from . import ident
    e, t = load(a.elf); ver, lik = ident.identify(e, t)
    for conf, g in (("verified", ver), ("likely", lik)):
        for nm, addrs in sorted(g.items()):
            for ad in addrs: print("0x%08x  %-8s %s" % (ad, nm, conf))

def cmd_match(a):
    """Compile every reconstructed function with `ps2an cc` and compare with the original bytes."""
    import glob, re, struct
    from . import cc
    e, t = load(a.elf); decomp = A.load_overrides(DECOMP); size = {x[0]: x[1] for x in t}
    srcs = {}
    for f in sorted(glob.glob("src/game/*.c")):
        txt = open(f).read()
        for nm in decomp.values():
            if re.search(r"\b%s\s*\(" % re.escape(nm), txt) and re.search(r"^[\w\s\*]+\b%s\s*\([^;]*\)\s*\{" % re.escape(nm), txt, re.M): srcs[nm] = f
    symbols = {nm: ad for ad, (nm, _ev) in named(e, t).items()}; symbols.update({nm: ad for ad, nm in decomp.items()})
    matched = []; rows = []
    for ad, nm in sorted(decomp.items()):
        f = srcs.get(nm)
        if not f: continue
        try: words, lines = cc.compile_function(f, nm, symbols=symbols)
        except cc.Unsupported as ex: rows.append((nm, ad, "unsupported", str(ex))); continue
        except Exception as ex: rows.append((nm, ad, "error", "%s: %s" % (type(ex).__name__, str(ex)[:60]))); continue
        orig = [int.from_bytes(e.read(ad + 4 * i, 4), "little") for i in range(len(words))]
        if orig == words: matched.append(nm); rows.append((nm, ad, "MATCH", "%d instructions" % len(words)))
        else:
            n = next((i for i in range(len(words)) if words[i] != orig[i]), 0)
            rows.append((nm, ad, "differs", "first diff at +0x%x: want %s, got %s" % (4 * n, mips.decode(orig[n], ad + 4 * n), lines[n])))
    for nm, ad, st, info in rows: print("%-26s 0x%08x  %-11s %s" % (nm, ad, st, info))
    print("matched %d of %d reconstructed" % (len(matched), len(decomp)))
    if a.write:
        open("src/game/matched.txt", "w").write("# Functions whose C compiles (ps2an cc) to the exact original instructions\n" + "".join("%s = 0x%08x;\n" % (nm, ad) for ad, nm in sorted(decomp.items()) if nm in matched))

def cmd_progress(a):
    from . import progress as P
    m = P.compute(a.root)
    if a.record: P.record(a.root, m, a.record, a.date)
    if a.check:
        bad = P.check(a.root, m)
        print("progress files in sync" if not bad else "OUT OF DATE (run: python -m ps2an progress): " + ", ".join(bad)); sys.exit(1 if bad else 0)
    P.write_all(a.root, m)
    print("functions %d/%d (%.2f%%)  bytes %.2f%%  hubs %d/%d" % (m["functions_done"], m["functions_total"], m["functions_pct"], m["bytes_pct"], m["hubs_done"], m["hubs_total"]))

def cmd_tail(a):
    """Research: low-confidence tiny-function candidates (not part of the default function list)."""
    e = Elf(a.elf); f = A.find_functions(e, A.load_overrides(OVERRIDES), tail=True); n = 0
    with open(a.o, "w") as fh:
        for ad, src in f.items():
            if src == "tail": fh.write("0x%08x\n" % ad); n += 1
    print("%d tail candidates -> %s (unverified)" % (n, a.o))

def cmd_hubs(a):
    """Most-called functions, flagged leaf/emulatable: the best next decompilation targets."""
    from . import ident
    import struct
    e, t = load(a.elf); n = names(e, t); cg = A.call_graph(e, t); info = {x[0]: x for x in t}; rows = []
    for ad, callers in cg.items():
        _a, size, _src, sec = info[ad]; W = struct.unpack("<%dI" % (size // 4), e.read(ad, size))
        leaf = not any(w >> 26 == 3 or (w & 0xFC00003F) == 0xC for w in W)
        emu = leaf and all(ident.supported(w, ad + 4 * i) for i, w in enumerate(W))
        rows.append((ad, n.get(ad, "FUN_%08x" % ad), len(callers), size, int(leaf), int(emu), sec))
    rows.sort(key=lambda r: -r[2])
    os.makedirs(os.path.dirname(a.o) or ".", exist_ok=True)
    w = csv.writer(open(a.o, "w", newline=""), lineterminator="\n"); w.writerow(["address", "name", "callers", "size", "leaf", "emulatable", "section"])
    for r in rows[:a.top]: w.writerow(["0x%08x" % r[0]] + list(r[1:]))
    print("%d called functions; top %d -> %s  (leaf+emulatable in top: %d)" % (len(rows), min(a.top, len(rows)), a.o, sum(r[5] for r in rows[:a.top])))

def cmd_ghidra(a):
    e, t = load(a.elf); mine = {x[0] for x in t}; g = set(A.gzf_functions(a.gzf)); hit = mine & g
    print("ps2an: %d   ghidra: %d   shared: %d" % (len(mine), len(g), len(hit)))
    print("recall    %.1f%%  (ghidra funcs found by ps2an)" % (100.0 * len(hit) / len(g)))
    print("precision %.1f%%  (ps2an funcs confirmed by ghidra)" % (100.0 * len(hit) / len(mine)))

def cmd_verify(a):
    cfg = json.load(open(a.config)); e = Elf(a.elf)
    ok = e.sha256 == cfg["sha256"]; print("OK" if ok else "MISMATCH", e.sha256); sys.exit(0 if ok else 1)

def main():
    p = argparse.ArgumentParser(prog="ps2an", description=__doc__); sp = p.add_subparsers(dest="cmd", required=True)
    def add(name, fn, h, **kw):
        s = sp.add_parser(name, help=h); s.set_defaults(fn=fn)
        if kw.get("elf", True): s.add_argument("elf", help="path to the game ELF")
        return s
    add("info", cmd_info, "headers, segments, sections")
    s = add("functions", cmd_functions, "detect functions (csv)"); s.add_argument("-o")
    s = add("strings", cmd_strings, "ASCII strings in data sections"); s.add_argument("--min", type=int, default=4)
    s = add("xrefs", cmd_xrefs, "functions referencing strings matching a regex"); s.add_argument("pattern")
    add("sdk", cmd_sdk, "SDK / kernel function names")
    add("ident", cmd_ident, "name libc-like functions by running them in the emulator")
    s = add("match", cmd_match, "compile reconstructed C with ps2an cc and compare bytes"); s.add_argument("--write", action="store_true")
    s = add("progress", cmd_progress, "update progress files from public metadata", elf=False); s.add_argument("--root", default="."); s.add_argument("--record", metavar="LABEL"); s.add_argument("--date"); s.add_argument("--check", action="store_true")
    s = add("tail", cmd_tail, "research: tiny-function candidates (unverified)"); s.add_argument("-o", default="build/tail_candidates.txt")
    s = add("hubs", cmd_hubs, "most-called functions (decompilation targets)"); s.add_argument("-o", default="symbols/hubs.csv"); s.add_argument("--top", type=int, default=300)
    add("embedded", cmd_embedded, "embedded ELF modules (IRX/ERX)")
    s = add("symbols", cmd_symbols, "write symbols/ (public-safe)"); s.add_argument("-o", dest="out", default="symbols")
    s = add("disasm", cmd_disasm, "disassemble a function"); s.add_argument("target"); s.add_argument("-n", type=int, default=64)
    s = add("split", cmd_split, "write per-function .s files (local only)"); s.add_argument("-o", dest="out", default="build/asm")
    s = add("stubs", cmd_stubs, "write C stubs for named functions"); s.add_argument("-o", default="src/stubs/sdk_stubs.c")
    s = add("ghidra", cmd_ghidra, "compare against a Ghidra .gzf"); s.add_argument("gzf")
    s = add("verify", cmd_verify, "check ELF sha256 against config"); s.add_argument("--config", default="config/game.json")
    a = p.parse_args(); a.fn(a)

if __name__ == "__main__": main()
