"""Decompilation progress, computed only from public metadata (no ELF needed):
   symbols/functions.csv, symbols/named.txt, symbols/hubs.csv, src/game/decomp.txt."""
import csv, datetime, json, os, re

def _load_named(path):
    out = {}
    for ln in open(path) if os.path.exists(path) else []:
        m = re.match(r"\s*(\w+)\s*=\s*(0x[0-9a-fA-F]+)\s*;\s*//\s*(\S+)", ln)
        if m: out[int(m.group(2), 16)] = (m.group(1), m.group(3))
    return out

def _load_manifest(path):
    return {int(m.group(2), 16): m.group(1) for m in (re.match(r"\s*(\w+)\s*=\s*(0x[0-9a-fA-F]+);", l) for l in open(path)) if m} if os.path.exists(path) else {}

def compute(root=".", decomp=None, libc=True):
    """decomp/libc let history backfill recompute earlier milestones."""
    funcs = [(int(r["address"], 16), int(r["size"]), r["section"]) for r in csv.DictReader(open(os.path.join(root, "symbols/functions.csv")))]
    named = _load_named(os.path.join(root, "symbols/named.txt"))
    done = set(decomp if decomp is not None else _load_manifest(os.path.join(root, "src/game/decomp.txt")))
    if libc: done |= {a for a, (_n, ev) in named.items() if ev == "behavior-verified"}       # libc functions with tested C in src/libc
    ident = {a for a in named if a not in done}
    mpath = os.path.join(root, "src/game/matched.txt")
    matched = set(_load_manifest(mpath)) & done if os.path.exists(mpath) and decomp is None else set()
    tot_f, tot_b = len(funcs), sum(s for _, s, _ in funcs)
    df = [f for f in funcs if f[0] in done]; db = sum(s for _, s, _ in df)
    sec = {}
    for a, s, name in funcs:
        d = sec.setdefault(name, [0, 0, 0, 0]); d[1] += 1; d[3] += s
        if a in done: d[0] += 1; d[2] += s
    mf = [f for f in funcs if f[0] in matched]; mb = sum(x[1] for x in mf)
    hubs = []
    p = os.path.join(root, "symbols/hubs.csv")
    if os.path.exists(p): hubs = [(int(r["address"], 16), int(r["callers"])) for r in csv.DictReader(open(p))]
    hd = [h for h in hubs if h[0] in done]
    return {"functions_done": len(df), "functions_total": tot_f, "functions_pct": 100.0 * len(df) / tot_f,
            "bytes_done": db, "bytes_total": tot_b, "bytes_pct": 100.0 * db / tot_b,
            "matched_done": len(mf), "matched_bytes": mb, "matched_pct": 100.0 * mb / tot_b,
            "identified_only": len(ident), "hubs_done": len(hd), "hubs_total": len(hubs),
            "hubs_pct": 100.0 * len(hd) / max(1, len(hubs)),
            "callsites_done": sum(c for _, c in hd), "callsites_total": sum(c for _, c in hubs),
            "callsites_pct": 100.0 * sum(c for _, c in hd) / max(1, sum(c for _, c in hubs)),
            "sections": {k: {"done": v[0], "total": v[1], "bytes_done": v[2], "bytes_total": v[3]} for k, v in sorted(sec.items(), key=lambda kv: -kv[1][3])}}

def _color(p): return "#e05d44" if p < 10 else "#dfb317" if p < 50 else "#97ca00"
def _w(t, k=6.4): return int(len(t) * k + 12)

def badge(label, value, color):
    lw, vw = _w(label), _w(value); W = lw + vw
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="20" role="img" aria-label="%s: %s">'
            '<linearGradient id="s" x2="0" y2="100%%"><stop offset="0" stop-color="#bbb" stop-opacity=".1"/><stop offset="1" stop-opacity=".1"/></linearGradient>'
            '<clipPath id="r"><rect width="%d" height="20" rx="3" fill="#fff"/></clipPath><g clip-path="url(#r)"><rect width="%d" height="20" fill="#555"/>'
            '<rect x="%d" width="%d" height="20" fill="%s"/><rect width="%d" height="20" fill="url(#s)"/></g>'
            '<g fill="#fff" text-anchor="middle" font-family="Verdana,DejaVu Sans,sans-serif" font-size="11"><text x="%d" y="14">%s</text><text x="%d" y="14">%s</text></g></svg>'
            % (W, label, value, W, lw, lw, vw, color, W, lw / 2, label, lw + vw / 2, value))

