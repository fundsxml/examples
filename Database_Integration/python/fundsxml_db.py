#!/usr/bin/env python3
# =============================================================================
# FundsXML <-> relational database — runnable reference (Python 3, SQLite).
#
# PURPOSE
#   A standalone, copy-me example showing BOTH directions:
#     * import : read a FundsXML file  -> rows in the relational schema
#     * export : read those rows       -> a FundsXML file
#   It is deliberately over-commented: read it top to bottom and you can
#   reimplement the same pattern in any language/RDBMS.
#
# DB SCHEMA
#   ../ddl/schema.sql  (document -> fund -> portfolio -> position; share_class
#   per fund; asset document-scoped). SQLite is used so the example runs with
#   zero setup; the SQL is plain enough to move to Postgres/Oracle/SQL Server.
#
# RUN
#   python3 fundsxml_db.py init      fx.db
#   python3 fundsxml_db.py import    fx.db  ../../FundsXML_Files/4.2.9/positions/Multi-Fund_Positions.xml
#   python3 fundsxml_db.py export    fx.db  FUNDSXML_MULTI_1  out.xml
#   python3 fundsxml_db.py roundtrip ../../FundsXML_Files/4.2.9/positions/Multi-Fund_Positions.xml out.xml
#
# DEPENDENCIES
#   Python stdlib `sqlite3` + `lxml` (already used elsewhere in this repo).
#
# FUNDSXML ASSUMPTIONS (important and non-obvious)
#   * FundsXML 4.x has NO XML namespace -> XPath uses bare element names.
#   * A document may contain MANY <Fund>, each MANY <Portfolio>, each MANY
#     <Position>. We iterate all of them (no [0] shortcuts) and remember their
#     order with 1-based *_seq columns so the export is byte-faithful.
#   * Positions link to AssetMasterData by a shared <UniqueID> (FundsXML's
#     own join key), so `asset` is document-scoped, not per-fund.
#   * The export is normalized to the 4.2.9 schema URL; round-trip equality is
#     checked with ../tools/xml_equiv.py, which ignores the volatile
#     ControlData/DocumentGenerated timestamp and numeric/whitespace
#     formatting (see that file for the exact rules).
#
# SECURITY
#   The XML parser disables network access and entity resolution (XXE / billion
#   laughs). FundsXML never needs DTDs or external entities.
# =============================================================================
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from lxml import etree

DDL = Path(__file__).resolve().parents[1] / "ddl" / "schema.sql"

# The official released schema for the version we normalize exports to. Set as
# xsi:noNamespaceSchemaLocation so any validator can find the XSD.
SCHEMA_URL = ("https://github.com/fundsxml/schema/releases/download/"
              "4.2.9/FundsXML.xsd")
XSI = "http://www.w3.org/2001/XMLSchema-instance"

# The "class of instrument" element a <Position> must carry (FundsXML models
# this as a choice). We store its name in position.kind and, for the kinds
# that require a quantity child, the numeric quantity in position.kind_qty.
# WHY: without this we could not regenerate a schema-valid Position (an empty
# <Equity/> is invalid — it needs <Units>). Kinds not in QTY_ELEM
# (FXForward/Swap/Repo/RealEstate/CallMoney/...) are valid as an empty element.
POSITION_KINDS = {"Equity", "Bond", "ShareClass", "Warrant", "Certificate",
                  "Option", "Future", "FXForward", "Swap", "Repo",
                  "RealEstate", "CallMoney", "Account", "Generic"}
QTY_ELEM = {"Equity": "Units", "Warrant": "Units", "Certificate": "Units",
            "Bond": "Nominal", "ShareClass": "Shares",
            "Option": "Contracts", "Future": "Contracts"}


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
def _text(node, path):
    """First matching element's text, or None. Bare names (no namespace)."""
    r = node.xpath(path)
    return r[0].text if r and r[0].text is not None else None


def _num(v):
    return float(v) if v not in (None, "") else None


def _el(parent, tag, text=None, **attrs):
    """Append a child element; the one XML-building primitive used throughout
    the exporter so the emitted structure stays consistent and reviewable."""
    e = etree.SubElement(parent, tag)
    for k, v in attrs.items():
        e.set(k, str(v))
    if text is not None:
        e.text = str(text)
    return e


def connect(db):
    con = sqlite3.connect(db)
    con.execute("PRAGMA foreign_keys = ON")  # enforce the FK graph
    con.row_factory = sqlite3.Row
    return con


