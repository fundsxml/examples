# Database Integration

![python](https://img.shields.io/badge/SQLite%20round--trip-verified-brightgreen) ![sql](https://img.shields.io/badge/Oracle%2FSQLServer%2FPostgres-code--reference-blue)

FundsXML ⇄ relational database, both directions. Per project scope **no
database is provisioned** (no Docker): the Oracle / SQL Server / PostgreSQL
files are **code references**, and the **SQLite Python implementation is the
runnable, verified reference** (stdlib + lxml only) that exercises the full
round-trip and produces XSD-valid FundsXML.

## Layout

| Path | What |
|------|------|
| [`ddl/schema.sql`](ddl/schema.sql) | Shared relational model (fund, share_class, asset, position) |
| [`load_from_fundsxml/`](load_from_fundsxml/) | FundsXML → DB: `postgres.sql` (XMLTABLE), `oracle.sql` (XMLType + XMLTABLE), `sqlserver.sql` (`.nodes()`/`.value()`) |
| [`generate_fundsxml/`](generate_fundsxml/) | DB → FundsXML: SQL/XML publishing (`xmlelement`/`xmlagg`, `XMLElement`/`XMLAgg`, `FOR XML PATH`) |
| [`python/fundsxml_db.py`](python/fundsxml_db.py) | **Runnable** SQLite reference: `init` / `load` / `generate` / `roundtrip` |

The relational model is keyed by `ControlData/UniqueDocumentID` so multiple
documents coexist. FundsXML 4.x has no XML namespace — all XPath/queries use
bare element names.

## Runnable round-trip (verified)

```bash
python3 Database_Integration/python/fundsxml_db.py roundtrip \
  FundsXML_Files/4.2.9/positions/Mixed-Fund_Positions.xml regenerated.xml

tools/fetch-schema.sh 4.2.9
xmllint --noout --schema .schema-cache/4.2.9/FundsXML.xsd regenerated.xml
```

Verified for the 4.2.9 positions, 4.1.0 and 4.0.0 positions, and 4.2.9
transactions samples: each loads into SQLite and regenerates **XSD-valid**
FundsXML with NAV, position count and percentage sum preserved.

### Round-trip fidelity

The model captures fund header, share classes (incl. `TotalAssetValues` /
`SharesOutstanding`), positions (value, %, class + quantity child) and asset
master data. It is intentionally **lossy** for everything outside that core
(issuer details, derivative terms, transactions, regulatory blocks) — the
regenerated file is a faithful *positions* document, normalized to the 4.2.9
schema (a 4.0.0 input comes back without `ControlData/Version`, which is valid).

The three enterprise-DB SQL files mirror the same shred/publish logic; only the
SQLite path is executed here. CI runs the round-trip on every push.
