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

**Schema resolution (same convention in every stack):**
`$FUNDSXML_SCHEMA_DIR` (a hand-placed copy — offline / corporate-network
escape hatch) → `.schema-cache/<version>/` → download from the official
GitHub release (302-aware; also pulls the imported `xmldsig-core-schema.xsd`),
caching into `.schema-cache/`. The official release stays the source of truth
— no committed catalog.

The **Java** (`XsdValidate`), **Python** (`validate.py`) and **.NET**
(`XsdValidate.cs` + `SchemaResolver.cs`) examples do this themselves —
standalone, cross-platform, no prior step. `tools/fetch-schema.sh` still seeds
the cache for the CLI/xmllint and (until its phase lands) PowerShell stacks:

```bash
tools/fetch-schema.sh 4.2.9          # only needed for the CLI/PowerShell stacks
```

## Security

Every example disables external entity resolution / DTD loading
(`FEATURE_SECURE_PROCESSING`, `resolve_entities=False`, `XmlResolver=null`,
`-nonet`) — FundsXML never needs them and they are a classic XXE vector.

## Stacks

| Stack | Script | API | Runnable on this box |
|-------|--------|-----|----------------------|
| CLI | [`cli/validate.sh`](cli/validate.sh) | `xmllint` (+ Saxon note) | ✅ |
| Python | [`python/validate.py`](python/validate.py) | `lxml.etree.XMLSchema` | ✅ standalone (`pip install -e .`) |
| Java | [`java/XsdValidate.java`](java/XsdValidate.java) | `javax.xml.validation` | ✅ standalone (`./mvnw`) |
| .NET/C# | [`dotnet/XsdValidate.cs`](dotnet/XsdValidate.cs) | `XmlSchemaSet` | ✅ standalone (`dotnet run`) |
| PowerShell | [`powershell/Validate-FundsXml.ps1`](powershell/Validate-FundsXml.ps1) | `System.Xml.Schema` | needs PowerShell |

Convention: each takes `<version> <xml-file>`, exits `0` on valid, `1` on
invalid, prints errors to stderr.

## Quick check (positive + negative)

Python (standalone — resolves the schema itself; `pip install -e .` once, see
the repo `pyproject.toml`):

```bash
python -m venv .venv && . .venv/bin/activate && pip install -e .   # Windows: .venv\Scripts\activate
python XSD_Validation/python/validate.py 4.2.9 FundsXML_Files/4.2.9/positions/Mixed-Fund_Positions.xml  # exit 0
python XSD_Validation/python/validate.py 4.2.9 tests/fixtures/invalid/xsd-invalid_Positions.xml         # exit 1
```

Java (standalone): `./mvnw -q -pl XSD_Validation/java compile exec:java -Dexec.args="4.2.9 <file>"`
(`mvnw.cmd` on Windows).

.NET (standalone): `dotnet run --project XSD_Validation/dotnet -- 4.2.9 <file>`
(exit 0 valid / 1 invalid).

The CLI/`xmllint` stack still uses `tools/fetch-schema.sh 4.2.9` until its
phase lands.
