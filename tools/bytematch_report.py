#!/usr/bin/env python3
"""Build an objdiff-format progress report (report.json) for ByteMatch from PUBLIC metadata only.

Inputs (all committed, no game files needed):
  symbols/functions.csv   address,size,section,name   -> every function of the game
  symbols/named.txt       name = addr; // evidence     -> names; "behavior-verified" = tested C exists
  src/game/decomp.txt     name = addr;                 -> C reconstruction passes tests/game_test.py
  src/game/matched.txt    name = addr;                 -> C compiles to the exact original bytes

Meaning of the numbers (honest mapping to objdiff's vocabulary):
  matched   = byte-exact functions only (matched.txt)  -> fuzzy_match_percent 100
  functional= tested-but-not-byte-exact C (decomp.txt minus matched.txt) -> functional.json, never counted as matched
  everything else is unmatched (0%).

Usage:  python3 tools/bytematch_report.py [-o build/bytematch] [--version SLPM_666.29] [--check]
"""
import argparse, csv, glob, json, os, re, sys

MANIFEST = re.compile(r"\s*(\w+)\s*=\s*(0x[0-9a-fA-F]+)\s*;")
NAMED = re.compile(r"\s*(\w+)\s*=\s*(0x[0-9a-fA-F]+)\s*;\s*//\s*(\S+)")
ADDR_COMMENT = re.compile(r"/\*\s*(0x[0-9a-fA-F]{8})\b")
CHUNK = 0x10000  # address span of one "unsorted" unit, keeps the unit map readable


def manifest(path):
    if not os.path.exists(path):
        return {}
    return {int(m.group(2), 16): m.group(1) for m in map(MANIFEST.match, open(path)) if m}


def named(path):
    out = {}
    if os.path.exists(path):
        for ln in open(path):
            m = NAMED.match(ln)
            if m:
                out[int(m.group(2), 16)] = (m.group(1), m.group(3))
    return out


def source_index(root, wanted):
    """address -> source file, from `/* 0x........` comments placed above/next to each function."""
    idx = {}
    for f in sorted(glob.glob(os.path.join(root, "src", "*", "*.c"))):
        rel = os.path.relpath(f, root).replace(os.sep, "/")
        for a in ADDR_COMMENT.findall(open(f, errors="ignore").read()):
            a = int(a, 16)
            if a in wanted and a not in idx:
                idx[a] = rel
    return idx


def u64(x):
    return str(int(x))  # objdiff's JSON writes 64-bit integers as strings


def measures(items, total_units=1, complete_units=0):
    """items: list of (size, matched_bool)."""
    tc = sum(s for s, _ in items)
    mc = sum(s for s, m in items if m)
    tf, mf = len(items), sum(1 for _, m in items if m)
    pct = lambda a, b: (100.0 * a / b) if b else 0.0
    return {
        "fuzzy_match_percent": pct(mc, tc), "total_code": u64(tc), "matched_code": u64(mc),
        "matched_code_percent": pct(mc, tc), "total_data": u64(0), "matched_data": u64(0),
        "matched_data_percent": 0.0, "total_functions": tf, "matched_functions": mf,
        "matched_functions_percent": pct(mf, tf), "complete_code": u64(0), "complete_code_percent": 0.0,
        "complete_data": u64(0), "complete_data_percent": 0.0,
        "total_units": total_units, "complete_units": complete_units,
    }


