"""Function discovery, string scan, xrefs and SDK naming."""
import re, struct, bisect
from . import mips

def find_functions(elf):
    """Return {addr: source} using jal targets + prologue-after-return heuristic."""
    ranges = [(s.addr, s.addr + s.size) for s in elf.code_sections()]
    inr = lambda a: a % 4 == 0 and any(lo <= a < hi for lo, hi in ranges)
    funcs = {}
    for s in elf.code_sections():
        W = elf.words(s); base = s.addr
        for i, w in enumerate(W):
            pc = base + i * 4
            if mips.is_jal(w):
                t = mips.jal_target(w, pc)
                if inr(t): funcs.setdefault(t, "jal")
            elif mips.is_sp_alloc(w):
                j = i - 1
                while j >= 0 and W[j] == 0: j -= 1
                if j >= 1 and W[j - 1] == 0x03E00008 and j < i:   # jr ra ; <delay slot> ; nops ; prologue
                    funcs.setdefault(pc, "prologue")
                elif i >= 2 and W[i - 2] == 0x03E00008:
                    funcs.setdefault(pc, "prologue")
        funcs.setdefault(base, "section")
    return dict(sorted(funcs.items()))

def func_table(elf, funcs):
    """[(addr, size, source, section)] with size = distance to next function start."""
    starts = sorted(funcs); out = []
    for k, a in enumerate(starts):
        sec = elf.section_at(a); end = sec.addr + sec.size
        nxt = starts[k + 1] if k + 1 < len(starts) else end
        out.append((a, min(nxt, end) - a, funcs[a], sec.name))
    return out

_STR = re.compile(rb"[\x20-\x7e\t\r\n]{4,}")
def find_strings(elf, min_len=4):
    out = []
    for s in elf.data_sections():
        blob = elf.data[s.off:s.off + s.size]
        for m in _STR.finditer(blob):
            e = m.end()
            if e < len(blob) and blob[e] != 0: continue          # must be NUL-terminated
            if m.start() and blob[m.start() - 1] != 0: continue  # and start at a boundary
            if m.end() - m.start() >= min_len:
                out.append((s.addr + m.start(), m.group().decode("ascii")))
    return out

def find_xrefs(elf, targets, window=10):
    """lui/addiu|ori|lw|sw pairs resolving into `targets` (a set of addresses). Returns {target: [pc,...]}."""
    refs = {}
    for s in elf.code_sections():
        W = elf.words(s); base = s.addr; n = len(W)
        for i, w in enumerate(W):
            if w >> 26 != 15: continue
            rt = (w >> 16) & 31; hi = (w & 0xFFFF) << 16
            for j in range(i + 1, min(i + window, n)):
                v = W[j]; op = v >> 26; vrs = (v >> 21) & 31; vrt = (v >> 16) & 31
                if vrs == rt and op in (9, 13, 35, 43, 32, 36, 33, 37, 40, 41, 55, 63, 30, 31, 49, 57):
                    lo = v & 0xFFFF
                    a = (hi + (mips.s16(lo) if op != 13 else lo)) & 0xFFFFFFFF
                    if a in targets: refs.setdefault(a, []).append(base + j * 4)
                if vrt == rt and op in (9, 13, 15, 35, 36, 33, 37, 32) : break   # register overwritten
    return refs

def owner(starts, pc):
    k = bisect.bisect_right(starts, pc) - 1
    return starts[k] if k >= 0 else None

_SDKPFX = re.compile(r"^((?:sce|sq|Sce|Sq)[A-Za-z0-9_]{3,}):")
def name_sdk(elf, table):
    """Name functions from '<name>: message' error strings they reference. -> {addr: name}"""
    strs = {a: t for a, t in find_strings(elf)}
    cand = {a: _SDKPFX.match(t).group(1) for a, t in strs.items() if _SDKPFX.match(t)}
    refs = find_xrefs(elf, set(cand))
    starts = [t[0] for t in table]; named = {}
    for a, pcs in refs.items():
        for pc in pcs:
            f = owner(starts, pc)
            if f is not None: named.setdefault(f, cand[a])
    return named

