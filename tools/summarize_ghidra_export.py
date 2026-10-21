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
    review_header = None
    try:
        if not args.no_review_csv:
            args.review_out.parent.mkdir(parents=True, exist_ok=True)
            review_file = args.review_out.open("w", newline="", encoding="utf-8-sig")
        for path in args.csv_files:
            if not path.is_file():
                raise FileNotFoundError("CSV not found: %s" % path)
            with path.open("r", newline="", encoding="utf-8-sig", errors="replace") as f:
                # Fast row parsing using standard csv.reader and positional index lookup
                # to avoid DictReader dict allocations per row and DictWriter dict-to-list mappings.
                reader = csv.reader(f)
                try:
                    header = next(reader)
                except StopIteration:
                    continue
                if not header:
                    continue

                if review_file and review_writer is None:
                    review_writer = csv.writer(review_file)
                    review_header = list(header) + ["review_reason"]
                    review_writer.writerow(review_header)

                mnemonic_idx1 = header.index("mnemonic") if "mnemonic" in header else -1
                mnemonic_idx2 = header.index("opcode") if "opcode" in header else -1

                block_idx1 = header.index("source_block") if "source_block" in header else -1
                block_idx2 = header.index("section") if "section" in header else -1

                fn_idx = header.index("function") if "function" in header else -1

                target_idx1 = header.index("flow_targets") if "flow_targets" in header else -1
                target_idx2 = header.index("static_target") if "static_target" in header else -1

                exec_idx1 = header.index("target_executable") if "target_executable" in header else -1
                exec_idx2 = header.index("target_in_executable_load_segment") if "target_in_executable_load_segment" in header else -1

                # Map current file column positions to review_header positions to support multi-file inputs with varying schemas
                col_map = [review_header.index(col) if (review_header and col in review_header) else -1 for col in header] if review_header else []
                review_base_len = len(review_header) - 1 if review_header else 0
                is_direct_mapping = (review_header is not None and len(header) == review_base_len and col_map == list(range(review_base_len)))

                # Pre-defined reason constants to avoid string allocation in hot loop
                REASON_TARGET = "target unresolved/indirect"
                REASON_EXEC = "target not marked executable by this analysis"
                REASON_FN = "instruction is not inside a defined function"

                for row in reader:
                    total += 1
                    row_len = len(row)

                    mnemonic_raw = row[mnemonic_idx1] if mnemonic_idx1 != -1 and mnemonic_idx1 < row_len else ""
                    if not mnemonic_raw and mnemonic_idx2 != -1 and mnemonic_idx2 < row_len:
                        mnemonic_raw = row[mnemonic_idx2]
                    mnemonic = (mnemonic_raw or "<unknown>").strip().upper()
                    mnemonic_counts[mnemonic] += 1

                    block_raw = row[block_idx1] if block_idx1 != -1 and block_idx1 < row_len else ""
                    if not block_raw and block_idx2 != -1 and block_idx2 < row_len:
                        block_raw = row[block_idx2]
                    block = (block_raw or "<unknown>").strip()
                    block_counts[block] += 1

                    fn_raw = row[fn_idx] if fn_idx != -1 and fn_idx < row_len else ""
                    fn = (fn_raw or "<no function>").strip()
                    function_counts[fn] += 1

                    target_raw = row[target_idx1] if target_idx1 != -1 and target_idx1 < row_len else ""
                    if not target_raw and target_idx2 != -1 and target_idx2 < row_len:
                        target_raw = row[target_idx2]
                    target = target_raw.strip()

                    exec_raw = row[exec_idx1] if exec_idx1 != -1 and exec_idx1 < row_len else ""
                    if not exec_raw and exec_idx2 != -1 and exec_idx2 < row_len:
                        exec_raw = row[exec_idx2]
                    executable = exec_raw.strip().lower()

                    target_lower = target.lower()
                    is_missing = not target or "no resolved" in target_lower or target_lower == "indirect"
                    is_nonexec = executable in ("false", "no")
                    is_nofn = fn in ("<no function>", "")

                    if is_missing or is_nonexec or is_nofn:
                        review_rows += 1
                        reasons = []
                        if is_missing:
                            missing_targets += 1
                            flag_counts[REASON_TARGET] += 1
                            reasons.append(REASON_TARGET)
                        if is_nonexec:
                            nonexec_targets += 1
                            flag_counts[REASON_EXEC] += 1
                            reasons.append(REASON_EXEC)
                        if is_nofn:
                            no_function += 1
                            flag_counts[REASON_FN] += 1
                            reasons.append(REASON_FN)

                        if review_writer:
                            reason_str = "; ".join(reasons)
                            if is_direct_mapping and row_len == review_base_len:
                                review_writer.writerow(row + [reason_str])
                            elif is_direct_mapping:
                                out_row = list(row[:review_base_len])
                                if len(out_row) < review_base_len:
                                    out_row.extend([""] * (review_base_len - len(out_row)))
                                out_row.append(reason_str)
                                review_writer.writerow(out_row)
                            else:
                                out_row = [""] * len(review_header)
                                for src_i, dest_i in enumerate(col_map):
                                    if dest_i != -1 and src_i < row_len:
                                        out_row[dest_i] = row[src_i]
                                out_row[-1] = reason_str
                                review_writer.writerow(out_row)
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
