# FundsXML 4.2.9 — Transactions Example

![Version](https://img.shields.io/badge/FundsXML-4.2.9-blue) ![validated](https://img.shields.io/badge/XSD-valid-brightgreen)

| Property | Value |
|----------|-------|
| **File** | `Fund_Transactions.xml` |
| **Schema version** | FundsXML 4.2.9 |
| **Validated against** | `https://github.com/fundsxml/schema/releases/download/4.2.9/FundsXML.xsd` |
| **Purpose** | Demonstrate portfolio transactions (buys/sells/cash) |

## Contents

`FundDynamicData/Portfolios/Portfolio/Transactions` with three `Transaction`
records:

| TransactionID | Kind | Asset (IDREF) | Nominal/Units | Description |
|---------------|------|---------------|---------------|-------------|
| TXN_2025_0001 | BUY  | ID_001 (Apple) | 10,000 | Equity purchase |
| TXN_2025_0002 | SELL | ID_002 (ASML)  | 1,250  | Partial equity sale |
| TXN_2025_0003 | CASH | –              | 500,000 | Cash inflow (subscription) |

`AssetUniqueID` is an `xs:IDREF` referencing `Asset/UniqueID` in
`AssetMasterData` — the same linking mechanism used by positions.

## Validation

```bash
# Give the validator the schema (the official 4.2.9 release URL — or a local
# FundsXML.xsd path) + the XML file; the xmldsig sibling is handled for you:
XSD_Validation/cli/validate.sh \
        https://github.com/fundsxml/schema/releases/download/4.2.9/FundsXML.xsd \
        FundsXML_Files/4.2.9/transactions/Fund_Transactions.xml
```

See [`XSD_Validation/`](../../../XSD_Validation/) for invocations in Python,
Java, .NET, PowerShell and CLI.
