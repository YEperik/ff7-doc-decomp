"""Fails if a directory contains anything that must not be published."""
import os, sys
BAD_EXT = {".elf", ".gzf", ".bin", ".iso", ".irx", ".erx", ".s", ".sdata", ".pak"}
SKIP = {".git", "__pycache__"}
def check(root):
    bad = []
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in SKIP]
        for n in files:
            p = os.path.join(d, n); ext = os.path.splitext(n)[1].lower()
            rel = os.path.relpath(p, root)
            if ext in BAD_EXT or n.upper().startswith(("SLPM_", "SLUS_", "SCES_")): bad.append((rel, "forbidden type"))
            elif os.path.getsize(p) > 5_000_000: bad.append((rel, "file > 5 MB"))
            else:
                with open(p, "rb") as fh: magic = fh.read(4)
                if magic in (b"\x7fELF", b"PK\x03\x04"): bad.append((rel, "binary magic"))
    return bad
if __name__ == "__main__":
    b = check(sys.argv[1] if len(sys.argv) > 1 else ".")
    for r, why in b: print("BLOCKED:", r, "-", why)
    print("public check:", "FAILED" if b else "OK"); sys.exit(1 if b else 0)
