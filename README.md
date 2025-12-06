# FundsXML Data Quality Examples

A comprehensive collection of examples and tools for validating and checking data quality in [FundsXML](https://www.fundsxml.org) documents. This repository helps developers, system integrators, and financial technologists implement FundsXML data validation in their systems.

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

| Component | Description | Location |
|-----------|-------------|----------|
| Sample Files | FundsXML example documents with diverse asset types | [FundsXML_Files/](./FundsXML_Files/) |
| Schematron Rules | Business rule validation using ISO Schematron | [Schematron_DataQuality_Checks/](./Schematron_DataQuality_Checks/) |
| XSLT Reports | HTML data quality report generators | [XSLT_DataQuality_Checks/](./XSLT_DataQuality_Checks/) |

## Repository Structure

```
FundsXML-Examples/
├── README.md                              # This file
├── CLAUDE.md                              # AI assistant guidance
├── LICENSE                                # Apache 2.0
│
├── FundsXML_Files/                        # Sample FundsXML documents
│   └── 4.2.9/
│       └── Mixed-Fund_Positions.xml       # Comprehensive example with 21 positions
│
├── Schematron_DataQuality_Checks/         # Schematron validation rules
│   └── Basic_Checks/
│       └── basic_checks.sch               # 7 validation patterns, 40+ rules
│
└── XSLT_DataQuality_Checks/               # XSLT transformation stylesheets
    ├── Basic_Checks/
    │   └── basic_checks.xslt              # XSLT 2.0 - 5 check sections
    └── Enhanced_Check/
        ├── FundsXML_CompleteDQReport_HTML.xsl  # XSLT 1.0 - 10-section dashboard
        └── FundsXML Complete Data Quality Report.pdf  # Sample output
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
saxon -s:FundsXML_Files/4.2.9/Mixed-Fund_Positions.xml \
      -xsl:XSLT_DataQuality_Checks/Basic_Checks/basic_checks.xslt \
      -o:report.html
```

### Option 2: Command Line (xsltproc - XSLT 1.0 only)

```bash
# Pre-installed on macOS, install on Linux:
sudo apt install xsltproc

# Generate enhanced report (XSLT 1.0 compatible)
xsltproc XSLT_DataQuality_Checks/Enhanced_Check/FundsXML_CompleteDQReport_HTML.xsl \
         FundsXML_Files/4.2.9/Mixed-Fund_Positions.xml > report.html
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
doc = etree.parse('FundsXML_Files/4.2.9/Mixed-Fund_Positions.xml')
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
| [FundsXML Files](./FundsXML_Files/README.md) | Understanding FundsXML structure and format |
| [Schematron Validation](./Schematron_DataQuality_Checks/README.md) | Business rule validation with Schematron |
| [XSLT Transformations](./XSLT_DataQuality_Checks/README.md) | Generating HTML quality reports |

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

Contributions are welcome! Please feel free to submit pull requests with:
- Additional sample FundsXML files
- New Schematron validation rules
- Additional XSLT report templates
- Documentation improvements
- Code examples in other languages

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **FundsXML Standard**: [FundsXML.org](https://www.fundsxml.org)
- **Schema Questions**: [FundsXML Schema Repository](https://github.com/fundsxml/schema)
