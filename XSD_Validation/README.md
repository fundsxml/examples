# XSD Validation

Validate a FundsXML document against the **official released schema** in five
enterprise stacks. Same input, same result everywhere.

## The schema source

Validation always targets the official release:

```
https://github.com/fundsxml/schema/releases/download/<version>/FundsXML.xsd
```

This is **not** a hand-maintained catalog — it is the canonical released schema.
Two realities every example must deal with:

1. **HTTP 302 redirect.** The GitHub URL redirects to
   `objects.githubusercontent.com`. Processors with a naive HTTP client
   (libxml2/xmllint) do not follow it. On locked-down enterprise networks the
   download also goes through an HTTP proxy.
2. **Relative import.** From release 4.2.9 on, `FundsXML.xsd` imports
   `xmldsig-core-schema.xsd` via a *relative* path; both files must sit together.

`tools/fetch-schema.sh <version>` resolves both (proxy-aware via curl) and
materializes the released schema into `.schema-cache/<version>/`. The examples
validate against that materialized release. Run it once up front:

```bash
tools/fetch-schema.sh 4.2.9
```

## Security

Every example disables external entity resolution / DTD loading
(`FEATURE_SECURE_PROCESSING`, `resolve_entities=False`, `XmlResolver=null`,
`-nonet`) — FundsXML never needs them and they are a classic XXE vector.

## Stacks

| Stack | Script | API | Runnable on this box |
|-------|--------|-----|----------------------|
| CLI | [`cli/validate.sh`](cli/validate.sh) | `xmllint` (+ Saxon note) | ✅ |
| Python | [`python/validate.py`](python/validate.py) | `lxml.etree.XMLSchema` | ✅ |
| Java | [`java/XsdValidate.java`](java/XsdValidate.java) | `javax.xml.validation` | ✅ (single-file, JDK 11+) |
| .NET/C# | [`dotnet/XsdValidate.cs`](dotnet/XsdValidate.cs) | `XmlSchemaSet` | needs .NET SDK |
| PowerShell | [`powershell/Validate-FundsXml.ps1`](powershell/Validate-FundsXml.ps1) | `System.Xml.Schema` | needs PowerShell |

Convention: each takes `<version> <xml-file>`, exits `0` on valid, `1` on
invalid, prints errors to stderr.

## Quick check (positive + negative)

```bash
tools/fetch-schema.sh 4.2.9
XSD_Validation/cli/validate.sh 4.2.9 FundsXML_Files/4.2.9/positions/Mixed-Fund_Positions.xml   # exit 0
XSD_Validation/cli/validate.sh 4.2.9 tests/fixtures/invalid/xsd-invalid_Positions.xml          # exit 1
```