def card(m):
    rows = [("Functions", m["functions_pct"], "%d / %d" % (m["functions_done"], m["functions_total"])),
            ("Code bytes", m["bytes_pct"], "%s / %s" % (format(m["bytes_done"], ","), format(m["bytes_total"], ","))),
            ("Byte-exact", m["matched_pct"], "%d functions" % m["matched_done"]),
            ("Top-300 hubs", m["hubs_pct"], "%d / %d" % (m["hubs_done"], m["hubs_total"])),
            ("Hub call sites", m["callsites_pct"], "%s / %s" % (format(m["callsites_done"], ","), format(m["callsites_total"], ",")))]
    o = ['<svg xmlns="http://www.w3.org/2000/svg" width="760" height="%d" font-family="Verdana,DejaVu Sans,sans-serif">' % (64 + 34 * len(rows)),
         '<style>.t{fill:#e6e6ee}.m{fill:#9aa0b4}@media (prefers-color-scheme: light){.bg{fill:#f4f4f8}.t{fill:#1b1b24}.m{fill:#555a6e}.tr{fill:#dcdce6}}</style>',
         '<rect class="bg" width="760" height="%d" rx="10" fill="#12131c"/>' % (64 + 34 * len(rows)),
         '<text class="t" x="24" y="34" font-size="17" font-weight="bold">Decompilation progress</text>',
         '<text class="m" x="736" y="34" font-size="12" text-anchor="end">C reconstructions tested against the original</text>']
    y = 62
    for lab, p, txt in rows:
        fill = max(2.0, 360 * p / 100.0)
        o += ['<text class="t" x="24" y="%d" font-size="13">%s</text>' % (y + 14, lab),
              '<rect class="tr" x="160" y="%d" width="360" height="18" rx="4" fill="#262838"/>' % y,
              '<rect x="160" y="%d" width="%.1f" height="18" rx="4" fill="%s"/>' % (y, fill, _color(p)),
              '<text class="t" x="532" y="%d" font-size="13" font-weight="bold">%.2f%%</text>' % (y + 14, p),
              '<text class="m" x="606" y="%d" font-size="11">%s</text>' % (y + 14, txt)]
        y += 34
    return "\n".join(o) + "</svg>"

HIST = "progress/history.csv"
def read_history(root):
    p = os.path.join(root, HIST)
    return list(csv.DictReader(open(p))) if os.path.exists(p) else []

def record(root, m, label, date=None):
    rows = read_history(root); date = date or datetime.date.today().isoformat()
    rows = [dict(r, matched_done=r.get("matched_done") or 0) for r in rows if r["milestone"] != label]
    rows.append({"milestone": label, "date": date, "functions_done": m["functions_done"], "functions_total": m["functions_total"],
                 "bytes_done": m["bytes_done"], "bytes_total": m["bytes_total"], "hubs_done": m["hubs_done"], "matched_done": m["matched_done"]})
    os.makedirs(os.path.join(root, "progress"), exist_ok=True)
    with open(os.path.join(root, HIST), "w", newline="") as fh:
        w = csv.DictWriter(fh, ["milestone", "date", "functions_done", "functions_total", "bytes_done", "bytes_total", "hubs_done", "matched_done"], lineterminator="\n")
        w.writeheader(); w.writerows(rows)

