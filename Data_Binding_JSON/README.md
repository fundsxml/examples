# Data Binding & JSON

![status](https://img.shields.io/badge/JSON%20round--trip%20%2B%20Java%20binding-verified-brightgreen)

Two recurring enterprise needs: exposing FundsXML to **JSON** APIs, and
**binding** FundsXML to typed objects.

## FundsXML ⇄ JSON (verified)

[`python/fundsxml_json.py`](python/fundsxml_json.py) — `to-json` / `from-json`
/ `roundtrip` (stdlib + lxml). Stable JSON shape
(`document` / `fund` / `shareClasses` / `positions` / `assets`); `from-json`
produces **XSD-valid** FundsXML 4.2.9. Lossless for the positions core,
intentionally lossy for issuer / derivative / regulatory detail (same scope
boundary as `Database_Integration/`).

```bash
python3 Data_Binding_JSON/python/fundsxml_json.py to-json \
  FundsXML_Files/4.2.9/positions/Mixed-Fund_Positions.xml fund.json
python3 Data_Binding_JSON/python/fundsxml_json.py roundtrip \
  FundsXML_Files/4.2.9/positions/Mixed-Fund_Positions.xml regenerated.xml
xmllint --noout --schema .schema-cache/4.2.9/FundsXML.xsd regenerated.xml
```

Verified: NAV, position count and percentage-sum preserved through
XML → JSON → XML.

## Binding: native vs. generated

[`java/NativeBinding.java`](java/NativeBinding.java) — **native Java, no JAXB**:
a thin hand-written binding over DOM + XPath into Java `record`s. Verified on
4.2.9 and 4.0.0 (FundsXML 4.x is backward compatible, so one binding spans
versions). This is the recommended default: the FundsXML schema is very large,
so a full generated model is heavy and brittle to maintain.

### Generated-binding references (when you do want codegen)

| Stack | Tool | Command (against the fetched schema) |
|-------|------|--------------------------------------|
| Java | JAXB `xjc` | `xjc -d src -p org.fundsxml.model .schema-cache/4.2.9/FundsXML.xsd` |
| Python | `xsdata` | `xsdata --package fundsxml.model .schema-cache/4.2.9/FundsXML.xsd` |
| .NET | `xsd.exe` / `XmlSerializer` | `xsd.exe /classes /namespace:FundsXml.Model .schema-cache\4.2.9\FundsXML.xsd` |

All three consume the **official released schema** fetched by
`tools/fetch-schema.sh` (which also pulls the imported `xmldsig-core-schema.xsd`
for 4.2.9). Trade-off: generated models are type-safe but regenerate on every
schema bump and produce thousands of classes; the native binding stays small
and version-tolerant. Pick per use case.

CI runs the JSON round-trip (XSD-validated, figures asserted) and the native
Java binding on every push.
