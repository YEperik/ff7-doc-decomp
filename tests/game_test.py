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

def g_lock(r, env): setup_lock(r, env, ARENA); return [ARENA]

LOCKQS = []
def setup_lock(r, env, q):
    LOCKQS.append(q); env.w32(q + 0x84, 0 if r.random() < .12 else r.getrandbits(32) | 1)
    w = r.randint(0, 31); mode = r.choice(["empty", "full", "mid", "mid"])
    rr = w if mode == "empty" else (w + 1) & 31 if mode == "full" else r.randint(0, 31)
    env.write(q + 0x80, struct.pack("<HH", rr, w))
def g_gq(r, env): setup_lock(r, env, 0x4dfd00); return []
def g_free(r, env): setup_lock(r, env, 0x4dfd00); return [r.getrandbits(32)]
def g_alloc(r, env): setup_lock(r, env, 0x4dfd00); return [r.choice([0, 1, 16, 0x1000, r.getrandbits(32)])]
def g_objlock(r, env): setup_lock(r, env, ARENA + 0x3d4); return [ARENA, r.choice([0, 1, -1, 7, 0, 1])]
def g_gv4fc(r, env):
    if r.random() < .4: env.w32(0x46b4fc, 0)
    return []
def g_obj54(r, env):
    if r.random() < .5: env.w32(ARENA + 0x108, 0)
    return [ARENA + 0x100, ARENA + 0x2000 + 16 * r.randint(0, 20)]
def g_5a3a48(r, env): env.w32(0x46f2e0, ARENA + 0x5000); return [ri32(r) & M32, ri32(r)]
def g_5a39e8(r, env): env.w32(0x46f2e0, ARENA + 0x5000); return [ARENA, r.choice([0, 1, 2, 3, 0x81, -1])]
def g_2a8060(r, env): env.w32(0x4ec258, ARENA + 0x6000); return [r.choice([0, 0, ri32(r), 5])]
def g_2e14f8(r, env): return [ri32(r), ri32(r), ri32(r), r.choice([1, 0, 2, -1, ri32(r)])]

# ---- mocked callees: one deterministic world drives both the C (via tests/shim.c) and the emulated original ----
# name -> (guest address, arity, argument kinds: v = compared value, o = output pointer, return kind)
CALLEES = {
 "DIntr": (0x0044cb68, 0, "", "bit"), "EIntr": (0x0044cbb0, 0, "", "bit"), "GetThreadId": (0x00451fd0, 0, "", "tid"),
 "SleepThread": (0x00452000, 0, "", None), "WakeupThread": (0x00452010, 1, "v", "zero"),
 "FUN_0042d398": (0x0042d398, 1, "v", None), "FUN_00248fd0": (0x00248fd0, 1, "v", None),
 "RotateThreadReadyQueue": (0x00451f90, 1, "v", "rand"), "FUN_00251150": (0x00251150, 1, "v", None),
 "FUN_002510b8": (0x002510b8, 3, "vvv", "rand"), "FUN_0054a7e8": (0x0054a7e8, 2, "vo", None),
 "FUN_0036f798": (0x0036f798, 2, "vv", "rand"), "FUN_002f3278": (0x002f3278, 2, "vv", "rand"), "FUN_0030b6b0": (0x0030b6b0, 3, "vvv", "rand"),
 "break": (None, 0, "", None),
}
class World:
    def __init__(self, seed, rd, wr, lockqs): self.rng = random.Random(seed); self.log = []; self.rd = rd; self.wr = wr; self.lockqs = lockqs
    def call(self, name, args=()):
        _a, arity, kinds, ret = CALLEES[name]
        self.log.append((name, tuple(x & M32 for x, k in zip(args[:arity], kinds) if k == "v")))
        if name == "FUN_0042d398":                                       # another thread drains every lock queue under test
            for q in self.lockqs: self.wr(q + 0x80, struct.pack("<H", (struct.unpack("<H", self.rd(q + 0x82, 2))[0] + 5) & 0x1F))
        if name == "FUN_0054a7e8": self.wr(args[1], self.rng.randbytes(0x40))      # fills the output buffer
        if ret == "bit": return self.rng.randint(0, 1)
        if ret == "tid": return struct.unpack("<i", self.rd(0x004b8cf8, 4))[0] if self.rng.random() < .5 else self.rng.randint(1, 60)
        if ret == "rand": return s32(self.rng.getrandbits(32))
        return 0

GLOBAL_PAGES = [0x4ef000, 0x46d000, 0x4b8000, 0x46b000, 0x4df000, 0x46f000, 0x4ec000]
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
 ("lock_acquire", 0x0042d428, g_lock, "void"), ("lock_release", 0x0042d590, g_lock, "void"),
 ("lock_acquire_004dfd00", 0x00251e30, g_gq, "void"), ("lock_release_004dfd00", 0x00251e50, g_gq, "void"),
 ("FUN_002521f0", 0x002521f0, g_free, "void"), ("FUN_00252160", 0x00252160, g_alloc, "s32"), ("FUN_002521a8", 0x002521a8, g_alloc, "s32"),
 ("FUN_00241de8", 0x00241de8, g_none, "s32"), ("FUN_00376198", 0x00376198, g_objlock, "void"), ("FUN_003761e8", 0x003761e8, g_objlock, "void"),
 ("get_gvar_0046b4fc", 0x002424a0, g_gv4fc, "s32"), ("FUN_00326540", 0x00326540, g_gv4fc, "s32"),
 ("FUN_0054a920", 0x0054a920, g_obj54, "void"), ("FUN_005a3a48", 0x005a3a48, g_5a3a48, "s32"), ("FUN_005a39e8", 0x005a39e8, g_5a39e8, "void"),
 ("FUN_002a8060", 0x002a8060, g_2a8060, "void"), ("FUN_002e14f8", 0x002e14f8, g_2e14f8, "s32"),
]

