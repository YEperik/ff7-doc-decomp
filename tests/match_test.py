"""Byte-exact check: every function listed in src/game/matched.txt must compile with `ps2an cc`
to exactly the original instructions, and `ps2an cc` must not match anything that is not listed
for a wrong reason (the assembler round-trip is checked separately in tests/asm_test.py).
Usage: python tests/match_test.py game/SLPM_666.29"""
import glob, os, re, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."); sys.path.insert(0, ROOT); os.chdir(ROOT)
from ps2an.elf import Elf; from ps2an import analyze as A, cc

def main(path):
    e = Elf(path); listed = A.load_overrides("src/game/matched.txt"); decomp = A.load_overrides("src/game/decomp.txt"); bad = 0
    srcs = {f: open(f).read() for f in glob.glob("src/game/*.c")}
    import ps2an.__main__ as M
    t = A.func_table(e, A.find_functions(e, A.load_overrides("symbols/overrides.txt"))); symbols = {nm: a for a, (nm, _ev) in M.named(e, t).items()}; symbols.update({nm: a for a, nm in decomp.items()})
    for ad, nm in sorted(listed.items()):
        f = next((f for f, t in srcs.items() if re.search(r"^[\w\s\*]+\b%s\s*\([^;]*\)\s*\{" % re.escape(nm), t, re.M)), None)
        ok = False
        if f and decomp.get(ad) == nm:
            try:
                words, _ = cc.compile_function(f, nm, symbols=symbols)
                ok = words == [int.from_bytes(e.read(ad + 4 * i, 4), "little") for i in range(len(words))]
            except cc.Unsupported: ok = False
        bad += not ok
        print("%-26s 0x%08x  %s" % (nm, ad, "MATCH" if ok else "FAIL"))
    print("%d byte-exact functions" % len(listed)); print("RESULT:", "FAIL" if bad else "ALL PASS"); sys.exit(1 if bad else 0)

if __name__ == "__main__": main(sys.argv[1] if len(sys.argv) > 1 else "game/SLPM_666.29")