def build(root, version):
    funcs = [(int(r["address"], 16), int(r["size"]), r["section"], r["name"])
             for r in csv.DictReader(open(os.path.join(root, "symbols/functions.csv")))]
    nm = named(os.path.join(root, "symbols/named.txt"))
    dec = manifest(os.path.join(root, "src/game/decomp.txt"))
    mat = manifest(os.path.join(root, "src/game/matched.txt"))
    done = set(dec) | {a for a, (_n, ev) in nm.items() if ev == "behavior-verified"}
    matched = set(mat) & done  # same rule as ps2an/progress.py
    src = source_index(root, done)

    def fname(a, csvname):
        return dec.get(a) or (nm[a][0] if a in nm else None) or csvname

    # unit name -> (source_path or None, [function entries])
    units = {}
    for a, size, sec, csvname in funcs:
        if a in src:
            rel = src[a]                                  # src/game/heap.c -> game/heap
            uname = os.path.splitext(rel[len("src/"):])[0]
            spath = rel
        elif a in done:
            uname, spath = "game/unlocated", "src/game"     # tested C exists but no address comment found
        else:
            uname, spath = "unsorted/%s/%04x" % (sec.lstrip(".").replace("_", "-"), a // CHUNK), None
        units.setdefault(uname, (spath, []))[1].append((a, size, sec, fname(a, csvname), a in matched))

    out_units, functional = [], []
    for uname in sorted(units):
        spath, fl = units[uname]
        fl.sort()
        items = [(s, m) for _a, s, _sec, _n, m in fl]
        secs = {}
        for _a, s, sec, _n, m in fl:
            d = secs.setdefault(sec, [0, 0]); d[0] += s; d[1] += s if m else 0
        unit = {
            "name": uname,
            "measures": measures(items),
            "sections": [{"name": k, "size": u64(v[0]), "fuzzy_match_percent": 100.0 * v[1] / v[0] if v[0] else 0.0}
                         for k, v in sorted(secs.items())],
            "functions": [{"name": n, "size": u64(s), "fuzzy_match_percent": 100.0 if m else 0.0,
                           "metadata": {"virtual_address": u64(a)}} for a, s, _sec, n, m in fl],
            "metadata": {"complete": False, "auto_generated": spath is None},
        }
        if spath:
            unit["metadata"]["source_path"] = spath
        out_units.append(unit)
        for a, s, _sec, n, m in fl:
            if a in done and not m:
                functional.append({"name": n, "confidence": "high"})  # passes differential tests vs original

    allitems = [(s, m) for u in units.values() for _a, s, _sec, _n, m in u[1]]
    report = {"measures": measures(allitems, total_units=len(out_units), complete_units=0),
              "units": out_units, "version": 2}
    return report, {"functions": functional}, {"done": len(done), "matched": len(matched), "located": len(src), "units": len(out_units), "total": len(funcs)}


def validate(report, stats, root):
    """Self-consistency checks so a broken report never reaches CI/ByteMatch."""
    errs = []
    m = report["measures"]
    fsum = sum(len(u["functions"]) for u in report["units"])
    csum = sum(int(f["size"]) for u in report["units"] for f in u["functions"])
    msum = sum(int(f["size"]) for u in report["units"] for f in u["functions"] if f["fuzzy_match_percent"] == 100.0)
    if fsum != m["total_functions"] or fsum != stats["total"]: errs.append("function count mismatch")
    if csum != int(m["total_code"]): errs.append("total_code mismatch")
    if msum != int(m["matched_code"]): errs.append("matched_code mismatch")
    # cross-check against the project's own progress calculation
    pj = os.path.join(root, "progress", "progress.json")
    if os.path.exists(pj):
        p = json.load(open(pj))
        if p.get("matched_done") != m["matched_functions"]: errs.append("matched functions differ from progress/progress.json")
        if p.get("matched_bytes") != int(m["matched_code"]): errs.append("matched bytes differ from progress/progress.json")
        if p.get("functions_total") != m["total_functions"]: errs.append("function total differs from progress/progress.json")
    return errs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--out", default="build/bytematch")
    ap.add_argument("--root", default=".")
    ap.add_argument("--check", action="store_true", help="validate only, write nothing")
    a = ap.parse_args()
    report, functional, st = build(a.root, None)
    errs = validate(report, st, a.root)
    for e in errs: print("ERROR:", e, file=sys.stderr)
    if errs: return 1
    m = report["measures"]
    print("units %d | functions %d | matched(byte-exact) %d (%.3f%% code) | functional-only %d | located in src: %d/%d"
          % (st["units"], m["total_functions"], m["matched_functions"], m["matched_code_percent"],
             len(functional["functions"]), st["located"], st["done"]))
    if not a.check:
        os.makedirs(a.out, exist_ok=True)
        json.dump(report, open(os.path.join(a.out, "report.json"), "w"), separators=(",", ":"))
        json.dump(functional, open(os.path.join(a.out, "functional.json"), "w"), indent=1)
        print("wrote", os.path.join(a.out, "report.json"), "and functional.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
