"""Differential test of src/game/*.c against the original functions.
Guest memory is mapped at identical addresses on the host, so the C code and the emulated
original operate on the very same pointers. Also requires 100% instruction coverage of the original.
Usage: python tests/game_test.py game/SLPM_666.29"""
import ctypes, glob, mmap, os, re, random, struct, subprocess, sys, tempfile
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."); sys.path.insert(0, ROOT)
from ps2an.elf import Elf; from ps2an import analyze as A
from ps2an.emu import CPU, Mem, Unsupported, M32

libc = ctypes.CDLL(None, use_errno=True)
libc.mmap.restype = ctypes.c_void_p
libc.mmap.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_long]
ARENA, ARENA_SZ = 0x01000000, 0x20000
GV_OFF = 0x40000000

class SnapMem(Mem):
    """Emulator memory = immutable snapshot of the guest regions + overlay of the writes the original makes."""
    def __init__(self, snaps): super().__init__({}); self.snaps = snaps          # [(addr, bytes)]
    def rd(self, a, n):
        out = bytearray()
        for i in range(n):
            x = (a + i) & M32
            if x in self.b: out.append(self.b[x]); continue
            for ra, data in self.snaps:
                if ra <= x < ra + len(data): out.append(data[x - ra]); break
            else: raise KeyError(hex(x))
        return bytes(out)
    def final(self, ra, data):
        buf = bytearray(data)
        for x, v in self.b.items():
            if ra <= x < ra + len(buf): buf[x - ra] = v
        return bytes(buf)

class Env:
    def __init__(self): self.regions = []; self.off = {}
    def region(self, addr, size, off=0):
        """Guest [addr, addr+size) lives on the host at addr+off (off=0: identical address)."""
        r = libc.mmap(addr + off, size, 3, 0x22 | 0x100000, -1, 0)      # PRIVATE|ANON|FIXED_NOREPLACE
        if r != addr + off: raise RuntimeError("cannot map guest region %#x (got %s)" % (addr, r))
        self.regions.append((addr, size)); self.off[addr] = off
    def hoff(self, a):
        for ra, n in self.regions:
            if ra <= a < ra + n: return self.off[ra]
        raise KeyError(hex(a))
    def write(self, addr, data): ctypes.memmove(addr + self.hoff(addr), bytes(data), len(data))
    def w32(self, addr, v): self.write(addr, struct.pack("<I", v & M32))
    def randomize(self, rng):
        for a, n in self.regions: self.write(a, rng.randbytes(n))
    def host(self, a, n): return ctypes.string_at(a + self.hoff(a), n)

def s32(x): x &= M32; return x - (1 << 32) if x & 0x80000000 else x
def ri32(r): return r.choice([0, 1, -1, 2, 7, -7, 0x7FFFFFFF, -0x80000000, r.randint(-100000, 100000), r.getrandbits(32) - (1 << 31)])

# ---- trial generators: each returns the argument list; they may patch memory through env ----
def p_ctx(r, env):
    sp = ARENA + 0x100 + 8 * r.randint(0, 100); env.w32(ARENA + 0xF014, sp); return ARENA, sp
def g_pop(r, env): return [p_ctx(r, env)[0]]
def g_push(r, env): return [p_ctx(r, env)[0], ri32(r)]
def g_drop(r, env): c, _ = p_ctx(r, env); return [c, 0 if r.random() < .4 else ARENA + 0x1000 + 8 * r.randint(0, 50)]
def g_none(r, env): return []
def g_s32(r, env): return [ri32(r)]
def g_shift(r, env): return [r.randint(-3, 70)]
def g_copy(r, env):
    s = ARENA + 16 * r.randint(0, 200); d = s if r.random() < .15 else ARENA + 0x2000 + 16 * r.randint(0, 200); return [d, s]
def g_obj(r, env):
    for off in (0x20, 0x17c): 
        if r.random() < .5: env.w32(ARENA + off, 0)
    return [ARENA]
def g_find(r, env):
    n = r.randint(0, 6); nodes = [ARENA + 0x4000 + 0x40 * i for i in range(n)]
    for i, a in enumerate(nodes): env.write(a + 3, bytes([r.choice([1, 2, 3, 0xFE, 0xFF, 0])])); env.w32(a + 0x30, nodes[i + 1] if i + 1 < n else 0)
    env.w32(ARENA + 0x24, nodes[0] if nodes else 0)
    return [ARENA, r.choice([1, 2, 3, 0, 0xFE, 0xFF, 0x1FF, 0x102, r.getrandbits(32)])]
def g_lookup(r, env):
    env.w32(ARENA + 0x24, ARENA + 0x1000)
    for i in range(41):
        e = 0 if r.random() < .25 else ARENA + 0x3000 + 8 * r.randint(0, 20); env.w32(ARENA + 0x1000 + 4 * i, e)
    for i in range(21): env.w32(ARENA + 0x3000 + 8 * i, r.getrandbits(32)); env.w32(ARENA + 0x3004 + 8 * i, r.getrandbits(32))
    return [ARENA, r.choice([r.randint(0, 40), r.randint(0, 40) + 0x10000, 0xFFFF0000 | r.randint(0, 40)])]
def g_spans(r, env):
    n = r.choice([-2, 0, 1, 2, 3, 5, 8]); env.w32(ARENA + 0xC, n & M32); env.w32(ARENA + 0x18, ARENA + 0x1000)
    objs = [ARENA + 0x3000 + 16 * i for i in range(12)]
    for a in objs: env.w32(a + 4, r.randint(0, 20)); env.w32(a + 8, r.randint(0, 20))
    for i in range(12): env.w32(ARENA + 0x1000 + 4 * i, r.choice(objs))
    return [ARENA]
