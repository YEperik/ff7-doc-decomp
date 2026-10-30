"""Behavioural identification: run small leaf functions in the emulator and match them
against reference libc semantics. Evidence = every randomized trial agrees."""
import random, struct
from .emu import CPU, Mem, Unsupported, M32

SRC, DST, BUF = 0x01000000, 0x01100000, 0x01200000

def sgn(x): x = x & 0xFFFFFFFF; x = x - (1 << 32) if x & 0x80000000 else x; return (x > 0) - (x < 0)
def rn(r, small=12, big=90): return r.randint(0, small) if r.random() < .5 else r.randint(small + 1, big)
def rstr(r, lo=0, hi=12, alpha=b"abcAB 0\x7f\x80\xffz"): return bytes(r.choice(alpha) for _ in range(r.randint(lo, hi)))

def _mem(**regions):
    m = Mem()
    for a, d in regions.items(): pass
    return m
def mk(*pairs):
    m = Mem()
    for a, d in pairs: m.wr(a, d)
    return m

# each spec: name -> trial(rng) -> (args, mem, check(ret, mem) -> bool)
# Lengths mix short (byte loops) and long (>= 16, SIMD fast paths); pointers are sometimes 16-byte aligned.
def AL(r): return r.choice([0, 0, 0, 16, 1, 3, 5, 8, 15])
def ST(r, lo=0, alpha=b"abcAB 0\x7f\x80\xffz"): return bytes(r.choice(alpha) for _ in range(r.randint(lo, rn(r))))

def t_strlen(r):
    S0 = SRC + AL(r); s = ST(r); return (S0,), mk((S0, s + b"\0")), lambda ret, m: (ret & M32) == len(s)
def t_strcpy(r):
    S0 = SRC + AL(r); D0 = DST + AL(r); s = ST(r)
    return (D0, S0), mk((S0, s + b"\0"), (D0, b"\xee" * (len(s) + 24))), \
        lambda ret, m: (ret & M32) == D0 and m.rd(D0, len(s) + 1) == s + b"\0" and m.rd(D0 + len(s) + 1, 4) == b"\xee" * 4
def t_strcmp(r):
    S0 = SRC + AL(r); D0 = DST + AL(r); a = ST(r, 0, b"abc\x80"); b = a if r.random() < .4 else (a[:r.randint(0, len(a))] + ST(r, 0, b"abc\x80") if r.random() < .5 else ST(r, 0, b"abc\x80"))
    exp = (a > b) - (a < b); return (S0, D0), mk((S0, a + b"\0"), (D0, b + b"\0")), lambda ret, m: sgn(ret) == exp
def t_strncmp(r):
    S0 = SRC + AL(r); D0 = DST + AL(r); a = ST(r, 0, b"abc"); b = a if r.random() < .5 else (a[:r.randint(0, len(a))] + ST(r, 0, b"abc"))
    n = rn(r, 12, 90); A = a + b"\0" + bytes(r.choice(b"xyz") for _ in range(8)); B = b + b"\0" + bytes(r.choice(b"xyz") for _ in range(8))
    ca, cb = a[:n], b[:n]; exp = (ca > cb) - (ca < cb)
    return (S0, D0, n), mk((S0, A), (D0, B)), lambda ret, m: sgn(ret) == exp
def t_strncpy(r):
    if r.random() < .5:     # aligned, long: reaches the 16-byte copy loop
        S0 = SRC + r.choice([0, 16]); D0 = DST + r.choice([0, 16]); al = r.choice([b"abc", b"\x80\xff\x90"]); s_ = bytes(r.choice(al) for _ in range(r.randint(20, 90))); n = r.randint(16, 100)   # bytes >= 0x80 reach the 16-byte loop
    else:
        S0 = SRC + AL(r); D0 = DST + AL(r); s_ = ST(r, 0, b"abc"); n = rn(r, 12, 90)
    exp = (s_[:n] + bytes(n))[:n]
    return (D0, S0, n), mk((S0, s_ + b"\0" + b"xyzxyz"), (D0, b"\xee" * (n + 24))), \
        lambda ret, m: (ret & M32) == D0 and m.rd(D0, n) == exp and m.rd(D0 + n, 4) == b"\xee" * 4
def t_strcat(r):
    D0 = DST + AL(r); S0 = SRC + AL(r); a = ST(r, 0, b"abc"); b = ST(r, 0, b"abc")
    return (D0, S0), mk((D0, a + b"\0" + b"\xee" * (len(b) + 24)), (S0, b + b"\0")), \
        lambda ret, m: (ret & M32) == D0 and m.rd(D0, len(a) + len(b) + 1) == a + b + b"\0"
