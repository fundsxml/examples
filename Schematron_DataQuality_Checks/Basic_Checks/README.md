# Basic Schematron Checks for FundsXML

This directory contains comprehensive Schematron validation rules for FundsXML data quality checking.

## File Overview

| Property | Value |
|----------|-------|
| **File** | `basic_checks.sch` |
| **Query Binding** | XSLT 2.0 (`queryBinding="xslt2"`) |
| **Patterns** | 9 validation patterns |
| **Total Rules** | 40+ assertions and reports |
| **Purpose** | Comprehensive FundsXML data quality validation |

## Known ruleset fix

ISO Schematron matches each node against only the **first** `rule` whose
`context` matches **within a pattern**. The `portfolio-validations` pattern
previously held two `Fund[…]` rules (position-value sum *and* percentage sum);
every real fund matched the first, so the **percentage-sum rule was dead code
and never fired** (likewise a `Position` rule shadowed the multi-currency
direction rule). These were split into their own patterns —
`percentage-validations`, `position-currency-validations`,
`position-direction-validations` — so each rule actually executes. Verified: a
document with percentages summing to 120 % now produces an ERROR; the canonical
sample (summing to 100 %) does not.

Run it across stacks via [`invocation/`](invocation/) (CLI, native Java,
Python/saxonche, .NET). The canonical sample yields **0 errors + 12 advisory
warnings** (the broad `ShareClass` rule also matches `AssetDetails/ShareClass`;
derivative assets without exposure info).

## Requirements

**XSLT 2.0 processor required** due to `queryBinding="xslt2"`.

Recommended processors:
- Saxon-HE 10+ (free, open source)
- Saxon-EE (commercial, with schema awareness)
- AltovaXML (commercial)

## Validation Rules Summary

### Pattern 1: Structural Checks

Validates the basic structure and required elements of FundsXML documents.

| Rule | Context | Severity | Description |
|------|---------|----------|-------------|
| Fund LEI | `Fund` | WARNING | Fund should have a LEI identifier |
| Portfolio Exists | `Fund` | WARNING | Fund must have at least one portfolio |
| NAV in Fund Currency | `Fund` | ERROR | Total Asset Value must be provided in fund currency |
| ShareClass ISIN | `ShareClass` | WARNING | ShareClasses should have an ISIN |

### Pattern 2: NAV Calculations

Validates NAV consistency between fund and share class levels.

| Rule | Context | Severity | Description | Tolerance |
|------|---------|----------|-------------|-----------|
| ShareClass NAV Sum | `Fund` | ERROR | Sum of ShareClass NAVs must equal Fund Total NAV | < 1 currency unit |
| Rounding Warning | `Fund` | WARNING | Alert for small rounding differences | 0.01 - 1 |
| Price Calculation | `ShareClass` | ERROR | Price × Shares must equal NAV | < 0.1 |
| Price Rounding | `ShareClass` | WARNING | Alert for small price differences | 0.01 - 0.1 |

### Pattern 3: Portfolio Validations

Checks portfolio positions and allocation consistency.

| Rule | Context | Severity | Description | Tolerance |
|------|---------|----------|-------------|-----------|
| Position Sum | `Fund` | ERROR | Sum of position values must equal Fund Total NAV | < 1 currency unit |
| Percentage Sum | `Fund` | ERROR | Position percentages must sum to 100% | ≤ 1% |
| Percentage Warning | `Fund` | WARNING | Alert for small percentage deviations | 0.01% - 1% |
| Position Currency | `Position` | ERROR | Each position must have value in fund currency | - |
| Value Direction | `Position` | ERROR | Position values must be consistent (+/-) across currencies | - |

### Pattern 4: Asset-Specific Validations

Asset type-specific requirements based on the AssetType code.

| Rule | Asset Types | Severity | Description |
|------|-------------|----------|-------------|
| ISIN Required | EQ, BO, SC | ERROR | Equity, Bond, ShareClass assets must have ISIN |
| Counterparty ID | AC | WARNING | Account assets should have counterparty LEI or BIC |
| Derivative Exposure | OP, FU, FX, SW | WARNING | Derivatives should have exposure information |
| Option Underlying | OP | ERROR | Options must have at least one underlying |
| Future Underlying | FU | ERROR | Futures must have at least one underlying |

**Asset Type Codes:**
- EQ = Equity
- BO = Bond
- SC = ShareClass (Fund investment)
- AC = Account
- OP = Option
- FU = Future
- FX = FX Forward
- SW = Swap

### Pattern 5: Date Consistency

Validates temporal consistency across the document.

| Rule | Context | Severity | Description |
|------|---------|----------|-------------|
| NAV Date Match | `Fund` | WARNING | All ShareClass NAV dates should match Fund NAV date |
| Future Date | `ContentDate` | WARNING | Content date should not be in the future |

### Pattern 6: Identifier Validations

Validates format and structure of identifiers.

