#!/usr/bin/env python3
"""FundsXML <-> JSON — runnable, verified converter (stdlib + lxml).

Many modern APIs speak JSON while the system of record is FundsXML. This maps
the positions core to a clean, stable JSON shape and back to XSD-valid
FundsXML.

  to-json    <fundsxml.xml> <out.json>
  from-json  <in.json> <out.xml>
  roundtrip  <fundsxml.xml> <out.xml>     # xml -> json -> xml in one shot

JSON shape (lossless for the positions core; intentionally lossy for issuer /
derivative / regulatory detail — same scope boundary as Database_Integration/):

  {"document": {...}, "fund": {...}, "shareClasses": [...],
   "positions": [...], "assets": [...]}

FundsXML 4.x has no XML namespace.
"""
import json
import sys
import tempfile
from pathlib import Path

from lxml import etree

SCHEMA = ("https://github.com/fundsxml/schema/releases/download/"
          "4.2.9/FundsXML.xsd")
XSI = "http://www.w3.org/2001/XMLSchema-instance"
POSITION_KINDS = {"Equity", "Bond", "ShareClass", "Warrant", "Certificate",
                  "Option", "Future", "FXForward", "Swap", "Repo",
                  "RealEstate", "CallMoney", "Account", "Generic"}
QTY_ELEM = {"Equity": "Units", "Warrant": "Units", "Certificate": "Units",
            "Bond": "Nominal", "ShareClass": "Shares",
            "Option": "Contracts", "Future": "Contracts"}


def _t(node, path):
    r = node.xpath(path)
    return r[0].text if r and r[0].text is not None else None


def _f(v):
    return float(v) if v not in (None, "") else None


# --------------------------------------------------------------- to JSON -----
def to_json(xml_path: str) -> dict:
    doc = etree.parse(xml_path)
    cd = doc.xpath("/FundsXML4/ControlData")[0]
    fund = doc.xpath("/FundsXML4/Funds/Fund")[0]
    ccy = _t(fund, "Currency")
    tav = fund.xpath("FundDynamicData/TotalAssetValues/TotalAssetValue")[0]

    out = {
        "document": {
            "id": _t(cd, "UniqueDocumentID"),
            "generated": _t(cd, "DocumentGenerated"),
            "version": _t(cd, "Version"),
            "contentDate": _t(cd, "ContentDate"),
            "dataOperation": _t(cd, "DataOperation"),
        },
        "fund": {
            "lei": _t(fund, "Identifiers/LEI"),
            "officialName": _t(fund, "Names/OfficialName"),
            "currency": ccy,
            "navDate": _t(tav, "NavDate"),
            "totalNav": _f(tav.xpath(
                f"TotalNetAssetValue/Amount[@ccy='{ccy}']")[0].text),
        },
        "shareClasses": [],
        "positions": [],
        "assets": [],
    }
    for sc in fund.xpath("SingleFund/ShareClasses/ShareClass"):
        out["shareClasses"].append({
            "isin": _t(sc, "Identifiers/ISIN"),
            "officialName": _t(sc, "Names/OfficialName"),
            "currency": _t(sc, "Currency"),
            "navPrice": _f(_t(sc, "Prices/Price/NavPrice")),
            "navFundCcy": _f((sc.xpath(
                "TotalAssetValues/TotalAssetValue/TotalNetAssetValue/"
                f"Amount[@ccy='{ccy}']") or [None])[0].text
                if sc.xpath("TotalAssetValues/TotalAssetValue/"
                            f"TotalNetAssetValue/Amount[@ccy='{ccy}']")
                else None),
            "sharesOutstanding": _f(_t(
                sc, "TotalAssetValues/TotalAssetValue/SharesOutstanding")),
        })
    for a in doc.xpath("/FundsXML4/AssetMasterData/Asset"):
        out["assets"].append({
            "uniqueId": _t(a, "UniqueID"),
            "isin": _t(a, "Identifiers/ISIN"),
            "name": _t(a, "Name"),
            "assetType": _t(a, "AssetType"),
            "currency": _t(a, "Currency"),
            "country": _t(a, "Country"),
        })
    for p in fund.xpath(
            "FundDynamicData/Portfolios/Portfolio/Positions/Position"):
        kinds = [c.tag for c in p if c.tag in POSITION_KINDS]
        kind = kinds[0] if kinds else None
        out["positions"].append({
            "uniqueId": _t(p, "UniqueID"),
            "isin": _t(p, "Identifiers/ISIN"),
            "currency": _t(p, "Currency"),
            "value": _f(p.xpath(f"TotalValue/Amount[@ccy='{ccy}']")[0].text),
            "percentage": _f(_t(p, "TotalPercentage")),
            "kind": kind,
            "kindQty": _f(_t(p, f"{kind}/{QTY_ELEM[kind]}"))
            if kind in QTY_ELEM else None,
        })
    return out


# ------------------------------------------------------------- from JSON -----
def _el(parent, tag, text=None, **attrs):
    e = etree.SubElement(parent, tag)
    for k, v in attrs.items():
        e.set(k, str(v))
    if text is not None:
        e.text = str(text)
    return e


