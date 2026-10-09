#!/usr/bin/env python3
"""Calculate SHA-256 for any file."""
import argparse
import hashlib
from pathlib import Path

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("file", type=Path)
    args = p.parse_args()
    if not args.file.is_file():
        p.error("not a file")
    h = hashlib.sha256()
    with args.file.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    print(f"File: {args.file}")
    print(f"Size: {args.file.stat().st_size:,} bytes")
    print(f"SHA256: {h.hexdigest()}")

if __name__ == "__main__":
    main()
