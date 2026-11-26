#!/usr/bin/env python3
"""Generate FundsXML 4.2.9 files from the database, one per partner, as the partner register says.

An example, not a product. It reads only released, current data (never what a later delivery
replaced), writes the file as a stream with lxml.etree.xmlfile in strict schema order, and leaves
out what it does not have: no empty elements, no placeholders.

    python generator/export.py --partner DISTRIBUTOR-B --date 2025-11-05 --out out/
    python generator/export.py --all --date 2025-11-05 --out out/
    python generator/export.py --partner DATAVENDOR-C --date 2025-11-05 --amend EXAMPLE-AM-DATAVENDOR-C-2025-11-05

--date        the content date: NAVs and prices of the partner's last nav_days up to this day,
              the latest portfolio up to this day (with the transactions and income of its month)
--generated   the generation time to write (default: now); fixed in tests, so files can be compared
--amend DOC   a correction of the delivery DOC: DataOperation AMEND, the complete corrected data
"""
import argparse
import json
import os
from datetime import date, datetime
from pathlib import Path

import psycopg
from lxml import etree

HERE = Path(__file__).resolve().parent
DSN = os.environ.get("DATABASE_URL", "postgresql://fundsxml:fundsxml@localhost:5432/fundsxml")
PARTNERS = {k: v for k, v in json.loads((HERE / "partners.json").read_text(encoding="utf-8")).items()
            if not k.startswith("_")}
SUPPLIER = {"short": "EXAMPLE-AM", "name": "Example Asset Management GmbH", "country": "AT"}
SCHEMA = "https://github.com/fundsxml/schema/releases/download/4.2.9/FundsXML.xsd"
XSI = "http://www.w3.org/2001/XMLSchema-instance"
BLANK = etree.XMLParser(remove_blank_text=True)
# template -> (block, container, record element) in RegulatoryReportings
TEMPLATES = {"EMT": ("DirectReporting", "EMT_V4_2"), "EET": ("DirectReporting", "EET1.1.3"),
             "TPT": ("IndirectReporting", "TripartiteTemplateSolvencyII_V7")}


# ------------------------------------------------------------------ formats

