#!/usr/bin/env python3
# =============================================================================
# EXPORT  —  relational database  ->  FundsXML file  (Python 3, SQLite).
#
# Standalone, copy-me example of ONE direction only: turning the relational
# rows back into a FundsXML document. The reverse (FundsXML -> DB) is a
# separate program, import_fundsxml.py. Over-commented as documentation.
#
# DB SCHEMA  ../ddl/schema.sql  (already populated by import_fundsxml.py).
#
# RUN
#   python3 import_fundsxml.py fx.db some.xml          # produces a doc id
#   python3 export_fundsxml.py fx.db FUNDSXML_MULTI_1 out.xml
#
# Prove the round-trip (import file vs exported file):
#   python3 ../tools/xml_equiv.py some.xml out.xml
#   XSD_Validation/cli/validate.sh <FundsXML.xsd path or release URL> out.xml
#
# DEPENDENCIES  Python stdlib `sqlite3` + `lxml`.
#
# FUNDSXML NOTES
#   * No XML namespace -> plain element names.
#   * Output is normalized to the 4.2.9 schema URL. Constants the model does
#     not store (TotalAssetNature=OFFICIAL, Price ActionCode=C / PriceNature=
#     OFFICIAL) are reproduced verbatim so the round-trip compares equal
#     (xml_equiv.py ignores the DocumentGenerated timestamp & number/whitespace
#     formatting; it is always paired with XSD validation).
#   * Rows are emitted ordered by the 1-based *_seq columns the import wrote,
#     so multiple funds/portfolios/positions come back in the original order.
# =============================================================================
import sqlite3
import sys
from datetime import datetime, timezone

from lxml import etree

SCHEMA_URL = ("https://github.com/fundsxml/schema/releases/download/"
              "4.2.9/FundsXML.xsd")
XSI = "http://www.w3.org/2001/XMLSchema-instance"
POSITION_KINDS = {"Equity", "Bond", "ShareClass", "Warrant", "Certificate",
                  "Option", "Future", "FXForward", "Swap", "Repo",
                  "RealEstate", "CallMoney", "Account", "Generic"}
QTY_ELEM = {"Equity": "Units", "Warrant": "Units", "Certificate": "Units",
            "Bond": "Nominal", "ShareClass": "Shares",
            "Option": "Contracts", "Future": "Contracts"}


def _el(parent, tag, text=None, **attrs):
    """Append a child element — the single XML-building primitive."""
    e = etree.SubElement(parent, tag)
    for k, v in attrs.items():
        e.set(k, str(v))
    if text is not None:
        e.text = str(text)
    return e


