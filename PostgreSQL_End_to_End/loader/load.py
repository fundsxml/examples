#!/usr/bin/env python3
"""Load FundsXML 4.2.x files into PostgreSQL.

An example, not a product: it shows the steps a production loader needs in as little code as
possible. Per file, in one transaction:

    check -> validate -> register -> stream -> link -> codes -> reconcile -> status

    python loader/load.py [--xsd FundsXML.xsd] [--landing] [--release-by NAME] FILE_OR_DIR...

--landing   treat each directory as a landing folder: files move to done/ or error/, and a
            rejected file gets a report next to it (error/<file>.report.txt)
--release-by  release every delivery that passes all checks, in the name of NAME
"""
import argparse
import base64
import copy
import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

import psycopg
from lxml import etree

HERE = Path(__file__).resolve().parent
DSN = os.environ.get("DATABASE_URL", "postgresql://fundsxml:fundsxml@localhost:5432/fundsxml")
VALIDATOR = HERE.parent / "tools" / "xsd11" / "validate.sh"
SENDERS = json.loads((HERE / "senders.json").read_text(encoding="utf-8"))
log = logging.getLogger("load")

# The one child of <Position> that says what it is (a choice in the schema) ...
POSITION_TYPES = {"Equity", "Bond", "ShareClass", "Warrant", "Certificate", "Option", "Future",
                  "FXForward", "Swap", "Repo", "FixedTimeDeposit", "CallMoney", "Account", "Fee",
                  "RealEstate", "REIT", "Loan", "Right", "Commodity", "PrivateEquity", "CommercialPaper"}
# ... and where it keeps the quantity: <Equity><Units>, <Bond><Nominal>, <Future><Contracts>, ...
QUANTITY_TAGS = ("Units", "Nominal", "Shares", "Contracts")
# Identifier elements we keep, and the scheme we store them under.
ID_SCHEMES = {"ISIN": "ISIN", "GermanWKN": "WKN", "SEDOL": "SEDOL", "CUSIP": "CUSIP",
              "OtherID[@FreeType='SUPPLIER']": "SUPPLIER"}   # our key for assets without ISIN, see export
# Containers dropped from memory as soon as their end tag is read (path endings, see FileLoader.key).
DROP = ("/Portfolios/Portfolio", "/Portfolio/BreakDowns", "/Portfolio/RiskCodes", "DynamicData/Benchmarks",
        "FUND/Subfunds/Subfund", "FundsXML4/Funds/Fund", "FundsXML4/Funds", "FundsXML4/AssetMasterData")


class Rejected(Exception):
    """The file must not be loaded. rule and detail go into the report for the sender."""

    def __init__(self, rule, detail):
        super().__init__(f"{rule}: {detail}")
        self.rule, self.detail = rule, detail


# ------------------------------------------------------------------ check / validate

def check(path):
    """The cheap checks first: complete? an expected sender? a version we know?"""
    with open(path, "rb") as f:
        f.seek(max(0, path.stat().st_size - 64))
        if b"</FundsXML4>" not in f.read():
            raise Rejected("INCOMPLETE", "no closing </FundsXML4>: the file was cut off during transfer")
    try:
        ctl = read_control_data(path)
    except etree.XMLSyntaxError as e:
        raise Rejected("NOT_WELL_FORMED", str(e))
    if ctl["data_supplier"] not in SENDERS:
        raise Rejected("UNKNOWN_SENDER", f"data supplier {ctl['data_supplier']!r} is not in loader/senders.json")
    if not ctl["version"].startswith("4."):
        raise Rejected("UNSUPPORTED_VERSION", f"FundsXML version {ctl['version']!r}")
    return ctl


def read_control_data(path):
    """Read only ControlData, the first lines of the file, not the whole file."""
    for _, elem in etree.iterparse(str(path), events=("end",), tag="ControlData"):
        return {
            "unique_document_id": elem.findtext("UniqueDocumentID"),
            "generated_at": elem.findtext("DocumentGenerated"),
            "content_date": elem.findtext("ContentDate"),
            "version": elem.findtext("Version") or "",
            "data_supplier": elem.findtext("DataSupplier/Short"),
            "data_operation": elem.findtext("DataOperation") or "INITIAL",
            "related_document_id": elem.findtext("RelatedDocumentIDs/RelatedDocumentID"),
        }
    raise Rejected("NO_CONTROL_DATA", "the file has no ControlData")


