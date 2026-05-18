# FundsXML 4.0.0 — Equity-Fund Positions Example

![Version](https://img.shields.io/badge/FundsXML-4.0.0-blue) ![validated](https://img.shields.io/badge/XSD-valid-brightgreen)

| Property | Value |
|----------|-------|
| **File** | `Equity-Fund_Positions.xml` |
| **Schema version** | FundsXML 4.0.0 |
| **Validated against** | `https://github.com/fundsxml/schema/releases/download/4.0.0/FundsXML.xsd` |
| **Purpose** | Oldest supported release, version comparison |

## Contents

Content-identical to the 4.1.0 example (3 equity positions), but adapted to the
4.0.0 schema rules.

## Version differences (important!)

- ❗ **4.0.0 `ControlData` has NO `<Version>` element** — that was introduced in
  4.1.0. The version here is only visible via `xsi:noNamespaceSchemaLocation`
  and the header comment. An inserted `<Version>` would break validation
  (`Element 'Version': This element is not expected`).
- The 4.0.0 release ships a self-contained `FundsXML.xsd`.
- Despite header differences, the positions/asset structure is stable across
  versions (backward compatibility).

## Validation

```bash
# Give the validator the schema (the official 4.0.0 release URL — or a local
# FundsXML.xsd path) + the XML file:
XSD_Validation/cli/validate.sh \
        https://github.com/fundsxml/schema/releases/download/4.0.0/FundsXML.xsd \
        FundsXML_Files/4.0.0/positions/Equity-Fund_Positions.xml
```
