# XSD Validation

Validate a FundsXML document against an XSD in five enterprise stacks. You
give each validator exactly two things — **a schema and an XML file** — and
get a `VALID`/`INVALID` report. Same input, same result everywhere.

```
validate <schema> <xml-file>
```

`<schema>` is a path to an `FundsXML.xsd` **or a remote URL**. No version
argument, no environment variable, no cache, no resolver — whatever you point
at is used as-is. Argument order is schema-first (matching the Schematron /
XSLT / XQuery invocations in this repo).

## The schema source

The canonical schema is the official release:

```
https://github.com/fundsxml/schema/releases/download/<version>/FundsXML.xsd
```

Pass that URL directly and the validator uses it. Two realities each stack
handles:

1. **HTTP 302 redirect.** The GitHub release URL redirects to an opaque
   `objects.githubusercontent.com` blob URL. So a URL schema (and the
   relative sibling below) is fetched into a temp dir first by the Python,
   CLI `validate.sh`, CLI `validate.ps1`-with-xmllint and Java stacks, then
   validated locally; .NET and PowerShell `Validate-FundsXml.ps1` resolve the
   URL natively via an `XmlUrlResolver` (the original URL stays the import
   base, so the redirect is transparent). No version-based resolution and no
   on-disk cache anywhere.
2. **Relative import.** From release 4.2.9 on, `FundsXML.xsd` imports
   `xmldsig-core-schema.xsd` via a *relative* path. It must be reachable next
   to `<schema>` — it is in the official release directory, and the URL
   stacks fetch it alongside `FundsXML.xsd`. For a **local** schema path,
   keep the sibling next to it (any complete copy of a release has it).

## Security

The *instance* document is parsed with external entity resolution / DTD
loading disabled (`FEATURE_SECURE_PROCESSING`, `resolve_entities=False`,
`XmlResolver=null`, `--nonet`) — FundsXML never needs them and they are a
classic XXE vector. Only the trusted, caller-supplied schema is fetched over
the network.

## Stacks

| Stack | Script | API | URL schema handling |
|-------|--------|-----|---------------------|
| CLI (Linux/macOS) | [`cli/validate.sh`](cli/validate.sh) | `xmllint` (POSIX sh) | fetch to temp, validate `--nonet` |
| CLI (Windows) | [`cli/validate.ps1`](cli/validate.ps1) | `xmllint` or .NET fallback | fetch to temp (xmllint) / `XmlUrlResolver` (.NET) |
| Python | [`python/validate.py`](python/validate.py) | `lxml.etree.XMLSchema` | fetch to temp (libxml2 has no HTTP loader) |
| Java | [`java/XsdValidate.java`](java/XsdValidate.java) | `javax.xml.validation` | fetch to temp |
| .NET/C# | [`dotnet/XsdValidate.cs`](dotnet/XsdValidate.cs) | `XmlSchemaSet` | native `XmlUrlResolver` |
| PowerShell | [`powershell/Validate-FundsXml.ps1`](powershell/Validate-FundsXml.ps1) | `System.Xml.Schema` | native `XmlUrlResolver` |

Convention: each takes `<schema> <xml-file>`, exits `0` on valid, `1` on
invalid, `2` on usage/setup error; prints errors to stderr.

## Quick check (positive + negative)

A reusable schema reference (use a local path or the release URL — both work
identically):

```bash
REL=https://github.com/fundsxml/schema/releases/download/4.2.9/FundsXML.xsd
```

Python (standalone — `pip install -e .` once for `lxml`, see the repo
`pyproject.toml`):

```bash
python -m venv .venv && . .venv/bin/activate && pip install -e .   # Windows: .venv\Scripts\activate
python XSD_Validation/python/validate.py "$REL" FundsXML_Files/4.2.9/positions/Mixed-Fund_Positions.xml  # exit 0
python XSD_Validation/python/validate.py "$REL" tests/fixtures/invalid/xsd-invalid_Positions.xml         # exit 1
```

Java (standalone, JDK 11+ only — no Maven needed, the example has no
dependencies beyond the JDK):

```bash
java XSD_Validation/java/XsdValidate.java "$REL" FundsXML_Files/4.2.9/positions/Mixed-Fund_Positions.xml  # exit 0
java XSD_Validation/java/XsdValidate.java "$REL" tests/fixtures/invalid/xsd-invalid_Positions.xml         # exit 1
```

(Windows: `java XSD_Validation\java\XsdValidate.java <schema> <xml-file>`.)
The same class also runs through the Maven aggregator, which is what CI uses:
`./mvnw -q -pl XSD_Validation/java compile exec:java -Dexec.args="$REL <file>"`
(`mvnw.cmd` on Windows).

.NET (standalone): `dotnet run --project XSD_Validation/dotnet -- "$REL" <file>`
(exit 0 valid / 1 invalid).

CLI: `XSD_Validation/cli/validate.sh "$REL" <file>` (Linux/macOS) or
`pwsh XSD_Validation/cli/validate.ps1 "$REL" <file>` (Windows — uses
`xmllint` if present, else the built-in .NET validator). Swap `"$REL"` for a
local `FundsXML.xsd` path to validate fully offline.
