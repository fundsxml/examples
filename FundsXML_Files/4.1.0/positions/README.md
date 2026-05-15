# FundsXML 4.1.0 — Equity-Fund Positions Example

![Version](https://img.shields.io/badge/FundsXML-4.1.0-blue) ![validated](https://img.shields.io/badge/XSD-valid-brightgreen)

| Property | Value |
|----------|-------|
| **File** | `Equity-Fund_Positions.xml` |
| **Schema version** | FundsXML 4.1.0 |
| **Validated against** | `https://github.com/fundsxml/schema/releases/download/4.1.0/FundsXML.xsd` |
| **Purpose** | Compact positions example on an older, still-valid version |

## Contents

Pure equity fund with 3 positions (ASML, Sanofi, SAP), summing to 100 %,
EUR 40m NAV. Deliberately small to make the version comparison easy.

## Version differences

- **4.1.0** has — like 4.2.9 — a `ControlData/Version` element.
- The **4.1.0 release** ships only a self-contained `FundsXML.xsd`
  (no separate `xmldsig-core-schema.xsd` import as from 4.2.9).
- FundsXML is backward compatible: this structure also validates against 4.2.9.

## Validation

```bash
tools/fetch-schema.sh 4.1.0
xmllint --noout --schema .schema-cache/4.1.0/FundsXML.xsd \
        FundsXML_Files/4.1.0/positions/Equity-Fund_Positions.xml
```