def g_flags(r, env): return [ARENA, r.choice([0, 1, -1, 5]), r.choice([-5, -1, 0, 3, 200, 0x1FF])]

GLOBAL_PAGES = [0x4ef000, 0x46d000, 0x4b8000, 0x46b000]
# name, guest address, argument generator, return kind ("s32" | "ptr" | "void")
SPECS = [
 ("cstack_pop", 0x003aa140, g_pop, "s32"), ("cstack_push_int", 0x003aa0c0, g_push, "void"), ("cstack_drop", 0x003aa108, g_drop, "void"),
 ("get_gvar_004efda0", 0x003a8db8, g_none, "s32"), ("get_gvar_0046de04", 0x002e14e8, g_none, "s32"),
 ("get_gvar_004b8d9c", 0x00241a00, g_none, "s32"), ("set_gvar_004b8d9c", 0x002419f0, g_s32, "void"),
 ("get_gvar_004b8d3c", 0x00241a10, g_none, "s32"), ("set_gvar_0046b3d4", 0x002413e0, g_s32, "void"),
 ("get_flag_004b8cc8", 0x002419d8, g_shift, "s32"), ("has_flag_004b8b80", 0x002413c0, g_shift, "s32"),
 ("copy16", 0x00444eb8, g_copy, "void"), ("FUN_0055a570", 0x0055a570, g_obj, "s32"), ("FUN_00316d38", 0x00316d38, g_obj, "s32"),
 ("FUN_002535e0", 0x002535e0, g_s32, "s32"), ("FUN_003cb2f8", 0x003cb2f8, g_find, "ptr"), ("FUN_002533b0", 0x002533b0, g_lookup, "s32"),
 ("FUN_002533f0", 0x002533f0, g_spans, "s32"), ("FUN_00340bf8", 0x00340bf8, g_flags, "void"),
]

def check_manifest():
    got = {m.group(1): int(m.group(2), 16) for m in (re.match(r"\s*(\w+)\s*=\s*(0x[0-9a-fA-F]+);", l) for l in open(os.path.join(ROOT, "src/game/decomp.txt"))) if m}
    want = {n: a for n, a, _g, _r in SPECS}
    if got != want: sys.exit("src/game/decomp.txt does not match SPECS: %s" % sorted(set(got.items()) ^ set(want.items())))

def build():
    so = os.path.join(tempfile.mkdtemp(), "game_ref.so"); srcs = sorted(glob.glob(os.path.join(ROOT, "src/game/*.c")))
    subprocess.run(["gcc", "-O2", "-shared", "-fPIC", "-fno-builtin", "-fno-strict-aliasing", "-fwrapv", "-w", "-DGV_BASE=%dUL" % GV_OFF, "-I", os.path.join(ROOT, "src/include"), "-o", so, *srcs], check=True)
    return ctypes.CDLL(so)

def main(elf_path, trials=500):
    check_manifest(); elf = Elf(elf_path); table = A.func_table(elf, A.find_functions(elf, A.load_overrides(os.path.join(ROOT, "symbols/overrides.txt"))))
    size = {a: s for a, s, _, _ in table}; lib = build(); fetch = lambda pc: int.from_bytes(elf.read(pc, 4), "little"); bad = 0
    env = Env(); env.region(ARENA, ARENA_SZ)
    for pg in GLOBAL_PAGES: env.region(pg, 0x1000, GV_OFF)
    for name, addr, gen, rk in SPECS:
        f = getattr(lib, name); f.restype = ctypes.c_int64 if rk != "ptr" else ctypes.c_void_p
        rng = random.Random(addr); ok = 0; seen = set()
        for _ in range(trials):
            env.randomize(rng); args = gen(rng, env)
            snaps = [(a_, env.host(a_, n)) for a_, n in env.regions]
            f.argtypes = [ctypes.c_int64 if a_ < 0 else ctypes.c_uint64 for a_ in args]
            cr = f(*args); cr = (cr or 0) & M32 if rk != "void" else 0
            mem = SnapMem(snaps); cpu = CPU(fetch, mem)
            try: orv = cpu.run(addr, [x & 0xFFFFFFFFFFFFFFFF for x in args], limit=5000) & M32 if rk != "void" else cpu.run(addr, [x & 0xFFFFFFFFFFFFFFFF for x in args], limit=5000) and 0
            except (Unsupported, KeyError) as ex: print("ERR", name, ex); bad += 1; break
            seen |= cpu.seen
            same = (cr == orv) and all(env.host(a_, n) == mem.final(a_, d) for (a_, d), (_, n) in zip(snaps, env.regions)); ok += same
        body = [addr + 4 * i for i in range(size[addr] // 4) if fetch(addr + 4 * i) != 0]; cov = len(set(body) & seen) / len(body)
        good = ok == trials and cov >= 0.999; bad += not good
        print("%-20s 0x%08x  %4d/%-4d  cov %3.0f%%  %s" % (name, addr, ok, trials, 100 * cov, "PASS" if good else "FAIL"))
    print("RESULT:", "FAIL" if bad else "ALL PASS"); sys.exit(1 if bad else 0)

if __name__ == "__main__": main(sys.argv[1] if len(sys.argv) > 1 else "game/SLPM_666.29")
