// =============================================================================
// EXPORT  —  relational database  ->  FundsXML file  (Node.js, SQLite).
//
// Standalone, copy-me example of ONE direction (DB -> FundsXML). The reverse
// is a separate program, import_fundsxml.mjs. Over-commented as documentation.
//
// DB SCHEMA  ../ddl/schema.sql  (already populated by import_fundsxml.mjs).
//
// RUN
//   node import_fundsxml.mjs fx.db some.xml
//   node export_fundsxml.mjs fx.db FUNDSXML_MULTI_1 out.xml
//   python3 ../tools/xml_equiv.py some.xml out.xml  # (needs lxml, see pyproject.toml) prove some.xml == out.xml
//
// DEPENDENCIES  sql.js (WASM SQLite) + @xmldom/xmldom (DOM serialization).
//
// FUNDSXML NOTES
//   * No XML namespace -> plain element names.
//   * Output normalized to the 4.2.9 schema URL; constants the model does not
//     store (TotalAssetNature=OFFICIAL, Price ActionCode=C / PriceNature=
//     OFFICIAL) reproduced verbatim so the round-trip compares equal
//     (../tools/xml_equiv.py, always paired with XSD validation).
//   * ORDER BY the 1-based *_seq columns reproduces the original order of
//     multiple funds / portfolios / positions.
// =============================================================================
import { readFileSync, writeFileSync } from "node:fs";
import initSqlJs from "sql.js";
import { DOMParser, XMLSerializer } from "@xmldom/xmldom";

const SCHEMA_URL =
  "https://github.com/fundsxml/schema/releases/download/4.2.9/FundsXML.xsd";
const POSITION_KINDS = new Set(["Equity", "Bond", "ShareClass", "Warrant",
  "Certificate", "Option", "Future", "FXForward", "Swap", "Repo",
  "RealEstate", "CallMoney", "Account", "Generic"]);
const QTY_ELEM = { Equity: "Units", Warrant: "Units", Certificate: "Units",
  Bond: "Nominal", ShareClass: "Shares", Option: "Contracts",
  Future: "Contracts" };
// Number formatting follows the DDL scale (schema.sql): amounts DECIMAL(20,2),
// TotalPercentage DECIMAL(9,4), quantities / NavPrice / SharesOutstanding
// DECIMAL(28,6). Render at that scale, then drop trailing zeros down to a floor
// of `minDec` decimals: 8.33 -> "8.33", 8.3333 -> "8.3333", 550000 shares ->
// "550000". A fixed toFixed(2) would silently truncate what the model stores
// (xml_equiv.py compares numerically and would flag the loss).
const num = (v, scale, minDec = 2) => {
  const [whole, frac = ""] = Number(v).toFixed(scale).split(".");
  const f = frac.replace(/0+$/, "").padEnd(minDec, "0");
  return f ? `${whole}.${f}` : whole;
};
const f2 = (v) => num(v, 2);           // amounts (scale 2)

function el(doc, parent, tag, text) {   // the one XML-build primitive
  const e = doc.createElement(tag);
  if (text != null) e.appendChild(doc.createTextNode(String(text)));
  parent.appendChild(e);
  return e;
}
function rows(db, sql, params) {
  const st = db.prepare(sql);
  st.bind(params);
  const out = [];
  while (st.step()) out.push(st.getAsObject());
  st.free();
  return out;
}

const [dbPath, docId, outPath] = process.argv.slice(2);
if (!dbPath || !docId || !outPath) {
  console.error("usage: export_fundsxml.mjs <db> <document_id> <out.xml>");
  process.exit(2);
}

const SQL = await initSqlJs();
const db = new SQL.Database(readFileSync(dbPath));

const d = rows(db, "SELECT * FROM document WHERE document_id=?", [docId])[0];
if (!d) throw new Error(`no document ${docId}`);

const doc = new DOMParser().parseFromString("<FundsXML4/>", "text/xml");
const root = doc.documentElement;
root.setAttribute("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance");
root.setAttribute("xsi:noNamespaceSchemaLocation", SCHEMA_URL);

const cd = el(doc, root, "ControlData");
el(doc, cd, "UniqueDocumentID", d.document_id);
// Regenerate the timestamp; xml_equiv.py ignores its value.
el(doc, cd, "DocumentGenerated", d.generated || "2025-10-02T00:00:00");
if (d.version != null) el(doc, cd, "Version", d.version); // none for 4.0.0
el(doc, cd, "ContentDate", d.content_date);
const ds = el(doc, cd, "DataSupplier");
el(doc, ds, "SystemCountry", d.supplier_country);
el(doc, ds, "Short", d.supplier_short);
el(doc, ds, "Name", d.supplier_name);
el(doc, ds, "Type", d.supplier_type);
el(doc, cd, "DataOperation", d.data_operation);

