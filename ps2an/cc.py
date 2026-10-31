"""ps2an cc - a small C-subset compiler for the R5900 (leaf functions), built on pycparser.

It models how the original compiler lays out small functions:
  * absolute addresses  -> lui + 16-bit offset
  * list scheduling with critical-path priority (all latencies 1), ties in source order
  * the last scheduled instruction fills the delay slot of `jr ra`
  * result chain in $v0, address temporaries in $v1 (value-returning) or $v0, other temporaries in spare argument registers
Unsupported constructs raise Unsupported, so `ps2an match` can report what is missing."""
import os, re, subprocess, sys, tempfile
from dataclasses import dataclass, field
from pycparser import CParser, c_ast
from . import asm

class Unsupported(Exception): pass

# ---------------------------------------------------------------- types
@dataclass
class CT:
    kind: str; size: int = 4; signed: bool = True; target: "CT" = None; fields: list = field(default_factory=list); align: int = 4; count: int = 0
INT = CT("int", 4, True); UINT = CT("int", 4, False)

def layout(fields):
    off = 0; al = 1; out = []
    for name, t in fields:
        a = max(1, min(t.align, 8)); off = (off + a - 1) // a * a; out.append((name, off, t)); off += t.size; al = max(al, a)
    return out, (off + al - 1) // al * al, al

class Types:
    def __init__(self): self.typedefs = {}; self.structs = {}
    def resolve(self, n):
        if isinstance(n, c_ast.TypeDecl): return self.resolve(n.type)
        if isinstance(n, c_ast.Typename): return self.resolve(n.type)
        if isinstance(n, c_ast.PtrDecl): return CT("ptr", 4, False, self.resolve(n.type), align=4)
        if isinstance(n, c_ast.ArrayDecl):
            e = self.resolve(n.type); cnt = int(n.dim.value, 0) if n.dim is not None else 0; return CT("array", e.size * cnt, False, e, align=e.align, count=cnt)
        if isinstance(n, c_ast.IdentifierType):
            names = n.names
            if len(names) == 1 and names[0] in self.typedefs: return self.typedefs[names[0]]
            if names == ["void"]: return CT("void", 0)
            uns = "unsigned" in names; b = [x for x in names if x not in ("unsigned", "signed")]
            sz = 1 if "char" in b else 2 if "short" in b else 8 if b.count("long") == 2 else 4
            return CT("int", sz, not uns, align=sz)
        if isinstance(n, c_ast.Struct):
            key = n.name or id(n)
            if n.decls is None: return self.structs[key]
            fs = [(d.name, self.resolve(d.type)) for d in n.decls]; lo, size, al = layout(fs)
            t = CT("struct", size, False, fields=lo, align=al); self.structs[key] = t; return t
        raise Unsupported("type %s" % type(n).__name__)

# ---------------------------------------------------------------- IR
@dataclass
class V:            # value: immediate or virtual register
    imm: int = None; reg: str = None; t: CT = field(default_factory=lambda: INT); addr: bool = False
@dataclass
class I:            # instruction
    op: str; d: str = None; a: str = None; b: str = None; imm: int = None; mem: bool = False; store: bool = False; cls: str = "alu"; fixed: str = None; boost: bool = False

LOAD = {(1, True): "lb", (1, False): "lbu", (2, True): "lh", (2, False): "lhu", (4, True): "lw", (4, False): "lw", (8, True): "ld", (8, False): "ld", (16, True): "lq", (16, False): "lq"}
STORE = {1: "sb", 2: "sh", 4: "sw", 8: "sd", 16: "sq"}

