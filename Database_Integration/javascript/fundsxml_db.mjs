// =============================================================================
// FundsXML <-> relational database — runnable reference (Node.js, SQLite).
//
// PURPOSE
//   Standalone, copy-me example of BOTH directions (import a FundsXML file into
//   the relational schema, export it back). Over-commented on purpose.
//
// DB SCHEMA  ../ddl/schema.sql  (document -> fund -> portfolio -> position;
//   share_class per fund; asset document-scoped).
//
// RUN
//   cd Database_Integration/javascript && npm install
//   node fundsxml_db.mjs roundtrip \
//     ../../FundsXML_Files/4.2.9/positions/Multi-Fund_Positions.xml out.xml
//   commands: init <db> | import <db> <xml> | export <db> <docId> <out> |
//             roundtrip <xml> <out>
//
// DEPENDENCIES (all pure-JS, no native build — runs on any Node >= 18):
//   sql.js          SQLite compiled to WebAssembly (the DB engine)
//   @xmldom/xmldom  a namespace-free DOM (FundsXML 4.x has no namespace)
//   xpath           XPath 1.0 over that DOM
//   Node 20 has no built-in node:sqlite (that arrived in 22.5), hence sql.js.
//
// FUNDSXML ASSUMPTIONS
//   * No XML namespace -> bare element names in XPath.
//   * Many <Fund>/<Portfolio>/<Position>: all iterated; 1-based *_seq columns
//     preserve order so the round-trip compares equal (../tools/xml_equiv.py).
//   * Positions link to AssetMasterData by shared <UniqueID> -> `asset` is
//     document-scoped.
//   * Export normalized to the 4.2.9 schema URL; constants the model does not
//     store (TotalAssetNature=OFFICIAL, Price ActionCode=C / PriceNature=
//     OFFICIAL) are reproduced verbatim.
//
// SECURITY
//   @xmldom/xmldom does not resolve external entities/DTDs (no XXE surface).
// =============================================================================
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import initSqlJs from "sql.js";
import { DOMParser, XMLSerializer } from "@xmldom/xmldom";
import xpath from "xpath";

const HERE = dirname(fileURLToPath(import.meta.url));
const DDL = resolve(HERE, "..", "ddl", "schema.sql");
const SCHEMA_URL =
  "https://github.com/fundsxml/schema/releases/download/4.2.9/FundsXML.xsd";

// Position instrument-class element + its mandatory quantity child. Kinds not
// in QTY_ELEM are schema-valid as an empty element.
const POSITION_KINDS = new Set(["Equity", "Bond", "ShareClass", "Warrant",
  "Certificate", "Option", "Future", "FXForward", "Swap", "Repo",
  "RealEstate", "CallMoney", "Account", "Generic"]);
const QTY_ELEM = { Equity: "Units", Warrant: "Units", Certificate: "Units",
  Bond: "Nominal", ShareClass: "Shares", Option: "Contracts",
  Future: "Contracts" };

// ---- tiny helpers ----------------------------------------------------------
const txt = (ctx, expr) => {           // first match's text or null
  const n = xpath.select1(expr, ctx);
  return n && n.textContent != null && n.textContent !== "" ? n.textContent : null;
};
const numOrNull = (s) => (s == null || s === "" ? null : Number(s));
const f2 = (v) => Number(v).toFixed(2);

function el(doc, parent, tag, text) {  // the one XML-build primitive
  const e = doc.createElement(tag);
  if (text != null) e.appendChild(doc.createTextNode(String(text)));
  parent.appendChild(e);
  return e;
}

function execScript(db, sql) {
  // Strip "--" line comments (no string literals in the DDL) then run.
  const clean = sql.split("\n").map((l) => {
    const i = l.indexOf("--");
    return i >= 0 ? l.slice(0, i) : l;
  }).join("\n");
  for (const stmt of clean.split(";")) if (stmt.trim()) db.run(stmt);
}

function parseSecure(xmlPath) {
  // @xmldom/xmldom never expands external entities; we additionally reject a
  // DOCTYPE so a malicious feed cannot even declare entities.
  const src = readFileSync(xmlPath, "utf8");
  if (/<!DOCTYPE/i.test(src)) throw new Error("DOCTYPE not allowed (XXE)");
  return new DOMParser().parseFromString(src, "text/xml");
}

// ---- persistence (sql.js is in-memory; a "db file" is its serialized image)
function persist(db, path) { writeFileSync(path, Buffer.from(db.export())); }
function load(SQL, path) { return new SQL.Database(readFileSync(path)); }

