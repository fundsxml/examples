# FundsXML 4.2.9 Sample: Mixed-Fund with Positions

This directory contains a comprehensive FundsXML sample document demonstrating all major asset types and structural elements.

## File Overview

| Property | Value |
|----------|-------|
| **File** | `Mixed-Fund_Positions.xml` |
| **Schema Version** | FundsXML 4.2.9 |
| **Size** | ~830 lines |
| **Purpose** | Demonstrate diverse asset types and complete FundsXML structure |

## Sample Data Summary

### Fund Information

| Field | Value |
|-------|-------|
| Fund Name | Erste Responsible Stock Global |
| LEI | 529900T8BM49AURSDO55 |
| Base Currency | EUR |
| NAV Date | 2025-10-01 |
| Total Net Asset Value | 125,000,000 EUR |
| Data Supplier | Erste Asset Management GmbH |
| Country | Austria (AT) |
| Inception Date | 2015-03-15 |
| Ongoing Costs | 1.80% |

### Share Classes

| ISIN | Name | Currency | NAV Price |
|------|------|----------|-----------|
| AT0000A2QM74 | Erste Responsible Stock Global USD R01 | USD | 142.87 |
| AT0000A2QM66 | Erste Responsible Stock Global EUR R01 | EUR | 134.25 |

### Portfolio Summary

- **Total Positions**: 21
- **Asset Types**: 13 different types
- **Currencies**: EUR, USD

## Asset Types Demonstrated

This sample file includes examples of all major FundsXML asset types:

| # | Type Code | Asset Type | Count | Example Position(s) |
|---|-----------|------------|-------|---------------------|
| 1 | **EQ** | Equity | 2 | Apple Inc. (US0378331005), ASML (NL0010273215) |
| 2 | **BO** | Bond | 2 | German Govt 1.70% 2032, Siemens 0.75% 2030 |
| 3 | **SC** | ShareClass (Fund) | 2 | PIMCO GIS Global Bond, Vanguard S&P 500 ETF |
| 4 | **WA** | Warrant | 2 | BNP Call on LVMH, SocGen Put on SAP |
| 5 | **CE** | Certificate | 2 | X-markets DAX Index, DZ Bank Euro Stoxx |
| 6 | **OP** | Option | 2 | Call on Allianz, Put on Volkswagen |
| 7 | **FU** | Future | 2 | Euro Stoxx 50 Dec 2025, EUR/USD Mar 2026 |
| 8 | **FX** | FX Forward | 2 | EUR/USD Dec 2025, EUR/GBP Jan 2026 |
| 9 | **SW** | Swap | 2 | 5Y Interest Rate Swap, Cross Currency EUR/CHF |
| 10 | **RP** | Repo | 1 | German Government Bond Repo |
| 11 | **RE** | Real Estate | 1 | Office Building Vienna Donaucity |
| 12 | **CM** | Call Money | 1 | Raiffeisen Bank International |

### Position Details

