# Database Integration

![python](https://img.shields.io/badge/Python-verified-brightgreen) ![java](https://img.shields.io/badge/Java-verified-brightgreen) ![node](https://img.shields.io/badge/JavaScript-verified-brightgreen) ![csharp](https://img.shields.io/badge/C%23-verified-brightgreen) ![multi-fund](https://img.shields.io/badge/multi--node-yes-blue)

Standalone, copy-me examples in the language you already use. **Import and
export are separate programs** — one shows FundsXML → DB, the other DB →
FundsXML — so you can lift exactly the direction you need:

| Language | Import (FundsXML → DB) | Export (DB → FundsXML) | DB driver | Verified |
|----------|------------------------|------------------------|-----------|----------|
| Python | [`python/import_fundsxml.py`](python/import_fundsxml.py) | [`python/export_fundsxml.py`](python/export_fundsxml.py) | stdlib `sqlite3` | ✅ locally + CI |
| Java | [`java/ImportFundsXml.java`](java/ImportFundsXml.java) | [`java/ExportFundsXml.java`](java/ExportFundsXml.java) | `sqlite-jdbc` (native `javax.xml`, no JAXB) | ✅ locally + CI |
| JavaScript | [`javascript/import_fundsxml.mjs`](javascript/import_fundsxml.mjs) | [`javascript/export_fundsxml.mjs`](javascript/export_fundsxml.mjs) | `sql.js` (pure-WASM) | ✅ locally + CI |
| C# / .NET | [`csharp/import/`](csharp/import/) | [`csharp/export/`](csharp/export/) | `Microsoft.Data.Sqlite` | ✅ locally + CI |

Every program is **self-contained** (one file / one project, its own copy of
the small helper maps — nothing shared to import) and heavily commented as a
teaching artifact. The CLI is uniform across languages:

```
<import-prog> <db> <fundsxml.xml>      FundsXML -> rows  (creates the schema)
<export-prog> <db> <docId> <out.xml>   rows -> FundsXML
```

The round-trip is then simply: run import, then run export, then compare.

## Relational model — multi-node

[`ddl/schema.sql`](ddl/schema.sql): `document → fund → portfolio → position`,
`share_class` per fund, document-scoped `asset`. 1-based ordinal keys
(`fund_seq`, `portfolio_seq`, `position_seq`) capture **multiple funds, multiple
portfolios, multiple positions** and preserve their order, so the export is
deterministic and faithful. SQLite makes the examples zero-setup; the same SQL
runs on PostgreSQL (Oracle/SQL Server need only type tweaks — noted in the DDL).

## Round-trip is proven by equivalence

The user requirement: export the data the import wrote, then check the import
and export files are the same. [`tools/xml_equiv.py`](tools/xml_equiv.py) is the
shared comparator — two FundsXML files are equal when they differ only by the
volatile `ControlData/DocumentGenerated` timestamp, numeric formatting,
whitespace, and attribute/namespace ordering; **everything else, including
child order, is significant**. It is always paired with XSD validation
(`xml_equiv` deliberately ignores `xmlns`, so XSD is the complementary check).

The fixture
[`FundsXML_Files/4.2.9/positions/Multi-Fund_Positions.xml`](../FundsXML_Files/4.2.9/positions/Multi-Fund_Positions.xml)
(2 funds; one with 2 portfolios; share classes; document-scoped assets) is
authored **round-trip-faithful** — it contains only what the model captures, so
all four languages reproduce it **exactly** (verified: each export is
`xml_equiv`-equal to the original *and* to every other language's export, and
XSD-valid). The canonical `Mixed-Fund_Positions.xml` also round-trips (n=1)
XSD-valid; it is intentionally lossy outside the positions core, so only its
XSD-validity is asserted.

## Run

Each example is run as **import, then export** (the round-trip = both, then
compare). `DOC` is the document id the import prints.

```bash
FX=FundsXML_Files/4.2.9/positions/Multi-Fund_Positions.xml
DOC=FUNDSXML_MULTI_1

# Python
# Python needs lxml: create the venv from the repo's pyproject.toml once
# (python -m venv .venv && . .venv/bin/activate && pip install -e .)
python3 Database_Integration/python/import_fundsxml.py fx.db "$FX"
python3 Database_Integration/python/export_fundsxml.py fx.db "$DOC" out.xml

# Java  (sqlite-jdbc from Maven Central via the committed Maven Wrapper;
#        on Windows use mvnw.cmd)
MJ="./mvnw -q -pl Database_Integration/java compile exec:java"
$MJ -Dexec.mainClass=ImportFundsXml -Dexec.args="fx.db $FX"
$MJ -Dexec.mainClass=ExportFundsXml -Dexec.args="fx.db $DOC out.xml"

# JavaScript
( cd Database_Integration/javascript && npm install )
node Database_Integration/javascript/import_fundsxml.mjs fx.db "$FX"
node Database_Integration/javascript/export_fundsxml.mjs fx.db "$DOC" out.xml

# C#
dotnet run --project Database_Integration/csharp/import -- fx.db "$FX"
dotnet run --project Database_Integration/csharp/export -- fx.db "$DOC" out.xml

# prove it: exported file == input file, and schema-valid
python3 Database_Integration/tools/xml_equiv.py "$FX" out.xml
XSD_Validation/cli/validate.sh \
  https://github.com/fundsxml/schema/releases/download/4.2.9/FundsXML.xsd \
  out.xml   # or a local FundsXML.xsd path
```

(`--enable-native-access=ALL-UNNAMED` only silences a JDK 24+ warning when
sqlite-jdbc loads its native library; the example works without it.)

## Engine-specific SQL references (not executed)

[`load_from_fundsxml/`](load_from_fundsxml/) and
[`generate_fundsxml/`](generate_fundsxml/) show the **multi-fund** shred/publish
pattern in Oracle, SQL Server and PostgreSQL SQL (nested `XMLTABLE` /
`.nodes()` with ordinality; grouped `XMLAGG` / `FOR XML PATH`). They are code
references mirroring the runnable examples; no database is provisioned here.

CI runs the round-trip for all four languages on the multi-fund fixture
(equivalence + XSD), plus the single-fund sample, on every push.
