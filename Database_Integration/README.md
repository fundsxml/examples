# Database Integration

![python](https://img.shields.io/badge/Python-verified-brightgreen) ![java](https://img.shields.io/badge/Java-verified-brightgreen) ![node](https://img.shields.io/badge/JavaScript-verified-brightgreen) ![csharp](https://img.shields.io/badge/C%23-verified-brightgreen) ![multi-fund](https://img.shields.io/badge/multi--node-yes-blue)

Standalone, copy-me examples that move data **both directions** between FundsXML
and a relational database, in the language you already use:

| Language | File | DB driver | Verified |
|----------|------|-----------|----------|
| Python | [`python/fundsxml_db.py`](python/fundsxml_db.py) | stdlib `sqlite3` | ✅ locally |
| Java | [`java/FundsXmlDb.java`](java/FundsXmlDb.java) | `sqlite-jdbc` (native `javax.xml`, no JAXB) | ✅ locally |
| JavaScript | [`javascript/fundsxml_db.mjs`](javascript/fundsxml_db.mjs) | `sql.js` (pure-WASM) | ✅ locally |
| C# / .NET | [`csharp/FundsXmlDb.cs`](csharp/FundsXmlDb.cs) | `Microsoft.Data.Sqlite` | ✅ locally + CI |

Every program is **self-contained**, heavily commented as a teaching artifact
(read one top-to-bottom and reimplement the pattern), and exposes the **same
CLI**:

```
<prog> init      <db>                  create the schema
<prog> import    <db> <fundsxml.xml>   FundsXML  -> rows
<prog> export    <db> <docId> <out>    rows      -> FundsXML
<prog> roundtrip <fundsxml.xml> <out>  import then export through the DB
```

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

```bash
tools/fetch-schema.sh 4.2.9          # XSD for validation
FX=FundsXML_Files/4.2.9/positions/Multi-Fund_Positions.xml

# Python
python3 Database_Integration/python/fundsxml_db.py roundtrip "$FX" out.xml

# Java  (sqlite-jdbc fetched into .lib/ by tools/fetch-tools.sh)
tools/fetch-tools.sh
CP=.lib/sqlite-jdbc-3.46.1.3.jar
javac -cp "$CP" -d /tmp/db Database_Integration/java/FundsXmlDb.java
java --enable-native-access=ALL-UNNAMED -cp "$CP:/tmp/db" FundsXmlDb roundtrip "$FX" out.xml

# JavaScript
( cd Database_Integration/javascript && npm install )
node Database_Integration/javascript/fundsxml_db.mjs roundtrip "$FX" out.xml

# C#
dotnet run --project Database_Integration/csharp -- roundtrip "$FX" out.xml

# prove it: identical to the input, and schema-valid
python3 Database_Integration/tools/xml_equiv.py "$FX" out.xml
xmllint --noout --schema .schema-cache/4.2.9/FundsXML.xsd out.xml
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
