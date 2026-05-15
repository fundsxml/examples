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

A comprehensive **enterprise FundsXML reference**. The table below maps use
cases to technologies and example locations. Every row is implemented, has its
own README, and is exercised by the CI workflow on each push.

| Use case | Technology | Location | Status |
|----------|-----------|----------|--------|
| Sample data (positions, transactions, documents, regulatory, signed) | XML, 3 versions | [FundsXML_Files/](./FundsXML_Files/) | ✅ |
| XSD validation | CLI, Python, Java, .NET, PowerShell | [XSD_Validation/](./XSD_Validation/) | ✅ |
| Schematron business rules | ISO Schematron + SchXslt | [Schematron_DataQuality_Checks/](./Schematron_DataQuality_Checks/) | ✅ |
| Schematron invocation | CLI, Python, Java, .NET | [Schematron_DataQuality_Checks/Basic_Checks/invocation/](./Schematron_DataQuality_Checks/Basic_Checks/) | ✅ |
| Data-quality reports | XSLT 1.0 / 2.0 | [XSLT_DataQuality_Checks/](./XSLT_DataQuality_Checks/) | ✅ |
| Company-internal DQ rules | XSLT 2.0 | [XSLT_DataQuality_Checks/Custom_Internal_Checks/](./XSLT_DataQuality_Checks/) | ✅ |
| Factsheet (HTML/PDF) & CSV export | XSLT, XSL-FO/FOP | [XSLT_Transformations/](./XSLT_Transformations/) | ✅ |
| Transformation invocation | CLI, Python, Java, .NET, Node | [XSLT_Transformations/invocation/](./XSLT_Transformations/) | ✅ |
| Schema fetch (proxy-aware) | Bash | [tools/fetch-schema.sh](./tools/fetch-schema.sh) | ✅ |
| CI (validate all samples) | GitHub Actions | [.github/workflows/ci.yml](./.github/workflows/) | ✅ |
| XQuery analytics (aggregation, top-holdings, look-through) | Saxon CLI/Java, Python, BaseX | [XQuery_Examples/](./XQuery_Examples/) | ✅ |
| XML signature sign/verify | Apache Santuario (Java), .NET, xmlsec1, signxml | [XML_Signature/](./XML_Signature/) | ✅ |
| Database import / export (multi-fund) | Separate standalone import + export programs in Python · Java · JavaScript · C# (SQLite), all verified; Oracle/SQL Server/Postgres SQL (code) | [Database_Integration/](./Database_Integration/) | ✅ |
| Large-file / streaming | lxml iterparse + Java StAX, split, delta-diff | [Large_File_Processing/](./Large_File_Processing/) | ✅ |
| Data binding & JSON | FundsXML⇄JSON, native Java binding, codegen refs | [Data_Binding_JSON/](./Data_Binding_JSON/) | ✅ |

## Repository Structure

```
fundsxml_examples/
├── README.md                              # This file (index above)
├── LICENSE                                # Apache 2.0
├── tools/                                 # fetch-schema.sh, fetch-tools.sh
│                                          #   (proxy-aware XSD / jar fetchers)
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
│   └── generate-test-key.sh
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

### Option 1: Command Line (Saxon)

```bash
# Install Saxon (XSLT 2.0/3.0 processor)
# macOS:
brew install saxon

# Ubuntu/Debian:
sudo apt install libsaxonhe-java

# Windows (Chocolatey):
choco install saxonhe

# Generate a data quality report
saxon -s:FundsXML_Files/4.2.9/positions/Mixed-Fund_Positions.xml \
      -xsl:XSLT_DataQuality_Checks/Basic_Checks/basic_checks.xslt \
      -o:report.html
```

### Option 2: Command Line (xsltproc - XSLT 1.0 only)

```bash
# Pre-installed on macOS, install on Linux:
sudo apt install xsltproc

# Generate enhanced report (XSLT 1.0 compatible)
xsltproc XSLT_DataQuality_Checks/Enhanced_Check/FundsXML_CompleteDQReport_HTML.xsl \
         FundsXML_Files/4.2.9/positions/Mixed-Fund_Positions.xml > report.html
```

### Option 3: Python

```bash
# Install dependencies
pip install lxml        # XSLT 1.0
pip install saxonche    # XSLT 2.0/3.0

# Run transformation
python -c "
from lxml import etree
xslt = etree.parse('XSLT_DataQuality_Checks/Enhanced_Check/FundsXML_CompleteDQReport_HTML.xsl')
transform = etree.XSLT(xslt)
doc = etree.parse('FundsXML_Files/4.2.9/positions/Mixed-Fund_Positions.xml')
result = transform(doc)
with open('report.html', 'wb') as f:
    f.write(etree.tostring(result, pretty_print=True))
print('Report generated: report.html')
"
```

### Option 4: Java

```java
// Add Saxon dependency to your project (Maven):
// <dependency>
//   <groupId>net.sf.saxon</groupId>
//   <artifactId>Saxon-HE</artifactId>
//   <version>12.4</version>
// </dependency>

import net.sf.saxon.s9api.*;
import java.io.File;

Processor processor = new Processor(false);
XsltCompiler compiler = processor.newXsltCompiler();
XsltExecutable executable = compiler.compile(new StreamSource(new File("basic_checks.xslt")));
Xslt30Transformer transformer = executable.load30();
transformer.transform(
    new StreamSource(new File("Mixed-Fund_Positions.xml")),
    processor.newSerializer(new File("report.html"))
);
```

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

### Minimum Requirements

| Component | XSLT 1.0 Reports | XSLT 2.0 Reports | Schematron |
|-----------|-----------------|------------------|------------|
| xsltproc | Yes | No | No |
| Saxon-HE | Yes | Yes | Yes |
| lxml (Python) | Yes | No | No |
| saxonche (Python) | Yes | Yes | Yes |
| System.Xml (.NET) | Yes | No | No |
| Saxon.Api (.NET) | Yes | Yes | Yes |

### Recommended Setup

- **Java 11+** with Saxon-HE 12.x for full XSLT 2.0/3.0 support
- **Python 3.8+** with saxonche for XSLT 2.0 support
- **.NET 6+** with Saxon.Api NuGet package

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
