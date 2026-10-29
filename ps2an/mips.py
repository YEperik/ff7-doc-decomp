"""Tiny MIPS III / R5900 decoder: enough for call graphs, prologues and xrefs."""
R = "zero at v0 v1 a0 a1 a2 a3 t0 t1 t2 t3 t4 t5 t6 t7 s0 s1 s2 s3 s4 s5 s6 s7 t8 t9 k0 k1 gp sp fp ra".split()
def s16(x): return x - 0x10000 if x & 0x8000 else x

_SPECIAL = {0:"sll",2:"srl",3:"sra",4:"sllv",6:"srlv",7:"srav",8:"jr",9:"jalr",10:"movz",11:"movn",12:"syscall",
 13:"break",15:"sync",16:"mfhi",17:"mthi",18:"mflo",19:"mtlo",20:"dsllv",22:"dsrlv",23:"dsrav",24:"mult",25:"multu",
 26:"div",27:"divu",32:"add",33:"addu",34:"sub",35:"subu",36:"and",37:"or",38:"xor",39:"nor",40:"mfsa",41:"mtsa",
 42:"slt",43:"sltu",44:"dadd",45:"daddu",46:"dsub",47:"dsubu",56:"dsll",58:"dsrl",59:"dsra",60:"dsll32",62:"dsrl32",63:"dsra32"}
_IMM = {8:"addi",9:"addiu",10:"slti",11:"sltiu",12:"andi",13:"ori",14:"xori",24:"daddi",25:"daddiu"}
_MEM = {32:"lb",33:"lh",34:"lwl",35:"lw",36:"lbu",37:"lhu",38:"lwr",39:"lwu",40:"sb",41:"sh",42:"swl",43:"sw",44:"sdl",
 45:"sdr",46:"swr",49:"lwc1",55:"ld",57:"swc1",61:"sqc2",54:"lqc2",63:"sd",30:"lq",31:"sq",26:"ldl",27:"ldr",52:"lld"}
_BR = {4:"beq",5:"bne",6:"blez",7:"bgtz",20:"beql",21:"bnel",22:"blezl",23:"bgtzl"}
_RI = {0:"bltz",1:"bgez",2:"bltzl",3:"bgezl",16:"bltzal",17:"bgezal"}

def is_jr_ra(w): return w == 0x03E00008
def is_nop(w): return w == 0
def is_jal(w): return w >> 26 == 3
def jal_target(w, pc): return ((pc + 4) & 0xF0000000) | ((w & 0x3FFFFFF) << 2)
def is_sp_alloc(w):
    """addiu/daddiu sp,sp,-N"""
    return (w >> 26) in (9, 25) and ((w >> 21) & 31) == 29 and ((w >> 16) & 31) == 29 and (w & 0x8000) != 0
def sp_frame(w): return -s16(w & 0xFFFF)

def decode(w, pc):
    op = w >> 26; rs = (w >> 21) & 31; rt = (w >> 16) & 31; rd = (w >> 11) & 31; sa = (w >> 6) & 31; imm = w & 0xFFFF
    if w == 0: return "nop"
    if op == 0:
        f = w & 63; m = _SPECIAL.get(f)
        if not m: return ".word 0x%08x" % w
        if f in (0,2,3,56,58,59,60,62,63): return "%s $%s, $%s, %d" % (m, R[rd], R[rt], sa)
        if f in (4,6,7,20,22,23): return "%s $%s, $%s, $%s" % (m, R[rd], R[rt], R[rs])
        if f == 8: return "jr $%s" % R[rs]
        if f == 9: return "jalr $%s, $%s" % (R[rd], R[rs])
        if f in (16,18): return "%s $%s" % (m, R[rd])
        if f in (17,19,41): return "%s $%s" % (m, R[rs])
        if f == 40: return "mfsa $%s" % R[rd]
        if f in (24,25,26,27): return "%s $%s, $%s" % (m, R[rs], R[rt])
        if f in (12,13,15): return m
        return "%s $%s, $%s, $%s" % (m, R[rd], R[rs], R[rt])
    if op == 1:
        m = _RI.get(rt)
        return ("%s $%s, 0x%x" % (m, R[rs], pc + 4 + (s16(imm) << 2))) if m else ".word 0x%08x" % w
    if op in (2, 3): return "%s 0x%x" % ("j" if op == 2 else "jal", jal_target(w, pc))
    if op in _BR:
        t = pc + 4 + (s16(imm) << 2)
        if op in (4,5,20,21): return "%s $%s, $%s, 0x%x" % (_BR[op], R[rs], R[rt], t)
        return "%s $%s, 0x%x" % (_BR[op], R[rs], t)
    if op == 15: return "lui $%s, 0x%x" % (R[rt], imm)
    if op in _IMM:
        v = imm if op in (12,13,14) else s16(imm)
        return "%s $%s, $%s, %s" % (_IMM[op], R[rt], R[rs], hex(v) if v >= 0 else "-" + hex(-v))
    if op in _MEM:
        reg = "$f%d" % rt if op in (49,57) else ("$vf%d" % rt if op in (54,61) else "$" + R[rt])
        return "%s %s, %d($%s)" % (_MEM[op], reg, s16(imm), R[rs])
    if op == 16 and rs in (0, 4): return "%s $%s, $%d" % ("mfc0" if rs == 0 else "mtc0", R[rt], rd)
    if op == 17 and rs in (0, 4): return "%s $%s, $f%d" % ("mfc1" if rs == 0 else "mtc1", R[rt], rd)
    return ".word 0x%08x" % w