// ---- import : FundsXML -> rows --------------------------------------------
function doImport(db, xmlPath) {
  const doc = parseSecure(xmlPath);
  const cd = xpath.select1("/FundsXML4/ControlData", doc);
  const docId = txt(cd, "UniqueDocumentID");

  db.run("INSERT INTO document VALUES (?,?,?,?,?,?,?,?,?)", [
    docId, txt(cd, "DocumentGenerated"), txt(cd, "Version"),
    txt(cd, "ContentDate"), txt(cd, "DataOperation"),
    txt(cd, "DataSupplier/SystemCountry"), txt(cd, "DataSupplier/Short"),
    txt(cd, "DataSupplier/Name"), txt(cd, "DataSupplier/Type")]);

  const funds = xpath.select("/FundsXML4/Funds/Fund", doc);
  funds.forEach((fund, fi) => {
    const fundSeq = fi + 1;                    // 1-based document order
    const ccy = txt(fund, "Currency");
    const tav = xpath.select1(
      "FundDynamicData/TotalAssetValues/TotalAssetValue", fund);
    db.run("INSERT INTO fund VALUES (?,?,?,?,?,?,?,?)", [
      docId, fundSeq, txt(fund, "Identifiers/LEI"),
      txt(fund, "Names/OfficialName"), ccy, txt(fund, "SingleFundFlag"),
      txt(tav, "NavDate"),
      Number(txt(tav, `TotalNetAssetValue/Amount[@ccy='${ccy}']`))]);

    for (const sc of xpath.select("SingleFund/ShareClasses/ShareClass", fund)) {
      db.run("INSERT INTO share_class VALUES (?,?,?,?,?,?,?,?)", [
        docId, fundSeq, txt(sc, "Identifiers/ISIN"),
        txt(sc, "Names/OfficialName"), txt(sc, "Currency"),
        numOrNull(txt(sc, "Prices/Price/NavPrice")),
        numOrNull(txt(sc,
          `TotalAssetValues/TotalAssetValue/TotalNetAssetValue/Amount[@ccy='${ccy}']`)),
        numOrNull(txt(sc,
          "TotalAssetValues/TotalAssetValue/SharesOutstanding"))]);
    }

    xpath.select("FundDynamicData/Portfolios/Portfolio", fund)
      .forEach((port, pi) => {
        const portSeq = pi + 1;
        db.run("INSERT INTO portfolio VALUES (?,?,?,?)",
          [docId, fundSeq, portSeq, txt(port, "NavDate")]);
        xpath.select("Positions/Position", port).forEach((pos, qi) => {
          let kind = null;
          for (let ch = pos.firstChild; ch; ch = ch.nextSibling)
            if (ch.nodeType === 1 && POSITION_KINDS.has(ch.nodeName)) {
              kind = ch.nodeName; break;
            }
          const qty = kind && QTY_ELEM[kind]
            ? numOrNull(txt(pos, `${kind}/${QTY_ELEM[kind]}`)) : null;
          db.run("INSERT INTO position VALUES (?,?,?,?,?,?,?,?,?,?,?)", [
            docId, fundSeq, portSeq, qi + 1, txt(pos, "UniqueID"),
            txt(pos, "Identifiers/ISIN"), txt(pos, "Currency"),
            Number(txt(pos, `TotalValue/Amount[@ccy='${ccy}']`)),
            Number(txt(pos, "TotalPercentage")), kind, qty]);
        });
      });
  });

  for (const a of xpath.select("/FundsXML4/AssetMasterData/Asset", doc)) {
    db.run("INSERT INTO asset VALUES (?,?,?,?,?,?,?)", [
      docId, txt(a, "UniqueID"), txt(a, "Identifiers/ISIN"),
      txt(a, "Name"), txt(a, "AssetType"), txt(a, "Currency"),
      txt(a, "Country")]);
  }
  return docId;
}

// ---- export : rows -> FundsXML --------------------------------------------
function rows(db, sql, params) {
  const st = db.prepare(sql);
  st.bind(params);
  const out = [];
  while (st.step()) out.push(st.getAsObject());
  st.free();
  return out;
}

function exportXml(db, docId, outPath) {
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
        el(doc, pos, "TotalPercentage", f2(p.percentage));
        const kind = POSITION_KINDS.has(p.kind) ? p.kind : "Generic";
        const ke = el(doc, pos, kind);
        if (QTY_ELEM[kind] && p.kind_qty != null)
          el(doc, ke, QTY_ELEM[kind], f2(p.kind_qty));
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
          el(doc, pr, "NavPrice", f2(sc.nav_price));
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
              Number(sc.shares_outstanding).toFixed(0));
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
      if (a.isin != null)
        el(doc, el(doc, ae, "Identifiers"), "ISIN", a.isin);
      el(doc, ae, "Currency", a.currency);
      if (a.country != null) el(doc, ae, "Country", a.country);
      el(doc, ae, "Name", a.name);
      el(doc, ae, "AssetType", a.asset_type);
    }
  }

  const xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    + new XMLSerializer().serializeToString(doc);
  writeFileSync(outPath, xml);
}

// ---- cli -------------------------------------------------------------------
const [cmd, a1, a2, a3] = process.argv.slice(2);
const SQL = await initSqlJs();
if (cmd === "init") {
  const db = new SQL.Database();
  execScript(db, readFileSync(DDL, "utf8"));
  persist(db, a1);
} else if (cmd === "import") {
  const db = load(SQL, a1);
  console.log("imported", doImport(db, a2));
  persist(db, a1);
} else if (cmd === "export") {
  exportXml(load(SQL, a1), a2, a3);
  console.log("wrote", a3);
} else if (cmd === "roundtrip") {
  // import then export THROUGH an (in-memory) DB — the required test.
  const db = new SQL.Database();
  execScript(db, readFileSync(DDL, "utf8"));
  const id = doImport(db, a1);
  exportXml(db, id, a2);
  console.log(`round-trip ok: ${a1} -> DB -> ${a2} (doc ${id})`);
} else {
  console.error("usage: init|import|export|roundtrip ...");
  process.exit(2);
}
