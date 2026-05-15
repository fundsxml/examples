#!/usr/bin/env python3
"""Position-level diff between two FundsXML files (INITIAL vs DELTA / day-over-day).

Usage:  delta_diff.py <old.xml> <new.xml> [--json]

FundsXML's ControlData/DataOperation says INITIAL (full snapshot) or DELTA
(changes only). Independent of that flag, this compares the two position sets
by UniqueID and reports:
  added     present in new, not in old
  removed   present in old, not in new
  changed   value or percentage differs (> 0.005 tolerance)
  unchanged count only

Both files are streamed with iterparse (constant memory). Exit code: 0 if the
sets are identical, 1 if there are differences, 2 on usage error.
"""
import json
import sys

from lxml import etree


def index(path):
    op = None
    out = {}
    ctx = etree.iterparse(path, events=("end",), resolve_entities=False,
                           no_network=True)
    for _, el in ctx:
        if el.tag == "DataOperation":
            op = (el.text or "").strip()
        elif el.tag == "Position":
            uid = el.findtext("UniqueID")
            amt = el.find("./TotalValue/Amount")
            val = float(amt.text) if amt is not None and amt.text else 0.0
            pct = float(el.findtext("TotalPercentage") or 0.0)
            if uid:
                out[uid] = (val, pct)
            el.clear()
            while el.getprevious() is not None:
                del el.getparent()[0]
    return op, out


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--json"]
    as_json = "--json" in sys.argv
    if len(args) != 2:
        print("usage: delta_diff.py <old.xml> <new.xml> [--json]",
              file=sys.stderr)
        return 2

    op_old, a = index(args[0])
    op_new, b = index(args[1])

    added = sorted(set(b) - set(a))
    removed = sorted(set(a) - set(b))
    changed = sorted(u for u in (set(a) & set(b))
                     if abs(a[u][0] - b[u][0]) > 0.005
                     or abs(a[u][1] - b[u][1]) > 0.005)
    unchanged = len(set(a) & set(b)) - len(changed)

    if as_json:
        print(json.dumps({
            "old": {"file": args[0], "dataOperation": op_old, "positions": len(a)},
            "new": {"file": args[1], "dataOperation": op_new, "positions": len(b)},
            "added": added, "removed": removed,
            "changed": [{"id": u, "old": a[u], "new": b[u]} for u in changed],
            "unchanged": unchanged,
        }, indent=2))
    else:
        print(f"old: {args[0]}  DataOperation={op_old}  positions={len(a)}")
        print(f"new: {args[1]}  DataOperation={op_new}  positions={len(b)}")
        print(f"added   : {len(added)}  {added[:10]}{' ...' if len(added) > 10 else ''}")
        print(f"removed : {len(removed)}  {removed[:10]}{' ...' if len(removed) > 10 else ''}")
        print(f"changed : {len(changed)}")
        for u in changed[:10]:
            print(f"  {u}: value {a[u][0]:.2f} -> {b[u][0]:.2f}, "
                  f"pct {a[u][1]:.4f} -> {b[u][1]:.4f}")
        if len(changed) > 10:
            print("  ...")
        print(f"unchanged: {unchanged}")

    return 0 if not (added or removed or changed) else 1


if __name__ == "__main__":
    sys.exit(main())
