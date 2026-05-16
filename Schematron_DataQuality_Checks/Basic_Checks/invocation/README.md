# Schematron Invocation

Run `basic_checks.sch` against a FundsXML document from four stacks. Same
SVRL semantics and pass/fail definition everywhere.

## Why a Saxon-class processor is required

`basic_checks.sch` declares `queryBinding="xslt2"`. ISO Schematron is applied by
**compiling it to XSLT** (SchXslt does this) and running the result to produce an
**SVRL** report. That needs an XSLT 2.0 engine — Saxon. `xmllint`/`xsltproc`/
`lxml` (XSLT 1.0 only) **cannot** run this ruleset.

The SchXslt CLI jar (a self-contained runner that bundles its own Saxon) is a
Maven dependency of this module's `pom.xml`, resolved from Maven Central by the
committed Maven Wrapper — no prior fetch step, no `.lib/`.

## SVRL semantics & pass/fail

`svrl-summary.py` is the single source of truth, shared by every stack and CI:

| SVRL element | Meaning |
|--------------|---------|
| `svrl:failed-assert` `role="error"` | ERROR |
| `svrl:failed-assert` `role="warning"` | WARNING |
| `svrl:successful-report` | a `<report>` fired (WARNING/INFO) |

`--fail-on error` (default) exits 1 only on ERROR-role failures; `--fail-on any`
exits 1 on any failed-assert (including warnings).

> The canonical sample currently yields **0 errors + 12 warnings**. The
> warnings are advisory (4× the broad `ShareClass` rule also matching
> `AssetDetails/ShareClass`; 8× derivative assets without exposure info). The
> percentage-sum rule is now active — see
> [`../README.md`](../README.md#known-ruleset-fix).

## Stacks

| Stack | File | Runnable on this box |
|-------|------|----------------------|
| Java (native) | [`SchematronValidate.java`](SchematronValidate.java) | ✅ verified (SchXslt Java API, via Maven Wrapper) |
| Python | [`validate_schematron.py`](validate_schematron.py) | saxonche via repo venv (`pip install -e .`); SchXslt jar via `$FUNDSXML_SCHXSLT_JAR` or Maven local repo — reference variant |
| .NET/C# | [`SchematronValidate.cs`](SchematronValidate.cs) | SaxonHE via NuGet (`dotnet build`); SchXslt jar via `$FUNDSXML_SCHXSLT_JAR` or Maven local repo — reference variant |
| shared | [`svrl-summary.py`](svrl-summary.py) | ✅ classifier used by all + CI |

The Java example runs standalone and cross-platform via the committed Maven
Wrapper (`./mvnw`, or `mvnw.cmd` on Windows) from the repo root. The SchXslt
CLI dependency already bundles Saxon — this module deliberately does **not**
depend on the standalone `Saxon-HE` jar (the two need different
`org.xmlresolver` APIs), which is why it is its own Maven module.

## Quick check (positive + negative)

```bash
SCH=Schematron_DataQuality_Checks/Basic_Checks/basic_checks.sch
M="./mvnw -q -pl Schematron_DataQuality_Checks/Basic_Checks/invocation compile exec:java"
$M -Dexec.args="$SCH FundsXML_Files/4.2.9/positions/Mixed-Fund_Positions.xml"   # exit 0 (0 errors)
$M -Dexec.args="$SCH tests/fixtures/invalid/schematron-invalid_Positions.xml"   # exit 1 (percentage 120%)
```
