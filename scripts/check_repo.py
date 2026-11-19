"""Repository hygiene check: no binaries, assembly listings, copied text or oversized files."""
import os, re, sys
BAD_EXT = {".elf", ".gzf", ".bin", ".iso", ".irx", ".erx", ".s", ".sdata", ".pak"}
TEXT_EXT = {".c", ".h", ".py", ".md", ".txt", ".json", ".csv", ".yml", ".mk", ""}
LISTING = re.compile(r"(\.word\s+0x[0-9a-fA-F]{8})|(/\*\s*[0-9a-fA-F]{6,8}\s+[0-9a-fA-F]{8}\s*\*/)|((^|\s)[0-9a-f]{8}:\s+[0-9a-f]{8}\s+[a-z]{2,7}\s+\$)", re.M)
LONGSTR = re.compile(r'"[^"\n]{40,}"')
def text_problem(txt, ext):
    """Instruction listings and long string literals are signs of copied game material."""
    if ext == ".py": return None                      # tool sources may contain format strings and docs
    if LISTING.search(txt): return "looks like a disassembly listing"
    if ext in (".c", ".h") and LONGSTR.search(txt): return "long string literal (game text?)"
    return None
SKIP = {".git", "__pycache__"}
def check(root):
    bad = []
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in SKIP]
        for n in files:
            p = os.path.join(d, n); ext = os.path.splitext(n)[1].lower()
            rel = os.path.relpath(p, root)
            if ext in BAD_EXT or n.upper().startswith(("SLPM_", "SLUS_", "SCES_")): bad.append((rel, "forbidden type"))
            elif os.path.getsize(p) > 2_000_000: bad.append((rel, "file > 2 MB"))
            else:
                with open(p, "rb") as fh: magic = fh.read(4)
                if magic in (b"\x7fELF", b"PK\x03\x04"): bad.append((rel, "binary magic"))
                elif ext in TEXT_EXT:
                    txt = open(p, errors="ignore").read(); why = text_problem(txt, ext)
                    if why: bad.append((rel, why))
    return bad
if __name__ == "__main__":
    b = check(sys.argv[1] if len(sys.argv) > 1 else ".")
    for r, why in b: print("BLOCKED:", r, "-", why)
    print("repo check:", "FAILED" if b else "OK"); sys.exit(1 if b else 0)
