#!/usr/bin/env python3
"""FundsXML <-> relational database — runnable reference (SQLite, stdlib).

The Oracle / SQL Server / Postgres examples in ../load_from_fundsxml/ and
../generate_fundsxml/ are code-only (no DB is provisioned, per project scope).
This SQLite implementation is the *executable* reference: it needs nothing
beyond the Python stdlib + lxml, runs the full FundsXML -> DB -> FundsXML
round-trip, and the regenerated file is XSD-valid.

Subcommands:
  init     <db>                       create the schema (ddl/schema.sql)
  load     <db> <fundsxml.xml>        shred a FundsXML file into the tables
  generate <db> <document_id> <out>   rebuild XSD-valid FundsXML from the tables
  roundtrip <fundsxml.xml> <out>      load + generate via a temp DB (one shot)

Relational model: ../ddl/schema.sql. FundsXML 4.x has no XML namespace, so all
XPath uses bare element names.
"""
import sqlite3
import sys
import tempfile
from pathlib import Path

from lxml import etree

# Position class elements (the required child after TotalPercentage). Many are
# valid when empty (FXForward/Swap/Repo/RealEstate/CallMoney in the canonical
# sample); the rest accept an empty element for this round-trip demo.
POSITION_KINDS = {"Equity", "Bond", "ShareClass", "Warrant", "Certificate",
                  "Option", "Future", "FXForward", "Swap", "Repo",
                  "RealEstate", "CallMoney", "Account", "Generic"}
# Kinds that require a numeric quantity child -> the child element name.
# The remaining kinds (FXForward/Swap/Repo/RealEstate/CallMoney/...) are
# schema-valid as an empty element.
QTY_ELEM = {"Equity": "Units", "Warrant": "Units", "Certificate": "Units",
            "Bond": "Nominal", "ShareClass": "Shares",
            "Option": "Contracts", "Future": "Contracts"}

DDL = Path(__file__).resolve().parents[1] / "ddl" / "schema.sql"
SCHEMA_URL = ("https://github.com/fundsxml/schema/releases/download/"
              "4.2.9/FundsXML.xsd")
XSI = "http://www.w3.org/2001/XMLSchema-instance"


# ---------------------------------------------------------------- load -------
def _txt(node, path, default=None):
    r = node.xpath(path)
    return r[0].text if r and r[0].text is not None else default


def load(db: str, xml_path: str) -> str:
    doc = etree.parse(xml_path)
    cd = doc.xpath("/FundsXML4/ControlData")[0]
    fund = doc.xpath("/FundsXML4/Funds/Fund")[0]
    doc_id = _txt(cd, "UniqueDocumentID")
    ccy = _txt(fund, "Currency")
    tav = fund.xpath("FundDynamicData/TotalAssetValues/TotalAssetValue")[0]
    nav = tav.xpath(f"TotalNetAssetValue/Amount[@ccy='{ccy}']")[0].text

    con = sqlite3.connect(db)
    con.execute("PRAGMA foreign_keys=ON")
    con.execute(
        "INSERT INTO fund VALUES (?,?,?,?,?,?,?,?)",
        (doc_id, _txt(fund, "Identifiers/LEI"),
         _txt(fund, "Names/OfficialName"), ccy,
         _txt(cd, "ContentDate"), _txt(tav, "NavDate"),
         float(nav), _txt(cd, "Version")))

    for sc in fund.xpath("SingleFund/ShareClasses/ShareClass"):
        sccy = _txt(sc, "Currency")
        con.execute(
            "INSERT INTO share_class VALUES (?,?,?,?,?,?,?)",
            (doc_id, _txt(sc, "Identifiers/ISIN"),
             _txt(sc, "Names/OfficialName"), sccy,
             _num(_txt(sc, "Prices/Price/NavPrice")),
             _num(_first(sc, "TotalAssetValues/TotalAssetValue/"
                             f"TotalNetAssetValue/Amount[@ccy='{ccy}']")),
             _num(_txt(sc, "TotalAssetValues/TotalAssetValue/"
                           "SharesOutstanding"))))

    for a in doc.xpath("/FundsXML4/AssetMasterData/Asset"):
        con.execute(
            "INSERT INTO asset VALUES (?,?,?,?,?,?,?)",
            (doc_id, _txt(a, "UniqueID"), _txt(a, "Identifiers/ISIN"),
             _txt(a, "Name"), _txt(a, "AssetType"),
             _txt(a, "Currency"), _txt(a, "Country")))

    for p in fund.xpath("FundDynamicData/Portfolios/Portfolio/Positions/Position"):
        kinds = [c.tag for c in p if c.tag in POSITION_KINDS]
        kind = kinds[0] if kinds else None
        qty = None
        if kind in QTY_ELEM:
            qty = _num(_txt(p, f"{kind}/{QTY_ELEM[kind]}"))
        con.execute(
            "INSERT INTO position VALUES (?,?,?,?,?,?,?,?)",
            (doc_id, _txt(p, "UniqueID"), _txt(p, "Identifiers/ISIN"),
             _txt(p, "Currency"),
             float(p.xpath(f"TotalValue/Amount[@ccy='{ccy}']")[0].text),
             float(_txt(p, "TotalPercentage")),
             kind, qty))
    con.commit()
    con.close()
    return doc_id


def _first(node, path):
    r = node.xpath(path)
    return r[0].text if r else None


