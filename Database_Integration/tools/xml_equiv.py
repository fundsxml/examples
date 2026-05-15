#!/usr/bin/env python3
"""Normalized FundsXML equivalence check — proves import file == export file.

Usage:  xml_equiv.py <a.xml> <b.xml>
Exit:   0 = equivalent, 1 = differ (first difference printed), 2 = usage

WHY this tool exists
--------------------
The database round-trip examples must demonstrate that exporting the rows the
import wrote yields *the same* FundsXML document. A byte comparison is wrong:
two equivalent FundsXML files legitimately differ in ways that carry no
information. This comparator treats two documents as equal when they differ
ONLY by:

  * ControlData/DocumentGenerated  — a generation timestamp; volatile by
    design, so its text is ignored (the element must still be present).
  * Numeric formatting             — 9375000 == 9375000.00 == 9.375E6;
    elements/attributes whose values are numbers compare as numbers.
  * Insignificant whitespace       — pretty-print indentation / text padding.
  * Attribute order & xmlns form   — attributes compare as a map; namespace
    declarations are not data.

Everything else is significant. FundsXML content models are xs:sequence, so
**child order is compared** (a reordered document is NOT considered equal) —
this is deliberately strict so the round-trip really proves fidelity.

Shared by the Python/Java/C#/JavaScript examples (via CI) so every language is
held to the identical definition of "round-trips correctly".

NOTE: namespace declarations are treated as non-data, so this check ALONE
would accept an xsi:* attribute that lost its namespace. Always pair it with
XSD validation (xmllint --schema ...) — the examples and CI always do.
"""
import sys

from lxml import etree

# Fully-qualified path (tag chain from the root) whose text is volatile.
IGNORE_TEXT_PATHS = {"FundsXML4/ControlData/DocumentGenerated"}


def _norm_num(s):
    """Return a canonical form: a float if the string is numeric, else the
    whitespace-stripped string. Lets 100 == 100.00 == 1E2 compare equal."""
    s = (s or "").strip()
    try:
        return ("num", float(s))
    except (TypeError, ValueError):
        return ("str", s)


def _children(el):
    # Element children only (drop comments/PIs); whitespace handled via text.
    return [c for c in el if isinstance(c.tag, str)]


def diff(a, b, path=""):
    """Return None if equal, else a human-readable description of the first
    difference (depth-first, document order)."""
    here = f"{path}/{etree.QName(a).localname}" if path else etree.QName(a).localname

    if etree.QName(a).localname != etree.QName(b).localname:
        return f"{path or '/'}: tag {etree.QName(a).localname} != {etree.QName(b).localname}"

    # Attributes as numeric-aware maps (local names; xmlns not data).
    aa = {etree.QName(k).localname: _norm_num(v) for k, v in a.attrib.items()}
    ba = {etree.QName(k).localname: _norm_num(v) for k, v in b.attrib.items()}
    if aa != ba:
        return f"{here}: attributes {aa} != {ba}"

    ac, bc = _children(a), _children(b)
    if not ac and not bc:
        # Leaf: compare text unless this path is whitelisted as volatile.
        if here in IGNORE_TEXT_PATHS:
            return None
        if _norm_num(a.text) != _norm_num(b.text):
            return (f"{here}: text {(a.text or '').strip()!r} != "
                    f"{(b.text or '').strip()!r}")
        return None

    if len(ac) != len(bc):
        return (f"{here}: child count {len(ac)} != {len(bc)} "
                f"(a=[{','.join(etree.QName(c).localname for c in ac)}] "
                f"b=[{','.join(etree.QName(c).localname for c in bc)}])")
    for ca, cb in zip(ac, bc):
        d = diff(ca, cb, here)
        if d:
            return d
    return None


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: xml_equiv.py <a.xml> <b.xml>", file=sys.stderr)
        return 2
    p = etree.XMLParser(remove_blank_text=True, resolve_entities=False,
                         no_network=True)
    a = etree.parse(sys.argv[1], p).getroot()
    b = etree.parse(sys.argv[2], p).getroot()
    d = diff(a, b)
    if d is None:
        print(f"EQUIVALENT: {sys.argv[1]} == {sys.argv[2]} "
              f"(ignoring timestamp & numeric/whitespace formatting)")
        return 0
    print(f"DIFFER: {d}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
