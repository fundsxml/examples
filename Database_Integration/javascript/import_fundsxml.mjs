// =============================================================================
// IMPORT  —  FundsXML file  ->  relational database  (Node.js, SQLite).
//
// Standalone, copy-me example of ONE direction (FundsXML -> DB). The reverse
// is a separate program, export_fundsxml.mjs. Over-commented as documentation.
//
// DB SCHEMA  ../ddl/schema.sql  (document -> fund -> portfolio -> position;
//   share_class per fund; asset document-scoped). Creates the schema in a
//   fresh DB then loads the file. The "db file" is sql.js's serialized image.
//
// RUN
//   cd Database_Integration/javascript && npm install
//   node import_fundsxml.mjs fx.db \
//     ../../FundsXML_Files/4.2.9/positions/Multi-Fund_Positions.xml
//   node export_fundsxml.mjs fx.db FUNDSXML_MULTI_1 out.xml
//
// DEPENDENCIES (pure-JS, no native build): sql.js (WASM SQLite),
//   @xmldom/xmldom + xpath (namespace-free DOM). Node 20 has no built-in
//   node:sqlite (added in 22.5), hence sql.js.
//
// FUNDSXML ASSUMPTIONS
//   * No XML namespace -> bare element names in XPath.
//   * Many <Fund>/<Portfolio>/<Position>: all iterated; 1-based *_seq columns
//     preserve order so the separate export reproduces the original document.
//   * Positions link to AssetMasterData by shared <UniqueID> -> `asset` is
//     document-scoped.
//
// SECURITY  @xmldom/xmldom never resolves external entities; we also reject a
//   DOCTYPE so a feed cannot declare entities (XXE).
// =============================================================================
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import initSqlJs from "sql.js";
import { DOMParser } from "@xmldom/xmldom";
import xpath from "xpath";

const HERE = dirname(fileURLToPath(import.meta.url));
const DDL = resolve(HERE, "..", "ddl", "schema.sql");

const POSITION_KINDS = new Set(["Equity", "Bond", "ShareClass", "Warrant",
  "Certificate", "Option", "Future", "FXForward", "Swap", "Repo",
  "RealEstate", "CallMoney", "Account", "Generic"]);
const QTY_ELEM = { Equity: "Units", Warrant: "Units", Certificate: "Units",
  Bond: "Nominal", ShareClass: "Shares", Option: "Contracts",
  Future: "Contracts" };

const txt = (ctx, expr) => {            // first match's text or null
  const n = xpath.select1(expr, ctx);
  return n && n.textContent !== "" && n.textContent != null
    ? n.textContent : null;
};
const numOrNull = (s) => (s == null || s === "" ? null : Number(s));

function execScript(db, sql) {
  // Strip "--" line comments (no string literals in the DDL) then run.
  const clean = sql.split("\n").map((l) => {
    const i = l.indexOf("--");
    return i >= 0 ? l.slice(0, i) : l;
  }).join("\n");
  for (const stmt of clean.split(";")) if (stmt.trim()) db.run(stmt);
}

const [dbPath, xmlPath] = process.argv.slice(2);
if (!dbPath || !xmlPath) {
  console.error("usage: import_fundsxml.mjs <db> <fundsxml.xml>");
  process.exit(2);
}

const src = readFileSync(xmlPath, "utf8");
if (/<!DOCTYPE/i.test(src)) throw new Error("DOCTYPE not allowed (XXE)");
const doc = new DOMParser().parseFromString(src, "text/xml");

const SQL = await initSqlJs();
const db = new SQL.Database();
execScript(db, readFileSync(DDL, "utf8"));   // create the schema (fresh DB)

const cd = xpath.select1("/FundsXML4/ControlData", doc);
const docId = txt(cd, "UniqueDocumentID");

db.run("INSERT INTO document VALUES (?,?,?,?,?,?,?,?,?)", [
  docId, txt(cd, "DocumentGenerated"), txt(cd, "Version"),
  txt(cd, "ContentDate"), txt(cd, "DataOperation"),
  txt(cd, "DataSupplier/SystemCountry"), txt(cd, "DataSupplier/Short"),
  txt(cd, "DataSupplier/Name"), txt(cd, "DataSupplier/Type")]);

xpath.select("/FundsXML4/Funds/Fund", doc).forEach((fund, fi) => {
  const fundSeq = fi + 1;                     // 1-based document order
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

writeFileSync(dbPath, Buffer.from(db.export()));
console.log("imported document_id:", docId);