| Rule | Identifier | Severity | Format |
|------|------------|----------|--------|
| ISIN Length | ISIN | ERROR | Exactly 12 characters |
| ISIN Format | ISIN | WARNING | 2 letters + 9 alphanumeric + 1 digit |
| LEI Length | LEI | ERROR | Exactly 20 characters |
| LEI Format | LEI | WARNING | 18 alphanumeric + 2 check digits |
| BIC Length | BIC | ERROR | 8 or 11 characters |

### Pattern 7: Currency Validations

Validates currency codes and Amount elements.

| Rule | Context | Severity | Description |
|------|---------|----------|-------------|
| Currency Code | `Currency`, `@ccy` | WARNING | Must be 3-letter ISO 4217 code |
| Amount Currency | `Amount` | ERROR | All Amount elements must have @ccy attribute |

## Running the Validation

### Prerequisites

1. Install Saxon-HE (see [parent README](../README.md) for installation)
2. Download SchXslt for Schematron compilation

### Quick Start

#### Using Saxon + SchXslt (Recommended)

```bash
# Download SchXslt
git clone https://github.com/schxslt/schxslt.git

# Validate
java -jar saxon-he.jar \
    -xsl:schxslt/2.0/pipeline-for-svrl.xsl \
    -s:../../FundsXML_Files/4.2.9/Mixed-Fund_Positions.xml \
    sch.file=basic_checks.sch \
    -o:validation_report.xml
```

#### Two-Step Process

```bash
# Step 1: Compile Schematron to XSLT
java -jar saxon-he.jar \
    -s:basic_checks.sch \
    -xsl:schxslt/2.0/include.xsl \
    -o:basic_checks_compiled.xsl

# Step 2: Run validation
java -jar saxon-he.jar \
    -s:../../FundsXML_Files/4.2.9/Mixed-Fund_Positions.xml \
    -xsl:basic_checks_compiled.xsl \
    -o:validation_report.xml
```

### Platform-Specific Examples

#### Windows (PowerShell)

```powershell
# Set paths
$SAXON = "C:\saxon\saxon-he.jar"
$SCHXSLT = "C:\schxslt\2.0\pipeline-for-svrl.xsl"
$INPUT = "..\..\FundsXML_Files\4.2.9\Mixed-Fund_Positions.xml"

# Run validation
java -jar $SAXON `
    -xsl:$SCHXSLT `
    -s:$INPUT `
    sch.file=basic_checks.sch `
    -o:validation_report.xml

# Display results summary
$report = [xml](Get-Content validation_report.xml)
$errors = $report.SelectNodes("//*[local-name()='failed-assert']").Count
$warnings = $report.SelectNodes("//*[local-name()='successful-report']").Count
Write-Host "Errors: $errors, Warnings: $warnings"
```

#### macOS / Linux (Bash)

```bash
#!/bin/bash
SAXON_JAR="${SAXON_JAR:-/opt/saxon/saxon-he.jar}"
SCHXSLT="${SCHXSLT:-/opt/schxslt/2.0/pipeline-for-svrl.xsl}"
INPUT="${1:-../../FundsXML_Files/4.2.9/Mixed-Fund_Positions.xml}"
OUTPUT="${2:-validation_report.xml}"

java -jar "$SAXON_JAR" \
    -xsl:"$SCHXSLT" \
    -s:"$INPUT" \
    sch.file=basic_checks.sch \
    -o:"$OUTPUT"

# Count results
echo "Errors: $(grep -c 'failed-assert' "$OUTPUT")"
echo "Warnings: $(grep -c 'successful-report' "$OUTPUT")"
```

## Understanding the Output

### SVRL (Schematron Validation Report Language)

The validation produces an SVRL report in XML format:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<svrl:schematron-output xmlns:svrl="http://purl.oclc.org/dsdl/svrl">
    <svrl:active-pattern name="Structural Integrity Checks"/>

    <!-- Passed assertion (no output normally) -->

    <!-- Failed assertion (ERROR) -->
    <svrl:failed-assert test="Identifiers/ISIN"
                        location="/FundsXML4/AssetMasterData/Asset[3]"
                        role="error">
        <svrl:text>ERROR: EQ asset "Example Stock" must have an ISIN identifier</svrl:text>
    </svrl:failed-assert>

    <!-- Successful report (WARNING/INFO) -->
    <svrl:successful-report test="$difference >= 0.01 and $difference &lt; 1"
                            location="/FundsXML4/Funds/Fund[1]"
                            role="warning">
        <svrl:text>WARNING: Small rounding difference detected. Difference: 0.50 EUR</svrl:text>
    </svrl:successful-report>
</svrl:schematron-output>
```

### Key Elements

| Element | Meaning |
|---------|---------|
| `svrl:failed-assert` | Validation rule failed (ERROR) |
| `svrl:successful-report` | Report condition triggered (WARNING/INFO) |
| `@location` | XPath to the element that triggered the message |
| `@test` | The XPath expression that was evaluated |
| `@role` | Severity level (error, warning, info) |
| `svrl:text` | Human-readable message |

### Parsing Results

#### Python

```python
import xml.etree.ElementTree as ET