def render_markdown(root, m):
    L = ["# Progress", "",
         "Generated by `python -m ps2an progress` from public metadata. A function counts as **decompiled** when its C reconstruction passes the differential tests (`make test`) against the original code.", "",
         "| Metric | Done | Total | % |", "|---|---:|---:|---:|",
         "| Functions | %d | %d | %.2f%% |" % (m["functions_done"], m["functions_total"], m["functions_pct"]),
         "| Code bytes | %s | %s | %.2f%% |" % (format(m["bytes_done"], ","), format(m["bytes_total"], ","), m["bytes_pct"]),
         "| Byte-exact functions | %d | %d | %.2f%% (bytes) |" % (m["matched_done"], m["functions_total"], m["matched_pct"]),
         "| Top-300 most-called functions | %d | %d | %.1f%% |" % (m["hubs_done"], m["hubs_total"], m["hubs_pct"]),
         "| Call sites into those hubs | %s | %s | %.1f%% |" % (format(m["callsites_done"], ","), format(m["callsites_total"], ","), m["callsites_pct"]),
         "", "Identified (named, not yet decompiled): **%d** functions." % m["identified_only"], "",
         "## By section", "", "| Section | Functions | Code bytes |", "|---|---:|---:|"]
    for k, v in m["sections"].items():
        L.append("| `%s` | %d / %d | %s / %s (%.2f%%) |" % (k, v["done"], v["total"], format(v["bytes_done"], ","), format(v["bytes_total"], ","), 100.0 * v["bytes_done"] / max(1, v["bytes_total"])))
    h = read_history(root)
    if h:
        L += ["", "## History", "", "| Milestone | Date | Functions | Code bytes | Byte-exact | Hubs |", "|---|---|---:|---:|---:|---:|"]
        for r in h: L.append("| %s | %s | %s | %.2f%% | %s | %s |" % (r["milestone"], r["date"], r["functions_done"], 100.0 * int(r["bytes_done"]) / int(r["bytes_total"]), r.get("matched_done") or 0, r["hubs_done"]))
    return "\n".join(L) + "\n"

START, END = "<!-- PROGRESS:START -->", "<!-- PROGRESS:END -->"
def readme_block(m):
    return "\n".join([START, '<p align="center"><img src="assets/progress.svg" alt="Decompilation progress" width="760"></p>', "",
        "| | Done | Total |", "|---|---:|---:|",
        "| Functions | %d (%.2f%%) | %d |" % (m["functions_done"], m["functions_pct"], m["functions_total"]),
        "| Code bytes | %.2f%% | %s |" % (m["bytes_pct"], format(m["bytes_total"], ",")),
        "| Byte-exact | %d (%.2f%% of bytes) | %d |" % (m["matched_done"], m["matched_pct"], m["functions_total"]),
        "| Most-called 300 | %d (%.1f%%) | %d |" % (m["hubs_done"], m["hubs_pct"], m["hubs_total"]),
        "", "Details and history: [docs/PROGRESS.md](docs/PROGRESS.md)", END])

def outputs(root, m):
    return {"progress/progress.json": json.dumps(m, indent=2) + "\n", "assets/progress.svg": card(m),
            "assets/badge-decompiled.svg": badge("decompiled", "%.2f%%" % m["bytes_pct"], _color(m["bytes_pct"])),
            "docs/PROGRESS.md": render_markdown(root, m)}

def write_all(root, m):
    for rel, text in outputs(root, m).items():
        os.makedirs(os.path.dirname(os.path.join(root, rel)), exist_ok=True); open(os.path.join(root, rel), "w").write(text)
    p = os.path.join(root, "README.md"); s = open(p).read()
    if START in s: s = re.sub(re.escape(START) + ".*?" + re.escape(END), lambda _m: readme_block(m), s, flags=re.S)
    open(p, "w").write(s)

def check(root, m):
    """True when generated files are in sync (used by CI)."""
    bad = [rel for rel, text in outputs(root, m).items() if not os.path.exists(os.path.join(root, rel)) or open(os.path.join(root, rel)).read() != text]
    s = open(os.path.join(root, "README.md")).read()
    if START not in s or re.search(re.escape(START) + ".*?" + re.escape(END), s, re.S).group(0) != readme_block(m): bad.append("README.md")
    return bad
