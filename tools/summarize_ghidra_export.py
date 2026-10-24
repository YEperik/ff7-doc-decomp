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
    # Pre-defined review reason strings to avoid string allocations inside hot loop
    REASON_UNRESOLVED = "target unresolved/indirect"
    REASON_NONEXEC = "target not marked executable by this analysis"
    REASON_NOFUNC = "instruction is not inside a defined function"
    COMBO_12 = REASON_UNRESOLVED + "; " + REASON_NONEXEC
    COMBO_13 = REASON_UNRESOLVED + "; " + REASON_NOFUNC
    COMBO_23 = REASON_NONEXEC + "; " + REASON_NOFUNC
    COMBO_123 = REASON_UNRESOLVED + "; " + REASON_NONEXEC + "; " + REASON_NOFUNC

    # Use standard dict instead of Counter inside the hot loop to reduce method lookup overhead
    mnemonic_counts, block_counts, function_counts, flag_counts = {}, {}, {}, {}
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

                # Pre-resolve primary and alternate column indices per file
                m_idx = header.index("mnemonic") if "mnemonic" in header else (header.index("opcode") if "opcode" in header else -1)
                alt_m_idx = header.index("opcode") if ("mnemonic" in header and "opcode" in header) else -1

                b_idx = header.index("source_block") if "source_block" in header else (header.index("section") if "section" in header else -1)
                alt_b_idx = header.index("section") if ("source_block" in header and "section" in header) else -1

                fn_i = header.index("function") if "function" in header else -1

                t_idx = header.index("flow_targets") if "flow_targets" in header else (header.index("static_target") if "static_target" in header else -1)
                alt_t_idx = header.index("static_target") if ("flow_targets" in header and "static_target" in header) else -1

                e_idx = header.index("target_executable") if "target_executable" in header else (header.index("target_in_executable_load_segment") if "target_in_executable_load_segment" in header else -1)
                alt_e_idx = header.index("target_in_executable_load_segment") if ("target_executable" in header and "target_in_executable_load_segment" in header) else -1

                # Map current file column positions to review_header positions to support multi-file inputs with varying schemas
                col_map = [review_header.index(col) if (review_header and col in review_header) else -1 for col in header] if review_header else []
                review_base_len = len(review_header) - 1 if review_header else 0
                is_direct_mapping = (review_header is not None and len(header) == review_base_len and col_map == list(range(review_base_len)))

                for row in reader:
                    total += 1
                    row_len = len(row)

                    m_raw = row[m_idx] if m_idx != -1 and m_idx < row_len else ""
                    if not m_raw and alt_m_idx != -1 and alt_m_idx < row_len:
                        m_raw = row[alt_m_idx]
                    mnemonic = m_raw.strip().upper() if m_raw else "<UNKNOWN>"
                    mnemonic_counts[mnemonic] = mnemonic_counts.get(mnemonic, 0) + 1

                    b_raw = row[b_idx] if b_idx != -1 and b_idx < row_len else ""
                    if not b_raw and alt_b_idx != -1 and alt_b_idx < row_len:
                        b_raw = row[alt_b_idx]
                    block = b_raw.strip() if b_raw else "<unknown>"
                    block_counts[block] = block_counts.get(block, 0) + 1

                    fn_raw = row[fn_i] if fn_i != -1 and fn_i < row_len else ""
                    fn = fn_raw.strip() if fn_raw else "<no function>"
                    function_counts[fn] = function_counts.get(fn, 0) + 1

                    t_raw = row[t_idx] if t_idx != -1 and t_idx < row_len else ""
                    if not t_raw and alt_t_idx != -1 and alt_t_idx < row_len:
                        t_raw = row[alt_t_idx]
                    target = t_raw.strip() if t_raw else ""
                    target_lower = target.lower() if target else ""

                    e_raw = row[e_idx] if e_idx != -1 and e_idx < row_len else ""
                    if not e_raw and alt_e_idx != -1 and alt_e_idx < row_len:
                        e_raw = row[alt_e_idx]
                    executable = e_raw.strip().lower() if e_raw else ""

                    r1 = not target_lower or "no resolved" in target_lower or target_lower == "indirect"
                    r2 = executable in ("false", "no")
                    r3 = fn in ("<no function>", "")

                    if r1 or r2 or r3:
                        review_rows += 1
                        if r1:
                            missing_targets += 1
                            flag_counts[REASON_UNRESOLVED] = flag_counts.get(REASON_UNRESOLVED, 0) + 1
                        if r2:
                            nonexec_targets += 1
                            flag_counts[REASON_NONEXEC] = flag_counts.get(REASON_NONEXEC, 0) + 1
                        if r3:
                            no_function += 1
                            flag_counts[REASON_NOFUNC] = flag_counts.get(REASON_NOFUNC, 0) + 1

                        if review_writer:
                            if r1 and r2 and r3:
                                reason_str = COMBO_123
                            elif r1 and r2:
                                reason_str = COMBO_12
                            elif r1 and r3:
                                reason_str = COMBO_13
                            elif r2 and r3:
                                reason_str = COMBO_23
                            elif r1:
                                reason_str = REASON_UNRESOLVED
                            elif r2:
                                reason_str = REASON_NONEXEC
                            else:
                                reason_str = REASON_NOFUNC

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
                   "mnemonic_counts": dict(sorted(mnemonic_counts.items(), key=lambda x: x[1], reverse=True)),
                   "rows_by_section_or_block": dict(sorted(block_counts.items(), key=lambda x: x[1], reverse=True)),
                   "top_functions": sorted(function_counts.items(), key=lambda x: x[1], reverse=True)[:100],
                   "unresolved_or_indirect_target_rows": missing_targets,
                   "targets_not_marked_executable_rows": nonexec_targets,
                   "rows_without_defined_function": no_function, "rows_flagged_for_manual_review": review_rows,
                   "review_flag_reason_counts": flag_counts,
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
