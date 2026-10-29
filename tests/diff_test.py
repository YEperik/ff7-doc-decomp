"""Differential test: C in src/libc/libc.c (host gcc) vs original code (ps2an emulator).
Usage: python tests/diff_test.py game/SLPM_666.29"""
import ctypes, os, random, subprocess, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ps2an.elf import Elf; from ps2an import analyze as A, ident
from ps2an.emu import CPU, Mem, Unsupported, M32

ROOT = os.path.join(os.path.dirname(__file__), "..")
def build():
    so = os.path.join(tempfile.mkdtemp(), "libc_ref.so")
    subprocess.run(["gcc", "-O2", "-shared", "-fPIC", "-fno-builtin", "-w", "-o", so, os.path.join(ROOT, "src/libc/libc.c")], check=True)
    return ctypes.CDLL(so)

B = 0x01000000           # emulator base address of the shared test arena
ARENA = 512
def sgn(x): return (x > 0) - (x < 0)

# name -> (arg kinds, result kind). kinds: p = pointer into arena (offset), s = size, c = char/int, "str" arenas hold NUL-terminated data.
SIG = {"strlen": ("p", "n"), "memchr": ("pcs", "p"), "memcpy": ("pps", "p"), "memmove": ("pps", "p"), "memset": ("pcs", "p"),
       "memcmp": ("pps", "sign"), "strchr": ("pc", "p"), "strcmp": ("pp", "sign"), "strncmp": ("pps", "sign"),
       "strcpy": ("pp", "p"), "strncpy": ("pps", "p"), "bzero": ("ps", "none")}

STRFN = {"strlen", "strchr", "strcmp", "strncmp", "strcpy", "strncpy"}
def trial(name, rng):
    """Random arena. Reads come from region A (0..159) / B (200..359); writes go to 300+ (or overlap inside A for memmove)."""
    alpha = rng.choice([b"abc", b"\x80\xff\x90", b"abc\x80\xffz"])
    arena = bytearray(rng.choice(alpha) for _ in range(ARENA))
    al = lambda: rng.choice([0, 16, 32, 48]) if rng.random() < .5 else rng.randrange(0, 16)
    kinds = SIG[name][0]; offs = []; pi = 0
    for k in kinds:
        if k == "p":
            if name == "memmove": offs.append(al() + rng.choice([0, 0, 16, 32, 5]))
            elif name in ("memcpy", "strcpy", "strncpy"): offs.append(300 + al() if pi == 0 else al())
            elif name in ("memset", "bzero"): offs.append(300 + al())
            else: offs.append(al() if pi == 0 else 200 + al())
            pi += 1
        elif k == "c": offs.append(rng.choice([0, 97, 98, 99, 122, 128, 255, 100, 0x90]))
        else: offs.append(rng.randint(0, 12) if rng.random() < .4 else rng.randint(13, 120))
    if name in STRFN:                                    # terminate every read string somewhere ahead of its pointer
        reads = [offs[1]] if name in ("strcpy", "strncpy") else [offs[0]] + ([offs[1]] if len(offs) > 1 and kinds[1] == "p" else [])
        for o in reads: arena[o + (rng.randint(0, 20) if rng.random() < .4 else rng.randint(21, 110))] = 0
        if name in ("strcmp", "strncmp") and rng.random() < .6:      # make the strings share a prefix
            n = rng.randint(1, 100); arena[offs[1]:offs[1] + n] = arena[offs[0]:offs[0] + n]
            if rng.random() < .5: arena[offs[1] + rng.randrange(n)] ^= 0x40
    if name in ("memcmp",) and rng.random() < .6:
        n = max(1, offs[2]); arena[offs[1]:offs[1] + n] = arena[offs[0]:offs[0] + n]
        if rng.random() < .5: arena[offs[1] + rng.randrange(n)] ^= 0x01
    return arena, kinds, offs

def run_ref(lib, name, arena, kinds, offs):
    buf = (ctypes.c_ubyte * ARENA).from_buffer_copy(bytes(arena)); base = ctypes.addressof(buf)
    f = getattr(lib, name); args = []; types = []
    for k, o in zip(kinds, offs):
        if k == "p": args.append(base + o); types.append(ctypes.c_void_p)
        elif k == "c": args.append(o); types.append(ctypes.c_int)
        else: args.append(o); types.append(ctypes.c_size_t)
    f.argtypes = types; f.restype = ctypes.c_void_p if SIG[name][1] in ("p",) else ctypes.c_long
    r = f(*args); res = SIG[name][1]
    if res == "p": r = None if r is None else r - base
    elif res == "sign": r = sgn(ctypes.c_int(r).value)
    elif res == "none": r = None
    return r, bytes(buf)

def run_orig(elf, addr, name, arena, kinds, offs):
    m = Mem(); m.wr(B, bytes(arena)); cpu = CPU(lambda pc: int.from_bytes(elf.read(pc, 4), "little"), m)
    args = [B + o if k == "p" else o for k, o in zip(kinds, offs)]
    r = cpu.run(addr, args, limit=20000) & M32; res = SIG[name][1]
    if res == "p": r = None if r == 0 else r - B
    elif res == "sign": r = sgn(r - (1 << 32) if r & 0x80000000 else r)
    elif res == "none": r = None
    return r, m.rd(B, ARENA)

def main(elf_path, trials=400):
    elf = Elf(elf_path); t = A.func_table(elf, A.find_functions(elf)); ver, lik = ident.identify(elf, t)
    lib = build(); rows = []; fail = 0
    for conf, group in (("verified", ver), ("likely", lik)):
        for name, addrs in sorted(group.items()):
            if name not in SIG: continue
            for addr in addrs:
                rng = random.Random(hash(name) & 0xFFFF); ok = ran = 0
                for _ in range(trials):
                    arena, kinds, offs = trial(name, rng)
                    try: o = run_orig(elf, addr, name, arena, kinds, offs)
                    except (Unsupported, KeyError): continue          # fast path (128-bit ops) not executable
                    ran += 1; ok += (o == run_ref(lib, name, arena, kinds, offs))
                rows.append((name, addr, conf, ok, ran)); fail += (ok != ran or ran < trials // 4)
    for name, addr, conf, ok, ran in rows:
        print("%-8s 0x%08x  %-8s  %4d/%-4d  %s" % (name, addr, conf, ok, ran, "PASS" if ok == ran and ran >= trials // 4 else "FAIL"))
    print("RESULT:", "FAIL" if fail else "ALL PASS"); sys.exit(1 if fail else 0)

if __name__ == "__main__": main(sys.argv[1] if len(sys.argv) > 1 else "game/SLPM_666.29")