def main() -> int:
    if len(sys.argv) != 4:
        print("usage: export_fundsxml.py <db> <document_id> <out.xml>",
              file=sys.stderr)
        return 2
    db, document_id, out_path = sys.argv[1], sys.argv[2], sys.argv[3]

    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    d = con.execute("SELECT * FROM document WHERE document_id=?",
                     (document_id,)).fetchone()
    if d is None:
        raise SystemExit(f"no document {document_id!r} in {db}")

    root = etree.Element("FundsXML4", nsmap={"xsi": XSI})
    root.set(f"{{{XSI}}}noNamespaceSchemaLocation", SCHEMA_URL)

    cd = _el(root, "ControlData")
    _el(cd, "UniqueDocumentID", d["document_id"])
    # Regenerate the timestamp; xml_equiv.py ignores its value by design.
    _el(cd, "DocumentGenerated",
        d["generated"] or datetime.now(timezone.utc)
        .strftime("%Y-%m-%dT%H:%M:%S"))
    if d["version"]:                       # absent for FundsXML 4.0.0
        _el(cd, "Version", d["version"])
    _el(cd, "ContentDate", d["content_date"])
    ds = _el(cd, "DataSupplier")
    _el(ds, "SystemCountry", d["supplier_country"])
    _el(ds, "Short", d["supplier_short"])
    _el(ds, "Name", d["supplier_name"])
    _el(ds, "Type", d["supplier_type"])
    _el(cd, "DataOperation", d["data_operation"])

    funds_el = _el(root, "Funds")
    for f in con.execute(
            "SELECT * FROM fund WHERE document_id=? ORDER BY fund_seq",
            (document_id,)):
        ccy = f["currency"]
        fund = _el(funds_el, "Fund")
        if f["lei"]:
            _el(_el(fund, "Identifiers"), "LEI", f["lei"])
        _el(_el(fund, "Names"), "OfficialName", f["official_name"])
        _el(fund, "Currency", ccy)
        if f["single_fund_flag"]:
            _el(fund, "SingleFundFlag", f["single_fund_flag"])

        fdd = _el(fund, "FundDynamicData")
        tav = _el(_el(_el(fdd, "TotalAssetValues"), "TotalAssetValue"),
                  "NavDate", f["nav_date"]).getparent()
        _el(tav, "TotalAssetNature", "OFFICIAL")
        _el(_el(tav, "TotalNetAssetValue"), "Amount",
            f'{f["total_nav"]:.2f}', ccy=ccy)

        ports = _el(fdd, "Portfolios")
        for pf in con.execute(
                "SELECT * FROM portfolio WHERE document_id=? AND fund_seq=? "
                "ORDER BY portfolio_seq", (document_id, f["fund_seq"])):
            pe = _el(ports, "Portfolio")
            _el(pe, "NavDate", pf["nav_date"])
            poss = _el(pe, "Positions")
            for p in con.execute(
                    "SELECT * FROM position WHERE document_id=? AND fund_seq=? "
                    "AND portfolio_seq=? ORDER BY position_seq",
                    (document_id, f["fund_seq"], pf["portfolio_seq"])):
                pos = _el(poss, "Position")
                _el(pos, "UniqueID", p["unique_id"])
                if p["isin"]:
                    _el(_el(pos, "Identifiers"), "ISIN", p["isin"])
                if p["currency"]:
                    _el(pos, "Currency", p["currency"])
                _el(_el(pos, "TotalValue"), "Amount",
                    f'{p["value_fund_ccy"]:.2f}', ccy=ccy)
                _el(pos, "TotalPercentage", f'{p["percentage"]:.2f}')
                kind = p["kind"] if p["kind"] in POSITION_KINDS else "Generic"
                ke = _el(pos, kind)
                if kind in QTY_ELEM and p["kind_qty"] is not None:
                    _el(ke, QTY_ELEM[kind], f'{p["kind_qty"]:.2f}')

        scs = con.execute(
            "SELECT * FROM share_class WHERE document_id=? AND fund_seq=? "
            "ORDER BY isin", (document_id, f["fund_seq"])).fetchall()
        if scs:
            sce = _el(_el(fund, "SingleFund"), "ShareClasses")
            for sc in scs:
                x = _el(sce, "ShareClass")
                _el(_el(x, "Identifiers"), "ISIN", sc["isin"])
                if sc["official_name"]:
                    _el(_el(x, "Names"), "OfficialName", sc["official_name"])
                _el(x, "Currency", sc["currency"])
                if sc["nav_price"] is not None:
                    pr = _el(_el(x, "Prices"), "Price")
                    _el(pr, "ActionCode", "C")
                    _el(pr, "NavDate", f["nav_date"])
                    _el(pr, "PriceCurrency", sc["currency"])
                    _el(pr, "PriceNature", "OFFICIAL")
                    _el(pr, "NavPrice", f'{sc["nav_price"]:.2f}')
                if sc["nav_fund_ccy"] is not None:
                    t = _el(_el(x, "TotalAssetValues"), "TotalAssetValue")
                    _el(t, "NavDate", f["nav_date"])
                    _el(t, "TotalAssetNature", "OFFICIAL")
                    _el(_el(t, "TotalNetAssetValue"), "Amount",
                        f'{sc["nav_fund_ccy"]:.2f}', ccy=ccy)
                    if sc["shares_outstanding"] is not None:
                        _el(t, "SharesOutstanding",
                            f'{sc["shares_outstanding"]:.0f}')

    assets = con.execute(
        "SELECT * FROM asset WHERE document_id=? ORDER BY unique_id",
        (document_id,)).fetchall()
    if assets:
        amd = _el(root, "AssetMasterData")
        for a in assets:
            ae = _el(amd, "Asset")
            _el(ae, "UniqueID", a["unique_id"])
            if a["isin"]:
                _el(_el(ae, "Identifiers"), "ISIN", a["isin"])
            _el(ae, "Currency", a["currency"])
            if a["country"]:
                _el(ae, "Country", a["country"])
            _el(ae, "Name", a["name"])
            _el(ae, "AssetType", a["asset_type"])
    con.close()

    etree.ElementTree(root).write(out_path, xml_declaration=True,
                                  encoding="UTF-8", pretty_print=True)
    print("wrote", out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