const fundsEl = el(doc, root, "Funds");
for (const f of rows(db,
    "SELECT * FROM fund WHERE document_id=? ORDER BY fund_seq", [docId])) {
  const ccy = f.currency;
  const fund = el(doc, fundsEl, "Fund");
  if (f.lei != null) el(doc, el(doc, fund, "Identifiers"), "LEI", f.lei);
  el(doc, el(doc, fund, "Names"), "OfficialName", f.official_name);
  el(doc, fund, "Currency", ccy);
  if (f.single_fund_flag != null)
    el(doc, fund, "SingleFundFlag", f.single_fund_flag);

  const fdd = el(doc, fund, "FundDynamicData");
  const tavp = el(doc, el(doc, fdd, "TotalAssetValues"), "TotalAssetValue");
  el(doc, tavp, "NavDate", f.nav_date);
  el(doc, tavp, "TotalAssetNature", "OFFICIAL");
  const amt = el(doc, el(doc, tavp, "TotalNetAssetValue"), "Amount",
    f2(f.total_nav));
  amt.setAttribute("ccy", ccy);

  const ports = el(doc, fdd, "Portfolios");
  for (const pf of rows(db,
      "SELECT * FROM portfolio WHERE document_id=? AND fund_seq=? "
      + "ORDER BY portfolio_seq", [docId, f.fund_seq])) {
    const pe = el(doc, ports, "Portfolio");
    el(doc, pe, "NavDate", pf.nav_date);
    const poss = el(doc, pe, "Positions");
    for (const p of rows(db,
        "SELECT * FROM position WHERE document_id=? AND fund_seq=? AND "
        + "portfolio_seq=? ORDER BY position_seq",
        [docId, f.fund_seq, pf.portfolio_seq])) {
      const pos = el(doc, poss, "Position");
      el(doc, pos, "UniqueID", p.unique_id);
      if (p.isin != null)
        el(doc, el(doc, pos, "Identifiers"), "ISIN", p.isin);
      if (p.currency != null) el(doc, pos, "Currency", p.currency);
      const tv = el(doc, el(doc, pos, "TotalValue"), "Amount",
        f2(p.value_fund_ccy));
      tv.setAttribute("ccy", ccy);
      el(doc, pos, "TotalPercentage", num(p.percentage, 4));
      const kind = POSITION_KINDS.has(p.kind) ? p.kind : "Generic";
      const ke = el(doc, pos, kind);
      if (QTY_ELEM[kind] && p.kind_qty != null)
        el(doc, ke, QTY_ELEM[kind], num(p.kind_qty, 6));
    }
  }

  const scs = rows(db, "SELECT * FROM share_class WHERE document_id=? AND "
    + "fund_seq=? ORDER BY isin", [docId, f.fund_seq]);
  if (scs.length) {
    const sce = el(doc, el(doc, fund, "SingleFund"), "ShareClasses");
    for (const sc of scs) {
      const x = el(doc, sce, "ShareClass");
      el(doc, el(doc, x, "Identifiers"), "ISIN", sc.isin);
      if (sc.official_name != null)
        el(doc, el(doc, x, "Names"), "OfficialName", sc.official_name);
      el(doc, x, "Currency", sc.currency);
      if (sc.nav_price != null) {
        const pr = el(doc, el(doc, x, "Prices"), "Price");
        el(doc, pr, "ActionCode", "C");
        el(doc, pr, "NavDate", f.nav_date);
        el(doc, pr, "PriceCurrency", sc.currency);
        el(doc, pr, "PriceNature", "OFFICIAL");
        el(doc, pr, "NavPrice", num(sc.nav_price, 6));
      }
      if (sc.nav_fund_ccy != null) {
        const t2 = el(doc, el(doc, x, "TotalAssetValues"),
          "TotalAssetValue");
        el(doc, t2, "NavDate", f.nav_date);
        el(doc, t2, "TotalAssetNature", "OFFICIAL");
        const a2 = el(doc, el(doc, t2, "TotalNetAssetValue"), "Amount",
          f2(sc.nav_fund_ccy));
        a2.setAttribute("ccy", ccy);
        if (sc.shares_outstanding != null)
          el(doc, t2, "SharesOutstanding",
            num(sc.shares_outstanding, 6, 0));
      }
    }
  }
}

const assets = rows(db,
  "SELECT * FROM asset WHERE document_id=? ORDER BY unique_id", [docId]);
if (assets.length) {
  const amd = el(doc, root, "AssetMasterData");
  for (const a of assets) {
    const ae = el(doc, amd, "Asset");
    el(doc, ae, "UniqueID", a.unique_id);
    if (a.isin != null) el(doc, el(doc, ae, "Identifiers"), "ISIN", a.isin);
    el(doc, ae, "Currency", a.currency);
    if (a.country != null) el(doc, ae, "Country", a.country);
    el(doc, ae, "Name", a.name);
    el(doc, ae, "AssetType", a.asset_type);
  }
}

writeFileSync(outPath, '<?xml version="1.0" encoding="UTF-8"?>\n'
  + new XMLSerializer().serializeToString(doc));
console.log("wrote", outPath);
