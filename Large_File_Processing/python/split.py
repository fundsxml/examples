#!/usr/bin/env python3
"""Split a large FundsXML positions file into smaller XSD-valid chunks.

Usage:  split.py <fundsxml.xml> <out-dir> [positions_per_chunk=5000]

Streams positions with iterparse (constant memory) and writes each batch as a
standalone FundsXML 4.2.9 file: <out-dir>/chunk-0001.xml, ... Each chunk gets
its own Fund TotalNetAssetValue (= sum of that chunk's position values) and its
percentages renormalized to 100, so **every chunk validates on its own**.

Useful for parallel downstream processing or staying under message-size limits.
FundsXML 4.x has no XML namespace.
"""
import sys
from pathlib import Path

from lxml import etree

SCHEMA = ("https://github.com/fundsxml/schema/releases/download/"
          "4.2.9/FundsXML.xsd")
HEAD = """<?xml version="1.0" encoding="UTF-8"?>
<FundsXML4 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
           xsi:noNamespaceSchemaLocation="{schema}">
  <ControlData>
    <UniqueDocumentID>{docid}</UniqueDocumentID>
    <DocumentGenerated>2025-10-02T00:00:00</DocumentGenerated>
    <Version>4.2.9</Version>
    <ContentDate>2025-10-01</ContentDate>
    <DataSupplier><SystemCountry>AT</SystemCountry><Short>EURAM</Short>\
<Name>Erste Asset Management GmbH</Name><Type>Asset Manager</Type></DataSupplier>
    <DataOperation>INITIAL</DataOperation>
  </ControlData>
  <Funds><Fund>
    <Identifiers><LEI>529900T8BM49AURSDO55</LEI></Identifiers>
    <Names><OfficialName>Erste Large Synthetic Fund (chunk {idx})</OfficialName></Names>
    <Currency>EUR</Currency>
    <SingleFundFlag>true</SingleFundFlag>
    <FundDynamicData>
      <TotalAssetValues><TotalAssetValue>
        <NavDate>2025-10-01</NavDate>
        <TotalAssetNature>OFFICIAL</TotalAssetNature>
        <TotalNetAssetValue><Amount ccy="EUR">{total:.2f}</Amount></TotalNetAssetValue>
      </TotalAssetValue></TotalAssetValues>
      <Portfolios><Portfolio>
        <NavDate>2025-10-01</NavDate>
        <Positions>
"""
FOOT = """        </Positions>
      </Portfolio></Portfolios>
    </FundDynamicData>
  </Fund></Funds>
</FundsXML4>
"""


def _flush(out_dir, idx, rows):
    total = sum(v for _, v, _, _ in rows)
    acc = 0.0
    body = []
    for j, (uid, val, _, kindxml) in enumerate(rows):
        if j < len(rows) - 1:
            pct = round(val / total * 100, 6) if total else 0.0
            acc += pct
        else:
            pct = round(100.0 - acc, 6) if total else 0.0
        body.append(
            f"<Position><UniqueID>{uid}</UniqueID><Currency>EUR</Currency>"
            f'<TotalValue><Amount ccy="EUR">{val:.2f}</Amount></TotalValue>'
            f"<TotalPercentage>{pct:.6f}</TotalPercentage>{kindxml}</Position>")
    p = Path(out_dir) / f"chunk-{idx:04d}.xml"
    p.write_text(HEAD.format(schema=SCHEMA, docid=f"FUNDSXML_CHUNK_{idx:04d}",
                             idx=idx, total=total)
                 + "\n".join(body) + "\n" + FOOT, encoding="utf-8")
    return p


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: split.py <fundsxml.xml> <out-dir> [n_per_chunk]",
              file=sys.stderr)
        return 2
    src, out_dir = sys.argv[1], sys.argv[2]
    per = int(sys.argv[3]) if len(sys.argv) > 3 else 5000
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    idx, rows, written = 1, [], []
    ctx = etree.iterparse(src, events=("end",), tag="Position",
                          resolve_entities=False, no_network=True)
    for _, pos in ctx:
        uid = pos.findtext("UniqueID")
        amt = pos.find("./TotalValue/Amount")
        val = float(amt.text) if amt is not None and amt.text else 0.0
        # Preserve the position-class element verbatim (Equity/Bond/...).
        kindxml = ""
        for c in pos:
            if c.tag not in ("UniqueID", "Identifiers", "Currency",
                             "TotalValue", "TotalPercentage"):
                kindxml = etree.tostring(c, encoding="unicode").strip()
                break
        rows.append((uid, val, None, kindxml))
        if len(rows) >= per:
            written.append(_flush(out_dir, idx, rows))
            idx += 1
            rows = []
        pos.clear()
        while pos.getprevious() is not None:
            del pos.getparent()[0]
    if rows:
        written.append(_flush(out_dir, idx, rows))

    for w in written:
        print(f"wrote {w}")
    print(f"{len(written)} chunk(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
