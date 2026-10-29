"""Minimal ELF32-LE reader (sections, segments, memory image)."""
import struct, hashlib
from dataclasses import dataclass

@dataclass
class Section:
    name: str; type: int; flags: int; addr: int; off: int; size: int
    @property
    def alloc(self): return bool(self.flags & 2)
    @property
    def exec(self): return bool(self.flags & 4)
    @property
    def nobits(self): return self.type == 8

@dataclass
class Segment:
    type: int; off: int; vaddr: int; filesz: int; memsz: int; flags: int

class Elf:
    def __init__(self, path):
        self.path = path
        self.data = d = open(path, "rb").read()
        if d[:4] != b"\x7fELF" or d[4] != 1 or d[5] != 1:
            raise ValueError("not an ELF32 little-endian file")
        (self.type, self.machine, _, self.entry, self.phoff, self.shoff, self.flags,
         _, self.phentsize, self.phnum, self.shentsize, self.shnum, self.shstrndx) = \
            struct.unpack_from("<HHIIIIIHHHHHH", d, 16)
        self.segments = []
        for i in range(self.phnum):
            t, off, va, _pa, fsz, msz, fl, _al = struct.unpack_from("<8I", d, self.phoff + i * self.phentsize)
            self.segments.append(Segment(t, off, va, fsz, msz, fl))
        raw = [struct.unpack_from("<10I", d, self.shoff + i * self.shentsize) for i in range(self.shnum)]
        stro = raw[self.shstrndx][4] if raw else 0
        self.sections = []
        for nm, ty, fl, ad, off, sz, *_ in raw:
            e = d.index(b"\0", stro + nm)
            self.sections.append(Section(d[stro + nm:e].decode("latin1"), ty, fl, ad, off, sz))

    @property
    def sha256(self): return hashlib.sha256(self.data).hexdigest()

    def code_sections(self):
        """Executable MIPS sections (VU microcode excluded)."""
        return [s for s in self.sections if s.exec and not s.nobits and s.size and s.addr
                and "vu" not in s.name.lower() and not s.name.startswith(".DVP")]

    def data_sections(self):
        return [s for s in self.sections if s.alloc and not s.exec and not s.nobits and s.size and s.addr]

    def section_at(self, addr):
        for s in self.sections:
            if s.alloc and s.addr and s.addr <= addr < s.addr + s.size:
                return s

    def read(self, addr, n):
        """Bytes at a virtual address (section-based; overlay sections may overlap segments)."""
        for s in self.sections:
            if s.alloc and s.addr and not s.nobits and s.addr <= addr and addr + n <= s.addr + s.size:
                o = s.off + addr - s.addr
                return self.data[o:o + n]
        raise KeyError(hex(addr))

    def words(self, sec):
        return struct.unpack_from("<%dI" % (sec.size // 4), self.data, sec.off)
