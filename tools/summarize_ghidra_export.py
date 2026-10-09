#!/usr/bin/env python3
"""Summarize large Ghidra JAL CSV exports without loading them all into memory."""
import argparse, csv, json
from collections import Counter
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv_files", nargs="+", type=Path, help="One or more Ghidra CSV parts or scanner CSV files")
    ap.add_argument("--out", type=Path, default=Path("reports/ghidra_summary.json"), help="Summary JSON path")
    ap.add_argument("--review-out", type=Path, default=Path("reports/rows_for_review.csv"), help="Rows flagged for manual review")
    ap.add_argument("--no-review-csv", action="store_true", help="Do not write review CSV")
    args = ap.parse_args()
    mnemonic_counts, block_counts, function_counts, flag_counts = Counter(), Counter(), Counter(), Counter()
    total, missing_targets, nonexec_targets, no_function, review_rows = 0, 0, 0, 0, 0
    review_writer = review_file = None
    try:
        if not args.no_review_csv:
            args.review_out.parent.mkdir(parents=True, exist_ok=True)
            review_file = args.review_out.open("w", newline="", encoding="utf-8-sig")
        for path in args.csv_files:
            if not path.is_file():
                raise FileNotFoundError("CSV not found: %s" % path)
            with path.open("r", newline="", encoding="utf-8-sig", errors="replace") as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    continue
                if review_file and review_writer is None:
                    review_writer = csv.DictWriter(review_file, fieldnames=list(reader.fieldnames) + ["review_reason"], extrasaction="ignore")
                    review_writer.writeheader()
                for row in reader:
                    total += 1
                    mnemonic = (row.get("mnemonic") or row.get("opcode") or "<unknown>").strip().upper()
                    mnemonic_counts[mnemonic] += 1
                    block = (row.get("source_block") or row.get("section") or "<unknown>").strip()
                    block_counts[block] += 1
                    fn = (row.get("function") or "<no function>").strip()
                    function_counts[fn] += 1
                    target = (row.get("flow_targets") or row.get("static_target") or "").strip()
                    executable = (row.get("target_executable") or row.get("target_in_executable_load_segment") or "").strip().lower()
                    reasons = []
                    if not target or "no resolved" in target.lower() or "indirect" == target.lower():
                        missing_targets += 1
                        reasons.append("target unresolved/indirect")
                    if executable in ("false", "no"):
                        nonexec_targets += 1
                        reasons.append("target not marked executable by this analysis")
                    if fn in ("<no function>", ""):
                        no_function += 1
                        reasons.append("instruction is not inside a defined function")
                    if reasons:
                        review_rows += 1
                        flag_counts.update(reasons)
                        if review_writer:
                            review_writer.writerow(dict(row, review_reason="; ".join(reasons)))
        summary = {"input_files": [str(p) for p in args.csv_files], "rows_processed": total,
                   "mnemonic_counts": dict(mnemonic_counts.most_common()),
                   "rows_by_section_or_block": dict(block_counts.most_common()),
                   "top_functions": function_counts.most_common(100),
                   "unresolved_or_indirect_target_rows": missing_targets,
                   "targets_not_marked_executable_rows": nonexec_targets,
                   "rows_without_defined_function": no_function, "rows_flagged_for_manual_review": review_rows,
                   "review_flag_reason_counts": dict(flag_counts),
                   "warning": "Review flags are triage hints only. Overlays, data-as-code, imports and Ghidra memory mapping can make a target appear non-executable without being a broken instruction."}
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print("Rows processed: %s" % format(total, ","))
        print("Mnemonics: %s" % dict(mnemonic_counts))
        print("Rows flagged for manual review: %s" % format(review_rows, ","))
        print("Summary: %s" % args.out.resolve())
        if review_file:
            review_file.close()
            print("Review CSV: %s" % args.review_out.resolve())
        return 0
    except (OSError, csv.Error) as exc:
        if review_file:
            review_file.close()
        ap.error(str(exc))

if __name__ == "__main__":
    raise SystemExit(main())