| ID | ISIN | Name | Type | Value (EUR) | % |
|----|------|------|------|-------------|---|
| ID_001 | US0378331005 | Apple Inc. | EQ | 9,375,000 | 7.50% |
| ID_002 | NL0010273215 | ASML Holding N.V. | EQ | 8,125,000 | 6.50% |
| ID_003 | DE0001102424 | Germany 1.70% 2032 | BO | 6,250,000 | 5.00% |
| ID_004 | XS2444622110 | Siemens 0.75% 2030 | BO | 6,250,000 | 5.00% |
| ID_005 | IE00B11XZB12 | PIMCO GIS Global Bond | SC | 10,000,000 | 8.00% |
| ID_006 | IE00B5BMR087 | Vanguard S&P 500 ETF | SC | 12,500,000 | 10.00% |
| ID_007 | DE000PN738Q3 | BNP Call Warrant LVMH | WA | 1,875,000 | 1.50% |
| ID_008 | DE000SQ962F7 | SocGen Put Warrant SAP | WA | 1,875,000 | 1.50% |
| ID_009 | DE000XM03HC3 | X-markets DAX Index Cert | CE | 3,125,000 | 2.50% |
| ID_010 | DE000DFM0XG2 | DZ Bank Euro Stoxx Cert | CE | 3,125,000 | 2.50% |
| ID_011 | DE000C0B6XV0 | Call Option Allianz | OP | 1,250,000 | 1.00% |
| ID_012 | DE000C0B6YC8 | Put Option Volkswagen | OP | 1,250,000 | 1.00% |
| ID_013 | DE000C0B6ZR4 | Euro Stoxx 50 Future | FU | 2,500,000 | 2.00% |
| ID_014 | XS2123456789 | EUR/USD Currency Future | FU | 2,500,000 | 2.00% |
| ID_015 | - | FX Forward EUR/USD | FX | 5,000,000 | 4.00% |
| ID_016 | - | FX Forward EUR/GBP | FX | 4,375,000 | 3.50% |
| ID_017 | - | EUR 5Y Interest Rate Swap | SW | 6,250,000 | 5.00% |
| ID_018 | - | Cross Currency Swap EUR/CHF | SW | 5,625,000 | 4.50% |
| ID_019 | - | Repo German Govt Bond | RP | 3,750,000 | 3.00% |
| ID_020 | - | Vienna Office Building | RE | 10,625,000 | 8.50% |
| ID_021 | - | Call Money Raiffeisen | CM | 6,875,000 | 5.50% |

**Total**: 125,000,000 EUR (100%)

## XML Structure Walkthrough

### ControlData Section

```xml
<ControlData>
    <UniqueDocumentID>FUNDSXML_FILE_1</UniqueDocumentID>
    <DocumentGenerated>2025-10-01T00:00:00</DocumentGenerated>
    <Version>4.2.9</Version>
    <ContentDate>2025-10-01</ContentDate>
    <DataSupplier>
        <SystemCountry>AT</SystemCountry>
        <Short>EURAM</Short>
        <Name>Erste Asset Management GmbH</Name>
        <Type>Asset Manager</Type>
    </DataSupplier>
    <DataOperation>INITIAL</DataOperation>
</ControlData>
```

### Fund Header

```xml
<Fund>
    <Identifiers>
        <LEI>529900T8BM49AURSDO55</LEI>
    </Identifiers>
    <Names>
        <OfficialName>Erste Responsible Stock Global</OfficialName>
    </Names>
    <Currency>EUR</Currency>
    <SingleFundFlag>true</SingleFundFlag>
    <!-- ... -->
</Fund>
```

### Position Example: Equity

```xml
<Position>
    <UniqueID>ID_001</UniqueID>
    <Identifiers>
        <ISIN>US0378331005</ISIN>
    </Identifiers>
    <Currency>USD</Currency>
    <TotalValue>
        <Amount ccy="EUR">9375000</Amount>
    </TotalValue>
    <TotalPercentage>7.50</TotalPercentage>
    <Equity>
        <Units>50000.00</Units>
        <Price>
            <Amount ccy="USD">202.50</Amount>
        </Price>
    </Equity>
</Position>
```

### Position Example: Bond

```xml
<Position>
    <UniqueID>ID_003</UniqueID>
    <Identifiers>
        <ISIN>DE0001102424</ISIN>
    </Identifiers>
    <Currency>EUR</Currency>
    <TotalValue>
        <Amount ccy="EUR">6250000</Amount>
    </TotalValue>
    <TotalPercentage>5.00</TotalPercentage>
    <Bond>
        <Nominal>6200000</Nominal>
        <Price>
            <Amount ccy="EUR">100.806</Amount>
        </Price>
    </Bond>
</Position>
```

### Position Example: Derivative (Swap)

```xml
<Position>
    <UniqueID>ID_017</UniqueID>
    <Currency>EUR</Currency>
    <TotalValue>
        <Amount ccy="EUR">6250000</Amount>
    </TotalValue>
    <TotalPercentage>5.00</TotalPercentage>
    <Swap/>
</Position>
```

### AssetMasterData Example: Equity