def validate(path, xsd):
    """XSD 1.1 validation runs as a separate (Java) process: lxml only implements XSD 1.0."""
    if not xsd:
        log.warning("validate   skipped: no --xsd given (FundsXML needs an XSD 1.1 validator)")
        return
    result = subprocess.run(["sh", str(VALIDATOR), xsd, str(path)], capture_output=True, text=True)
    if result.returncode != 0:
        errors = [f"line {line.split(' ', 1)[0].rsplit(':', 1)[1]}: {line.split(' ', 2)[2]}"
                  for line in result.stdout.splitlines() if " ERROR " in line or " FATAL " in line]
        raise Rejected("SCHEMA", "\n".join(errors) or result.stderr)
    log.info("validate   ok: valid against %s (XSD 1.1)", Path(xsd).name)


# ------------------------------------------------------------------ register

def register_delivery(cur, path, ctl):
    """Idempotency: a UniqueDocumentID we already have is skipped, never loaded twice."""
    cur.execute("SELECT status FROM delivery WHERE unique_document_id = %s", (ctl["unique_document_id"],))
    if row := cur.fetchone():
        return None, row[0]
    data = path.read_bytes()
    cur.execute(
        """INSERT INTO delivery (unique_document_id, data_supplier, content_date, generated_at, schema_version,
                                 data_operation, related_document_id, file_name, file_sha256, raw)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, XMLPARSE(DOCUMENT %s)) RETURNING delivery_id""",
        (ctl["unique_document_id"], ctl["data_supplier"], ctl["content_date"], ctl["generated_at"], ctl["version"],
         ctl["data_operation"], ctl["related_document_id"], path.name, hashlib.sha256(data).hexdigest(),
         data.decode("utf-8")))
    return cur.fetchone()[0], None


VERSIONED = ("price", "nav", "portfolio", "fund_static", "sc_flow", "distribution", "document", "regulatory_report")


def replace_related(cur, delivery_id, ctl):
    """AMEND and DELETE take back everything the related document delivered. History is kept."""
    cur.execute("SELECT delivery_id FROM delivery WHERE unique_document_id = %s", (ctl["related_document_id"],))
    related = cur.fetchone()
    if related is None:
        raise Rejected("UNKNOWN_RELATED", f"{ctl['data_operation']} refers to unknown document {ctl['related_document_id']}")
    replaced = {}
    for table in VERSIONED:
        cur.execute(f"UPDATE {table} SET replaced_by_delivery_id = %s "
                    "WHERE delivery_id = %s AND replaced_by_delivery_id IS NULL", (delivery_id, related[0]))
        if cur.rowcount:
            replaced[table] = cur.rowcount
    log.info("register   %s of %s: rows marked replaced %s", ctl["data_operation"], ctl["related_document_id"], replaced)


def supersede(cur, table, delivery_id, **key):
    """Latest delivery wins: a current row with the same key is marked replaced, not overwritten."""
    where = " AND ".join(f"{col} IS NOT DISTINCT FROM %s" for col in key)
    cur.execute(f"UPDATE {table} SET replaced_by_delivery_id = %s "
                f"WHERE {where} AND replaced_by_delivery_id IS NULL", (delivery_id, *key.values()))


def xml(elem):
    """An element as XML text, without the namespace declarations it only inherited from the root."""
    elem = copy.deepcopy(elem)
    etree.cleanup_namespaces(elem)
    return etree.tostring(elem, encoding="unicode")


# ------------------------------------------------------------------ stream