def text(value):
    """Formats: decimal point, no thousands separators, ISO dates, true/false."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def el(tag, *content, **attrib):
    """An element, or None when it has no content: leave out what you do not have."""
    children = [c for c in content if isinstance(c, etree._Element)]
    values = [c for c in content if c is not None and not isinstance(c, etree._Element)]
    if not children and not values:
        return None
    e = etree.Element(tag, {k: text(v) for k, v in attrib.items() if v is not None})
    if values:
        e.text = text(values[0])
    e.extend(children)
    return e


def amounts(tag, rows):
    """<tag><Amount ccy="..">: one per currency; the flags say which is fund and share-class currency."""
    return el(tag, *[el("Amount", a, ccy=c, isShareClassCcy=True if sc else None, isFundCcy=True if fc else None)
                     for a, c, sc, fc in rows])


def stored(xml_text, **replace):
    """A block kept as XML in the database; replace={tag: new text} rewrites file-local references."""
    e = etree.fromstring(xml_text, BLANK)
    for tag, new in replace.items():
        for x in e.iter(tag):
            x.text = new(x.text)
    return e


def put(xf, element):
    if element is not None:
        xf.write(element)


# ------------------------------------------------------------------ queries

def rows(conn, sql, *params):
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def stream(conn, sql, *params):
    """Large results (positions) come from a server-side cursor, a few hundred rows at a time."""
    with conn.cursor(name="export_stream") as cur:
        cur.itersize = 500
        cur.execute(sql, params)
        yield from cur


RELEASED = "replaced_by_delivery_id IS NULL AND delivery_id IN (SELECT delivery_id FROM delivery WHERE status = 'released')"


def nav_dates(conn, fund_ids, until, days):
    """The last `days` NAV dates up to `until` of these funds."""
    found = rows(conn, f"""SELECT DISTINCT nav_date FROM nav WHERE fund_id = ANY(%s) AND nav_date <= %s AND {RELEASED}
                           ORDER BY nav_date DESC LIMIT %s""", fund_ids, until, days)
    return sorted(d for d, in found)


# ------------------------------------------------------------------ the file

class Export:
    def __init__(self, conn, partner, until, generated, amend_of=None, doc_id=None):
        self.conn, self.partner, self.cfg = conn, partner, PARTNERS[partner]
        self.until, self.generated, self.amend_of = until, generated, amend_of
        self.blocks = set(self.cfg["blocks"])
        base = f"{SUPPLIER['short']}-{partner}-{until.isoformat()}"
        self.doc_id = doc_id or (f"{amend_of}-AMEND-1" if amend_of else base)
        self.assets = set()          # our asset_ids referenced in this file -> AssetMasterData
        self.isins = []              # share classes in this file -> documents and templates
        self.lookups()

    def lookups(self):
        top = rows(self.conn, "SELECT fund_id FROM fund WHERE lei = ANY(%s) ORDER BY array_position(%s, lei)",
                   self.cfg["funds"], self.cfg["funds"])
        self.top = [f for f, in top]
        everything = rows(self.conn, "SELECT fund_id FROM fund WHERE fund_id = ANY(%s) OR parent_fund_id = ANY(%s)",
                          self.top, self.top)
        self.fund_ids = [f for f, in everything]
        self.dates = nav_dates(self.conn, self.fund_ids, self.until, self.cfg["nav_days"])

    def uid(self, asset_id):
        """Our key as the file's UniqueID: valid in this file only, like any UniqueID."""
        self.assets.add(asset_id)
        return f"A{asset_id}"

    # --- ControlData

    def control_data(self):
        return el("ControlData",
                  el("UniqueDocumentID", self.doc_id),        # new for every file, never reused
                  el("DocumentGenerated", self.generated),     # now ...
                  el("Version", "4.2.9"),
                  el("ContentDate", self.until),               # ... and the day the data is valid for
                  el("DataSupplier", el("SystemCountry", SUPPLIER["country"]), el("Short", SUPPLIER["short"]),
                     el("Name", SUPPLIER["name"]), el("Type", "Asset Manager")),
                  el("DataOperation", "AMEND" if self.amend_of else "INITIAL"),
                  el("RelatedDocumentIDs", el("RelatedDocumentID", self.amend_of)) if self.amend_of else None,
                  el("Language", "en"))

    # --- funds

    def names(self, fund_id):
        kinds = {k: [] for k in ("OfficialName", "ShortName", "LanguageName")}
        for kind, lang, name in rows(self.conn, "SELECT kind, language, name FROM fund_name WHERE fund_id = %s "
                                                "ORDER BY language", fund_id):
            kinds.setdefault(kind, []).append((lang, name))
        official = kinds["OfficialName"][0][1] if kinds["OfficialName"] else \
            rows(self.conn, "SELECT name FROM fund WHERE fund_id = %s", fund_id)[0][0]
        return el("Names", el("OfficialName", official),
                  el("ShortName", kinds["ShortName"][0][1]) if kinds["ShortName"] else None,
                  el("LanguageNames", *[el("Name", n, language=lang) for lang, n in kinds["LanguageName"]]))

    def write_fund(self, xf, fund_id):
        lei, ccy, single = rows(self.conn, "SELECT lei, currency, single_fund_flag FROM fund WHERE fund_id = %s", fund_id)[0]
        with xf.element("Fund"):
            put(xf, el("Identifiers", el("LEI", lei)))
            put(xf, self.names(fund_id))
            put(xf, el("Currency", ccy))
            put(xf, el("SingleFundFlag", single))
            if "static" in self.blocks:
                for details, in rows(self.conn, f"SELECT details FROM fund_static WHERE fund_id = %s AND {RELEASED}", fund_id):
                    put(xf, stored(details))
            self.write_dynamic(xf, "FundDynamicData", fund_id, ccy)
            if single:
                with xf.element("SingleFund"):
                    self.write_share_classes(xf, fund_id)
            else:
                with xf.element("Subfunds"):
                    for sub_id, sub_lei, sub_ccy in rows(self.conn, "SELECT fund_id, lei, currency FROM fund "
                                                                    "WHERE parent_fund_id = %s ORDER BY fund_id", fund_id):
                        with xf.element("Subfund"):
                            put(xf, el("Identifiers", el("LEI", sub_lei)))
                            put(xf, self.names(sub_id))
                            put(xf, el("Currency", sub_ccy))
                            self.write_dynamic(xf, "SubfundDynamicData", sub_id, sub_ccy)
                            self.write_share_classes(xf, sub_id)

    def total_asset_values(self, fund_id, share_class_id, dates):
        """TotalAssetValues: per date and nature one TotalAssetValue, with one Amount per currency."""
        found = rows(self.conn, f"""SELECT nav_date, nature, amount, currency, is_share_class_ccy, is_fund_ccy, shares_outstanding
                                   FROM nav WHERE fund_id = %s AND share_class_id IS NOT DISTINCT FROM %s
                                     AND nav_date = ANY(%s) AND {RELEASED}
                                   ORDER BY nav_date, nature, is_share_class_ccy DESC, currency""",
                     fund_id, share_class_id, dates)
        groups = {}
        for d, nature, amount, ccy, sc, fc, shares in found:
            groups.setdefault((d, nature), {"rows": [], "shares": shares})["rows"].append((amount, ccy, sc, fc))
        return el("TotalAssetValues", *[
            el("TotalAssetValue", el("NavDate", d), el("TotalAssetNature", nature), amounts("TotalNetAssetValue", g["rows"]),
               el("SharesOutstanding", g["shares"]))
            for (d, nature), g in groups.items()])

    def portfolio_date(self, fund_id):
        found = rows(self.conn, f"SELECT max(nav_date) FROM portfolio WHERE fund_id = %s AND nav_date <= %s AND {RELEASED}",
                     fund_id, self.until)
        return found[0][0]

    def write_dynamic(self, xf, tag, fund_id, ccy):
        pdate = self.portfolio_date(fund_id) if "portfolio" in self.blocks else None
        dates = sorted(set(self.dates) | ({pdate} if pdate else set()))
        tavs = self.total_asset_values(fund_id, None, dates) if "navs" in self.blocks else None
        if tavs is None and pdate is None:
            return
        with xf.element(tag):
            put(xf, tavs)
            if pdate:
                self.write_portfolio(xf, fund_id, pdate)

    def write_portfolio(self, xf, fund_id, pdate):
        (portfolio_id,), = rows(self.conn, f"SELECT portfolio_id FROM portfolio WHERE fund_id = %s AND nav_date = %s "
                                           f"AND {RELEASED}", fund_id, pdate)
        period = {"from": pdate.replace(day=1).isoformat(), "to": pdate.isoformat()}
        with xf.element("Portfolios"), xf.element("Portfolio"):
            put(xf, el("NavDate", pdate))
            self.write_positions(xf, portfolio_id, look_through=False)
            if "transactions" in self.blocks:
                found = rows(self.conn, "SELECT details, asset_id FROM trade WHERE portfolio_id = %s ORDER BY entry_date, "
                                        "transaction_id", portfolio_id)
                if found:
                    with xf.element("Transactions", period):
                        for details, asset_id in found:
                            put(xf, stored(details, AssetUniqueID=lambda _, a=asset_id: self.uid(a)))
            if "income" in self.blocks:
                found = rows(self.conn, "SELECT details, asset_id FROM earning WHERE portfolio_id = %s ORDER BY entry_date, "
                                        "earning_id", portfolio_id)
                if found:
                    with xf.element("Earnings", period):
                        for details, asset_id in found:
                            put(xf, stored(details, AssetUniqueID=lambda _, a=asset_id: self.uid(a)))
            if "look_through" in self.blocks and rows(self.conn, "SELECT 1 FROM position WHERE portfolio_id = %s "
                                                                 "AND look_through LIMIT 1", portfolio_id):
                with xf.element("PositionsDecomposed"):
                    put(xf, el("LookThroughLevels", 1))
                    self.write_positions(xf, portfolio_id, look_through=True)

    def write_positions(self, xf, portfolio_id, look_through):
        """The position as delivered, with our asset key as UniqueID and the values from the columns."""
        with xf.element("Positions"):
            for asset_id, details, value, ccy, pct in stream(
                    self.conn, "SELECT asset_id, details, total_value, currency, percentage FROM position "
                               "WHERE portfolio_id = %s AND look_through = %s ORDER BY position_no",
                    portfolio_id, look_through):
                pos = stored(details, UniqueID=lambda _, a=asset_id: self.uid(a))
                pos.find("TotalValue/Amount").text = text(value)
                if pct is not None and pos.find("TotalPercentage") is not None:
                    pos.find("TotalPercentage").text = text(pct)
                xf.write(pos)

    # --- share classes

    def write_share_classes(self, xf, fund_id):
        found = rows(self.conn, "SELECT share_class_id, isin, name, currency, hedged FROM share_class "
                                "WHERE fund_id = %s ORDER BY isin", fund_id)
        if not found:
            return
        with xf.element("ShareClasses"):
            for sc_id, isin, name, ccy, hedged in found:
                self.isins.append(isin)
                put(xf, el("ShareClass",
                           el("Identifiers", el("ISIN", isin)), el("Names", el("OfficialName", name)), el("Currency", ccy),
                           el("CurrencyHedgedFlag", hedged),
                           self.prices(sc_id) if "prices" in self.blocks else None,
                           self.total_asset_values(fund_id, sc_id, self.dates) if "navs" in self.blocks else None,
                           self.distributions(sc_id) if "distributions" in self.blocks else None,
                           self.flows(sc_id, fund_id) if "flows" in self.blocks else None))

    def prices(self, sc_id):
        found = rows(self.conn, f"""SELECT nav_date, currency, nature, nav_price, subscription_price, redemption_price
                                   FROM price WHERE share_class_id = %s AND nav_date = ANY(%s) AND {RELEASED}
                                   ORDER BY nav_date, nature""", sc_id, self.dates)
        return el("Prices", *[el("Price", el("ActionCode", "C"), el("NavDate", d), el("PriceCurrency", c),
                                 el("PriceNature", n), el("NavPrice", v), el("SubscriptionPrice", s),
                                 el("RedemptionPrice", r)) for d, c, n, v, s, r in found])

    def month(self, fund_id):
        pdate = self.portfolio_date(fund_id) or self.until
        return pdate.replace(day=1), pdate

    def distributions(self, sc_id):
        found = rows(self.conn, f"""SELECT status, record_date, ex_date, payment_date, currency, gross_per_share, net_per_share
                                   FROM distribution WHERE share_class_id = %s AND {RELEASED} ORDER BY ex_date""", sc_id)
        return el("Distributions", *[
            el("Distribution", el("ActionCode", "C"), el("DividendStatus", st), el("RecordDate", rd), el("ExDate", ex), el("PaymentDate", pay),
               el("PaymentCurrency", ccy), el("GrossDividendAmount", amounts("PerShare", [(g, ccy, False, False)])),
               el("NetDividendAmount", amounts("PerShare", [(n, ccy, False, False)]) if n is not None else None),
               el("DistributionFlag", True))
            for st, rd, ex, pay, ccy, g, n in found])

    def flows(self, sc_id, fund_id):
        start, end = self.month(fund_id)
        found = rows(self.conn, f"""SELECT transaction_id, trade_date, accounting_date, settlement_date, flow_type, units,
                                          value, currency
                                   FROM sc_flow WHERE share_class_id = %s AND trade_date BETWEEN %s AND %s AND {RELEASED}
                                   ORDER BY trade_date, transaction_id""", sc_id, start, end)
        if not found:
            return None
        return el("Flows", *[
            el("Flow", el("ActionCode", "C"), el("TransactionID", t), el("TradeDate", td), el("AccountingDate", ad),
               el("SettlementDate", sd), el("TransactionType", ft), el("Units", u), amounts("TotalValue", [(v, c, False, False)]))
            for t, td, ad, sd, ft, u, v, c in found], **{"from": start, "to": end})

    # --- after the funds: assets, documents, templates

    def asset_master_data(self):
        """Every asset the file refers to, once. Assets without an ISIN carry our key as OtherID, so
        that a correction finds the same asset again."""
        found = rows(self.conn, """SELECT a.asset_id, a.currency, a.country, a.name, a.asset_type, a.details,
                                          (SELECT value FROM asset_identifier WHERE asset_id = a.asset_id AND scheme = 'ISIN'),
                                          (SELECT value FROM asset_identifier WHERE asset_id = a.asset_id AND scheme = 'SUPPLIER')
                                   FROM asset a WHERE a.asset_id = ANY(%s) ORDER BY a.asset_id""", sorted(self.assets))
        return el("AssetMasterData", *[
            el("Asset", el("UniqueID", f"A{aid}"),
               el("Identifiers", el("ISIN", isin), el("OtherID", sup, FreeType="SUPPLIER") if not isin else None),
               el("Currency", ccy), el("Country", country), el("Name", name), el("AssetType", kind),
               stored(details) if details else None)
            for aid, ccy, country, name, kind, details, isin, sup in found])

    def documents(self):
        found = rows(self.conn, f"""SELECT DISTINCT d.document_id, d.doc_type, d.version, d.language, d.name, d.file_name,
                                          d.for_public_usage, d.format, d.creation_date, d.expiration_date, d.size_bytes,
                                          d.url, d.content
                                   FROM document d JOIN document_target t USING (document_id)
                                   LEFT JOIN share_class s ON s.share_class_id = t.share_class_id
                                   WHERE (t.fund_id = ANY(%s) OR s.isin = ANY(%s)) AND d.{RELEASED}
                                     AND (d.creation_date IS NULL OR d.creation_date <= %s)
                                     AND (d.expiration_date IS NULL OR d.expiration_date >= %s)
                                   ORDER BY d.document_id""",
                     self.fund_ids, self.isins, self.until, self.until)
        docs = []
        for doc_id, kind, version, lang, name, fname, public, fmt, created, expires, size, url, content in found:
            funds = rows(self.conn, "SELECT f.lei, f.name, f.currency FROM document_target t JOIN fund f USING (fund_id) "
                                    "WHERE t.document_id = %s ORDER BY f.lei", doc_id)
            classes = rows(self.conn, "SELECT s.isin, s.name, s.currency FROM document_target t JOIN share_class s "
                                      "USING (share_class_id) WHERE t.document_id = %s ORDER BY s.isin", doc_id)
            docs.append(el("Document", el("Type", el("ListedType", kind)), el("Version", version), el("Language", lang),
                           el("Fund", el("Identifiers", el("LEI", funds[0][0])), el("Name", funds[0][1]),
                              el("Currency", funds[0][2])) if funds else None,
                           el("ShareClasses", *[el("ShareClass", el("Identifiers", el("ISIN", i)), el("Name", n),
                                                   el("Currency", c)) for i, n, c in classes]),
                           el("Name", name), el("FileName", fname), el("ForPublicUsage", public), el("Format", fmt),
                           el("CreationDate", created), el("ExpirationDate", expires), el("SizeInBytes", size),
                           el("DocumentURL", url), el("BinaryData", base64_lines(content)) if content else None))
        return el("Documents", *docs)

    def regulatory(self):
        blocks = {}
        for template in self.cfg["templates"]:
            block, container = TEMPLATES[template]
            found = rows(self.conn, f"""SELECT content FROM regulatory_report WHERE template = %s AND isin = ANY(%s)
                                       AND {RELEASED} ORDER BY isin""", template, self.isins)
            if found:
                blocks.setdefault(block, []).append(el(container, *[stored(c) for c, in found]))
        return el("RegulatoryReportings", *[el(b, *blocks[b]) for b in ("DirectReporting", "IndirectReporting")
                                            if b in blocks])

    # --- the whole file

    def write(self, out):
        """Streamed: one fund at a time goes to the file, so memory stays flat."""
        with etree.xmlfile(str(out), encoding="UTF-8") as xf:
            xf.write_declaration()
            xf.write(etree.Comment(f" Synthetic sample: written by generator/export.py for {self.partner} "
                                   "from the example database. "))
            with xf.element("FundsXML4", {f"{{{XSI}}}noNamespaceSchemaLocation": SCHEMA}, nsmap={"xsi": XSI}):
                xf.write(self.control_data())
                with xf.element("Funds"):
                    for fund_id in self.top:
                        self.write_fund(xf, fund_id)
                if self.assets:
                    xf.write(self.asset_master_data())
                if "documents" in self.blocks:
                    put(xf, self.documents())
                put(xf, self.regulatory())
        pretty(out)