def t_strchr(r):
    S0 = SRC + AL(r); s = ST(r, 0, b"abc"); c = r.choice(b"abcd"); i = s.find(bytes([c]))
    return (S0, c), mk((S0, s + b"\0")), lambda ret, m: (ret & M32) == (0 if i < 0 else S0 + i)
def t_strrchr(r):
    S0 = SRC + AL(r); s = ST(r, 0, b"abc"); c = r.choice(b"abcd"); i = s.rfind(bytes([c]))
    return (S0, c), mk((S0, s + b"\0")), lambda ret, m: (ret & M32) == (0 if i < 0 else S0 + i)
def t_memchr(r):
    S0 = SRC + AL(r); n = rn(r, 20, 90); d = bytes(r.choice(b"abcd") for _ in range(100)); c = r.choice(b"abcde"); i = d[:n].find(bytes([c]))
    return (S0, c, n), mk((S0, d)), lambda ret, m: (ret & M32) == (0 if i < 0 else S0 + i)
def t_memcpy(r):
    n = rn(r, 40, 120); S0 = SRC + AL(r); D0 = DST + AL(r); s = bytes(r.randrange(256) for _ in range(n))
    return (D0, S0, n), mk((S0, s), (D0, b"\xee" * (n + 32))), lambda ret, m: (ret & M32) == D0 and m.rd(D0, n) == s and m.rd(D0 + n, 4) == b"\xee" * 4
def t_memmove(r):
    n = rn(r, 40, 100); base = bytes(r.randrange(256) for _ in range(256)); d = AL(r) + r.choice([0, 16, 32, 5, 40]); sr = AL(r) + r.choice([0, 16, 32, 7, 40])
    exp = bytearray(base); exp[d:d + n] = base[sr:sr + n]
    return (BUF + d, BUF + sr, n), mk((BUF, base)), lambda ret, m: (ret & M32) == BUF + d and m.rd(BUF, 256) == bytes(exp)
def t_memset(r):
    n = rn(r, 40, 120); c = r.randrange(256); D0 = DST + AL(r)
    return (D0, c, n), mk((D0, b"\xee" * (n + 32))), lambda ret, m: (ret & M32) == D0 and m.rd(D0, n) == bytes([c]) * n and m.rd(D0 + n, 4) == b"\xee" * 4
def t_bzero(r):
    n = rn(r, 40, 120); D0 = DST + AL(r)
    return (D0, n), mk((D0, b"\xee" * (n + 32))), lambda ret, m: m.rd(D0, n) == bytes(n) and m.rd(D0 + n, 4) == b"\xee" * 4
def t_bcopy(r):
    n = rn(r, 40, 100); base = bytes(r.randrange(256) for _ in range(256)); d = AL(r) + r.choice([0, 16, 32, 5, 40]); sr = AL(r) + r.choice([0, 16, 32, 7, 40])
    exp = bytearray(base); exp[d:d + n] = base[sr:sr + n]
    return (BUF + sr, BUF + d, n), mk((BUF, base)), lambda ret, m: m.rd(BUF, 256) == bytes(exp)
def t_memcmp(r):
    S0 = SRC + AL(r); D0 = DST + AL(r); n = rn(r, 12, 90); a = bytes(r.choice(b"\x00\x01\x80") for _ in range(n)); b = bytearray(a)
    if r.random() < .6 and n: b[r.randrange(n)] = r.choice(b"\x00\x01\x80")
    b = bytes(b); exp = (a > b) - (a < b); return (S0, D0, n), mk((S0, a), (D0, b)), lambda ret, m: sgn(ret) == exp
def t_abs(r):
    v = r.choice([0, 1, -1, 5, -5, 2**31 - 1, -(2**31) + 1, r.randint(-1000, 1000)]); return (v,), Mem(), lambda ret, m: (ret & M32) == (abs(v) & M32)
def t_min(r):
    a, b = r.randint(-9, 9), r.randint(-9, 9); return (a, b), Mem(), lambda ret, m: (ret & M32) == (min(a, b) & M32)
def t_max(r):
    a, b = r.randint(-9, 9), r.randint(-9, 9); return (a, b), Mem(), lambda ret, m: (ret & M32) == (max(a, b) & M32)
def t_toupper(r):
    c = r.randrange(256); e = c - 32 if 97 <= c <= 122 else c; return (c,), Mem(), lambda ret, m: (ret & 0xFF) == e and (ret & M32) < 256
