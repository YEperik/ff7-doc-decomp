"""Assembler for the instruction subset ps2an can disassemble (inverse of mips.decode)."""
import re
from . import mips
from .mips import R, _SPECIAL, _IMM, _MEM, _BR, _RI, _MMI

REG = {n: i for i, n in enumerate(R)}
_SP = {v: k for k, v in _SPECIAL.items()}; _IM = {v: k for k, v in _IMM.items()}; _ME = {v: k for k, v in _MEM.items()}
_BRN = {v: k for k, v in _BR.items()}; _RIN = {v: k for k, v in _RI.items()}; _MM = {v: k for k, v in _MMI.items()}
_MM["pcpyh"] = (0x29, 0x1B)

def _r(t): return REG[t.strip().lstrip("$")]
def _n(t): return int(t.strip(), 0)
def _imm16(v): return v & 0xFFFF

def assemble(text, pc=0):
    """One instruction -> 32-bit word. Branch/jump operands are absolute addresses."""
    t = text.strip(); 
    if t == "nop": return 0
    m, _, rest = t.partition(" "); a = [x.strip() for x in rest.split(",")] if rest else []
    if m == ".word": return int(a[0], 0)
    if m in _SP:
        f = _SP[m]
        if m in ("sll", "srl", "sra", "dsll", "dsrl", "dsra", "dsll32", "dsrl32", "dsra32"): return (_r(a[1]) << 16) | (_r(a[0]) << 11) | (_n(a[2]) << 6) | f
        if m in ("sllv", "srlv", "srav", "dsllv", "dsrlv", "dsrav"): return (_r(a[2]) << 21) | (_r(a[1]) << 16) | (_r(a[0]) << 11) | f
        if m == "jr": return (_r(a[0]) << 21) | f
        if m == "jalr": return (_r(a[1]) << 21) | (_r(a[0]) << 11) | f
        if m in ("mfhi", "mflo"): return (_r(a[0]) << 11) | f
        if m in ("mthi", "mtlo", "mtsa"): return (_r(a[0]) << 21) | f
        if m == "mfsa": return (_r(a[0]) << 11) | f
        if m in ("mult", "multu", "div", "divu"): return (_r(a[0]) << 21) | (_r(a[1]) << 16) | f
        if m in ("syscall", "break"): return (_n(a[0]) << 6 | f) if a else f
        if m == "sync": return f
        return (_r(a[1]) << 21) | (_r(a[2]) << 16) | (_r(a[0]) << 11) | f            # 3-register ALU
    if m in _IM: return (_IM[m] << 26) | (_r(a[1]) << 21) | (_r(a[0]) << 16) | _imm16(_n(a[2]))
    if m == "lui": return (15 << 26) | (_r(a[0]) << 16) | _imm16(_n(a[1]))
    if m in _ME:
        mo = re.match(r"(-?\w+)\((\$\w+)\)", a[1]); off, base = _n(mo.group(1)), _r(mo.group(2))
        rt = int(a[0][2:]) if a[0].startswith("$f") or a[0].startswith("$vf") and False else (int(a[0].replace("$vf", "").replace("$f", "")) if a[0].startswith(("$f", "$vf")) else _r(a[0]))
        return (_ME[m] << 26) | (base << 21) | (rt << 16) | _imm16(off)
    if m in _BRN:
        tgt = _n(a[-1]); off = (tgt - (pc + 4)) >> 2
        rs = _r(a[0]); rt = _r(a[1]) if m in ("beq", "bne", "beql", "bnel") else 0
        return (_BRN[m] << 26) | (rs << 21) | (rt << 16) | _imm16(off)
    if m in _RIN: return (1 << 26) | (_r(a[0]) << 21) | (_RIN[m] << 16) | _imm16((_n(a[1]) - (pc + 4)) >> 2)
    if m in ("j", "jal"): return ((2 if m == "j" else 3) << 26) | ((_n(a[0]) >> 2) & 0x3FFFFFF)
    if m in _MM:
        f, sa = _MM[m]
        if m == "pcpyh": return (0x1C << 26) | (_r(a[1]) << 16) | (_r(a[0]) << 11) | (sa << 6) | f
        return (0x1C << 26) | (_r(a[1]) << 21) | (_r(a[2]) << 16) | (_r(a[0]) << 11) | (sa << 6) | f
    raise ValueError("cannot assemble: " + text)

_SKIP = ("mfc0", "mtc0", "mfc1", "mtc1", "lwc1", "swc1", "lqc2", "sqc2")

def roundtrip(elf, table, span=24):
    """Disassemble then assemble the first `span` words of every function that is certainly code
    (reached by jal, or with a stack-frame prologue). Returns (total, ok, examples of failures)."""
    from . import analyze as A
    tot = ok = 0; bad = []
    for a, size, src, _sec in table:
        if src not in ("jal", "prologue", "syscall"): continue
        for i in range(min(span, size // 4)):
            pc = a + 4 * i; w = int.from_bytes(elf.read(pc, 4), "little"); t = mips.decode(w, pc)
            if t.startswith(".word") or t.split()[0] in _SKIP: continue
            tot += 1
            try: good = assemble(t, pc) == w
            except Exception: good = False
            ok += good
            if not good and len(bad) < 8: bad.append((hex(pc), hex(w), t))
    return tot, ok, bad