def _num(v):
    return float(v) if v not in (None, "") else None


# ------------------------------------------------------------ generate -------
def _el(parent, tag, text=None, **attrs):
    e = etree.SubElement(parent, tag)
    for k, v in attrs.items():
        e.set(k, str(v))
    if text is not None:
        e.text = str(text)
    return e


def generate(db: str, document_id: str, out: str) -> None:
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    f = con.execute("SELECT * FROM fund WHERE document_id=?",
                     (document_id,)).fetchone()
    if f is None:
        raise SystemExit(f"no fund with document_id {document_id!r}")
    ccy = f["currency"]

    root = etree.Element("FundsXML4", nsmap={"xsi": XSI})
    root.set(f"{{{XSI}}}noNamespaceSchemaLocation", SCHEMA_URL)

    cd = _el(root, "ControlData")
    _el(cd, "UniqueDocumentID", f["document_id"])
    _el(cd, "DocumentGenerated", "2025-10-02T00:00:00")
    if f["fxml_version"]:
        _el(cd, "Version", f["fxml_version"])
    _el(cd, "ContentDate", f["content_date"])
    ds = _el(cd, "DataSupplier")
    _el(ds, "SystemCountry", "AT")
    _el(ds, "Short", "EURAM")
    _el(ds, "Name", "Erste Asset Management GmbH")
    _el(ds, "Type", "Asset Manager")
    _el(cd, "DataOperation", "INITIAL")

    fund = _el(_el(root, "Funds"), "Fund")
    if f["lei"]:
        _el(_el(fund, "Identifiers"), "LEI", f["lei"])
    _el(_el(fund, "Names"), "OfficialName", f["official_name"])
    _el(fund, "Currency", ccy)
    _el(fund, "SingleFundFlag", "true")

    fdd = _el(fund, "FundDynamicData")
    tav = _el(_el(_el(fdd, "TotalAssetValues"), "TotalAssetValue"), "NavDate",
              f["nav_date"]).getparent()
    _el(tav, "TotalAssetNature", "OFFICIAL")
    _el(_el(tav, "TotalNetAssetValue"), "Amount",
        f'{f["total_nav"]:.2f}', ccy=ccy)

    port = _el(_el(fdd, "Portfolios"), "Portfolio")
    _el(port, "NavDate", f["nav_date"])
    poss = _el(port, "Positions")
    for p in con.execute(
            "SELECT * FROM position WHERE document_id=? ORDER BY unique_id",
            (document_id,)):
        pos = _el(poss, "Position")
        _el(pos, "UniqueID", p["unique_id"])
        if p["isin"]:
            _el(_el(pos, "Identifiers"), "ISIN", p["isin"])
        if p["currency"]:
            _el(pos, "Currency", p["currency"])
        _el(_el(pos, "TotalValue"), "Amount",
            f'{p["value_fund_ccy"]:.2f}', ccy=ccy)
        _el(pos, "TotalPercentage", f'{p["percentage"]:.2f}')
        # Required Position class element. Kinds with a mandatory quantity
        # child get it back (Units/Nominal/Shares/Contracts); the rest are
        # schema-valid empty.
        kind = p["kind"] if p["kind"] in POSITION_KINDS else "Generic"
        ke = _el(pos, kind)
        if kind in QTY_ELEM and p["kind_qty"] is not None:
            _el(ke, QTY_ELEM[kind], f'{p["kind_qty"]:.2f}')

    scs = con.execute("SELECT * FROM share_class WHERE document_id=? "
                       "ORDER BY isin", (document_id,)).fetchall()
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

    assets = con.execute("SELECT * FROM asset WHERE document_id=? "
                          "ORDER BY unique_id", (document_id,)).fetchall()
    if assets:
        amd = _el(root, "AssetMasterData")
        for a in assets:
            ae = _el(amd, "Asset")
            _el(ae, "UniqueID", a["unique_id"])
            if a["isin"]:
                _el(_el(ae, "Identifiers"), "ISIN", a["isin"])
            _el(ae, "Currency", a["currency"] or ccy)
            if a["country"]:
                _el(ae, "Country", a["country"])
            _el(ae, "Name", a["name"])
            _el(ae, "AssetType", a["asset_type"])
    con.close()

    etree.ElementTree(root).write(out, xml_declaration=True,
                                  encoding="UTF-8", pretty_print=True)


# ---------------------------------------------------------------- cli --------
def _init(db: str) -> None:
    con = sqlite3.connect(db)
    con.executescript(DDL.read_text())
    con.commit()
    con.close()


def main() -> int:
    a = sys.argv[1:]
    if not a:
        print(__doc__, file=sys.stderr)
        return 2
    if a[0] == "init":
        _init(a[1])
    elif a[0] == "load":
        print("loaded document_id:", load(a[1], a[2]))
    elif a[0] == "generate":
        generate(a[1], a[2], a[3])
        print("wrote", a[3])
    elif a[0] == "roundtrip":
        with tempfile.TemporaryDirectory() as t:
            db = str(Path(t) / "fundsxml.db")
            _init(db)
            doc_id = load(db, a[1])
            generate(db, doc_id, a[2])
        print(f"round-trip ok: {a[1]} -> DB -> {a[2]} (doc {doc_id})")
    else:
        print(f"unknown subcommand {a[0]!r}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
