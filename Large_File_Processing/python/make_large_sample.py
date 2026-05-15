#!/usr/bin/env python3
"""Generate a large but XSD-valid FundsXML positions file by STREAMING writes.

Usage:  make_large_sample.py <out.xml> [n_positions=50000]

Builds the document with plain incremental writes (no in-memory DOM), so it
scales to very large files at constant memory — the write-side counterpart to
the streaming readers in this directory. Output validates against the official
4.2.9 schema (Fund + Portfolio/Positions, each an Equity with Units).
"""
import sys

SCHEMA = ("https://github.com/fundsxml/schema/releases/download/"
          "4.2.9/FundsXML.xsd")


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: make_large_sample.py <out.xml> [n]", file=sys.stderr)
        return 2
    out = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 50000

    # Integer cents keep the value sum exact; percentages are derived so they
    # sum to exactly 100 (last position absorbs the rounding remainder).
    unit_value = 1000  # EUR per position
    total = n * unit_value
    base_pct = round(100.0 / n, 6)

    with open(out, "w", encoding="utf-8") as f:
        w = f.write
        w('<?xml version="1.0" encoding="UTF-8"?>\n')
        w('<FundsXML4 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n')
        w(f'           xsi:noNamespaceSchemaLocation="{SCHEMA}">\n')
        w('  <ControlData>\n')
        w(f'    <UniqueDocumentID>FUNDSXML_LARGE_{n}</UniqueDocumentID>\n')
        w('    <DocumentGenerated>2025-10-02T00:00:00</DocumentGenerated>\n')
        w('    <Version>4.2.9</Version>\n')
        w('    <ContentDate>2025-10-01</ContentDate>\n')
        w('    <DataSupplier><SystemCountry>AT</SystemCountry>'
          '<Short>EURAM</Short><Name>Erste Asset Management GmbH</Name>'
          '<Type>Asset Manager</Type></DataSupplier>\n')
        w('    <DataOperation>INITIAL</DataOperation>\n')
        w('  </ControlData>\n')
        w('  <Funds><Fund>\n')
        w('    <Identifiers><LEI>529900T8BM49AURSDO55</LEI></Identifiers>\n')
        w('    <Names><OfficialName>Erste Large Synthetic Fund</OfficialName></Names>\n')
        w('    <Currency>EUR</Currency>\n')
        w('    <SingleFundFlag>true</SingleFundFlag>\n')
        w('    <FundDynamicData>\n')
        w('      <TotalAssetValues><TotalAssetValue>\n')
        w('        <NavDate>2025-10-01</NavDate>\n')
        w('        <TotalAssetNature>OFFICIAL</TotalAssetNature>\n')
        w(f'        <TotalNetAssetValue><Amount ccy="EUR">{total}.00</Amount>'
          '</TotalNetAssetValue>\n')
        w('      </TotalAssetValue></TotalAssetValues>\n')
        w('      <Portfolios><Portfolio>\n')
        w('        <NavDate>2025-10-01</NavDate>\n')
        w('        <Positions>\n')
        acc = 0.0
        for i in range(1, n + 1):
            if i < n:
                pct = base_pct
                acc += pct
            else:
                pct = round(100.0 - acc, 6)   # remainder on the last one
            w(f'<Position><UniqueID>ID_{i:08d}</UniqueID>'
              f'<Currency>EUR</Currency>'
              f'<TotalValue><Amount ccy="EUR">{unit_value}.00</Amount></TotalValue>'
              f'<TotalPercentage>{pct:.6f}</TotalPercentage>'
              f'<Equity><Units>{unit_value}.00</Units></Equity></Position>\n')
        w('        </Positions>\n')
        w('      </Portfolio></Portfolios>\n')
        w('    </FundDynamicData>\n')
        w('  </Fund></Funds>\n')
        w('</FundsXML4>\n')

    print(f"wrote {out}: {n} positions, total NAV {total}.00 EUR")
    return 0


if __name__ == "__main__":
    sys.exit(main())