class Compiler:
    def __init__(self, cfile, include_dirs, symbols=None):
        self.symbols = symbols or {}
        here = os.path.dirname(os.path.abspath(__file__))
        cmd = ["gcc", "-E", "-P", "-nostdinc", "-DCC_PARSE", "-D__attribute__(x)=", "-I", os.path.join(here, "cc_fake")] + sum([["-I", d] for d in include_dirs], []) + [cfile]
        text = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
        self.ast = CParser().parse(text); self.types = Types(); self.funcs = {}
        for ext in self.ast.ext:
            if isinstance(ext, c_ast.Typedef): self.types.typedefs[ext.name] = self.types.resolve(ext.type)
            elif isinstance(ext, c_ast.FuncDef): self.funcs[ext.decl.name] = ext

    # ---------- function entry
    def compile(self, name):
        fd = self.funcs.get(name)
        if fd is None: raise Unsupported("function not found")
        self.ir = []; self.n = 0; self.params = {}; self.ft = fd.decl.type; self.fixed = {}; self.has_call = False; self.callres = None
        for i, p in enumerate(self.ft.args.params if self.ft.args else []):
            if p.name is None: continue
            if i > 3: raise Unsupported("more than 4 parameters")
            self.params[p.name] = V(reg="a%d" % i, t=self.types.resolve(p.type))
        self.rett = self.types.resolve(self.ft.type); self.ret_value = None; self.used_params = set(); self.locals = {}; self.base2 = {}; self.fixed_lui = set()
        body = fd.body.block_items or []
        for st in body: self.stmt(st)
        return self.finish()

    def tmp(self): self.n += 1; return "t%d" % self.n

    # ---------- statements
    def stmt(self, st):
        if isinstance(st, c_ast.Return):
            if st.expr is None: return
            v = self.expr(st.expr)
            self.ret_value = self.reg(v); return
        if isinstance(st, c_ast.Assignment) and st.op == "=":
            self.assign(st); return
        if isinstance(st, c_ast.FuncCall):
            self.call(st); return
        if isinstance(st, c_ast.Decl):
            t = self.types.resolve(st.type)
            if st.init is None: raise Unsupported("uninitialised local")
            v = self.expr(st.init); self.locals[st.name] = V(imm=v.imm, reg=v.reg, t=t); return
        raise Unsupported("statement %s" % type(st).__name__)

    def reg(self, v):
        if v.reg is not None:
            if v.reg.startswith("a"): self.used_params.add(v.reg)
            return v.reg
        d = self.tmp(); self.emit(I("li", d, imm=v.imm)); return d

    def emit(self, i): self.ir.append(i); return i

    # ---------- constants / addresses
    def const(self, n):
        if isinstance(n, c_ast.Constant):
            s = n.value.rstrip("uUlL"); return int(s, 0)
        if isinstance(n, c_ast.Cast): return self.const(n.expr)
        if isinstance(n, c_ast.BinaryOp) and n.op in ("+", "-", "|", "<<", "&"):
            a, b = self.const(n.left), self.const(n.right)
            if a is None or b is None: return None
            return {"+": a + b, "-": a - b, "|": a | b, "<<": a << b, "&": a & b}[n.op] & 0xFFFFFFFF
        if isinstance(n, c_ast.UnaryOp) and n.op == "-":
            a = self.const(n.expr); return None if a is None else (-a) & 0xFFFFFFFF
        return None

    def mem_of(self, n):
        """lvalue node -> (base reg or None, offset, ctype)."""
        if isinstance(n, c_ast.UnaryOp) and n.op == "*":
            ty = self.type_of_deref(n.expr); c = self.const(n.expr)
            if c is not None: return (None, c, ty)
            v = self.expr(n.expr); return (self.reg(v), 0, ty)
        if isinstance(n, c_ast.StructRef):
            if n.type != "->": raise Unsupported("struct value member")
            v = self.expr(n.name); st = v.t.target
            if st is None or st.kind != "struct": raise Unsupported("member of non-struct")
            for fname, off, ft in st.fields:
                if fname == n.field.name: return (self.reg(v), off, ft)
            raise Unsupported("no such field")
        raise Unsupported("lvalue %s" % type(n).__name__)

    def type_of_deref(self, e):
        if isinstance(e, c_ast.Cast): 
            t = self.types.resolve(e.to_type)
            if t.kind == "ptr": return t.target
        v = self.expr(e) if not isinstance(e, c_ast.Cast) else None
        if v is not None and v.t.kind == "ptr": return v.t.target
        raise Unsupported("deref type")

    def addr_parts(self, base, off):
        """-> (base register, 16-bit offset), emitting lui for absolute addresses."""
        if base is None:
            hi = ((off + 0x8000) >> 16) & 0xFFFF; lo = off - (hi << 16)
            r = self.tmp(); self.emit(I("lui", r, imm=hi, cls="addr")); return r, lo
        if not -0x8000 <= off < 0x8000:
            if not 0x8000 <= off < 0x10000 - 0: raise Unsupported("large field offset")
            key = (base, 0x8000)
            if key not in self.base2:                       # base + 0x8000 is computed once and shared
                t1 = self.tmp(); self.emit(I("li", t1, imm=0x8000)); b2 = self.tmp(); self.emit(I("addu", b2, a=base, b=t1)); self.base2[key] = b2
            return self.base2[key], off - 0x8000
        return base, off

    def load(self, base, off, t):
        sz = t.size
        if sz not in (1, 2, 4, 8, 16): raise Unsupported("load size %d" % sz)
        b, o = self.addr_parts(base, off); d = self.tmp()
        self.emit(I(LOAD[(sz, t.signed)], d, a=b, imm=o, mem=True)); return V(reg=d, t=t)

    # ---------- expressions
    def expr(self, n):
        c = self.const(n) if isinstance(n, (c_ast.Constant,)) else None
        if c is not None: return V(imm=c)
        if isinstance(n, c_ast.ID):
            if n.name in self.locals: return self.locals[n.name]
            if n.name in self.params: return self.params[n.name]
            raise Unsupported("identifier %s" % n.name)
        if isinstance(n, c_ast.Cast):
            c = self.const(n)
            if c is not None: return V(imm=c, t=self.types.resolve(n.to_type))
            v = self.expr(n.expr); t = self.types.resolve(n.to_type)
            if t.kind in ("ptr",) or (t.kind == "int" and t.size == 4): return V(imm=v.imm, reg=v.reg, t=t)
            raise Unsupported("narrowing cast")
        if isinstance(n, c_ast.UnaryOp) and n.op == "*":
            base, off, t = self.mem_of(n); return self.load(base, off, t)
        if isinstance(n, c_ast.StructRef):
            base, off, t = self.mem_of(n); return self.load(base, off, t)
        if isinstance(n, c_ast.UnaryOp) and n.op == "!":
            v = self.expr(n.expr); d = self.tmp(); self.emit(I("sltiu", d, a=self.reg(v), imm=1)); return V(reg=d)
        if isinstance(n, c_ast.BinaryOp): return self.binop(n)
        if isinstance(n, c_ast.FuncCall): return self.call(n)
        raise Unsupported("expression %s" % type(n).__name__)

    def binop(self, n):
        op = n.op
        if op in ("==", "!=") and self.const(n.right) == 0:
            v = self.expr(n.left); d = self.tmp()
            if op == "==": self.emit(I("sltiu", d, a=self.reg(v), imm=1))
            else: self.emit(I("sltu", d, a="zero", b=self.reg(v)))
            return V(reg=d)
        if op in (">>", "<<"):
            l = self.expr(n.left); amt = n.right
            if isinstance(amt, c_ast.BinaryOp) and amt.op == "&" and self.const(amt.right) == 31: amt = amt.left   # hardware masks shift counts
            k = self.const(amt); d = self.tmp()
            la = self.reg(l)
            if k is not None: self.emit(I({">>": "sra" if l.t.signed else "srl", "<<": "sll"}[op] if True else "", d, a=la, imm=k & 31)); return V(reg=d, t=l.t)
            r = self.reg(self.expr(amt)); nm = {">>": "srav" if l.t.signed else "srlv", "<<": "sllv"}[op]
            self.emit(I(nm, d, a=la, b=r)); return V(reg=d, t=l.t)
        if op in ("+", "-"):                                   # pointer arithmetic is scaled by the element size
            l0 = self.expr(n.left)
            if l0.t.kind == "ptr" and l0.t.target is not None and self.const(n.right) is not None:
                k = self.const(n.right) * l0.t.target.size * (1 if op == "+" else -1); d = self.tmp()
                if not -0x8000 <= k < 0x8000: raise Unsupported("pointer offset")
                self.emit(I("addiu", d, a=self.reg(l0), imm=k)); return V(reg=d, t=l0.t)
        if op in ("&", "|", "^", "+", "-"):
            if op != "-" and self.is_mem(n.left) and isinstance(n.right, c_ast.BinaryOp):
                r = self.expr(n.right); l = self.expr(n.left)         # canonical order: the computed operand goes first
            else:
                l = self.expr(n.left); r = self.expr(n.right)
            if l.imm is not None and r.imm is None and op in ("&", "|", "^", "+"): l, r = r, l
            ra = self.reg(l); d = self.tmp()
            if r.imm is not None:
                if op == "+" and -0x8000 <= r.imm < 0x8000: self.emit(I("addiu", d, a=ra, imm=r.imm)); return V(reg=d, t=l.t)
                if op == "-" and -0x7FFF <= r.imm <= 0x8000: self.emit(I("addiu", d, a=ra, imm=-r.imm)); return V(reg=d, t=l.t)
                if op in ("&", "|", "^") and 0 <= r.imm <= 0xFFFF: self.emit(I({"&": "andi", "|": "ori", "^": "xori"}[op], d, a=ra, imm=r.imm)); return V(reg=d, t=l.t)
            rb = self.reg(r); self.emit(I({"&": "and", "|": "or", "^": "xor", "+": "addu", "-": "subu"}[op], d, a=ra, b=rb)); return V(reg=d, t=l.t)
        if op in ("!=", "=="): 
            l = self.reg(self.expr(n.left)); r = self.reg(self.expr(n.right))
            if l == self.callres: l, r = r, l                      # canonical order: a call result is the second operand
            x = self.tmp(); self.emit(I("xor", x, a=l, b=r)); d = self.tmp()
            self.emit(I("sltiu", d, a=x, imm=1) if op == "==" else I("sltu", d, a="zero", b=x)); return V(reg=d)
        raise Unsupported("operator " + op)

    def is_mem(self, n):
        return isinstance(n, c_ast.StructRef) or (isinstance(n, c_ast.UnaryOp) and n.op == "*") or (isinstance(n, c_ast.Cast) and self.is_mem(n.expr))

    def assign(self, st):
        base, off, t = self.mem_of(st.lvalue); rv = self.rvalue_for_store(st.rvalue, t)
        if t.size not in STORE: raise Unsupported("store size")
        b, o = self.addr_parts(base, off)
        self.emit(I(STORE[t.size], a=b, b=rv, imm=o, mem=True, store=True))

    def rvalue_for_store(self, n, t):
        if t.kind == "struct":                                   # whole-object copy
            if isinstance(n, c_ast.UnaryOp) and n.op == "*":
                base, off, st = self.mem_of(n); 
                if st.size != t.size: raise Unsupported("struct copy size")
                return self.load(base, off, CT("int", t.size, False)).reg
            raise Unsupported("struct rvalue")
        return self.reg(self.expr(n))

    # ---------- calls
    def sym(self, name):
        if name in self.symbols: return self.symbols[name]
        m = re.fullmatch(r"FUN_([0-9a-fA-F]{8})", name)
        if m: return int(m.group(1), 16)
        raise Unsupported("unknown callee %s" % name)

    def set_fixed(self, v, reg):
        self.fixed[v] = reg
        for ins in self.ir:                                       # `lui t1 ; addiu t2,t1,lo` share one register
            if ins.d == v and ins.op == "addiu" and ins.a in self.fixed_lui: self.fixed[ins.a] = reg

    def li32(self, imm):
        v = imm & 0xFFFFFFFF; s32 = v - (1 << 32) if v & 0x80000000 else v
        if -0x8000 <= s32 <= 0x7FFF or 0 <= v <= 0xFFFF: d = self.tmp(); self.emit(I("li", d, imm=v)); return d
        hi = ((v + 0x8000) >> 16) & 0xFFFF; lo = v - (hi << 16)
        t1 = self.tmp(); self.emit(I("lui", t1, imm=hi, cls="addr")); self.fixed_lui.add(t1)
        if lo == 0: return t1
        t2 = self.tmp(); self.emit(I("addiu", t2, a=t1, imm=lo)); return t2

    def call(self, n):
        if self.has_call: raise Unsupported("more than one call")
        if not isinstance(n.name, c_ast.ID): raise Unsupported("indirect call")
        tgt = self.sym(n.name.name)
        args = n.args.exprs if n.args else []
        if len(args) > 4: raise Unsupported("more than 4 arguments")
        self.has_call = True; moved = set()
        for i, a in enumerate(args):                               # parameters that would be clobbered are copied first
            if isinstance(a, c_ast.ID) and a.name in self.params and a.name not in self.locals:
                k = int(self.params[a.name].reg[1:])
                if k != i:
                    d = self.tmp(); self.used_params.add("a%d" % k); self.emit(I("daddu", d, a="a%d" % k, b="zero")); self.fixed[d] = "a%d" % i; moved.add(i)
        for i, a in enumerate(args):
            if i in moved: continue
            v = self.expr(a)
            if v.imm is not None:
                if v.imm == 0: d = self.tmp(); self.emit(I("daddu", d, a="zero", b="zero")); self.set_fixed(d, "a%d" % i)
                else: self.set_fixed(self.li32(v.imm), "a%d" % i)
            elif v.reg.startswith("a"):
                if int(v.reg[1:]) != i: raise Unsupported("argument register shuffle")
                self.used_params.add(v.reg)
            else: self.set_fixed(v.reg, "a%d" % i)
        rv = self.tmp(); self.callres = rv; self.fixed[rv] = "v0"
        self.emit(I("jal", rv, imm=tgt, cls="call")); return V(reg=rv, t=self.rett if self.rett.kind != "void" else INT)

    # ---------- backend
    ALU2 = {"addu", "subu", "addiu", "and", "or", "xor", "andi", "ori", "xori", "sll", "srl", "sra", "sllv", "srlv", "srav", "sltiu", "sltu"}

    LAT = {"lb": 2, "lbu": 2, "lh": 2, "lhu": 2, "lw": 2, "ld": 2, "lq": 2}          # everything else: 1 cycle
    PARAMS = ("a0", "a1", "a2", "a3")

    def finish(self):
        ir = list(self.ir); ret = self.ret_value; frame = 0
        if self.has_call:
            ji = next(i for i, x in enumerate(ir) if x.op == "jal"); dk = {x.d: k for k, x in enumerate(ir) if x.d}
            for k in range(ji + 1, len(ir)):                       # nothing may live across the call (no callee-saved registers yet)
                for x in (ir[k].a, ir[k].b):
                    if x and x != "zero" and x != self.callres and ((x in self.PARAMS) or (x in dk and dk[x] < ji)): raise Unsupported("value live across call")
            if ret and ret != self.callres and ((ret in self.PARAMS) or (ret in dk and dk[ret] < ji)): raise Unsupported("value live across call")
            frame = 16
            ir = [I("addiu", "sp", a="sp", imm=-frame, fixed="sp", boost=True), I("sd", a="sp", b="ra", imm=0, mem=True, store=True, boost=True)] + ir \
                 + [I("ld", "ra", a="sp", imm=0, mem=True, fixed="ra")]
        n = len(ir); deps = {i: {} for i in range(n)}; war = {i: set() for i in range(n)}; defs = {}; memops = []; readers = {r: [] for r in self.PARAMS}; barrier = None
        def dep(i, j, lat): deps[i][j] = max(deps[i].get(j, 0), lat)
        for i, ins in enumerate(ir):
            for x in (ins.a, ins.b):
                if x and x != "zero":
                    if x in defs: dep(i, defs[x], self.LAT.get(ir[defs[x]].op, 1))
                    if x in readers: readers[x].append(i)
            if ins.mem:
                for j in memops:
                    if ir[j].store or ins.store: dep(i, j, 1)
                memops.append(i)
            if ins.op == "jal":
                for j in range(i): dep(i, j, 1)
                barrier = i
            elif barrier is not None: dep(i, barrier, 1)
            fx = ins.fixed or self.fixed.get(ins.d)
            if fx in readers:
                for r in readers[fx]:
                    if r != i: dep(i, r, 1); war[i].add(r)           # anti-dependence: the parameter must be read first
            if ins.d: defs[ins.d] = i
        succ = {i: [] for i in range(n)}
        for i, ds in deps.items():
            for j in ds:
                if j not in war[i]: succ[j].append(i)
        prio = {}
        for i in reversed(range(n)): prio[i] = self.LAT.get(ir[i].op, 1) + max([prio[j] for j in succ[i]] or [1])
        order = self.schedule(ir, deps, prio)
        sched = [ir[i] for i in order]
        regs = self.allocate(sched, ret)                              # registers are chosen in scheduled order
        lines = []
        if self.has_call:
            jj = next(k for k, x in enumerate(sched) if x.op == "jal"); slot = None
            for k in range(jj - 1, -1, -1):                           # delay slot of the call: last instruction that can move there
                c = sched[k]
                if "ra" in (c.a, c.b): continue
                if all(not self.conflict(c, m, regs) for m in sched[k + 1:jj]): slot = k; break
            pre = [x for k, x in enumerate(sched[:jj]) if k != slot]
            lines = [self.render(x, regs) for x in pre] + [self.render(sched[jj], regs), self.render(sched[slot], regs) if slot is not None else "nop"]
            lines += [self.render(x, regs) for x in sched[jj + 1:]] + ["jr $ra", "addiu $sp, $sp, %d" % frame]
        else:
            lines = [self.render(x, regs) for x in sched]
            if lines: lines.insert(len(lines) - 1, "jr $ra")
            else: lines = ["jr $ra", "nop"]
        return self.assemble(lines)

    def conflict(self, c, m, regs):
        rd = lambda x: {regs.get(y) for y in (x.a, x.b) if y and y != "zero"}
        wr = lambda x: {regs.get(x.d)} if x.d else set()
        if wr(c) & rd(m) or rd(c) & wr(m) or wr(c) & wr(m): return True
        return bool(c.mem and m.mem and (c.store or m.store))

    def schedule(self, ir, deps, prio):
        """Cycle-by-cycle list scheduling: 2 issue slots, at most one memory operation per cycle, the call alone."""
        n = len(ir); issue = {}; order = []; cyc = 0
        while len(order) < n:
            cyc += 1; picked = []
            ready = [i for i in range(n) if i not in issue and all(j in issue and issue[j] + lat <= cyc for j, lat in deps[i].items())]
            for i in sorted(ready, key=lambda i: (not ir[i].boost, -prio[i], i)):
                if len(picked) == 2: break
                if ir[i].op == "jal" and picked: continue
                if ir[i].mem and any(ir[j].mem for j in picked): continue
                if picked and ir[picked[0]].op == "jal": break
                picked.append(i)
            for i in picked: issue[i] = cyc; order.append(i)
        return order

    def allocate(self, ir, ret):
        fixed_of = lambda ins: ins.fixed or self.fixed.get(ins.d)
        first = {}; last = {}
        for k, ins in enumerate(ir):
            for x in (ins.a, ins.b):
                if x and x != "zero": last[x] = k
            if ins.d: first[ins.d] = k
        for pr in self.PARAMS: first[pr] = -1
        ji = next((k for k, x in enumerate(ir) if x.op == "jal"), None)
        prod = {x.d: k for k, x in enumerate(ir) if x.d}
        chain = set(); cur = ret
        while cur in prod and not cur.startswith("a"):
            ins = ir[prod[cur]]
            if fixed_of(ins) is not None: break
            chain.add(cur)
            if ins.mem or ins.op in ("lui", "li"): break
            src = [x for x in (ins.a, ins.b) if x in prod and x not in chain and fixed_of(ir[prod[x]]) is None]
            nxt = src[0] if src else None
            if nxt is not None and self.callres in last and first[nxt] <= last[self.callres] and last.get(nxt, -1) >= ji: nxt = None   # would collide with the call result in $v0
            cur = nxt
            if cur is None: break
        regs = {"zero": "zero", "sp": "sp", "ra": "ra", "a0": "a0", "a1": "a1", "a2": "a2", "a3": "a3"}
        pref = ["v0", "v1", "a0", "a1", "a2", "a3", "t0", "t1", "t2", "t3"]
        occupied = {}
        for pr in self.PARAMS:
            if pr in last: occupied[pr] = (pr, last[pr])
        for k, ins in enumerate(ir):
            d = ins.d
            if not d or ins.op == "jal" and False: continue
            fx = fixed_of(ins)
            if d in ("sp", "ra"): continue
            quad = ins.op == "lq"
            if fx: r = fx
            elif d in chain: r = "v0"
            else:
                r = None
                if ins.op in self.ALU2:
                    for x in ((ins.a, ins.b) if ins.op != "sltu" else (ins.b, ins.a)):
                        if x and x in regs and x not in ("zero", "sp", "ra") and last.get(x) == k and regs[x] != "v0": r = regs[x]; break
                if r is None:
                    order = ["a0", "a1", "a2", "a3", "v1", "v0", "t0", "t1", "t2", "t3"] if (ji is not None and k > ji and ins.op == "lui") else pref
                    for c in order:
                        if quad and c in ("v0", "v1"): continue
                        held = occupied.get(c)
                        if held and held[1] >= k and held[0] != d: continue
                        if c == "v0" and any(first[c2] >= k and first[c2] <= last.get(d, k) for c2 in chain): continue
                        r = c; break
            if r is None: raise Unsupported("out of registers")
            regs[d] = r; occupied[r] = (d, last.get(d, k))
        if ret is not None and not ret.startswith("a") and regs.get(ret) != "v0": raise Unsupported("return value not in v0")
        return regs

    def render(self, x, regs):
        R = lambda v: "$" + regs[v]
        if x.op == "lui": return "lui %s, %d" % (R(x.d), x.imm)
        if x.op == "jal": return "jal 0x%x" % x.imm
        if x.op == "li":
            v = x.imm & 0xFFFFFFFF; s = v - (1 << 32) if v & 0x80000000 else v
            if v == 0: return "daddu %s, $zero, $zero" % R(x.d)
            if -0x8000 <= s <= 0x7FFF: return "addiu %s, $zero, %d" % (R(x.d), s)
            if 0 <= v <= 0xFFFF: return "ori %s, $zero, %d" % (R(x.d), v)
            raise Unsupported("32-bit constant")
        if x.mem and not x.store: return "%s %s, %d(%s)" % (x.op, R(x.d), x.imm, R(x.a))
        if x.mem and x.store: return "%s %s, %d(%s)" % (x.op, R(x.b), x.imm, R(x.a))
        if x.op in ("addiu", "andi", "ori", "xori", "sltiu"): return "%s %s, %s, %d" % (x.op, R(x.d), R(x.a), x.imm)
        if x.op in ("sll", "srl", "sra"): return "%s %s, %s, %d" % (x.op, R(x.d), R(x.a), x.imm)
        if x.op in ("sllv", "srlv", "srav"): return "%s %s, %s, %s" % (x.op, R(x.d), R(x.a), R(x.b))
        return "%s %s, %s, %s" % (x.op, R(x.d), R(x.a), R(x.b))

    def assemble(self, lines):
        self.asm = lines; pc = 0; out = []
        for ln in lines: out.append(asm.assemble(ln, pc)); pc += 4
        return out

def compile_function(cfile, name, include_dirs=("src/include",), symbols=None):
    c = Compiler(cfile, list(include_dirs), symbols); words = c.compile(name); return words, c.asm