```xml
<Asset>
    <UniqueID>ID_001</UniqueID>
    <Identifiers>
        <ISIN>US0378331005</ISIN>
    </Identifiers>
    <Currency>USD</Currency>
    <Country>US</Country>
    <Name>APPLE INC.</Name>
    <AssetType>EQ</AssetType>
    <AssetDetails>
        <Equity>
            <Issuer>
                <Identifiers>
                    <LEI>HWUPKR0MPOU8FGXBT394</LEI>
                </Identifiers>
                <Name>APPLE INC.</Name>
            </Issuer>
        </Equity>
    </AssetDetails>
</Asset>
```

### AssetMasterData Example: Swap

```xml
<Asset>
    <UniqueID>ID_017</UniqueID>
    <Currency>EUR</Currency>
    <Name>EUR 5Y Interest Rate Swap</Name>
    <AssetType>SW</AssetType>
    <AssetDetails>
        <Swap>
            <Type>Interestrateswap</Type>
            <MaturityDate>2030-10-01</MaturityDate>
            <Counterparty>
                <Identifiers>
                    <LEI>549300V65Q6MY42G2B26</LEI>
                </Identifiers>
                <Name>J.P. Morgan SE</Name>
            </Counterparty>
            <Legs>
                <Leg>
                    <Type>SELL</Type>
                    <Currency>EUR</Currency>
                    <Notional>6250000</Notional>
                    <YieldDayConvention>30/360</YieldDayConvention>
                </Leg>
                <Leg>
                    <Type>BUY</Type>
                    <Currency>EUR</Currency>
                    <Notional>6250000</Notional>
                    <YieldType>Fixed Rate</YieldType>
                </Leg>
            </Legs>
        </Swap>
    </AssetDetails>
</Asset>
```

## Validation

This sample file can be validated using the tools in this repository:

### Schema Validation

```bash
# Download schema
curl -O https://github.com/fundsxml/schema/releases/download/4.2.9/FundsXML.xsd

# Validate with xmllint
xmllint --schema FundsXML.xsd Mixed-Fund_Positions.xml --noout
```

### Schematron Validation

```bash
# Using the Schematron rules in this repository
cd ../../Schematron_DataQuality_Checks/Basic_Checks/
# See Schematron README for execution instructions
```

### XSLT Data Quality Report

```bash
# Generate basic HTML report
saxon -s:Mixed-Fund_Positions.xml \
      -xsl:../../XSLT_DataQuality_Checks/Basic_Checks/basic_checks.xslt \
      -o:dq_report.html

# Generate comprehensive dashboard
xsltproc ../../XSLT_DataQuality_Checks/Enhanced_Check/FundsXML_CompleteDQReport_HTML.xsl \
         Mixed-Fund_Positions.xml > full_report.html
```

## Use Cases

This sample file is useful for:

1. **Parser Testing** - Test FundsXML parsers with diverse asset types
2. **Validation Development** - Develop and test validation rules
3. **Integration Testing** - Test data import/export pipelines
4. **Learning** - Understand FundsXML structure and conventions
5. **Documentation** - Reference for FundsXML implementation

## Notes

### Data Quality Considerations

This sample is designed to **pass all validation checks**:
- All percentages sum to exactly 100%
- All positions have values in fund currency (EUR)
- All required identifiers are present (LEI, ISIN where applicable)
- NAV dates are consistent

### Intentional Characteristics

- **Mixed currencies**: Positions in both EUR and USD
- **Complete AssetMasterData**: Every position has corresponding asset details
- **Derivatives with counterparties**: All OTC derivatives include counterparty LEI
- **Issuer information**: Equities and bonds include issuer details

### Modifications for Testing

To test error conditions, you can modify the file:

```xml
<!-- Test: Missing ISIN for Equity -->
<Asset>
    <AssetType>EQ</AssetType>
    <!-- Remove ISIN to trigger validation error -->
</Asset>

<!-- Test: Percentage sum != 100% -->
<Position>
    <TotalPercentage>8.00</TotalPercentage>  <!-- Change to break sum -->
</Position>

<!-- Test: Missing fund currency value -->
<TotalValue>
    <Amount ccy="USD">1000000</Amount>  <!-- Only USD, missing EUR -->
</TotalValue>
```
