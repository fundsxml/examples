# FundsXML 4.2.9 — Documents Example

![Version](https://img.shields.io/badge/FundsXML-4.2.9-blue) ![validated](https://img.shields.io/badge/XSD-valid-brightgreen)

| Property | Value |
|----------|-------|
| **File** | `Fund_Documents.xml` |
| **Schema version** | FundsXML 4.2.9 |
| **Validated against** | `https://github.com/fundsxml/schema/releases/download/4.2.9/FundsXML.xsd` |
| **Purpose** | Reference or embed fund documents |

## Contents

Top-level `<Documents>` with two `Document` entries:

| Type (ListedType) | Delivery | Note |
|-------------------|----------|------|
| `Factsheet` | `DocumentURL` (link) | public PDF, linked |
| `PRIIPS-KID` | `BinaryData` (base64) | embedded PDF stub, with `ExpirationDate` |

Required fields per document: `Type`, `Language`, `Format`. Link to the fund
via `Document/Fund/Identifiers/LEI`.

## Validation

```bash
python -m fundsxml_schema 4.2.9   # caches the XSD into .schema-cache/ (run `pip install -e .` once; cross-platform)
xmllint --noout --schema .schema-cache/4.2.9/FundsXML.xsd \
        FundsXML_Files/4.2.9/documents/Fund_Documents.xml
```