# ---------------------------------------------------------------------------
# init : create the schema
# ---------------------------------------------------------------------------
def init(db):
    con = connect(db)
    con.executescript(DDL.read_text())
    con.commit()
    con.close()


# ---------------------------------------------------------------------------
# import : FundsXML  ->  relational rows
#
# We walk the document in its natural order and assign 1-based ordinals
# (fund_seq / portfolio_seq / position_seq). Those ordinals are what make the
# export deterministic and therefore comparable to the original file.
# ---------------------------------------------------------------------------
def do_import(db, xml_path):
    parser = etree.XMLParser(resolve_entities=False, no_network=True,
                             load_dtd=False, huge_tree=False)
    doc = etree.parse(xml_path, parser)
    cd = doc.xpath("/FundsXML4/ControlData")[0]
    document_id = _text(cd, "UniqueDocumentID")

    con = connect(db)

    # ControlData -> one `document` row (so it round-trips exactly instead of
    # being hard-coded by the exporter).
    con.execute(
        "INSERT INTO document VALUES (?,?,?,?,?,?,?,?,?)",
        (document_id, _text(cd, "DocumentGenerated"), _text(cd, "Version"),
         _text(cd, "ContentDate"), _text(cd, "DataOperation"),
         _text(cd, "DataSupplier/SystemCountry"),
         _text(cd, "DataSupplier/Short"),
         _text(cd, "DataSupplier/Name"),
         _text(cd, "DataSupplier/Type")))

    # Every <Fund> (not just the first).
    for fund_seq, fund in enumerate(doc.xpath("/FundsXML4/Funds/Fund"), start=1):
        ccy = _text(fund, "Currency")
        tav = fund.xpath("FundDynamicData/TotalAssetValues/TotalAssetValue")[0]
        con.execute(
            "INSERT INTO fund VALUES (?,?,?,?,?,?,?,?)",
            (document_id, fund_seq, _text(fund, "Identifiers/LEI"),
             _text(fund, "Names/OfficialName"), ccy,
             _text(fund, "SingleFundFlag"), _text(tav, "NavDate"),
             float(tav.xpath(
                 f"TotalNetAssetValue/Amount[@ccy='{ccy}']")[0].text)))

        # Share classes of THIS fund.
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

        # Every <Portfolio> of this fund, and every <Position> in it.
        for p_seq, port in enumerate(
                fund.xpath("FundDynamicData/Portfolios/Portfolio"), start=1):
            con.execute("INSERT INTO portfolio VALUES (?,?,?,?)",
                        (document_id, fund_seq, p_seq, _text(port, "NavDate")))
            for pos_seq, pos in enumerate(
                    port.xpath("Positions/Position"), start=1):
                # The Position's instrument-class child (Equity/Bond/...).
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
    return document_id


# ---------------------------------------------------------------------------
# export : relational rows  ->  FundsXML
#
# Emits a fixed, canonical structure in schema order. Constants that the model
# does not store (TotalAssetNature=OFFICIAL, Price ActionCode=C,
# PriceNature=OFFICIAL) are reproduced verbatim; the round-trip fixture uses
# the same constants, so xml_equiv.py sees the files as equal.
# ---------------------------------------------------------------------------
def export(db, document_id, out_path):
    con = connect(db)
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

    funds = con.execute(
        "SELECT * FROM fund WHERE document_id=? ORDER BY fund_seq",
        (document_id,)).fetchall()
    funds_el = _el(root, "Funds")
    for f in funds:
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

        # Share classes (authored in ISIN order in the fixture, so ORDER BY
        # isin makes export child-order match the original).
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


# ---------------------------------------------------------------------------
# cli
# ---------------------------------------------------------------------------
def main() -> int:
    a = sys.argv[1:]
    if not a:
        print(__doc__, file=sys.stderr)
        return 2
    cmd = a[0]
    if cmd == "init":
        init(a[1])
    elif cmd == "import":
        print("imported document_id:", do_import(a[1], a[2]))
    elif cmd == "export":
        export(a[1], a[2], a[3])
        print("wrote", a[3])
    elif cmd == "roundtrip":
        # import then export THROUGH the DB (the user's required test): the
        # data exported is exactly the data the import wrote.
        with tempfile.TemporaryDirectory() as t:
            db = str(Path(t) / "rt.db")
            init(db)
            doc_id = do_import(db, a[1])
            export(db, doc_id, a[2])
        print(f"round-trip ok: {a[1]} -> DB -> {a[2]} (doc {doc_id})")
    else:
        print(f"unknown command {cmd!r}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
