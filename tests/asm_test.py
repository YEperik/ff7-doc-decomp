"""Assembler validation: disassemble then assemble must reproduce the original words.
Usage: python tests/asm_test.py game/SLPM_666.29"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from ps2an.elf import Elf; from ps2an import asm, analyze as A

def main(path):
    e = Elf(path); t = A.func_table(e, A.find_functions(e, A.load_overrides("symbols/overrides.txt")))
    tot, ok, bad = asm.roundtrip(e, t); pct = 100.0 * ok / tot
    print("round-trip %d/%d (%.2f%%) over the entry code of every detected function" % (ok, tot, pct))
    print("RESULT:", "ALL PASS" if pct >= 99.5 else "FAIL"); sys.exit(0 if pct >= 99.5 else 1)

if __name__ == "__main__": main(sys.argv[1] if len(sys.argv) > 1 else "game/SLPM_666.29")