class FileLoader:
    """Writes the parts of one file to the database while lxml streams through it."""

    def __init__(self, cur, delivery_id, supplier):
        self.cur, self.delivery_id, self.supplier = cur, delivery_id, supplier
        self.funds = []                 # fund_id of the umbrella or single fund, then of the subfund
        self.portfolio_id = None
        self.position_no = {}
        self.staged, self.pending = [], []
        self.file_asset = {}            # FundsXML UniqueID (valid in this file only) -> our asset_id
        self.codes = []                 # (list, code, path) to check against code_list
        self.findings = []
        self.counts = dict.fromkeys(("funds", "share classes", "prices", "navs", "positions", "trades", "income",
                                     "flows", "distributions", "assets", "new assets", "documents", "templates"), 0)
        self.cur.execute("CREATE TEMP TABLE file_asset (file_unique_id text PRIMARY KEY, asset_id bigint) "
                         "ON COMMIT DROP")
        dyn = ("FUND/FundDynamicData", "SUB/SubfundDynamicData")
        pf = [d + "/Portfolios/Portfolio" for d in dyn]
        reg = "FundsXML4/RegulatoryReportings"
        self.handlers = {
            "FUND/SingleFundFlag": self.fund,          # Identifiers, Names, Currency are complete here
            "SUB/Currency": self.subfund,
            "FUND/FundStaticData": self.fund_static,
            "FUND/SingleFund/ShareClasses/ShareClass": self.share_class,
            "SUB/ShareClasses/ShareClass": self.share_class,
            "FundsXML4/AssetMasterData/Asset": self.asset,
            "FundsXML4/Documents/Document": self.document,
            f"{reg}/DirectReporting/EMT_V4_2/FinancialInstrument": self.emt,
            f"{reg}/DirectReporting/EET1.1.3/EET1.1.3": self.eet,
            f"{reg}/IndirectReporting/TripartiteTemplateSolvencyII_V7/Portfolio": self.tpt,
        }
        for d in dyn:
            self.handlers[d + "/TotalAssetValues/TotalAssetValue"] = self.fund_nav
        for p in pf:
            self.handlers[p + "/NavDate"] = self.portfolio
            self.handlers[p + "/Positions/Position"] = self.position
            self.handlers[p + "/PositionsDecomposed/Positions/Position"] = self.look_through
            self.handlers[p + "/Transactions/Transaction"] = self.trade
            self.handlers[p + "/Earnings/Earning"] = self.earning

    @staticmethod
    def key(stack):
        """Funds and subfunds have the same parts: one name for both levels."""
        path = "/".join(stack)
        if path.startswith("FundsXML4/Funds/Fund/Subfunds/Subfund/"):
            return "SUB/" + path[len("FundsXML4/Funds/Fund/Subfunds/Subfund/"):]
        if path.startswith("FundsXML4/Funds/Fund/"):
            return "FUND/" + path[len("FundsXML4/Funds/Fund/"):]
        return path

    def stream(self, path):
        """One pass, flat memory: handle an element at its end tag, then throw it away."""
        stack = []
        for event, elem in etree.iterparse(str(path), events=("start", "end")):
            if event == "start":
                stack.append(elem.tag)
                continue
            key = self.key(stack)
            handler = self.handlers.get(key)
            stack.pop()
            if handler:
                handler(elem)
            if handler or key.endswith(DROP):
                if key == "FUND/Subfunds/Subfund":
                    self.funds.pop()
                elem.clear()                        # free the subtree ...
                while elem.getprevious() is not None:
                    del elem.getparent()[0]         # ... and the siblings we are done with
        self.flush()

    # --- funds and share classes

    @property
    def fund_id(self):
        return self.funds[-1]

    def upsert_fund(self, f, parent_id, single):
        lei = f.findtext("Identifiers/LEI")
        self.cur.execute(
            """INSERT INTO fund (lei, name, currency, parent_fund_id, single_fund_flag) VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (lei) DO UPDATE SET name = EXCLUDED.name, currency = EXCLUDED.currency,
                   parent_fund_id = EXCLUDED.parent_fund_id,
                   single_fund_flag = coalesce(EXCLUDED.single_fund_flag, fund.single_fund_flag)
               RETURNING fund_id""",
            (lei, f.findtext("Names/OfficialName"), f.findtext("Currency"), parent_id, single))
        fund_id = self.cur.fetchone()[0]
        names = [(n.tag, "", n.text) for n in f.find("Names") if n.text and n.tag != "LanguageNames"]
        names += [("LanguageName", n.get("language"), n.text) for n in f.iterfind("Names/LanguageNames/Name")]
        self.cur.executemany("""INSERT INTO fund_name VALUES (%s, %s, %s, %s)
                                ON CONFLICT (fund_id, kind, language) DO UPDATE SET name = EXCLUDED.name""",
                             [(fund_id, *n) for n in names])
        self.cur.executemany("""INSERT INTO fund_identifier VALUES (%s, %s, %s)
                                ON CONFLICT (fund_id, scheme) DO UPDATE SET value = EXCLUDED.value""",
                             [(fund_id, i.tag, i.text) for i in f.find("Identifiers") if i.text and i.text.strip()])
        self.counts["funds"] += 1
        return fund_id

    def fund(self, flag):
        self.funds = [self.upsert_fund(flag.getparent(), None, flag.text == "true")]

    def subfund(self, ccy):
        self.funds.append(self.upsert_fund(ccy.getparent(), self.funds[0], None))

    def fund_static(self, s):
        supersede(self.cur, "fund_static", self.delivery_id, fund_id=self.fund_id)
        self.cur.execute(
            """INSERT INTO fund_static (fund_id, domicile_country, legal_structure, inception_date, open_closed,
                                        sfdr_product_type, ongoing_charges_pct, details, delivery_id)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s::xml, %s)""",
            (self.fund_id, s.findtext("DomicileCountry"), s.findtext("ListedLegalStructure"),
             s.findtext("InceptionDate"), s.findtext("OpenClosedEnded"), s.findtext("SFDRProductType"),
             s.findtext("OngoingCosts/OngoingCost[CostType='Ongoing Charges']/Percentage"), xml(s), self.delivery_id))

    def fund_nav(self, tav):
        self.nav(tav, share_class_id=None)

    def nav(self, tav, share_class_id):
        """One row per currency: a share class in another currency reports its net assets twice."""
        nature = tav.findtext("TotalAssetNature")
        self.codes.append(("TotalAssetNature", nature, "TotalAssetValue/TotalAssetNature"))
        for amount in tav.iterfind("TotalNetAssetValue/Amount"):
            key = dict(fund_id=self.fund_id, share_class_id=share_class_id, nav_date=tav.findtext("NavDate"),
                       nature=nature, currency=amount.get("ccy"))
            supersede(self.cur, "nav", self.delivery_id, **key)
            self.cur.execute(
                """INSERT INTO nav (fund_id, share_class_id, nav_date, nature, currency, amount, is_fund_ccy,
                                    is_share_class_ccy, shares_outstanding, delivery_id)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (*key.values(), amount.text, amount.get("isFundCcy") == "true",
                 amount.get("isShareClassCcy") == "true", tav.findtext("SharesOutstanding"), self.delivery_id))
            self.counts["navs"] += 1

    def share_class(self, sc):
        hedged = sc.findtext("CurrencyHedgedFlag")
        self.cur.execute(
            """INSERT INTO share_class (fund_id, isin, name, currency, type_code, earning_use, hedged)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (isin) DO UPDATE SET fund_id = EXCLUDED.fund_id, name = EXCLUDED.name,
                   type_code = coalesce(EXCLUDED.type_code, share_class.type_code),
                   earning_use = coalesce(EXCLUDED.earning_use, share_class.earning_use),
                   hedged = coalesce(EXCLUDED.hedged, share_class.hedged)
               RETURNING share_class_id""",
            (self.fund_id, sc.findtext("Identifiers/ISIN"), sc.findtext("Names/OfficialName"), sc.findtext("Currency"),
             sc.findtext("ShareClassType/Code"), sc.findtext("ShareClassType/EarningUse"),
             None if hedged is None else hedged == "true"))
        sc_id = self.cur.fetchone()[0]
        for p in sc.iterfind("Prices/Price"):
            key = dict(share_class_id=sc_id, nav_date=p.findtext("NavDate"), nature=p.findtext("PriceNature"))
            self.codes.append(("PriceNature", key["nature"], "Price/PriceNature"))
            supersede(self.cur, "price", self.delivery_id, **key)
            self.cur.execute(
                """INSERT INTO price (share_class_id, nav_date, nature, nav_price, subscription_price,
                                      redemption_price, currency, delivery_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (*key.values(), p.findtext("NavPrice"), p.findtext("SubscriptionPrice"), p.findtext("RedemptionPrice"),
                 p.findtext("PriceCurrency"), self.delivery_id))
            self.counts["prices"] += 1
        for tav in sc.iterfind("TotalAssetValues/TotalAssetValue"):
            self.nav(tav, sc_id)
        for d in sc.iterfind("Distributions/Distribution"):
            supersede(self.cur, "distribution", self.delivery_id, share_class_id=sc_id, ex_date=d.findtext("ExDate"))
            self.cur.execute(
                """INSERT INTO distribution (share_class_id, ex_date, status, record_date, payment_date, gross_per_share,
                                             net_per_share, currency, delivery_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (sc_id, d.findtext("ExDate"), d.findtext("DividendStatus"), d.findtext("RecordDate"), d.findtext("PaymentDate"),
                 d.findtext("GrossDividendAmount/PerShare/Amount"), d.findtext("NetDividendAmount/PerShare/Amount"),
                 d.findtext("PaymentCurrency"), self.delivery_id))
            self.counts["distributions"] += 1
        for fl in sc.iterfind("Flows/Flow"):
            self.codes.append(("FlowType", fl.findtext("TransactionType"), "Flow/TransactionType"))
            supersede(self.cur, "sc_flow", self.delivery_id, share_class_id=sc_id, transaction_id=fl.findtext("TransactionID"))
            amount = fl.find("TotalValue/Amount")
            self.cur.execute(
                """INSERT INTO sc_flow (share_class_id, transaction_id, trade_date, accounting_date, settlement_date,
                                        flow_type, units, value, currency, delivery_id)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (sc_id, fl.findtext("TransactionID"), fl.findtext("TradeDate"), fl.findtext("AccountingDate"),
                 fl.findtext("SettlementDate"),
                 fl.findtext("TransactionType"), fl.findtext("Units"), amount.text, amount.get("ccy"), self.delivery_id))
            self.counts["flows"] += 1
        self.counts["share classes"] += 1

    # --- portfolios: positions, look-through, trades and income

    def portfolio(self, nav_date):
        supersede(self.cur, "portfolio", self.delivery_id, fund_id=self.fund_id, nav_date=nav_date.text)
        self.cur.execute("INSERT INTO portfolio (fund_id, nav_date, delivery_id) VALUES (%s, %s, %s) "
                         "RETURNING portfolio_id", (self.fund_id, nav_date.text, self.delivery_id))
        self.portfolio_id = self.cur.fetchone()[0]

    def position(self, pos, look_through=False):
        """Positions come before AssetMasterData in the file: stage them, link them at the end."""
        amount = pos.find("TotalValue/Amount")
        detail = next(child for child in pos if child.tag in POSITION_TYPES)
        quantity = next((detail.findtext(t) for t in QUANTITY_TAGS if detail.find(t) is not None), None)
        no = self.position_no[(self.portfolio_id, look_through)] = self.position_no.get((self.portfolio_id, look_through), 0) + 1
        self.staged.append((self.delivery_id, self.portfolio_id, no, look_through, pos.findtext("UniqueID"),
                            detail.tag, amount.text, amount.get("ccy"), pos.findtext("TotalPercentage"), quantity, xml(pos)))
        if len(self.staged) >= 1000:
            self.flush()

    def look_through(self, pos):
        self.position(pos, look_through=True)

    def flush(self):
        self.cur.executemany(
            """INSERT INTO position_staging (delivery_id, portfolio_id, position_no, look_through, file_unique_id,
                                             position_type, total_value, currency, percentage, quantity, details)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""", self.staged)
        self.counts["positions"] += len(self.staged)
        self.staged.clear()

    def trade(self, t):
        """Trades and income name their asset by UniqueID too; few rows, so they wait in memory."""
        self.codes.append(("TransactionKind", t.findtext("TransactionKind"), "Transaction/TransactionKind"))
        settle = t.find("SettlementAmount/Amount")
        self.pending.append(("trade", t.findtext("AssetUniqueID"), (
            self.portfolio_id, t.findtext("TransactionID"), t.findtext("TransactionKind"), t.findtext("EntryDate"),
            t.findtext("ValutaDate"), t.findtext("NominalOrUnitsOrContracts"),
            None if settle is None else settle.text, None if settle is None else settle.get("ccy"),
            t.findtext("Counterparty/Identifiers/LEI"), t.findtext("PostingText"), xml(t))))
        self.counts["trades"] += 1

    def earning(self, e):
        self.codes.append(("EarningKind", e.findtext("EarningKind"), "Earning/EarningKind"))
        value = e.find("EntryValue/Amount")
        self.pending.append(("earning", e.findtext("AssetUniqueID"), (
            self.portfolio_id, e.findtext("EarningID"), e.findtext("EarningKind"), e.findtext("EntryDate"),
            e.findtext("ValutaDate"), value.text, value.get("ccy"), e.findtext("PostingText"), xml(e))))
        self.counts["income"] += 1

    # --- assets

    def asset(self, a):
        asset_id, new = resolve_asset(self.cur, a, self.supplier)
        self.file_asset[a.findtext("UniqueID")] = asset_id
        self.cur.execute("INSERT INTO file_asset VALUES (%s, %s)", (a.findtext("UniqueID"), asset_id))
        self.counts["assets"] += 1
        self.counts["new assets"] += new

    # --- documents

    def document(self, d):
        doc_type = d.findtext("Type/ListedType") or d.findtext("Type/UnlistedType")
        self.codes.append(("DocumentType", d.findtext("Type/ListedType"), "Document/Type/ListedType"))
        content = d.findtext("BinaryData")
        content = base64.b64decode("".join(content.split())) if content else None
        size = d.findtext("SizeInBytes")
        if content is not None and size and int(size) != len(content):
            self.findings.append(("warning", "DOCUMENT_SIZE", "Document/SizeInBytes", size,
                                  f"{d.findtext('FileName')}: SizeInBytes {size}, decoded {len(content)} bytes"))
        supersede(self.cur, "document", self.delivery_id, file_name=d.findtext("FileName"))
        self.cur.execute(
            """INSERT INTO document (doc_type, version, language, name, file_name, format, for_public_usage,
                                     creation_date, expiration_date, size_bytes, url, content, sha256, delivery_id)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING document_id""",
            (doc_type, d.findtext("Version"), d.findtext("Language"), d.findtext("Name"), d.findtext("FileName"),
             d.findtext("Format"), d.findtext("ForPublicUsage") == "true", d.findtext("CreationDate"),
             d.findtext("ExpirationDate"), size, d.findtext("DocumentURL"), content,
             hashlib.sha256(content).hexdigest() if content else None, self.delivery_id))
        document_id = self.cur.fetchone()[0]
        targets = [("fund", lei) for lei in d.xpath("Fund/Identifiers/LEI/text() | Subfunds/Subfund/Identifiers/LEI/text()")]
        targets += [("share_class", isin) for isin in d.xpath("ShareClasses/ShareClass/Identifiers/ISIN/text()")]
        for kind, value in targets:
            column, key = ("fund_id", "lei") if kind == "fund" else ("share_class_id", "isin")
            self.cur.execute(f"SELECT {column} FROM {kind} WHERE {key} = %s", (value,))
            row = self.cur.fetchone()
            if row is None:
                self.findings.append(("warning", "UNKNOWN_TARGET", f"Document/{kind}", value,
                                      f"{d.findtext('FileName')} belongs to a {kind.replace('_', ' ')} we do not know"))
                continue
            self.cur.execute(f"INSERT INTO document_target (document_id, {column}) VALUES (%s, %s)", (document_id, row[0]))
        self.counts["documents"] += 1

    # --- regulatory templates: the record as XML, plus key fields

    def template(self, record, template, version, isin, reference_date, **fields):
        supersede(self.cur, "regulatory_report", self.delivery_id, template=template, template_version=version, isin=isin)
        cols = ["template", "template_version", "isin", "share_class_id", "reference_date", *fields, "content", "delivery_id"]
        self.cur.execute(
            f"""INSERT INTO regulatory_report ({", ".join(cols)})
                VALUES (%s, %s, %s, (SELECT share_class_id FROM share_class WHERE isin = %s), %s,
                        {"%s, " * len(fields)}%s::xml, %s)""",
            (template, version, isin, isin, reference_date, *fields.values(), xml(record), self.delivery_id))
        self.counts["templates"] += 1

    def emt(self, r):
        self.template(r, "EMT", "V4.2", r.findtext("GeneralInformation/Code"),
                      r.findtext("CostsAndChargesExAnte/CostsReferenceDate"),
                      ongoing_costs=r.findtext("CostsAndChargesExAnte/Fund/OngoingCosts"))

    def eet(self, r):
        self.template(r, "EET", "V1.1.3", r.findtext("GeneralFinancialInstrumentInformation/IdentifyingData"),
                      r.findtext("DataSetInformation/ManufacturerInformation/GeneralReferenceDate"),
                      sfdr_product_type=r.findtext("MainCriterias/SFDRProductType"),
                      considers_pai=r.findtext("MainCriterias/ConsidersPrincipleAdverseImpact") == "Y")

    def tpt(self, r):
        self.template(r, "TPT", r.findtext("TPTVersion") or "V7", r.findtext("PortfolioID/Code"),
                      r.findtext("ValuationDate"), tpt_positions=len(r.findall("Positions/Position")))


def asset_keys(asset, supplier):
    """Identifiers first. Without any, the file's own UniqueID is all we have; it only means
    something together with who sent it, so the key becomes supplier/asset type/ID."""
    keys = [(scheme, asset.findtext(f"Identifiers/{tag}")) for tag, scheme in ID_SCHEMES.items()]
    keys = [(scheme, value) for scheme, value in keys if value]
    if not keys:
        keys.append(("SUPPLIER", f"{supplier}/{asset.findtext('AssetType')}/{asset.findtext('UniqueID')}"))
    return keys


def resolve_asset(cur, asset, supplier):
    """Find the asset by any of its identifiers, or create it. Returns (our asset_id, created?)."""
    keys = asset_keys(asset, supplier)
    cur.execute("SELECT asset_id FROM asset_identifier "
                "WHERE (scheme, value) IN (SELECT * FROM unnest(%s::text[], %s::text[]))",
                ([s for s, _ in keys], [v for _, v in keys]))
    details = asset.find("AssetDetails")
    details = xml(details) if details is not None else None
    if row := cur.fetchone():
        asset_id, new = row[0], False
        cur.execute("UPDATE asset SET name = %s, details = coalesce(%s::xml, details) WHERE asset_id = %s",
                    (asset.findtext("Name"), details, asset_id))   # the latest delivery's master data wins
    else:
        cur.execute("INSERT INTO asset (name, asset_type, currency, country, details) "
                    "VALUES (%s, %s, %s, %s, %s::xml) RETURNING asset_id",
                    (asset.findtext("Name"), asset.findtext("AssetType"),
                     asset.findtext("Currency"), asset.findtext("Country"), details))
        asset_id, new = cur.fetchone()[0], True
    cur.executemany("INSERT INTO asset_identifier VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                    [(asset_id, s, v) for s, v in keys])
    return asset_id, new


# ------------------------------------------------------------------ link / codes / reconcile

def link(cur, loader):
    """Turn staged positions into real ones by joining the file's IDs to our assets; then trades and income."""
    cur.execute("""INSERT INTO position (portfolio_id, position_no, look_through, asset_id, position_type,
                                         total_value, currency, percentage, quantity, details)
                   SELECT s.portfolio_id, s.position_no, s.look_through, fa.asset_id, s.position_type,
                          s.total_value, s.currency, s.percentage, s.quantity, s.details::xml
                   FROM position_staging s JOIN file_asset fa USING (file_unique_id)
                   WHERE s.delivery_id = %s""", (loader.delivery_id,))
    linked = cur.rowcount
    cur.execute("DELETE FROM position_staging WHERE delivery_id = %s", (loader.delivery_id,))
    if cur.rowcount != linked:
        raise Rejected("BROKEN_REFERENCE", f"{cur.rowcount - linked} positions reference no asset in AssetMasterData")
    for table, uid, row in loader.pending:
        asset_id = loader.file_asset.get(uid) if uid else None
        if uid and asset_id is None:
            raise Rejected("BROKEN_REFERENCE", f"{table} {row[1]} references {uid}, which is not in AssetMasterData")
        if table == "trade":
            cur.execute("""INSERT INTO trade (portfolio_id, transaction_id, kind, entry_date, valuta_date, quantity,
                                              settlement_amount, settlement_ccy, counterparty_lei, posting_text,
                                              details, asset_id)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::xml, %s)""", (*row, asset_id))
        else:
            cur.execute("""INSERT INTO earning (portfolio_id, earning_id, kind, entry_date, valuta_date, value,
                                                currency, posting_text, details, asset_id)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::xml, %s)""", (*row, asset_id))
    return linked


def check_codes(cur, loader, version):
    """Every listed code must be in the code list of the schema; unknown ones become findings."""
    seen = {(lst, code): path for lst, code, path in loader.codes if code}
    if not seen:
        return
    cur.execute("SELECT list, code, max(schema_version) FROM code_list "
                "WHERE (list, code) IN (SELECT * FROM unnest(%s::text[], %s::text[])) GROUP BY list, code",
                ([lst for lst, _ in seen], [c for _, c in seen]))
    known = {(lst, code): v for lst, code, v in cur.fetchall()}
    for (lst, code), path in seen.items():
        if (lst, code) not in known:
            loader.findings.append(("error", "UNKNOWN_CODE", path, code, f"{code!r} is not a {lst} code"))
        elif known[(lst, code)] > version:
            loader.findings.append(("warning", "NEWER_CODE", path, code, f"{code!r} is from FundsXML {known[(lst, code)]}"))
    log.info("codes      %d distinct codes checked against code_list", len(seen))


def reconcile(cur, loader):
    cur.execute("SELECT fund, nav_date, currency, sum_positions, total_net_assets, sum_weights, ok "
                "FROM portfolio_reconciliation WHERE delivery_id = %s ORDER BY fund", (loader.delivery_id,))
    for fund, nav_date, ccy, total, tna, weights, ok in cur.fetchall():
        log.log(logging.INFO if ok else logging.WARNING,
                "reconcile  %s %s: positions %s vs net assets %s %s, weights %s %% -> %s",
                fund, nav_date, total, tna, ccy, weights, "ok" if ok else "MISMATCH")
        if not ok:
            loader.findings.append(("error", "RECONCILIATION", f"{fund} {nav_date}", f"{total} / {weights} %",
                                    f"positions {total} vs net assets {tna} {ccy}, weights {weights} %"))


# ------------------------------------------------------------------ one file

def load_file(conn, path, xsd, release_by):
    """Returns 'loaded', 'skipped' or raises Rejected."""
    log.info("file       %s", path.name)
    ctl = check(path)
    log.info("check      %s, %s, content date %s, from %s",
             ctl["unique_document_id"], ctl["data_operation"], ctl["content_date"], ctl["data_supplier"])
    validate(path, xsd)
    with conn.transaction(), conn.cursor() as cur:   # one transaction per file: all or nothing
        delivery_id, status = register_delivery(cur, path, ctl)
        if delivery_id is None:
            log.info("register   skipped: %s already loaded (status %s)", ctl["unique_document_id"], status)
            return "skipped"
        log.info("register   delivery %d", delivery_id)
        if ctl["data_operation"] in ("AMEND", "DELETE"):
            replace_related(cur, delivery_id, ctl)
        loader = FileLoader(cur, delivery_id, ctl["data_supplier"])
        if ctl["data_operation"] != "DELETE":           # a DELETE brings no new data
            loader.stream(path)
            log.info("stream     %s", ", ".join(f"{n} {k}" for k, n in loader.counts.items() if n))
            linked = link(cur, loader)
            if linked:
                log.info("link       %d positions linked to assets", linked)
            check_codes(cur, loader, ctl["version"])
            reconcile(cur, loader)
        cur.executemany("INSERT INTO delivery_finding (delivery_id, severity, rule, path, value, message) "
                        "VALUES (%s, %s, %s, %s, %s, %s)", [(delivery_id, *f) for f in loader.findings])
        for severity, rule, _, _, message in loader.findings:
            log.warning("finding    %s %s: %s", severity, rule, message)
        ok = not any(f[0] == "error" for f in loader.findings)
        cur.execute("UPDATE delivery SET status = %s WHERE delivery_id = %s", ("checked" if ok else "loaded", delivery_id))
        if ok and release_by:
            cur.execute("SELECT release_delivery(%s, %s)", (ctl["unique_document_id"], release_by))
        log.info("status     %s", "released" if ok and release_by else "checked" if ok else "loaded (held back)")
    return "loaded"


def report(path, error):
    """A report the sender can act on: file, document ID, rule, details, and what happened."""
    try:
        doc_id = read_control_data(path)["unique_document_id"]
    except Exception:   # noqa: BLE001  (a broken file may not even have readable ControlData)
        doc_id = "(not readable)"
    return (f"File:        {path.name}\nDocument ID: {doc_id}\nRule:        {error.rule}\n"
            f"Details:     {error.detail}\nOutcome:     rejected, nothing was loaded. "
            f"Please send a corrected file with a new UniqueDocumentID.\n")


def files(args):
    for arg in map(Path, args):
        yield from sorted(arg.glob("*.xml")) if arg.is_dir() else [arg]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+", help="FundsXML files or directories with *.xml")
    ap.add_argument("--xsd", default=os.environ.get("FUNDSXML_XSD"), help="schema for XSD 1.1 validation")
    ap.add_argument("--landing", action="store_true", help="move files to done/ or error/ next to them")
    ap.add_argument("--release-by", help="release deliveries that pass all checks, in this name")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S")
    summary = {"loaded": 0, "skipped": 0, "rejected": 0}
    with psycopg.connect(DSN, autocommit=True) as conn:
        for path in list(files(args.paths)):
            try:
                outcome = load_file(conn, path, args.xsd, args.release_by)
                target = "done"
            except Rejected as e:
                log.error("rejected   %s: %s", path.name, e.rule + ": " + e.detail.splitlines()[0])
                outcome, target = "rejected", "error"
                if args.landing:
                    (path.parent / "error").mkdir(exist_ok=True)
                    (path.parent / "error" / (path.name + ".report.txt")).write_text(report(path, e), encoding="utf-8")
            summary[outcome] += 1
            if args.landing:
                (path.parent / target).mkdir(exist_ok=True)
                shutil.move(str(path), str(path.parent / target / path.name))
    log.info("summary    %s", ", ".join(f"{n} {k}" for k, n in summary.items()))
    sys.exit(1 if summary["rejected"] else 0)


if __name__ == "__main__":
    main()
