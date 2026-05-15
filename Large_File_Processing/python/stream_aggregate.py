#!/usr/bin/env python3
"""Constant-memory aggregation over a huge FundsXML file via lxml iterparse.

Usage:  stream_aggregate.py <fundsxml.xml>

Streams Position elements one at a time, summing value (fund ccy) and
percentage and counting positions, then frees each element AND its already-
processed previous siblings so memory stays flat regardless of file size
(the classic lxml fast_iter pattern). Prints the totals and peak RSS.

FundsXML 4.x has no XML namespace — match the bare 'Position' tag.

Dependencies: lxml (`pip install lxml`); Python stdlib otherwise.
Security: iterparse runs with resolve_entities=False, no_network=True and
huge_tree=False — XXE / entity-expansion safe even on untrusted feeds.
"""
import resource
import sys

from lxml import etree


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: stream_aggregate.py <fundsxml.xml>", file=sys.stderr)
        return 2
    path = sys.argv[1]

    n = 0
    sum_value = 0.0
    sum_pct = 0.0

    # Pull events for Position end-tags only; no DTD/entity expansion.
    context = etree.iterparse(path, events=("end",), tag="Position",
                              resolve_entities=False, no_network=True,
                              huge_tree=False)
    for _, pos in context:
        amt = pos.find("./TotalValue/Amount")
        if amt is not None and amt.text:
            sum_value += float(amt.text)
        p = pos.findtext("TotalPercentage")
        if p:
            sum_pct += float(p)
        n += 1
        # Free this element and earlier siblings already parsed.
        pos.clear()
        while pos.getprevious() is not None:
            del pos.getparent()[0]
    del context

    peak_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(f"positions      : {n}")
    print(f"sum value (EUR): {sum_value:.2f}")
    print(f"sum percentage : {sum_pct:.4f}")
    print(f"peak RSS       : {peak_kb // 1024} MiB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