def find_embedded_elf(elf):
    """Embedded ELF images (IOP IRX/ERX modules)."""
    d = elf.data; out = []; i = 4
    while True:
        i = d.find(b"\x7fELF", i)
        if i < 0: break
        try:
            shoff, = struct.unpack_from("<I", d, i + 32); shent, shnum = struct.unpack_from("<HH", d, i + 46)
            size = shoff + shent * shnum; typ, mach = struct.unpack_from("<HH", d, i + 16)
            if 0 < size < len(d) - i and shnum < 64: out.append((i, size, typ, mach))
        except struct.error: pass
        i += 4
    return out

def gzf_functions(path):
    """Function addresses stored in a Ghidra .gzf (default FUN_xxxxxxxx names)."""
    import zlib
    d = open(path, "rb").read(); i = d.find(b"PK\x03\x04")
    nlen, elen = struct.unpack_from("<HH", d, i + 26)
    raw = zlib.decompressobj(-15).decompress(d[i + 30 + nlen + elen:])
    return sorted({int(m, 16) for m in re.findall(rb"FUN_([0-9a-f]{8})", raw)})

# EE kernel syscall numbers (public, ps2sdk-documented). Only entries that are well established.
SYSCALLS = {0x02:"SetGsCrt",0x04:"Exit",0x06:"LoadExecPS2",0x07:"ExecPS2",0x10:"AddIntcHandler",0x11:"RemoveIntcHandler",
 0x12:"AddDmacHandler",0x13:"RemoveDmacHandler",0x14:"_EnableIntc",0x15:"_DisableIntc",0x16:"_EnableDmac",0x17:"_DisableDmac",
 0x20:"CreateThread",0x21:"DeleteThread",0x22:"StartThread",0x23:"ExitThread",0x24:"ExitDeleteThread",0x25:"TerminateThread",
 0x29:"ChangeThreadPriority",0x2B:"RotateThreadReadyQueue",0x2D:"ReleaseWaitThread",0x2F:"GetThreadId",0x30:"ReferThreadStatus",
 0x32:"SleepThread",0x33:"WakeupThread",0x34:"iWakeupThread",0x35:"CancelWakeupThread",0x37:"SuspendThread",0x39:"ResumeThread",
 0x3C:"SetupThread",0x3D:"SetupHeap",0x3E:"EndOfHeap",0x40:"CreateSema",0x41:"DeleteSema",0x42:"SignalSema",0x43:"iSignalSema",
 0x44:"WaitSema",0x45:"PollSema",0x46:"iPollSema",0x47:"ReferSemaStatus",0x64:"FlushCache",0x70:"GsGetIMR",0x71:"GsPutIMR",
 0x73:"SetVSyncFlag",0x74:"SetSyscall",0x76:"sceSifDmaStat",0x77:"sceSifSetDma",0x78:"sceSifSetDChain",0x79:"sceSifSetReg",
 0x7A:"sceSifGetReg",0x7C:"Deci2Call",0x7E:"MachineType",0x7F:"GetMemorySize"}

def name_syscalls(elf, table):
    """Tiny leaf wrappers `li v1,N ; syscall ; jr ra` -> kernel syscall names. -> {addr: name}"""
    out = {}
    for a, size, _src, _sec in table:
        if size > 32: continue
        W = struct.unpack("<%dI" % (size // 4), elf.read(a, size))
        for w in W:
            if (w >> 26) == 9 and (w >> 21) & 31 == 0 and (w >> 16) & 31 == 3:   # addiu v1,zero,N
                n = abs(mips.s16(w & 0xFFFF))
                if 0x0000000C in [x & 0xFC00003F for x in W] and n in SYSCALLS:
                    out[a] = SYSCALLS[n] + ("_neg" if mips.s16(w & 0xFFFF) < 0 else "")
    return out
