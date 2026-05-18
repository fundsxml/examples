# FundsXML Enterprise Examples

A comprehensive, runnable reference for working with [FundsXML](https://www.fundsxml.org) in enterprise settings: sample data across versions and use cases, XSD validation, Schematron, XSLT transformations, XQuery analytics, XML signatures, database integration, large-file streaming, and data binding / JSON — each demonstrated across the common enterprise stacks (CLI, Python, Java, .NET/C#, Node.js) and exercised in CI.

## What is FundsXML?

FundsXML is an industry-standard XML format for exchanging fund and investment data between asset managers, fund administrators, custodians, and data vendors. It provides a structured way to represent:

- Fund master data (identifiers, names, currencies)
- Share class information (ISINs, NAV prices)
- Portfolio holdings and positions
- Asset master data for various instrument types
- Dynamic fund data (total asset values, performance)

**Official Resources:**
- [FundsXML.org](https://www.fundsxml.org) - Official website
- [FundsXML Schema Repository](https://github.com/fundsxml/schema) - XSD schemas

## What This Repository Provides

A comprehensive **enterprise FundsXML reference**. Every area below is
implemented, has its own README, runs standalone & cross-platform (Windows +
Linux/macOS) with no bash prerequisite, and is exercised by the CI workflow.

| Area | Technology | Location |
|------|-----------|----------|
| Sample data (positions, transactions, documents, regulatory, signed) | XML, 3 versions (4.2.9 / 4.1.0 / 4.0.0) | [FundsXML_Files/](./FundsXML_Files/) |
| XSD validation | CLI (sh + ps1), Python, Java, .NET, PowerShell | [XSD_Validation/](./XSD_Validation/) |
| Schematron business rules | ISO Schematron + SchXslt | [Schematron_DataQuality_Checks/](./Schematron_DataQuality_Checks/) |
| Schematron invocation | Java, Python, .NET | [Schematron_DataQuality_Checks/Basic_Checks/invocation/](./Schematron_DataQuality_Checks/Basic_Checks/) |
| Data-quality reports | XSLT 1.0 / 2.0 | [XSLT_DataQuality_Checks/](./XSLT_DataQuality_Checks/) |
| Company-internal DQ rules | XSLT 2.0 | [XSLT_DataQuality_Checks/Custom_Internal_Checks/](./XSLT_DataQuality_Checks/) |
| Factsheet (HTML/PDF) & CSV export | XSLT, XSL-FO/FOP | [XSLT_Transformations/](./XSLT_Transformations/) |
| Transformation invocation | Java, Python, Node | [XSLT_Transformations/invocation/](./XSLT_Transformations/) |
| XQuery analytics (aggregation, top-holdings, look-through) | Saxon (Java), Python, BaseX | [XQuery_Examples/](./XQuery_Examples/) |
| XML signature sign / verify | Apache Santuario (Java), .NET, xmlsec1, signxml | [XML_Signature/](./XML_Signature/) |
| Database import / export (multi-fund) | Separate import + export programs in Python · Java · JavaScript · C# (SQLite); Oracle/SQL Server/Postgres SQL (code refs) | [Database_Integration/](./Database_Integration/) |
| Large-file / streaming | lxml iterparse + Java StAX, split, delta-diff | [Large_File_Processing/](./Large_File_Processing/) |
| Data binding & JSON | FundsXML⇄JSON, native Java binding, codegen refs | [Data_Binding_JSON/](./Data_Binding_JSON/) |

## Repository Structure

```
fundsxml_examples/
├── README.md                              # This file (index above)
├── LICENSE                                # Apache 2.0
├── pom.xml  mvnw  mvnw.cmd  .mvn/         # Maven aggregator + committed
│                                          #   wrapper: builds all Java
│                                          #   examples standalone (deps from
│                                          #   Maven Central), no preinstall
├── pyproject.toml                          # Python deps (lxml + saxonche);
│                                          #   dependency-only, nothing packaged
│
├── FundsXML_Files/                        # Sample documents, per version & use-case
│   ├── 4.2.9/{positions,transactions,documents,regulatory,signed}/
│   ├── 4.1.0/positions/   └── 4.0.0/positions/
│
├── XSD_Validation/                        # Validation per stack
│   └── {cli,python,java,dotnet,powershell}/
│
├── Schematron_DataQuality_Checks/Basic_Checks/
│   ├── basic_checks.sch                   # patterns + rules
│   └── invocation/                        # CLI, Python, Java, .NET
│
├── XSLT_DataQuality_Checks/
│   ├── Basic_Checks/  Enhanced_Check/     # HTML/PDF DQ reports
│   └── Custom_Internal_Checks/            # company-internal DQ rules
│
├── XSLT_Transformations/                  # Factsheet (HTML/PDF), CSV export
│   └── {Factsheet,CSV_Export,invocation}/
│
├── XQuery_Examples/                       # aggregation, top-holdings, look-through
│   └── invocation/                        # Saxon CLI, Java, Python
│
├── XML_Signature/                         # enveloped XML-DSig sign/verify
│   ├── java/  csharp/  python/  cli/      # Apache Santuario, SignedXml, …
│   │   └── java/GenerateTestKey.java      # throwaway keys via JDK keytool
│
├── Database_Integration/                  # FundsXML ⇄ relational DB (multi-fund)
│   ├── ddl/schema.sql
│   ├── python/{import,export}_fundsxml.py
│   ├── java/{Import,Export}FundsXml.java
│   ├── javascript/{import,export}_fundsxml.mjs
│   ├── csharp/import/  csharp/export/     # one .csproj each
│   ├── load_from_fundsxml/  generate_fundsxml/   # Oracle/MSSQL/PG SQL (code)
│   └── tools/xml_equiv.py                 # normalized round-trip comparator
│
├── Large_File_Processing/                 # constant-memory streaming
│   ├── python/  java/                     # iterparse / StAX, split, delta-diff
│
├── Data_Binding_JSON/                     # FundsXML ⇄ JSON, native binding
│   └── python/  java/
│
├── tests/fixtures/invalid/                # deliberately broken negative fixtures
└── .github/workflows/ci.yml               # validates everything on each push
```

## Quick Start

Every example is **standalone and cross-platform** — no bash prerequisite, no
manual dependency fetching. Each language uses its own idiomatic build system;
dependencies are resolved automatically on first run. The XSD validators take
a schema (local path or remote URL) plus the XML file — you supply the schema,
nothing is auto-resolved. **Run all commands from the repo root.** On Windows
use `mvnw.cmd` instead of `./mvnw` and `.venv\Scripts\activate` instead of the
`source` line.

### One-time setup (only the toolchains you intend to use)

```bash
# Java   — nothing to install: the committed Maven Wrapper bootstraps Maven
#          and pulls all deps from Maven Central on first ./mvnw call.
# .NET   — .NET SDK 8+ ; `dotnet run` restores NuGet packages itself.
# Node   — Node 20+    ; `npm install` in Database_Integration/javascript.

# Python — one venv from pyproject.toml (lxml + saxonche; deps only)
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e .
```

The XSD is whatever you hand the validator — a local `FundsXML.xsd` path or a
remote URL (e.g. the official release
`https://github.com/fundsxml/schema/releases/download/<ver>/FundsXML.xsd`).
No version arg, no cache, no env var. Nothing to run up front.

### Try one example per area

```bash
SRC=FundsXML_Files/4.2.9/positions/Mixed-Fund_Positions.xml
XSD=https://github.com/fundsxml/schema/releases/download/4.2.9/FundsXML.xsd
# ($XSD can equally be a local FundsXML.xsd path — same result, fully offline)

# XSD validation — pick any stack (schema + xml, schema-first):
python XSD_Validation/python/validate.py "$XSD" $SRC
dotnet run --project XSD_Validation/dotnet -- "$XSD" $SRC
./mvnw -q -pl XSD_Validation/java compile exec:java -Dexec.args="$XSD $SRC"
XSD_Validation/cli/validate.sh "$XSD" $SRC          # Windows: pwsh .../validate.ps1

# Schematron business rules (SVRL; exit 0 = no ERROR-role failures)
./mvnw -q -pl Schematron_DataQuality_Checks/Basic_Checks/invocation compile exec:java \
  -Dexec.args="Schematron_DataQuality_Checks/Basic_Checks/basic_checks.sch $SRC"

# XSLT 2.0 transform — CSV export (also: Factsheet HTML / XSL-FO)
./mvnw -q -pl XSLT_Transformations/invocation compile exec:java \
  -Dexec.args="XSLT_Transformations/CSV_Export/positions_csv.xslt $SRC out.csv"

# XQuery analytics — top 5 holdings (serialized to stdout)
./mvnw -q -pl XQuery_Examples/invocation compile exec:java \
  -Dexec.args="XQuery_Examples/top-holdings.xq $SRC n=5"

# XML signature — throwaway key, then sign + verify (RSA-SHA256, enveloped)
./mvnw -q -pl XML_Signature/java compile exec:java -Dexec.mainClass=GenerateTestKey
./mvnw -q -pl XML_Signature/java exec:java -Dexec.mainClass=SignFundsXml \
  -Dexec.args="$SRC signed.xml XML_Signature/keys/test-signing.p12 changeit fundsxml"
./mvnw -q -pl XML_Signature/java exec:java -Dexec.mainClass=VerifyFundsXml \
  -Dexec.args="signed.xml XML_Signature/keys/test-signing-cert.pem"

# Database round-trip — import → export → prove equivalence
FX=FundsXML_Files/4.2.9/positions/Multi-Fund_Positions.xml
python Database_Integration/python/import_fundsxml.py fx.db $FX
python Database_Integration/python/export_fundsxml.py fx.db FUNDSXML_MULTI_1 out.xml
python Database_Integration/tools/xml_equiv.py $FX out.xml

# Large-file streaming (constant memory) — synthesize, then aggregate
python Large_File_Processing/python/make_large_sample.py big.xml 50000
python Large_File_Processing/python/stream_aggregate.py big.xml

# Legacy XSLT 1.0 report (xsltproc, no Saxon needed)
xsltproc XSLT_DataQuality_Checks/Enhanced_Check/FundsXML_CompleteDQReport_HTML.xsl \
         $SRC > report.html
```

Each area's README has the full per-language matrix (Java / Python / .NET /
Node / CLI), platform notes, and deeper walk-throughs — see the table below.

## Data Quality Checks Overview

### Validation Categories

| Category | Description | Severity |
|----------|-------------|----------|
| **Structural** | Required elements present (LEI, ISIN, portfolios) | ERROR/WARNING |
| **NAV Calculations** | ShareClass NAVs sum to Fund Total NAV | ERROR |
| **Price Consistency** | Price × Shares = NAV per ShareClass | ERROR |
| **Portfolio Reconciliation** | Position values sum to Fund NAV | ERROR |
| **Percentage Allocation** | Position percentages sum to 100% | ERROR |
| **Identifier Format** | ISIN (12), LEI (20), BIC (8/11), Currency (3) | ERROR/WARNING |
| **Asset Rules** | Derivatives have underlyings, accounts have counterparties | ERROR/WARNING |
| **Date Consistency** | NAV dates match content date | WARNING |

### Severity Levels

- **ERROR** - Critical issues that must be fixed before data can be used
- **WARNING** - Important issues that should be reviewed
- **INFO** - Informational messages about data quality

## Detailed Documentation

Each folder contains detailed README files with:
- Technology explanation
- Full code examples for Java, Python, .NET/C#, Node.js
- Platform-specific instructions (Windows, macOS, Linux)
- Troubleshooting guides

| Documentation | Description |
|--------------|-------------|
| [FundsXML Files](./FundsXML_Files/README.md) | FundsXML structure, versions and sample documents |
| [XSD Validation](./XSD_Validation/README.md) | Schema validation per stack (CLI/Python/Java/.NET/PowerShell) |
| [Schematron Validation](./Schematron_DataQuality_Checks/README.md) | Business-rule validation with Schematron + invocation |
| [XSLT DQ Checks](./XSLT_DataQuality_Checks/README.md) | HTML/PDF data-quality reports & custom internal rules |
| [XSLT Transformations](./XSLT_Transformations/README.md) | Factsheet (HTML/PDF) and CSV export |
| [XQuery Examples](./XQuery_Examples/README.md) | Aggregation, top-holdings, look-through analytics |
| [XML Signature](./XML_Signature/README.md) | Enveloped XML-DSig sign/verify (Apache Santuario & co.) |
| [Database Integration](./Database_Integration/README.md) | Multi-fund import/export, 4 languages, round-trip-verified |
| [Large-File Processing](./Large_File_Processing/README.md) | Constant-memory streaming, split, INITIAL/DELTA diff |
| [Data Binding & JSON](./Data_Binding_JSON/README.md) | FundsXML⇄JSON and native binding vs. codegen |

## Requirements

You only need the toolchain for the stack you want to run. Third-party
libraries (Saxon, SchXslt, Apache Santuario, SQLite drivers, lxml, saxonche,
…) are **not installed manually** — each build system resolves them:

| Stack | Need installed | Dependencies come from |
|-------|----------------|------------------------|
| Java | JDK 17+ (the committed `./mvnw` wrapper handles Maven itself) | Maven Central |
| Python | Python 3.9+ | `pip install -e .` (pyproject.toml) |
| .NET | .NET SDK 8+ | NuGet (`dotnet run` restores) |
| Node | Node 20+ | `npm install` (Database_Integration/javascript) |
| CLI | a POSIX shell + `xmllint` (Linux/macOS) **or** PowerShell 5.1+/7+ (Windows) | n/a |
| Legacy XSLT 1.0 | `xsltproc` | n/a |

Network access to Maven Central / PyPI / NuGet on first run is expected. For
the XSD validators, network is only needed if you pass a schema **URL**; pass
a local `FundsXML.xsd` path (keep its `xmldsig-core-schema.xsd` sibling beside
it for 4.2.9+) to validate fully offline.

## Asset Types in Examples

The sample files demonstrate various FundsXML asset types:

| Code | Asset Type | Description |
|------|------------|-------------|
| EQ | Equity | Stocks, shares |
| BO | Bond | Fixed income securities |
| SC | ShareClass | Fund investments |
| OP | Option | Call/Put options |
| FU | Future | Futures contracts |
| FX | FX Forward | Currency forwards |
| SW | Swap | Interest rate, currency swaps |
| WA | Warrant | Warrants |
| CE | Certificate | Structured products |
| AC | Account | Bank accounts |
| RP | Repo | Repurchase agreements |
| RE | Real Estate | Property investments |
| CM | Call Money | Short-term deposits |

## Contributing

Contributions are welcome — additional samples, rules, report templates,
language examples, and documentation improvements. Please read
**[CONTRIBUTING.md](./CONTRIBUTING.md)** first: it covers the FundsXML
conventions, the secure-XML and round-trip requirements, local verification,
and the branch/PR workflow this repo expects.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/fundsxml/examples/issues)
- **FundsXML Standard**: [FundsXML.org](https://www.fundsxml.org)
- **Schema Questions**: [FundsXML Schema Repository](https://github.com/fundsxml/schema)
