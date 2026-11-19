"""Minimal MIPS III/R5900 integer interpreter for differential testing of leaf functions.
Not a full emulator: no COP/MMI/VU, no syscalls, no interrupts. Unknown opcodes raise Unsupported."""
import struct
from fractions import Fraction
from .mips import s16

M32 = 0xFFFFFFFF; M64 = 0xFFFFFFFFFFFFFFFF
# MMI subset that is implemented: (function, sa) pairs of opcode 0x1C
MMI_OK = {(0x08, 0x01), (0x08, 0x09), (0x09, 0x0E), (0x09, 0x12), (0x09, 0x13), (0x29, 0x0E), (0x29, 0x13), (0x29, 0x1B)}
def lanes(v, bits): return [(v >> (i * bits)) & ((1 << bits) - 1) for i in range(128 // bits)]
def join(l, bits): return sum(x << (i * bits) for i, x in enumerate(l))
# ---- R5900 single precision: no NaN/Inf/denormals, results rounded toward zero, overflow clamps
def f2q(b):
    e = (b >> 23) & 255
    if e == 0: return Fraction(0)                                   # denormals read as zero
    m = (b & 0x7FFFFF) | 0x800000; v = Fraction(m) * (Fraction(2) ** (e - 150))
    return -v if b >> 31 else v

def q2f(q):
    if q == 0: return 0
    neg = q < 0; a = -q if neg else q
    e = a.numerator.bit_length() - a.denominator.bit_length()
    if Fraction(2) ** e > a: e -= 1
    elif Fraction(2) ** (e + 1) <= a: e += 1
    if e < -126: return 0                                           # flush to zero
    if e > 127: return (0x80000000 if neg else 0) | 0x7FFFFFFF      # clamp to the largest magnitude
    mant = int(a / (Fraction(2) ** (e - 23)))                      # truncation
    return (0x80000000 if neg else 0) | ((e + 127) << 23) | (mant & 0x7FFFFF)

FPU_OK = {("S", f) for f in (0, 1, 2, 3, 4, 5, 6, 7, 0x16, 0x24, 0x28, 0x29, 0x30, 0x32, 0x34, 0x36)} | {("W", 0x20)}
def fpu_supported(w):
    """True if the emulator implements this COP1/lwc1/swc1 word."""
    op = w >> 26
    if op in (0x31, 0x39): return True
    if op != 0x11: return False
    fmt = (w >> 21) & 31
    if fmt in (0, 2, 4, 6): return True
    if fmt == 8: return ((w >> 16) & 31) in (0, 1, 2, 3)
    if fmt == 16: return ("S", w & 63) in FPU_OK
    if fmt == 20: return ("W", w & 63) in FPU_OK
    return False

class Unsupported(Exception): pass
class Stop(Exception): pass

def s32(x): x &= M32; return x - (1 << 32) if x & 0x80000000 else x
def s64(x): x &= M64; return x - (1 << 64) if x & (1 << 63) else x
def sx(x): return s32(x) & M64                      # 32-bit result sign-extended to 64

class Mem:
    def __init__(self, backing=None): self.b = backing or {}   # sparse bytes
    def rd(self, a, n): return bytes(self.b.get((a + i) & M32, 0) for i in range(n))
    def wr(self, a, data):
        for i, v in enumerate(data): self.b[(a + i) & M32] = v
    def u(self, a, n): return int.from_bytes(self.rd(a, n), "little")
    def put(self, a, n, v): self.wr(a, (v & ((1 << (8 * n)) - 1)).to_bytes(n, "little"))

class CPU:
    def __init__(self, code_reader, mem=None):
        self.r = [0] * 32; self.u = [0] * 32; self.hi = self.lo = 0; self.pc = 0
        self.fetch = code_reader; self.mem = mem or Mem(); self.steps = 0; self.seen = set()
        self.fpr = [0] * 32; self.fcond = False; self.fcr31 = 0
        self.hooks = {}          # guest address -> callable(cpu): replaces the whole function (call + return)
        self.on_break = None     # callable(cpu) invoked by `break`; execution then continues

    def run(self, entry, args=(), ra=0xDEAD0000, sp=0x7F000000, limit=200000, fargs=()):
        self.fpr = [0] * 32; self.fcond = False
        for i, v in enumerate(fargs[:8]): self.fpr[12 + i] = v & M32            # float arguments in $f12..
        self.r = [0] * 32; self.u = [0] * 32; self.pc = entry; self.r[31] = ra; self.r[29] = sp
        for i, v in enumerate(args[:4]): self.r[4 + i] = v & M64 if v >= 0 else (v & M64)
        for i, v in enumerate(args[4:8]): self.r[8 + i] = v & M64            # n32/eabi64 style a4-a7
        self.stop = ra; self.steps = 0
        try:
            while True:
                self.step()
                if self.steps > limit: raise Unsupported("step limit")
        except Stop: pass
        return self.r[2]

    def step(self):
        if self.pc in self.hooks:                          # host-implemented callee: run it, then return to $ra
            h = self.hooks[self.pc]; h(self); self.r[0] = 0; self.pc = self.r[31] & M32; self.steps += 1
            if self.pc == self.stop: raise Stop
            return
        pc = self.pc; w = self.fetch(pc); self.steps += 1; self.seen.add(pc)
        npc = pc + 4; delay = None; self.pc = npc      # default fallthrough
        self.exec(w, pc)
        # branch handling: exec() may set self.br = (target, likely_taken_flag)
        br = getattr(self, "br", None)
        if br is not None:
            self.br = None; tgt, taken, likely = br
            if likely and not taken: self.pc = pc + 8; return
            dw = self.fetch(pc + 4); self.steps += 1; self.seen.add(pc + 4)
            self.pc = pc + 4; self.exec(dw, pc + 4)
            if getattr(self, "br", None) is not None: raise Unsupported("branch in delay slot")
            if taken: self.pc = tgt
            else: self.pc = pc + 8
            if self.pc == self.stop: raise Stop
        self.r[0] = 0

    def exec(self, w, pc):
        r = self.r; m = self.mem
        op = w >> 26; rs = (w >> 21) & 31; rt = (w >> 16) & 31; rd = (w >> 11) & 31; sa = (w >> 6) & 31; imm = w & 0xFFFF; simm = s16(imm)
        A = r[rs]; B = r[rt]
        def W(i, v): 
            if i: r[i] = v & M64
        if w == 0: return
        if op == 0:
            f = w & 63
            if f == 0: W(rd, sx(B << sa))
            elif f == 2: W(rd, sx((B & M32) >> sa))
            elif f == 3: W(rd, sx(s32(B) >> sa))
            elif f == 4: W(rd, sx(B << (A & 31)))
            elif f == 6: W(rd, sx((B & M32) >> (A & 31)))
            elif f == 7: W(rd, sx(s32(B) >> (A & 31)))
            elif f in (8, 9):
                t = A & M32
                if f == 9: W(rd, pc + 8)
                self.br = (t, True, False)
            elif f == 10: 
                if B == 0: W(rd, A)
            elif f == 11:
                if B != 0: W(rd, A)
            elif f == 16: W(rd, self.hi)
            elif f == 18: W(rd, self.lo)
            elif f == 17: self.hi = A
            elif f == 19: self.lo = A
            elif f in (20,): W(rd, B << (A & 63))
            elif f in (22,): W(rd, B >> (A & 63))
            elif f in (23,): W(rd, s64(B) >> (A & 63))
            elif f == 24:
                p = s32(A) * s32(B); self.lo = sx(p); self.hi = sx(p >> 32)
                if rd: W(rd, self.lo)
            elif f == 25:
                p = (A & M32) * (B & M32); self.lo = sx(p); self.hi = sx(p >> 32)
                if rd: W(rd, self.lo)
            elif f == 26:
                if s32(B) == 0: self.lo = self.hi = 0
                else:
                    a, b = s32(A), s32(B); q = abs(a) // abs(b) * (1 if (a < 0) == (b < 0) else -1)
                    self.lo = sx(q); self.hi = sx(a - q * b)
            elif f == 27:
                if (B & M32) == 0: self.lo = self.hi = 0
                else: self.lo = sx((A & M32) // (B & M32)); self.hi = sx((A & M32) % (B & M32))
            elif f in (32, 33): W(rd, sx(A + B))
            elif f in (34, 35): W(rd, sx(A - B))
            elif f == 36: W(rd, A & B)
            elif f == 37: W(rd, A | B)
            elif f == 38: W(rd, A ^ B)
            elif f == 39: W(rd, ~(A | B))
            elif f == 42: W(rd, 1 if s64(A) < s64(B) else 0)
            elif f == 43: W(rd, 1 if A < B else 0)
            elif f in (44, 45): W(rd, A + B)
            elif f in (46, 47): W(rd, A - B)
            elif f == 56: W(rd, B << sa)
            elif f == 58: W(rd, B >> sa)
            elif f == 59: W(rd, s64(B) >> sa)
            elif f == 60: W(rd, B << (sa + 32))
            elif f == 62: W(rd, B >> (sa + 32))
            elif f == 63: W(rd, s64(B) >> (sa + 32))
            elif f == 15: pass
            elif f == 13:
                if self.on_break is None: raise Unsupported("break @%x" % pc)
                self.on_break(self)
            else: raise Unsupported("special %d @%x" % (f, pc))
        elif op == 1:
            a = s64(A); t = pc + 4 + (simm << 2)
            c = {0: a < 0, 1: a >= 0, 2: a < 0, 3: a >= 0}.get(rt)
            if c is None: raise Unsupported("regimm %d" % rt)
            self.br = (t, c, rt in (2, 3))
        elif op == 2: self.br = (((pc + 4) & 0xF0000000) | ((w & 0x3FFFFFF) << 2), True, False)
        elif op == 3:
            W(31, pc + 8); self.br = (((pc + 4) & 0xF0000000) | ((w & 0x3FFFFFF) << 2), True, False)
        elif op in (4, 5, 6, 7, 20, 21, 22, 23):
            t = pc + 4 + (simm << 2); k = op & 7 if op < 20 else op - 16
            c = {4: A == B, 5: A != B, 6: s64(A) <= 0, 7: s64(A) > 0}[k]
            self.br = (t, c, op >= 20)
        elif op in (8, 9): W(rt, sx(A + simm))
        elif op == 10: W(rt, 1 if s64(A) < simm else 0)
        elif op == 11: W(rt, 1 if A < (simm & M64) else 0)
        elif op == 12: W(rt, A & imm)
        elif op == 13: W(rt, A | imm)
        elif op == 14: W(rt, A ^ imm)
        elif op == 15: W(rt, sx(imm << 16))
        elif op in (24, 25): W(rt, A + simm)
        elif op == 32: v = m.u(A + simm & M32, 1); W(rt, v - 256 if v & 128 else v)
        elif op == 33: v = m.u(A + simm & M32, 2); W(rt, v - 65536 if v & 0x8000 else v)
        elif op == 35: W(rt, sx(m.u(A + simm & M32, 4)))
        elif op == 36: W(rt, m.u(A + simm & M32, 1))
        elif op == 37: W(rt, m.u(A + simm & M32, 2))
        elif op == 39: W(rt, m.u(A + simm & M32, 4))
        elif op == 55: W(rt, m.u(A + simm & M32, 8))
        elif op == 40: m.put(A + simm & M32, 1, B)
        elif op == 41: m.put(A + simm & M32, 2, B)
        elif op == 43: m.put(A + simm & M32, 4, B)
        elif op == 63: m.put(A + simm & M32, 8, B)
        elif op in (34, 38, 42, 46):
            a = (A + simm) & M32; al = a & ~3; sh = a & 3; mem = m.u(al, 4); reg = B & M32
            if op == 34:     # lwl (little-endian)
                keep = reg & ((1 << (8 * (3 - sh))) - 1); W(rt, sx(((mem << (8 * (3 - sh))) & M32) | keep))
            elif op == 38:   # lwr
                keep = (reg & ~((1 << (8 * (4 - sh))) - 1) & M32) if sh else 0; W(rt, sx((mem >> (8 * sh)) | keep))
            elif op == 42:   # swl
                m.put(al, sh + 1, reg >> (8 * (3 - sh)))
            else:            # swr
                m.put(a, 4 - sh, reg)
        elif op == 30:   # lq (address low 4 bits ignored)
            a = (A + simm) & M32 & ~15; v = m.u(a, 16)
            if rt: r[rt] = v & M64; self.u[rt] = v >> 64
        elif op == 31:   # sq
            a = (A + simm) & M32 & ~15; m.put(a, 16, B | (self.u[rt] << 64))
        elif op == 0x31: self.fpr[rt] = m.u(A + simm & M32, 4)                                   # lwc1
        elif op == 0x39: m.put(A + simm & M32, 4, self.fpr[rt])                                 # swc1
        elif op == 0x11: self.cop1(w, pc, rs, rt, rd, sa, simm)
        elif op == 0x1C:
            f = w & 63; key = (f, sa)
            if key not in MMI_OK: raise Unsupported("mmi %x/%x @%x" % (f, sa, pc))
            X = r[rs] | (self.u[rs] << 64); Y = r[rt] | (self.u[rt] << 64); M128 = (1 << 128) - 1
            if key == (0x09, 0x12): z = X & Y
            elif key == (0x09, 0x13): z = X ^ Y
            elif key == (0x29, 0x13): z = ~(X | Y) & M128
            elif key == (0x09, 0x0E): z = (Y & M64) | ((X & M64) << 64)                 # pcpyld
            elif key == (0x29, 0x0E): z = (X >> 64) | (Y & (M64 << 64))                 # pcpyud
            elif key == (0x29, 0x1B): z = (Y & 0xFFFF) * 0x0001000100010001 | (((Y >> 64) & 0xFFFF) * 0x0001000100010001) << 64   # pcpyh
            elif key == (0x08, 0x09): z = join([(a_ - b_) & 0xFF for a_, b_ in zip(lanes(X, 8), lanes(Y, 8))], 8)   # psubb
            else: z = join([(a_ - b_) & M32 for a_, b_ in zip(lanes(X, 32), lanes(Y, 32))], 32)                       # psubw
            if rd: r[rd] = z & M64; self.u[rd] = z >> 64
        else: raise Unsupported("op %d @%x" % (op, pc))

    def cop1(self, w, pc, fmt, rt, fs, fd, simm):
        r = self.r; F = self.fpr; ft = rt
        if fmt == 0:                                                                               # mfc1
            if rt: r[rt] = sx(F[fs])
            return
        if fmt == 4: F[fs] = r[rt] & M32; return                                                   # mtc1
        if fmt == 2:                                                                               # cfc1
            if rt: r[rt] = (self.fcr31 | ((1 << 23) if self.fcond else 0)) & M32
            return
        if fmt == 6: self.fcr31 = r[rt] & M32; self.fcond = bool(self.fcr31 & (1 << 23)); return    # ctc1
        if fmt == 8:                                                                               # bc1f / bc1t / bc1fl / bc1tl
            t = pc + 4 + (simm << 2); c = self.fcond if (rt & 1) else not self.fcond
            self.br = (t, c, bool(rt & 2)); return
        f = w & 63
        if fmt == 20 and f == 32: F[fd] = q2f(Fraction(s32(F[fs]))); return                       # cvt.s.w
        if fmt != 16: raise Unsupported("cop1 fmt %d @%x" % (fmt, pc))
        a = f2q(F[fs]); b = f2q(F[ft])
        if f == 0: F[fd] = q2f(a + b)
        elif f == 1: F[fd] = q2f(a - b)
        elif f == 2: F[fd] = q2f(a * b)
        elif f == 3: F[fd] = q2f(a / b) if b != 0 else (0x7FFFFFFF if (F[fs] ^ F[ft]) >> 31 == 0 else 0xFFFFFFFF)
        elif f == 4:                                                                               # sqrt.s fd, ft
            import math
            if b <= 0: F[fd] = 0
            else:
                sh = 200; F[fd] = q2f(Fraction(math.isqrt(b.numerator * b.denominator * (1 << (2 * sh))), b.denominator * (1 << sh)))
        elif f == 5: F[fd] = F[fs] & 0x7FFFFFFF
        elif f == 6: F[fd] = F[fs]
        elif f == 7: F[fd] = F[fs] ^ 0x80000000
        elif f == 0x16:                                                                            # rsqrt.s fd, fs, ft
            import math
            if b <= 0 or a < 0: F[fd] = 0x7FFFFFFF
            else: F[fd] = q2f(a / Fraction(math.isqrt(int(b * (1 << 400))), 1 << 200))
        elif f == 0x24:                                                                            # cvt.w.s
            v = int(a); F[fd] = (0x7FFFFFFF if v > 0x7FFFFFFF else 0x80000000 if v < -0x80000000 else v) & M32
        elif f == 0x28: F[fd] = F[fs] if a >= b else F[ft]
        elif f == 0x29: F[fd] = F[fs] if a <= b else F[ft]
        elif f == 0x30: self.fcond = False
        elif f == 0x32: self.fcond = a == b
        elif f == 0x34: self.fcond = a < b
        elif f == 0x36: self.fcond = a <= b
        else: raise Unsupported("cop1 funct %x @%x" % (f, pc))
