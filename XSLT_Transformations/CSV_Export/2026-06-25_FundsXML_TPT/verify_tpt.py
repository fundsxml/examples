#!/usr/bin/env python3
"""Sanity-check a generated TPT V7.0 CSV against the spec.

Checks, per file:
  * header column count == 152 (151 numbered TPT fields + 1000_TPT_Version)
  * every data row has the same field count as the header
  * which MANDATORY (spec flag 'M') columns are still empty across all rows
  * valuation weight (col 26) sums to ~1.0 per portfolio block (grouped by the
    portfolio identifier in col 1)

Usage:  python verify_tpt.py <tpt.csv> [<tpt.csv> ...]
"""
import csv, json, sys, os

SPEC = json.load(open(os.path.join(os.path.dirname(__file__), "work", "tpt_spec.json")))
MAN = {s["num"].split("_")[0]: s["man"] for s in SPEC}


def key(col):
    return col.split("_")[0]


def check(path):
    rows = list(csv.reader(open(path)))
    hdr, data = rows[0], rows[1:]
    problems = []
    if len(hdr) != 152:
        problems.append(f"header has {len(hdr)} columns, expected 152")
    bad = [i for i, r in enumerate(data) if len(r) != len(hdr)]
    if bad:
        problems.append(f"{len(bad)} row(s) have wrong field count")

    filled = [any(r[i].strip() for r in data) for i in range(len(hdr))]
    empty_mand = [hdr[i] for i in range(len(hdr))
                  if MAN.get(key(hdr[i])) == "M" and not filled[i]]

    # weight reconciliation per block (col 1 = portfolio id, col 26 = weight)
    blocks = {}
    for r in data:
        blocks.setdefault(r[0], []).append(r)
    weight_msgs = []
    wi = next(i for i, h in enumerate(hdr) if h.startswith("26_"))
    for pid, rs in blocks.items():
        s = sum(float(r[wi]) for r in rs if r[wi].strip())
        if abs(s - 1.0) > 0.02:
            weight_msgs.append(f"{pid[:24]}={s:.4f}")

    print(f"\n== {os.path.basename(path)} ==")
    print(f"   columns={len(hdr)}  rows={len(data)}  blocks={len(blocks)}")
    print(f"   empty mandatory cols ({len(empty_mand)}): "
          + (", ".join(c.split('_')[0] for c in empty_mand) or "none"))
    print("   weight sums per block: "
          + ("OK (~1.0)" if not weight_msgs else "OFF -> " + "; ".join(weight_msgs)))
    if problems:
        print("   PROBLEMS: " + "; ".join(problems))
    return not problems


if __name__ == "__main__":
    results = [check(p) for p in sys.argv[1:]]
    sys.exit(0 if all(results) else 1)
