#!/usr/bin/env python3
# =============================================================================
# IMPORT  —  FundsXML file  ->  relational database  (Python 3, SQLite).
#
# Standalone, copy-me example of ONE direction only: reading a FundsXML file
# into the relational schema. The reverse (DB -> FundsXML) is a separate
# program, export_fundsxml.py. Over-commented so it doubles as documentation.
#
# DB SCHEMA  ../ddl/schema.sql  (document -> fund -> portfolio -> position;
#   share_class per fund; asset document-scoped). This program CREATES the
#   schema in a fresh SQLite DB and then loads the file.
#
# RUN
#   python3 import_fundsxml.py fx.db \
#     ../../FundsXML_Files/4.2.9/positions/Multi-Fund_Positions.xml
#   # then, separately:  python3 export_fundsxml.py fx.db <docId> out.xml
#
# DEPENDENCIES  Python stdlib `sqlite3` + `lxml`.
#
# FUNDSXML ASSUMPTIONS (non-obvious)
#   * FundsXML 4.x has NO XML namespace -> XPath uses bare element names.
#   * A document may hold MANY <Fund>, each MANY <Portfolio>, each MANY
#     <Position>. We iterate all of them and record 1-based *_seq ordinals so
#     a later export reproduces the document order exactly.
#   * Positions link to AssetMasterData by a shared <UniqueID> -> `asset` is
#     document-scoped, not per-fund.
#
# SECURITY  the XML parser disables network access and entity resolution
#   (XXE / billion laughs). FundsXML needs no DTD/external entities.
# =============================================================================
import sqlite3
import sys
from pathlib import Path

from lxml import etree

DDL = Path(__file__).resolve().parents[1] / "ddl" / "schema.sql"

# The Position "class of instrument" element (FundsXML models this as a
# choice). We store its name and, for the kinds that require a quantity child,
# the numeric quantity, so the export can rebuild a schema-valid Position.
POSITION_KINDS = {"Equity", "Bond", "ShareClass", "Warrant", "Certificate",
                  "Option", "Future", "FXForward", "Swap", "Repo",
                  "RealEstate", "CallMoney", "Account", "Generic"}
QTY_ELEM = {"Equity": "Units", "Warrant": "Units", "Certificate": "Units",
            "Bond": "Nominal", "ShareClass": "Shares",
            "Option": "Contracts", "Future": "Contracts"}


def _text(node, path):
    """First matching element's text, or None (bare names; no namespace)."""
    r = node.xpath(path)
    return r[0].text if r and r[0].text is not None else None


def _num(v):
    return float(v) if v not in (None, "") else None


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: import_fundsxml.py <db> <fundsxml.xml>",
              file=sys.stderr)
        return 2
    db, xml_path = sys.argv[1], sys.argv[2]

    con = sqlite3.connect(db)
    con.execute("PRAGMA foreign_keys = ON")
    # Create the relational schema (this example targets a fresh DB).
    con.executescript(DDL.read_text())

    # Parse hardened: no network, no entity resolution, no huge-tree blowups.
    parser = etree.XMLParser(resolve_entities=False, no_network=True,
                             load_dtd=False, huge_tree=False)
    doc = etree.parse(xml_path, parser)

    cd = doc.xpath("/FundsXML4/ControlData")[0]
    document_id = _text(cd, "UniqueDocumentID")

    # ControlData -> one `document` row, so it round-trips exactly instead of
    # being hard-coded by the exporter.
    con.execute(
        "INSERT INTO document VALUES (?,?,?,?,?,?,?,?,?)",
        (document_id, _text(cd, "DocumentGenerated"), _text(cd, "Version"),
         _text(cd, "ContentDate"), _text(cd, "DataOperation"),
         _text(cd, "DataSupplier/SystemCountry"),
         _text(cd, "DataSupplier/Short"),
         _text(cd, "DataSupplier/Name"),
         _text(cd, "DataSupplier/Type")))

    # Every <Fund> (not just the first) gets a 1-based fund_seq.
    for fund_seq, fund in enumerate(doc.xpath("/FundsXML4/Funds/Fund"),
                                    start=1):
        ccy = _text(fund, "Currency")
        tav = fund.xpath("FundDynamicData/TotalAssetValues/TotalAssetValue")[0]
        con.execute(
            "INSERT INTO fund VALUES (?,?,?,?,?,?,?,?)",
            (document_id, fund_seq, _text(fund, "Identifiers/LEI"),
             _text(fund, "Names/OfficialName"), ccy,
             _text(fund, "SingleFundFlag"), _text(tav, "NavDate"),
             float(tav.xpath(
                 f"TotalNetAssetValue/Amount[@ccy='{ccy}']")[0].text)))

        for sc in fund.xpath("SingleFund/ShareClasses/ShareClass"):
            navf = sc.xpath("TotalAssetValues/TotalAssetValue/"
                            f"TotalNetAssetValue/Amount[@ccy='{ccy}']")
            con.execute(
                "INSERT INTO share_class VALUES (?,?,?,?,?,?,?,?)",
                (document_id, fund_seq, _text(sc, "Identifiers/ISIN"),
                 _text(sc, "Names/OfficialName"), _text(sc, "Currency"),
                 _num(_text(sc, "Prices/Price/NavPrice")),
                 _num(navf[0].text) if navf else None,
                 _num(_text(sc, "TotalAssetValues/TotalAssetValue/"
                                "SharesOutstanding"))))

        for p_seq, port in enumerate(
                fund.xpath("FundDynamicData/Portfolios/Portfolio"), start=1):
            con.execute("INSERT INTO portfolio VALUES (?,?,?,?)",
                        (document_id, fund_seq, p_seq,
                         _text(port, "NavDate")))
            for pos_seq, pos in enumerate(
                    port.xpath("Positions/Position"), start=1):
                kinds = [c.tag for c in pos if c.tag in POSITION_KINDS]
                kind = kinds[0] if kinds else None
                qty = (_num(_text(pos, f"{kind}/{QTY_ELEM[kind]}"))
                       if kind in QTY_ELEM else None)
                con.execute(
                    "INSERT INTO position VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (document_id, fund_seq, p_seq, pos_seq,
                     _text(pos, "UniqueID"), _text(pos, "Identifiers/ISIN"),
                     _text(pos, "Currency"),
                     float(pos.xpath(
                         f"TotalValue/Amount[@ccy='{ccy}']")[0].text),
                     float(_text(pos, "TotalPercentage")), kind, qty))

    # AssetMasterData is shared by all funds (document-scoped).
    for a in doc.xpath("/FundsXML4/AssetMasterData/Asset"):
        con.execute(
            "INSERT INTO asset VALUES (?,?,?,?,?,?,?)",
            (document_id, _text(a, "UniqueID"), _text(a, "Identifiers/ISIN"),
             _text(a, "Name"), _text(a, "AssetType"),
             _text(a, "Currency"), _text(a, "Country")))

    con.commit()
    con.close()
    print("imported document_id:", document_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