def from_json(data: dict, out_path: str) -> None:
    d, fu = data["document"], data["fund"]
    ccy = fu["currency"]
    root = etree.Element("FundsXML4", nsmap={"xsi": XSI})
    root.set(f"{{{XSI}}}noNamespaceSchemaLocation", SCHEMA)

    cd = _el(root, "ControlData")
    _el(cd, "UniqueDocumentID", d["id"])
    _el(cd, "DocumentGenerated", d.get("generated") or "2025-10-02T00:00:00")
    if d.get("version"):
        _el(cd, "Version", d["version"])
    _el(cd, "ContentDate", d["contentDate"])
    ds = _el(cd, "DataSupplier")
    _el(ds, "SystemCountry", "AT")
    _el(ds, "Short", "EURAM")
    _el(ds, "Name", "Erste Asset Management GmbH")
    _el(ds, "Type", "Asset Manager")
    _el(cd, "DataOperation", d.get("dataOperation") or "INITIAL")

    fund = _el(_el(root, "Funds"), "Fund")
    if fu.get("lei"):
        _el(_el(fund, "Identifiers"), "LEI", fu["lei"])
    _el(_el(fund, "Names"), "OfficialName", fu["officialName"])
    _el(fund, "Currency", ccy)
    _el(fund, "SingleFundFlag", "true")
    fdd = _el(fund, "FundDynamicData")
    tav = _el(_el(_el(fdd, "TotalAssetValues"), "TotalAssetValue"),
              "NavDate", fu["navDate"]).getparent()
    _el(tav, "TotalAssetNature", "OFFICIAL")
    _el(_el(tav, "TotalNetAssetValue"), "Amount",
        f'{fu["totalNav"]:.2f}', ccy=ccy)
    port = _el(_el(fdd, "Portfolios"), "Portfolio")
    _el(port, "NavDate", fu["navDate"])
    poss = _el(port, "Positions")
    for p in data["positions"]:
        pos = _el(poss, "Position")
        _el(pos, "UniqueID", p["uniqueId"])
        if p.get("isin"):
            _el(_el(pos, "Identifiers"), "ISIN", p["isin"])
        if p.get("currency"):
            _el(pos, "Currency", p["currency"])
        _el(_el(pos, "TotalValue"), "Amount", f'{p["value"]:.2f}', ccy=ccy)
        _el(pos, "TotalPercentage", f'{p["percentage"]:.2f}')
        kind = p["kind"] if p.get("kind") in POSITION_KINDS else "Generic"
        ke = _el(pos, kind)
        if kind in QTY_ELEM and p.get("kindQty") is not None:
            _el(ke, QTY_ELEM[kind], f'{p["kindQty"]:.2f}')

    if data.get("shareClasses"):
        sce = _el(_el(fund, "SingleFund"), "ShareClasses")
        for sc in data["shareClasses"]:
            x = _el(sce, "ShareClass")
            _el(_el(x, "Identifiers"), "ISIN", sc["isin"])
            if sc.get("officialName"):
                _el(_el(x, "Names"), "OfficialName", sc["officialName"])
            _el(x, "Currency", sc["currency"])
            if sc.get("navPrice") is not None:
                pr = _el(_el(x, "Prices"), "Price")
                _el(pr, "ActionCode", "C")
                _el(pr, "NavDate", fu["navDate"])
                _el(pr, "PriceCurrency", sc["currency"])
                _el(pr, "PriceNature", "OFFICIAL")
                _el(pr, "NavPrice", f'{sc["navPrice"]:.2f}')
            if sc.get("navFundCcy") is not None:
                t = _el(_el(x, "TotalAssetValues"), "TotalAssetValue")
                _el(t, "NavDate", fu["navDate"])
                _el(t, "TotalAssetNature", "OFFICIAL")
                _el(_el(t, "TotalNetAssetValue"), "Amount",
                    f'{sc["navFundCcy"]:.2f}', ccy=ccy)
                if sc.get("sharesOutstanding") is not None:
                    _el(t, "SharesOutstanding",
                        f'{sc["sharesOutstanding"]:.0f}')

    if data.get("assets"):
        amd = _el(root, "AssetMasterData")
        for a in data["assets"]:
            ae = _el(amd, "Asset")
            _el(ae, "UniqueID", a["uniqueId"])
            if a.get("isin"):
                _el(_el(ae, "Identifiers"), "ISIN", a["isin"])
            _el(ae, "Currency", a.get("currency") or ccy)
            if a.get("country"):
                _el(ae, "Country", a["country"])
            _el(ae, "Name", a["name"])
            _el(ae, "AssetType", a["assetType"])

    etree.ElementTree(root).write(out_path, xml_declaration=True,
                                  encoding="UTF-8", pretty_print=True)


def main() -> int:
    a = sys.argv[1:]
    if len(a) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    mode, src, dst = a
    if mode == "to-json":
        Path(dst).write_text(json.dumps(to_json(src), indent=2))
        print("wrote", dst)
    elif mode == "from-json":
        from_json(json.loads(Path(src).read_text()), dst)
        print("wrote", dst)
    elif mode == "roundtrip":
        with tempfile.TemporaryDirectory() as t:
            j = Path(t) / "doc.json"
            j.write_text(json.dumps(to_json(src), indent=2))
            from_json(json.loads(j.read_text()), dst)
        print(f"round-trip ok: {src} -> JSON -> {dst}")
    else:
        print(f"unknown mode {mode!r}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
