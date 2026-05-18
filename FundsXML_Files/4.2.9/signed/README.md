# FundsXML 4.2.9 — Signed File (Skeleton)

![Version](https://img.shields.io/badge/FundsXML-4.2.9-blue) ![validated](https://img.shields.io/badge/XSD-valid-brightgreen) ![Signature](https://img.shields.io/badge/XMLDSig-placeholder-orange)

| Property | Value |
|----------|-------|
| **File** | `Signed_Fund_Skeleton.xml` |
| **Schema version** | FundsXML 4.2.9 |
| **Validated against** | `https://github.com/fundsxml/schema/releases/download/4.2.9/FundsXML.xsd` |
| **Purpose** | Structure of an enveloped-XMLDSig-signed FundsXML file |

## Contents

`ds:Signature` (namespace `http://www.w3.org/2000/09/xmldsig#`) is the **last
optional child** of `<FundsXML4>`. From release 4.2.9 on, `FundsXML.xsd` imports
`xmldsig-core-schema.xsd` for this — the validators fetch that sibling
alongside `FundsXML.xsd` when you pass the release URL (and it sits next to a
local `FundsXML.xsd` in any complete copy of the release).

> ⚠️ **Placeholder:** `DigestValue` and `SignatureValue` are schema-valid base64
> strings but **not cryptographically verifiable**. Real signing and
> verification (Apache Santuario / .NET `SignedXml` / `xmlsec1` / Python
> `signxml`) follows in **Phase 3** under `XML_Signature/`.

Algorithms used (enveloped signature): C14N 2001-03-15, RSA-SHA256, SHA-256.

## Validation

```bash
# Give the validator the schema (the official 4.2.9 release URL — or a local
# FundsXML.xsd path) + the XML file; the xmldsig sibling is handled for you:
XSD_Validation/cli/validate.sh \
        https://github.com/fundsxml/schema/releases/download/4.2.9/FundsXML.xsd \
        FundsXML_Files/4.2.9/signed/Signed_Fund_Skeleton.xml
```
