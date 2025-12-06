# FundsXML Sample Files

This directory contains sample FundsXML documents demonstrating the standard's structure and capabilities.

## What is FundsXML?

FundsXML is an open, vendor-neutral XML standard for the exchange of fund data in the investment management industry. Developed and maintained by the [FundsXML Working Group](https://www.fundsxml.org), it provides a comprehensive data model for representing:

- **Fund master data** - Legal entity information, identifiers, domicile
- **Share class details** - ISINs, pricing, distributions
- **Portfolio holdings** - Positions, valuations, exposures
- **Asset information** - Instrument details for all asset types
- **Dynamic data** - NAVs, performance, flows

### Industry Adoption

FundsXML is widely used across Europe and increasingly globally by:
- Asset managers
- Fund administrators
- Custodian banks
- Data vendors
- Regulatory reporting systems
- Risk management platforms

## FundsXML Document Structure

A FundsXML document follows a hierarchical structure:

```xml
<FundsXML4>
    <ControlData>           <!-- Document metadata -->
    <Funds>                 <!-- Fund definitions -->
        <Fund>
            <Identifiers>   <!-- LEI, proprietary IDs -->
            <Names>         <!-- Official name, translations -->
            <Currency>      <!-- Base currency -->
            <FundStaticData>    <!-- Inception date, costs -->
            <FundDynamicData>   <!-- NAV, portfolios -->
                <TotalAssetValues>
                <Portfolios>
                    <Portfolio>
                        <Positions>
            <SingleFund>
                <ShareClasses>  <!-- Share class details -->
    <AssetMasterData>       <!-- Asset definitions -->
        <Asset>
            <Identifiers>   <!-- ISIN, SEDOL, etc. -->
            <AssetType>     <!-- EQ, BO, OP, etc. -->
            <AssetDetails>  <!-- Type-specific details -->
</FundsXML4>
```

### Key Sections

#### ControlData
Document-level metadata including:
- `UniqueDocumentID` - Unique identifier for the file
- `DocumentGenerated` - Timestamp of generation
- `Version` - FundsXML schema version
- `ContentDate` - Business date of the data
- `DataSupplier` - Source organization information

#### Funds/Fund
Fund-level information:
- **Identifiers** - LEI (Legal Entity Identifier), proprietary codes
- **Names** - Official name, short name, translations
- **Currency** - Base currency (ISO 4217)
- **FundStaticData** - Inception date, ongoing costs, legal structure
- **FundDynamicData** - NAV data, portfolio holdings

#### ShareClasses
Share class details including:
- **Identifiers** - ISIN, SEDOL, WKN
- **Prices** - NAV price, issue/redemption prices
- **TotalAssetValues** - Share class level NAV

#### AssetMasterData
Detailed asset definitions:
- **Identifiers** - ISIN, LEI, Bloomberg ticker
- **AssetType** - Classification code
- **AssetDetails** - Instrument-specific attributes

## Asset Type Codes

FundsXML uses standardized codes for asset classification:

| Code | Type | Description | Key Attributes |
|------|------|-------------|----------------|
| **EQ** | Equity | Stocks, shares | Issuer, exchange, sector |
| **BO** | Bond | Fixed income | Coupon, maturity, issuer |
| **SC** | ShareClass | Fund investments | Underlying fund, share class |
| **OP** | Option | Options contracts | Strike, expiry, underlying |
| **FU** | Future | Futures contracts | Contract size, expiry |
| **FX** | FX Forward | Currency forwards | Currencies, amounts, maturity |
| **SW** | Swap | Swap contracts | Type, legs, counterparty |
| **WA** | Warrant | Warrants | Strike, expiry, type |
| **CE** | Certificate | Structured products | Type, underlying |
| **AC** | Account | Bank accounts | Counterparty, account type |
| **RP** | Repo | Repurchase agreements | Collateral, counterparty |
| **RE** | Real Estate | Property | Location, type, valuation |
| **CM** | Call Money | Short-term deposits | Counterparty, maturity |
| **OT** | Other | Other assets | Custom attributes |

## Version History

| Version | Status | Key Features |
|---------|--------|--------------|
| 4.2.9 | Current | Enhanced derivative support, ESG fields |
| 4.2.x | Stable | Improved exposure reporting |
| 4.1.x | Legacy | Added cost transparency fields |
| 4.0.x | Legacy | Major restructuring from 3.x |

## Schema Validation

FundsXML documents should be validated against the official XSD schema:

### Download Schema

```bash
# Get the official schema for version 4.2.9
curl -O https://github.com/fundsxml/schema/releases/download/4.2.9/FundsXML.xsd
```

### Validate with xmllint (macOS/Linux)

```bash
xmllint --schema FundsXML.xsd FundsXML_Files/4.2.9/Mixed-Fund_Positions.xml --noout
```

### Validate with Saxon

```bash
saxon -s:Mixed-Fund_Positions.xml -xsd:FundsXML.xsd -o:validation-report.xml
```

### Validate with Python

```python
from lxml import etree

# Load schema
with open('FundsXML.xsd', 'rb') as f:
    schema_doc = etree.parse(f)
    schema = etree.XMLSchema(schema_doc)

# Validate document
with open('Mixed-Fund_Positions.xml', 'rb') as f:
    doc = etree.parse(f)

if schema.validate(doc):
    print("Document is valid")
else:
    print("Validation errors:")
    for error in schema.error_log:
        print(f"  Line {error.line}: {error.message}")
```

### Validate with Java

```java
import javax.xml.validation.*;
import javax.xml.transform.stream.StreamSource;
import java.io.File;

SchemaFactory factory = SchemaFactory.newInstance(XMLConstants.W3C_XML_SCHEMA_NS_URI);
Schema schema = factory.newSchema(new File("FundsXML.xsd"));
Validator validator = schema.newValidator();

try {
    validator.validate(new StreamSource(new File("Mixed-Fund_Positions.xml")));
    System.out.println("Document is valid");
} catch (SAXException e) {
    System.out.println("Validation error: " + e.getMessage());
}
```

### Validate with .NET/C#

```csharp
using System.Xml;
using System.Xml.Schema;

var settings = new XmlReaderSettings();
settings.Schemas.Add(null, "FundsXML.xsd");
settings.ValidationType = ValidationType.Schema;
settings.ValidationEventHandler += (sender, e) => {
    Console.WriteLine($"Validation {e.Severity}: {e.Message}");
};

using var reader = XmlReader.Create("Mixed-Fund_Positions.xml", settings);
while (reader.Read()) { }
Console.WriteLine("Validation complete");
```

## Available Samples

| Version | File | Description |
|---------|------|-------------|
| [4.2.9](./4.2.9/) | Mixed-Fund_Positions.xml | Comprehensive example with 21 diverse positions |

## External Resources

- **Official Website**: [https://www.fundsxml.org](https://www.fundsxml.org)
- **Schema Repository**: [https://github.com/fundsxml/schema](https://github.com/fundsxml/schema)
- **Working Group**: Contact via fundsxml.org for membership
- **Release Notes**: Available in schema repository

## Troubleshooting

### Common Schema Validation Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Element 'xxx' is not expected` | Wrong element order | Check schema for correct sequence |
| `Value 'xxx' is not valid` | Invalid enumeration | Use allowed values from schema |
| `Missing required element` | Required field absent | Add mandatory elements |
| `Invalid date format` | Wrong date format | Use ISO 8601 (YYYY-MM-DD) |

### Namespace Issues

FundsXML 4.x uses no namespace by default. If your document has namespace issues:

```xml
<!-- Correct: No namespace -->
<FundsXML4 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
           xsi:noNamespaceSchemaLocation="FundsXML.xsd">

<!-- Incorrect: Adding a namespace -->
<FundsXML4 xmlns="http://www.fundsxml.org/4.0">  <!-- Don't do this -->
```