def t_tolower(r):
    c = r.randrange(256); e = c + 32 if 65 <= c <= 90 else c; return (c,), Mem(), lambda ret, m: (ret & 0xFF) == e and (ret & M32) < 256
def t_wmemset_u32(r):
    n = r.randint(0, 10); v = r.randrange(2**32)
    return (DST, v, n), mk((DST, b"\xee" * 64)), lambda ret, m: all(m.u(DST + 4 * i, 4) == v for i in range(n)) and m.rd(DST + 4 * n, 4) == b"\xee" * 4

SPECS = {"strlen": t_strlen, "strcpy": t_strcpy, "strcmp": t_strcmp, "strncmp": t_strncmp, "strncpy": t_strncpy, "strcat": t_strcat, "strchr": t_strchr,
         "memmove": t_memmove, "memchr": t_memchr, "strrchr": t_strrchr, "bzero": t_bzero, "bcopy": t_bcopy, "memcpy": t_memcpy, "memset": t_memset, "memcmp": t_memcmp, "abs": t_abs, "min_s32": t_min, "max_s32": t_max,
         "toupper": t_toupper, "tolower": t_tolower, "memset32": t_wmemset_u32}

def matches(elf, addr, spec, trials=60, seed=7, tolerate=False, cov=None):
    """True if every executed trial agrees. tolerate=True skips trials that hit unexecutable ops
    (fast paths) but requires at least half the trials to run."""
    rng = random.Random(seed); fetch = lambda pc: int.from_bytes(elf.read(pc, 4), "little"); ran = 0
    for _ in range(trials):
        args, mem, chk = SPECS[spec](rng)
        cpu = CPU(fetch, mem)
        try: ret = cpu.run(addr, args, limit=4000)
        except (Unsupported, KeyError, RecursionError):
            if tolerate: continue
            return False
        ran += 1
        if cov is not None: cov |= cpu.seen
        if not chk(ret, cpu.mem): return False
    return ran >= trials // 2 if tolerate else True

# Pre-computed supported opcode function sets for fast instruction execution checks.
# Avoids expensive string decoding/formatting in decode() during candidate function scans (~5x speedup).
_SPECIAL_OK = {0, 2, 3, 4, 6, 7, 8, 9, 10, 11, 12, 13, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 27, 32, 33, 34, 35, 36, 37, 38, 39, 42, 43, 44, 45, 46, 47, 56, 58, 59, 60, 62, 63}
_IMM_OK = {8, 9, 10, 11, 12, 13, 14, 15, 24, 25}
_BR_OK = {2, 3, 4, 5, 6, 7, 20, 21, 22, 23}
_MEM_OK = {26, 27, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 52, 55, 63}

_RI_OK = {0, 1, 2, 3, 16, 17}

def supported(w, pc=0):
    """True if the emulator can execute this instruction."""
    from .emu import MMI_OK
    op = w >> 26
    if op == 0:
        return (w & 63) in _SPECIAL_OK
    if op == 1:
        return ((w >> 16) & 31) in _RI_OK
    if op == 0x1C:
        return ((w & 63), (w >> 6) & 31) in MMI_OK
    return op in _IMM_OK or op in _BR_OK or op in _MEM_OK

MIN_COVERAGE = 0.90
def identify(elf, table, max_size=0x600):
    """-> (verified, likely). verified: all instructions executable AND >= 90% of them executed by the tests.
    likely: some code path is not executable or not reached. identify.coverage[addr] holds the fraction."""
    import struct as S
    ver, lik = {}, {}; identify.coverage = {}
    for a, size, _src, sec in table:
        if sec != ".text" or size > max_size or size < 8: continue
        W = S.unpack("<%dI" % (size // 4), elf.read(a, size))
        if any(w >> 26 == 3 for w in W) or any((w & 0xFC00003F) == 0xC for w in W): continue
        part = any(not supported(w, a + 4 * i) for i, w in enumerate(W))
        for name in SPECS:
            if not matches(elf, a, name, 40, tolerate=part): continue
            cov = set()
            if all(matches(elf, a, name, 200, seed=sd, tolerate=part, cov=cov) for sd in (1, 2, 3)):
                # padding nops after the final return do not count
                body = [a + 4 * i for i, w in enumerate(W) if w != 0]; frac = len(cov & set(body)) / max(1, len(body))
                identify.coverage[a] = frac
                if frac < 0.5: break            # test barely touches the function: no evidence
                (lik if part or frac < MIN_COVERAGE else ver).setdefault(name, []).append(a)
            break
    return ver, lik
