# FundsXML 4.2.9 — Regulatory Reporting Example (EFT)

![Version](https://img.shields.io/badge/FundsXML-4.2.9-blue) ![validated](https://img.shields.io/badge/XSD-valid-brightgreen)

| Property | Value |
|----------|-------|
| **File** | `EFT_Regulatory.xml` |
| **Schema version** | FundsXML 4.2.9 |
| **Validated against** | `https://github.com/fundsxml/schema/releases/download/4.2.9/FundsXML.xsd` |
| **Purpose** | Supervisory reporting via `RegulatoryReportings` |

## Contents

`RegulatoryReportings/DirectReporting/EFTs/EFT` (European Feeder/Flow Template).
Deliberately chosen because it is the **most compact** of the regulatory
FundsXML structures (EMT/EET/PRIIPS/TPT are considerably larger and will follow
as their own examples in later phases).

Mandatory blocks included:

- `DataSetInformation` → `ReportInformationAndScope` (version, generation/period
  dates, `ReferenceTargetMarket`)
- `SubmitterEntityInformation` and `ManufacturerEntityInformation`
  (name, identifier, identifier type, position in the distribution chain)
- `GeneralFinancialInstrumentInformation` (identification, name,
  `TotalNumberOfTransactions`)

## Validation

```bash
tools/fetch-schema.sh 4.2.9
xmllint --noout --schema .schema-cache/4.2.9/FundsXML.xsd \
        FundsXML_Files/4.2.9/regulatory/EFT_Regulatory.xml
```