def check_manifest():
    got = {m.group(1): int(m.group(2), 16) for m in (re.match(r"\s*(\w+)\s*=\s*(0x[0-9a-fA-F]+);", l) for l in open(os.path.join(ROOT, "src/game/decomp.txt"))) if m}
    want = {n: a for n, a, _g, _r in SPECS}
    if got != want: sys.exit("src/game/decomp.txt does not match SPECS: %s" % sorted(set(got.items()) ^ set(want.items())))

def build():
    so = os.path.join(tempfile.mkdtemp(), "game_ref.so"); srcs = sorted(glob.glob(os.path.join(ROOT, "src/game/*.c"))) + [os.path.join(ROOT, "tests/shim.c")]
    subprocess.run(["gcc", "-O2", "-shared", "-fPIC", "-fno-builtin", "-fno-strict-aliasing", "-fwrapv", "-w", "-DGV_BASE=%dUL" % GV_OFF, "-DHOST_TEST", "-I", os.path.join(ROOT, "src/include"), "-o", so, *srcs], check=True)
    return ctypes.CDLL(so)

def host_write(env, a, d):
    try: env.write(a, d)
    except KeyError: ctypes.memmove(a, bytes(d), len(d))       # a real host pointer (e.g. a local buffer of the C code)

CBTYPE = ctypes.CFUNCTYPE(ctypes.c_int64, ctypes.c_char_p, ctypes.c_uint64, ctypes.c_uint64, ctypes.c_uint64, ctypes.c_uint64)

def main(elf_path, trials=500):
    check_manifest(); elf = Elf(elf_path); table = A.func_table(elf, A.find_functions(elf, A.load_overrides(os.path.join(ROOT, "symbols/overrides.txt"))))
    size = {a: s for a, s, _, _ in table}; lib = build(); fetch = lambda pc: int.from_bytes(elf.read(pc, 4), "little"); bad = 0
    env = Env(); env.region(ARENA, ARENA_SZ)
    for pg in GLOBAL_PAGES: env.region(pg, 0x1000, GV_OFF)
    cur = {}; reconstructed = {n for n, _a, _g, _r in SPECS}
    cb = CBTYPE(lambda n, a0, a1, a2, a3: cur["w"].call(n.decode(), (a0, a1, a2, a3))); lib.shim_set_cb(cb)
    only = set(filter(None, os.environ.get("ONLY", "").split(",")))          # e.g. ONLY=FUN_002e14f8,FUN_003761e8
    for name, addr, gen, rk in SPECS:
        if only and name not in only: continue
        f = getattr(lib, name); f.restype = ctypes.c_int64 if rk != "ptr" else ctypes.c_void_p
        rng = random.Random(addr); ok = 0; seen = set(); calls = 0
        for t in range(trials):
            LOCKQS.clear(); env.randomize(rng); args = gen(rng, env)
            snaps = [(a_, env.host(a_, n)) for a_, n in env.regions]
            f.argtypes = [ctypes.c_int64 if a_ < 0 else ctypes.c_uint64 for a_ in args]
            hw = World(t, lambda a_, n: env.host(a_, n), lambda a_, d: host_write(env, a_, d), list(LOCKQS)); cur["w"] = hw
            cr = f(*args); cr = (cr or 0) & M32 if rk != "void" else 0
            mem = SnapMem(snaps); cpu = CPU(fetch, mem)
            ew = World(t, lambda a_, n: mem.rd(a_, n), lambda a_, d: mem.wr(a_, d), list(LOCKQS))
            for cn, (ga, _ar, _k, _rt) in CALLEES.items():                   # callees that are not reconstructed run as mocks
                if ga is not None and cn not in reconstructed: cpu.hooks[ga] = (lambda c, n=cn: c.r.__setitem__(2, ew.call(n, (c.r[4], c.r[5], c.r[6], c.r[7])) & 0xFFFFFFFFFFFFFFFF))
            cpu.on_break = lambda c: ew.call("break")
            try: orv = cpu.run(addr, [x & 0xFFFFFFFFFFFFFFFF for x in args], limit=40000) & M32
            except (Unsupported, KeyError) as ex: print("ERR", name, ex); bad += 1; break
            orv = orv if rk != "void" else 0
            seen |= cpu.seen; calls += len(hw.log)
            same = (cr == orv) and hw.log == ew.log and all(env.host(a_, n) == mem.final(a_, d) for (a_, d), (_, n) in zip(snaps, env.regions)); ok += same
        body = [addr + 4 * i for i in range(size[addr] // 4) if fetch(addr + 4 * i) != 0]; cov = len(set(body) & seen) / len(body)
        good = ok == trials and cov >= 0.999; bad += not good
        print("%-24s 0x%08x  %4d/%-4d  cov %3.0f%%  %s%s" % (name, addr, ok, trials, 100 * cov, "PASS" if good else "FAIL", "  (%d calls compared)" % calls if calls else ""))
    print("RESULT:", "FAIL" if bad else "ALL PASS"); sys.exit(1 if bad else 0)

if __name__ == "__main__": main(sys.argv[1] if len(sys.argv) > 1 else "game/SLPM_666.29")