def base64_lines(data):
    import base64
    b64 = base64.b64encode(bytes(data)).decode("ascii")
    return "\n" + "\n".join(b64[i:i + 76] for i in range(0, len(b64), 76)) + "\n"


def pretty(path):
    """Indent for people who open the file; for very large files, skip this and keep the stream."""
    tree = etree.parse(str(path), BLANK)
    root = tree.getroot()
    etree.cleanup_namespaces(root)
    etree.indent(root, space="  ")
    comment = root.getprevious()
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        if comment is not None:
            f.write(etree.tostring(comment, encoding="unicode").strip() + "\n")
        f.write(etree.tostring(root, encoding="unicode") + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    who = ap.add_mutually_exclusive_group(required=True)
    who.add_argument("--partner", choices=sorted(PARTNERS))
    who.add_argument("--all", action="store_true", help="every partner in generator/partners.json")
    ap.add_argument("--date", required=True, type=date.fromisoformat)
    ap.add_argument("--generated", default=datetime.now().replace(microsecond=0).isoformat())
    ap.add_argument("--amend", metavar="DOC", help="UniqueDocumentID of the delivery this file corrects")
    ap.add_argument("--out", default="out", type=Path)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    with psycopg.connect(DSN) as conn:
        for partner in sorted(PARTNERS) if args.all else [args.partner]:
            export = Export(conn, partner, args.date, args.generated, args.amend)
            path = args.out / f"{export.doc_id}.xml"
            export.write(path)
            print(f"wrote {path} ({path.stat().st_size // 1024} KB, {len(export.assets)} assets)")


if __name__ == "__main__":
    main()