tree = ET.parse('validation_report.xml')
ns = {'svrl': 'http://purl.oclc.org/dsdl/svrl'}

errors = tree.findall('.//svrl:failed-assert', ns)
warnings = tree.findall('.//svrl:successful-report', ns)

print(f"Errors: {len(errors)}")
for err in errors:
    print(f"  {err.find('svrl:text', ns).text}")

print(f"\nWarnings: {len(warnings)}")
for warn in warnings:
    print(f"  {warn.find('svrl:text', ns).text}")
```

#### Java

```java
import javax.xml.parsers.*;
import org.w3c.dom.*;

DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
factory.setNamespaceAware(true);
Document doc = factory.newDocumentBuilder().parse("validation_report.xml");

NodeList errors = doc.getElementsByTagNameNS(
    "http://purl.oclc.org/dsdl/svrl", "failed-assert");
NodeList warnings = doc.getElementsByTagNameNS(
    "http://purl.oclc.org/dsdl/svrl", "successful-report");

System.out.println("Errors: " + errors.getLength());
System.out.println("Warnings: " + warnings.getLength());
```

## Customization

### Adding New Rules

To add a new validation rule:

```xml
<pattern id="my-custom-checks">
    <title>Custom Validation Rules</title>

    <rule context="Fund">
        <!-- Assert: condition must be true, otherwise error -->
        <assert test="FundStaticData/InceptionDate" role="warning">
            WARNING: Fund should have an inception date
        </assert>

        <!-- Report: condition triggers message when true -->
        <report test="number(FundDynamicData/TotalAssetValues/TotalAssetValue/TotalNetAssetValue/Amount) > 1000000000" role="info">
            INFO: Fund has over 1 billion in assets
        </report>
    </rule>
</pattern>
```

### Adjusting Tolerance Levels

Modify the tolerance variables in the .sch file:

```xml
<!-- Original: 1 currency unit tolerance -->
<assert test="$difference &lt; 1" role="error">

<!-- Stricter: 0.01 currency unit tolerance -->
<assert test="$difference &lt; 0.01" role="error">

<!-- Looser: 10 currency unit tolerance -->
<assert test="$difference &lt; 10" role="error">
```

### Custom Error Messages

Use `value-of` to include dynamic values:

```xml
<assert test="$sum = 100" role="error">
    ERROR: Percentages sum to <value-of select="format-number($sum, '0.00')"/>%
    instead of 100%. Difference: <value-of select="format-number(abs($sum - 100), '0.00')"/>%
</assert>
```

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| "QueryBinding not supported" | XSLT 1.0 processor | Use Saxon-HE or other XSLT 2.0 processor |
| "Unknown function: abs" | Wrong XPath version | Ensure queryBinding="xslt2" |
| "No matching template" | Compilation issue | Verify SchXslt installation |
| Empty report | Document doesn't match patterns | Check document structure and namespaces |

### Namespace Issues

If your FundsXML uses a namespace:

```xml
<!-- Document with namespace -->
<FundsXML4 xmlns="http://www.fundsxml.org/4.0">

<!-- Schematron must declare and use it -->
<schema xmlns="http://purl.oclc.org/dsdl/schematron"
        xmlns:fx="http://www.fundsxml.org/4.0">
    <ns prefix="fx" uri="http://www.fundsxml.org/4.0"/>

    <rule context="fx:Fund">
        <assert test="fx:Identifiers/fx:LEI">...</assert>
    </rule>
</schema>
```

### Debug Mode

Add diagnostic output:

```xml
<pattern id="debug">
    <rule context="Fund">
        <report test="true()" role="info">
            DEBUG: Processing Fund: <value-of select="Names/OfficialName"/>
            Currency: <value-of select="Currency"/>
            NAV: <value-of select="FundDynamicData/TotalAssetValues/TotalAssetValue/TotalNetAssetValue/Amount"/>
        </report>
    </rule>
</pattern>
```

## Validation Rule Details

### NAV Calculation Formula

```
Fund Total NAV = Σ (ShareClass NAV)
ShareClass NAV = Price × Shares Outstanding
Position Sum = Fund Total NAV
Percentage Sum = 100%
```

### ISIN Format Regex

```
^[A-Z]{2}[A-Z0-9]{9}[0-9]$
```
- Positions 1-2: Country code (letters)
- Positions 3-11: NSIN (alphanumeric)
- Position 12: Check digit (numeric)

### LEI Format Regex

```
^[A-Z0-9]{18}[0-9]{2}$
```
- Positions 1-18: Entity identifier (alphanumeric)
- Positions 19-20: Check digits (numeric)

## Resources

- [ISO Schematron Specification](http://schematron.com)
- [SchXslt Documentation](https://github.com/schxslt/schxslt)
- [FundsXML Schema](https://github.com/fundsxml/schema)
- [Parent Schematron README](../README.md)
